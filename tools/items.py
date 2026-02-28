#!/usr/bin/env python3
"""Hypixel API resource data — items, skills, collections.

Fetches and caches the three free resource endpoints (no API key needed):
  - /v2/resources/skyblock/items      (5,361 items with stats, requirements, etc.)
  - /v2/resources/skyblock/skills     (skill XP tables + max levels)
  - /v2/resources/skyblock/collections (collection tiers + thresholds)

All data is lazy-loaded on first access and cached to disk with a 1-day TTL.
Other tools import from this module instead of maintaining their own fetch logic.

Standalone: python3 items.py [search query]
"""

import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DATA_DIR = Path(__file__).parent.parent / "data"
ITEMS_CACHE_PATH = DATA_DIR / "items_resource.json"
SKILLS_CACHE_PATH = DATA_DIR / "skills_resource.json"
COLLECTIONS_CACHE_PATH = DATA_DIR / "collections_resource.json"

ITEMS_URL = "https://api.hypixel.net/v2/resources/skyblock/items"
SKILLS_URL = "https://api.hypixel.net/v2/resources/skyblock/skills"
COLLECTIONS_URL = "https://api.hypixel.net/v2/resources/skyblock/collections"

RESOURCE_TTL = 86400  # 1 day

# Matches Minecraft color codes like §6, §a, §l, etc.
_COLOR_CODE_RE = re.compile(r"§[0-9a-fk-or]")

# ─── Lazy-loaded module state ────────────────────────────────────────

_items_by_id = None     # item_id -> full item dict
_skills_data = None     # raw skills API response
_collections_data = None  # raw collections API response


# ─── Fetch & Cache ───────────────────────────────────────────────────

def _fetch_resource(url, cache_path):
    """Fetch a resource endpoint, using disk cache if fresh."""
    # Check disk cache
    if cache_path.exists():
        try:
            mtime = cache_path.stat().st_mtime
            if time.time() - mtime < RESOURCE_TTL:
                return json.loads(cache_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    # Fetch from API
    try:
        req = Request(url, headers={"User-Agent": "SkyblockTools/1.0"})
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        if not data.get("success"):
            # API returned failure — fall back to stale cache
            return _load_stale_cache(cache_path)
        # Write to cache
        try:
            cache_path.write_text(json.dumps(data))
        except OSError:
            pass
        return data
    except (HTTPError, URLError, OSError) as e:
        print(f"  [API fetch error for {url}: {e}]", file=sys.stderr)
        return _load_stale_cache(cache_path)


def _load_stale_cache(cache_path):
    """Load stale cache as fallback. Returns None if no cache exists."""
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return None


# ─── Items ───────────────────────────────────────────────────────────

def _ensure_items():
    """Load items index on first access."""
    global _items_by_id
    if _items_by_id is not None:
        return

    data = _fetch_resource(ITEMS_URL, ITEMS_CACHE_PATH)
    _items_by_id = {}
    if data:
        for item in data.get("items", []):
            item_id = item.get("id")
            if item_id:
                _items_by_id[item_id] = item


def get_item(item_id):
    """Get the full item dict for an item ID, or None."""
    _ensure_items()
    return _items_by_id.get(item_id)


def display_name(item_id):
    """Get the human-readable display name for an item ID.

    Uses the API's name field (clean, no color codes). Falls back to
    title-casing the item ID if not found in the API.
    """
    _ensure_items()
    item = _items_by_id.get(item_id)
    if item:
        raw = item.get("name", "")
        if raw:
            return _COLOR_CODE_RE.sub("", raw).strip()
    return item_id.replace("_", " ").title()


def get_requirements(item_id):
    """Get structured requirements for an item. Returns list of dicts or None."""
    item = get_item(item_id)
    if not item:
        return None
    reqs = item.get("requirements")
    return reqs if reqs else None


def get_stats(item_id):
    """Get base stats for an item. Returns dict or None."""
    item = get_item(item_id)
    if not item:
        return None
    return item.get("stats")


def get_tier(item_id):
    """Get rarity tier (COMMON, UNCOMMON, RARE, etc.). Returns str or None."""
    item = get_item(item_id)
    if not item:
        return None
    return item.get("tier")


def get_upgrade_costs(item_id):
    """Get essence/item upgrade costs per star. Returns list or None."""
    item = get_item(item_id)
    if not item:
        return None
    return item.get("upgrade_costs")


def get_prestige(item_id):
    """Get Kuudra prestige/upgrade chain info. Returns dict or None."""
    item = get_item(item_id)
    if not item:
        return None
    return item.get("prestige")


def get_category(item_id):
    """Get item category (SWORD, HELMET, ACCESSORY, etc.). Returns str or None."""
    item = get_item(item_id)
    if not item:
        return None
    return item.get("category")


def get_npc_sell_price(item_id):
    """Get NPC sell price. Returns int or None."""
    item = get_item(item_id)
    if not item:
        return None
    return item.get("npc_sell_price")


def search_items(query):
    """Search items by name substring (case-insensitive). Returns list of item dicts."""
    _ensure_items()
    query_lower = query.lower()
    results = []
    for item_id, item in _items_by_id.items():
        name = item.get("name", "")
        if query_lower in name.lower() or query_lower in item_id.lower():
            results.append(item)
    return results


# ─── Skills ──────────────────────────────────────────────────────────

def get_skill_data():
    """Get skills XP tables + max levels. Returns the skills dict from the API."""
    global _skills_data
    if _skills_data is None:
        _skills_data = _fetch_resource(SKILLS_URL, SKILLS_CACHE_PATH)
    if _skills_data:
        return _skills_data.get("skills", {})
    return {}


# ─── Collections ─────────────────────────────────────────────────────

def get_collections_data():
    """Get collections data. Returns (all_items, name_to_key) tuple.

    all_items: {api_key: {api_key, tiers: {tier_num: amount_required}}}
    name_to_key: {display_name_lower: same entry}
    """
    global _collections_data
    if _collections_data is None:
        _collections_data = _fetch_resource(COLLECTIONS_URL, COLLECTIONS_CACHE_PATH)

    if not _collections_data:
        return {}, {}

    colls = _collections_data.get("collections", {})
    name_to_key = {}
    all_items = {}
    for category_data in colls.values():
        items = category_data.get("items", {})
        for api_key, item_data in items.items():
            display = item_data.get("name", "")
            tiers = {}
            for t in item_data.get("tiers", []):
                tiers[t["tier"]] = t["amountRequired"]
            entry = {"api_key": api_key, "tiers": tiers}
            all_items[api_key] = entry
            if display:
                name_to_key[display.lower()] = entry

    return all_items, name_to_key


# ─── Standalone CLI ──────────────────────────────────────────────────

def main():
    _ensure_items()
    skills = get_skill_data()
    all_colls, _ = get_collections_data()

    print(f"Items API: {len(_items_by_id)} items loaded")
    print(f"Skills API: {len(skills)} skills loaded")
    print(f"Collections API: {len(all_colls)} collection items loaded")

    # Count features
    counts = {}
    for item in _items_by_id.values():
        for key in ("requirements", "upgrade_costs", "prestige", "stats",
                     "npc_sell_price", "category", "gemstone_slots"):
            if key in item:
                counts[key] = counts.get(key, 0) + 1
    print("\nFeature coverage:")
    for key, count in sorted(counts.items()):
        print(f"  {key}: {count} items")

    # Search if args provided
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        results = search_items(query)
        print(f"\nSearch '{query}': {len(results)} results")
        for item in results[:20]:
            tier = item.get("tier", "")
            cat = item.get("category", "")
            print(f"  {item['id']:<45s} {item.get('name', ''):30s} {tier:12s} {cat}")


if __name__ == "__main__":
    main()
