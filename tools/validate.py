#!/usr/bin/env python3
"""Cross-validation tool — compare our calculations against Coflnet.

Uses Coflnet's pre-computed aggregate endpoints to validate our
pricing logic. Flags significant divergences that may indicate
stale data or calculation bugs.

Endpoints used (single calls, no rate limiting):
  - /api/craft/profit — craft flip profits
  - /api/kat/profit   — Kat upgrade profits
  - /api/flip/fusion  — shard fusion profits
  - /api/flip/forge   — forge recipe profits

Usage:
    python3 validate.py                 # run all validations
    python3 validate.py --crafts        # craft profits only
    python3 validate.py --kat           # Kat upgrade profits only
    python3 validate.py --fusions       # shard fusion profits only
    python3 validate.py --forge         # forge recipe profits only
    python3 validate.py --threshold 30  # flag divergences >30% (default: 20%)
    python3 validate.py --json          # machine-readable output
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from items import display_name
from pricing import PriceCache, _fmt

DATA_DIR = Path(__file__).parent.parent / "data"

# Coflnet API endpoints
CRAFT_PROFIT_URL = "https://sky.coflnet.com/api/craft/profit"
KAT_PROFIT_URL = "https://sky.coflnet.com/api/kat/profit"
FUSION_URL = "https://sky.coflnet.com/api/flip/fusion"
FORGE_URL = "https://sky.coflnet.com/api/flip/forge"

import re
_COLOR_CODE_RE = re.compile(r"§[0-9a-fk-or]")


def fetch_json(url, label="data"):
    """Fetch JSON from a URL."""
    req = Request(url, headers={"User-Agent": "SkyBlock-Tools/1.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except (HTTPError, URLError, json.JSONDecodeError) as e:
        print(f"  ERROR: Failed to fetch {label}: {e}", file=sys.stderr)
        return None


# ─── Craft Validation ─────────────────────────────────────────────────

def validate_crafts(pc, threshold_pct=20):
    """Compare our craft pricing against Coflnet craft/profit endpoint.

    Coflnet provides: itemId, sellPrice (LBIN), craftCost, volume, median.
    We compare our prices for the same items.
    """
    print("  Fetching Coflnet craft profit data...", end="", flush=True)
    coflnet_data = fetch_json(CRAFT_PROFIT_URL, "craft profits")
    if not coflnet_data:
        return None
    print(f" {len(coflnet_data)} items")

    results = []
    matched = 0
    divergent = 0

    for entry in coflnet_data:
        item_id = entry.get("itemId", "")
        cofl_sell = entry.get("sellPrice", 0) or 0
        cofl_craft = entry.get("craftCost", 0) or 0
        cofl_volume = entry.get("volume", 0) or 0
        cofl_median = entry.get("median", 0) or 0

        if not item_id or cofl_sell <= 0:
            continue

        # Skip very low volume items (unreliable pricing)
        if cofl_volume < 0.5:
            continue

        # Get our price
        our_price = pc.get_price(item_id)
        our_sell = 0
        if our_price["source"] == "bazaar":
            our_sell = our_price.get("sell") or 0
        elif our_price["source"] == "auction":
            our_sell = our_price.get("avg_bin") or our_price.get("lowest_bin") or 0

        if our_sell <= 0:
            continue

        matched += 1

        # Calculate divergence
        if cofl_sell > 0:
            pct_diff = abs(our_sell - cofl_sell) / cofl_sell * 100
        else:
            pct_diff = 0

        is_divergent = pct_diff > threshold_pct

        if is_divergent:
            divergent += 1

        results.append({
            "item_id": item_id,
            "name": _COLOR_CODE_RE.sub("", entry.get("itemName", "")).strip() or display_name(item_id),
            "our_sell": our_sell,
            "coflnet_sell": cofl_sell,
            "coflnet_craft_cost": cofl_craft,
            "coflnet_median": cofl_median,
            "coflnet_volume": cofl_volume,
            "pct_diff": pct_diff,
            "divergent": is_divergent,
        })

    return {
        "type": "crafts",
        "total_coflnet": len(coflnet_data),
        "matched": matched,
        "divergent": divergent,
        "threshold_pct": threshold_pct,
        "items": results,
    }


# ─── Kat Validation ───────────────────────────────────────────────────

def validate_kat(pc, threshold_pct=20):
    """Compare our Kat pricing against Coflnet kat/profit endpoint.

    Coflnet provides: upgradeCost, materialCost, profit, purchaseCost,
    targetRarity, originAuctionName, volume, median.
    """
    print("  Fetching Coflnet Kat profit data...", end="", flush=True)
    coflnet_data = fetch_json(KAT_PROFIT_URL, "Kat profits")
    if not coflnet_data:
        return None
    print(f" {len(coflnet_data)} upgrades")

    results = []
    matched = 0
    divergent = 0

    for entry in coflnet_data:
        cofl_profit = entry.get("profit", 0) or 0
        cofl_volume = entry.get("volume", 0) or 0
        cofl_median = entry.get("median", 0) or 0
        purchase_cost = entry.get("purchaseCost", 0) or 0
        upgrade_cost = entry.get("upgradeCost", 0) or 0
        material_cost = entry.get("materialCost", 0) or 0
        target_rarity = entry.get("targetRarity", "")
        name = entry.get("originAuctionName", "")

        if not name or cofl_volume < 0.3:
            continue

        core = entry.get("coreData", {})
        item_id = core.get("itemId", "") if core else ""

        total_cost = purchase_cost + upgrade_cost + material_cost
        sell_value = total_cost + cofl_profit if cofl_profit else 0

        matched += 1

        results.append({
            "name": _COLOR_CODE_RE.sub("", name).strip(),
            "item_id": item_id,
            "target_rarity": target_rarity,
            "coflnet_profit": cofl_profit,
            "coflnet_purchase": purchase_cost,
            "coflnet_upgrade": upgrade_cost,
            "coflnet_material": material_cost,
            "coflnet_total_cost": total_cost,
            "coflnet_volume": cofl_volume,
            "coflnet_median": cofl_median,
        })

    # Sort by profit
    results.sort(key=lambda x: x["coflnet_profit"], reverse=True)

    return {
        "type": "kat",
        "total_coflnet": len(coflnet_data),
        "matched": matched,
        "divergent": 0,  # Can't directly compare — different data structure
        "threshold_pct": threshold_pct,
        "items": results,
    }


# ─── Fusion Validation ────────────────────────────────────────────────

def validate_fusions(pc, threshold_pct=20):
    """Compare shard fusion data against Coflnet flip/fusion endpoint.

    Coflnet provides: inputs, inputCost, volume, inputVolume,
    outputValue, output, outputCount.
    """
    print("  Fetching Coflnet fusion data...", end="", flush=True)
    coflnet_data = fetch_json(FUSION_URL, "fusion profits")
    if not coflnet_data:
        return None
    print(f" {len(coflnet_data)} fusions")

    results = []
    matched = 0
    divergent = 0

    for entry in coflnet_data:
        output_id = entry.get("output", "")
        output_count = entry.get("outputCount", 1) or 1
        input_cost = entry.get("inputCost", 0) or 0
        output_value = entry.get("outputValue", 0) or 0
        volume = entry.get("volume", 0) or 0
        inputs = entry.get("inputs", {})

        if not output_id:
            continue

        # Get our price for output
        our_price = pc.get_price(output_id)
        our_sell = 0
        if our_price["source"] == "bazaar":
            our_sell = our_price.get("sell") or 0
        elif our_price["source"] == "auction":
            our_sell = our_price.get("avg_bin") or our_price.get("lowest_bin") or 0

        cofl_per_unit = output_value / output_count if output_count else 0
        cofl_profit = output_value - input_cost

        # Compare our per-unit price vs Coflnet
        pct_diff = 0
        if cofl_per_unit > 0 and our_sell > 0:
            pct_diff = abs(our_sell - cofl_per_unit) / cofl_per_unit * 100

        is_divergent = pct_diff > threshold_pct and our_sell > 0

        if is_divergent:
            divergent += 1

        matched += 1
        results.append({
            "output_id": output_id,
            "output_name": display_name(output_id),
            "output_count": output_count,
            "inputs": inputs,
            "our_sell_price": our_sell,
            "coflnet_output_value": output_value,
            "coflnet_per_unit": cofl_per_unit,
            "coflnet_input_cost": input_cost,
            "coflnet_profit": cofl_profit,
            "coflnet_volume": volume,
            "pct_diff": pct_diff,
            "divergent": is_divergent,
        })

    return {
        "type": "fusions",
        "total_coflnet": len(coflnet_data),
        "matched": matched,
        "divergent": divergent,
        "threshold_pct": threshold_pct,
        "items": results,
    }


# ─── Forge Validation ─────────────────────────────────────────────────

def validate_forge(pc, threshold_pct=20):
    """Compare forge item sell prices against Coflnet flip/forge endpoint."""
    print("  Fetching Coflnet forge data...", end="", flush=True)
    coflnet_data = fetch_json(FORGE_URL, "forge profits")
    if not coflnet_data:
        return None
    print(f" {len(coflnet_data)} recipes")

    results = []
    matched = 0
    divergent = 0

    for entry in coflnet_data:
        craft = entry.get("craftData", {})
        item_id = craft.get("itemId", "")
        cofl_sell = craft.get("sellPrice", 0) or 0
        cofl_craft = craft.get("craftCost", 0) or 0
        cofl_volume = craft.get("volume", 0) or 0
        cofl_median = craft.get("median", 0) or 0

        if not item_id or cofl_sell <= 0:
            continue

        # Get our price
        our_price = pc.get_price(item_id)
        our_sell = 0
        if our_price["source"] == "bazaar":
            our_sell = our_price.get("sell") or 0
        elif our_price["source"] == "auction":
            our_sell = our_price.get("avg_bin") or our_price.get("lowest_bin") or 0

        if our_sell <= 0:
            continue

        matched += 1
        pct_diff = abs(our_sell - cofl_sell) / cofl_sell * 100 if cofl_sell > 0 else 0
        is_divergent = pct_diff > threshold_pct

        if is_divergent:
            divergent += 1

        results.append({
            "item_id": item_id,
            "name": _COLOR_CODE_RE.sub("", craft.get("itemName", "")).strip() or display_name(item_id),
            "our_sell": our_sell,
            "coflnet_sell": cofl_sell,
            "coflnet_craft_cost": cofl_craft,
            "coflnet_median": cofl_median,
            "coflnet_volume": cofl_volume,
            "pct_diff": pct_diff,
            "divergent": is_divergent,
        })

    return {
        "type": "forge",
        "total_coflnet": len(coflnet_data),
        "matched": matched,
        "divergent": divergent,
        "threshold_pct": threshold_pct,
        "items": results,
    }


# ─── Printing ─────────────────────────────────────────────────────────

def print_validation_result(result, show_all=False):
    """Print validation results for one category."""
    if result is None:
        return

    vtype = result["type"].upper()
    matched = result["matched"]
    divergent = result["divergent"]
    threshold = result["threshold_pct"]
    items = result["items"]

    print(f"\n{'═' * 80}")
    print(f"  {vtype} VALIDATION")
    print(f"  Coflnet items: {result['total_coflnet']} | Matched: {matched} | "
          f"Divergent (>{threshold}%): {divergent}")
    print(f"{'═' * 80}")

    if result["type"] == "kat":
        # Kat: show top Coflnet profits as reference data
        print(f"\n  Top Kat upgrades by Coflnet profit (reference data — no direct comparison):")
        print(f"  {'Pet Name':<30s} {'Rarity':>8s} {'Profit':>10s} {'Cost':>10s} {'Vol':>5s}")
        print(f"  {'─' * 30} {'─' * 8} {'─' * 10} {'─' * 10} {'─' * 5}")
        for item in items[:20]:
            vol = f"{item['coflnet_volume']:.1f}"
            print(f"  {item['name'][:28]:<30s} {item['target_rarity']:>8s} "
                  f"{_fmt(item['coflnet_profit']):>10s} {_fmt(item['coflnet_total_cost']):>10s} {vol:>5s}")
        return

    # For crafts, forge, fusions: show divergent items
    divergent_items = [i for i in items if i.get("divergent")]
    if divergent_items:
        divergent_items.sort(key=lambda x: x["pct_diff"], reverse=True)

        # Categorize divergences to reduce noise
        # "ours_higher" = we price much higher (usually AH price vs Coflnet craft cost)
        # "cofl_higher" = Coflnet prices higher (potential pricing bug on our side)
        ours_higher = [i for i in divergent_items
                       if i.get("our_sell", i.get("our_sell_price", 0)) > i.get("coflnet_sell", i.get("coflnet_per_unit", 0))]
        cofl_higher = [i for i in divergent_items
                       if i.get("our_sell", i.get("our_sell_price", 0)) <= i.get("coflnet_sell", i.get("coflnet_per_unit", 0))]

        # High volume items are more concerning
        high_vol = [i for i in divergent_items if i.get("coflnet_volume", 0) >= 10]

        print(f"\n  Divergent items: {len(divergent_items)} total")
        print(f"    Ours higher: {len(ours_higher)} (usually AH price vs Coflnet craft cost — methodology diff)")
        print(f"    Coflnet higher: {len(cofl_higher)} (potential pricing gaps)")
        print(f"    High volume (≥10): {len(high_vol)} (most actionable)")

        # Show only high-volume or coflnet-higher items (the actionable ones)
        actionable = sorted(
            [i for i in divergent_items if i.get("coflnet_volume", 0) >= 10 or
             i.get("our_sell", i.get("our_sell_price", 0)) <= i.get("coflnet_sell", i.get("coflnet_per_unit", 0))],
            key=lambda x: x["pct_diff"], reverse=True
        )

        if actionable:
            print(f"\n  Actionable divergences (high-volume or Coflnet prices higher):")
            if result["type"] == "fusions":
                print(f"  {'Item':<25s} {'Ours':>10s} {'Coflnet':>10s} {'Diff':>7s} {'Volume':>7s}")
                print(f"  {'─' * 25} {'─' * 10} {'─' * 10} {'─' * 7} {'─' * 7}")
                for item in actionable[:25]:
                    print(f"  {item['output_name'][:23]:<25s} {_fmt(item['our_sell_price']):>10s} "
                          f"{_fmt(item['coflnet_per_unit']):>10s} {item['pct_diff']:>6.1f}% {item['coflnet_volume']:>7.0f}")
            else:
                print(f"  {'Item':<30s} {'Ours':>10s} {'Coflnet':>10s} {'Diff':>7s} {'Volume':>7s}")
                print(f"  {'─' * 30} {'─' * 10} {'─' * 10} {'─' * 7} {'─' * 7}")
                for item in actionable[:25]:
                    key = "name" if "name" in item else "item_id"
                    print(f"  {item[key][:28]:<30s} {_fmt(item.get('our_sell', 0)):>10s} "
                          f"{_fmt(item.get('coflnet_sell', 0)):>10s} {item['pct_diff']:>6.1f}% {item.get('coflnet_volume', 0):>7.1f}")
        else:
            print(f"\n  ✓ All divergences are low-volume methodology differences")
    else:
        print(f"\n  ✓ No divergences found above {threshold}% threshold")

    if show_all and not divergent_items:
        # Show sample of matches
        print(f"\n  Sample of matched items:")
        sample = items[:10]
        for item in sample:
            key = "name" if "name" in item else "output_name" if "output_name" in item else "item_id"
            our = _fmt(item.get("our_sell") or item.get("our_sell_price", 0))
            cofl = _fmt(item.get("coflnet_sell") or item.get("coflnet_per_unit", 0))
            print(f"    {item[key][:35]:<37s} Ours: {our:>10s}  Coflnet: {cofl:>10s}")


def print_summary(all_results):
    """Print overall validation summary."""
    print(f"\n{'═' * 60}")
    print(f"  VALIDATION SUMMARY")
    print(f"{'═' * 60}")

    total_matched = 0
    total_divergent = 0

    for result in all_results:
        if result is None:
            continue
        status = "✓" if result["divergent"] == 0 else "⚠"
        print(f"  {status} {result['type']:>10s}: {result['matched']:>4d} matched, "
              f"{result['divergent']:>3d} divergent (>{result['threshold_pct']}%)")
        total_matched += result["matched"]
        total_divergent += result["divergent"]

    print(f"  {'─' * 50}")
    print(f"    Total: {total_matched} matched, {total_divergent} divergent")

    if total_divergent > 0:
        print(f"\n  Divergences may indicate:")
        print(f"    - Stale external data files (pull latest from repos)")
        print(f"    - Different price source (we use Moulberry, Coflnet uses their own)")
        print(f"    - Timing differences (prices shift between our fetch and Coflnet's)")
        print(f"    - Calculation differences (rounding, fee handling)")
    else:
        print(f"\n  All prices within tolerance. Data looks fresh.")


def main():
    parser = argparse.ArgumentParser(description="SkyBlock calculation validator (vs Coflnet)")
    parser.add_argument("--crafts", action="store_true",
                        help="Validate craft profits only")
    parser.add_argument("--kat", action="store_true",
                        help="Validate Kat upgrade profits only")
    parser.add_argument("--fusions", action="store_true",
                        help="Validate shard fusion profits only")
    parser.add_argument("--forge", action="store_true",
                        help="Validate forge recipe profits only")
    parser.add_argument("--threshold", "-t", type=float, default=20, metavar="PCT",
                        help="Divergence threshold percent (default: 20)")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show all items, not just divergent")
    args = parser.parse_args()

    # If no specific flags, run all
    run_all = not (args.crafts or args.kat or args.fusions or args.forge)

    pc = PriceCache()
    all_results = []

    if run_all or args.crafts:
        result = validate_crafts(pc, args.threshold)
        all_results.append(result)
        if not args.json:
            print_validation_result(result, show_all=args.verbose)

    if run_all or args.kat:
        result = validate_kat(pc, args.threshold)
        all_results.append(result)
        if not args.json:
            print_validation_result(result, show_all=args.verbose)

    if run_all or args.fusions:
        result = validate_fusions(pc, args.threshold)
        all_results.append(result)
        if not args.json:
            print_validation_result(result, show_all=args.verbose)

    if run_all or args.forge:
        result = validate_forge(pc, args.threshold)
        all_results.append(result)
        if not args.json:
            print_validation_result(result, show_all=args.verbose)

    if args.json:
        print(json.dumps(all_results, indent=2))
    elif len(all_results) > 1:
        print_summary(all_results)

    pc.flush()


if __name__ == "__main__":
    main()
