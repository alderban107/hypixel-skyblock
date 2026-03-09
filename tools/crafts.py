#!/usr/bin/env python3
"""Craft flip scanner for Hypixel SkyBlock.

Finds items where bazaar-bought ingredients can be crafted into items
that sell on the Auction House for more than the material cost. Uses
Moulberry's bulk APIs for pricing data (3-day averaged lowest BIN,
current lowest BIN, and actual sales volume).

Usage:
    python3 crafts.py              # Full scan — all profitable crafts
    python3 crafts.py --forge      # Scan forge recipes (time-gated crafts)
    python3 crafts.py --profile    # Filter by player's unlocked recipes
    python3 crafts.py --cached     # Use cached prices only (skip API calls)
    python3 crafts.py --fresh      # Ignore cache, fetch all prices fresh
    python3 crafts.py --undercut 8 # Set undercut % below LBIN (default: 5%)
    python3 crafts.py --item MINING_2_TRAVEL_SCROLL         # Single item breakdown
    python3 crafts.py --item MINING_2_TRAVEL_SCROLL --check # + requirement check
"""

import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from items import (display_name, get_all_requirements, check_requirements,
                   search_items, _load_profile_member)
from pricing import PriceCache, _fmt

DATA_DIR = Path(__file__).parent.parent / "data"
NEU_ITEMS_DIR = DATA_DIR / "neu-repo" / "items"
CRAFT_CACHE_PATH = DATA_DIR / "craft_cache.json"

MOULBERRY_LBIN_URL = "https://moulberry.codes/lowestbin.json"
MOULBERRY_AVG_LBIN_URL = "https://moulberry.codes/auction_averages_lbin/3day.json"
MOULBERRY_AVG_URL = "https://moulberry.codes/auction_averages/3day.json"
MOULBERRY_TTL = 300          # 5 minutes
MOULBERRY_EVICT = 3600       # 1 hour

MIN_PROFIT = 10_000
MIN_VOLUME = 1
LBIN_SANITY_MULT = 5  # Skip AH price if LBIN > this × avg_lbin (manipulation guard)

# Items that are disabled in-game but still have NEU recipes / AH listings
DISABLED_ITEMS = {
    "SOULS_REBOUND",
}


# ─── Recipe Parsing ───────────────────────────────────────────────────

def _parse_recipe_grid(recipe_data):
    """Parse a NEU recipe grid (A1-C3) into {item_id: qty} dict."""
    ingredients = {}
    for row in "ABC":
        for col in "123":
            slot = recipe_data.get(f"{row}{col}", "")
            if not slot:
                continue
            parts = slot.split(":")
            if len(parts) == 2:
                ing_id, qty = parts[0], int(parts[1])
            elif len(parts) == 1:
                ing_id, qty = parts[0], 1
            else:
                continue
            if not ing_id:
                continue
            ingredients[ing_id] = ingredients.get(ing_id, 0) + qty
    return ingredients


def parse_recipes():
    """Scan NEU repo for all craftable items. Returns list of recipe dicts."""
    recipes = []
    if not NEU_ITEMS_DIR.exists():
        print("  NEU repo not found at", NEU_ITEMS_DIR, file=sys.stderr)
        return recipes

    for path in NEU_ITEMS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        item_id = data.get("internalname", path.stem)

        # Get recipe — handle both "recipe" (dict) and "recipes" (list) formats
        recipe_data = None
        if "recipes" in data and isinstance(data["recipes"], list):
            for r in data["recipes"]:
                if r.get("type", "crafting") == "crafting":
                    recipe_data = r
                    break
        elif "recipe" in data and isinstance(data["recipe"], dict):
            recipe_data = data["recipe"]

        if not recipe_data:
            continue

        ingredients = _parse_recipe_grid(recipe_data)

        if not ingredients:
            continue

        output_count = recipe_data.get("count", 1)
        if isinstance(output_count, str):
            try:
                output_count = int(output_count)
            except ValueError:
                output_count = 1

        # Use overrideOutputId if present
        output_id = recipe_data.get("overrideOutputId", item_id)

        # Get unlock requirement from items.py (merges NEU + API sources)
        all_reqs = get_all_requirements(output_id)
        requirement = all_reqs[0] if all_reqs else None

        recipes.append({
            "item_id": output_id,
            "ingredients": ingredients,
            "output_count": max(output_count, 1),
            "requirement": requirement,
        })

    return recipes


def parse_forge_recipes():
    """Scan NEU repo for all forge recipes. Returns list of recipe dicts."""
    recipes = []
    if not NEU_ITEMS_DIR.exists():
        print("  NEU repo not found at", NEU_ITEMS_DIR, file=sys.stderr)
        return recipes

    for path in NEU_ITEMS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        item_id = data.get("internalname", path.stem)

        if "recipes" not in data or not isinstance(data["recipes"], list):
            continue

        for r in data["recipes"]:
            if r.get("type") != "forge":
                continue

            # Parse inputs — format is "ITEM_ID:QTY" or just "ITEM_ID"
            ingredients = {}
            for inp in r.get("inputs", []):
                parts = str(inp).split(":")
                if len(parts) == 2:
                    ing_id = parts[0]
                    try:
                        qty = int(float(parts[1]))
                    except ValueError:
                        qty = 1
                elif len(parts) == 1:
                    ing_id, qty = parts[0], 1
                else:
                    continue
                if ing_id:
                    ingredients[ing_id] = ingredients.get(ing_id, 0) + qty

            if not ingredients:
                continue

            output_count = r.get("count", 1)
            if isinstance(output_count, str):
                try:
                    output_count = int(output_count)
                except ValueError:
                    output_count = 1

            output_id = r.get("overrideOutputId", item_id)
            duration = r.get("duration", 0)  # seconds

            all_reqs = get_all_requirements(output_id)
            requirement = all_reqs[0] if all_reqs else None

            recipes.append({
                "item_id": output_id,
                "ingredients": ingredients,
                "output_count": max(output_count, 1),
                "duration": duration,
                "requirement": requirement,
            })
            break  # only first forge recipe per item

    return recipes


def _format_duration(seconds):
    """Format forge duration in human-readable form."""
    if seconds <= 0:
        return "instant"
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    if days > 0:
        if hours > 0:
            return f"{days}d {hours}h"
        return f"{days}d"
    if hours > 0:
        if minutes > 0:
            return f"{hours}h {minutes}m"
        return f"{hours}h"
    return f"{minutes}m"


def calculate_forge_cost(recipe, price_cache):
    """Calculate total ingredient cost for a forge recipe.

    Accepts mixed sources: Bazaar buy price preferred, falls back to AH LBIN.
    Returns (total_cost, sources) where sources maps ingredient IDs to their
    price source ("bazaar" or "auction").
    """
    total = 0
    sources = {}
    for ing_id, qty in recipe["ingredients"].items():
        p = price_cache.get_price(ing_id)
        if p["source"] == "bazaar" and p.get("buy"):
            total += p["buy"] * qty
            sources[ing_id] = "bazaar"
        elif p["source"] == "auction" and p.get("lowest_bin"):
            total += p["lowest_bin"] * qty
            sources[ing_id] = "auction"
        else:
            return None, None  # can't price this ingredient
    return total / recipe["output_count"], sources


def scan_forge_flips(recipes, price_cache, craft_cache, use_cached_only=False,
                     force_refresh=False, undercut_pct=5):
    """Scan forge recipes for profitable flips.

    Unlike craft flips, forge outputs can sell on Bazaar OR AH.
    Picks whichever sell channel gives better profit.
    """
    # Load bulk AH data for items that sell on AH
    if use_cached_only:
        mb = craft_cache.get("moulberry", {})
        lowestbin = mb.get("lowestbin", {})
        avg_lbin = mb.get("avg_lbin", {})
        auction_averages = mb.get("auction_averages", {})
    else:
        lowestbin, avg_lbin, auction_averages = fetch_moulberry_data(
            cache=craft_cache, force_refresh=force_refresh)

    flips = []
    for recipe in recipes:
        item_id = recipe["item_id"]

        if item_id in DISABLED_ITEMS:
            continue

        cost, sources = calculate_forge_cost(recipe, price_cache)
        if cost is None:
            continue

        # Check both sell channels for output
        output_price = price_cache.get_price(item_id)

        sell_price = None
        sell_channel = None
        sales_per_day = None

        # Check Bazaar instant-sell
        if output_price["source"] == "bazaar" and output_price.get("sell"):
            bz_sell = output_price["sell"]
            bz_profit = bz_sell - cost
            sell_price = bz_sell
            sell_channel = "bazaar"
            # Bazaar volume is essentially unlimited for instant-sell
            sales_per_day = None  # continuous

        # Check AH
        ah_lbin = lowestbin.get(item_id, 0)
        ah_avg = avg_lbin.get(item_id, 0)
        ah_data = auction_averages.get(item_id, {})
        ah_sales = ah_data.get("clean_sales") or ah_data.get("sales")
        ah_sales_day = ah_sales / 3.0 if ah_sales else None

        if ah_lbin and ah_lbin > 0:
            # Sanity check: skip if LBIN looks manipulated (>5× avg)
            if ah_avg and ah_avg > 0 and ah_lbin > LBIN_SANITY_MULT * ah_avg:
                pass  # LBIN unreliable, skip AH channel
            else:
                sell_mult = (1 - undercut_pct / 100) * 0.99
                ah_profit = ah_lbin * sell_mult - cost

                # Use AH if it's more profitable (or if no Bazaar option)
                if sell_channel is None or ah_profit > (sell_price - cost if sell_price else 0):
                    sell_price = ah_lbin
                    sell_channel = "auction"
                    sales_per_day = ah_sales_day

        if sell_price is None:
            continue

        # Calculate final profit
        if sell_channel == "bazaar":
            profit = sell_price - cost
        else:
            sell_mult = (1 - undercut_pct / 100) * 0.99
            profit = sell_price * sell_mult - cost

        if profit < MIN_PROFIT:
            continue

        # Require sales volume for AH items
        if sell_channel == "auction" and (sales_per_day is None or sales_per_day < MIN_VOLUME):
            continue

        flips.append({
            "item_id": item_id,
            "cost": cost,
            "sell_price": sell_price,
            "avg_lbin": ah_avg if sell_channel == "auction" else None,
            "profit": profit,
            "sales_per_day": sales_per_day,
            "sell_channel": sell_channel,
            "duration": recipe["duration"],
            "requirement": recipe.get("requirement"),
            "input_sources": sources,
        })

    flips.sort(key=lambda x: x["profit"], reverse=True)
    return flips


def print_forge_flips(flips, title="FORGE FLIPS"):
    """Print a table of forge flips."""
    print(f"\n{title} (min {_fmt(MIN_PROFIT)} profit, min {MIN_VOLUME} sale/day)")
    print("=" * 110)
    print(f"  {'Item':<28s} {'Cost':>10s}  {'Sell':>10s}  {'Profit':>10s} {'Sales':>6s}  {'Time':>8s}  {'Channel':>7s}  Requirement")
    print(f"  {'-'*28} {'-'*10}  {'-'*10}  {'-'*10} {'-'*6}  {'-'*8}  {'-'*7}  {'-'*20}")

    for flip in flips:
        name = display_name(flip["item_id"])
        if len(name) > 28:
            name = name[:25] + "..."
        req_text = flip["requirement"]["text"] if flip.get("requirement") else ""
        spd = flip.get("sales_per_day")
        if spd is None:
            spd_str = "∞"
        elif spd >= 10:
            spd_str = f"{spd:.0f}/d"
        else:
            spd_str = f"{spd:.1f}/d"
        channel = "BZ" if flip["sell_channel"] == "bazaar" else "AH"
        dur = _format_duration(flip["duration"])
        print(f"  {name:<28s} {_fmt(flip['cost']):>10s}  {_fmt(flip['sell_price']):>10s}  "
              f"{_fmt(flip['profit']):>10s} {spd_str:>6s}  {dur:>8s}  {channel:>7s}  {req_text}")

    if not flips:
        print("  No profitable forge flips found.")
    print()


def print_profile_forge_flips(flips, member):
    """Print forge flips filtered by player unlocks."""
    unlocked = []
    almost = []

    for flip in flips:
        item_id = flip["item_id"]
        checked = check_requirements(item_id, member)

        if not checked:
            unlocked.append(flip)
            continue

        all_met = all(r.get("met", False) for r in checked)
        if all_met:
            unlocked.append(flip)
        else:
            for r in checked:
                if not r.get("met", False) and r.get("needed") and r["needed"] > 0:
                    progress = r.get("progress", 0) or 0
                    pct = progress / r["needed"] if r["needed"] > 0 else 0
                    almost.append({
                        **flip,
                        "progress": progress,
                        "needed": r["needed"],
                        "pct": pct,
                        "req_text": r.get("text", ""),
                        "req_type": r.get("type", ""),
                    })
                    break

    # Print unlocked
    print(f"\nUNLOCKED FORGE FLIPS")
    print("=" * 100)
    if unlocked:
        print(f"  {'Item':<28s} {'Cost':>10s}  {'Sell':>10s}  {'Profit':>10s} {'Sales':>6s}  {'Time':>8s}  {'Via':>3s}")
        print(f"  {'-'*28} {'-'*10}  {'-'*10}  {'-'*10} {'-'*6}  {'-'*8}  {'-'*3}")
        for flip in unlocked:
            name = display_name(flip["item_id"])
            if len(name) > 28:
                name = name[:25] + "..."
            spd = flip.get("sales_per_day")
            if spd is None:
                spd_str = "∞"
            elif spd >= 10:
                spd_str = f"{spd:.0f}/d"
            else:
                spd_str = f"{spd:.1f}/d"
            channel = "BZ" if flip["sell_channel"] == "bazaar" else "AH"
            dur = _format_duration(flip["duration"])
            print(f"  {name:<28s} {_fmt(flip['cost']):>10s}  {_fmt(flip['sell_price']):>10s}  "
                  f"{_fmt(flip['profit']):>10s} {spd_str:>6s}  {dur:>8s}  {channel:>3s}")
    else:
        print("  No unlocked profitable forge flips found.")
    print()

    # Print almost unlocked
    almost.sort(key=lambda x: x["pct"], reverse=True)
    almost = almost[:10]
    if almost:
        print(f"ALMOST UNLOCKED FORGE FLIPS (sorted by proximity)")
        print("=" * 88)
        print(f"  {'Item':<24s} {'Profit':>8s}  {'Time':>8s}  {'Requirement':<22s} Progress")
        print(f"  {'-'*24} {'-'*8}  {'-'*8}  {'-'*22} {'-'*20}")
        for flip in almost:
            name = display_name(flip["item_id"])
            if len(name) > 24:
                name = name[:21] + "..."
            req_text = flip.get("req_text", "")
            if len(req_text) > 22:
                req_text = req_text[:19] + "..."
            dur = _format_duration(flip["duration"])
            prog_str = f"{_fmt(flip['progress'])} / {_fmt(flip['needed'])}"
            if flip.get("req_type") == "SLAYER":
                prog_str += " XP"
            pct_str = f"({flip['pct']*100:.0f}%)"
            print(f"  {name:<24s} {_fmt(flip['profit']):>8s}  {dur:>8s}  {req_text:<22s} {prog_str} {pct_str}")
        print()


# ─── Moulberry Bulk Price Data ───────────────────────────────────────

def load_craft_cache():
    """Load the craft flip cache from disk."""
    if not CRAFT_CACHE_PATH.exists():
        return {"moulberry": {}, "collections": None, "collections_ts": 0}
    try:
        data = json.loads(CRAFT_CACHE_PATH.read_text())
        # Evict stale moulberry data
        now = time.time()
        mb = data.get("moulberry", {})
        if mb and now - mb.get("ts", 0) > MOULBERRY_EVICT:
            data["moulberry"] = {}
        # Drop old-format sold_prices if present
        data.pop("sold_prices", None)
        if "moulberry" not in data:
            data["moulberry"] = {}
        return data
    except (json.JSONDecodeError, OSError):
        return {"moulberry": {}, "collections": None, "collections_ts": 0}


def save_craft_cache(cache):
    """Save the craft flip cache to disk."""
    try:
        CRAFT_CACHE_PATH.write_text(json.dumps(cache, indent=2))
    except OSError as e:
        print(f"  Warning: couldn't save cache: {e}", file=sys.stderr)


def fetch_moulberry_data(cache, force_refresh=False):
    """Fetch all three Moulberry bulk datasets.

    Returns (lowestbin, avg_lbin, auction_averages) dicts.
    Uses cache if fresh. Falls back to cached data per-endpoint on failure.
    """
    now = time.time()
    mb = cache.get("moulberry", {})

    if not force_refresh and mb and now - mb.get("ts", 0) < MOULBERRY_TTL:
        return mb.get("lowestbin", {}), mb.get("avg_lbin", {}), mb.get("auction_averages", {})

    urls = {
        "lowestbin": MOULBERRY_LBIN_URL,
        "avg_lbin": MOULBERRY_AVG_LBIN_URL,
        "auction_averages": MOULBERRY_AVG_URL,
    }

    results = {}
    for key, url in urls.items():
        try:
            req = Request(url, headers={"User-Agent": "SkyblockTools/1.0"})
            with urlopen(req, timeout=15) as resp:
                results[key] = json.loads(resp.read())
            print(f"  Fetched {key}: {len(results[key])} items", file=sys.stderr)
        except (HTTPError, URLError, OSError) as e:
            print(f"  Warning: Moulberry {key} fetch failed: {e}", file=sys.stderr)
            results[key] = mb.get(key, {})

    cache["moulberry"] = {
        "lowestbin": results["lowestbin"],
        "avg_lbin": results["avg_lbin"],
        "auction_averages": results["auction_averages"],
        "ts": now,
    }

    return results["lowestbin"], results["avg_lbin"], results["auction_averages"]


# ─── Craft Flip Analysis ──────────────────────────────────────────────

def filter_craft_flips(recipes, price_cache):
    """Filter recipes to those where all ingredients are on bazaar.
    Output can sell on either AH or Bazaar (best channel chosen at scan time)."""
    bazaar_items = set()
    price_cache._fetch_bazaar()
    for pid, bz in price_cache._bazaar.items():
        if bz.get("buy", 0) > 0 or bz.get("sell", 0) > 0:
            bazaar_items.add(pid)

    def _on_bazaar(item_id):
        """Check if an item is on bazaar, resolving ID mismatches."""
        if item_id in bazaar_items:
            return True
        resolved = price_cache._resolve_bazaar_id(item_id)
        return resolved != item_id and resolved in bazaar_items

    valid = []
    for recipe in recipes:
        # All ingredients must be on bazaar
        all_bz = True
        for ing_id in recipe["ingredients"]:
            if not _on_bazaar(ing_id):
                all_bz = False
                break
        if not all_bz:
            continue

        valid.append(recipe)

    return valid


def calculate_craft_cost(recipe, price_cache):
    """Calculate total ingredient cost using bazaar buyPrice."""
    total = 0
    for ing_id, qty in recipe["ingredients"].items():
        p = price_cache.get_price(ing_id)
        if p["source"] != "bazaar" or not p.get("buy"):
            return None
        total += p["buy"] * qty
    return total / recipe["output_count"]


def scan_craft_flips(recipes, price_cache, craft_cache, use_cached_only=False,
                     force_refresh=False, undercut_pct=5):
    """Scan all recipes and return profitable craft flips.

    All price data is loaded in bulk from Moulberry APIs up front,
    then a single pass iterates recipes and looks up prices in memory.
    Output can sell on AH or Bazaar — whichever gives better profit.

    undercut_pct: how far below LBIN to price for AH items (default 5%).
    AH profit formula: LBIN * (1 - undercut/100) * 0.99 - cost
    Bazaar profit formula: instant_sell - cost
    """
    # Load bulk price data
    if use_cached_only:
        mb = craft_cache.get("moulberry", {})
        lowestbin = mb.get("lowestbin", {})
        avg_lbin = mb.get("avg_lbin", {})
        auction_averages = mb.get("auction_averages", {})
        if not avg_lbin:
            print("  No cached data. Run 'python3 crafts.py' first.", file=sys.stderr)
            return []
    else:
        lowestbin, avg_lbin, auction_averages = fetch_moulberry_data(
            cache=craft_cache, force_refresh=force_refresh)
        if not avg_lbin:
            print("  Error: Could not fetch Moulberry data.", file=sys.stderr)
            return []

    sell_mult = (1 - undercut_pct / 100) * 0.99

    flips = []
    for recipe in recipes:
        item_id = recipe["item_id"]

        if item_id in DISABLED_ITEMS:
            continue

        cost = calculate_craft_cost(recipe, price_cache)
        if cost is None:
            continue

        # Check both sell channels for output
        output_price = price_cache.get_price(item_id)

        best_profit = None
        best_channel = None
        best_sell = None
        best_avg = None
        best_lbin = None
        best_sales = None

        # Check Bazaar instant-sell
        if output_price["source"] == "bazaar" and output_price.get("sell"):
            bz_profit = output_price["sell"] - cost
            if bz_profit >= MIN_PROFIT:
                best_profit = bz_profit
                best_channel = "bazaar"
                best_sell = output_price["sell"]
                best_sales = None  # continuous

        # Check AH
        item_avg = avg_lbin.get(item_id)
        current_lbin = lowestbin.get(item_id, 0)
        avg_data = auction_averages.get(item_id, {})
        ah_sales = avg_data.get("sales", 0) / 3.0 if avg_data else 0

        if item_avg and item_avg > 0 and current_lbin and current_lbin > 0 and ah_sales >= MIN_VOLUME:
            # Sanity check: skip if LBIN looks manipulated (>5× avg)
            if current_lbin > LBIN_SANITY_MULT * item_avg:
                pass  # LBIN unreliable, skip AH channel
            else:
                ah_profit = current_lbin * sell_mult - cost
                if ah_profit >= MIN_PROFIT and (best_profit is None or ah_profit > best_profit):
                    best_profit = ah_profit
                    best_channel = "auction"
                    best_sell = current_lbin
                    best_avg = item_avg
                    best_lbin = current_lbin
                    best_sales = ah_sales

        if best_profit is None:
            continue

        flips.append({
            "item_id": item_id,
            "cost": cost,
            "avg_lbin": best_avg,
            "lbin": best_lbin,
            "sell_price": best_sell,
            "profit": best_profit,
            "sales_per_day": best_sales,
            "sell_channel": best_channel,
            "requirement": recipe["requirement"],
        })

    flips.sort(key=lambda x: x["profit"], reverse=True)
    return flips


# ─── Profile Filtering ────────────────────────────────────────────────



# ─── Display ──────────────────────────────────────────────────────────

def print_flips(flips, title="CRAFT FLIPS"):
    """Print a table of craft flips."""
    print(f"\n{title} (min {_fmt(MIN_PROFIT)} profit, min {MIN_VOLUME} sale/day)")
    print("=" * 106)
    print(f"  {'Item':<30s} {'Cost':>10s}  {'Sell':>10s}  {'Profit':>10s} {'Sales':>6s}  {'Via':>3s}  Requirement")
    print(f"  {'-'*30} {'-'*10}  {'-'*10}  {'-'*10} {'-'*6}  {'-'*3}  {'-'*20}")

    for flip in flips:
        name = display_name(flip["item_id"])
        if len(name) > 30:
            name = name[:27] + "..."
        req_text = flip["requirement"]["text"] if flip["requirement"] else ""
        spd = flip.get("sales_per_day")
        if spd is None:
            spd_str = "∞"
        elif spd >= 10:
            spd_str = f"{spd:.0f}/d"
        else:
            spd_str = f"{spd:.1f}/d"
        sell_str = _fmt(flip.get("sell_price") or flip.get("lbin") or 0)
        channel = "BZ" if flip.get("sell_channel") == "bazaar" else "AH"
        print(f"  {name:<30s} {_fmt(flip['cost']):>10s}  {sell_str:>10s}  "
              f"{_fmt(flip['profit']):>10s} {spd_str:>6s}  {channel:>3s}  {req_text}")

    if not flips:
        print("  No profitable crafts found.")
    print()


def print_profile_flips(flips, member):
    """Print flips filtered by player unlocks.

    Uses the requirement aggregator from items.py to check ALL requirement
    types (collection, slayer, skill, dungeon_tier, dungeon_skill, HotM,
    museum). Previously only checked collection and slayer, silently hiding
    items gated behind skill levels or dungeon completions.
    """
    unlocked = []
    almost = []

    for flip in flips:
        item_id = flip["item_id"]
        checked = check_requirements(item_id, member)

        if not checked:
            # No requirements — unlocked by default
            unlocked.append(flip)
            continue

        all_met = all(r.get("met", False) for r in checked)
        if all_met:
            unlocked.append(flip)
        else:
            # Find the closest unmet requirement for "almost" display
            for r in checked:
                if not r.get("met", False) and r.get("needed") and r["needed"] > 0:
                    progress = r.get("progress", 0) or 0
                    pct = progress / r["needed"] if r["needed"] > 0 else 0
                    almost.append({
                        **flip,
                        "progress": progress,
                        "needed": r["needed"],
                        "pct": pct,
                        "req_text": r.get("text", ""),
                        "req_type": r.get("type", ""),
                    })
                    break  # only show the blocking requirement

    # Print unlocked
    print(f"\nUNLOCKED CRAFT FLIPS")
    print("=" * 90)
    if unlocked:
        print(f"  {'Item':<30s} {'Cost':>10s}  {'Sell':>10s}  {'Profit':>10s} {'Sales':>6s}  {'Via':>3s}")
        print(f"  {'-'*30} {'-'*10}  {'-'*10}  {'-'*10} {'-'*6}  {'-'*3}")
        for flip in unlocked:
            name = display_name(flip["item_id"])
            if len(name) > 30:
                name = name[:27] + "..."
            spd = flip.get("sales_per_day")
            if spd is None:
                spd_str = "∞"
            elif spd >= 10:
                spd_str = f"{spd:.0f}/d"
            else:
                spd_str = f"{spd:.1f}/d"
            sell_str = _fmt(flip.get("sell_price") or flip.get("lbin") or 0)
            channel = "BZ" if flip.get("sell_channel") == "bazaar" else "AH"
            print(f"  {name:<30s} {_fmt(flip['cost']):>10s}  {sell_str:>10s}  "
                  f"{_fmt(flip['profit']):>10s} {spd_str:>6s}  {channel:>3s}")
    else:
        print("  No unlocked profitable crafts found.")
    print()

    # Print almost unlocked (sorted by proximity)
    almost.sort(key=lambda x: x["pct"], reverse=True)
    almost = almost[:10]  # top 10 closest
    if almost:
        print(f"ALMOST UNLOCKED (sorted by proximity to requirement)")
        print("=" * 78)
        print(f"  {'Item':<26s} {'Profit':>8s}  {'Requirement':<22s} Progress")
        print(f"  {'-'*26} {'-'*8}  {'-'*22} {'-'*20}")
        for flip in almost:
            name = display_name(flip["item_id"])
            if len(name) > 26:
                name = name[:23] + "..."
            req_text = flip.get("req_text", "")
            if len(req_text) > 22:
                req_text = req_text[:19] + "..."
            prog_str = f"{_fmt(flip['progress'])} / {_fmt(flip['needed'])}"
            if flip.get("req_type") == "SLAYER":
                prog_str += " XP"
            pct_str = f"({flip['pct']*100:.0f}%)"
            print(f"  {name:<26s} {_fmt(flip['profit']):>8s}  {req_text:<22s} {prog_str} {pct_str}")
        print()


# ─── Single Item Breakdown ────────────────────────────────────────────

def find_recipe(item_id, recipes=None):
    """Find a recipe for an item. Searches parsed recipes, then NEU repo directly."""
    if recipes:
        for r in recipes:
            if r["item_id"] == item_id:
                return r

    # Direct NEU lookup
    neu_path = NEU_ITEMS_DIR / f"{item_id}.json"
    if not neu_path.exists():
        return None

    try:
        data = json.loads(neu_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    # Find crafting recipe
    recipe_data = None
    if "recipes" in data and isinstance(data["recipes"], list):
        for r in data["recipes"]:
            if r.get("type", "crafting") == "crafting":
                recipe_data = r
                break
    elif "recipe" in data and isinstance(data["recipe"], dict):
        recipe_data = data["recipe"]

    if not recipe_data:
        return None

    ingredients = _parse_recipe_grid(recipe_data)

    if not ingredients:
        return None

    output_count = recipe_data.get("count", 1)
    if isinstance(output_count, str):
        try:
            output_count = int(output_count)
        except ValueError:
            output_count = 1

    output_id = recipe_data.get("overrideOutputId", item_id)
    all_reqs = get_all_requirements(output_id)
    requirement = all_reqs[0] if all_reqs else None

    return {
        "item_id": output_id,
        "ingredients": ingredients,
        "output_count": max(output_count, 1),
        "requirement": requirement,
    }


def show_item_breakdown(item_id, price_cache, do_check=False, undercut_pct=5):
    """Show a full recipe breakdown for a single item with costs and profit."""
    item_id = item_id.upper()
    name = display_name(item_id)

    # Find the recipe
    recipe = find_recipe(item_id)
    if not recipe:
        # Fuzzy search: find items whose ID or display name contains the query
        matches = search_items(item_id)
        craftable = []
        for m in matches:
            mid = m.get("id", "")
            if mid and mid != item_id:
                r = find_recipe(mid)
                if r:
                    craftable.append((mid, display_name(mid)))
        if craftable:
            print(f"\n  No exact recipe for '{item_id}'. Did you mean:")
            for mid, mname in craftable[:8]:
                print(f"    {mname:40s} --item {mid}")
            return
        print(f"\n  No crafting recipe found for {name} ({item_id})")
        return

    print(f"\n  Recipe: {name}")

    # Show requirements (using the new aggregator)
    reqs = get_all_requirements(item_id)
    if reqs:
        for r in reqs:
            source_tag = f" [{r['source']}]" if r.get("source") else ""
            print(f"  Requirement: {r['text']}{source_tag}")

    # Check requirements against profile if requested
    if do_check:
        checked = check_requirements(item_id)
        if checked:
            for r in checked:
                status = "\u2713" if r["met"] else "\u2717"
                if r["type"] == "COLLECTION":
                    prog_str = f"{_fmt(r['progress'])} / {_fmt(r['needed'])}"
                elif r["type"] == "SLAYER":
                    prog_str = f"{_fmt(r['progress'])} / {_fmt(r['needed'])} XP"
                else:
                    prog_str = f"{r['progress']} / {r['needed']}"
                print(f"    {status} {r['text']} -- {prog_str}")
        elif reqs:
            print("    (no profile data -- run profile.py first)")

    # Ingredient breakdown
    print()
    print(f"  {'Ingredient':<30s} {'Qty':>6s} {'Price':>10s} {'Total':>12s}")
    print(f"  {'─' * 30} {'─' * 6} {'─' * 10} {'─' * 12}")

    total_cost = 0
    for ing_id, qty in sorted(recipe["ingredients"].items()):
        p = price_cache.get_price(ing_id)
        ing_name = display_name(ing_id)
        if len(ing_name) > 30:
            ing_name = ing_name[:27] + "..."

        if p["source"] == "bazaar" and p.get("buy"):
            unit_price = p["buy"]
            line_total = unit_price * qty
            total_cost += line_total
            print(f"  {ing_name:<30s} {qty:>6,d} {_fmt(unit_price):>10s} {_fmt(line_total):>12s}")
        elif p["source"] == "auction" and p.get("lowest_bin"):
            unit_price = p["lowest_bin"]
            line_total = unit_price * qty
            total_cost += line_total
            print(f"  {ing_name:<30s} {qty:>6,d} {_fmt(unit_price):>10s} {_fmt(line_total):>12s}  (AH)")
        else:
            print(f"  {ing_name:<30s} {qty:>6,d} {'?':>10s} {'?':>12s}")

    # Output count adjustment
    if recipe["output_count"] > 1:
        total_cost_per = total_cost / recipe["output_count"]
        print(f"  {'':>30s} {'':>6s} {'':>10s} {'─' * 12}")
        print(f"  {'Total craft cost':>30s} {'':>6s} {'':>10s} {_fmt(total_cost):>12s}")
        print(f"  {'Per item (' + str(recipe['output_count']) + 'x output)':>30s} {'':>6s} {'':>10s} {_fmt(total_cost_per):>12s}")
    else:
        total_cost_per = total_cost
        print(f"  {'':>30s} {'':>6s} {'':>10s} {'─' * 12}")
        print(f"  {'Craft Cost':>30s} {'':>6s} {'':>10s} {_fmt(total_cost):>12s}")

    # AH sell price
    sell_price = price_cache.get_price(item_id)
    print()
    if sell_price["source"] == "auction":
        lbin = sell_price.get("lowest_bin")
        avg = sell_price.get("avg_bin")
        sales = sell_price.get("sales_day")
        parts = []
        if lbin:
            parts.append(f"LBIN {_fmt(lbin)}")
        if avg:
            parts.append(f"avg {_fmt(avg)}")
        if sales:
            parts.append(f"({sales:.1f}/day)")
        print(f"  AH Sell:  {' '.join(parts)}")

        # Profit calc: price × (1 - undercut%) × 0.99 (AH tax) - cost
        sell_mult = (1 - undercut_pct / 100) * 0.99
        pct_label = f"-{undercut_pct:g}%"
        if avg and total_cost_per > 0:
            profit = avg * sell_mult - total_cost_per
            print(f"  Profit:   {_fmt(profit)} (avg×{sell_mult:.3f} - cost, {pct_label} undercut)")
        elif lbin and total_cost_per > 0:
            profit = lbin * sell_mult - total_cost_per
            print(f"  Profit:   {_fmt(profit)} (LBIN×{sell_mult:.3f} - cost, {pct_label} undercut)")
    elif sell_price["source"] == "bazaar":
        print(f"  Bazaar Sell:  {_fmt(sell_price['sell'])} instant-sell / {_fmt(sell_price['buy'])} instant-buy")
        if sell_price.get("sell") and total_cost_per > 0:
            profit = sell_price["sell"] - total_cost_per
            print(f"  Profit:   {_fmt(profit)} (sell - cost)")
    else:
        print(f"  Sell:  No price data")

    print()


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SkyBlock craft flip scanner")
    parser.add_argument("--forge", action="store_true",
                        help="Scan forge recipes instead of crafting recipes")
    parser.add_argument("--profile", action="store_true",
                        help="Filter by player's unlocked recipes (reads last_profile.json)")
    parser.add_argument("--cached", action="store_true",
                        help="Use cached prices only (skip API calls)")
    parser.add_argument("--fresh", action="store_true",
                        help="Ignore cache, fetch all prices fresh")
    parser.add_argument("--item", type=str, metavar="ITEM_ID",
                        help="Show recipe breakdown for a single item")
    parser.add_argument("--check", action="store_true",
                        help="Check requirements against player profile (with --item)")
    parser.add_argument("--undercut", type=float, default=5, metavar="PCT",
                        help="Undercut LBIN by this %% when calculating profit (default: 5)")
    args = parser.parse_args()

    # Single item mode
    if args.item:
        price_cache = PriceCache()
        show_item_breakdown(args.item, price_cache, do_check=args.check,
                            undercut_pct=args.undercut)
        price_cache.flush()
        return

    # Load cache
    craft_cache = load_craft_cache()

    if args.fresh:
        craft_cache["moulberry"] = {}
        print("  Cleared price cache (--fresh)", file=sys.stderr)

    price_cache = PriceCache()

    if args.forge:
        # ── Forge flip mode ──────────────────────────────────────────
        print("  Parsing forge recipes from NEU repo...", file=sys.stderr)
        forge_recipes = parse_forge_recipes()
        print(f"  Found {len(forge_recipes)} forge recipes", file=sys.stderr)

        if not forge_recipes:
            print("\n  No forge recipes found.")
            price_cache.flush()
            return

        flips = scan_forge_flips(forge_recipes, price_cache, craft_cache,
                                 use_cached_only=args.cached, force_refresh=args.fresh,
                                 undercut_pct=args.undercut)

        save_craft_cache(craft_cache)
        price_cache.flush()

        if args.profile:
            member = _load_profile_member()
            if not member:
                print("  Error: last_profile.json not found or invalid.", file=sys.stderr)
                print("  Run 'python3 profile.py' first to fetch profile data.", file=sys.stderr)
                print_forge_flips(flips)
            else:
                print_profile_forge_flips(flips, member)
        else:
            print_forge_flips(flips)

    else:
        # ── Craft flip mode (default) ───────────────────────────────
        print("  Parsing recipes from NEU repo...", file=sys.stderr)
        all_recipes = parse_recipes()
        print(f"  Found {len(all_recipes)} crafting recipes", file=sys.stderr)

        valid = filter_craft_flips(all_recipes, price_cache)
        print(f"  {len(valid)} recipes with all-bazaar ingredients", file=sys.stderr)

        if not valid:
            print("\n  No valid craft flip candidates found.")
            price_cache.flush()
            return

        flips = scan_craft_flips(valid, price_cache, craft_cache,
                                 use_cached_only=args.cached, force_refresh=args.fresh,
                                 undercut_pct=args.undercut)

        save_craft_cache(craft_cache)
        price_cache.flush()

        if args.profile:
            member = _load_profile_member()
            if not member:
                print("  Error: last_profile.json not found or invalid.", file=sys.stderr)
                print("  Run 'python3 profile.py' first to fetch profile data.", file=sys.stderr)
                print_flips(flips)
            else:
                print_profile_flips(flips, member)
        else:
            print_flips(flips)

    mb = craft_cache.get("moulberry", {})
    n_lbin = len(mb.get("lowestbin", {}))
    n_avg = len(mb.get("avg_lbin", {}))
    n_sales = len(mb.get("auction_averages", {}))
    print(f"  Data: {n_lbin} lowest BINs, {n_avg} avg BINs, {n_sales} sale records", file=sys.stderr)


if __name__ == "__main__":
    main()
