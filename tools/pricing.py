#!/usr/bin/env python3
"""Live pricing for Hypixel SkyBlock items.

Fetches real-time prices from the Hypixel Bazaar API and Coflnet auction API.
Standalone CLI: python3 pricing.py SHADOW_ASSASSIN_CHESTPLATE ENCHANTED_DIAMOND
"""

import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CACHE_PATH = Path(__file__).parent.parent / "data" / "price_cache.json"

BAZAAR_URL = "https://api.hypixel.net/v2/skyblock/bazaar"
COFLNET_BIN_URL = "https://sky.coflnet.com/api/item/price/{tag}/bin"

BAZAAR_TTL = 300       # 5 minutes
AUCTION_TTL = 600      # 10 minutes
COFLNET_RATE_LIMIT = 0.6  # seconds between requests (100/min)


def _fmt(n):
    """Format a number with K/M/B suffixes."""
    if n is None:
        return "?"
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{n:,.0f}"


class PriceCache:
    """Fetches and caches SkyBlock item prices."""

    def __init__(self):
        self._bazaar = {}       # item_id -> {buy, sell, ts}
        self._auctions = {}     # item_id -> {lowest_bin, ts}
        self._bazaar_fetched = 0
        self._last_coflnet = 0
        self._load_cache()

    def _load_cache(self):
        """Load file-backed cache if it exists."""
        if not CACHE_PATH.exists():
            return
        try:
            data = json.loads(CACHE_PATH.read_text())
            self._bazaar = data.get("bazaar", {})
            self._auctions = data.get("auctions", {})
            self._bazaar_fetched = data.get("bazaar_fetched", 0)
        except (json.JSONDecodeError, KeyError):
            pass

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
            self._bazaar[pid] = {
                "buy": qs.get("buyPrice", 0),
                "sell": qs.get("sellPrice", 0),
                "buy_volume": qs.get("buyVolume", 0),
                "sell_volume": qs.get("sellVolume", 0),
                "ts": now,
            }

        self._bazaar_fetched = now
        self._save_cache()

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
                self._save_cache()
            return

        lowest = data.get("lowest")
        self._auctions[item_id] = {"lowest_bin": lowest, "ts": now}
        self._save_cache()

    def get_price(self, item_id):
        """Get price info for an item. Returns dict with source and prices.

        Returns:
            {
                "source": "bazaar" | "auction" | "unknown",
                "buy": float | None,      # bazaar buy (instant buy) price
                "sell": float | None,      # bazaar sell (instant sell) price
                "lowest_bin": int | None,  # auction lowest BIN
            }
        """
        self._fetch_bazaar()

        # Try bazaar first
        bz = self._bazaar.get(item_id)
        if bz and bz.get("buy", 0) > 0:
            return {
                "source": "bazaar",
                "buy": bz["buy"],
                "sell": bz["sell"],
                "lowest_bin": None,
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
            }

        return {"source": "unknown", "buy": None, "sell": None, "lowest_bin": None}

    def format_price(self, item_id):
        """Return a human-readable price string for an item."""
        p = self.get_price(item_id)
        if p["source"] == "bazaar":
            return f"Bazaar: {_fmt(p['buy'])} buy / {_fmt(p['sell'])} sell"
        if p["source"] == "auction":
            return f"Lowest BIN: {_fmt(p['lowest_bin'])}"
        return "No price data"

    def get_prices_bulk(self, item_ids):
        """Get prices for multiple items. Returns {item_id: price_info}."""
        self._fetch_bazaar()  # single request for all bazaar items
        results = {}
        for item_id in item_ids:
            results[item_id] = self.get_price(item_id)
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
        display = item_id.replace("_", " ").title()
        print(f"  {display:40s} {price_str}")


if __name__ == "__main__":
    main()
