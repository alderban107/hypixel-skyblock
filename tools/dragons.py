#!/usr/bin/env python3
"""Dragon Profit Calculator for Hypixel SkyBlock.

Calculates expected profit per dragon fight by dragon type, using
DragonLoot.json drop tables and live market pricing.

The dragon fight system works via quality-based loot placement:
- Each item has a quality score and drop chance
- Higher damage placement = higher quality threshold = rarer drops
- Items marked "eye": true require placing an Eye of Ender (summoning eye)
- Items marked "unique": true can only drop once per fight
- Non-unique items (fragments, ender pearls) always drop

Data source: skyblock-plus-data DragonLoot.json

Usage:
    python3 dragons.py                  # all dragon types summary
    python3 dragons.py --type superior  # detailed Superior breakdown
    python3 dragons.py --eyes 4         # assume 4 eyes placed (affects cost)
    python3 dragons.py --json           # machine-readable output
"""

import argparse
import json
import sys
from pathlib import Path

from items import display_name
from pricing import PriceCache, _fmt

DATA_DIR = Path(__file__).parent.parent / "data"
EXTERNAL_DIR = DATA_DIR / "external"
DRAGON_LOOT_PATH = EXTERNAL_DIR / "DragonLoot.json"

# ─── Item name → Item ID mapping ──────────────────────────────────────
# DragonLoot.json uses display names. Map to internal IDs for pricing.
DRAGON_ITEM_IDS = {
    # Shared drops
    "Dragon Claw": "DRAGON_CLAW",
    "Dragon Horn": "DRAGON_HORN",
    "Dragon Scale": "DRAGON_SCALE",
    "Aspect Of The Dragons": "ASPECT_OF_THE_DRAGON",
    "Epic Ender Dragon": "ENDER_DRAGON;3",
    "Legendary Ender Dragon": "ENDER_DRAGON;4",
    "Travel Scroll To Dragon's Nest": "DRAGON_NEST_TRAVEL_SCROLL",
    "Ender Pearl": "ENDER_PEARL",
    # Old Dragon
    "Old Dragon Chestplate": "OLD_DRAGON_CHESTPLATE",
    "Old Dragon Leggings": "OLD_DRAGON_LEGGINGS",
    "Old Dragon Helmet": "OLD_DRAGON_HELMET",
    "Old Dragon Boots": "OLD_DRAGON_BOOTS",
    "Old Dragon Fragment": "OLD_DRAGON_FRAGMENT",
    # Protector Dragon
    "Protector Dragon Chestplate": "PROTECTOR_DRAGON_CHESTPLATE",
    "Protector Dragon Leggings": "PROTECTOR_DRAGON_LEGGINGS",
    "Protector Dragon Helmet": "PROTECTOR_DRAGON_HELMET",
    "Protector Dragon Boots": "PROTECTOR_DRAGON_BOOTS",
    "Protector Dragon Fragment": "PROTECTOR_DRAGON_FRAGMENT",
    # Strong Dragon
    "Strong Dragon Chestplate": "STRONG_DRAGON_CHESTPLATE",
    "Strong Dragon Leggings": "STRONG_DRAGON_LEGGINGS",
    "Strong Dragon Helmet": "STRONG_DRAGON_HELMET",
    "Strong Dragon Boots": "STRONG_DRAGON_BOOTS",
    "Strong Dragon Fragment": "STRONG_DRAGON_FRAGMENT",
    # Superior Dragon
    "Superior Dragon Chestplate": "SUPERIOR_DRAGON_CHESTPLATE",
    "Superior Dragon Leggings": "SUPERIOR_DRAGON_LEGGINGS",
    "Superior Dragon Helmet": "SUPERIOR_DRAGON_HELMET",
    "Superior Dragon Boots": "SUPERIOR_DRAGON_BOOTS",
    "Superior Dragon Fragment": "SUPERIOR_DRAGON_FRAGMENT",
    # Unstable Dragon
    "Unstable Dragon Chestplate": "UNSTABLE_DRAGON_CHESTPLATE",
    "Unstable Dragon Leggings": "UNSTABLE_DRAGON_LEGGINGS",
    "Unstable Dragon Helmet": "UNSTABLE_DRAGON_HELMET",
    "Unstable Dragon Boots": "UNSTABLE_DRAGON_BOOTS",
    "Unstable Dragon Fragment": "UNSTABLE_DRAGON_FRAGMENT",
    # Wise Dragon
    "Wise Dragon Chestplate": "WISE_DRAGON_CHESTPLATE",
    "Wise Dragon Leggings": "WISE_DRAGON_LEGGINGS",
    "Wise Dragon Helmet": "WISE_DRAGON_HELMET",
    "Wise Dragon Boots": "WISE_DRAGON_BOOTS",
    "Wise Dragon Fragment": "WISE_DRAGON_FRAGMENT",
    # Young Dragon
    "Dragon Armor": "YOUNG_DRAGON_CHESTPLATE",  # Young's chestplate is "Dragon Armor" in JSON
    "Young Dragon Leggings": "YOUNG_DRAGON_LEGGINGS",
    "Young Dragon Helmet": "YOUNG_DRAGON_HELMET",
    "Young Dragon Boots": "YOUNG_DRAGON_BOOTS",
    "Young Dragon Fragment": "YOUNG_DRAGON_FRAGMENT",
}

# Dragon types in display order
DRAGON_TYPES = ["protector", "old", "unstable", "young", "strong", "wise", "superior"]

# ─── Summoning Eye cost ───────────────────────────────────────────────
SUMMONING_EYE_ID = "SUMMONING_EYE"

# Default fragments dropped per kill (the JSON says 100% chance — typically 8 fragments)
DEFAULT_FRAGMENT_QTY = 8


def load_dragon_loot():
    """Load DragonLoot.json data."""
    if not DRAGON_LOOT_PATH.exists():
        print(f"ERROR: {DRAGON_LOOT_PATH} not found.", file=sys.stderr)
        print("  Copy from skyblock-plus-data: data/external/DragonLoot.json", file=sys.stderr)
        sys.exit(1)
    with open(DRAGON_LOOT_PATH) as f:
        return json.load(f)


def resolve_item_id(display_name_str):
    """Map a display name from DragonLoot.json to an item ID for pricing."""
    item_id = DRAGON_ITEM_IDS.get(display_name_str)
    if item_id:
        return item_id
    # Fallback: convert display name to item ID format
    return display_name_str.upper().replace(" ", "_").replace("'", "")


def calc_dragon_ev(dragon_type, loot_table, pc, eyes_placed=1):
    """Calculate expected value of fighting a specific dragon type.

    Args:
        dragon_type: e.g. "superior", "young"
        loot_table: dict of {item_display_name: {quality, drop_chance, unique?, eye?}}
        pc: PriceCache instance
        eyes_placed: number of eyes placed (1-8), affects cost

    Returns:
        dict with: items (list of item EVs), total_ev, eye_cost, net_profit
    """
    items = []

    for item_name, info in loot_table.items():
        item_id = resolve_item_id(item_name)
        drop_chance_str = info.get("drop_chance", "0%")
        drop_chance = float(drop_chance_str.strip("%")) / 100.0
        quality = info.get("quality", 0)
        is_unique = info.get("unique", False)
        requires_eye = info.get("eye", False)

        # Get price
        price_info = pc.get_price(item_id)
        # Use avg_bin for auction items (more stable), buy for bazaar
        if price_info["source"] == "bazaar":
            price = price_info.get("sell") or 0  # sell price = what you'd get
        elif price_info["source"] == "auction":
            price = price_info.get("avg_bin") or price_info.get("lowest_bin") or 0
        elif price_info["source"] == "override":
            price = price_info.get("lowest_bin") or 0
        else:
            price = 0

        # Fragments drop in qty 8 (non-unique, 100% chance)
        qty = DEFAULT_FRAGMENT_QTY if "Fragment" in item_name else 1

        ev = drop_chance * price * qty

        items.append({
            "name": item_name,
            "item_id": item_id,
            "drop_chance": drop_chance,
            "quality": quality,
            "price": price,
            "qty": qty,
            "ev": ev,
            "unique": is_unique,
            "requires_eye": requires_eye,
        })

    # Sort by EV descending
    items.sort(key=lambda x: x["ev"], reverse=True)
    total_ev = sum(i["ev"] for i in items)

    # Eye cost: each eye costs market price × eyes_placed
    eye_price_info = pc.get_price(SUMMONING_EYE_ID)
    if eye_price_info["source"] == "bazaar":
        eye_cost = (eye_price_info.get("buy") or 0) * eyes_placed
    else:
        eye_cost = (eye_price_info.get("avg_bin") or eye_price_info.get("lowest_bin") or 0) * eyes_placed

    net_profit = total_ev - eye_cost

    return {
        "dragon_type": dragon_type,
        "items": items,
        "total_ev": total_ev,
        "eye_cost": eye_cost,
        "eyes_placed": eyes_placed,
        "net_profit": net_profit,
    }


def print_dragon_detail(result, pc):
    """Print detailed breakdown for one dragon type."""
    dt = result["dragon_type"].title()
    print(f"\n{'═' * 60}")
    print(f"  {dt} Dragon")
    print(f"{'═' * 60}")

    # Eye cost
    eye_info = pc.get_price(SUMMONING_EYE_ID)
    eye_price = 0
    if eye_info["source"] == "bazaar":
        eye_price = eye_info.get("buy") or 0
    else:
        eye_price = eye_info.get("avg_bin") or eye_info.get("lowest_bin") or 0
    print(f"  Eyes Placed:  {result['eyes_placed']}  (cost: {_fmt(result['eye_cost'])})")
    print(f"  Eye Price:    {_fmt(eye_price)} each")
    print()

    # Drop table
    print(f"  {'Item':<35s} {'Chance':>8s} {'Price':>10s} {'EV':>10s}")
    print(f"  {'─' * 35} {'─' * 8} {'─' * 10} {'─' * 10}")

    for item in result["items"]:
        chance_str = f"{item['drop_chance'] * 100:.2f}%"
        if item["drop_chance"] >= 1.0:
            chance_str = "100%"
        name = item["name"]
        if item["qty"] > 1:
            name += f" ×{item['qty']}"
        flags = ""
        if item["requires_eye"]:
            flags += " 👁"
        if item["unique"]:
            flags += " ★"

        price_str = _fmt(item["price"]) if item["price"] else "?"
        ev_str = _fmt(item["ev"]) if item["ev"] else "-"
        print(f"  {name + flags:<35s} {chance_str:>8s} {price_str:>10s} {ev_str:>10s}")

    print(f"  {'─' * 35} {'─' * 8} {'─' * 10} {'─' * 10}")
    print(f"  {'Total EV':<35s} {'':>8s} {'':>10s} {_fmt(result['total_ev']):>10s}")
    print(f"  {'Eye Cost':<35s} {'':>8s} {'':>10s} {'-' + _fmt(result['eye_cost']):>10s}")
    profit_str = _fmt(result['net_profit'])
    if result['net_profit'] < 0:
        profit_str = f"-{_fmt(abs(result['net_profit']))}"
    print(f"  {'Net Profit':<35s} {'':>8s} {'':>10s} {profit_str:>10s}")
    print()
    print("  👁 = requires eye placement  ★ = unique (max 1 per fight)")


def print_summary(results, pc):
    """Print summary table of all dragon types."""
    print(f"\n{'═' * 70}")
    print(f"  Dragon Profit Calculator — Expected Value Per Fight")
    print(f"{'═' * 70}")

    # Eye price for context
    eye_info = pc.get_price(SUMMONING_EYE_ID)
    eye_price = 0
    if eye_info["source"] == "bazaar":
        eye_price = eye_info.get("buy") or 0
    else:
        eye_price = eye_info.get("avg_bin") or eye_info.get("lowest_bin") or 0
    eyes = results[0]["eyes_placed"] if results else 1
    print(f"  Summoning Eye: {_fmt(eye_price)} | Eyes placed: {eyes} | Eye cost: {_fmt(eye_price * eyes)}")
    print()

    print(f"  {'Dragon':<15s} {'Total EV':>10s} {'Eye Cost':>10s} {'Net Profit':>12s} {'Top Drop':>20s}")
    print(f"  {'─' * 15} {'─' * 10} {'─' * 10} {'─' * 12} {'─' * 20}")

    # Sort by net profit
    sorted_results = sorted(results, key=lambda x: x["net_profit"], reverse=True)

    for r in sorted_results:
        dt = r["dragon_type"].title()
        top_item = r["items"][0] if r["items"] else None
        top_name = top_item["name"][:18] if top_item else "?"

        profit_str = _fmt(r["net_profit"])
        if r["net_profit"] < 0:
            profit_str = f"-{_fmt(abs(r['net_profit']))}"

        print(f"  {dt:<15s} {_fmt(r['total_ev']):>10s} {_fmt(r['eye_cost']):>10s} {profit_str:>12s} {top_name:>20s}")

    print()
    best = sorted_results[0]
    worst = sorted_results[-1]
    print(f"  Best:  {best['dragon_type'].title()} ({_fmt(best['net_profit'])} net)")
    print(f"  Worst: {worst['dragon_type'].title()} ({_fmt(worst['net_profit'])} net)")
    print()
    print("  Note: EV assumes average luck. Actual returns vary by RNG.")
    print("  Dragon armor pieces are priced at current LBIN — heavily enchanted")
    print("  pieces may sell for more. Pet drops are extremely rare.")


def main():
    parser = argparse.ArgumentParser(description="SkyBlock Dragon Profit Calculator")
    parser.add_argument("--type", "-t", type=str, metavar="DRAGON",
                        help="Dragon type (protector/old/unstable/young/strong/wise/superior)")
    parser.add_argument("--eyes", "-e", type=int, default=1, metavar="N",
                        help="Number of eyes placed (1-8, default: 1)")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    args = parser.parse_args()

    if args.eyes < 1 or args.eyes > 8:
        print("ERROR: --eyes must be 1-8", file=sys.stderr)
        sys.exit(1)

    loot_data = load_dragon_loot()
    pc = PriceCache()

    if args.type:
        dtype = args.type.lower()
        if dtype not in loot_data:
            print(f"ERROR: Unknown dragon type '{args.type}'", file=sys.stderr)
            print(f"  Valid types: {', '.join(DRAGON_TYPES)}", file=sys.stderr)
            sys.exit(1)
        result = calc_dragon_ev(dtype, loot_data[dtype], pc, args.eyes)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_dragon_detail(result, pc)
    else:
        results = []
        for dtype in DRAGON_TYPES:
            if dtype in loot_data:
                results.append(calc_dragon_ev(dtype, loot_data[dtype], pc, args.eyes))
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print_summary(results, pc)

    pc.flush()


if __name__ == "__main__":
    main()
