#!/usr/bin/env python3
"""Flip engine — recursive cost optimization and shared scanning logic.

Provides:
  - CostEngine: computes optimal acquisition cost for every craftable item
    (min of bazaar buy vs recursive craft cost)
  - Common flip result schema
  - Scanner functions for each flip type
"""

import json
import sys
import time
from pathlib import Path

from items import (display_name, get_all_requirements, check_requirements,
                   search_items, _load_profile_member, _load_neu_item)
from pricing import PriceCache, _fmt

DATA_DIR = Path(__file__).parent.parent / "data"
NEU_ITEMS_DIR = DATA_DIR / "neu-repo" / "items"
CRAFT_CACHE_PATH = DATA_DIR / "craft_cache.json"

MOULBERRY_LBIN_URL = "https://moulberry.codes/lowestbin.json"
MOULBERRY_AVG_LBIN_URL = "https://moulberry.codes/auction_averages_lbin/3day.json"
MOULBERRY_AVG_URL = "https://moulberry.codes/auction_averages/3day.json"
MOULBERRY_TTL = 300
MOULBERRY_EVICT = 3600

MIN_PROFIT = 10_000
MIN_VOLUME = 1
MIN_BUY_VOLUME = 50        # for sell-order flips (patient by nature, low volume OK)
LBIN_SANITY_MULT = 5       # skip AH price if LBIN > this × avg_lbin
CONTESTED_SPREAD = 60      # spreads above this % are likely contested/illiquid

# Items disabled in-game but still have NEU recipes / AH listings
DISABLED_ITEMS = {
    "SOULS_REBOUND",
}

# Margin buffer: only prefer crafting an ingredient if craft < buy * this
# From SkyCrafts — prevents false positives from bazaar spread noise
RECURSIVE_MARGIN = 0.98

# Minimum daily sell volume for an item to be considered "available on bazaar".
# If an item has sufficient bazaar supply, we use the bazaar buy price directly
# rather than recursively costing from raw materials — even if crafting from
# scratch is theoretically cheaper.  Crafting 3M Hard Stone into Enchanted Hard
# Stone may save 36% on paper, but no one actually does that.
BAZAAR_LIQUID_VOLUME = 5_000


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

        output_id = recipe_data.get("overrideOutputId", item_id)
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
            duration = r.get("duration", 0)
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


# ─── Moulberry Bulk Data ─────────────────────────────────────────────

def load_craft_cache():
    """Load the craft flip cache from disk."""
    if not CRAFT_CACHE_PATH.exists():
        return {"moulberry": {}, "collections": None, "collections_ts": 0}
    try:
        data = json.loads(CRAFT_CACHE_PATH.read_text())
        now = time.time()
        mb = data.get("moulberry", {})
        if mb and now - mb.get("ts", 0) > MOULBERRY_EVICT:
            data["moulberry"] = {}
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
    """
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

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


# ─── CostEngine: Recursive Craft Cost Optimization ──────────────────

class CostEngine:
    """Computes optimal acquisition cost for every item.

    For each item, determines whether it's cheaper to buy from bazaar
    or craft from ingredients (whose costs are themselves recursively
    optimized). Uses a 2% margin buffer to avoid false positives from
    bazaar spread noise.

    Usage:
        engine = CostEngine(price_cache, recipes)
        engine.build()
        cost = engine.get_cost("ENCHANTED_IRON")
        # Returns (cost, source) where source is "bazaar" or "craft"
    """

    def __init__(self, price_cache, recipes, recursive=True):
        self.price_cache = price_cache
        self.recursive = recursive
        # Index recipes by output item ID
        self._recipes = {}  # item_id -> recipe dict
        for r in recipes:
            # Keep first recipe per item
            if r["item_id"] not in self._recipes:
                self._recipes[r["item_id"]] = r
        # Computed costs: item_id -> (cost, source, craft_breakdown)
        # source: "bazaar", "auction", "craft", "unknown"
        # craft_breakdown: None or {ing_id: (qty, cost, source)} for craft items
        self._costs = {}
        # Items currently being computed (cycle detection)
        self._computing = set()

    def build(self):
        """Pre-compute optimal costs for all items with recipes."""
        for item_id in self._recipes:
            self._compute(item_id)

    def _compute(self, item_id):
        """Compute optimal cost for an item. Returns (cost, source, breakdown)."""
        if item_id in self._costs:
            return self._costs[item_id]

        # Cycle detection
        if item_id in self._computing:
            return self._get_market_cost(item_id)

        self._computing.add(item_id)

        # Get market price (bazaar or auction)
        market_cost, market_source, _ = self._get_market_cost(item_id)

        if not self.recursive or item_id not in self._recipes:
            result = (market_cost, market_source, None)
            self._costs[item_id] = result
            self._computing.discard(item_id)
            return result

        # Skip recursion for items with healthy bazaar liquidity.
        # Crafting 3M Hard Stone to save 36% on Enchanted Hard Stone
        # is theoretically cheaper but nobody does it.  If the item is
        # readily buyable on bazaar, just use the bazaar price.
        if market_source == "bazaar" and market_cost and market_cost > 0:
            p = self.price_cache.get_price(item_id)
            sell_vol = p.get("sell_volume", 0) or 0
            if sell_vol >= BAZAAR_LIQUID_VOLUME:
                result = (market_cost, market_source, None)
                self._costs[item_id] = result
                self._computing.discard(item_id)
                return result

        # Try crafting
        recipe = self._recipes[item_id]
        craft_total = 0
        craft_breakdown = {}
        can_craft = True

        for ing_id, qty in recipe["ingredients"].items():
            ing_cost, ing_source, _ = self._compute(ing_id)
            if ing_cost is None or ing_cost <= 0:
                can_craft = False
                break
            craft_breakdown[ing_id] = (qty, ing_cost, ing_source)
            craft_total += ing_cost * qty

        if can_craft:
            craft_cost = craft_total / recipe["output_count"]
            # Use craft cost only if meaningfully cheaper (2% margin)
            if market_cost is None or market_cost <= 0:
                result = (craft_cost, "craft", craft_breakdown)
            elif craft_cost < market_cost * RECURSIVE_MARGIN:
                result = (craft_cost, "craft", craft_breakdown)
            else:
                result = (market_cost, market_source, None)
        else:
            result = (market_cost, market_source, None)

        self._costs[item_id] = result
        self._computing.discard(item_id)
        return result

    def _get_market_cost(self, item_id):
        """Get the buy price from bazaar or auction. Returns (cost, source, None).

        Override (NPC) prices are excluded — they represent NPC sell prices
        (what you'd get for selling) or limited-stock NPC buys, neither of
        which should be treated as unlimited cheap crafting inputs.
        """
        p = self.price_cache.get_price(item_id)
        if p["source"] == "bazaar" and p.get("buy") and p["buy"] > 0:
            return (p["buy"], "bazaar", None)
        if p["source"] == "auction" and p.get("lowest_bin") and p["lowest_bin"] > 0:
            return (p["lowest_bin"], "auction", None)
        return (None, "unknown", None)

    def get_cost(self, item_id):
        """Get optimal cost for an item. Returns (cost, source, breakdown).

        If the item wasn't in the recipe list, falls back to market price.
        """
        if item_id in self._costs:
            return self._costs[item_id]
        # Not a recipe item — just market price
        return self._get_market_cost(item_id)

    def get_ingredient_cost(self, item_id, qty=1):
        """Get cost for qty of an ingredient. Returns (total_cost, source)."""
        cost, source, _ = self.get_cost(item_id)
        if cost is None:
            return None, "unknown"
        return cost * qty, source

    def explain(self, item_id, indent=0):
        """Return a string explaining the cost breakdown for an item."""
        cost, source, breakdown = self.get_cost(item_id)
        prefix = "  " * indent
        name = display_name(item_id)

        if cost is None:
            return f"{prefix}{name}: no price data"

        if source != "craft" or breakdown is None:
            return f"{prefix}{name}: {_fmt(cost)} ({source})"

        lines = [f"{prefix}{name}: {_fmt(cost)} (craft)"]
        for ing_id, (qty, ing_cost, ing_source) in sorted(breakdown.items()):
            ing_name = display_name(ing_id)
            total = ing_cost * qty
            lines.append(f"{prefix}  {qty}× {ing_name}: {_fmt(ing_cost)} ea = {_fmt(total)} ({ing_source})")
        return "\n".join(lines)


# ─── Supply/Demand Indicator ─────────────────────────────────────────

def supply_indicator(item_id, price_cache, sell_channel, sales_per_day=None):
    """Return a supply/demand indicator string.

    Bazaar items: compare buy_volume vs sell_volume
      ↑ = undersupplied (sells fill fast)
      ↓ = oversupplied (competitive)
      ≈ = balanced

    AH items: use sales/day
      ⚠ = < 1/day (illiquid)
      number = sales/day
    """
    if sell_channel == "bazaar":
        p = price_cache.get_price(item_id)
        bv = p.get("buy_volume", 0) or 0
        sv = p.get("sell_volume", 0) or 0
        if bv == 0 and sv == 0:
            return "?"
        if sv < bv * 0.8:
            return "↑"  # undersupplied
        if sv > bv * 1.2:
            return "↓"  # oversupplied
        return "≈"
    else:
        # AH item
        if sales_per_day is None:
            return "?"
        if sales_per_day < 1:
            return "⚠"
        if sales_per_day >= 10:
            return f"{sales_per_day:.0f}/d"
        return f"{sales_per_day:.1f}/d"


# ─── Scanning: Craft Flips ───────────────────────────────────────────

def _get_bazaar_item_ids(price_cache):
    """Get set of all item IDs available on the bazaar."""
    price_cache._fetch_bazaar()
    bazaar_ids = set()
    for pid, bz in price_cache._bazaar.items():
        if bz.get("buy", 0) > 0 or bz.get("sell", 0) > 0:
            bazaar_ids.add(pid)
    return bazaar_ids


def filter_bazaar_ingredient_recipes(recipes, price_cache):
    """Filter recipes to those where all ingredients are on bazaar."""
    bazaar_ids = _get_bazaar_item_ids(price_cache)

    def _on_bazaar(item_id):
        if item_id in bazaar_ids:
            return True
        resolved = price_cache._resolve_bazaar_id(item_id)
        return resolved != item_id and resolved in bazaar_ids

    return [r for r in recipes if all(_on_bazaar(ing) for ing in r["ingredients"])]


def scan_craft_flips(recipes, engine, price_cache, craft_cache,
                     use_cached_only=False, force_refresh=False, undercut_pct=5):
    """Scan crafting recipes for profitable instant flips.

    Uses CostEngine for ingredient costs (recursive by default).
    Output can sell on AH or Bazaar — whichever gives better profit.
    """
    if use_cached_only:
        mb = craft_cache.get("moulberry", {})
        lowestbin = mb.get("lowestbin", {})
        avg_lbin = mb.get("avg_lbin", {})
        auction_averages = mb.get("auction_averages", {})
    else:
        lowestbin, avg_lbin, auction_averages = fetch_moulberry_data(
            cache=craft_cache, force_refresh=force_refresh)

    sell_mult = (1 - undercut_pct / 100) * 0.99
    flips = []

    for recipe in recipes:
        item_id = recipe["item_id"]
        if item_id in DISABLED_ITEMS:
            continue

        # Calculate cost using CostEngine
        total_cost = 0
        can_price = True
        ing_sources = {}
        for ing_id, qty in recipe["ingredients"].items():
            cost, source = engine.get_ingredient_cost(ing_id, qty)
            if cost is None:
                can_price = False
                break
            total_cost += cost
            ing_sources[ing_id] = source

        if not can_price:
            continue

        cost_per = total_cost / recipe["output_count"]

        # Check both sell channels
        output_price = price_cache.get_price(item_id)
        best_profit = None
        best_channel = None
        best_sell = None
        best_avg = None
        best_sales = None

        # Bazaar instant-sell
        if output_price["source"] == "bazaar" and output_price.get("sell"):
            bz_profit = output_price["sell"] - cost_per
            if bz_profit >= MIN_PROFIT:
                best_profit = bz_profit
                best_channel = "bazaar"
                best_sell = output_price["sell"]
                best_sales = None  # continuous

        # AH
        item_avg = avg_lbin.get(item_id)
        current_lbin = lowestbin.get(item_id, 0)
        avg_data = auction_averages.get(item_id, {})
        ah_sales = avg_data.get("sales", 0) / 3.0 if avg_data else 0

        if item_avg and item_avg > 0 and current_lbin and current_lbin > 0 and ah_sales >= MIN_VOLUME:
            if current_lbin <= LBIN_SANITY_MULT * item_avg:
                ah_profit = current_lbin * sell_mult - cost_per
                if ah_profit >= MIN_PROFIT and (best_profit is None or ah_profit > best_profit):
                    best_profit = ah_profit
                    best_channel = "auction"
                    best_sell = current_lbin
                    best_avg = item_avg
                    best_sales = ah_sales

        if best_profit is None:
            continue

        indicator = supply_indicator(item_id, price_cache, best_channel, best_sales)

        flips.append({
            "type": "craft",
            "item_id": item_id,
            "cost": cost_per,
            "sell_price": best_sell,
            "avg_lbin": best_avg,
            "profit": best_profit,
            "sell_channel": best_channel,
            "sales_per_day": best_sales,
            "supply": indicator,
            "requirement": recipe["requirement"],
            "time_cost": None,
            "profit_per_hour": None,
            "input_sources": ing_sources,
        })

    flips.sort(key=lambda x: x["profit"], reverse=True)
    return flips


# ─── Scanning: Forge Flips ───────────────────────────────────────────

def scan_forge_flips(recipes, engine, price_cache, craft_cache,
                     use_cached_only=False, force_refresh=False, undercut_pct=5):
    """Scan forge recipes for profitable time-gated flips.

    Uses CostEngine for ingredient costs. Accepts mixed sources
    (bazaar + AH). Includes duration and profit/hour.
    """
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

        # Cost using CostEngine (mixed sources OK)
        total_cost = 0
        can_price = True
        ing_sources = {}
        for ing_id, qty in recipe["ingredients"].items():
            cost, source = engine.get_ingredient_cost(ing_id, qty)
            if cost is None:
                can_price = False
                break
            total_cost += cost
            ing_sources[ing_id] = source

        if not can_price:
            continue

        cost_per = total_cost / recipe["output_count"]

        # Check sell channels
        output_price = price_cache.get_price(item_id)
        sell_price = None
        sell_channel = None
        sales_per_day = None

        # Bazaar
        if output_price["source"] == "bazaar" and output_price.get("sell"):
            sell_price = output_price["sell"]
            sell_channel = "bazaar"
            sales_per_day = None

        # AH
        ah_lbin = lowestbin.get(item_id, 0)
        ah_avg = avg_lbin.get(item_id, 0)
        ah_data = auction_averages.get(item_id, {})
        ah_sales = ah_data.get("clean_sales") or ah_data.get("sales")
        ah_sales_day = ah_sales / 3.0 if ah_sales else None

        if ah_lbin and ah_lbin > 0:
            if not (ah_avg and ah_avg > 0 and ah_lbin > LBIN_SANITY_MULT * ah_avg):
                sell_mult = (1 - undercut_pct / 100) * 0.99
                ah_profit = ah_lbin * sell_mult - cost_per
                bz_profit = (sell_price - cost_per) if sell_price else 0
                if sell_channel is None or ah_profit > bz_profit:
                    sell_price = ah_lbin
                    sell_channel = "auction"
                    sales_per_day = ah_sales_day

        if sell_price is None:
            continue

        if sell_channel == "bazaar":
            profit = sell_price - cost_per
        else:
            sell_mult = (1 - undercut_pct / 100) * 0.99
            profit = sell_price * sell_mult - cost_per

        if profit < MIN_PROFIT:
            continue

        if sell_channel == "auction" and (sales_per_day is None or sales_per_day < MIN_VOLUME):
            continue

        duration = recipe.get("duration", 0)
        pph = None
        if duration and duration > 0:
            pph = profit / (duration / 3600)

        indicator = supply_indicator(item_id, price_cache, sell_channel, sales_per_day)

        flips.append({
            "type": "forge",
            "item_id": item_id,
            "cost": cost_per,
            "sell_price": sell_price,
            "avg_lbin": ah_avg if sell_channel == "auction" else None,
            "profit": profit,
            "sell_channel": sell_channel,
            "sales_per_day": sales_per_day,
            "supply": indicator,
            "requirement": recipe.get("requirement"),
            "time_cost": duration,
            "profit_per_hour": pph,
            "input_sources": ing_sources,
        })

    flips.sort(key=lambda x: x.get("profit_per_hour") or 0, reverse=True)
    return flips


# ─── Scanning: Sell-Order Flips ──────────────────────────────────────

def scan_sell_order_flips(recipes, engine, price_cache, undercut_pct=0.1):
    """Scan for crafts where you instant-buy materials and sell-order the output.

    Compares instant-buy cost vs sell-order revenue (buy price on bazaar).
    Bazaar takes a 1.125% tax on sell orders.
    """
    BZ_TAX = 0.98875

    price_cache._fetch_bazaar()

    flips = []
    for recipe in recipes:
        item_id = recipe["item_id"]
        if item_id in DISABLED_ITEMS:
            continue

        # Cost using CostEngine
        total_cost = 0
        can_price = True
        ing_sources = {}
        for ing_id, qty in recipe["ingredients"].items():
            cost, source = engine.get_ingredient_cost(ing_id, qty)
            if cost is None:
                can_price = False
                break
            total_cost += cost
            ing_sources[ing_id] = source

        if not can_price:
            continue

        cost_per = total_cost / recipe["output_count"]

        # Output must be on bazaar
        output_price = price_cache.get_price(item_id)
        if output_price["source"] != "bazaar":
            continue

        buy_price = output_price.get("buy", 0)
        sell_price = output_price.get("sell", 0)
        buy_volume = output_price.get("buy_volume", 0)

        if buy_price <= 0 or buy_volume < MIN_BUY_VOLUME:
            continue

        order_price = buy_price * (1 - undercut_pct / 100)
        revenue = order_price * BZ_TAX
        profit = revenue - cost_per

        if profit < MIN_PROFIT:
            continue

        spread = buy_price - sell_price
        spread_pct = (spread / buy_price * 100) if buy_price > 0 else 0

        indicator = supply_indicator(item_id, price_cache, "bazaar")

        flips.append({
            "type": "sell-order",
            "item_id": item_id,
            "cost": cost_per,
            "sell_price": order_price,
            "profit": profit,
            "sell_channel": "bazaar",
            "sales_per_day": None,
            "supply": indicator,
            "requirement": recipe.get("requirement"),
            "time_cost": None,
            "profit_per_hour": None,
            "buy_price": buy_price,
            "spread": spread,
            "spread_pct": spread_pct,
            "buy_volume": buy_volume,
            "contested": spread_pct > CONTESTED_SPREAD,
            "input_sources": ing_sources,
        })

    flips.sort(key=lambda x: x["profit"], reverse=True)
    return flips


# ─── Scanning: NPC Flips ─────────────────────────────────────────────

def scan_npc_flips(price_cache):
    """Scan for items that can be bought from NPCs and sold on bazaar/AH for profit.

    Uses PriceOverrides (NPC prices) as the buy cost and compares against
    bazaar sell / AH LBIN.
    """
    price_cache._load_price_overrides()
    overrides = price_cache._price_overrides or {}

    flips = []
    for item_id, npc_price in overrides.items():
        if not npc_price or npc_price <= 0:
            continue

        p = price_cache.get_price(item_id)

        if p["source"] == "bazaar" and p.get("sell") and p["sell"] > 0:
            profit = p["sell"] - npc_price
            if profit >= MIN_PROFIT:
                indicator = supply_indicator(item_id, price_cache, "bazaar")
                flips.append({
                    "type": "npc",
                    "item_id": item_id,
                    "cost": npc_price,
                    "sell_price": p["sell"],
                    "profit": profit,
                    "sell_channel": "bazaar",
                    "sales_per_day": None,
                    "supply": indicator,
                    "requirement": None,
                    "time_cost": None,
                    "profit_per_hour": None,
                })

    flips.sort(key=lambda x: x["profit"], reverse=True)
    return flips


# ─── Scanning: Bit Shop ─────────────────────────────────────────────

def scan_bit_flips(price_cache):
    """Rank bit shop items by coins/bit value."""
    bit_items = price_cache.get_all_bit_items()
    if not bit_items:
        return []

    results = []
    for item_id, bit_cost in bit_items.items():
        cpb, market_price, _ = price_cache.coins_per_bit(item_id)
        if cpb is None or cpb <= 0:
            continue

        results.append({
            "type": "bits",
            "item_id": item_id,
            "bit_cost": bit_cost,
            "market_price": market_price,
            "coins_per_bit": cpb,
        })

    results.sort(key=lambda x: x["coins_per_bit"], reverse=True)
    return results


# ─── Scanning: Kat Flips ─────────────────────────────────────────────

def _discover_pet_types():
    """Find all pet types by scanning NEU repo for *;0.json files."""
    return [p.stem.split(";")[0] for p in sorted(NEU_ITEMS_DIR.glob("*;0.json"))]


def _find_katgrade(pet_type, target_rarity):
    """Find katgrade recipe for upgrading TO the target rarity."""
    from pricing import RARITY_NAME
    pet_id = f"{pet_type};{target_rarity}"
    data = _load_neu_item(pet_id)
    if not data:
        return None
    for recipe in data.get("recipes", []):
        if recipe.get("type") == "katgrade":
            return recipe
    return None


def _get_available_rarities(pet_type):
    """Find which rarities exist for a pet type."""
    available = []
    for rarity_num in range(6):
        if _load_neu_item(f"{pet_type};{rarity_num}"):
            available.append(rarity_num)
    return available


def _parse_item_str(item_str):
    """Parse 'ENCHANTED_RABBIT:16' into (item_id, qty)."""
    parts = item_str.split(":")
    if len(parts) == 2:
        try:
            return parts[0], int(parts[1])
        except ValueError:
            return parts[0], 1
    return parts[0], 1


def _get_pet_craft_cost(pet_type, rarity_num, price_cache):
    """Calculate craft cost for a pet. Returns cost or None."""
    pet_id = f"{pet_type};{rarity_num}"
    data = _load_neu_item(pet_id)
    if not data:
        return None
    for recipe in data.get("recipes", []):
        if recipe.get("type") == "crafting":
            total = 0
            for slot in ("A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3"):
                slot_val = recipe.get(slot, "")
                if not slot_val:
                    continue
                item_id, qty = _parse_item_str(slot_val)
                p = price_cache.get_price(item_id)
                if p["source"] == "bazaar" and p.get("buy"):
                    total += p["buy"] * qty
                elif p["source"] == "auction" and p.get("lowest_bin"):
                    total += p["lowest_bin"] * qty
                else:
                    return None
            return total
    return None


def _get_pet_input_cost(pet_type, from_rarity, price_cache):
    """Get cheapest way to obtain starting pet: min(AH, craft). Returns (cost, source)."""
    start_id = f"{pet_type};{from_rarity}"
    buy = price_cache.get_price(start_id)
    ah_cost = (buy.get("lowest_bin") or 0) if buy["source"] != "unknown" else 0
    craft_cost = _get_pet_craft_cost(pet_type, from_rarity, price_cache)

    if craft_cost and craft_cost > 0:
        if ah_cost > 0:
            return (craft_cost, "craft") if craft_cost < ah_cost else (ah_cost, "AH")
        return craft_cost, "craft"
    elif ah_cost > 0:
        return ah_cost, "AH"
    return 0, "?"


def scan_kat_flips(price_cache):
    """Scan all pets with katgrade recipes, rank by full-chain profit."""
    from pricing import RARITY_NAME

    pet_types = _discover_pet_types()
    print(f"  Scanning {len(pet_types)} pet types for Kat flips...", file=sys.stderr)

    results = []
    for pet_type in pet_types:
        available = _get_available_rarities(pet_type)
        if not available:
            continue

        upgrades = [r for r in available if _find_katgrade(pet_type, r)]
        if not upgrades:
            continue

        min_rarity = upgrades[0] - 1
        max_rarity = upgrades[-1]

        # Calculate total upgrade cost
        total_coins = 0
        total_time = 0
        total_material_cost = 0
        can_price = True

        for rarity_num in range(min_rarity + 1, max_rarity + 1):
            katgrade = _find_katgrade(pet_type, rarity_num)
            if not katgrade:
                can_price = False
                break

            total_coins += katgrade.get("coins", 0)
            total_time += katgrade.get("time", 0)

            for item_str in katgrade.get("items", []):
                item_id, qty = _parse_item_str(item_str)
                p = price_cache.get_price(item_id)
                if p["source"] == "bazaar" and p.get("buy"):
                    total_material_cost += p["buy"] * qty
                elif p["source"] == "auction" and p.get("lowest_bin"):
                    total_material_cost += p["lowest_bin"] * qty
                else:
                    can_price = False
                    break
            if not can_price:
                break

        if not can_price:
            continue

        kat_total = total_coins + total_material_cost
        input_cost, input_source = _get_pet_input_cost(pet_type, min_rarity, price_cache)

        # Sell price
        sell = price_cache.get_price(f"{pet_type};{max_rarity}")
        if sell["source"] == "unknown":
            continue
        sell_val = sell.get("avg_bin") or sell.get("lowest_bin") or 0
        if sell_val <= 0:
            continue
        sales_day = sell.get("sales_day")

        profit = sell_val * 0.99 - (input_cost + kat_total)

        if profit < MIN_PROFIT:
            continue

        pph = None
        if total_time > 0:
            pph = profit / (total_time / 3600)

        from_name = RARITY_NAME.get(min_rarity, "?")
        to_name = RARITY_NAME.get(max_rarity, "?")

        results.append({
            "type": "kat",
            "item_id": f"{pet_type};{max_rarity}",
            "pet_type": pet_type,
            "from_rarity": min_rarity,
            "to_rarity": max_rarity,
            "cost": input_cost + kat_total,
            "input_cost": input_cost,
            "input_source": input_source,
            "kat_total": kat_total,
            "sell_price": sell_val,
            "profit": profit,
            "sell_channel": "auction",
            "sales_per_day": sales_day,
            "supply": supply_indicator(f"{pet_type};{max_rarity}", price_cache, "auction", sales_day),
            "requirement": None,
            "time_cost": total_time,
            "profit_per_hour": pph,
        })

    results.sort(key=lambda x: x.get("profit_per_hour") or 0, reverse=True)
    return results


# ─── Single Item Breakdown ───────────────────────────────────────────

def calculate_craft_cost(recipe, price_cache):
    """Calculate total ingredient cost using bazaar buyPrice.

    Simple non-recursive version for use by other tools (accessories, etc.).
    For recursive costing, use CostEngine instead.
    """
    total = 0
    for ing_id, qty in recipe["ingredients"].items():
        p = price_cache.get_price(ing_id)
        if p["source"] != "bazaar" or not p.get("buy"):
            return None
        total += p["buy"] * qty
    return total / recipe["output_count"]


def find_recipe(item_id, recipes=None):
    """Find a recipe for an item. Searches parsed recipes, then NEU repo."""
    if recipes:
        for r in recipes:
            if r["item_id"] == item_id:
                return r

    neu_path = NEU_ITEMS_DIR / f"{item_id}.json"
    if not neu_path.exists():
        return None

    try:
        data = json.loads(neu_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

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
