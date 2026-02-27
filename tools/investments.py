#!/usr/bin/env python3
"""SkyBlock event investment tracker.

Analyzes event-driven price cycles using Coflnet historical data and recommends
when to buy/sell. Items flood the market during events (prices drop) and become
scarce between events (prices rise).

All historical data is fetched on-demand from Coflnet — no background jobs or
local snapshots needed.

Usage:
    python3 investments.py              # Recommendations + current prices + event timing
    python3 investments.py --calendar   # SkyBlock calendar + upcoming events
    python3 investments.py --event spooky  # Detail view for one event
    python3 investments.py --history GREEN_CANDY  # Price history for one item
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pricing import PriceCache, _fmt, display_name

DATA_DIR = Path(__file__).parent.parent / "data"

COFLNET_RATE_LIMIT = 0.6  # seconds between requests

# ─── SkyBlock Calendar Constants ─────────────────────────────────────

SB_EPOCH = 1_560_275_700      # Unix seconds — June 11, 2019 10:55 AM PDT
SB_YEAR_SECONDS = 446_400     # 124 real hours
SB_MONTH_SECONDS = 37_200     # 31 SB days * 1200 sec/day
SB_DAY_SECONDS = 1_200        # 20 real minutes
SB_HOUR_SECONDS = 50          # 50 real seconds

SB_MONTHS = [
    "Early Spring", "Spring", "Late Spring",
    "Early Summer", "Summer", "Late Summer",
    "Early Autumn", "Autumn", "Late Autumn",
    "Early Winter", "Winter", "Late Winter",
]

_MONTH_IDX = {name: i for i, name in enumerate(SB_MONTHS)}


def real_to_sb(unix_ts):
    """Convert real Unix timestamp to SB date."""
    elapsed = unix_ts - SB_EPOCH
    if elapsed < 0:
        return {"year": 0, "month_idx": 0, "month": SB_MONTHS[0], "day": 1}
    year = int(elapsed // SB_YEAR_SECONDS) + 1
    remainder = elapsed % SB_YEAR_SECONDS
    month_idx = min(int(remainder // SB_MONTH_SECONDS), 11)
    remainder = remainder % SB_MONTH_SECONDS
    day = int(remainder // SB_DAY_SECONDS) + 1
    return {"year": year, "month_idx": month_idx, "month": SB_MONTHS[month_idx], "day": day}


def sb_to_real(year, month_idx, day=1):
    """Convert SB date to real Unix timestamp."""
    return (SB_EPOCH
            + (year - 1) * SB_YEAR_SECONDS
            + month_idx * SB_MONTH_SECONDS
            + (day - 1) * SB_DAY_SECONDS)


def sb_month_day_to_year_offset(month_idx, day):
    """Get the offset in seconds from the start of a SB year."""
    return month_idx * SB_MONTH_SECONDS + (day - 1) * SB_DAY_SECONDS


def next_event_real_times(event, from_ts=None):
    """Return (start_unix, end_unix) for the next occurrence of an event."""
    if not event.get("schedule"):
        return None

    now = from_ts or time.time()
    sb_now = real_to_sb(now)
    current_year = sb_now["year"]

    for year in [current_year, current_year + 1]:
        year_start = sb_to_real(year, 0, 1)
        for month_idx, start_day, end_day in event["schedule"]:
            ev_start = year_start + sb_month_day_to_year_offset(month_idx, start_day)
            ev_end = year_start + sb_month_day_to_year_offset(month_idx, end_day) + SB_DAY_SECONDS
            if ev_end > now:
                return (ev_start, ev_end)

    return None


def time_until_str(unix_ts, from_ts=None):
    """Human-readable duration until a timestamp."""
    now = from_ts or time.time()
    diff = unix_ts - now
    if diff <= 0:
        return "NOW"
    days = int(diff // 86400)
    hours = int((diff % 86400) // 3600)
    minutes = int((diff % 3600) // 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}m")
    return " ".join(parts)


def event_duration_str(event):
    """Human-readable duration of the event in real time."""
    if not event.get("schedule"):
        return "varies"
    total_days = 0
    for _, start_day, end_day in event["schedule"]:
        total_days += end_day - start_day + 1
    total_seconds = total_days * SB_DAY_SECONDS
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    if hours and minutes:
        return f"{hours}h {minutes}m"
    elif hours:
        return f"{hours}h"
    return f"{minutes}m"


def cycle_position(event, from_ts=None):
    """Determine where we are in an event's cycle.

    Returns: "DURING_EVENT", "PRE_EVENT", "POST_EVENT", "MID_CYCLE",
             or "MAYOR_DEPENDENT"
    """
    if not event.get("schedule"):
        return "MAYOR_DEPENDENT"

    now = from_ts or time.time()
    times = next_event_real_times(event, now)
    if not times:
        return "MID_CYCLE"

    ev_start, ev_end = times

    if ev_start <= now < ev_end:
        return "DURING_EVENT"

    if 0 < ev_start - now <= SB_MONTH_SECONDS:
        return "PRE_EVENT"

    # Check previous occurrence for post-event
    sb_now = real_to_sb(now)
    for year in [sb_now["year"], sb_now["year"] - 1]:
        year_start = sb_to_real(year, 0, 1)
        for month_idx, start_day, end_day in event["schedule"]:
            prev_end = year_start + sb_month_day_to_year_offset(month_idx, end_day) + SB_DAY_SECONDS
            if 0 < now - prev_end <= SB_MONTH_SECONDS:
                return "POST_EVENT"

    return "MID_CYCLE"


def is_during_event(sb_date, event):
    """Check if a SB date falls within an event's schedule."""
    month_idx = sb_date["month_idx"]
    day = sb_date["day"]
    for ev_month, ev_start, ev_end in event.get("schedule", []):
        if month_idx == ev_month and ev_start <= day <= ev_end:
            return True
    return False


# ─── Event Definitions ───────────────────────────────────────────────

EVENTS = {
    "spooky": {
        "name": "Spooky Festival",
        "schedule": [(7, 29, 31)],  # Autumn (idx 7), days 29-31
        "shop_window": "Autumn 26 - Late Autumn 3",
        "items": {
            "GREEN_CANDY":              {"market": "bazaar",  "pattern": "flood_during"},
            "PURPLE_CANDY":             {"market": "bazaar",  "pattern": "flood_during"},
            "SPOOKY_SHARD":             {"market": "auction", "pattern": "flood_during"},
            "BAT_PERSON_HELMET":        {"market": "auction", "pattern": "flood_during"},
            "BAT_PERSON_CHESTPLATE":    {"market": "auction", "pattern": "flood_during"},
            "BAT_PERSON_LEGGINGS":      {"market": "auction", "pattern": "flood_during"},
            "BAT_PERSON_BOOTS":         {"market": "auction", "pattern": "flood_during"},
            "SPOOKY_HELMET":            {"market": "auction", "pattern": "flood_during"},
            "SPOOKY_CHESTPLATE":        {"market": "auction", "pattern": "flood_during"},
            "SPOOKY_LEGGINGS":          {"market": "auction", "pattern": "flood_during"},
            "SPOOKY_BOOTS":             {"market": "auction", "pattern": "flood_during"},
            "CANDY_ARTIFACT":           {"market": "auction", "pattern": "flood_during"},
            "CANDY_RELIC":              {"market": "auction", "pattern": "flood_during"},
        },
    },
    "jerry": {
        "name": "Jerry's Workshop",
        "schedule": [(11, 1, 31)],  # Late Winter (idx 11), full month
        "items": {
            "WHITE_GIFT":               {"market": "auction", "pattern": "flood_during"},
            "GREEN_GIFT":               {"market": "auction", "pattern": "flood_during"},
            "RED_GIFT":                 {"market": "auction", "pattern": "flood_during"},
            "GLACIAL_FRAGMENT":         {"market": "auction", "pattern": "flood_during"},
            "FROZEN_BAUBLE":            {"market": "auction", "pattern": "flood_during"},
            "JINGLE_BELLS":             {"market": "auction", "pattern": "flood_during"},
            "SNOW_SUIT_HELMET":         {"market": "auction", "pattern": "flood_during"},
            "SNOW_SUIT_CHESTPLATE":     {"market": "auction", "pattern": "flood_during"},
            "SNOW_SUIT_LEGGINGS":       {"market": "auction", "pattern": "flood_during"},
            "SNOW_SUIT_BOOTS":          {"market": "auction", "pattern": "flood_during"},
            "NUTCRACKER_HELMET":        {"market": "auction", "pattern": "flood_during"},
            "NUTCRACKER_CHESTPLATE":    {"market": "auction", "pattern": "flood_during"},
            "NUTCRACKER_LEGGINGS":      {"market": "auction", "pattern": "flood_during"},
            "NUTCRACKER_BOOTS":         {"market": "auction", "pattern": "flood_during"},
            "YETI_SWORD":              {"market": "auction", "pattern": "flood_during"},
        },
    },
    "hoppity": {
        "name": "Hoppity's Hunt",
        "schedule": [(0, 1, 31)],  # Early Spring (idx 0), full month
        "items": {
            "NIBBLE_CHOCOLATE_STICK":   {"market": "auction", "pattern": "demand_before"},
            "SMOOTH_CHOCOLATE_BAR":     {"market": "auction", "pattern": "demand_before"},
            "RICH_CHOCOLATE_CHUNK":     {"market": "auction", "pattern": "demand_before"},
            "GANACHE_CHOCOLATE_SLAB":   {"market": "auction", "pattern": "demand_before"},
            "PRESTIGE_CHOCOLATE_REALM": {"market": "auction", "pattern": "demand_before"},
        },
    },
    "zoo": {
        "name": "Traveling Zoo",
        "schedule": [(3, 1, 3), (9, 1, 3)],  # Early Summer + Early Winter, days 1-3
        "items": {
            "ENCHANTED_RAW_FISH":       {"market": "bazaar",  "pattern": "demand_before"},
            "ENCHANTED_CLOWNFISH":      {"market": "bazaar",  "pattern": "demand_before"},
            "ENCHANTED_RAW_CHICKEN":    {"market": "bazaar",  "pattern": "demand_before"},
            "ENCHANTED_RAW_BEEF":       {"market": "bazaar",  "pattern": "demand_before"},
            "ENCHANTED_PORK":           {"market": "bazaar",  "pattern": "demand_before"},
        },
    },
    "fishing": {
        "name": "Fishing Festival",
        "schedule": [],
        "mayor_dependent": True,
        "mayors": ["Marina"],
        "items": {
            "SHARK_FIN":                {"market": "bazaar",  "pattern": "flood_during"},
            "ENCHANTED_SHARK_FIN":      {"market": "bazaar",  "pattern": "flood_during"},
            "NURSE_SHARK_TOOTH":        {"market": "auction", "pattern": "flood_during"},
            "BLUE_SHARK_TOOTH":         {"market": "auction", "pattern": "flood_during"},
            "TIGER_SHARK_TOOTH":        {"market": "auction", "pattern": "flood_during"},
            "GREAT_WHITE_SHARK_TOOTH":  {"market": "auction", "pattern": "flood_during"},
        },
    },
    "mining": {
        "name": "Mining Fiesta",
        "schedule": [],
        "mayor_dependent": True,
        "mayors": ["Cole"],
        "items": {
            "REFINED_MINERAL":          {"market": "bazaar",  "pattern": "flood_during"},
            "GLOSSY_GEMSTONE":          {"market": "bazaar",  "pattern": "flood_during"},
        },
    },
}


# ─── Coflnet Historical Data ────────────────────────────────────────

def _coflnet_get(url):
    """Fetch JSON from a Coflnet endpoint."""
    req = Request(url, headers={"User-Agent": "SkyblockInvestments/1.0"})
    with urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _parse_coflnet_ts(ts_str):
    """Parse a Coflnet timestamp into Unix seconds."""
    dt = datetime.fromisoformat(ts_str.replace("Z", ""))
    dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def fetch_item_history(item_id, market, days=30):
    """Fetch price history for one item from Coflnet.

    Returns list of {ts, sb_date, price, volume} dicts, sorted by time.
    """
    points = []

    if market == "bazaar":
        # Custom date range for bazaar
        now = time.time()
        start_ts = now - days * 86400
        start_iso = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        end_iso = datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        url = f"https://sky.coflnet.com/api/bazaar/{item_id}/history?start={start_iso}&end={end_iso}"

        try:
            records = _coflnet_get(url)
            for r in records:
                ts = _parse_coflnet_ts(r["timestamp"])
                points.append({
                    "ts": ts,
                    "sb_date": real_to_sb(ts),
                    "price": r.get("buy", 0) or 0,
                    "sell": r.get("sell", 0) or 0,
                    "volume": r.get("buyVolume", 0),
                })
        except (HTTPError, URLError, OSError, KeyError, ValueError):
            pass

    else:
        # AH item — use /history/month (30 days, daily intervals)
        url = f"https://sky.coflnet.com/api/item/price/{item_id}/history/month"

        try:
            records = _coflnet_get(url)
            for r in records:
                ts = _parse_coflnet_ts(r["time"])
                points.append({
                    "ts": ts,
                    "sb_date": real_to_sb(ts),
                    "price": r.get("avg", 0) or 0,
                    "min": r.get("min", 0) or 0,
                    "max": r.get("max", 0) or 0,
                    "volume": r.get("volume", 0),
                })
        except (HTTPError, URLError, OSError, KeyError, ValueError):
            pass

    points.sort(key=lambda p: p["ts"])
    return points


def fetch_all_history(items_by_market):
    """Fetch history for multiple items, respecting rate limits.

    items_by_market: dict of item_id -> market ("bazaar" or "auction")
    Returns dict of item_id -> [points]
    """
    history = {}
    total = len(items_by_market)

    for i, (item_id, market) in enumerate(items_by_market.items()):
        name = display_name(item_id)
        print(f"  [{i+1}/{total}] {name}...", end="", file=sys.stderr, flush=True)
        points = fetch_item_history(item_id, market)
        history[item_id] = points
        print(f" {len(points)} pts", file=sys.stderr)
        if i < total - 1:
            time.sleep(COFLNET_RATE_LIMIT)

    return history


# ─── Current Prices (Moulberry + Bazaar) ─────────────────────────────

MOULBERRY_LBIN_URL = "https://moulberry.codes/lowestbin.json"


def fetch_current_prices():
    """Fetch current prices for all tracked items.

    Returns dict: item_id -> {"price": float, "market": str}
    """
    bazaar_items = set()
    auction_items = set()
    for event in EVENTS.values():
        for item_id, info in event["items"].items():
            if info["market"] == "bazaar":
                bazaar_items.add(item_id)
            else:
                auction_items.add(item_id)

    prices = {}

    # Bazaar — single bulk request
    pc = PriceCache()
    pc._fetch_bazaar()
    for item_id in bazaar_items:
        bz = pc._bazaar.get(item_id)
        if bz:
            prices[item_id] = {
                "price": bz.get("buy", 0),
                "sell": bz.get("sell", 0),
                "market": "bazaar",
            }
    pc.flush()

    # Auction — Moulberry bulk lowest BIN
    try:
        req = Request(MOULBERRY_LBIN_URL, headers={"User-Agent": "SkyblockInvestments/1.0"})
        with urlopen(req, timeout=15) as resp:
            lowestbin = json.loads(resp.read())
        for item_id in auction_items:
            lbin = lowestbin.get(item_id, 0)
            if lbin:
                prices[item_id] = {"price": lbin, "market": "auction"}
    except (HTTPError, URLError, OSError):
        pass

    return prices


# ─── Analysis ────────────────────────────────────────────────────────

def compute_item_stats(points, event):
    """Compute event vs off-event stats from historical data points."""
    event_prices = []
    off_event_prices = []

    for pt in points:
        price = pt.get("price", 0)
        if not price or price <= 0:
            continue
        if is_during_event(pt["sb_date"], event):
            event_prices.append(price)
        else:
            off_event_prices.append(price)

    if not event_prices and not off_event_prices:
        return None

    result = {
        "event_count": len(event_prices),
        "off_event_count": len(off_event_prices),
    }
    if event_prices:
        result["event_avg"] = sum(event_prices) / len(event_prices)
        result["event_min"] = min(event_prices)
        result["event_max"] = max(event_prices)
    if off_event_prices:
        result["off_event_avg"] = sum(off_event_prices) / len(off_event_prices)
        result["off_event_min"] = min(off_event_prices)
        result["off_event_max"] = max(off_event_prices)

    return result


def recommend(item_id, event, current_price, stats, position):
    """Generate a BUY/SELL/HOLD/WATCH recommendation."""
    pattern = event["items"][item_id].get("pattern", "flood_during")

    if not stats or (stats.get("event_count", 0) + stats.get("off_event_count", 0)) < 3:
        return ("WATCH", "Insufficient data", None)

    event_avg = stats.get("event_avg")
    off_event_avg = stats.get("off_event_avg")

    if not event_avg or not off_event_avg:
        return ("WATCH", "Need both event and off-event data", None)

    buy_target = min(event_avg, off_event_avg)
    sell_target = max(event_avg, off_event_avg)

    def profit_pct(from_price):
        if from_price <= 0:
            return None
        pct = ((sell_target / from_price) - 1) * 100
        return f"+{pct:.0f}%" if pct > 0 else None

    if pattern == "demand_before":
        # Prices rise around event, fall off-event. Buy off-event, sell pre/during.
        if position == "DURING_EVENT":
            if current_price >= event_avg * 0.9:
                return ("SELL", "Event active, demand price peak", None)
            return ("HOLD", "Event active but price below avg", None)
        elif position == "PRE_EVENT":
            if current_price >= event_avg * 0.9:
                return ("SELL", "Demand peaks before event", None)
            return ("BUY", "Pre-event but price still low", profit_pct(current_price))
        elif position == "POST_EVENT":
            return ("BUY", "Post-event, demand fading", profit_pct(current_price))
        else:
            if current_price <= off_event_avg * 1.1:
                return ("BUY", "Off-event lows, buy for next event", profit_pct(current_price))
            return ("HOLD", "Mid-cycle, price above off-event avg", None)
    else:
        # flood_during: prices drop during event. Buy during, sell off-event.
        if position == "DURING_EVENT":
            if current_price <= event_avg * 1.1:
                return ("BUY", "Event active, price near event low", profit_pct(current_price))
            return ("HOLD", "Event active but price above event avg", None)
        elif position == "PRE_EVENT":
            return ("HOLD", "Event approaching, prices should drop soon", None)
        elif position == "POST_EVENT":
            if current_price <= event_avg * 1.2:
                return ("BUY", "Post-event, price still near lows", profit_pct(current_price))
            return ("HOLD", "Post-event, price already recovering", None)
        else:
            if current_price >= off_event_avg * 0.9:
                return ("SELL", "Price near off-event highs", None)
            elif current_price <= buy_target * 1.3:
                return ("BUY", "Price below event avg mid-cycle", profit_pct(current_price))
            return ("HOLD", "Mid-cycle, between averages", None)


# ─── Display: Calendar ───────────────────────────────────────────────

def show_calendar():
    """Show SkyBlock calendar and upcoming events."""
    now = time.time()
    sb = real_to_sb(now)
    real_dt = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M")

    print(f"\nSkyBlock Calendar")
    print("=" * 60)
    print(f"  Current:   Year {sb['year']}, {sb['month']}, Day {sb['day']}")
    print(f"  Real time: {real_dt}")
    print()

    upcoming = []
    for key, event in EVENTS.items():
        times = next_event_real_times(event, now)
        pos = cycle_position(event, now)
        if times:
            upcoming.append((times[0], times[1], key, event, pos))
        else:
            upcoming.append((float('inf'), 0, key, event, pos))

    upcoming.sort(key=lambda x: x[0])

    print(f"  {'Event':<26s} {'Schedule':<28s} {'Status':<16s} Duration")
    print(f"  {'-'*26} {'-'*28} {'-'*16} {'-'*10}")

    for start, end, key, event, pos in upcoming:
        name = event["name"]
        if len(name) > 26:
            name = name[:23] + "..."

        if not event.get("schedule"):
            schedule_str = "Mayor-dependent"
            status = f"({', '.join(event.get('mayors', []))})"
            dur = "varies"
        else:
            parts = []
            for m_idx, s_day, e_day in event["schedule"]:
                parts.append(f"{SB_MONTHS[m_idx]} {s_day}-{e_day}")
            schedule_str = ", ".join(parts)
            if len(schedule_str) > 28:
                schedule_str = schedule_str[:25] + "..."
            dur = event_duration_str(event)

            if pos == "DURING_EVENT":
                status = "ACTIVE NOW"
            elif start < float('inf'):
                status = f"in {time_until_str(start, now)}"
            else:
                status = "unknown"

        print(f"  {name:<26s} {schedule_str:<28s} {status:<16s} {dur}")

    print()


# ─── Display: Event Detail ───────────────────────────────────────────

def show_event_detail(event_key):
    """Show detailed view for one event with Coflnet history."""
    matched = None
    for key in EVENTS:
        if event_key.lower() in key:
            matched = key
            break
    if not matched:
        print(f"  Unknown event '{event_key}'. Available: {', '.join(EVENTS.keys())}")
        return

    event = EVENTS[matched]
    now = time.time()
    pos = cycle_position(event, now)
    times = next_event_real_times(event, now)

    print(f"\n{event['name'].upper()}")
    print("=" * 70)

    if event.get("schedule"):
        parts = []
        for m_idx, s_day, e_day in event["schedule"]:
            parts.append(f"{SB_MONTHS[m_idx]} {s_day}-{e_day}")
        print(f"  Schedule:  {', '.join(parts)} ({event_duration_str(event)} real time)")
        if event.get("shop_window"):
            print(f"  Shop:      {event['shop_window']}")
        if times:
            start, end = times
            if pos == "DURING_EVENT":
                print(f"  Status:    ACTIVE NOW (ends in {time_until_str(end, now)})")
            else:
                print(f"  Next:      in {time_until_str(start, now)}")
    else:
        print(f"  Schedule:  Mayor-dependent ({', '.join(event.get('mayors', []))})")

    print(f"  Cycle:     {pos.replace('_', ' ').title()}")

    # Fetch history from Coflnet
    items_by_market = {iid: info["market"] for iid, info in event["items"].items()}
    print(f"\n  Fetching 30-day history from Coflnet...", file=sys.stderr)
    history = fetch_all_history(items_by_market)

    # Current prices
    prices = fetch_current_prices()

    print(f"\n  {'Item':<28s} {'Market':<8s} {'Current':>10s}  {'Event Avg':>10s}  {'Off-Event':>10s}  {'Pts':>4s}  Pattern")
    print(f"  {'-'*28} {'-'*8} {'-'*10}  {'-'*10}  {'-'*10}  {'-'*4}  {'-'*14}")

    for item_id, info in event["items"].items():
        name = display_name(item_id)
        if len(name) > 28:
            name = name[:25] + "..."

        p = prices.get(item_id, {})
        current = p.get("price", 0)
        current_str = _fmt(current) if current else "N/A"

        points = history.get(item_id, [])
        stats = compute_item_stats(points, event)
        ev_str = _fmt(stats["event_avg"]) if stats and stats.get("event_avg") else "---"
        off_str = _fmt(stats["off_event_avg"]) if stats and stats.get("off_event_avg") else "---"
        pts = str(len(points)) if points else "0"

        print(f"  {name:<28s} {info['market']:<8s} {current_str:>10s}  {ev_str:>10s}  {off_str:>10s}  {pts:>4s}  {info['pattern']}")

    print()


# ─── Display: Item History ───────────────────────────────────────────

def show_item_history(item_id_query):
    """Show price history for a specific item."""
    item_id = item_id_query.upper()

    # Find which event(s) track this item
    found_events = []
    market = None
    for key, event in EVENTS.items():
        if item_id in event["items"]:
            found_events.append((key, event))
            market = event["items"][item_id]["market"]

    if not found_events:
        print(f"  '{item_id}' is not a tracked event item.")
        print(f"  Tracked items:")
        for key, event in EVENTS.items():
            items = ", ".join(sorted(event["items"].keys()))
            print(f"    {event['name']}: {items}")
        return

    name = display_name(item_id)
    event_names = ", ".join(e["name"] for _, e in found_events)

    print(f"\n{name} -- Price History")
    print("=" * 80)
    print(f"  Market: {market.title()} | Events: {event_names}")

    # Fetch history
    print(f"  Fetching from Coflnet...", file=sys.stderr)
    points = fetch_item_history(item_id, market)

    if not points:
        print(f"\n  No historical data available from Coflnet.")
        print()
        return

    # Tag event points
    for pt in points:
        pt["during_event"] = any(
            is_during_event(pt["sb_date"], event) for _, event in found_events
        )

    # Stats
    event_prices = [p["price"] for p in points if p["during_event"] and p["price"] > 0]
    off_prices = [p["price"] for p in points if not p["during_event"] and p["price"] > 0]
    all_prices = [p["price"] for p in points if p["price"] > 0]

    if all_prices:
        print(f"\n  Statistics ({len(all_prices)} data points):")
        if event_prices:
            print(f"    Event avg:      {_fmt(sum(event_prices)/len(event_prices))} ({len(event_prices)} points)")
        if off_prices:
            print(f"    Off-event avg:  {_fmt(sum(off_prices)/len(off_prices))} ({len(off_prices)} points)")
        if event_prices and off_prices:
            ratio = (sum(off_prices)/len(off_prices)) / (sum(event_prices)/len(event_prices))
            print(f"    Ratio:          {ratio:.1f}x")
        print(f"    All-time low:   {_fmt(min(all_prices))}")
        print(f"    All-time high:  {_fmt(max(all_prices))}")

    # Table
    print(f"\n  {'Date':<14s} {'SB Date':<28s} {'Price':>10s}", end="")
    if market == "bazaar":
        print(f"  {'Sell':>10s}  {'Volume':>10s}", end="")
    else:
        print(f"  {'Volume':>7s}", end="")
    print(f"  Event?")
    print(f"  {'-'*14} {'-'*28} {'-'*10}", end="")
    if market == "bazaar":
        print(f"  {'-'*10}  {'-'*10}", end="")
    else:
        print(f"  {'-'*7}", end="")
    print(f"  {'-'*6}")

    for pt in points:
        if pt["price"] <= 0:
            continue
        dt_str = datetime.fromtimestamp(pt["ts"]).strftime("%m-%d %H:%M")
        sbd = pt["sb_date"]
        sb_str = f"Y{sbd['year']} {sbd['month']} {sbd['day']}"
        marker = " *" if pt["during_event"] else ""
        print(f"  {dt_str:<14s} {sb_str:<28s} {_fmt(pt['price']):>10s}", end="")
        if market == "bazaar":
            print(f"  {_fmt(pt.get('sell', 0)):>10s}  {_fmt(pt.get('volume', 0)):>10s}", end="")
        else:
            print(f"  {pt.get('volume', 0):>7d}", end="")
        print(f"  {marker}")

    print()


# ─── Display: Recommendations ────────────────────────────────────────

def show_recommendations():
    """Show investment recommendations based on Coflnet history + current prices."""
    now = time.time()
    sb = real_to_sb(now)
    real_dt = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M")

    print(f"\nSkyBlock Investment Tracker")
    print(f"  Current: Year {sb['year']}, {sb['month']}, Day {sb['day']}  |  {real_dt}")

    # Show event status
    print(f"\n  EVENTS")
    print(f"  {'-'*60}")
    for key, event in EVENTS.items():
        pos = cycle_position(event, now)
        times = next_event_real_times(event, now)
        name = event["name"]
        if pos == "DURING_EVENT" and times:
            _, end = times
            print(f"  {name:<24s}  ACTIVE (ends in {time_until_str(end, now)})")
        elif pos == "MAYOR_DEPENDENT":
            print(f"  {name:<24s}  Mayor-dependent ({', '.join(event.get('mayors', []))})")
        elif times:
            start, _ = times
            print(f"  {name:<24s}  {pos.replace('_', ' ').lower():<14s} (next in {time_until_str(start, now)})")
        else:
            print(f"  {name:<24s}  {pos.replace('_', ' ').lower()}")

    # Collect all items to fetch history for
    items_by_market = {}
    for event in EVENTS.values():
        for item_id, info in event["items"].items():
            items_by_market[item_id] = info["market"]

    print(f"\n  Fetching 30-day history from Coflnet ({len(items_by_market)} items)...", file=sys.stderr)
    history = fetch_all_history(items_by_market)

    # Current prices
    print(f"  Fetching current prices...", file=sys.stderr)
    prices = fetch_current_prices()

    # Generate recommendations
    recs = []
    for key, event in EVENTS.items():
        pos = cycle_position(event, now)
        for item_id, info in event["items"].items():
            p = prices.get(item_id, {})
            current = p.get("price", 0)
            if not current:
                continue

            points = history.get(item_id, [])
            stats = compute_item_stats(points, event)
            action, reason, profit_pct = recommend(item_id, event, current, stats, pos)

            recs.append({
                "item_id": item_id,
                "event": event["name"],
                "market": info["market"],
                "current": current,
                "action": action,
                "reason": reason,
                "profit_pct": profit_pct,
                "event_avg": stats.get("event_avg") if stats else None,
                "off_event_avg": stats.get("off_event_avg") if stats else None,
            })

    # Sort by action priority, then price descending
    action_order = {"BUY": 0, "SELL": 1, "HOLD": 2, "WATCH": 3}
    recs.sort(key=lambda r: (action_order.get(r["action"], 4), -(r.get("current") or 0)))

    buys = [r for r in recs if r["action"] == "BUY"]
    sells = [r for r in recs if r["action"] == "SELL"]
    holds = [r for r in recs if r["action"] == "HOLD"]
    watches = [r for r in recs if r["action"] == "WATCH"]

    if buys:
        print(f"\n  BUY RECOMMENDATIONS")
        print(f"  {'Item':<26s} {'Event':<18s} {'Current':>10s}  {'Event Avg':>10s}  {'Off-Event':>10s}  {'Profit':>7s}  Reason")
        print(f"  {'-'*26} {'-'*18} {'-'*10}  {'-'*10}  {'-'*10}  {'-'*7}  {'-'*30}")
        for r in buys:
            name = display_name(r["item_id"])
            if len(name) > 26:
                name = name[:23] + "..."
            ev_name = r["event"][:18]
            ev_str = _fmt(r["event_avg"]) if r["event_avg"] else "---"
            off_str = _fmt(r["off_event_avg"]) if r["off_event_avg"] else "---"
            pct_str = r["profit_pct"] or ""
            print(f"  {name:<26s} {ev_name:<18s} {_fmt(r['current']):>10s}  {ev_str:>10s}  {off_str:>10s}  {pct_str:>7s}  {r['reason']}")

    if sells:
        print(f"\n  SELL RECOMMENDATIONS")
        print(f"  {'Item':<26s} {'Event':<18s} {'Current':>10s}  Reason")
        print(f"  {'-'*26} {'-'*18} {'-'*10}  {'-'*30}")
        for r in sells:
            name = display_name(r["item_id"])
            if len(name) > 26:
                name = name[:23] + "..."
            print(f"  {name:<26s} {r['event'][:18]:<18s} {_fmt(r['current']):>10s}  {r['reason']}")

    if holds:
        print(f"\n  HOLD")
        print(f"  {'Item':<26s} {'Event':<18s} {'Current':>10s}  Reason")
        print(f"  {'-'*26} {'-'*18} {'-'*10}  {'-'*30}")
        for r in holds:
            name = display_name(r["item_id"])
            if len(name) > 26:
                name = name[:23] + "..."
            print(f"  {name:<26s} {r['event'][:18]:<18s} {_fmt(r['current']):>10s}  {r['reason']}")

    if watches:
        print(f"\n  WATCH (insufficient history)")
        for r in watches:
            name = display_name(r["item_id"])
            if len(name) > 26:
                name = name[:23] + "..."
            print(f"  {name:<26s} {r['event'][:18]:<18s} {_fmt(r['current']):>10s}")

    if not recs:
        print(f"\n  No price data available for tracked items.")

    print()


# ─── Main ────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="SkyBlock event investment tracker (Coflnet-powered)")
    parser.add_argument("--calendar", action="store_true",
                        help="Show SkyBlock calendar and upcoming events")
    parser.add_argument("--event", type=str, metavar="EVENT",
                        help="Show details for a specific event")
    parser.add_argument("--history", type=str, metavar="ITEM_ID",
                        help="Show price history for a specific item")

    args = parser.parse_args()

    if args.calendar:
        show_calendar()
    elif args.event:
        show_event_detail(args.event)
    elif args.history:
        show_item_history(args.history)
    else:
        show_recommendations()


if __name__ == "__main__":
    main()
