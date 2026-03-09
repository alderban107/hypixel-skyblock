#!/usr/bin/env python3
"""Slayer Profit Calculator for Hypixel SkyBlock.

Calculates expected profit per boss for each slayer type and tier,
with live pricing, RNG meter optimization, and Magic Find support.

Data sources:
  - Luckalyzer (Mabi19, MIT) — RNG drop probabilities and meter boss counts
  - Fandom Wiki — common/guaranteed drops, boss stats, spawn costs
  - pricing.py — live Bazaar weighted avg + Moulberry LBIN

Usage:
    python3 slayers.py                         # all slayer types summary
    python3 slayers.py --type zombie           # detailed Revenant breakdown
    python3 slayers.py --type zombie --tier 5  # detailed T5 Revenant
    python3 slayers.py --magic-find 200        # factor in Magic Find
    python3 slayers.py --aatrox                # apply Aatrox mayor bonuses
    python3 slayers.py --kills-per-hour 12     # override kill speed
    python3 slayers.py --json                  # machine-readable output
"""

import argparse
import json
import sys
from pathlib import Path

from items import display_name
from pricing import PriceCache, _fmt

DATA_DIR = Path(__file__).parent.parent / "data"
DROPS_PATH = DATA_DIR / "slayer_drops.json"
LAST_PROFILE_PATH = DATA_DIR / "last_profile.json"

# ─── Aatrox Mayor Bonuses ─────────────────────────────────────────────

AATROX_COST_DISCOUNT = 0.25     # 25% reduced costs
AATROX_MF_MULTIPLIER = 1.2     # MF × 1.2 + 20 (Pathfinder)
AATROX_MF_BONUS = 20

# ─── Magic Find threshold ─────────────────────────────────────────────
# Only drops with <5% base chance are affected by Magic Find
MF_CHANCE_THRESHOLD = 0.05


# ─── Data Loading ─────────────────────────────────────────────────────

def load_slayer_data():
    """Load slayer drop data from JSON."""
    if not DROPS_PATH.exists():
        print("Error: data/slayer_drops.json not found.", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(DROPS_PATH.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error reading slayer_drops.json: {e}", file=sys.stderr)
        sys.exit(1)


def load_profile():
    """Load last_profile.json for player name. Returns (player_name, member) or defaults."""
    if not LAST_PROFILE_PATH.exists():
        return "Unknown", None
    try:
        data = json.loads(LAST_PROFILE_PATH.read_text())
        player = data.get("player", data.get("uuid", "Unknown"))
        return player, data
    except (json.JSONDecodeError, OSError):
        return "Unknown", None


# ─── Price Resolution ─────────────────────────────────────────────────

def get_item_price(item_id, price_cache, npc_sell=None):
    """Get the best price for an item: max(market_price, npc_sell).

    Returns the price or None if no pricing available.
    """
    market = price_cache.weighted(item_id)
    if npc_sell and market:
        return max(market, npc_sell)
    if npc_sell and not market:
        return npc_sell
    return market


# ─── Drop Calculations ────────────────────────────────────────────────

def calculate_drop_ev(drop, tier, price_cache, magic_find=0, aatrox=False):
    """Calculate expected value of a drop at a specific tier.

    Returns dict with name, ev, price, chance, avg_qty, type, etc.
    """
    tier_key = str(tier)
    tier_data = drop.get("tiers", {}).get(tier_key)
    if not tier_data:
        return None

    item_id = drop["id"]
    name = drop["name"]
    drop_type = drop["type"]
    npc_sell = drop.get("npc_sell")

    price = get_item_price(item_id, price_cache, npc_sell)
    if price is None or price <= 0:
        price = 0  # Still show the drop, just with 0 value

    if drop_type == "guaranteed":
        min_qty, max_qty = tier_data[0], tier_data[1]
        avg_qty = (min_qty + max_qty) / 2
        ev = avg_qty * price
        return {
            "name": name, "id": item_id, "type": drop_type,
            "price": price, "ev": ev, "chance": 1.0, "avg_qty": avg_qty,
            "min_qty": min_qty, "max_qty": max_qty,
        }

    # Common or RNG drop: [min, max, chance]
    min_qty, max_qty, base_chance = tier_data[0], tier_data[1], tier_data[2]
    avg_qty = (min_qty + max_qty) / 2

    # Apply Magic Find to drops with <5% base chance
    chance = base_chance
    if base_chance < MF_CHANCE_THRESHOLD and magic_find > 0:
        effective_mf = magic_find
        if aatrox:
            effective_mf = magic_find * AATROX_MF_MULTIPLIER + AATROX_MF_BONUS
        chance = base_chance * (1 + effective_mf / 100)
        # Cap at a reasonable value (don't exceed 100%)
        chance = min(chance, 1.0)

    ev = chance * avg_qty * price

    result = {
        "name": name, "id": item_id, "type": drop_type,
        "price": price, "ev": ev, "chance": chance, "avg_qty": avg_qty,
        "min_qty": min_qty, "max_qty": max_qty,
        "base_chance": base_chance,
    }

    # Add RNG meter info if available
    if drop.get("prob") and drop.get("meter"):
        result["prob"] = drop["prob"]
        result["meter"] = drop["meter"]

    return result


def calculate_rng_meter(rng_drops, tier_xp, ref_tier_xp, price_cache):
    """Calculate RNG meter optimization.

    For each eligible drop:
      meter_xp = rng_meter_bosses × ref_tier_xp
      coins_per_xp = item_price / meter_xp
    Best target = highest coins_per_xp
    Meter value per boss = tier_xp × best_coins_per_xp

    Returns (best_target, coins_per_xp, meter_value_per_boss, all_targets).
    """
    targets = []
    for drop in rng_drops:
        if not drop.get("meter") or not drop.get("prob"):
            continue
        price = drop["price"]
        if price is None or price <= 0:
            continue
        meter_xp = drop["meter"] * ref_tier_xp
        if meter_xp <= 0:
            continue
        coins_per_xp = price / meter_xp
        targets.append({
            "name": drop["name"],
            "id": drop["id"],
            "price": price,
            "meter_bosses": drop["meter"],
            "meter_xp": meter_xp,
            "coins_per_xp": coins_per_xp,
            "bosses_at_tier": meter_xp / tier_xp if tier_xp > 0 else float("inf"),
        })

    if not targets:
        return None, 0, 0, []

    targets.sort(key=lambda t: t["coins_per_xp"], reverse=True)
    best = targets[0]
    meter_value = tier_xp * best["coins_per_xp"]

    return best, best["coins_per_xp"], meter_value, targets


def calculate_scavenger(level):
    """Calculate Scavenger 5 coins from boss level."""
    if level <= 0:
        return 0
    return level * 0.18


def calculate_champion():
    """Champion X coins per boss (if not one-shot)."""
    return 5


# ─── Per-Boss Profit ──────────────────────────────────────────────────

def calculate_boss_profit(slayer_data, tier, price_cache,
                          magic_find=0, aatrox=False, kills_per_hour=None):
    """Calculate complete profit breakdown for a specific slayer + tier.

    Returns dict with all breakdown info.
    """
    tier_key = str(tier)
    tier_info = slayer_data["tiers"].get(tier_key)
    if not tier_info:
        return None

    cost = tier_info["cost"]
    xp = tier_info["xp"]
    level = tier_info.get("level", 0)
    kph = kills_per_hour or tier_info.get("kph", 10)
    ref_tier = slayer_data.get("rng_meter_ref_tier", tier_key)
    ref_tier_xp = slayer_data["tiers"].get(ref_tier, {}).get("xp", xp)

    # Aatrox cost discount
    effective_cost = cost
    if aatrox:
        effective_cost = int(cost * (1 - AATROX_COST_DISCOUNT))

    # Calculate all drops
    guaranteed = []
    common = []
    rng = []

    for drop in slayer_data.get("drops", []):
        result = calculate_drop_ev(drop, tier, price_cache, magic_find, aatrox)
        if result is None:
            continue
        if result["type"] == "guaranteed":
            guaranteed.append(result)
        elif result["type"] == "rng":
            rng.append(result)
        else:
            common.append(result)

    # Sort by EV descending
    common.sort(key=lambda d: d["ev"], reverse=True)
    rng.sort(key=lambda d: d["ev"], reverse=True)

    # RNG meter optimization (only for RNG drops with meter data)
    meter_drops = [d for d in rng if d.get("meter")]
    best_meter, coins_per_xp, meter_value, all_meter_targets = \
        calculate_rng_meter(meter_drops, xp, ref_tier_xp, price_cache)

    # Scavenger & Champion
    scav_coins = calculate_scavenger(level)
    champ_coins = calculate_champion()

    # Totals
    guaranteed_total = sum(d["ev"] for d in guaranteed)
    common_total = sum(d["ev"] for d in common)
    rng_total = sum(d["ev"] for d in rng)
    other_income = scav_coins + champ_coins + meter_value
    total_value = guaranteed_total + common_total + rng_total + other_income
    profit = total_value - effective_cost
    coins_per_xp_total = profit / xp if xp > 0 else 0
    hourly = profit * kph

    return {
        "slayer_name": slayer_data["name"],
        "tier": tier,
        "cost": cost,
        "effective_cost": effective_cost,
        "xp": xp,
        "level": level,
        "kph": kph,
        "guaranteed": guaranteed,
        "common": common,
        "rng": rng,
        "guaranteed_total": guaranteed_total,
        "common_total": common_total,
        "rng_total": rng_total,
        "meter_value": meter_value,
        "best_meter_target": best_meter,
        "meter_coins_per_xp": coins_per_xp,
        "all_meter_targets": all_meter_targets,
        "scavenger": scav_coins,
        "champion": champ_coins,
        "other_income": other_income,
        "total_value": total_value,
        "profit": profit,
        "coins_per_xp": coins_per_xp_total,
        "hourly": hourly,
    }


# ─── Output Formatting ────────────────────────────────────────────────

def print_detailed(result, magic_find=0, aatrox=False):
    """Print detailed breakdown for a specific slayer + tier."""
    name = result["slayer_name"]
    tier = result["tier"]
    cost = result["effective_cost"]

    # Header
    print(f"\n{'═' * 60}")
    header_parts = [f"  SLAYER PROFIT — {name} (T{tier})"]
    if aatrox:
        header_parts.append(f"  Mayor: Aatrox (−{AATROX_COST_DISCOUNT:.0%} cost)")
    if magic_find > 0:
        header_parts.append(f"  Magic Find: {magic_find}")
    print("\n".join(header_parts))
    print(f"  Summoning Cost: {cost:,} coins")
    print(f"{'═' * 60}")

    # Guaranteed drops
    if result["guaranteed"]:
        print(f"\n  Guaranteed Drops:")
        for d in result["guaranteed"]:
            qty_str = f"×{d['avg_qty']:.1f} avg" if d["min_qty"] != d["max_qty"] else f"×{d['min_qty']}"
            ev_str = _fmt(d["ev"])
            print(f"    {d['name']} {qty_str:<16s} {ev_str:>10s}")

    # Common drops
    visible_common = [d for d in result["common"] if d["ev"] > 0]
    if visible_common:
        print(f"\n  Common Drops (weight-based):")
        for d in visible_common:
            odds_str = f"(1 in {1/d['chance']:.1f})" if d["chance"] > 0 and d["chance"] < 1 else ""
            ev_str = f"{_fmt(d['ev'])}/boss"
            npc_tag = "  [NPC sell]" if d.get("base_chance") and d["id"] == "FOUL_FLESH" else ""
            print(f"    {d['name']:<30s} {odds_str:<16s} {ev_str:>12s}{npc_tag}")

    # RNG drops
    visible_rng = [d for d in result["rng"] if d["price"] > 0]
    if visible_rng:
        print(f"\n  RNG Drops:")
        print(f"    {'Drop':<26s} {'Chance':<14s} {'Price':>10s}   {'EV/Boss':>10s}")
        print(f"    {'─' * 26} {'─' * 14} {'─' * 10}   {'─' * 10}")
        for d in visible_rng:
            chance_str = f"1/{1/d['chance']:,.0f}" if d["chance"] > 0 else "?"
            print(f"    {d['name']:<26s} {chance_str:<14s} {_fmt(d['price']):>10s}   {_fmt(d['ev']):>10s}")

    # RNG Meter
    if result["best_meter_target"]:
        best = result["best_meter_target"]
        print(f"\n  RNG Meter ({result['xp']:,} XP/boss):")
        print(f"    Best target: {best['name']} ({_fmt(best['coins_per_xp'])} coins/XP)")
        print(f"    Meter value per boss:             {_fmt(result['meter_value']):>10s} ★")

        # Show all targets
        if len(result["all_meter_targets"]) > 1:
            print(f"\n    All meter targets:")
            print(f"      {'Target':<26s} {'Price':>10s}  {'Bosses':>8s}  {'Coins/XP':>10s}")
            print(f"      {'─' * 26} {'─' * 10}  {'─' * 8}  {'─' * 10}")
            for t in result["all_meter_targets"]:
                bosses_str = f"{t['bosses_at_tier']:,.0f}"
                print(f"      {t['name']:<26s} {_fmt(t['price']):>10s}  {bosses_str:>8s}  {_fmt(t['coins_per_xp']):>10s}")

    # Other income
    if result["scavenger"] > 0 or result["champion"] > 0:
        print(f"\n  Other Income:")
        if result["scavenger"] > 0:
            print(f"    Scavenger 5 (lvl {result['level']:,}):         {_fmt(result['scavenger']):>10s}")
        if result["champion"] > 0:
            print(f"    Champion X:                       {_fmt(result['champion']):>10s}")

    # Summary
    print(f"\n  {'─' * 56}")
    print(f"  Total Value/Boss:                   {_fmt(result['total_value']):>10s}")
    print(f"  Profit/Boss (after cost):           {_profit_str(result['profit']):>10s}")
    print(f"  Coins/XP:                           {_fmt(result['coins_per_xp']):>10s}")
    print(f"  Est. kills/hr:                      {result['kph']:>10d}")
    print(f"  Profit/hr:                          {_profit_str(result['hourly']):>10s}")


def print_tier_comparison(slayer_data, all_results, aatrox=False):
    """Print tier comparison table for a slayer type."""
    name = slayer_data["name"]

    print(f"\n  Tier Comparison — {name}:")
    print(f"    {'Tier':>4s}   {'Cost':>8s}   {'Profit/Boss':>12s}   {'Coins/XP':>10s}   {'Kills/hr':>8s}   {'Profit/hr':>10s}")
    print(f"    {'─' * 4}   {'─' * 8}   {'─' * 12}   {'─' * 10}   {'─' * 8}   {'─' * 10}")

    best_hourly_tier = None
    best_hourly = float("-inf")
    for r in all_results:
        if r["hourly"] > best_hourly:
            best_hourly = r["hourly"]
            best_hourly_tier = r["tier"]

    for r in all_results:
        marker = "  ← Best $/hr" if r["tier"] == best_hourly_tier else ""
        cost_str = _fmt(r["effective_cost"])
        print(f"    T{r['tier']:<3d}   {cost_str:>8s}   {_profit_str(r['profit']):>12s}   "
              f"{_fmt(r['coins_per_xp']):>10s}   {r['kph']:>8d}   {_profit_str(r['hourly']):>10s}{marker}")


def print_summary(all_slayers, price_cache, magic_find=0, aatrox=False):
    """Print summary across all slayer types (best tier for each)."""
    print(f"\n{'═' * 70}")
    print(f"  SLAYER PROFIT SUMMARY")
    mods = []
    if aatrox:
        mods.append("Aatrox")
    if magic_find > 0:
        mods.append(f"MF {magic_find}")
    if mods:
        print(f"  Modifiers: {', '.join(mods)}")
    print(f"{'═' * 70}")

    print(f"\n  {'Slayer':<24s} {'Best Tier':>9s}   {'Profit/Boss':>12s}   {'Profit/hr':>10s}   {'Coins/XP':>10s}")
    print(f"  {'─' * 24} {'─' * 9}   {'─' * 12}   {'─' * 10}   {'─' * 10}")

    for slayer_key, slayer_data in all_slayers.items():
        if slayer_key.startswith("_"):
            continue
        name = slayer_data["name"]
        tiers = slayer_data["tiers"]

        # Find best tier by hourly profit
        best = None
        for tier_key in sorted(tiers.keys(), key=int):
            tier = int(tier_key)
            result = calculate_boss_profit(slayer_data, tier, price_cache,
                                           magic_find, aatrox)
            if result and (best is None or result["hourly"] > best["hourly"]):
                best = result

        if best:
            print(f"  {name:<24s} T{best['tier']:<8d}   {_profit_str(best['profit']):>12s}   "
                  f"{_profit_str(best['hourly']):>10s}   {_fmt(best['coins_per_xp']):>10s}")

    print()


def _profit_str(value):
    """Format a profit value with +/- prefix."""
    if value >= 0:
        return f"+{_fmt(value)}"
    return f"-{_fmt(abs(value))}"


# ─── JSON Output ──────────────────────────────────────────────────────

def json_output_detailed(result):
    """Output detailed JSON for a specific slayer + tier."""
    # Simplify drop dicts for JSON
    def simplify_drops(drops):
        return [{
            "id": d["id"], "name": d["name"], "type": d["type"],
            "price": d["price"], "ev": round(d["ev"], 2),
            "chance": d["chance"], "avg_qty": d["avg_qty"],
        } for d in drops]

    out = {
        "slayer": result["slayer_name"],
        "tier": result["tier"],
        "cost": result["effective_cost"],
        "xp": result["xp"],
        "level": result["level"],
        "kph": result["kph"],
        "guaranteed": simplify_drops(result["guaranteed"]),
        "common": simplify_drops(result["common"]),
        "rng": simplify_drops(result["rng"]),
        "guaranteed_total": round(result["guaranteed_total"], 2),
        "common_total": round(result["common_total"], 2),
        "rng_total": round(result["rng_total"], 2),
        "meter_value": round(result["meter_value"], 2),
        "best_meter_target": result["best_meter_target"]["name"] if result["best_meter_target"] else None,
        "scavenger": round(result["scavenger"], 2),
        "champion": result["champion"],
        "total_value": round(result["total_value"], 2),
        "profit": round(result["profit"], 2),
        "coins_per_xp": round(result["coins_per_xp"], 2),
        "hourly": round(result["hourly"], 2),
    }
    print(json.dumps(out, indent=2))


def json_output_summary(all_slayers, price_cache, magic_find=0, aatrox=False):
    """Output JSON summary across all slayer types."""
    results = {}
    for slayer_key, slayer_data in all_slayers.items():
        if slayer_key.startswith("_"):
            continue
        tiers_out = {}
        for tier_key in sorted(slayer_data["tiers"].keys(), key=int):
            tier = int(tier_key)
            r = calculate_boss_profit(slayer_data, tier, price_cache,
                                      magic_find, aatrox)
            if r:
                tiers_out[tier_key] = {
                    "cost": r["effective_cost"],
                    "profit": round(r["profit"], 2),
                    "coins_per_xp": round(r["coins_per_xp"], 2),
                    "hourly": round(r["hourly"], 2),
                    "total_value": round(r["total_value"], 2),
                    "meter_value": round(r["meter_value"], 2),
                }
        results[slayer_key] = {
            "name": slayer_data["name"],
            "tiers": tiers_out,
        }
    print(json.dumps(results, indent=2))


# ─── Main ─────────────────────────────────────────────────────────────

SLAYER_ALIASES = {
    "zombie": "zombie", "revenant": "zombie", "rev": "zombie",
    "spider": "spider", "tarantula": "spider", "tara": "spider",
    "wolf": "wolf", "sven": "wolf",
    "enderman": "enderman", "eman": "enderman", "voidgloom": "enderman",
    "blaze": "blaze", "inferno": "blaze", "demonlord": "blaze",
}


def main():
    parser = argparse.ArgumentParser(
        description="Calculate expected slayer profit per boss with live pricing."
    )
    parser.add_argument("--type", "-t", type=str, default=None,
                        help="Slayer type (zombie/spider/wolf/enderman/blaze)")
    parser.add_argument("--tier", type=int, default=None,
                        help="Specific tier (1-5)")
    parser.add_argument("--magic-find", "--mf", type=int, default=0,
                        help="Magic Find stat value")
    parser.add_argument("--aatrox", action="store_true",
                        help="Apply Aatrox mayor bonuses (cost discount + MF boost)")
    parser.add_argument("--kills-per-hour", "--kph", type=int, default=None,
                        help="Override kills per hour estimate")
    parser.add_argument("--json", action="store_true",
                        help="Machine-readable JSON output")
    args = parser.parse_args()

    def status(msg):
        print(msg, file=sys.stderr)

    # Load data
    all_data = load_slayer_data()
    player, _ = load_profile()

    # Resolve slayer type
    slayer_key = None
    if args.type:
        slayer_key = SLAYER_ALIASES.get(args.type.lower())
        if not slayer_key or slayer_key not in all_data:
            valid = ", ".join(k for k in all_data if not k.startswith("_"))
            print(f"Error: Unknown slayer type '{args.type}'. Valid: {valid}", file=sys.stderr)
            sys.exit(1)

    # Collect all item IDs that need pricing
    all_item_ids = set()
    slayer_keys = [slayer_key] if slayer_key else [k for k in all_data if not k.startswith("_")]
    for sk in slayer_keys:
        for drop in all_data[sk].get("drops", []):
            all_item_ids.add(drop["id"])

    # Fetch prices
    price_cache = PriceCache()
    status("Fetching prices...")
    price_cache.get_prices_bulk(list(all_item_ids))

    magic_find = args.magic_find
    aatrox = args.aatrox
    kph = args.kills_per_hour

    if slayer_key and args.tier:
        # Detailed single tier
        slayer_data = all_data[slayer_key]
        result = calculate_boss_profit(slayer_data, args.tier, price_cache,
                                       magic_find, aatrox, kph)
        if not result:
            valid_tiers = ", ".join(sorted(slayer_data["tiers"].keys(), key=int))
            print(f"Error: Tier {args.tier} not available for {slayer_data['name']}. "
                  f"Valid: {valid_tiers}", file=sys.stderr)
            sys.exit(1)

        if args.json:
            json_output_detailed(result)
        else:
            print_detailed(result, magic_find, aatrox)

            # Also show tier comparison
            all_results = []
            for tk in sorted(slayer_data["tiers"].keys(), key=int):
                t = int(tk)
                r = calculate_boss_profit(slayer_data, t, price_cache,
                                          magic_find, aatrox, kph)
                if r:
                    all_results.append(r)
            print_tier_comparison(slayer_data, all_results, aatrox)

    elif slayer_key:
        # All tiers for one slayer type
        slayer_data = all_data[slayer_key]
        all_results = []
        best_tier = None
        best_hourly = float("-inf")

        for tk in sorted(slayer_data["tiers"].keys(), key=int):
            t = int(tk)
            r = calculate_boss_profit(slayer_data, t, price_cache,
                                      magic_find, aatrox, kph)
            if r:
                all_results.append(r)
                if r["hourly"] > best_hourly:
                    best_hourly = r["hourly"]
                    best_tier = t

        if args.json:
            json_data = {}
            for r in all_results:
                json_data[str(r["tier"])] = {
                    "cost": r["effective_cost"],
                    "profit": round(r["profit"], 2),
                    "coins_per_xp": round(r["coins_per_xp"], 2),
                    "hourly": round(r["hourly"], 2),
                    "total_value": round(r["total_value"], 2),
                    "meter_value": round(r["meter_value"], 2),
                }
            print(json.dumps({"name": slayer_data["name"], "tiers": json_data}, indent=2))
        else:
            # Show detailed for best hourly tier
            if best_tier:
                best_result = next(r for r in all_results if r["tier"] == best_tier)
                print_detailed(best_result, magic_find, aatrox)
            print_tier_comparison(slayer_data, all_results, aatrox)

    else:
        # Summary of all slayer types
        if args.json:
            json_output_summary(all_data, price_cache, magic_find, aatrox)
        else:
            print_summary(all_data, price_cache, magic_find, aatrox)

            # Also show tier comparisons for each type
            for sk in [k for k in all_data if not k.startswith("_")]:
                slayer_data = all_data[sk]
                all_results = []
                for tk in sorted(slayer_data["tiers"].keys(), key=int):
                    t = int(tk)
                    r = calculate_boss_profit(slayer_data, t, price_cache,
                                              magic_find, aatrox, kph)
                    if r:
                        all_results.append(r)
                print_tier_comparison(slayer_data, all_results, aatrox)

    price_cache.flush()
    status("")


if __name__ == "__main__":
    main()
