#!/usr/bin/env python3
"""Museum donation optimizer for Hypixel SkyBlock.

Shows the cheapest items you haven't donated to the Museum yet,
similar to Skyblocker's in-game museum feature.

Usage:
    python3 museum.py                    # Show cheapest 25 missing items
    python3 museum.py -n 50              # Show top 50
    python3 museum.py --category combat  # Filter by category
    python3 museum.py --all              # Show all missing items
    python3 museum.py --xp               # Sort by XP/coin ratio instead
    python3 museum.py --sets             # Show armor sets separately
    python3 museum.py --refresh          # Fetch fresh museum data first
    python3 museum.py --special          # Include special items (no XP/milestones)
"""

import argparse
import json
import os
import sys
from pathlib import Path

from items import display_name
from pricing import PriceCache, _fmt
from crafts import parse_recipes
from profile import api_get, resolve_uuid, get_profiles, get_museum, API_KEY

DATA_DIR = Path(__file__).parent.parent / "data"
NEU_MUSEUM = DATA_DIR / "neu-repo" / "constants" / "museum.json"
LAST_PROFILE = DATA_DIR / "last_profile.json"

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

USERNAME = os.environ.get("MINECRAFT_USERNAME", "")


def load_museum_data():
    """Load the NEU museum constants (all donatable items)."""
    with open(NEU_MUSEUM) as f:
        return json.load(f)


def refresh_museum_data():
    """Fetch fresh museum data from the Hypixel API and update last_profile.json."""
    if not USERNAME:
        print("Error: MINECRAFT_USERNAME not set in .env", file=sys.stderr)
        sys.exit(1)

    print(f"Refreshing museum data for {USERNAME}...")
    uuid, display = resolve_uuid(USERNAME)
    data = get_profiles(uuid)

    if not data.get("success") or not data.get("profiles"):
        print("Error: No profiles found!", file=sys.stderr)
        sys.exit(1)

    # Find active profile
    active = None
    for p in data["profiles"]:
        if p.get("selected"):
            active = p
            break
    if not active:
        active = data["profiles"][0]

    profile_id = active["profile_id"]
    museum_data = get_museum(profile_id)

    if not museum_data or not museum_data.get("success"):
        print("Error: Could not fetch museum data. Is Museum API enabled?",
              file=sys.stderr)
        sys.exit(1)

    # Update last_profile.json with fresh museum data
    if LAST_PROFILE.exists():
        with open(LAST_PROFILE) as f:
            cached = json.load(f)
        cached["museum"] = museum_data
        cached["uuid"] = uuid
    else:
        cached = {"uuid": uuid, "museum": museum_data}

    LAST_PROFILE.write_text(json.dumps(cached, indent=2))
    print(f"Museum data refreshed ({active.get('cute_name', 'Unknown')} profile).")
    return museum_data, uuid


def load_donated_items(refresh=False):
    """Load donated item IDs from the Hypixel Museum API.

    If refresh=True, fetches fresh data first. Otherwise uses last_profile.json.
    """
    if refresh:
        museum, uuid = refresh_museum_data()
    else:
        if not LAST_PROFILE.exists():
            print("Error: No cached profile data. Run with --refresh or "
                  "'python3 profile.py' first.", file=sys.stderr)
            sys.exit(1)

        with open(LAST_PROFILE) as f:
            profile = json.load(f)

        museum = profile.get("museum", {})
        uuid = profile.get("uuid", "").replace("-", "")

    if not museum or not museum.get("success"):
        print("Error: Museum data not available. Make sure Museum API is enabled.",
              file=sys.stderr)
        print("       Run with --refresh or 'python3 profile.py museum' to fetch.",
              file=sys.stderr)
        sys.exit(1)

    if not isinstance(uuid, str):
        uuid = ""
    uuid = uuid.replace("-", "")
    members = museum.get("members", {})

    member_data = None
    for key, val in members.items():
        if key.replace("-", "") == uuid:
            member_data = val
            break

    if not member_data:
        print("Error: Could not find your museum data.", file=sys.stderr)
        sys.exit(1)

    # Collect all donated item/set IDs
    donated = set()
    items = member_data.get("items", {})
    for item_id in items:
        donated.add(item_id)

    # Special items
    special = member_data.get("special", [])
    for sp in special:
        if isinstance(sp, dict):
            # Special items have different structure, extract what we can
            pass
        elif isinstance(sp, str):
            donated.add(sp)

    return donated


def build_upgrade_chains(children):
    """Build upgrade chains from the children map.

    children maps parent -> child (e.g., ABYSSAL -> DIVER means ABYSSAL is an
    upgrade of DIVER). If you've donated an upgrade, all downgrades are covered.

    Returns dict: item_id -> list of all downgrades (items it covers).
    """
    # children: key is the upgrade, value is what it upgraded FROM
    # So ABYSSAL -> DIVER means ABYSSAL is the upgraded version of DIVER
    downgrades = {}
    for upgrade_id, base_id in children.items():
        if upgrade_id not in downgrades:
            downgrades[upgrade_id] = []
        downgrades[upgrade_id].append(base_id)
        # Also inherit any downgrades of the base
        if base_id in downgrades:
            downgrades[upgrade_id].extend(downgrades[base_id])
    return downgrades


def get_covered_items(donated, children):
    """Get the full set of items covered by donations, including via upgrades.

    If you donated ABYSSAL armor (an upgrade of DIVER), DIVER is also covered.
    """
    covered = set(donated)
    # Build full downgrade map
    downgrades = build_upgrade_chains(children)

    for item_id in donated:
        if item_id in downgrades:
            for dg in downgrades[item_id]:
                covered.add(dg)

    return covered


def build_recipe_index(recipes):
    """Build item_id -> recipe lookup from parsed recipes."""
    by_id = {}
    for r in recipes:
        # Keep the first (usually only) crafting recipe per item
        if r["item_id"] not in by_id:
            by_id[r["item_id"]] = r
    return by_id


def _best_buy_price(price_info):
    """Get the best buy price from price info.

    Prefers: bazaar buy price > lowest BIN > average BIN.
    """
    if not price_info:
        return None

    if price_info.get("source") == "bazaar":
        buy = price_info.get("buy")
        if buy and buy > 0:
            return buy

    lbin = price_info.get("lowest_bin")
    avg = price_info.get("avg_bin")

    if lbin and lbin > 0:
        return lbin
    if avg and avg > 0:
        return avg

    return None


def calc_craft_cost(item_id, price_cache, recipe_index, _seen=None):
    """Calculate the cost to craft an item from its recipe.

    Uses bazaar or auction prices for each ingredient, whichever is available.
    Recurses into sub-crafts if an ingredient has its own recipe and no
    direct price. Returns None if any ingredient can't be priced.
    """
    if _seen is None:
        _seen = set()
    if item_id in _seen:
        return None  # circular recipe
    _seen.add(item_id)

    recipe = recipe_index.get(item_id)
    if not recipe:
        return None

    total = 0
    for ing_id, qty in recipe["ingredients"].items():
        # Try to buy the ingredient directly
        info = price_cache.get_price(ing_id)
        buy_price = _best_buy_price(info)

        # Also try crafting the ingredient
        craft_price = calc_craft_cost(ing_id, price_cache, recipe_index, _seen.copy())

        # Use whichever is cheaper
        if buy_price and craft_price:
            best = min(buy_price, craft_price)
        elif buy_price:
            best = buy_price
        elif craft_price:
            best = craft_price
        else:
            return None  # can't price this ingredient at all

        total += best * qty

    output_count = recipe.get("output_count", 1)
    return total / output_count


def price_item(price_cache, item_id, sets_to_items, recipe_index):
    """Get the effective price for an item or armor set.

    For each item, considers both the buy price and the craft cost,
    and uses whichever is cheaper — matching how Skyblocker does it.
    For armor sets, sums the best price per piece.
    Returns (price, source_desc) where price is None if not priceable.
    """
    pieces = sets_to_items.get(item_id)

    if pieces:
        # It's an armor/equipment set — sum best price per piece
        total = 0
        all_priced = True
        for piece_id in pieces:
            buy = _best_buy_price(price_cache.get_price(piece_id))
            craft = calc_craft_cost(piece_id, price_cache, recipe_index)
            if buy and craft:
                total += min(buy, craft)
            elif buy:
                total += buy
            elif craft:
                total += craft
            else:
                all_priced = False
        if total > 0:
            return (total, f"set of {len(pieces)}")
        return (None, f"set of {len(pieces)}, no price")
    else:
        # Single item — use min(buy, craft)
        buy = _best_buy_price(price_cache.get_price(item_id))
        craft = calc_craft_cost(item_id, price_cache, recipe_index)

        if buy and craft:
            p = min(buy, craft)
            src = "craft" if craft <= buy else price_cache.get_price(item_id).get("source", "auction")
            return (p, src)
        elif buy:
            return (buy, price_cache.get_price(item_id).get("source", "auction"))
        elif craft:
            return (craft, "craft")
        return (None, "no price")


def get_item_name(item_id, sets_to_items, armor_names, set_exceptions):
    """Get a nice display name for an item or set."""
    if item_id in sets_to_items:
        # Check if there's a friendly name for this set
        if item_id in armor_names:
            return armor_names[item_id]
        # Check set_exceptions (reverse: real_id -> display_id)
        for exc_name, exc_id in set_exceptions.items():
            if exc_id == item_id:
                return format_set_name(exc_name)
        return format_set_name(item_id)
    else:
        name = display_name(item_id)
        return name if name != item_id else item_id.replace("_", " ").title()


def format_set_name(item_id):
    """Format a set ID into a readable name like 'Shadow Assassin Armor'."""
    name = item_id.replace("_", " ").title()
    # Don't add 'Armor' if it already ends with armor/outfit/suit/tuxedo
    lower = name.lower()
    if not any(lower.endswith(s) for s in ("armor", "outfit", "suit", "tuxedo")):
        name += " Armor"
    return name


def main():
    parser = argparse.ArgumentParser(
        description="Find the cheapest museum items you haven't donated yet."
    )
    parser.add_argument("-n", "--count", type=int, default=25,
                        help="Number of items to show (default: 25)")
    parser.add_argument("--all", action="store_true",
                        help="Show all missing items")
    parser.add_argument("--category", "-c", type=str, default=None,
                        help="Filter by category (combat, farming, mining, etc.)")
    parser.add_argument("--xp", action="store_true",
                        help="Sort by XP/coin ratio (best value)")
    parser.add_argument("--sets", action="store_true",
                        help="Expand armor sets to show individual pieces")
    parser.add_argument("--special", action="store_true",
                        help="Include special category items (excluded by default — no XP or milestones)")
    parser.add_argument("--refresh", "-r", action="store_true",
                        help="Fetch fresh museum data from the API before running")
    args = parser.parse_args()

    # Load data
    print("Loading museum data...")
    museum_const = load_museum_data()
    donated = load_donated_items(refresh=args.refresh)

    items_by_cat = museum_const["items"]
    sets_to_items = museum_const.get("sets_to_items", {})
    children = museum_const.get("children", {})
    item_to_xp = museum_const.get("itemToXp", {})
    mapped_ids = museum_const.get("mapped_ids", {})
    set_exceptions = museum_const.get("set_exceptions", {})

    # Build a friendly name map for armor sets
    armor_names = {}
    armor_to_id = museum_const.get("armor_to_id", {})
    for set_id in sets_to_items:
        # Determine if it's equipment
        is_equipment = all(
            any(t in piece.upper() for t in
                ("BELT", "GLOVES", "CLOAK", "GAUNTLET", "NECKLACE",
                 "BRACELET", "HAT", "LOCKET", "VINE", "GRIPPERS"))
            for piece in sets_to_items[set_id]
        )
        real_id = set_id
        for exc_name, exc_id in set_exceptions.items():
            if exc_id == set_id:
                real_id = exc_name
                break
        name = real_id.replace("_", " ").title()
        if is_equipment:
            name += " Equipment"
        elif not any(name.lower().endswith(s) for s in
                     ("armor", "outfit", "suit", "tuxedo")):
            name += " Armor"
        armor_names[set_id] = name

    # Expand donated IDs with mapped_ids (reverse: some items have alternate IDs)
    expanded_donated = set(donated)
    # mapped_ids maps alternate_id -> canonical_id
    # If we donated the alternate, we've also donated the canonical
    for alt_id, canon_id in mapped_ids.items():
        if alt_id in expanded_donated:
            expanded_donated.add(canon_id)
        if canon_id in expanded_donated:
            expanded_donated.add(alt_id)

    # Get all covered items (including via upgrade chains)
    covered = get_covered_items(expanded_donated, children)

    # Collect missing items
    missing = []
    categories = items_by_cat.keys()
    if args.category:
        cat = args.category.lower()
        if cat not in items_by_cat:
            print(f"Unknown category '{cat}'. Available: {', '.join(items_by_cat.keys())}")
            sys.exit(1)
        categories = [cat]

    for category in categories:
        if not args.special and category == "special":
            continue
        for item_id in items_by_cat[category]:
            if item_id not in covered:
                xp = item_to_xp.get(item_id, 0)
                missing.append({
                    "id": item_id,
                    "category": category,
                    "xp": xp,
                    "is_set": item_id in sets_to_items,
                })

    print(f"Museum progress: {len(donated)} donated, {len(missing)} missing "
          f"(of {sum(len(v) for v in items_by_cat.values())} total)\n")

    if not missing:
        print("🎉 You've donated everything! Museum complete!")
        return

    # Load recipes and price all missing items
    print(f"Loading recipes and pricing {len(missing)} items...")
    price_cache = PriceCache()
    recipes = parse_recipes()
    recipe_index = build_recipe_index(recipes)

    for item in missing:
        price, source = price_item(price_cache, item["id"], sets_to_items, recipe_index)
        item["price"] = price
        item["source"] = source
        if item["xp"] > 0 and price and price > 0:
            item["xp_per_coin"] = item["xp"] / price
        else:
            item["xp_per_coin"] = 0

    price_cache.flush()

    # Sort
    if args.xp:
        # Best XP/coin ratio first (highest ratio = best value)
        missing.sort(key=lambda x: -(x["xp_per_coin"]))
    else:
        # Cheapest first, unpriceable at the end
        missing.sort(key=lambda x: (x["price"] is None, x["price"] or float("inf")))

    # Display
    limit = len(missing) if args.all else min(args.count, len(missing))
    showing = missing[:limit]

    # Count stats
    priceable = sum(1 for x in missing if x["price"] is not None)
    total_for_all = sum(x["price"] for x in missing if x["price"] is not None)

    if args.xp:
        print(f"\n{'':>4} {'Item':<40} {'Price':>10} {'XP':>5} {'XP/Coin':>10} {'Category':<12}")
        print(f"{'':>4} {'─' * 40} {'─' * 10} {'─' * 5} {'─' * 10} {'─' * 12}")
    else:
        print(f"\n{'':>4} {'Item':<40} {'Price':>10} {'XP':>5} {'Source':<15} {'Category':<12}")
        print(f"{'':>4} {'─' * 40} {'─' * 10} {'─' * 5} {'─' * 15} {'─' * 12}")

    for i, item in enumerate(showing, 1):
        name = get_item_name(item["id"], sets_to_items, armor_names, set_exceptions)
        price_str = _fmt(item["price"]) if item["price"] else "???"
        xp_str = str(item["xp"]) if item["xp"] else "-"

        if args.xp:
            ratio = f"{item['xp_per_coin']:.4f}" if item["xp_per_coin"] > 0 else "-"
            print(f"{i:>3}. {name:<40} {price_str:>10} {xp_str:>5} {ratio:>10} {item['category']:<12}")
        else:
            print(f"{i:>3}. {name:<40} {price_str:>10} {xp_str:>5} {item['source']:<15} {item['category']:<12}")

        # Optionally show set pieces
        if args.sets and item["is_set"]:
            pieces = sets_to_items[item["id"]]
            for piece_id in pieces:
                piece_name = display_name(piece_id)
                info = price_cache.get_price(piece_id)
                p = _best_buy_price(info)
                p_str = _fmt(p) if p else "???"
                print(f"     └─ {piece_name:<38} {p_str:>10}")

    # Summary
    print(f"\n{'─' * 88}")
    print(f"  Showing {limit} of {len(missing)} missing items "
          f"({priceable} priceable, {len(missing) - priceable} unknown)")
    if priceable > 0:
        cheapest_total = sum(x["price"] for x in showing if x["price"] is not None)
        print(f"  Cost of shown items: {_fmt(cheapest_total)}")
        print(f"  Cost of ALL missing (priceable): {_fmt(total_for_all)}")
    total_xp_missing = sum(x["xp"] for x in missing)
    if total_xp_missing:
        print(f"  Total missing XP: {total_xp_missing:,}")


if __name__ == "__main__":
    main()
