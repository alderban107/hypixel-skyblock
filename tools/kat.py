#!/usr/bin/env python3
"""Kat upgrade calculator for Hypixel SkyBlock.

Given a pet type and start/end rarity, calculates total materials, coins,
time, and Bazaar costs for the upgrade chain. Shows profit if selling the
upgraded pet.

Uses NEU repo katgrade recipe data — no wiki parsing needed.

Usage:
    python3 kat.py RABBIT                                    # All upgrade paths
    python3 kat.py RABBIT --from uncommon --to legendary     # Specific range
    python3 kat.py RABBIT --from common --to legendary --profit  # Include profit
"""

import json
import sys
from pathlib import Path

from items import display_name
from pricing import PriceCache, RARITY_NUM, RARITY_NAME, _fmt

DATA_DIR = Path(__file__).parent.parent / "data"
NEU_ITEMS_DIR = DATA_DIR / "neu-repo" / "items"


def _load_neu_item(item_id):
    """Load a NEU repo item JSON. Returns dict or None."""
    path = NEU_ITEMS_DIR / f"{item_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _find_katgrade(pet_type, target_rarity):
    """Find katgrade recipe for upgrading TO the target rarity.

    The recipe lives on the output pet file (e.g., RABBIT;4 has the
    recipe for upgrading from epic to legendary).
    """
    pet_id = f"{pet_type};{target_rarity}"
    data = _load_neu_item(pet_id)
    if not data:
        return None

    for recipe in data.get("recipes", []):
        if recipe.get("type") == "katgrade":
            return recipe
    return None


def _parse_item_str(item_str):
    """Parse 'ENCHANTED_RABBIT:16' into (item_id, qty)."""
    parts = item_str.split(":")
    if len(parts) == 2:
        return parts[0], int(parts[1])
    return parts[0], 1


def _format_time(seconds):
    """Format seconds into human-readable time."""
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min"
    hours = minutes // 60
    remaining_min = minutes % 60
    if hours < 24:
        if remaining_min:
            return f"{hours}h {remaining_min}m"
        return f"{hours}h"
    days = hours // 24
    remaining_hours = hours % 24
    if remaining_hours:
        return f"{days}d {remaining_hours}h"
    return f"{days}d"


def get_available_rarities(pet_type):
    """Find which rarities exist for a pet type in the NEU repo."""
    available = []
    for rarity_num in range(6):
        pet_id = f"{pet_type};{rarity_num}"
        if _load_neu_item(pet_id):
            available.append(rarity_num)
    return available


def get_kat_chain(pet_type, from_rarity, to_rarity):
    """Load Kat upgrade steps from NEU repo.

    Returns list of step dicts: {coins, time, items, from_rarity, to_rarity}
    """
    chain = []
    for rarity_num in range(from_rarity + 1, to_rarity + 1):
        katgrade = _find_katgrade(pet_type, rarity_num)
        if not katgrade:
            return None  # Missing step — can't complete the chain
        chain.append({
            "coins": katgrade.get("coins", 0),
            "time": katgrade.get("time", 0),
            "items": katgrade.get("items", []),
            "from_rarity": rarity_num - 1,
            "to_rarity": rarity_num,
        })
    return chain


def calculate_total(chain, price_cache):
    """Sum up coins, materials, time, and bazaar costs across all steps."""
    total_coins = sum(step["coins"] for step in chain)
    total_time = sum(step["time"] for step in chain)

    # Aggregate items across all steps
    all_items = {}
    for step in chain:
        for item_str in step["items"]:
            item_id, qty = _parse_item_str(item_str)
            all_items[item_id] = all_items.get(item_id, 0) + qty

    # Price each material
    total_material_cost = 0
    material_details = []
    for item_id, qty in sorted(all_items.items()):
        p = price_cache.get_price(item_id)
        if p["source"] == "bazaar" and p.get("buy"):
            unit_price = p["buy"]
        elif p["source"] == "auction" and p.get("lowest_bin"):
            unit_price = p["lowest_bin"]
        else:
            unit_price = 0
        line_total = unit_price * qty
        total_material_cost += line_total
        material_details.append({
            "item_id": item_id,
            "qty": qty,
            "unit_price": unit_price,
            "total": line_total,
            "source": p["source"],
        })

    return {
        "total_coins": total_coins,
        "total_time": total_time,
        "total_material_cost": total_material_cost,
        "materials": material_details,
        "grand_total": total_coins + total_material_cost,
    }


def show_upgrade(pet_type, from_rarity, to_rarity, price_cache, show_profit=False):
    """Display a full Kat upgrade breakdown."""
    from_name = RARITY_NAME.get(from_rarity, str(from_rarity))
    to_name = RARITY_NAME.get(to_rarity, str(to_rarity))
    pet_display = pet_type.replace("_", " ").title()

    chain = get_kat_chain(pet_type, from_rarity, to_rarity)
    if not chain:
        print(f"\n  No Kat upgrade path found for {pet_display}: {from_name} -> {to_name}")
        return

    print(f"\n  Kat Upgrade: {pet_display} -- {from_name} -> {to_name}")
    print()

    # Step-by-step table
    print(f"  {'Step':<22s} {'Coins':>10s} {'Time':>10s}  Materials")
    print(f"  {'─' * 22} {'─' * 10} {'─' * 10}  {'─' * 40}")

    for step in chain:
        step_from = RARITY_NAME.get(step["from_rarity"], "?")
        step_to = RARITY_NAME.get(step["to_rarity"], "?")
        step_label = f"{step_from} -> {step_to}"

        # Format materials inline
        mat_parts = []
        for item_str in step["items"]:
            item_id, qty = _parse_item_str(item_str)
            name = display_name(item_id)
            mat_parts.append(f"{qty} {name}")
        mat_str = ", ".join(mat_parts)

        print(f"  {step_label:<22s} {_fmt(step['coins']):>10s} {_format_time(step['time']):>10s}  {mat_str}")

    # Totals
    totals = calculate_total(chain, price_cache)
    print()

    # Material cost breakdown
    print(f"  Total Materials:")
    for mat in totals["materials"]:
        name = display_name(mat["item_id"])
        if len(name) > 28:
            name = name[:25] + "..."
        source_tag = "  (AH)" if mat["source"] == "auction" else ""
        if mat["unit_price"] > 0:
            print(f"    {name:<28s} {mat['qty']:>6,d} x {_fmt(mat['unit_price']):>8s}  = {_fmt(mat['total']):>12s}{source_tag}")
        else:
            print(f"    {name:<28s} {mat['qty']:>6,d} x {'?':>8s}  = {'?':>12s}")

    print()
    print(f"  Total Kat Coins:  {_fmt(totals['total_coins'])}")
    print(f"  Total Materials:  {_fmt(totals['total_material_cost'])}")
    print(f"  Grand Total:      {_fmt(totals['grand_total'])}")
    print(f"  Kat Time:         {_format_time(totals['total_time'])}")

    # Profit analysis
    if show_profit:
        print()
        # Get sell price of upgraded pet
        upgraded_id = f"{pet_type};{to_rarity}"
        sell = price_cache.get_price(upgraded_id)

        # Get buy price of starting pet
        start_id = f"{pet_type};{from_rarity}"
        buy = price_cache.get_price(start_id)

        if sell["source"] != "unknown":
            lbin = sell.get("lowest_bin")
            avg = sell.get("avg_bin")
            sales = sell.get("sales_day")
            parts = []
            if lbin:
                parts.append(f"LBIN {_fmt(lbin)}")
            if avg:
                parts.append(f"avg {_fmt(avg)}")
            if sales:
                parts.append(f"({sales:.1f}/day)")
            print(f"  {to_name} {pet_display} AH:  {' '.join(parts)}")

            # Buy price of starting pet
            if buy["source"] != "unknown":
                buy_lbin = buy.get("lowest_bin", 0) or 0
                print(f"  {from_name} {pet_display} AH:  LBIN {_fmt(buy_lbin)}")
                input_cost = buy_lbin
            else:
                input_cost = 0

            # Profit = sell_price * 0.99 - (input_cost + grand_total)
            sell_val = avg or lbin or 0
            if sell_val > 0:
                profit = sell_val * 0.99 - (input_cost + totals["grand_total"])
                print(f"  Profit:  {_fmt(profit)}")
        else:
            print(f"  No AH data for {to_name} {pet_display}")

    print()


def show_all_upgrades(pet_type, price_cache, show_profit=False):
    """Show all possible single-step upgrades for a pet."""
    available = get_available_rarities(pet_type)
    pet_display = pet_type.replace("_", " ").title()

    if not available:
        print(f"\n  No pet data found for {pet_display}")
        return

    # Find which rarities have katgrade recipes
    upgrades = []
    for rarity in available:
        katgrade = _find_katgrade(pet_type, rarity)
        if katgrade:
            upgrades.append(rarity)

    if not upgrades:
        print(f"\n  No Kat upgrades available for {pet_display}")
        print(f"  Available rarities: {', '.join(RARITY_NAME[r] for r in available)}")
        return

    print(f"\n  Kat Upgrades for {pet_display}")
    print(f"  Available rarities: {', '.join(RARITY_NAME[r] for r in available)}")
    print()

    # Show each single-step upgrade as a summary
    print(f"  {'Upgrade':<26s} {'Coins':>10s} {'Materials':>12s} {'Total':>12s} {'Time':>10s}")
    print(f"  {'─' * 26} {'─' * 10} {'─' * 12} {'─' * 12} {'─' * 10}")

    for rarity in upgrades:
        chain = get_kat_chain(pet_type, rarity - 1, rarity)
        if not chain:
            continue
        totals = calculate_total(chain, price_cache)
        from_name = RARITY_NAME.get(rarity - 1, "?")
        to_name = RARITY_NAME.get(rarity, "?")
        label = f"{from_name} -> {to_name}"

        print(f"  {label:<26s} {_fmt(totals['total_coins']):>10s} "
              f"{_fmt(totals['total_material_cost']):>12s} "
              f"{_fmt(totals['grand_total']):>12s} "
              f"{_format_time(totals['total_time']):>10s}")

    # Show multi-step paths if there are 3+ upgradeable rarities
    if len(upgrades) >= 2:
        min_rarity = upgrades[0] - 1
        max_rarity = upgrades[-1]
        if max_rarity - min_rarity >= 2:
            print()
            print(f"  Full chain: {RARITY_NAME[min_rarity]} -> {RARITY_NAME[max_rarity]}")
            chain = get_kat_chain(pet_type, min_rarity, max_rarity)
            if chain:
                totals = calculate_total(chain, price_cache)
                print(f"    Coins: {_fmt(totals['total_coins'])}  "
                      f"Materials: {_fmt(totals['total_material_cost'])}  "
                      f"Total: {_fmt(totals['grand_total'])}  "
                      f"Time: {_format_time(totals['total_time'])}")

                if show_profit:
                    upgraded_id = f"{pet_type};{max_rarity}"
                    start_id = f"{pet_type};{min_rarity}"
                    sell = price_cache.get_price(upgraded_id)
                    buy = price_cache.get_price(start_id)
                    buy_cost = (buy.get("lowest_bin") or 0) if buy["source"] != "unknown" else 0
                    sell_val = (sell.get("avg_bin") or sell.get("lowest_bin") or 0) if sell["source"] != "unknown" else 0
                    if sell_val > 0:
                        profit = sell_val * 0.99 - (buy_cost + totals["grand_total"])
                        print(f"    Buy {RARITY_NAME[min_rarity]}: {_fmt(buy_cost)}  "
                              f"Sell {RARITY_NAME[max_rarity]}: {_fmt(sell_val)}  "
                              f"Profit: {_fmt(profit)}")

    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SkyBlock Kat upgrade calculator")
    parser.add_argument("pet", type=str, help="Pet type (e.g., RABBIT, BEE, ELEPHANT)")
    parser.add_argument("--from", dest="from_rarity", type=str, default=None,
                        help="Starting rarity (common/uncommon/rare/epic/legendary)")
    parser.add_argument("--to", dest="to_rarity", type=str, default=None,
                        help="Target rarity (uncommon/rare/epic/legendary/mythic)")
    parser.add_argument("--profit", action="store_true",
                        help="Show profit analysis (AH buy/sell comparison)")
    args = parser.parse_args()

    pet_type = args.pet.upper()
    price_cache = PriceCache()

    if args.from_rarity and args.to_rarity:
        from_num = RARITY_NUM.get(args.from_rarity.lower())
        to_num = RARITY_NUM.get(args.to_rarity.lower())
        if from_num is None:
            print(f"  Unknown rarity: {args.from_rarity}", file=sys.stderr)
            print(f"  Valid: {', '.join(RARITY_NUM.keys())}", file=sys.stderr)
            sys.exit(1)
        if to_num is None:
            print(f"  Unknown rarity: {args.to_rarity}", file=sys.stderr)
            print(f"  Valid: {', '.join(RARITY_NUM.keys())}", file=sys.stderr)
            sys.exit(1)
        if from_num >= to_num:
            print(f"  --from rarity must be lower than --to rarity", file=sys.stderr)
            sys.exit(1)
        show_upgrade(pet_type, from_num, to_num, price_cache, show_profit=args.profit)
    else:
        show_all_upgrades(pet_type, price_cache, show_profit=args.profit)

    price_cache.flush()


if __name__ == "__main__":
    main()
