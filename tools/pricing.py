#!/usr/bin/env python3
"""Live pricing for Hypixel SkyBlock items.

Fetches real-time prices from the Hypixel Bazaar API and Moulberry bulk auction APIs.
Standalone CLI:
    python3 pricing.py SHADOW_ASSASSIN_CHESTPLATE ENCHANTED_DIAMOND
    python3 pricing.py "RABBIT;4"              # Pet by ID
    python3 pricing.py "rabbit legendary"       # Pet by name + rarity
    python3 pricing.py rabbit                   # Show all pet rarities
"""

import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from items import display_name, get_items_data  # noqa: F401 — re-exported for backwards compat

DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_PATH = DATA_DIR / "price_cache.json"

BAZAAR_URL = "https://api.hypixel.net/v2/skyblock/bazaar"
MOULBERRY_LBIN_URL = "https://moulberry.codes/lowestbin.json"
MOULBERRY_AVG_LBIN_URL = "https://moulberry.codes/auction_averages_lbin/3day.json"
MOULBERRY_AVG_URL = "https://moulberry.codes/auction_averages/3day.json"
SKYHELPER_PRICES_URL = "https://raw.githubusercontent.com/SkyHelperBot/Prices/main/pricesV2.json"

BAZAAR_TTL = 300       # 5 minutes
MOULBERRY_TTL = 300    # 5 minutes
SKYHELPER_TTL = 600    # 10 minutes
MOULBERRY_EVICT = 3600 # 1 hour — drop stale bulk data on load

EXTERNAL_DIR = DATA_DIR / "external"
PRICE_OVERRIDES_PATH = EXTERNAL_DIR / "PriceOverrides.json"
BIT_PRICES_PATH = EXTERNAL_DIR / "BitPrices.json"

# Pet rarity name → numeric ID used in pet item IDs (e.g., RABBIT;4 = legendary)
RARITY_NUM = {
    "common": 0, "uncommon": 1, "rare": 2,
    "epic": 3, "legendary": 4, "mythic": 5,
}
RARITY_NAME = {v: k.upper() for k, v in RARITY_NUM.items()}


def _fmt(n):
    """Format a number with K/M/B suffixes."""
    if n is None:
        return "?"
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        val = n / 1_000_000
        if val >= 999.95:
            return f"{n / 1_000_000_000:.1f}B"
        return f"{val:.1f}M"
    if n >= 1_000:
        val = n / 1_000
        if val >= 999.95:
            return f"{n / 1_000_000:.1f}M"
        return f"{val:.1f}K"
    return f"{n:,.0f}"


class PriceCache:
    """Fetches and caches SkyBlock item prices.

    Price resolution order:
    1. SkyHelper variant price (attribute rolls, skins, shiny, editioned, pet level)
    2. Bazaar weighted average
    3. Moulberry LBIN / avg_lbin_3d
    4. PriceOverrides (NPC prices, manual overrides for untradeable items)
    5. Craft cost (handled externally by networth.py)
    """

    def __init__(self):
        self._bazaar = {}       # item_id -> {buy, sell, buy_volume, sell_volume, ts}
        self._bazaar_fetched = 0
        # Moulberry bulk data
        self._moulberry_lbin = {}       # item_id -> price
        self._moulberry_avg_lbin = {}   # item_id -> price
        self._moulberry_avg = {}        # item_id -> {price, count, sales, ...}
        self._moulberry_fetched = 0
        # SkyHelper prices (variant-aware: attribute rolls, skins, pets by level)
        self._skyhelper = {}            # variant_key -> price
        self._skyhelper_fetched = 0
        # PriceOverrides (NPC prices, manual overrides)
        self._price_overrides = None    # lazy loaded from disk
        # BitPrices (bits shop item costs)
        self._bit_prices = None         # lazy loaded from disk
        self._dirty = False
        self._name_to_bz_id = None  # lazy: display name -> bazaar product ID
        self._load_cache()

    def _load_cache(self):
        """Load file-backed cache if it exists."""
        if not CACHE_PATH.exists():
            return
        try:
            data = json.loads(CACHE_PATH.read_text())
            self._bazaar = data.get("bazaar", {})
            self._bazaar_fetched = data.get("bazaar_fetched", 0)
            # Load Moulberry data, evicting if stale
            now = time.time()
            mb = data.get("moulberry", {})
            if mb and now - mb.get("ts", 0) < MOULBERRY_EVICT:
                self._moulberry_lbin = mb.get("lowestbin", {})
                self._moulberry_avg_lbin = mb.get("avg_lbin", {})
                self._moulberry_avg = mb.get("auction_averages", {})
                self._moulberry_fetched = mb.get("ts", 0)
            elif mb:
                self._dirty = True  # will save cleaned cache on next flush
            # Load SkyHelper data, evicting if stale
            sh = data.get("skyhelper", {})
            if sh and now - sh.get("ts", 0) < MOULBERRY_EVICT:
                self._skyhelper = sh.get("prices", {})
                self._skyhelper_fetched = sh.get("ts", 0)
            elif sh:
                self._dirty = True
        except (json.JSONDecodeError, KeyError):
            pass

    def flush(self):
        """Write cache to disk if changed. Call when done fetching prices."""
        if self._dirty:
            self._save_cache()
            self._dirty = False

    def _save_cache(self):
        """Persist cache to disk."""
        data = {
            "bazaar": self._bazaar,
            "bazaar_fetched": self._bazaar_fetched,
            "moulberry": {
                "lowestbin": self._moulberry_lbin,
                "avg_lbin": self._moulberry_avg_lbin,
                "auction_averages": self._moulberry_avg,
                "ts": self._moulberry_fetched,
            },
            "skyhelper": {
                "prices": self._skyhelper,
                "ts": self._skyhelper_fetched,
            },
        }
        try:
            CACHE_PATH.write_text(json.dumps(data, indent=2))
        except OSError:
            pass

    def _fetch_bazaar(self):
        """Fetch all bazaar products. Single request, no API key needed."""
        now = time.time()
        if now - self._bazaar_fetched < BAZAAR_TTL:
            return  # still fresh

        try:
            req = Request(BAZAAR_URL, headers={"User-Agent": "SkyblockTools/1.0"})
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
        except (HTTPError, URLError, OSError) as e:
            print(f"  [Bazaar API error: {e}]", file=sys.stderr)
            return  # fall back to stale cache

        if not data.get("success"):
            return

        for pid, product in data.get("products", {}).items():
            qs = product.get("quick_status", {})
            # API fields match the player's perspective directly:
            #   buyPrice  = instant-buy price  = what YOU pay to buy instantly
            #   sellPrice = instant-sell price = what YOU receive when selling instantly
            self._bazaar[pid] = {
                "buy": qs.get("buyPrice", 0),     # what you pay to instant-buy
                "sell": qs.get("sellPrice", 0),    # what you get from instant-sell
                "buy_volume": qs.get("buyVolume", 0),
                "sell_volume": qs.get("sellVolume", 0),
                "ts": now,
            }

        self._bazaar_fetched = now
        self._dirty = True

    def _fetch_moulberry(self):
        """Fetch all three Moulberry bulk datasets (LBIN, avg LBIN, avg BIN)."""
        now = time.time()
        if now - self._moulberry_fetched < MOULBERRY_TTL:
            return  # still fresh

        urls = {
            "lowestbin": MOULBERRY_LBIN_URL,
            "avg_lbin": MOULBERRY_AVG_LBIN_URL,
            "auction_averages": MOULBERRY_AVG_URL,
        }

        for key, url in urls.items():
            try:
                req = Request(url, headers={"User-Agent": "SkyblockTools/1.0"})
                with urlopen(req, timeout=15) as resp:
                    result = json.loads(resp.read())
                if key == "lowestbin":
                    self._moulberry_lbin = result
                elif key == "avg_lbin":
                    self._moulberry_avg_lbin = result
                else:
                    self._moulberry_avg = result
            except (HTTPError, URLError, OSError) as e:
                print(f"  [Moulberry {key} error: {e}]", file=sys.stderr)
                # Keep stale data on failure

        self._moulberry_fetched = now
        self._dirty = True

    def _fetch_skyhelper(self):
        """Fetch SkyHelper variant-aware prices (attribute rolls, skins, pets by level)."""
        now = time.time()
        if now - self._skyhelper_fetched < SKYHELPER_TTL:
            return

        try:
            req = Request(SKYHELPER_PRICES_URL, headers={"User-Agent": "SkyblockTools/1.0"})
            with urlopen(req, timeout=30) as resp:
                self._skyhelper = json.loads(resp.read())
            self._skyhelper_fetched = now
            self._dirty = True
        except (HTTPError, URLError, OSError) as e:
            print(f"  [SkyHelper prices error: {e}]", file=sys.stderr)

    def _load_price_overrides(self):
        """Load NPC/manual price overrides from disk (lazy, once).

        PriceOverrides.json has two sections:
        - "manual": manually set prices (e.g., KUUDRA_TEETH=10K, HEAVY_PEARL=10K)
        - "automatic": NPC sell prices for vanilla items (DIAMOND=8, GOLD_INGOT=4)
        """
        if self._price_overrides is not None:
            return
        self._price_overrides = {}
        if PRICE_OVERRIDES_PATH.exists():
            try:
                data = json.loads(PRICE_OVERRIDES_PATH.read_text())
                for section_name in ("manual", "automatic"):
                    section = data.get(section_name, {})
                    if isinstance(section, dict):
                        for item_id, price in section.items():
                            if isinstance(price, (int, float)) and price > 0:
                                self._price_overrides[item_id] = price
            except (json.JSONDecodeError, OSError):
                pass

    def get_override_price(self, item_id):
        """Get NPC/manual override price for an item. Returns price or None."""
        self._load_price_overrides()
        return self._price_overrides.get(item_id)

    def _load_bit_prices(self):
        """Load bits shop costs from disk (lazy, once)."""
        if self._bit_prices is not None:
            return
        self._bit_prices = {}
        if BIT_PRICES_PATH.exists():
            try:
                data = json.loads(BIT_PRICES_PATH.read_text())
                if isinstance(data, dict):
                    for item_id, bits in data.items():
                        if isinstance(bits, (int, float)) and bits > 0:
                            self._bit_prices[item_id] = int(bits)
            except (json.JSONDecodeError, OSError):
                pass

    def get_bit_cost(self, item_id):
        """Get bits shop cost for an item. Returns bit cost or None."""
        self._load_bit_prices()
        return self._bit_prices.get(item_id)

    def coins_per_bit(self, item_id):
        """Get coins-per-bit value for a bits shop item.

        Returns (coins_per_bit, market_price, bit_cost) or (None, None, None).
        """
        bit_cost = self.get_bit_cost(item_id)
        if not bit_cost:
            return None, None, None
        market_price = self.weighted(item_id)
        if not market_price or market_price <= 0:
            return None, None, None
        return market_price / bit_cost, market_price, bit_cost

    def get_all_bit_items(self):
        """Get all bits shop items with their costs. Returns dict of item_id → bit_cost."""
        self._load_bit_prices()
        return dict(self._bit_prices)

    def get_skyhelper_price(self, variant_key):
        """Get SkyHelper variant price. Returns price or None."""
        self._fetch_skyhelper()
        return self._skyhelper.get(variant_key)

    @staticmethod
    def build_variant_key(item_id, item_nbt=None):
        """Build a SkyHelper variant key from item ID and NBT data.

        Checks for attribute rolls, skins, shiny flag, and edition.
        Returns the most specific variant key, or None if no variant applies.
        """
        if not item_nbt:
            return None

        keys = []

        # Attribute rolls (Kuudra gear): ITEM_ROLL_ATTR1_ROLL_ATTR2
        attributes = item_nbt.get("attributes")
        if attributes and isinstance(attributes, dict) and len(attributes) >= 2:
            # Sort attributes alphabetically for consistent key
            sorted_attrs = sorted(attributes.keys())
            roll_suffix = "_".join(f"ROLL_{a.upper()}" for a in sorted_attrs[:2])
            keys.append(f"{item_id}_{roll_suffix}")

        # Skinned: ITEM_SKINNED_SKINNAME
        skin = item_nbt.get("skin")
        if skin:
            keys.append(f"{item_id}_SKINNED_{skin}")

        # Shiny: ITEM_SHINY
        if item_nbt.get("is_shiny"):
            keys.append(f"{item_id}_SHINY")

        # Editioned: ITEM_EDITIONED
        if item_nbt.get("edition") is not None:
            keys.append(f"{item_id}_EDITIONED")

        return keys if keys else None

    @staticmethod
    def build_pet_variant_key(pet_type, rarity_num, level=None):
        """Build SkyHelper pet variant key with level.

        Returns keys like LVL_100_LEGENDARY_RABBIT.
        """
        rarity_name = RARITY_NAME.get(rarity_num, "").upper()
        if not rarity_name:
            return None
        if level is not None:
            return f"LVL_{level}_{rarity_name}_{pet_type}"
        return None

    def _resolve_bazaar_id(self, item_id):
        """Resolve an item ID to its Bazaar product ID.

        Some items use different internal IDs on the Bazaar vs the item/NEU repo.
        E.g., "Drill Motor" is DRILL_MOTOR in common usage but DRILL_ENGINE on
        Bazaar; "Fuel Canister" is FUEL_CANISTER but FUEL_TANK on Bazaar.

        Falls back to display-name matching against Bazaar product names.
        """
        if item_id in self._bazaar:
            return item_id
        # Build reverse lookup: display name -> bazaar product ID (once)
        if self._name_to_bz_id is None:
            self._name_to_bz_id = {}
            try:
                items_data = get_items_data()
                for item in items_data:
                    iid = item.get("id", "")
                    if iid in self._bazaar:
                        name = item.get("name", "").lower().strip()
                        if name:
                            self._name_to_bz_id[name] = iid
            except Exception:
                pass
        # Look up the display name of the requested ID and find the bazaar equivalent
        name = display_name(item_id).lower().strip()
        return self._name_to_bz_id.get(name, item_id)

    def get_price(self, item_id):
        """Get price info for an item. Returns dict with source and prices.

        Pet IDs (containing ";") skip bazaar and go straight to auction data.
        If the exact ID isn't found on the Bazaar, resolves via display name
        to handle ID mismatches (e.g., DRILL_MOTOR -> DRILL_ENGINE).

        Returns:
            {
                "source": "bazaar" | "auction" | "unknown",
                "buy": float | None,      # what you pay to instant-buy (bazaar)
                "sell": float | None,      # what you receive from instant-sell (bazaar)
                "lowest_bin": int | None,  # auction lowest BIN
                "avg_bin": float | None,   # 3-day average lowest BIN
                "sales_day": float | None, # estimated daily sales volume
                "buy_volume": int | None,  # bazaar buy order volume
                "sell_volume": int | None, # bazaar sell order volume
            }
        """
        is_pet = ";" in item_id

        if not is_pet:
            self._fetch_bazaar()

            # Resolve ID mismatches (e.g., DRILL_MOTOR -> DRILL_ENGINE)
            bz_id = self._resolve_bazaar_id(item_id)

            # Try bazaar first
            bz = self._bazaar.get(bz_id)
            if bz and (bz.get("buy", 0) > 0 or bz.get("sell", 0) > 0):
                return {
                    "source": "bazaar",
                    "buy": bz["buy"],
                    "sell": bz["sell"],
                    "lowest_bin": None,
                    "avg_bin": None,
                    "sales_day": None,
                    "buy_volume": bz.get("buy_volume", 0),
                    "sell_volume": bz.get("sell_volume", 0),
                }

        # Fall back to auction (Moulberry bulk data)
        self._fetch_moulberry()
        lbin = self._moulberry_lbin.get(item_id)
        avg_lbin = self._moulberry_avg_lbin.get(item_id)
        avg_data = self._moulberry_avg.get(item_id, {})

        if lbin is not None:
            # Moulberry avg data has "price" (avg BIN), "count" (auctions),
            # "sales" (actual sales), "clean_price", "clean_sales"
            sales = avg_data.get("clean_sales") or avg_data.get("sales")
            # sales is total over 3 days, convert to daily
            sales_day = sales / 3.0 if sales else None
            return {
                "source": "auction",
                "buy": None,
                "sell": None,
                "lowest_bin": int(lbin),
                "avg_bin": avg_lbin,
                "sales_day": sales_day,
                "buy_volume": None,
                "sell_volume": None,
            }

        # Fall back to PriceOverrides (NPC prices, manual overrides)
        override = self.get_override_price(item_id)
        if override is not None and override > 0:
            return {
                "source": "override",
                "buy": None, "sell": None,
                "lowest_bin": int(override),
                "avg_bin": None, "sales_day": None,
                "buy_volume": None, "sell_volume": None,
            }

        return {"source": "unknown", "buy": None, "sell": None,
                "lowest_bin": None, "avg_bin": None, "sales_day": None,
                "buy_volume": None, "sell_volume": None}

    def format_price(self, item_id):
        """Return a human-readable price string for an item."""
        p = self.get_price(item_id)
        base = ""
        if p["source"] == "bazaar":
            vol = min(p.get("buy_volume", 0) or 0, p.get("sell_volume", 0) or 0)
            base = f"Bazaar: {_fmt(p['buy'])} buy / {_fmt(p['sell'])} sell"
            if vol < 1000:
                base += " (thin market)"
        elif p["source"] == "auction":
            parts = [f"Lowest BIN: {_fmt(p['lowest_bin'])}"]
            if p.get("avg_bin") is not None:
                parts.append(f"avg: {_fmt(p['avg_bin'])}")
            if p.get("sales_day") is not None:
                parts.append(f"{p['sales_day']:.0f}/day")
            # Flag likely LBIN manipulation
            lbin = p.get("lowest_bin") or 0
            avg = p.get("avg_bin") or 0
            if lbin and avg and avg > 0 and lbin > 3 * avg:
                parts.append("⚠️ LBIN may be manipulated")
            base = "  ".join(parts)
        elif p["source"] == "override":
            base = f"NPC/Override: {_fmt(p['lowest_bin'])}"
        else:
            base = "No price data"

        # Append bits info if available
        cpb, market_price, bit_cost = self.coins_per_bit(item_id)
        if cpb is not None:
            base += f"  │  Bits: {bit_cost:,} → {cpb:,.1f} coins/bit"

        return base

    def weighted(self, item_id):
        """Get weighted average price for an item.

        For Bazaar items:
            weighted = (buy_price × buy_volume + sell_price × sell_volume)
                       / (buy_volume + sell_volume)
        For AH items: returns LBIN with manipulation guard — if LBIN > 5×
            the 3-day avg, uses avg instead (matches crafts.py sanity check).
        For overrides: returns the override price.
        Returns None if no price data.
        """
        p = self.get_price(item_id)
        if p["source"] == "bazaar":
            buy = p.get("buy") or 0
            sell = p.get("sell") or 0
            bv = p.get("buy_volume") or 0
            sv = p.get("sell_volume") or 0
            total_vol = bv + sv
            if total_vol > 0 and (buy > 0 or sell > 0):
                return (buy * bv + sell * sv) / total_vol
            return buy or sell or None
        if p["source"] in ("auction", "override"):
            lbin = p.get("lowest_bin")
            avg = p.get("avg_bin")
            # LBIN manipulation guard: if LBIN > 5× avg, use avg instead
            if lbin and avg and avg > 0 and lbin > 5 * avg:
                return avg
            return lbin or avg or None
        return None

    def variant_price(self, item_id, item_nbt=None):
        """Get the best price for an item, checking variant-specific pricing first.

        Tries SkyHelper variant keys (attribute rolls, skins, shiny, editioned)
        before falling back to standard weighted price.

        Returns (price, variant_key_used) or (price, None) if base price used.
        """
        if item_nbt:
            variant_keys = self.build_variant_key(item_id, item_nbt)
            if variant_keys:
                self._fetch_skyhelper()
                for vk in variant_keys:
                    sh_price = self._skyhelper.get(vk)
                    if sh_price is not None and sh_price > 0:
                        return sh_price, vk
        # Fall back to standard pricing
        return self.weighted(item_id), None

    def get_prices_bulk(self, item_ids):
        """Get prices for multiple items. Returns {item_id: price_info}."""
        self._fetch_bazaar()  # single request for all bazaar items
        self._fetch_moulberry()  # single bulk fetch for all auction items
        self._fetch_skyhelper()  # single bulk fetch for variant prices
        results = {}
        for item_id in item_ids:
            results[item_id] = self.get_price(item_id)
        self.flush()
        return results

    def export(self):
        """Export all cached price data for saving to last_profile.json."""
        return {
            "bazaar_products": len(self._bazaar),
            "auction_items": len(self._moulberry_lbin),
            "skyhelper_items": len(self._skyhelper),
            "bazaar_fetched": self._bazaar_fetched,
            "moulberry_fetched": self._moulberry_fetched,
            "skyhelper_fetched": self._skyhelper_fetched,
            "bazaar": {k: {"buy": v["buy"], "sell": v["sell"]}
                       for k, v in self._bazaar.items()
                       if v.get("buy", 0) > 0 or v.get("sell", 0) > 0},
            "auctions": {k: int(v)
                         for k, v in self._moulberry_lbin.items()},
        }


def resolve_pet_input(raw):
    """Resolve pet-friendly input to a pet item ID.

    Returns:
        (item_id, show_all_rarities) — if show_all_rarities is True,
        item_id is just the pet type (e.g., "RABBIT") and caller should
        show all rarities.
    """
    raw = raw.strip()

    # Already a pet ID like "RABBIT;4"
    if ";" in raw:
        return raw.upper(), False

    # Try "rabbit legendary" or "RABBIT LEGENDARY" format
    parts = raw.split()
    if len(parts) >= 2:
        rarity_word = parts[-1].lower()
        if rarity_word in RARITY_NUM:
            pet_type = "_".join(parts[:-1]).upper()
            return f"{pet_type};{RARITY_NUM[rarity_word]}", False

    # Bare name — might be a pet, might be a regular item
    return raw.upper(), True


def _is_pet_type(pet_type, cache):
    """Check if a pet type exists in Moulberry data (any rarity)."""
    cache._fetch_moulberry()
    for rarity_num in range(6):
        pet_id = f"{pet_type};{rarity_num}"
        if pet_id in cache._moulberry_lbin:
            return True
    return False


def _show_all_pet_rarities(pet_type, cache):
    """Show prices for all available rarities of a pet."""
    cache._fetch_moulberry()
    found_any = False
    for rarity_num in range(6):
        pet_id = f"{pet_type};{rarity_num}"
        p = cache.get_price(pet_id)
        if p["source"] != "unknown":
            name = display_name(pet_id)
            price_str = cache.format_price(pet_id)
            print(f"  {name:40s} {price_str}")
            found_any = True
    if not found_any:
        print(f"  No auction data for pet: {pet_type}")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print("Usage: python3 pricing.py ITEM_ID [ITEM_ID ...]")
        print("       python3 pricing.py \"RABBIT;4\"              # Pet by ID")
        print("       python3 pricing.py \"rabbit legendary\"       # Pet by name + rarity")
        print("       python3 pricing.py rabbit                   # All pet rarities")
        sys.exit(0 if sys.argv[1:] and sys.argv[1] in ("--help", "-h") else 1)

    cache = PriceCache()

    for raw_arg in sys.argv[1:]:
        item_id, show_all = resolve_pet_input(raw_arg)

        if show_all and _is_pet_type(item_id, cache):
            _show_all_pet_rarities(item_id, cache)
        else:
            price_str = cache.format_price(item_id)
            print(f"  {display_name(item_id):40s} {price_str}")

    cache.flush()


if __name__ == "__main__":
    main()
