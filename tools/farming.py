#!/usr/bin/env python3
"""Farming Profit Calculator for Hypixel SkyBlock.

Calculates profit per hour for each crop based on farming fortune,
with NPC sell vs Bazaar sell comparison and enchanted item crafting.

Farming fortune formula:
  fortune / 100 = average drop multiplier
  e.g., 260 fortune = guaranteed 2 extra drops + 60% chance of 3rd = avg 3.6×

Blocks broken per second depends on crop type and farming speed. Default is
~20 BPS (blocks per second) for standard farming, adjusted per crop.

Data sources:
  - farming_weight.json — crop names, weight divisors
  - Bazaar prices for raw + enchanted crops
  - Profile data for farming fortune, garden level

Usage:
    python3 farming.py                      # all crops, default fortune
    python3 farming.py --fortune 500        # set farming fortune
    python3 farming.py --crop wheat         # detailed wheat breakdown
    python3 farming.py --profile            # auto-detect fortune from profile
    python3 farming.py --npc                # show NPC sell prices too
    python3 farming.py --json               # machine-readable output
"""

import argparse
import json
import sys
import time
from pathlib import Path

from pricing import PriceCache, _fmt

DATA_DIR = Path(__file__).parent.parent / "data"
EXTERNAL_DIR = DATA_DIR / "external"
FARMING_WEIGHT_PATH = EXTERNAL_DIR / "farming_weight.json"
LAST_PROFILE_PATH = DATA_DIR / "last_profile.json"

# ─── Crop Data ─────────────────────────────────────────────────────────
# Each crop: bazaar_id for raw item, enchanted_id, NPC price per raw item,
# items per enchanted craft, drops per break, blocks per second estimate.
#
# BPS (blocks per second) varies by tool, speed, crop layout:
#   - Single-block crops (wheat, carrot, potato, nether wart): ~20 BPS
#   - Tall crops (sugar cane, cactus): ~20 BPS (2 blocks but counted as 1 break)
#   - Melon/pumpkin: ~14-18 BPS (need to break stems less often with good tools)
#   - Cocoa beans: ~18 BPS
#   - Mushroom: ~14 BPS (slower with mushroom cow setup)
#
# drops_per_break: base drops per crop block broken (before fortune)
#   Most crops drop 1 item per break. Melon drops 3-7 (avg ~5 with fortune 0).
#   These are the BASE drops that fortune multiplies.

CROP_DATA = {
    "wheat": {
        "name": "Wheat",
        "bazaar_id": "WHEAT",
        "enchanted_id": "ENCHANTED_HAY_BLOCK",
        "npc_price": 6,
        "raw_per_enchanted": 1296,   # 6×3×72 = hay bale craft chain
        "drops_per_break": 1,
        "bps": 20,
        "seeds_drop": True,        # also drops seeds (not counted for profit)
        "collection_id": "WHEAT",
    },
    "carrot": {
        "name": "Carrot",
        "bazaar_id": "CARROT_ITEM",
        "enchanted_id": "ENCHANTED_GOLDEN_CARROT",
        "npc_price": 3,
        "raw_per_enchanted": 20480,  # carrot → enchanted carrot (160) → enchanted golden (160×128)
        "drops_per_break": 1,
        "bps": 20,
        "collection_id": "CARROT_ITEM",
    },
    "potato": {
        "name": "Potato",
        "bazaar_id": "POTATO_ITEM",
        "enchanted_id": "ENCHANTED_BAKED_POTATO",
        "npc_price": 3,
        "raw_per_enchanted": 25600,  # potato → enchanted (160) → baked (160×160)
        "drops_per_break": 1,
        "bps": 20,
        "collection_id": "POTATO_ITEM",
    },
    "nether_wart": {
        "name": "Nether Wart",
        "bazaar_id": "NETHER_STALK",
        "enchanted_id": "MUTANT_NETHER_STALK",
        "npc_price": 4,
        "raw_per_enchanted": 25600,  # nether wart → enchanted (160) → mutant (160×160)
        "drops_per_break": 1,
        "bps": 20,
        "collection_id": "NETHER_STALK",
    },
    "sugar_cane": {
        "name": "Sugar Cane",
        "bazaar_id": "SUGAR_CANE",
        "enchanted_id": "ENCHANTED_SUGAR_CANE",
        "npc_price": 4,
        "raw_per_enchanted": 25600,
        "drops_per_break": 2,       # double-break crop
        "bps": 20,
        "collection_id": "SUGAR_CANE",
    },
    "melon": {
        "name": "Melon",
        "bazaar_id": "MELON",
        "enchanted_id": "ENCHANTED_MELON_BLOCK",
        "npc_price": 2,
        "raw_per_enchanted": 25600,
        "drops_per_break": 5,       # melon drops avg 5 slices base
        "bps": 15,
        "collection_id": "MELON",
    },
    "pumpkin": {
        "name": "Pumpkin",
        "bazaar_id": "PUMPKIN",
        "enchanted_id": "POLISHED_PUMPKIN",
        "npc_price": 10,
        "raw_per_enchanted": 25600,
        "drops_per_break": 1,
        "bps": 15,
        "collection_id": "PUMPKIN",
    },
    "cactus": {
        "name": "Cactus",
        "bazaar_id": "CACTUS",
        "enchanted_id": "ENCHANTED_CACTUS",
        "npc_price": 3,
        "raw_per_enchanted": 25600,
        "drops_per_break": 2,       # double-break crop
        "bps": 20,
        "collection_id": "CACTUS",
    },
    "cocoa_beans": {
        "name": "Cocoa Beans",
        "bazaar_id": "INK_SACK:3",
        "enchanted_id": "ENCHANTED_COOKIE",
        "npc_price": 3,
        "raw_per_enchanted": 25600,
        "drops_per_break": 1,
        "bps": 18,
        "collection_id": "INK_SACK:3",
    },
    "mushroom": {
        "name": "Mushroom",
        "bazaar_id": "BROWN_MUSHROOM",
        "enchanted_id": "ENCHANTED_BROWN_MUSHROOM_BLOCK",
        "bazaar_id_alt": "RED_MUSHROOM",
        "enchanted_id_alt": "ENCHANTED_RED_MUSHROOM_BLOCK",
        "npc_price": 4,
        "raw_per_enchanted": 25600,
        "drops_per_break": 1,
        "bps": 14,
        "collection_id": "MUSHROOM_COLLECTION",
    },
}

# Special crops added with the Greenhouse update
SPECIAL_CROP_DATA = {
    "sunflower": {
        "name": "Sunflower",
        "bazaar_id": "DOUBLE_PLANT",
        "npc_price": 2,
        "drops_per_break": 1,
        "bps": 18,
        "collection_id": "DOUBLE_PLANT",
    },
}


def load_farming_weight():
    """Load farming weight data (crop names, weight divisors)."""
    if FARMING_WEIGHT_PATH.exists():
        with open(FARMING_WEIGHT_PATH) as f:
            return json.load(f)
    return {}


def load_profile_fortune():
    """Try to detect farming fortune from cached profile data.

    Farming fortune sources we can detect from API:
    - Farming skill level (4 FF per level, max 240 at 60)
    - Garden crop upgrades (5 FF per level per crop, max 45 each)
    - Garden plots (3 FF per plot)
    - Extra Farming Fortune (Anita perk)

    Sources we CAN'T detect (need tool/armor inspection):
    - Tool fortune (varies by hoe tier + counter)
    - Armor fortune (Fermento, Melon, etc.)
    - Pet fortune (Elephant, Mooshroom Cow, etc.)
    - Reforge fortune
    """
    if not LAST_PROFILE_PATH.exists():
        return None
    try:
        data = json.loads(LAST_PROFILE_PATH.read_text())
        member_data = data.get("profile", {}).get("members", {})
        for uuid, member in member_data.items():
            result = {"fortune": 0, "breakdown": {}}

            # Farming skill level → fortune
            xp = member.get("player_data", {}).get("experience", {}).get("SKILL_FARMING", 0)
            # Farming XP table (simplified — accurate to level 50, approximate for 50-60)
            farming_xp_table = [
                0, 50, 175, 375, 675, 1175, 1925, 2925, 4425, 6425, 9925,
                14925, 22425, 32425, 47425, 67425, 97425, 147425, 222425, 322425, 522425,
                822425, 1222425, 1722425, 2322425, 3022425, 3822425, 4722425, 5722425, 6822425, 8022425,
                9322425, 10722425, 12222425, 13822425, 15522425, 17322425, 19222425, 21222425, 23322425, 25522425,
                27822425, 30222425, 32722425, 35322425, 38072425, 40972425, 44072425, 47472425, 51172425, 55172425,
                59472425, 64072425, 68972425, 74172425, 79672425, 85472425, 91572425, 97972425, 104672425, 111672425,
            ]
            farming_level = 0
            for lvl, xp_needed in enumerate(farming_xp_table):
                if xp >= xp_needed:
                    farming_level = lvl
            farming_fortune = farming_level * 4
            result["fortune"] += farming_fortune
            result["breakdown"]["Farming Skill"] = farming_fortune
            result["farming_level"] = farming_level

            # Garden data (need separate API call data — check if stored)
            # For now, we can't easily get garden data from last_profile.json
            # since it's a separate endpoint. Use a conservative estimate.

            return result
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def calc_crop_profit(crop_key, crop_info, fortune, pc, bps_override=None):
    """Calculate profit per hour for a crop.

    Args:
        crop_key: crop identifier
        crop_info: dict with crop data
        fortune: total farming fortune
        pc: PriceCache
        bps_override: override blocks per second

    Returns:
        dict with profit breakdown
    """
    bps = bps_override or crop_info["bps"]
    drops_per_break = crop_info["drops_per_break"]

    # Fortune multiplier: fortune / 100 gives average extra drops
    # At 0 fortune: 1× drops. At 100: 2×. At 260: 3.6×, etc.
    fortune_mult = 1 + (fortune / 100)

    # Drops per second = BPS × drops_per_break × fortune_multiplier
    drops_per_second = bps * drops_per_break * fortune_mult
    drops_per_hour = drops_per_second * 3600

    # Get prices
    bazaar_id = crop_info["bazaar_id"]
    price_info = pc.get_price(bazaar_id)
    npc_price = crop_info.get("npc_price", 0)

    # Bazaar sell (instant sell) price
    bz_sell = 0
    if price_info["source"] == "bazaar":
        bz_sell = price_info.get("sell") or 0

    # Also check enchanted version sell price
    enchanted_id = crop_info.get("enchanted_id")
    enchanted_sell = 0
    raw_per_enchanted = crop_info.get("raw_per_enchanted", 0)
    if enchanted_id and raw_per_enchanted > 0:
        ench_price = pc.get_price(enchanted_id)
        if ench_price["source"] == "bazaar":
            enchanted_sell = (ench_price.get("sell") or 0) / raw_per_enchanted

    # Best bazaar price per raw item
    bz_price = max(bz_sell, enchanted_sell)
    bz_method = "raw" if bz_sell >= enchanted_sell else "enchanted"

    # Profit per hour calculations
    npc_profit_hr = drops_per_hour * npc_price
    bz_profit_hr = drops_per_hour * bz_price
    best_profit_hr = max(npc_profit_hr, bz_profit_hr)
    best_method = "NPC" if npc_profit_hr > bz_profit_hr else f"Bazaar ({bz_method})"

    return {
        "crop": crop_key,
        "name": crop_info["name"],
        "fortune": fortune,
        "fortune_mult": fortune_mult,
        "bps": bps,
        "drops_per_break": drops_per_break,
        "drops_per_hour": drops_per_hour,
        "npc_price": npc_price,
        "bz_sell_price": bz_sell,
        "enchanted_sell_per_raw": enchanted_sell,
        "enchanted_id": enchanted_id,
        "bz_method": bz_method,
        "npc_profit_hr": npc_profit_hr,
        "bz_profit_hr": bz_profit_hr,
        "best_profit_hr": best_profit_hr,
        "best_method": best_method,
    }


def print_crop_detail(result, pc):
    """Print detailed breakdown for one crop."""
    print(f"\n{'═' * 60}")
    print(f"  {result['name']} — Farming Profit Breakdown")
    print(f"{'═' * 60}")
    print(f"  Farming Fortune: {result['fortune']:.0f} ({result['fortune_mult']:.2f}× drops)")
    print(f"  Blocks/Second:   {result['bps']}")
    print(f"  Drops/Break:     {result['drops_per_break']}")
    print(f"  Drops/Hour:      {_fmt(result['drops_per_hour'])}")
    print()

    print(f"  Pricing:")
    print(f"    NPC sell:           {result['npc_price']:.1f} per item")
    print(f"    Bazaar sell (raw):  {result['bz_sell_price']:.1f} per item")
    if result.get("enchanted_id"):
        print(f"    Bazaar (enchanted): {result['enchanted_sell_per_raw']:.2f} per raw item equiv")
    print()

    print(f"  Profit Per Hour:")
    npc_str = _fmt(result['npc_profit_hr'])
    bz_str = _fmt(result['bz_profit_hr'])
    best_marker_npc = " ◄ BEST" if result['best_method'] == "NPC" else ""
    best_marker_bz = " ◄ BEST" if "Bazaar" in result['best_method'] else ""
    print(f"    NPC:    {npc_str:>10s}{best_marker_npc}")
    print(f"    Bazaar: {bz_str:>10s} ({result['bz_method']}){best_marker_bz}")
    print()
    print(f"  Best: {_fmt(result['best_profit_hr'])}/hr via {result['best_method']}")


def print_summary(results, fortune, show_npc=False):
    """Print summary table of all crops."""
    print(f"\n{'═' * 80}")
    print(f"  Farming Profit Calculator — Coins/Hour by Crop")
    print(f"  Farming Fortune: {fortune:.0f} ({1 + fortune/100:.2f}× drop multiplier)")
    print(f"{'═' * 80}")
    print()

    if show_npc:
        print(f"  {'#':>3s}  {'Crop':<18s} {'Drops/hr':>10s} {'NPC $/hr':>10s} {'BZ $/hr':>10s} {'Best $/hr':>10s} {'Method':>15s}")
        print(f"  {'─' * 3}  {'─' * 18} {'─' * 10} {'─' * 10} {'─' * 10} {'─' * 10} {'─' * 15}")
    else:
        print(f"  {'#':>3s}  {'Crop':<18s} {'Drops/hr':>10s} {'Best $/hr':>10s} {'Method':>15s}")
        print(f"  {'─' * 3}  {'─' * 18} {'─' * 10} {'─' * 10} {'─' * 15}")

    # Sort by best profit
    sorted_results = sorted(results, key=lambda x: x["best_profit_hr"], reverse=True)

    for i, r in enumerate(sorted_results, 1):
        if show_npc:
            print(f"  {i:>3d}  {r['name']:<18s} {_fmt(r['drops_per_hour']):>10s} "
                  f"{_fmt(r['npc_profit_hr']):>10s} {_fmt(r['bz_profit_hr']):>10s} "
                  f"{_fmt(r['best_profit_hr']):>10s} {r['best_method']:>15s}")
        else:
            print(f"  {i:>3d}  {r['name']:<18s} {_fmt(r['drops_per_hour']):>10s} "
                  f"{_fmt(r['best_profit_hr']):>10s} {r['best_method']:>15s}")

    print()
    print(f"  BPS (blocks/sec) estimates assume standard farming speed with good tools.")
    print(f"  Use --fortune to set your total farming fortune (skill + tool + armor + pet).")
    print(f"  Use --bps to override blocks/second for your specific setup.")
    print(f"  Bazaar prices use instant-sell. Enchanted sell = craft up + sell if more profitable.")


def main():
    parser = argparse.ArgumentParser(description="SkyBlock Farming Profit Calculator")
    parser.add_argument("--fortune", "-f", type=float, default=100, metavar="FF",
                        help="Total farming fortune (default: 100)")
    parser.add_argument("--crop", "-c", type=str, metavar="CROP",
                        help="Show detailed breakdown for one crop")
    parser.add_argument("--bps", type=float, metavar="N",
                        help="Override blocks per second (default: varies by crop)")
    parser.add_argument("--profile", "-p", action="store_true",
                        help="Auto-detect farming fortune from profile (skill level only)")
    parser.add_argument("--npc", action="store_true",
                        help="Show NPC sell prices in summary")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    args = parser.parse_args()

    fortune = args.fortune

    if args.profile:
        profile_data = load_profile_fortune()
        if profile_data:
            detected = profile_data["fortune"]
            print(f"  Detected farming fortune from skill level: {detected}")
            for src, val in profile_data.get("breakdown", {}).items():
                print(f"    {src}: +{val}")
            print(f"  Note: Tool, armor, pet, and reforge fortune not detected.")
            print(f"        Use --fortune to set your actual total fortune.")
            if fortune == 100:  # default — use detected
                fortune = detected
        else:
            print("  Warning: Could not load profile. Run profile.py first.", file=sys.stderr)

    pc = PriceCache()

    # Merge all crops
    all_crops = {**CROP_DATA, **SPECIAL_CROP_DATA}

    if args.crop:
        crop_key = args.crop.lower().replace(" ", "_")
        if crop_key not in all_crops:
            # Try fuzzy match
            matches = [k for k in all_crops if crop_key in k or crop_key in all_crops[k]["name"].lower()]
            if len(matches) == 1:
                crop_key = matches[0]
            elif matches:
                print(f"  Ambiguous crop '{args.crop}'. Matches: {', '.join(matches)}")
                sys.exit(1)
            else:
                print(f"  Unknown crop '{args.crop}'")
                print(f"  Available: {', '.join(sorted(all_crops.keys()))}")
                sys.exit(1)

        result = calc_crop_profit(crop_key, all_crops[crop_key], fortune, pc, args.bps)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_crop_detail(result, pc)
    else:
        results = []
        for crop_key, crop_info in all_crops.items():
            results.append(calc_crop_profit(crop_key, crop_info, fortune, pc, args.bps))

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print_summary(results, fortune, show_npc=args.npc)

    pc.flush()


if __name__ == "__main__":
    main()
