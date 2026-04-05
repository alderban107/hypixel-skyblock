#!/usr/bin/env python3
"""Unified flip scanner for Hypixel SkyBlock.

Finds profitable transformations: buy inputs, transform, sell outputs.
Covers craft flips, forge recipes, sell-order flips, Kat pet upgrades,
NPC buy→sell, and bit shop value ranking.

Uses recursive craft cost optimization by default — if an ingredient is
cheaper to craft than buy, that cascades through all recipes using it.

Usage:
    python3 flips.py                          # All flip types
    python3 flips.py craft                    # Craft flips only
    python3 flips.py forge                    # Forge flips only
    python3 flips.py sell-order               # Bazaar sell-order flips
    python3 flips.py kat                      # Kat pet upgrade flips
    python3 flips.py npc                      # NPC buy → market sell
    python3 flips.py bits                     # Bit shop items by coins/bit

    python3 flips.py --profile                # Filter by player unlocks
    python3 flips.py --item ITEM_ID           # Single item breakdown
    python3 flips.py --item ITEM_ID --check   # + requirement check
    python3 flips.py --no-recursive           # Disable recursive costing
    python3 flips.py --undercut 8             # Undercut % for AH items
    python3 flips.py --cached / --fresh       # Cache control
"""

import argparse
import sys

from items import (display_name, check_requirements, search_items,
                   _load_profile_member)
from pricing import PriceCache, _fmt, RARITY_NAME

from flip_engine import (
    CostEngine, parse_recipes, parse_forge_recipes,
    filter_bazaar_ingredient_recipes,
    scan_craft_flips, scan_forge_flips, scan_sell_order_flips,
    scan_kat_flips, scan_npc_flips, scan_bit_flips,
    find_recipe, load_craft_cache, save_craft_cache,
    fetch_moulberry_data, supply_indicator,
    MIN_PROFIT, MIN_VOLUME, MIN_BUY_VOLUME,
)


# ─── Display Helpers ─────────────────────────────────────────────────

def _format_duration(seconds):
    """Format duration in human-readable form."""
    if seconds is None or seconds <= 0:
        return ""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    if days > 0:
        return f"{days}d {hours}h" if hours else f"{days}d"
    if hours > 0:
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    return f"{minutes}m"


def _sales_str(spd):
    if spd is None:
        return "∞"
    if spd >= 10:
        return f"{spd:.0f}/d"
    return f"{spd:.1f}/d"


def _trunc(name, width):
    if len(name) > width:
        return name[:width - 3] + "..."
    return name


# ─── Print: Instant Flips ────────────────────────────────────────────

def print_instant_flips(flips, title="INSTANT FLIPS"):
    """Print table of instant flips (craft, npc)."""
    print(f"\n{title} (min {_fmt(MIN_PROFIT)} profit)")
    print("=" * 115)
    print(f"  {'Item':<30s} {'Type':<6s} {'Cost':>10s}  {'Sell':>10s}  "
          f"{'Profit':>10s} {'Sales':>6s} {'Mkt':>3s}  {'Via':>3s}  Requirement")
    print(f"  {'-'*30} {'-'*6} {'-'*10}  {'-'*10}  "
          f"{'-'*10} {'-'*6} {'-'*3}  {'-'*3}  {'-'*20}")

    for flip in flips:
        name = _trunc(display_name(flip["item_id"]), 30)
        req_text = flip["requirement"]["text"] if flip.get("requirement") else ""
        spd = _sales_str(flip.get("sales_per_day"))
        channel = "BZ" if flip.get("sell_channel") == "bazaar" else "AH"
        supply = flip.get("supply", "")
        ftype = flip["type"]

        print(f"  {name:<30s} {ftype:<6s} {_fmt(flip['cost']):>10s}  "
              f"{_fmt(flip['sell_price']):>10s}  {_fmt(flip['profit']):>10s} "
              f"{spd:>6s} {supply:>3s}  {channel:>3s}  {req_text}")

    if not flips:
        print("  No profitable instant flips found.")
    print()


def print_instant_flips_profile(flips, member):
    """Print instant flips filtered by player unlocks."""
    unlocked, almost = _split_by_requirements(flips, member)

    print(f"\nUNLOCKED INSTANT FLIPS")
    print("=" * 100)
    if unlocked:
        print(f"  {'Item':<30s} {'Type':<6s} {'Cost':>10s}  {'Sell':>10s}  "
              f"{'Profit':>10s} {'Sales':>6s} {'Mkt':>3s}  {'Via':>3s}")
        print(f"  {'-'*30} {'-'*6} {'-'*10}  {'-'*10}  "
              f"{'-'*10} {'-'*6} {'-'*3}  {'-'*3}")
        for flip in unlocked:
            name = _trunc(display_name(flip["item_id"]), 30)
            spd = _sales_str(flip.get("sales_per_day"))
            channel = "BZ" if flip.get("sell_channel") == "bazaar" else "AH"
            supply = flip.get("supply", "")
            print(f"  {name:<30s} {flip['type']:<6s} {_fmt(flip['cost']):>10s}  "
                  f"{_fmt(flip['sell_price']):>10s}  {_fmt(flip['profit']):>10s} "
                  f"{spd:>6s} {supply:>3s}  {channel:>3s}")
    else:
        print("  No unlocked profitable instant flips found.")
    print()

    _print_almost_unlocked(almost)


def _split_by_requirements(flips, member):
    """Split flips into unlocked and almost-unlocked lists."""
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

    return unlocked, almost


def _print_almost_unlocked(almost, limit=10):
    """Print almost-unlocked section."""
    if not almost:
        return

    almost.sort(key=lambda x: x["pct"], reverse=True)
    almost = almost[:limit]

    print(f"ALMOST UNLOCKED (sorted by proximity)")
    print("=" * 88)
    print(f"  {'Item':<26s} {'Type':<6s} {'Profit':>8s}  {'Requirement':<22s} Progress")
    print(f"  {'-'*26} {'-'*6} {'-'*8}  {'-'*22} {'-'*20}")
    for flip in almost:
        name = _trunc(display_name(flip["item_id"]), 26)
        req_text = _trunc(flip.get("req_text", ""), 22)
        prog_str = f"{_fmt(flip['progress'])} / {_fmt(flip['needed'])}"
        if flip.get("req_type") == "SLAYER":
            prog_str += " XP"
        pct_str = f"({flip['pct']*100:.0f}%)"
        print(f"  {name:<26s} {flip['type']:<6s} {_fmt(flip['profit']):>8s}  "
              f"{req_text:<22s} {prog_str} {pct_str}")
    print()


# ─── Print: Time-Gated Flips ─────────────────────────────────────────

def print_time_gated_flips(flips, title="TIME-GATED FLIPS"):
    """Print table of time-gated flips (forge, kat), sorted by profit/hour."""
    print(f"\n{title} (min {_fmt(MIN_PROFIT)} profit)")
    print("=" * 120)
    print(f"  {'Item':<28s} {'Type':<6s} {'Cost':>10s}  {'Sell':>10s}  "
          f"{'Profit':>10s} {'Profit/hr':>10s} {'Time':>8s} {'Sales':>6s} {'Mkt':>3s}  {'Via':>3s}")
    print(f"  {'-'*28} {'-'*6} {'-'*10}  {'-'*10}  "
          f"{'-'*10} {'-'*10} {'-'*8} {'-'*6} {'-'*3}  {'-'*3}")

    for flip in flips:
        if flip["type"] == "kat":
            pet_type = flip.get("pet_type", "")
            from_r = RARITY_NAME.get(flip.get("from_rarity", -1), "?")
            to_r = RARITY_NAME.get(flip.get("to_rarity", -1), "?")
            name = f"{pet_type.replace('_', ' ').title()} {from_r[0]}→{to_r[0]}"
        else:
            name = display_name(flip["item_id"])
        name = _trunc(name, 28)

        spd = _sales_str(flip.get("sales_per_day"))
        channel = "BZ" if flip.get("sell_channel") == "bazaar" else "AH"
        supply = flip.get("supply", "")
        dur = _format_duration(flip.get("time_cost"))
        pph = _fmt(flip["profit_per_hour"]) if flip.get("profit_per_hour") else ""

        print(f"  {name:<28s} {flip['type']:<6s} {_fmt(flip['cost']):>10s}  "
              f"{_fmt(flip['sell_price']):>10s}  {_fmt(flip['profit']):>10s} "
              f"{pph:>10s} {dur:>8s} {spd:>6s} {supply:>3s}  {channel:>3s}")

    if not flips:
        print("  No profitable time-gated flips found.")
    print()


def print_time_gated_flips_profile(flips, member):
    """Print time-gated flips filtered by player unlocks."""
    unlocked, almost = _split_by_requirements(flips, member)

    print(f"\nUNLOCKED TIME-GATED FLIPS")
    print("=" * 115)
    if unlocked:
        print(f"  {'Item':<28s} {'Type':<6s} {'Cost':>10s}  {'Sell':>10s}  "
              f"{'Profit':>10s} {'Profit/hr':>10s} {'Time':>8s} {'Sales':>6s} {'Mkt':>3s}  {'Via':>3s}")
        print(f"  {'-'*28} {'-'*6} {'-'*10}  {'-'*10}  "
              f"{'-'*10} {'-'*10} {'-'*8} {'-'*6} {'-'*3}  {'-'*3}")
        for flip in unlocked:
            if flip["type"] == "kat":
                pet_type = flip.get("pet_type", "")
                from_r = RARITY_NAME.get(flip.get("from_rarity", -1), "?")
                to_r = RARITY_NAME.get(flip.get("to_rarity", -1), "?")
                name = f"{pet_type.replace('_', ' ').title()} {from_r[0]}→{to_r[0]}"
            else:
                name = display_name(flip["item_id"])
            name = _trunc(name, 28)

            spd = _sales_str(flip.get("sales_per_day"))
            channel = "BZ" if flip.get("sell_channel") == "bazaar" else "AH"
            supply = flip.get("supply", "")
            dur = _format_duration(flip.get("time_cost"))
            pph = _fmt(flip["profit_per_hour"]) if flip.get("profit_per_hour") else ""

            print(f"  {name:<28s} {flip['type']:<6s} {_fmt(flip['cost']):>10s}  "
                  f"{_fmt(flip['sell_price']):>10s}  {_fmt(flip['profit']):>10s} "
                  f"{pph:>10s} {dur:>8s} {spd:>6s} {supply:>3s}  {channel:>3s}")
    else:
        print("  No unlocked profitable time-gated flips found.")
    print()

    _print_almost_unlocked(almost)


# ─── Print: Sell-Order Flips ─────────────────────────────────────────

def print_sell_order_flips(flips):
    """Print table of sell-order bazaar flips."""
    print(f"\nSELL-ORDER FLIPS (min {_fmt(MIN_PROFIT)} profit, min {MIN_BUY_VOLUME} buy volume)")
    print("  Buy materials instantly, craft, place sell order.")
    print("  ⚠ = spread >60%, likely contested (undercutting wars, slow fills)")
    print("=" * 120)
    print(f"  {'Item':<30s} {'Cost':>10s}  {'Order @':>10s}  {'Profit':>10s}  "
          f"{'Spread':>7s}  {'BuyVol':>8s}  {'Mkt':>3s}  Requirement")
    print(f"  {'-'*30} {'-'*10}  {'-'*10}  {'-'*10}  "
          f"{'-'*7}  {'-'*8}  {'-'*3}  {'-'*20}")

    for flip in flips:
        name = _trunc(display_name(flip["item_id"]), 30)
        req_text = flip["requirement"]["text"] if flip.get("requirement") else ""
        warn = "⚠" if flip.get("contested") else " "
        spread_str = f"{warn}{flip['spread_pct']:.0f}%"
        bvol_str = f"{flip['buy_volume']:,}"
        supply = flip.get("supply", "")
        print(f"  {name:<30s} {_fmt(flip['cost']):>10s}  {_fmt(flip['sell_price']):>10s}  "
              f"{_fmt(flip['profit']):>10s}  {spread_str:>7s}  {bvol_str:>8s}  {supply:>3s}  {req_text}")

    if not flips:
        print("  No profitable sell-order flips found.")
    else:
        print(f"\n  Profit = OrderPrice × 0.98875 (bazaar tax) − Cost.")
        print(f"  Spread = gap between instant-buy and instant-sell.")
    print()


def print_sell_order_flips_profile(flips, member):
    """Print sell-order flips filtered by player unlocks."""
    unlocked, almost = _split_by_requirements(flips, member)

    print(f"\nUNLOCKED SELL-ORDER FLIPS")
    print("  Buy materials instantly, craft, place sell order.")
    print("  ⚠ = spread >60%, likely contested (undercutting wars, slow fills)")
    print("=" * 110)
    if unlocked:
        print(f"  {'Item':<30s} {'Cost':>10s}  {'Order @':>10s}  {'Profit':>10s}  "
              f"{'Spread':>7s}  {'BuyVol':>8s}  {'Mkt':>3s}")
        print(f"  {'-'*30} {'-'*10}  {'-'*10}  {'-'*10}  "
              f"{'-'*7}  {'-'*8}  {'-'*3}")
        for flip in unlocked:
            name = _trunc(display_name(flip["item_id"]), 30)
            warn = "⚠" if flip.get("contested") else " "
            spread_str = f"{warn}{flip['spread_pct']:.0f}%"
            bvol_str = f"{flip['buy_volume']:,}"
            supply = flip.get("supply", "")
            print(f"  {name:<30s} {_fmt(flip['cost']):>10s}  {_fmt(flip['sell_price']):>10s}  "
                  f"{_fmt(flip['profit']):>10s}  {spread_str:>7s}  {bvol_str:>8s}  {supply:>3s}")
    else:
        print("  No unlocked profitable sell-order flips found.")
    print()

    _print_almost_unlocked(almost)


# ─── Print: Bit Shop ─────────────────────────────────────────────────

def print_bit_flips(results):
    """Print bit shop value ranking."""
    print(f"\nBIT SHOP VALUE (sorted by coins/bit)")
    print("=" * 75)
    print(f"  {'Item':<30s} {'Bits':>8s}  {'Market':>10s}  {'Coins/Bit':>10s}")
    print(f"  {'-'*30} {'-'*8}  {'-'*10}  {'-'*10}")

    for r in results:
        name = _trunc(display_name(r["item_id"]), 30)
        print(f"  {name:<30s} {r['bit_cost']:>8,d}  {_fmt(r['market_price']):>10s}  "
              f"{r['coins_per_bit']:>10,.1f}")

    if not results:
        print("  No bit shop data available.")
    print()


# ─── Single Item Breakdown ───────────────────────────────────────────

def show_item_breakdown(item_id, engine, price_cache, do_check=False, undercut_pct=5,
                        forge_recipes=None):
    """Show a full recipe breakdown for a single item with recursive cost info."""
    from items import get_all_requirements

    item_id = item_id.upper()
    name = display_name(item_id)

    # Search crafting recipes first, then forge recipes
    recipe = find_recipe(item_id)
    is_forge = False
    if not recipe and forge_recipes:
        for fr in forge_recipes:
            if fr["item_id"] == item_id:
                recipe = fr
                is_forge = True
                break
    if not recipe:
        matches = search_items(item_id)
        craftable = []
        for m in matches:
            mid = m.get("id", "")
            if mid and mid != item_id:
                r = find_recipe(mid)
                if r:
                    craftable.append((mid, display_name(mid)))
                elif forge_recipes:
                    for fr in forge_recipes:
                        if fr["item_id"] == mid:
                            craftable.append((mid, display_name(mid)))
                            break
        if craftable:
            print(f"\n  No exact recipe for '{item_id}'. Did you mean:")
            for mid, mname in craftable[:8]:
                print(f"    {mname:40s} --item {mid}")
            return
        print(f"\n  No recipe found for {name} ({item_id})")
        return

    recipe_type = "Forge" if is_forge else "Recipe"
    print(f"\n  {recipe_type}: {name}")
    if is_forge and recipe.get("duration"):
        print(f"  Forge Time: {_format_duration(recipe['duration'])}")

    # Requirements
    reqs = get_all_requirements(item_id)
    if reqs:
        for r in reqs:
            source_tag = f" [{r['source']}]" if r.get("source") else ""
            print(f"  Requirement: {r['text']}{source_tag}")

    if do_check:
        checked = check_requirements(item_id)
        if checked:
            for r in checked:
                status = "✓" if r["met"] else "✗"
                if r["type"] == "COLLECTION":
                    prog_str = f"{_fmt(r['progress'])} / {_fmt(r['needed'])}"
                elif r["type"] == "SLAYER":
                    prog_str = f"{_fmt(r['progress'])} / {_fmt(r['needed'])} XP"
                else:
                    prog_str = f"{r['progress']} / {r['needed']}"
                print(f"    {status} {r['text']} -- {prog_str}")
        elif reqs:
            print("    (no profile data -- run profile.py first)")

    # Ingredient breakdown with recursive cost info
    print()
    print(f"  {'Ingredient':<30s} {'Qty':>6s} {'Price':>10s} {'Total':>12s}  Source")
    print(f"  {'─' * 30} {'─' * 6} {'─' * 10} {'─' * 12}  {'─' * 12}")

    total_cost = 0
    for ing_id, qty in sorted(recipe["ingredients"].items()):
        cost, source, breakdown = engine.get_cost(ing_id)
        ing_name = _trunc(display_name(ing_id), 30)

        if cost is not None and cost > 0:
            line_total = cost * qty
            total_cost += line_total
            source_label = source
            if source == "craft":
                source_label = "craft ←"
            print(f"  {ing_name:<30s} {qty:>6,d} {_fmt(cost):>10s} {_fmt(line_total):>12s}  {source_label}")

            # If this ingredient is crafted, show sub-ingredients
            if breakdown:
                for sub_id, (sub_qty, sub_cost, sub_source) in sorted(breakdown.items()):
                    sub_name = _trunc(display_name(sub_id), 26)
                    sub_total_per = sub_cost * sub_qty
                    total_needed = sub_qty * qty
                    print(f"    └ {sub_name:<26s} {total_needed:>6,d} {_fmt(sub_cost):>10s} "
                          f"{_fmt(sub_total_per * qty):>12s}  {sub_source}")
        else:
            print(f"  {ing_name:<30s} {qty:>6,d} {'?':>10s} {'?':>12s}")

    # Output count
    if recipe["output_count"] > 1:
        total_cost_per = total_cost / recipe["output_count"]
        print(f"  {'':>30s} {'':>6s} {'':>10s} {'─' * 12}")
        print(f"  {'Total craft cost':>30s} {'':>6s} {'':>10s} {_fmt(total_cost):>12s}")
        oc = recipe['output_count']
        print(f"  {f'Per item ({oc}x output)':>30s} {'':>6s} {'':>10s} {_fmt(total_cost_per):>12s}")
    else:
        total_cost_per = total_cost
        print(f"  {'':>30s} {'':>6s} {'':>10s} {'─' * 12}")
        print(f"  {'Craft Cost':>30s} {'':>6s} {'':>10s} {_fmt(total_cost):>12s}")

    # Sell price
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
        indicator = supply_indicator(item_id, price_cache, "auction", sales)
        parts.append(f"[{indicator}]")
        print(f"  AH Sell:  {' '.join(parts)}")

        sell_mult = (1 - undercut_pct / 100) * 0.99
        pct_label = f"-{undercut_pct:g}%"
        if avg and total_cost_per > 0:
            profit = avg * sell_mult - total_cost_per
            print(f"  Profit:   {_fmt(profit)} (avg×{sell_mult:.3f} - cost, {pct_label} undercut)")
            if is_forge and recipe.get("duration") and recipe["duration"] > 0:
                pph = profit / (recipe["duration"] / 3600)
                print(f"  Profit/hr: {_fmt(pph)}")
        elif lbin and total_cost_per > 0:
            profit = lbin * sell_mult - total_cost_per
            print(f"  Profit:   {_fmt(profit)} (LBIN×{sell_mult:.3f} - cost, {pct_label} undercut)")
            if is_forge and recipe.get("duration") and recipe["duration"] > 0:
                pph = profit / (recipe["duration"] / 3600)
                print(f"  Profit/hr: {_fmt(pph)}")
    elif sell_price["source"] == "bazaar":
        indicator = supply_indicator(item_id, price_cache, "bazaar")
        print(f"  Bazaar:  {_fmt(sell_price['sell'])} instant-sell / "
              f"{_fmt(sell_price['buy'])} instant-buy  [{indicator}]")
        if sell_price.get("sell") and total_cost_per > 0:
            profit = sell_price["sell"] - total_cost_per
            print(f"  Profit:   {_fmt(profit)} (instant-sell - cost)")
            if is_forge and recipe.get("duration") and recipe["duration"] > 0:
                pph = profit / (recipe["duration"] / 3600)
                print(f"  Profit/hr: {_fmt(pph)}")
    else:
        print(f"  Sell:  No price data")

    print()


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SkyBlock unified flip scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Flip types:
  craft       Craft flips: buy ingredients on bazaar, craft, sell on AH/BZ
  forge       Forge flips: time-gated crafts with mixed-source ingredients
  sell-order  Bazaar sell-order: instant-buy materials, place sell order
  kat         Kat pet upgrades: buy pet, upgrade rarity, sell upgraded pet
  npc         NPC flips: buy from NPC, sell on bazaar/AH
  bits        Bit shop value: rank items by coins/bit

Run with no subcommand to see all flip types in a unified view.
""")
    parser.add_argument("mode", nargs="?", default="all",
                        choices=["all", "craft", "forge", "sell-order",
                                 "kat", "npc", "bits"],
                        help="Flip type to scan (default: all)")
    parser.add_argument("--profile", action="store_true",
                        help="Filter by player unlocks")
    parser.add_argument("--item", type=str, metavar="ITEM_ID",
                        help="Show recipe breakdown for a single item")
    parser.add_argument("--check", action="store_true",
                        help="Check requirements against profile (with --item)")
    parser.add_argument("--no-recursive", action="store_true", dest="no_recursive",
                        help="Disable recursive craft cost optimization")
    parser.add_argument("--all-liquidity", action="store_true", dest="all_liquidity",
                        help="Include illiquid flips (default: hide <0.5 sales/day for AH items)")
    parser.add_argument("--undercut", type=float, default=5, metavar="PCT",
                        help="Undercut LBIN by this %% for AH items (default: 5)")
    parser.add_argument("--cached", action="store_true",
                        help="Use cached prices only")
    parser.add_argument("--fresh", action="store_true",
                        help="Ignore cache, fetch all prices fresh")
    args = parser.parse_args()

    price_cache = PriceCache()
    craft_cache = load_craft_cache()
    recursive = not args.no_recursive

    if args.fresh:
        craft_cache["moulberry"] = {}
        print("  Cleared price cache (--fresh)", file=sys.stderr)

    # ── Single item mode ─────────────────────────────────────────────
    if args.item:
        print("  Parsing recipes...", file=sys.stderr)
        all_recipes = parse_recipes()
        forge_recipes = parse_forge_recipes()
        engine = CostEngine(price_cache, all_recipes + forge_recipes, recursive=recursive)
        if recursive:
            print(f"  Building recursive cost table ({len(all_recipes) + len(forge_recipes)} recipes)...",
                  file=sys.stderr)
            engine.build()
        show_item_breakdown(args.item, engine, price_cache,
                            do_check=args.check, undercut_pct=args.undercut,
                            forge_recipes=forge_recipes)
        price_cache.flush()
        return

    # ── Parse recipes (shared across modes) ──────────────────────────
    need_craft = args.mode in ("all", "craft")
    need_sell_order = args.mode in ("all", "sell-order")
    need_forge = args.mode in ("all", "forge")
    need_kat = args.mode in ("all", "kat")
    need_npc = args.mode in ("all", "npc")
    need_bits = args.mode in ("all", "bits")

    all_recipes = []
    forge_recipes = []

    if need_craft or need_forge or need_sell_order:
        print("  Parsing crafting recipes...", file=sys.stderr)
        all_recipes = parse_recipes()
        print(f"  Found {len(all_recipes)} crafting recipes", file=sys.stderr)

    if need_forge:
        print("  Parsing forge recipes...", file=sys.stderr)
        forge_recipes = parse_forge_recipes()
        print(f"  Found {len(forge_recipes)} forge recipes", file=sys.stderr)

    # ── Build CostEngine ─────────────────────────────────────────────
    # Include both crafting and forge recipes for cost optimization
    engine_recipes = all_recipes + forge_recipes
    engine = CostEngine(price_cache, engine_recipes, recursive=recursive)
    if recursive and engine_recipes:
        print(f"  Building recursive cost table ({len(engine_recipes)} recipes)...",
              file=sys.stderr)
        engine.build()

    # ── Load profile if needed ───────────────────────────────────────
    member = None
    if args.profile:
        member = _load_profile_member()
        if not member:
            print("  Warning: last_profile.json not found. Run profile.py first.",
                  file=sys.stderr)
            print("  Showing unfiltered results.", file=sys.stderr)

    # ── Run scanners ─────────────────────────────────────────────────
    instant_flips = []
    time_gated_flips = []
    sell_order_flips_list = []
    bit_results = []

    # Craft flips
    if need_craft:
        valid = filter_bazaar_ingredient_recipes(all_recipes, price_cache)
        print(f"  {len(valid)} recipes with all-bazaar ingredients", file=sys.stderr)
        craft_flips = scan_craft_flips(valid, engine, price_cache, craft_cache,
                                        use_cached_only=args.cached,
                                        force_refresh=args.fresh,
                                        undercut_pct=args.undercut)
        instant_flips.extend(craft_flips)

    # Sell-order flips
    if need_sell_order:
        if not all_recipes:
            all_recipes = parse_recipes()
        valid_so = filter_bazaar_ingredient_recipes(all_recipes, price_cache)
        so_flips = scan_sell_order_flips(valid_so, engine, price_cache,
                                         undercut_pct=args.undercut)
        sell_order_flips_list.extend(so_flips)

    # Forge flips
    if need_forge:
        f_flips = scan_forge_flips(forge_recipes, engine, price_cache, craft_cache,
                                    use_cached_only=args.cached,
                                    force_refresh=args.fresh,
                                    undercut_pct=args.undercut)
        time_gated_flips.extend(f_flips)

    # Kat flips
    if need_kat:
        kat_flips = scan_kat_flips(price_cache)
        time_gated_flips.extend(kat_flips)

    # NPC flips
    if need_npc:
        npc_flips = scan_npc_flips(price_cache)
        instant_flips.extend(npc_flips)

    # Bit shop
    if need_bits:
        bit_results = scan_bit_flips(price_cache)

    # ── Save caches ──────────────────────────────────────────────────
    save_craft_cache(craft_cache)
    price_cache.flush()

    # ── Sort combined lists ──────────────────────────────────────────
    instant_flips.sort(key=lambda x: x["profit"], reverse=True)
    time_gated_flips.sort(key=lambda x: x.get("profit_per_hour") or 0, reverse=True)

    # ── Filter illiquid AH flips unless --all-liquidity ──────────────
    if not args.all_liquidity:
        def _is_liquid(flip):
            if flip.get("sell_channel") == "bazaar":
                return True  # bazaar = infinite liquidity
            spd = flip.get("sales_per_day")
            return spd is not None and spd >= 0.5

        illiquid_instant = [f for f in instant_flips if not _is_liquid(f)]
        illiquid_timed = [f for f in time_gated_flips if not _is_liquid(f)]
        instant_flips = [f for f in instant_flips if _is_liquid(f)]
        time_gated_flips = [f for f in time_gated_flips if _is_liquid(f)]
        n_hidden = len(illiquid_instant) + len(illiquid_timed)
    else:
        n_hidden = 0

    # ── Display ──────────────────────────────────────────────────────
    has_profile = member is not None and args.profile

    # Instant flips (craft + npc)
    if instant_flips:
        if has_profile:
            print_instant_flips_profile(instant_flips, member)
        else:
            print_instant_flips(instant_flips)

    # Sell-order flips (separate section — different columns)
    if sell_order_flips_list:
        if has_profile:
            print_sell_order_flips_profile(sell_order_flips_list, member)
        else:
            print_sell_order_flips(sell_order_flips_list)

    # Time-gated flips (forge + kat)
    if time_gated_flips:
        if has_profile:
            print_time_gated_flips_profile(time_gated_flips, member)
        else:
            print_time_gated_flips(time_gated_flips)

    # Bit shop
    if bit_results:
        print_bit_flips(bit_results)

    # No results at all
    if not instant_flips and not sell_order_flips_list and not time_gated_flips and not bit_results:
        print("\n  No profitable flips found.")

    if n_hidden > 0:
        print(f"  {n_hidden} illiquid flips hidden (<0.5 sales/day). Use --all-liquidity to show.",
              file=sys.stderr)

    # Data summary
    mb = craft_cache.get("moulberry", {})
    n_lbin = len(mb.get("lowestbin", {}))
    n_avg = len(mb.get("avg_lbin", {}))
    n_sales = len(mb.get("auction_averages", {}))
    recursive_str = "recursive" if recursive else "flat"
    print(f"  Data: {n_lbin} lowest BINs, {n_avg} avg BINs, {n_sales} sale records ({recursive_str} costing)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
