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
    python3 kat.py --scan                                    # Scan all pets, rank by profit
    python3 kat.py SKELETON --shopping                       # Consolidated shopping list
    python3 kat.py RABBIT --from common --to mythic --shopping   # Shopping list with range
"""

import sys
from pathlib import Path

from items import display_name, _load_neu_item
from pricing import PriceCache, RARITY_NUM, RARITY_NAME, _fmt

DATA_DIR = Path(__file__).parent.parent / "data"
NEU_ITEMS_DIR = DATA_DIR / "neu-repo" / "items"


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
        try:
            return parts[0], int(parts[1])
        except ValueError:
            return parts[0], 1
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
    has_unpriced = False
    for item_id, qty in sorted(all_items.items()):
        p = price_cache.get_price(item_id)
        if p["source"] == "bazaar" and p.get("buy"):
            unit_price = p["buy"]
        elif p["source"] == "auction" and p.get("lowest_bin"):
            unit_price = p["lowest_bin"]
        else:
            unit_price = 0
            has_unpriced = True
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
        "has_unpriced": has_unpriced,
    }


def get_craft_recipe(pet_type, rarity_num):
    """Get the crafting recipe for a pet at a specific rarity.

    Returns dict of {item_id: qty} or None if no crafting recipe exists.
    """
    pet_id = f"{pet_type};{rarity_num}"
    data = _load_neu_item(pet_id)
    if not data:
        return None

    for recipe in data.get("recipes", []):
        if recipe.get("type") == "crafting":
            items = {}
            for slot in ("A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3"):
                slot_val = recipe.get(slot, "")
                if not slot_val:
                    continue
                item_id, qty = _parse_item_str(slot_val)
                items[item_id] = items.get(item_id, 0) + qty
            return items
    return None


def _get_craft_cost(pet_type, rarity_num, price_cache):
    """Calculate the total Bazaar cost to craft a pet. Returns cost or None."""
    recipe = get_craft_recipe(pet_type, rarity_num)
    if not recipe:
        return None
    total = 0
    for item_id, qty in recipe.items():
        p = price_cache.get_price(item_id)
        if p["source"] == "bazaar" and p.get("buy"):
            total += p["buy"] * qty
        elif p["source"] == "auction" and p.get("lowest_bin"):
            total += p["lowest_bin"] * qty
        else:
            return None  # Can't price an ingredient — craft cost unknown
    return total


def _get_input_cost(pet_type, from_rarity, price_cache):
    """Get the cheapest way to obtain the starting pet: min(AH LBIN, craft cost).

    Returns (cost, source_label) where source_label is "AH" or "craft".
    """
    # AH price
    start_id = f"{pet_type};{from_rarity}"
    buy = price_cache.get_price(start_id)
    ah_cost = (buy.get("lowest_bin") or 0) if buy["source"] != "unknown" else 0

    # Craft cost
    craft_cost = _get_craft_cost(pet_type, from_rarity, price_cache)

    if craft_cost is not None and craft_cost > 0:
        if ah_cost > 0:
            if craft_cost < ah_cost:
                return craft_cost, "craft"
            else:
                return ah_cost, "AH"
        else:
            return craft_cost, "craft"
    elif ah_cost > 0:
        return ah_cost, "AH"
    else:
        return 0, "?"


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
            if sales is None or sales < 0.5:
                print(f"  ⚠ This rarity has very low AH volume — selling may take a long time")

            # Get cheapest input cost (AH vs craft)
            input_cost, input_source = _get_input_cost(pet_type, from_rarity, price_cache)
            craft_cost = _get_craft_cost(pet_type, from_rarity, price_cache)
            start_id = f"{pet_type};{from_rarity}"
            buy = price_cache.get_price(start_id)
            ah_lbin = (buy.get("lowest_bin") or 0) if buy["source"] != "unknown" else 0

            # Show both prices when craft exists
            if craft_cost is not None and ah_lbin > 0:
                using = "craft" if input_source == "craft" else "AH"
                print(f"  {from_name} {pet_display}:  AH LBIN {_fmt(ah_lbin)} | Craft {_fmt(craft_cost)}  <- using {using}")
            elif craft_cost is not None:
                print(f"  {from_name} {pet_display}:  Craft {_fmt(craft_cost)}")
            elif ah_lbin > 0:
                print(f"  {from_name} {pet_display} AH:  LBIN {_fmt(ah_lbin)}")

            # Profit = sell_price * 0.99 - (input_cost + grand_total)
            sell_val = avg or lbin or 0
            if sell_val > 0:
                profit = sell_val * 0.99 - (input_cost + totals["grand_total"])
                profit_str = f"  Profit:  {_fmt(profit)}"
                warnings = []
                if totals.get("has_unpriced"):
                    warnings.append("some materials unpriced")
                if input_cost == 0:
                    warnings.append("input pet cost unknown")
                if warnings:
                    profit_str += f"  ⚠ ({', '.join(warnings)})"
                print(profit_str)
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
                    input_cost, input_source = _get_input_cost(pet_type, min_rarity, price_cache)
                    sell_val = (sell.get("avg_bin") or sell.get("lowest_bin") or 0) if sell["source"] != "unknown" else 0

                    craft_cost = _get_craft_cost(pet_type, min_rarity, price_cache)
                    buy = price_cache.get_price(start_id)
                    ah_cost = (buy.get("lowest_bin") or 0) if buy["source"] != "unknown" else 0

                    # Show input cost with craft alternative if available
                    cost_parts = []
                    if ah_cost > 0:
                        cost_parts.append(f"AH {_fmt(ah_cost)}")
                    if craft_cost is not None:
                        cost_parts.append(f"Craft {_fmt(craft_cost)}")
                    buy_str = " | ".join(cost_parts) if cost_parts else "?"

                    if sell_val > 0:
                        profit = sell_val * 0.99 - (input_cost + totals["grand_total"])
                        print(f"    Buy {RARITY_NAME[min_rarity]}: {buy_str}  "
                              f"Sell {RARITY_NAME[max_rarity]}: {_fmt(sell_val)}  "
                              f"Profit: {_fmt(profit)}")

    print()


# ─── Scan Mode ────────────────────────────────────────────────────────

def _discover_pet_types():
    """Find all pet types by scanning NEU repo for *;0.json files."""
    pet_types = []
    for path in sorted(NEU_ITEMS_DIR.glob("*;0.json")):
        pet_type = path.stem.split(";")[0]
        pet_types.append(pet_type)
    return pet_types


def scan_all_pets(price_cache):
    """Scan all pets with katgrade recipes, rank by full-chain profit."""
    pet_types = _discover_pet_types()
    print(f"  Scanning {len(pet_types)} pet types...", file=sys.stderr)

    results = []
    for pet_type in pet_types:
        available = get_available_rarities(pet_type)
        if not available:
            continue

        # Find katgrade upgrades
        upgrades = []
        for rarity in available:
            if _find_katgrade(pet_type, rarity):
                upgrades.append(rarity)
        if not upgrades:
            continue

        # Full chain: lowest available -> highest katgrade output
        min_rarity = upgrades[0] - 1
        max_rarity = upgrades[-1]

        chain = get_kat_chain(pet_type, min_rarity, max_rarity)
        if not chain:
            continue

        totals = calculate_total(chain, price_cache)

        # Sell price of end pet
        sell = price_cache.get_price(f"{pet_type};{max_rarity}")
        if sell["source"] == "unknown":
            continue
        sell_val = sell.get("avg_bin") or sell.get("lowest_bin") or 0
        if sell_val <= 0:
            continue
        sales_day = sell.get("sales_day")

        # Input cost: min(AH, craft)
        input_cost, input_source = _get_input_cost(pet_type, min_rarity, price_cache)

        profit = sell_val * 0.99 - (input_cost + totals["grand_total"])

        results.append({
            "pet_type": pet_type,
            "from_rarity": min_rarity,
            "to_rarity": max_rarity,
            "input_cost": input_cost,
            "input_source": input_source,
            "kat_total": totals["grand_total"],
            "sell_val": sell_val,
            "profit": profit,
            "time": totals["total_time"],
            "sales_day": sales_day,
        })

    # Sort by profit descending
    results.sort(key=lambda r: r["profit"], reverse=True)

    # Partition by liquidity
    liquid = [r for r in results if r["sales_day"] is not None and r["sales_day"] >= 0.5]
    illiquid = [r for r in results if r["sales_day"] is None or r["sales_day"] < 0.5]

    def _print_scan_table(rows, header):
        print()
        print(f"  {header}")
        w = 95
        print(f"  {'═' * w}")
        print(f"  {'Pet':<20s} {'Path':<22s} {'Input':>8s} {'Kat':>8s} {'Sell':>8s} {'Profit':>8s} {'Time':>8s} {'Sales':>6s}")
        print(f"  {'─' * 20} {'─' * 22} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 6}")

        for r in rows:
            pet_display = r["pet_type"].replace("_", " ").title()
            if len(pet_display) > 19:
                pet_display = pet_display[:16] + "..."
            from_name = RARITY_NAME[r["from_rarity"]]
            to_name = RARITY_NAME[r["to_rarity"]]
            path = f"{from_name} -> {to_name}"

            # Flag craft-sourced input
            input_str = _fmt(r["input_cost"])
            if r["input_source"] == "craft":
                input_str += "*"

            sales_str = f"{r['sales_day']:.0f}/d" if r["sales_day"] else "?"

            print(f"  {pet_display:<20s} {path:<22s} {input_str:>8s} {_fmt(r['kat_total']):>8s} "
                  f"{_fmt(r['sell_val']):>8s} {_fmt(r['profit']):>8s} {_format_time(r['time']):>8s} {sales_str:>6s}")

    _print_scan_table(liquid, "KAT FLIPS (full chain, sorted by profit)")

    if illiquid:
        _print_scan_table(illiquid, "⚠ LOW LIQUIDITY (may take days/weeks to sell)")

    print()
    notes = []
    if any(r["input_source"] == "craft" for r in results):
        notes.append('* = input pet priced via crafting recipe (cheaper than AH)')
    notes.append('Sales "?" = no recent AH data. High profit + low liquidity = high risk.')
    for note in notes:
        print(f"  {note}")
    print()


# ─── Shopping List ────────────────────────────────────────────────────

def show_shopping_list(pet_type, from_rarity, to_rarity, price_cache):
    """Show a consolidated shopping list combining craft recipe + Kat materials."""
    from_name = RARITY_NAME.get(from_rarity, str(from_rarity))
    to_name = RARITY_NAME.get(to_rarity, str(to_rarity))
    pet_display = pet_type.replace("_", " ").title()

    chain = get_kat_chain(pet_type, from_rarity, to_rarity)
    if not chain:
        print(f"\n  No Kat upgrade path found for {pet_display}: {from_name} -> {to_name}")
        return

    totals = calculate_total(chain, price_cache)

    # Merge materials: craft recipe + Kat upgrade materials
    all_items = {}  # item_id -> qty

    # Check if crafting the starting pet is cheaper than buying
    craft_recipe = get_craft_recipe(pet_type, from_rarity)
    craft_cost = _get_craft_cost(pet_type, from_rarity, price_cache)
    input_cost, input_source = _get_input_cost(pet_type, from_rarity, price_cache)

    include_craft = craft_recipe is not None and input_source == "craft"

    if include_craft:
        for item_id, qty in craft_recipe.items():
            all_items[item_id] = all_items.get(item_id, 0) + qty

    # Add Kat upgrade materials
    for mat in totals["materials"]:
        item_id = mat["item_id"]
        all_items[item_id] = all_items.get(item_id, 0) + mat["qty"]

    # Price everything
    material_lines = []
    materials_total = 0
    for item_id, qty in sorted(all_items.items()):
        p = price_cache.get_price(item_id)
        if p["source"] == "bazaar" and p.get("buy"):
            unit_price = p["buy"]
            source = "Bazaar"
        elif p["source"] == "auction" and p.get("lowest_bin"):
            unit_price = p["lowest_bin"]
            source = "AH"
        else:
            unit_price = 0
            source = "?"
        line_total = unit_price * qty
        materials_total += line_total
        material_lines.append({
            "item_id": item_id,
            "qty": qty,
            "unit_price": unit_price,
            "total": line_total,
            "source": source,
        })

    # Print
    title = f"Shopping List: {pet_display} ({from_name} -> {to_name})"
    if include_craft:
        title += "  [crafting pet]"
    else:
        title += "  [buying pet from AH]"

    print()
    print(f"  {title}")
    w = 80
    print(f"  {'═' * w}")
    print(f"  {'Item':<30s} {'Qty':>6s} {'Price Each':>12s} {'Total':>10s}  {'Source':<8s}")
    print(f"  {'─' * 30} {'─' * 6} {'─' * 12} {'─' * 10}  {'─' * 8}")

    for mat in material_lines:
        name = display_name(mat["item_id"])
        if len(name) > 29:
            name = name[:26] + "..."
        if mat["unit_price"] > 0:
            print(f"  {name:<30s} {mat['qty']:>6,d} {_fmt(mat['unit_price']):>12s} {_fmt(mat['total']):>10s}  {mat['source']:<8s}")
        else:
            print(f"  {name:<30s} {mat['qty']:>6,d} {'?':>12s} {'?':>10s}  {mat['source']:<8s}")

    print(f"  {'─' * 30} {'─' * 6} {'─' * 12} {'─' * 10}  {'─' * 8}")
    print(f"  {'Materials subtotal:':<49s} {_fmt(materials_total):>10s}")

    if not include_craft:
        print(f"  {'Buy pet from AH:':<49s} {_fmt(input_cost):>10s}")

    kat_coins = totals["total_coins"]
    step_count = len(chain)
    s = "s" if step_count != 1 else ""
    kat_label = f"Kat coins ({step_count} upgrade{s}):"
    print(f"  {kat_label:<49s} {_fmt(kat_coins):>10s}")

    total_cost = materials_total + kat_coins + (0 if include_craft else input_cost)
    print(f"  {'─' * 30} {'─' * 6} {'─' * 12} {'─' * 10}  {'─' * 8}")
    print(f"  {'TOTAL COST:':<49s} {_fmt(total_cost):>10s}")

    # Sell price + profit
    upgraded_id = f"{pet_type};{to_rarity}"
    sell = price_cache.get_price(upgraded_id)
    if sell["source"] != "unknown":
        sell_val = sell.get("avg_bin") or sell.get("lowest_bin") or 0
        if sell_val > 0:
            print(f"  {f'Sell {to_name} {pet_display} (avg):':<49s} {_fmt(sell_val):>10s}")
            profit = sell_val * 0.99 - total_cost
            print(f"  {'PROFIT:':<49s} {_fmt(profit):>10s}")

    print(f"  {'Kat Time:':<49s} {_format_time(totals['total_time']):>10s}")
    print()


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SkyBlock Kat upgrade calculator")
    parser.add_argument("pet", type=str, nargs="?", default=None,
                        help="Pet type (e.g., RABBIT, BEE, ELEPHANT)")
    parser.add_argument("--from", dest="from_rarity", type=str, default=None,
                        help="Starting rarity (common/uncommon/rare/epic/legendary)")
    parser.add_argument("--to", dest="to_rarity", type=str, default=None,
                        help="Target rarity (uncommon/rare/epic/legendary/mythic)")
    parser.add_argument("--profit", action="store_true",
                        help="Show profit analysis (AH buy/sell comparison)")
    parser.add_argument("--scan", action="store_true",
                        help="Scan all pets and rank by profit")
    parser.add_argument("--shopping", action="store_true",
                        help="Show consolidated shopping list")
    args = parser.parse_args()

    # --scan and --shopping imply --profit
    if args.scan or args.shopping:
        args.profit = True

    # Validate: need pet unless --scan
    if not args.scan and not args.pet:
        parser.error("pet is required unless --scan is used")

    price_cache = PriceCache()

    if args.scan:
        scan_all_pets(price_cache)
    elif args.shopping:
        pet_type = args.pet.upper()
        # Determine from/to rarities
        if args.from_rarity and args.to_rarity:
            from_num = RARITY_NUM.get(args.from_rarity.lower())
            to_num = RARITY_NUM.get(args.to_rarity.lower())
            if from_num is None:
                print(f"  Unknown rarity: {args.from_rarity}", file=sys.stderr)
                sys.exit(1)
            if to_num is None:
                print(f"  Unknown rarity: {args.to_rarity}", file=sys.stderr)
                sys.exit(1)
            if from_num >= to_num:
                print(f"  --from rarity must be lower than --to rarity", file=sys.stderr)
                sys.exit(1)
        else:
            # Auto-detect full chain
            available = get_available_rarities(pet_type)
            upgrades = [r for r in available if _find_katgrade(pet_type, r)]
            if not upgrades:
                print(f"  No Kat upgrades available for {pet_type.replace('_', ' ').title()}")
                sys.exit(1)
            from_num = upgrades[0] - 1
            to_num = upgrades[-1]
        show_shopping_list(pet_type, from_num, to_num, price_cache)
    else:
        pet_type = args.pet.upper()
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
