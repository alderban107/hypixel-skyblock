#!/usr/bin/env python3
"""Forge Profit Calculator for Hypixel SkyBlock.

Shows profitable forge recipes sorted by profit/hour, using Coflnet's
pre-computed /api/flip/forge endpoint (single call, no rate limit concern).

Accounts for Quick Forge perk level (reduces forge time) and filters by
HotM (Heart of the Mountain) level from profile data.

Data source: Coflnet /api/flip/forge (pre-computed, single call)

Usage:
    python3 forge.py                    # all profitable forges
    python3 forge.py --hotm 5           # filter by HotM level 5+
    python3 forge.py --top 20           # show top 20 only
    python3 forge.py --quick-forge 20   # Quick Forge perk level (% time reduction)
    python3 forge.py --profile          # auto-detect HotM from profile
    python3 forge.py --buy-order        # use buy order costs (cheaper inputs)
    python3 forge.py --json             # machine-readable output
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from items import display_name
from pricing import _fmt

DATA_DIR = Path(__file__).parent.parent / "data"
LAST_PROFILE_PATH = DATA_DIR / "last_profile.json"
FORGE_API_URL = "https://sky.coflnet.com/api/flip/forge"

# Quick Forge reduces forge time by this % per perk level
# Max level is 20 (reduces by 30% total)
QUICK_FORGE_REDUCTION = {
    0: 0.0,
    1: 0.005, 2: 0.01, 3: 0.015, 4: 0.02, 5: 0.03,
    6: 0.04, 7: 0.05, 8: 0.06, 9: 0.07, 10: 0.10,
    11: 0.113, 12: 0.126, 13: 0.139, 14: 0.152, 15: 0.165,
    16: 0.178, 17: 0.191, 18: 0.204, 19: 0.217, 20: 0.30,
}

# Color codes from Minecraft formatting → strip
import re
_COLOR_CODE_RE = re.compile(r"§[0-9a-fk-or]")


def fetch_forge_data():
    """Fetch forge profit data from Coflnet API."""
    req = Request(FORGE_API_URL, headers={"User-Agent": "SkyBlock-Tools/1.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except (HTTPError, URLError, json.JSONDecodeError) as e:
        print(f"ERROR: Failed to fetch Coflnet forge data: {e}", file=sys.stderr)
        sys.exit(1)


def load_profile_hotm():
    """Try to load HotM level from cached profile data."""
    if not LAST_PROFILE_PATH.exists():
        return None
    try:
        data = json.loads(LAST_PROFILE_PATH.read_text())
        uuid = data.get("uuid", "")
        members = data.get("profile", {}).get("members", {})
        # Find the correct member by UUID
        mdata = None
        for key, val in members.items():
            if key.replace("-", "") == uuid:
                mdata = val
                break
        if not mdata:
            # Fallback: use first member
            mdata = next(iter(members.values()), None)
        if not mdata:
            return None

        # HotM XP — check new path first (skill_tree.experience.mining),
        # fall back to old path (mining_core.experience)
        experience = (mdata.get("skill_tree", {}).get("experience", {}).get("mining", 0)
                      or mdata.get("mining_core", {}).get("experience", 0))

        # Quick Forge — check new path first (skill_tree.nodes.mining),
        # fall back to old path (mining_core.nodes)
        quick_forge_level = (mdata.get("skill_tree", {}).get("nodes", {})
                             .get("mining", {}).get("forge_time", 0)
                             or mdata.get("mining_core", {}).get("nodes", {})
                             .get("forge_time", 0))

        hotm_level = 0
        hotm_xp_table = [0, 3000, 12000, 37000, 97000, 197000, 347000, 557000, 847000, 1247000]
        for lvl, xp_needed in enumerate(hotm_xp_table):
            if experience >= xp_needed:
                hotm_level = lvl + 1

        return {"hotm": hotm_level, "quick_forge": quick_forge_level}
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def format_duration(hours):
    """Format duration in hours to human-readable string."""
    if hours < 1:
        minutes = hours * 60
        if minutes < 1:
            return f"{minutes * 60:.0f}s"
        return f"{minutes:.0f}m"
    if hours < 24:
        h = int(hours)
        m = int((hours - h) * 60)
        if m:
            return f"{h}h {m}m"
        return f"{h}h"
    days = hours / 24
    if days == int(days):
        return f"{int(days)}d"
    d = int(days)
    h = int((days - d) * 24)
    return f"{d}d {h}h"


def calc_forge_profits(forge_data, hotm_filter=None, quick_forge_level=0, use_buy_order=False):
    """Process raw forge data into sorted profit entries.

    Args:
        forge_data: raw API response list
        hotm_filter: minimum HotM level filter (None = no filter)
        quick_forge_level: Quick Forge perk level (0-20)
        use_buy_order: use buy order costs instead of instant buy

    Returns:
        list of processed forge entries, sorted by profit/hour
    """
    time_mult = 1.0 - QUICK_FORGE_REDUCTION.get(quick_forge_level, 0)
    results = []

    for entry in forge_data:
        craft = entry.get("craftData", {})
        # Coflnet returns duration in seconds; convert to hours
        duration_hours = entry.get("duration", 0) / 3600
        hotm_required = entry.get("requiredHotMLevel", 0)
        requirements = entry.get("requirements", {})

        # Sanity check: warn if duration exceeds 30 days (possible API unit change)
        if duration_hours > 720:
            print(f"  Warning: {entry.get('craftData', {}).get('itemName', '?')} "
                  f"duration is {duration_hours:.0f}h ({duration_hours/24:.0f}d) — "
                  f"possible API unit change", file=sys.stderr)

        # Filter by HotM
        if hotm_filter is not None and hotm_required > hotm_filter:
            continue

        item_id = craft.get("itemId", "")
        item_name = _COLOR_CODE_RE.sub("", craft.get("itemName", "")).strip()
        sell_price = craft.get("sellPrice", 0) or 0
        median_price = craft.get("median", 0) or 0
        volume = craft.get("volume", 0) or 0

        # Use sell_price (LBIN) for conservative estimate
        # Use median for reference
        price = sell_price

        if use_buy_order:
            craft_cost = craft.get("buyOrderCraftCost", 0) or craft.get("craftCost", 0) or 0
        else:
            craft_cost = craft.get("craftCost", 0) or 0

        if craft_cost <= 0 or price <= 0:
            continue

        profit = price - craft_cost
        if profit <= 0:
            continue

        # Adjust duration for Quick Forge
        adj_duration = duration_hours * time_mult
        if adj_duration <= 0:
            adj_duration = 0.0167  # minimum ~1 minute

        profit_per_hour = profit / adj_duration

        # Parse ingredients
        ingredients = []
        for ing in craft.get("ingredients", []):
            ing_id = ing.get("itemId", "")
            ing_count = ing.get("count", 1)
            if use_buy_order:
                ing_cost = ing.get("buyOrderCost") or ing.get("cost", 0) or 0
            else:
                ing_cost = ing.get("cost", 0) or 0
            ingredients.append({
                "item_id": ing_id,
                "count": ing_count,
                "cost": ing_cost,
            })

        results.append({
            "item_id": item_id,
            "item_name": item_name or display_name(item_id),
            "sell_price": price,
            "median_price": median_price,
            "craft_cost": craft_cost,
            "profit": profit,
            "duration_hours": adj_duration,
            "raw_duration_hours": duration_hours,
            "profit_per_hour": profit_per_hour,
            "hotm_required": hotm_required,
            "volume": volume,
            "ingredients": ingredients,
            "requirements": requirements,
        })

    results.sort(key=lambda x: x["profit_per_hour"], reverse=True)
    return results


def print_detail(entry):
    """Print detailed breakdown for one forge recipe."""
    print(f"\n{'═' * 60}")
    print(f"  {entry['item_name']}")
    print(f"{'═' * 60}")
    print(f"  Sell Price:   {_fmt(entry['sell_price']):>12s}")
    print(f"  Median:       {_fmt(entry['median_price']):>12s}")
    print(f"  Craft Cost:   {_fmt(entry['craft_cost']):>12s}")
    print(f"  Profit:       {_fmt(entry['profit']):>12s}")
    print(f"  Duration:     {format_duration(entry['raw_duration_hours']):>12s}", end="")
    if entry['duration_hours'] != entry['raw_duration_hours']:
        print(f" → {format_duration(entry['duration_hours'])} (Quick Forge)")
    else:
        print()
    print(f"  Profit/Hour:  {_fmt(entry['profit_per_hour']):>12s}")
    print(f"  HotM Req:     {entry['hotm_required']:>12d}")
    print(f"  Volume/Day:   {entry['volume']:>12.1f}")
    print()
    print(f"  Ingredients:")
    for ing in entry["ingredients"]:
        name = display_name(ing["item_id"])
        print(f"    {ing['count']:>3d}× {name:<30s} {_fmt(ing['cost']):>10s}")


def print_summary(results, top_n=None, quick_forge_level=0):
    """Print forge profit summary table."""
    print(f"\n{'═' * 90}")
    print(f"  Forge Profit Calculator — Sorted by Profit/Hour")
    if quick_forge_level > 0:
        reduction = QUICK_FORGE_REDUCTION.get(quick_forge_level, 0) * 100
        print(f"  Quick Forge Level {quick_forge_level} ({reduction:.1f}% time reduction)")
    print(f"{'═' * 90}")
    print()

    display = results[:top_n] if top_n else results

    print(f"  {'#':>3s}  {'Item':<35s} {'Profit':>10s} {'Duration':>8s} {'Profit/hr':>10s} {'HotM':>4s} {'Vol':>5s}")
    print(f"  {'─' * 3}  {'─' * 35} {'─' * 10} {'─' * 8} {'─' * 10} {'─' * 4} {'─' * 5}")

    for i, entry in enumerate(display, 1):
        name = entry["item_name"][:33]
        dur = format_duration(entry["duration_hours"])
        vol = f"{entry['volume']:.1f}" if entry["volume"] >= 0.1 else "<0.1"

        print(f"  {i:>3d}  {name:<35s} {_fmt(entry['profit']):>10s} {dur:>8s} "
              f"{_fmt(entry['profit_per_hour']):>10s} {entry['hotm_required']:>4d} {vol:>5s}")

    total_shown = len(display)
    total_all = len(results)
    print()
    print(f"  Showing {total_shown} of {total_all} profitable forges")
    if total_all > total_shown:
        print(f"  Use --top {total_all} to see all, or --type to filter")
    print()
    print("  Volume = estimated daily sales. Low volume items may be hard to sell.")
    print("  Profit uses LBIN sell price − instant-buy ingredient cost (conservative).")
    print("  Use --buy-order for cheaper ingredient costs (slower to fill).")


def main():
    parser = argparse.ArgumentParser(description="SkyBlock Forge Profit Calculator")
    parser.add_argument("--hotm", type=int, metavar="LEVEL",
                        help="Filter by max HotM level")
    parser.add_argument("--top", type=int, metavar="N",
                        help="Show top N results")
    parser.add_argument("--quick-forge", "-q", type=int, default=0, metavar="LEVEL",
                        help="Quick Forge perk level (0-20, default: 0)")
    parser.add_argument("--profile", "-p", action="store_true",
                        help="Auto-detect HotM and Quick Forge from profile")
    parser.add_argument("--buy-order", "-b", action="store_true",
                        help="Use buy order costs (cheaper but slower)")
    parser.add_argument("--item", "-i", type=str, metavar="ITEM_ID",
                        help="Show detail for specific item")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    args = parser.parse_args()

    hotm_filter = args.hotm
    quick_forge_level = args.quick_forge

    # Auto-detect from profile
    if args.profile:
        profile_data = load_profile_hotm()
        if profile_data:
            if hotm_filter is None:
                hotm_filter = profile_data.get("hotm", 0)
                print(f"  Detected HotM level: {hotm_filter}")
            if quick_forge_level == 0 and profile_data.get("quick_forge", 0) > 0:
                quick_forge_level = profile_data["quick_forge"]
                print(f"  Detected Quick Forge level: {quick_forge_level}")
        else:
            print("  Warning: Could not load profile data. Run profile.py first.", file=sys.stderr)

    forge_data = fetch_forge_data()
    print(f"  Fetching forge data from Coflnet... {len(forge_data)} recipes")

    results = calc_forge_profits(
        forge_data,
        hotm_filter=hotm_filter,
        quick_forge_level=quick_forge_level,
        use_buy_order=args.buy_order,
    )

    if args.item:
        target = args.item.upper()
        match = [r for r in results if r["item_id"] == target]
        if not match:
            # Try substring match on name
            match = [r for r in results if target.lower() in r["item_name"].lower()]
        if not match:
            print(f"\n  No profitable forge found for '{args.item}'", file=sys.stderr)
            # Show all forge items with that substring
            all_results = calc_forge_profits(forge_data, quick_forge_level=quick_forge_level)
            matches = [r for r in all_results if target.lower() in r["item_name"].lower()
                       or target == r["item_id"]]
            if matches:
                print(f"  Found {len(matches)} forge recipes matching '{args.item}' (including unprofitable):")
                for r in matches:
                    print(f"    {r['item_id']}: {r['item_name']} (profit: {_fmt(r['profit'])})")
            sys.exit(1)
        for m in match:
            if args.json:
                print(json.dumps(m, indent=2))
            else:
                print_detail(m)
        return

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_summary(results, top_n=args.top or 30, quick_forge_level=quick_forge_level)


if __name__ == "__main__":
    main()
