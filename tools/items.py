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
    Handles pet IDs like "RABBIT;4" → "Rabbit (LEGENDARY)".
    """
    _ensure_items()
    item = _items_by_id.get(item_id)
    if item:
        raw = item.get("name", "")
        if raw:
            return _COLOR_CODE_RE.sub("", raw).strip()

    # Handle pet IDs (e.g., "RABBIT;4")
    if ";" in item_id:
        _rarity_names = {0: "COMMON", 1: "UNCOMMON", 2: "RARE",
                         3: "EPIC", 4: "LEGENDARY", 5: "MYTHIC"}
        parts = item_id.split(";", 1)
        pet_name = parts[0].replace("_", " ").title()
        try:
            rarity = _rarity_names.get(int(parts[1]), parts[1])
        except ValueError:
            rarity = parts[1]
        return f"{pet_name} ({rarity})"

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


# ─── Requirement Aggregator ──────────────────────────────────────────

NEU_ITEMS_DIR = DATA_DIR / "neu-repo" / "items"
LEVELING_PATH = DATA_DIR / "neu-repo" / "constants" / "leveling.json"
LAST_PROFILE_PATH = DATA_DIR / "last_profile.json"

_ROMAN = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
    "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
}

_SLAYER_MAP = {
    "ZOMBIE": "zombie", "SPIDER": "spider", "WOLF": "wolf",
    "EMAN": "enderman", "BLAZE": "blaze", "VAMP": "vampire",
    "VAMPIRE": "vampire", "ENDERMAN": "enderman",
}


def _load_neu_item(item_id):
    """Load a NEU repo item JSON. Returns dict or None."""
    path = NEU_ITEMS_DIR / f"{item_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _parse_neu_requirements(neu_data):
    """Parse crafttext and slayer_req from NEU item data into requirement dicts."""
    reqs = []

    # slayer_req field (e.g., "EMAN_5", "WOLF_3")
    slayer_req = neu_data.get("slayer_req", "")
    if slayer_req:
        parts = slayer_req.rsplit("_", 1)
        if len(parts) == 2 and parts[0] in _SLAYER_MAP:
            try:
                level = int(parts[1])
            except ValueError:
                level = 0
            boss = _SLAYER_MAP[parts[0]]
            reqs.append({
                "type": "SLAYER",
                "slayer_boss_type": boss,
                "level": level,
                "text": f"{boss.title()} Slayer {level}",
                "source": "neu",
            })

    # crafttext field (e.g., "Requires: Redstone Dust VII")
    crafttext = neu_data.get("crafttext", "")
    if crafttext and "Requires:" in crafttext:
        req_text = crafttext.replace("Requires: ", "").replace("Requires:", "").strip()

        # Slayer in crafttext: "Wolf Slayer 3"
        slayer_match = re.match(r"(\w+)\s+Slayer\s+(\d+)", req_text)
        if slayer_match:
            boss_display = slayer_match.group(1)
            level = int(slayer_match.group(2))
            boss = boss_display.lower()
            if not any(r["type"] == "SLAYER" for r in reqs):
                reqs.append({
                    "type": "SLAYER",
                    "slayer_boss_type": boss,
                    "level": level,
                    "text": f"{boss_display} Slayer {level}",
                    "source": "neu",
                })
        # HotM: "HotM 5"
        elif re.match(r"HotM\s+(\d+)", req_text):
            m = re.match(r"HotM\s+(\d+)", req_text)
            reqs.append({
                "type": "HEART_OF_THE_MOUNTAIN",
                "tier": int(m.group(1)),
                "text": f"HotM {m.group(1)}",
                "source": "neu",
            })
        # Museum: "20 Museum Donations"
        elif re.match(r"(\d+)\s+Museum\s+Donations?", req_text):
            m = re.match(r"(\d+)\s+Museum\s+Donations?", req_text)
            reqs.append({
                "type": "MUSEUM",
                "count": int(m.group(1)),
                "text": req_text,
                "source": "neu",
            })
        # Collection: "Redstone Dust VII", "Lily Pad II"
        else:
            coll_match = re.match(r"(.+?)\s+([IVXL]+)$", req_text)
            if coll_match:
                tier = _ROMAN.get(coll_match.group(2), 0)
                if tier > 0:
                    reqs.append({
                        "type": "COLLECTION",
                        "collection_name": coll_match.group(1),
                        "tier": tier,
                        "text": req_text,
                        "source": "neu",
                    })
            else:
                # Unknown crafttext requirement
                reqs.append({
                    "type": "OTHER",
                    "text": req_text,
                    "source": "neu",
                })

    return reqs


def _normalize_api_req(req):
    """Add a text field to an API requirement for display."""
    r = dict(req)
    r["source"] = "api"
    rtype = r.get("type", "")

    if rtype == "COLLECTION":
        coll = r.get("collection", "").replace("_", " ").title()
        r["text"] = f"{coll} {r.get('tier', '')}"
    elif rtype == "SLAYER":
        boss = r.get("slayer_boss_type", "")
        r["text"] = f"{boss.title()} Slayer {r.get('level', '')}"
    elif rtype == "SKILL":
        r["text"] = f"{r.get('skill', '').title()} {r.get('level', '')}"
    elif rtype == "HEART_OF_THE_MOUNTAIN":
        r["text"] = f"HotM {r.get('tier', '')}"
    elif rtype == "DUNGEON_TIER":
        r["text"] = f"{r.get('dungeon_type', 'Catacombs').title()} Floor {r.get('tier', '')}"
    elif rtype == "DUNGEON_SKILL":
        r["text"] = f"{r.get('dungeon_type', 'Catacombs').title()} Level {r.get('level', '')}"
    else:
        r["text"] = rtype
    return r


def _reqs_match(api_req, neu_req):
    """Check if an API requirement and NEU requirement refer to the same thing."""
    if api_req["type"] != neu_req["type"]:
        return False
    if api_req["type"] == "SLAYER":
        return (api_req.get("slayer_boss_type") == neu_req.get("slayer_boss_type")
                and api_req.get("level") == neu_req.get("level"))
    if api_req["type"] == "COLLECTION":
        return api_req.get("tier") == neu_req.get("tier")
    if api_req["type"] == "HEART_OF_THE_MOUNTAIN":
        return api_req.get("tier") == neu_req.get("tier")
    return False


def get_all_requirements(item_id):
    """Get ALL known requirements for an item by combining API + NEU sources.

    Returns list of requirement dicts, each with:
        type: COLLECTION | SLAYER | SKILL | HEART_OF_THE_MOUNTAIN | DUNGEON_TIER |
              DUNGEON_SKILL | MUSEUM | OTHER
        source: "api" | "neu" | "api+neu"
        text: human-readable description
        conflict: True if API and NEU disagree (rare)
        ... plus type-specific fields
    """
    results = []

    # 1. API requirements
    api_reqs = get_requirements(item_id) or []
    api_normalized = [_normalize_api_req(r) for r in api_reqs]

    # 2. NEU requirements
    neu_data = _load_neu_item(item_id)
    neu_reqs = _parse_neu_requirements(neu_data) if neu_data else []

    # 3. Merge: find matches, flag conflicts, add unique
    matched_neu = set()
    for api_r in api_normalized:
        found_match = False
        for i, neu_r in enumerate(neu_reqs):
            if _reqs_match(api_r, neu_r):
                # Both sources agree
                merged = dict(api_r)
                merged["source"] = "api+neu"
                results.append(merged)
                matched_neu.add(i)
                found_match = True
                break
        if not found_match:
            # Check for same-type conflict
            conflict = False
            for i, neu_r in enumerate(neu_reqs):
                if api_r["type"] == neu_r["type"] and i not in matched_neu:
                    # Same type but different values — conflict
                    api_r["conflict"] = True
                    neu_r["conflict"] = True
                    results.append(api_r)
                    results.append(neu_r)
                    matched_neu.add(i)
                    conflict = True
                    break
            if not conflict:
                results.append(api_r)

    # Add NEU-only requirements
    for i, neu_r in enumerate(neu_reqs):
        if i not in matched_neu:
            results.append(neu_r)

    return results


def _load_leveling_data():
    """Load leveling data (slayer XP, catacombs XP, skill XP, HotM)."""
    if not LEVELING_PATH.exists():
        return {}
    try:
        return json.loads(LEVELING_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _load_profile_member():
    """Load the player member data from last_profile.json."""
    if not LAST_PROFILE_PATH.exists():
        return None
    try:
        data = json.loads(LAST_PROFILE_PATH.read_text())
        uuid = data.get("uuid", "")
        members = data.get("profile", {}).get("members", {})
        for key, val in members.items():
            if key.replace("-", "") == uuid:
                return val
        return None
    except (json.JSONDecodeError, OSError, KeyError):
        return None


def _xp_to_level(xp, xp_table):
    """Convert cumulative XP to level using a per-level XP table."""
    total = 0
    for i, needed in enumerate(xp_table):
        total += needed
        if xp < total:
            return i
    return len(xp_table)


def check_requirements(item_id, member=None):
    """Check if a player meets all requirements for an item.

    Args:
        item_id: The item ID to check
        member: Profile member dict (loaded from last_profile.json if None)

    Returns list of requirement dicts, each with added fields:
        met: True/False
        progress: current value (e.g., collection count, XP)
        needed: threshold value
    """
    if member is None:
        member = _load_profile_member()
    if member is None:
        return []

    reqs = get_all_requirements(item_id)
    leveling = _load_leveling_data()
    all_colls, name_to_key = get_collections_data()

    results = []
    for req in reqs:
        r = dict(req)
        rtype = r["type"]

        if rtype == "COLLECTION":
            # Resolve collection name to API key if needed
            api_key = r.get("collection")
            tier = r.get("tier", 0)
            if not api_key:
                # NEU source — resolve via name
                coll_name = r.get("collection_name", "")
                entry = name_to_key.get(coll_name.lower())
                if entry:
                    api_key = entry["api_key"]
                    r["collection"] = api_key
            # Get threshold
            coll_entry = all_colls.get(api_key, {})
            threshold = coll_entry.get("tiers", {}).get(tier, 0)
            progress = member.get("collection", {}).get(api_key, 0)
            r["met"] = progress >= threshold if threshold else False
            r["progress"] = progress
            r["needed"] = threshold

        elif rtype == "SLAYER":
            boss = r.get("slayer_boss_type", "")
            level = r.get("level", 0)
            slayer_xp = leveling.get("slayer_xp", {})
            thresholds = slayer_xp.get(boss, [])
            needed = thresholds[level - 1] if 0 < level <= len(thresholds) else 0
            current_xp = (member.get("slayer", {}).get("slayer_bosses", {})
                          .get(boss, {}).get("xp", 0))
            r["met"] = current_xp >= needed
            r["progress"] = current_xp
            r["needed"] = needed

        elif rtype == "SKILL":
            skill = r.get("skill", "").upper()
            level_needed = r.get("level", 0)
            skill_key = f"SKILL_{skill}"
            xp = member.get("player_data", {}).get("experience", {}).get(skill_key, 0)
            xp_table = leveling.get("leveling_xp", [])
            current_level = _xp_to_level(xp, xp_table)
            r["met"] = current_level >= level_needed
            r["progress"] = current_level
            r["needed"] = level_needed

        elif rtype == "HEART_OF_THE_MOUNTAIN":
            tier_needed = r.get("tier", 0)
            hotm_xp = member.get("mining_core", {}).get("experience", 0) or 0
            hotm_table = leveling.get("HOTM", [])
            current_tier = _xp_to_level(hotm_xp, hotm_table)
            r["met"] = current_tier >= tier_needed
            r["progress"] = current_tier
            r["needed"] = tier_needed

        elif rtype == "DUNGEON_TIER":
            dungeon_type = r.get("dungeon_type", "CATACOMBS").lower()
            tier = r.get("tier", 0)
            completions = (member.get("dungeons", {}).get("dungeon_types", {})
                           .get(dungeon_type, {}).get("tier_completions", {}))
            completed = completions.get(str(tier), 0)
            r["met"] = completed > 0
            r["progress"] = int(completed)
            r["needed"] = 1

        elif rtype == "DUNGEON_SKILL":
            dungeon_type = r.get("dungeon_type", "CATACOMBS").lower()
            level_needed = r.get("level", 0)
            xp = (member.get("dungeons", {}).get("dungeon_types", {})
                  .get(dungeon_type, {}).get("experience", 0))
            cata_table = leveling.get("catacombs", [])
            current_level = _xp_to_level(xp, cata_table)
            r["met"] = current_level >= level_needed
            r["progress"] = current_level
            r["needed"] = level_needed

        elif rtype == "MUSEUM":
            # Museum donation count — check profile data
            # The exact path varies; museum data isn't reliably in the API
            r["met"] = False
            r["progress"] = 0
            r["needed"] = r.get("count", 0)

        else:
            r["met"] = False
            r["progress"] = 0
            r["needed"] = 0

        results.append(r)

    return results


# ─── Standalone CLI ──────────────────────────────────────────────────

def main():
    _ensure_items()

    # If args provided, check for exact item ID or search
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])

        # If it looks like an exact item ID, show requirements directly
        exact = get_item(query.upper())
        if exact or _load_neu_item(query.upper()):
            item_id = query.upper()
            print(f"{display_name(item_id)} ({item_id})")
            reqs = get_all_requirements(item_id)
            if reqs:
                print(f"\n  Requirements ({len(reqs)}):")
                for r in reqs:
                    conflict = " [CONFLICT]" if r.get("conflict") else ""
                    print(f"    [{r['source']:7s}] {r['text']}{conflict}")

                # Check against profile if available
                checked = check_requirements(item_id)
                if checked:
                    print(f"\n  Profile check:")
                    for r in checked:
                        status = "\u2713" if r["met"] else "\u2717"
                        prog = f"{r['progress']}" if r["progress"] is not None else "?"
                        need = f"{r['needed']}" if r["needed"] is not None else "?"
                        print(f"    {status} {r['text']:30s} ({prog} / {need})")
            else:
                print("  No requirements found.")
            return

        # Fuzzy search
        results = search_items(query)
        print(f"Search '{query}': {len(results)} results")
        for item in results[:20]:
            tier = item.get("tier", "")
            cat = item.get("category", "")
            print(f"  {item['id']:<45s} {item.get('name', ''):30s} {tier:12s} {cat}")
        return

    # No args — show API stats summary
    skills = get_skill_data()
    all_colls, _ = get_collections_data()

    print(f"Items API: {len(_items_by_id)} items loaded")
    print(f"Skills API: {len(skills)} skills loaded")
    print(f"Collections API: {len(all_colls)} collection items loaded")

    counts = {}
    for item in _items_by_id.values():
        for key in ("requirements", "upgrade_costs", "prestige", "stats",
                     "npc_sell_price", "category", "gemstone_slots"):
            if key in item:
                counts[key] = counts.get(key, 0) + 1
    print("\nFeature coverage:")
    for key, count in sorted(counts.items()):
        print(f"  {key}: {count} items")


if __name__ == "__main__":
    main()
