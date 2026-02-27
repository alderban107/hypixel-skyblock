#!/usr/bin/env python3
"""Craft flip scanner for Hypixel SkyBlock.

Finds items where bazaar-bought ingredients can be crafted into items
that sell on the Auction House for more than the material cost. Uses
Moulberry's bulk APIs for pricing data (3-day averaged lowest BIN,
current lowest BIN, and actual sales volume).

Usage:
    python3 crafts.py              # Full scan — all profitable crafts
    python3 crafts.py --profile    # Filter by player's unlocked recipes
    python3 crafts.py --cached     # Use cached prices only (skip API calls)
    python3 crafts.py --fresh      # Ignore cache, fetch all prices fresh
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pricing import PriceCache, _fmt, display_name

DATA_DIR = Path(__file__).parent.parent / "data"
NEU_ITEMS_DIR = DATA_DIR / "neu-repo" / "items"
CRAFT_CACHE_PATH = DATA_DIR / "craft_cache.json"
COLLECTIONS_PATH = DATA_DIR / "collections_resource.json"
LEVELING_PATH = DATA_DIR / "neu-repo" / "constants" / "leveling.json"
LAST_PROFILE_PATH = DATA_DIR / "last_profile.json"

MOULBERRY_LBIN_URL = "https://moulberry.codes/lowestbin.json"
MOULBERRY_AVG_LBIN_URL = "https://moulberry.codes/auction_averages_lbin/3day.json"
MOULBERRY_AVG_URL = "https://moulberry.codes/auction_averages/3day.json"
MOULBERRY_TTL = 300          # 5 minutes
MOULBERRY_EVICT = 3600       # 1 hour
COLLECTIONS_TTL = 86400      # 1 day

MIN_PROFIT = 10_000
MIN_VOLUME = 1

# Roman numeral lookup
_ROMAN = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
    "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
}

# Slayer req code → (boss_key in slayer_xp, display_name)
_SLAYER_MAP = {
    "ZOMBIE": ("zombie", "Zombie"),
    "SPIDER": ("spider", "Spider"),
    "WOLF": ("wolf", "Wolf"),
    "EMAN": ("enderman", "Enderman"),
    "BLAZE": ("blaze", "Blaze"),
    "VAMP": ("vampire", "Vampire"),
    "VAMPIRE": ("vampire", "Vampire"),
}


# ─── Recipe Parsing ───────────────────────────────────────────────────

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

        # Parse grid slots A1-C3
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

        # Parse unlock requirement
        requirement = parse_requirement(data)

        recipes.append({
            "item_id": output_id,
            "ingredients": ingredients,
            "output_count": max(output_count, 1),
            "requirement": requirement,
        })

    return recipes


def parse_requirement(data):
    """Parse crafttext and slayer_req fields into structured requirement."""
    # Prefer slayer_req field (more reliable format: "EMAN_5", "WOLF_3")
    slayer_req = data.get("slayer_req", "")
    if slayer_req:
        parts = slayer_req.rsplit("_", 1)
        if len(parts) == 2:
            code, level_str = parts
            if code in _SLAYER_MAP:
                boss_key, boss_display = _SLAYER_MAP[code]
                try:
                    level = int(level_str)
                except ValueError:
                    level = 0
                return {
                    "type": "slayer",
                    "boss": boss_key,
                    "boss_display": boss_display,
                    "level": level,
                    "text": f"{boss_display} Slayer {level}",
                }

    crafttext = data.get("crafttext", "")
    if not crafttext or "Requires:" not in crafttext:
        return None

    req_text = crafttext.replace("Requires: ", "").replace("Requires:", "").strip()

    # Check for slayer in crafttext: "Wolf Slayer 3", "Enderman Slayer 5"
    slayer_match = re.match(r"(\w+)\s+Slayer\s+(\d+)", req_text)
    if slayer_match:
        boss_display = slayer_match.group(1)
        level = int(slayer_match.group(2))
        # Map display name to boss key
        boss_key = boss_display.lower()
        return {
            "type": "slayer",
            "boss": boss_key,
            "boss_display": boss_display,
            "level": level,
            "text": f"{boss_display} Slayer {level}",
        }

    # Check for HotM: "HotM 5"
    hotm_match = re.match(r"HotM\s+(\d+)", req_text)
    if hotm_match:
        return {
            "type": "hotm",
            "level": int(hotm_match.group(1)),
            "text": f"HotM {hotm_match.group(1)}",
        }

    # Check for museum: "20 Museum Donations"
    museum_match = re.match(r"(\d+)\s+Museum\s+Donations?", req_text)
    if museum_match:
        return {
            "type": "museum",
            "count": int(museum_match.group(1)),
            "text": req_text,
        }

    # Collection requirement: "Iron Ingot VI", "Lily Pad II", "Mangrove Log III"
    # Match: display name (possibly multi-word) + roman numeral
    coll_match = re.match(r"(.+?)\s+([IVXL]+)$", req_text)
    if coll_match:
        coll_name = coll_match.group(1)
        tier = _ROMAN.get(coll_match.group(2), 0)
        if tier > 0:
            return {
                "type": "collection",
                "display_name": coll_name,
                "tier": tier,
                "text": req_text,
            }

    # Unknown requirement
    return {"type": "other", "text": req_text}


# ─── Collections Data ─────────────────────────────────────────────────

def load_collections_data(cache):
    """Load collections data from cache or file. Returns (collections_dict, name_to_key)."""
    # Check cache first
    now = time.time()
    cached_colls = cache.get("collections")
    cached_ts = cache.get("collections_ts", 0)
    if cached_colls and now - cached_ts < COLLECTIONS_TTL:
        colls = cached_colls
    else:
        # Load from file
        if not COLLECTIONS_PATH.exists():
            print("  collections_resource.json not found", file=sys.stderr)
            return {}, {}
        try:
            raw = json.loads(COLLECTIONS_PATH.read_text())
            colls = raw.get("collections", {})
            cache["collections"] = colls
            cache["collections_ts"] = now
        except (json.JSONDecodeError, OSError):
            return {}, {}

    # Build reverse lookup: display name (lowercase) → {api_key, tiers}
    name_to_key = {}
    all_items = {}
    for category_data in colls.values():
        items = category_data.get("items", {})
        for api_key, item_data in items.items():
            display = item_data.get("name", "")
            tiers = {}
            for t in item_data.get("tiers", []):
                tiers[t["tier"]] = t["amountRequired"]
            entry = {"api_key": api_key, "tiers": tiers}
            all_items[api_key] = entry
            if display:
                name_to_key[display.lower()] = entry

    return all_items, name_to_key


def resolve_collection_requirement(req, name_to_key):
    """Resolve a collection requirement to include the API key and threshold."""
    if not req or req["type"] != "collection":
        return req

    display = req["display_name"]
    entry = name_to_key.get(display.lower())
    if not entry:
        return req

    tier = req["tier"]
    threshold = entry["tiers"].get(tier, 0)
    req["key"] = entry["api_key"]
    req["threshold"] = threshold
    return req


# ─── Slayer XP Thresholds ─────────────────────────────────────────────

def load_slayer_thresholds():
    """Load slayer XP thresholds from NEU leveling.json."""
    if not LEVELING_PATH.exists():
        return {}
    try:
        data = json.loads(LEVELING_PATH.read_text())
        return data.get("slayer_xp", {})
    except (json.JSONDecodeError, OSError):
        return {}


def resolve_slayer_requirement(req, slayer_thresholds):
    """Add XP threshold to slayer requirement."""
    if not req or req["type"] != "slayer":
        return req

    boss = req["boss"]
    level = req["level"]
    thresholds = slayer_thresholds.get(boss, [])
    # thresholds[0] = level 1, thresholds[1] = level 2, etc.
    if 0 < level <= len(thresholds):
        req["xp_needed"] = thresholds[level - 1]
    return req


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
            req = Request(url, headers={"User-Agent": "SkyblockCrafts/1.0"})
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
    """Filter recipes to those where all ingredients are on bazaar
    and the output is NOT on bazaar (i.e., sold on AH)."""
    bazaar_items = set()
    price_cache._fetch_bazaar()
    for pid, bz in price_cache._bazaar.items():
        if bz.get("buy", 0) > 0 or bz.get("sell", 0) > 0:
            bazaar_items.add(pid)

    valid = []
    for recipe in recipes:
        item_id = recipe["item_id"]

        # Output must NOT be on bazaar (it's an AH item)
        if item_id in bazaar_items:
            continue

        # All ingredients must be on bazaar
        all_bz = True
        for ing_id in recipe["ingredients"]:
            if ing_id not in bazaar_items:
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
                     force_refresh=False):
    """Scan all recipes and return profitable craft flips.

    All price data is loaded in bulk from Moulberry APIs up front,
    then a single pass iterates recipes and looks up prices in memory.
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

    flips = []
    for recipe in recipes:
        item_id = recipe["item_id"]

        cost = calculate_craft_cost(recipe, price_cache)
        if cost is None:
            continue

        # Get 3-day avg lowest BIN (primary profit metric)
        item_avg = avg_lbin.get(item_id)
        if not item_avg or item_avg <= 0:
            continue

        # Get sales volume from auction averages
        avg_data = auction_averages.get(item_id)
        if not avg_data:
            continue
        sales_per_day = avg_data.get("sales", 0) / 3.0

        if sales_per_day < MIN_VOLUME:
            continue

        # Current lowest BIN for display
        current_lbin = lowestbin.get(item_id, 0)

        # Profit based on avg BIN (more stable than current BIN)
        profit = item_avg * 0.99 - cost

        if profit < MIN_PROFIT:
            continue

        flips.append({
            "item_id": item_id,
            "cost": cost,
            "avg_lbin": item_avg,
            "lbin": current_lbin,
            "profit": profit,
            "sales_per_day": sales_per_day,
            "requirement": recipe["requirement"],
        })

    flips.sort(key=lambda x: x["profit"], reverse=True)
    return flips


# ─── Profile Filtering ────────────────────────────────────────────────

def load_player_data():
    """Load player data from last_profile.json."""
    if not LAST_PROFILE_PATH.exists():
        return None
    try:
        data = json.loads(LAST_PROFILE_PATH.read_text())
        profile = data.get("profile", {})
        uuid = data.get("uuid", "")
        # Find the member data
        members = profile.get("members", {})
        member = members.get(uuid)
        if not member:
            # Try with dashes
            formatted = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
            member = members.get(formatted)
        if not member:
            for key, val in members.items():
                if key.replace("-", "") == uuid:
                    member = val
                    break
        return member
    except (json.JSONDecodeError, OSError, KeyError):
        return None


def check_unlocked(req, member, slayer_thresholds):
    """Check if a player meets a requirement. Returns (unlocked, progress, needed)."""
    if req is None:
        return True, None, None

    if req["type"] == "collection":
        api_key = req.get("key")
        threshold = req.get("threshold", 0)
        if not api_key or not threshold:
            return False, 0, 0
        collections = member.get("collection", {})
        progress = collections.get(api_key, 0)
        return progress >= threshold, progress, threshold

    if req["type"] == "slayer":
        boss = req["boss"]
        level = req["level"]
        # Map boss key to API boss key format
        boss_api_map = {
            "zombie": "zombie",
            "spider": "spider",
            "wolf": "wolf",
            "enderman": "enderman",
            "blaze": "blaze",
            "vampire": "vampire",
        }
        api_boss = boss_api_map.get(boss, boss)
        slayer_data = member.get("slayer", {}).get("slayer_bosses", {})
        boss_data = slayer_data.get(api_boss, {})
        current_xp = boss_data.get("xp", 0)
        thresholds = slayer_thresholds.get(boss, [])
        needed = thresholds[level - 1] if 0 < level <= len(thresholds) else 0
        return current_xp >= needed, current_xp, needed

    if req["type"] == "hotm":
        hotm = member.get("mining_core", {})
        current_level = hotm.get("nodes", {}).get("special_0", 0)
        # HotM level is stored differently — try experience
        experience = hotm.get("experience", 0)
        # Simple level calc from experience (approximate)
        level = req["level"]
        # Actually, HotM level is usually stored directly
        # Try getting it from the tier
        tier = hotm.get("tier", 1)
        return tier >= level, tier, level

    # Unknown types — assume not unlocked
    return False, 0, 0


# ─── Display ──────────────────────────────────────────────────────────

def print_flips(flips, title="CRAFT FLIPS"):
    """Print a table of craft flips."""
    print(f"\n{title} (min {_fmt(MIN_PROFIT)} profit, min {MIN_VOLUME} sale/day)")
    print("=" * 100)
    print(f"  {'Item':<30s} {'Cost':>10s}  {'Avg BIN':>10s}  {'Lbin':>10s}  {'Profit':>10s} {'Sales':>6s}  Requirement")
    print(f"  {'-'*30} {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10} {'-'*6}  {'-'*20}")

    for flip in flips:
        name = display_name(flip["item_id"])
        if len(name) > 30:
            name = name[:27] + "..."
        req_text = flip["requirement"]["text"] if flip["requirement"] else ""
        spd = flip.get("sales_per_day", 0)
        spd_str = f"{spd:.0f}/d" if spd >= 10 else f"{spd:.1f}/d"
        lbin_str = _fmt(flip["lbin"]) if flip.get("lbin") else "N/A"
        print(f"  {name:<30s} {_fmt(flip['cost']):>10s}  {_fmt(flip['avg_lbin']):>10s}  "
              f"{lbin_str:>10s}  {_fmt(flip['profit']):>10s} {spd_str:>6s}  {req_text}")

    if not flips:
        print("  No profitable crafts found.")
    print()


def print_profile_flips(flips, member, slayer_thresholds):
    """Print flips filtered by player unlocks."""
    unlocked = []
    almost = []

    for flip in flips:
        req = flip["requirement"]
        is_unlocked, progress, needed = check_unlocked(req, member, slayer_thresholds)

        if is_unlocked:
            unlocked.append(flip)
        elif progress is not None and needed and needed > 0:
            pct = progress / needed
            almost.append({**flip, "progress": progress, "needed": needed, "pct": pct})

    # Print unlocked
    print(f"\nUNLOCKED CRAFT FLIPS")
    print("=" * 90)
    if unlocked:
        print(f"  {'Item':<30s} {'Cost':>10s}  {'Avg BIN':>10s}  {'Lbin':>10s}  {'Profit':>10s} {'Sales':>6s}")
        print(f"  {'-'*30} {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10} {'-'*6}")
        for flip in unlocked:
            name = display_name(flip["item_id"])
            if len(name) > 30:
                name = name[:27] + "..."
            spd = flip.get("sales_per_day", 0)
            spd_str = f"{spd:.0f}/d" if spd >= 10 else f"{spd:.1f}/d"
            lbin_str = _fmt(flip["lbin"]) if flip.get("lbin") else "N/A"
            print(f"  {name:<30s} {_fmt(flip['cost']):>10s}  {_fmt(flip['avg_lbin']):>10s}  "
                  f"{lbin_str:>10s}  {_fmt(flip['profit']):>10s} {spd_str:>6s}")
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
            req_text = flip["requirement"]["text"] if flip["requirement"] else ""
            if len(req_text) > 22:
                req_text = req_text[:19] + "..."
            prog_str = f"{_fmt(flip['progress'])} / {_fmt(flip['needed'])}"
            if flip["requirement"]["type"] == "slayer":
                prog_str += " XP"
            pct_str = f"({flip['pct']*100:.0f}%)"
            print(f"  {name:<26s} {_fmt(flip['profit']):>8s}  {req_text:<22s} {prog_str} {pct_str}")
        print()


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SkyBlock craft flip scanner")
    parser.add_argument("--profile", action="store_true",
                        help="Filter by player's unlocked recipes (reads last_profile.json)")
    parser.add_argument("--cached", action="store_true",
                        help="Use cached prices only (skip API calls)")
    parser.add_argument("--fresh", action="store_true",
                        help="Ignore cache, fetch all prices fresh")
    args = parser.parse_args()

    # Load cache
    craft_cache = load_craft_cache()

    if args.fresh:
        craft_cache["moulberry"] = {}
        print("  Cleared price cache (--fresh)", file=sys.stderr)

    # Parse all recipes from NEU repo
    print("  Parsing recipes from NEU repo...", file=sys.stderr)
    all_recipes = parse_recipes()
    print(f"  Found {len(all_recipes)} crafting recipes", file=sys.stderr)

    # Load collections and slayer data for requirement resolution
    all_items, name_to_key = load_collections_data(craft_cache)
    slayer_thresholds = load_slayer_thresholds()

    # Resolve requirements with actual thresholds
    for recipe in all_recipes:
        if recipe["requirement"]:
            resolve_collection_requirement(recipe["requirement"], name_to_key)
            resolve_slayer_requirement(recipe["requirement"], slayer_thresholds)

    # Filter to valid craft flips (all ingredients on bazaar, output on AH)
    price_cache = PriceCache()
    valid = filter_craft_flips(all_recipes, price_cache)
    print(f"  {len(valid)} recipes with all-bazaar ingredients and AH output", file=sys.stderr)

    if not valid:
        print("\n  No valid craft flip candidates found.")
        price_cache.flush()
        return

    # Scan for profitable flips
    flips = scan_craft_flips(valid, price_cache, craft_cache,
                             use_cached_only=args.cached, force_refresh=args.fresh)

    # Save caches
    save_craft_cache(craft_cache)
    price_cache.flush()

    # Display results
    if args.profile:
        member = load_player_data()
        if not member:
            print("  Error: last_profile.json not found or invalid.", file=sys.stderr)
            print("  Run 'python3 profile.py' first to fetch profile data.", file=sys.stderr)
            # Fall back to full list
            print_flips(flips)
        else:
            print_profile_flips(flips, member, slayer_thresholds)
    else:
        print_flips(flips)

    mb = craft_cache.get("moulberry", {})
    n_lbin = len(mb.get("lowestbin", {}))
    n_avg = len(mb.get("avg_lbin", {}))
    n_sales = len(mb.get("auction_averages", {}))
    print(f"  Data: {n_lbin} lowest BINs, {n_avg} avg BINs, {n_sales} sale records", file=sys.stderr)


if __name__ == "__main__":
    main()
