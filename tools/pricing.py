#!/usr/bin/env python3
"""Live pricing for Hypixel SkyBlock items.

Fetches real-time prices from the Hypixel Bazaar API and Coflnet auction API.
Standalone CLI: python3 pricing.py SHADOW_ASSASSIN_CHESTPLATE ENCHANTED_DIAMOND
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_PATH = DATA_DIR / "price_cache.json"
NAME_CACHE_PATH = DATA_DIR / "display_names.json"
NEU_ITEMS_DIR = DATA_DIR / "neu-repo" / "items"

BAZAAR_URL = "https://api.hypixel.net/v2/skyblock/bazaar"
COFLNET_BIN_URL = "https://sky.coflnet.com/api/item/price/{tag}/bin"

BAZAAR_TTL = 300       # 5 minutes
AUCTION_TTL = 600      # 10 minutes
AUCTION_EVICT = 86400  # 24 hours — drop stale auction entries on load
COFLNET_RATE_LIMIT = 0.6  # seconds between requests (100/min)

# Matches Minecraft color codes like §6, §a, §l, etc.
_COLOR_CODE_RE = re.compile(r"§[0-9a-fk-or]")

# Loaded lazily on first use
_display_names = None


def _fmt(n):
    """Format a number with K/M/B suffixes."""
    if n is None:
        return "?"
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        val = n / 1_000_000
        return f"{val:.1f}B" if val >= 999.95 else f"{val:.1f}M"
    if n >= 1_000:
        val = n / 1_000
        return f"{val:.1f}M" if val >= 999.95 else f"{val:.1f}K"
    return f"{n:,.0f}"


def _build_display_names():
    """Build display name cache from NEU repo items."""
    names = {}
    if not NEU_ITEMS_DIR.exists():
        return names
    for path in NEU_ITEMS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text())
            raw_name = data.get("displayname", "")
            if raw_name:
                clean = _COLOR_CODE_RE.sub("", raw_name).strip()
                item_id = path.stem
                # Only store if the clean name differs from the default formatting
                default = item_id.replace("_", " ").title()
                if clean and clean != default:
                    names[item_id] = clean
        except (json.JSONDecodeError, OSError):
            continue
    return names


def _load_display_names():
    """Load display names, building cache if needed."""
    global _display_names
    if _display_names is not None:
        return _display_names

    # Try loading from cache
    if NAME_CACHE_PATH.exists():
        try:
            # Rebuild if NEU repo is newer than cache
            neu_mtime = max(
                (f.stat().st_mtime for f in NEU_ITEMS_DIR.glob("*.json")),
                default=0,
            ) if NEU_ITEMS_DIR.exists() else 0
            cache_mtime = NAME_CACHE_PATH.stat().st_mtime
            if cache_mtime >= neu_mtime:
                _display_names = json.loads(NAME_CACHE_PATH.read_text())
                return _display_names
        except (json.JSONDecodeError, OSError):
            pass

    # Build from NEU repo
    _display_names = _build_display_names()
    try:
        NAME_CACHE_PATH.write_text(json.dumps(_display_names, indent=2, sort_keys=True))
    except OSError:
        pass
    return _display_names


def display_name(item_id):
    """Get the human-readable display name for an item ID."""
    names = _load_display_names()
    return names.get(item_id, item_id.replace("_", " ").title())


class PriceCache:
    """Fetches and caches SkyBlock item prices."""

    def __init__(self):
        self._bazaar = {}       # item_id -> {buy, sell, buy_volume, sell_volume, ts}
        self._auctions = {}     # item_id -> {lowest_bin, ts}
        self._bazaar_fetched = 0
        self._last_coflnet = 0
        self._dirty = False
        self._load_cache()

    def _load_cache(self):
        """Load file-backed cache if it exists, evicting stale auction entries."""
        if not CACHE_PATH.exists():
            return
        try:
            data = json.loads(CACHE_PATH.read_text())
            self._bazaar = data.get("bazaar", {})
            self._bazaar_fetched = data.get("bazaar_fetched", 0)
            # Evict auction entries older than 24h
            now = time.time()
            self._auctions = {
                k: v for k, v in data.get("auctions", {}).items()
                if now - v.get("ts", 0) < AUCTION_EVICT
            }
            if len(self._auctions) < len(data.get("auctions", {})):
                self._dirty = True  # will save cleaned cache on next flush
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
            "auctions": self._auctions,
            "bazaar_fetched": self._bazaar_fetched,
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
            req = Request(BAZAAR_URL, headers={"User-Agent": "SkyblockProfile/1.0"})
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

    def _fetch_auction(self, item_id):
        """Fetch lowest BIN for a single item via Coflnet."""
        now = time.time()

        # Check cache freshness
        cached = self._auctions.get(item_id)
        if cached and now - cached.get("ts", 0) < AUCTION_TTL:
            return

        # Rate limiting
        wait = self._last_coflnet + COFLNET_RATE_LIMIT - now
        if wait > 0:
            time.sleep(wait)

        try:
            url = COFLNET_BIN_URL.format(tag=item_id)
            req = Request(url, headers={"User-Agent": "SkyblockProfile/1.0"})
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            self._last_coflnet = time.time()
        except (HTTPError, URLError, OSError) as e:
            self._last_coflnet = time.time()
            # 404 means item not on AH — cache that too
            if isinstance(e, HTTPError) and e.code == 404:
                self._auctions[item_id] = {"lowest_bin": None, "ts": now}
                self._dirty = True
            return

        lowest = data.get("lowest")
        self._auctions[item_id] = {"lowest_bin": lowest, "ts": now}
        self._dirty = True

    def get_price(self, item_id):
        """Get price info for an item. Returns dict with source and prices.

        Returns:
            {
                "source": "bazaar" | "auction" | "unknown",
                "buy": float | None,      # what you pay to instant-buy
                "sell": float | None,      # what you receive from instant-sell
                "lowest_bin": int | None,  # auction lowest BIN
                "buy_volume": int | None,  # bazaar buy order volume
                "sell_volume": int | None, # bazaar sell order volume
            }
        """
        self._fetch_bazaar()

        # Try bazaar first
        bz = self._bazaar.get(item_id)
        if bz and (bz.get("buy", 0) > 0 or bz.get("sell", 0) > 0):
            return {
                "source": "bazaar",
                "buy": bz["buy"],
                "sell": bz["sell"],
                "lowest_bin": None,
                "buy_volume": bz.get("buy_volume", 0),
                "sell_volume": bz.get("sell_volume", 0),
            }

        # Fall back to auction
        self._fetch_auction(item_id)
        ah = self._auctions.get(item_id)
        if ah and ah.get("lowest_bin") is not None:
            return {
                "source": "auction",
                "buy": None,
                "sell": None,
                "lowest_bin": ah["lowest_bin"],
                "buy_volume": None,
                "sell_volume": None,
            }

        return {"source": "unknown", "buy": None, "sell": None,
                "lowest_bin": None, "buy_volume": None, "sell_volume": None}

    def format_price(self, item_id):
        """Return a human-readable price string for an item."""
        p = self.get_price(item_id)
        if p["source"] == "bazaar":
            vol = min(p.get("buy_volume", 0) or 0, p.get("sell_volume", 0) or 0)
            price = f"Bazaar: {_fmt(p['buy'])} buy / {_fmt(p['sell'])} sell"
            if vol < 1000:
                price += " (thin market)"
            return price
        if p["source"] == "auction":
            return f"Lowest BIN: {_fmt(p['lowest_bin'])}"
        return "No price data"

    def get_prices_bulk(self, item_ids):
        """Get prices for multiple items. Returns {item_id: price_info}."""
        self._fetch_bazaar()  # single request for all bazaar items
        results = {}
        for item_id in item_ids:
            results[item_id] = self.get_price(item_id)
        self.flush()
        return results

    def export(self):
        """Export all cached price data for saving to last_profile.json."""
        return {
            "bazaar_products": len(self._bazaar),
            "auction_items": len(self._auctions),
            "bazaar_fetched": self._bazaar_fetched,
            "bazaar": {k: {"buy": v["buy"], "sell": v["sell"]}
                       for k, v in self._bazaar.items()
                       if v.get("buy", 0) > 0 or v.get("sell", 0) > 0},
            "auctions": {k: v.get("lowest_bin")
                         for k, v in self._auctions.items()
                         if v.get("lowest_bin") is not None},
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 pricing.py ITEM_ID [ITEM_ID ...]")
        print("Example: python3 pricing.py SHADOW_ASSASSIN_CHESTPLATE ENCHANTED_DIAMOND")
        sys.exit(1)

    cache = PriceCache()
    for item_id in sys.argv[1:]:
        item_id = item_id.upper()
        price_str = cache.format_price(item_id)
        print(f"  {display_name(item_id):40s} {price_str}")
    cache.flush()


if __name__ == "__main__":
    main()
