#!/usr/bin/env python3
"""Dungeon Profit Calculator for Hypixel SkyBlock.

Calculates expected profit per run for each dungeon floor based on drop
tables and current market prices. Shows per-chest EV, OPEN/SKIP verdicts,
Kismet Feather reroll analysis, and RNG drop breakdown.

Data is parsed from the fandom wiki (hypixel-skyblock.fandom.com), cached
locally as data/dungeon_loot.json with a 24-hour TTL. Use --refresh to
force re-scrape.

Usage:
    python3 dungeons.py                           # all floors summary
    python3 dungeons.py --floor f7                # detailed F7 breakdown
    python3 dungeons.py --floor m5                # Master Mode 5
    python3 dungeons.py --talisman ring           # Treasure Talisman tier
    python3 dungeons.py --luck 5                  # Boss Luck level
    python3 dungeons.py --no-splus                # base rates instead of S+
    python3 dungeons.py --runs-per-hour 6         # override runs/hr
    python3 dungeons.py --json                    # machine-readable output
    python3 dungeons.py --refresh                 # force re-scrape wiki
"""

import argparse
import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from items import display_name, get_items_data
from pricing import PriceCache, _fmt

DATA_DIR = Path(__file__).parent.parent / "data"
WIKI_DIR = DATA_DIR / "wiki"
LOOT_CACHE_PATH = DATA_DIR / "dungeon_loot.json"
LOOT_CACHE_TTL = 86400  # 24 hours

FANDOM_LOOT_URL = "https://hypixel-skyblock.fandom.com/wiki/Dungeon_Reward_Chest/Loot"

# Threshold below which a drop is classified as "RNG drop"
RNG_THRESHOLD = 1.0  # percent

# Default runs/hour estimates by floor (conservative, for average players)
DEFAULT_RUNS_PER_HOUR = {
    "F1": 12, "F2": 10, "F3": 8, "F4": 7, "F5": 6, "F6": 5, "F7": 4,
    "M1": 8, "M2": 7, "M3": 6, "M4": 5, "M5": 4, "M6": 3, "M7": 2,
}

# All valid floors
ALL_FLOORS = ["F1", "F2", "F3", "F4", "F5", "F6", "F7",
              "M1", "M2", "M3", "M4", "M5", "M6", "M7"]

# Chest ordering for display
CHEST_ORDER = ["Wood", "Gold", "Diamond", "Emerald", "Obsidian", "Bedrock"]

# ─── Item Name → Item ID Mapping ────────────────────────────────────
# Based on FluxCapacitor2's dungeon-loot-calculator constants/items.ts
# Maps wiki display names to priceable item IDs (Bazaar/AH).

ITEM_NAME_TO_ID = {
    # Common drops
    "Recombobulator 3000": "RECOMBOBULATOR_3000",
    "Bonzo's Staff": "BONZO_STAFF",
    "Fuming Potato Book": "FUMING_POTATO_BOOK",
    "Bonzo's Mask": "BONZO_MASK",
    "Red Nose": "RED_NOSE",
    "Hot Potato Book": "HOT_POTATO_BOOK",
    "Necromancer's Brooch": "NECROMANCER_BROOCH",
    "Kismet Feather": "KISMET_FEATHER",
    # Enchanted books (ultimate enchants)
    "No Pain No Gain I": "ENCHANTED_BOOK-ULTIMATE_NO_PAIN_NO_GAIN-1",
    "No Pain No Gain II": "ENCHANTED_BOOK-ULTIMATE_NO_PAIN_NO_GAIN-2",
    "No Pain No Gain III": "ENCHANTED_BOOK-ULTIMATE_NO_PAIN_NO_GAIN-3",
    "Ultimate Jerry I": "ENCHANTED_BOOK-ULTIMATE_JERRY-1",
    "Ultimate Jerry II": "ENCHANTED_BOOK-ULTIMATE_JERRY-2",
    "Ultimate Jerry III": "ENCHANTED_BOOK-ULTIMATE_JERRY-3",
    "Bank I": "ENCHANTED_BOOK-ULTIMATE_BANK-1",
    "Bank II": "ENCHANTED_BOOK-ULTIMATE_BANK-2",
    "Bank III": "ENCHANTED_BOOK-ULTIMATE_BANK-3",
    "One For All I": "ENCHANTED_BOOK-ULTIMATE_ONE_FOR_ALL-1",
    "Soul Eater I": "ENCHANTED_BOOK-ULTIMATE_SOUL_EATER-1",
    "Combo I": "ENCHANTED_BOOK-ULTIMATE_COMBO-1",
    "Combo II": "ENCHANTED_BOOK-ULTIMATE_COMBO-2",
    "Combo III": "ENCHANTED_BOOK-ULTIMATE_COMBO-3",
    "Infinite Quiver VI": "ENCHANTED_BOOK-INFINITE_QUIVER-6",
    "Infinite Quiver VII": "ENCHANTED_BOOK-INFINITE_QUIVER-7",
    "Infinite Quiver VIII": "ENCHANTED_BOOK-INFINITE_QUIVER-8",
    "Feather Falling VI": "ENCHANTED_BOOK-FEATHER_FALLING-6",
    "Feather Falling VII": "ENCHANTED_BOOK-FEATHER_FALLING-7",
    "Feather Falling VIII": "ENCHANTED_BOOK-FEATHER_FALLING-8",
    "Rejuvenate I": "ENCHANTED_BOOK-REJUVENATE-1",
    "Rejuvenate II": "ENCHANTED_BOOK-REJUVENATE-2",
    "Rejuvenate III": "ENCHANTED_BOOK-REJUVENATE-3",
    "Ultimate Wise I": "ENCHANTED_BOOK-ULTIMATE_WISE-1",
    "Ultimate Wise II": "ENCHANTED_BOOK-ULTIMATE_WISE-2",
    "Ultimate Wise III": "ENCHANTED_BOOK-ULTIMATE_WISE-3",
    "Wisdom I": "ENCHANTED_BOOK-ULTIMATE_WISDOM-1",
    "Wisdom II": "ENCHANTED_BOOK-ULTIMATE_WISDOM-2",
    "Wisdom III": "ENCHANTED_BOOK-ULTIMATE_WISDOM-3",
    "Last Stand I": "ENCHANTED_BOOK-ULTIMATE_LAST_STAND-1",
    "Last Stand II": "ENCHANTED_BOOK-ULTIMATE_LAST_STAND-2",
    "Last Stand III": "ENCHANTED_BOOK-ULTIMATE_LAST_STAND-3",
    "Rend I": "ENCHANTED_BOOK-ULTIMATE_REND-1",
    "Rend II": "ENCHANTED_BOOK-ULTIMATE_REND-2",
    "Rend III": "ENCHANTED_BOOK-ULTIMATE_REND-3",
    "Overload I": "ENCHANTED_BOOK-OVERLOAD-1",
    "Legion I": "ENCHANTED_BOOK-ULTIMATE_LEGION-1",
    "Swarm I": "ENCHANTED_BOOK-ULTIMATE_SWARM-1",
    "Lethality VI": "ENCHANTED_BOOK-LETHALITY-6",
    "Lethality I": "ENCHANTED_BOOK-LETHALITY-6",  # wiki typo (says I, means VI)
    "Thunderlord VII": "ENCHANTED_BOOK-THUNDERLORD-7",
    # F5 drops
    "Spirit Bone": "SPIRIT_BONE",
    "Spirit Wing": "SPIRIT_WING",
    "Suspicious Vial": "SUSPICIOUS_VIAL",
    "Dark Claymore": "DARK_CLAYMORE",
    "Legendary Spirit Pet": "SPIRIT;4",
    "Epic Spirit Pet": "SPIRIT;3",
    "Spirit Bow": "ITEM_SPIRIT_BOW",
    "Spirit Sword": "SPIRIT_SWORD",
    "Spirit Boots": "THORNS_BOOTS",
    "Spirit Stone": "SPIRIT_DECOY",
    "Warped Stone": "AOTE_STONE",
    # F5 armor
    "Shadow Assassin Chestplate": "SHADOW_ASSASSIN_CHESTPLATE",
    "Shadow Assassin Leggings": "SHADOW_ASSASSIN_LEGGINGS",
    "Shadow Assassin Helmet": "SHADOW_ASSASSIN_HELMET",
    "Shadow Assassin Boots": "SHADOW_ASSASSIN_BOOTS",
    "Last Breath": "LAST_BREATH",
    "Shadow Fury": "SHADOW_FURY",
    "Livid Dagger": "LIVID_DAGGER",
    # F5 adaptive
    "Adaptive Blade": "STONE_BLADE",
    "Adaptive Boots": "ADAPTIVE_BOOTS",
    "Adaptive Leggings": "ADAPTIVE_LEGGINGS",
    "Adaptive Chestplate": "ADAPTIVE_CHESTPLATE",
    "Adaptive Helmet": "ADAPTIVE_HELMET",
    # F6 drops
    "Giant's Sword": "GIANTS_SWORD",
    "Giant Tooth": "GIANT_TOOTH",
    "Dark Orb": "DARK_ORB",
    "Precursor Eye": "PRECURSOR_EYE",
    "Necromancer Lord Chestplate": "NECROMANCER_LORD_CHESTPLATE",
    "Necromancer Lord Leggings": "NECROMANCER_LORD_LEGGINGS",
    "Necromancer Lord Helmet": "NECROMANCER_LORD_HELMET",
    "Necromancer Lord Boots": "NECROMANCER_LORD_BOOTS",
    "Necromancer Sword": "NECROMANCER_SWORD",
    "Summoning Ring": "SUMMONING_RING",
    "Sadan's Brooch": "SADAN_BROOCH",
    "Ancient Rose": "GOLEM_POPPY",
    "Red Scarf": "RED_SCARF",
    "Scarf's Studies": "SCARF_STUDIES",
    # F7 drops
    "Wither Boots": "WITHER_BOOTS",
    "Wither Helmet": "WITHER_HELMET",
    "Wither Chestplate": "WITHER_CHESTPLATE",
    "Wither Leggings": "WITHER_LEGGINGS",
    "Wither Catalyst": "WITHER_CATALYST",
    "Precursor Gear": "PRECURSOR_GEAR",
    "Wither Cloak Sword": "WITHER_CLOAK",
    "Wither Blood": "WITHER_BLOOD",
    "Implosion": "IMPLOSION_SCROLL",
    "Shadow Warp": "SHADOW_WARP_SCROLL",
    "Wither Shield": "WITHER_SHIELD_SCROLL",
    "Auto Recombobulator": "AUTO_RECOMBOBULATOR",
    "Necron's Handle": "NECRON_HANDLE",
    "Necron Dye": "DYE_NECRON",
    # Fish pets (F7)
    "Maxor the Fish": "MAXOR_THE_FISH",
    "Goldor the Fish": "GOLDOR_THE_FISH",
    "Storm the Fish": "STORM_THE_FISH",
    # Master Mode drops
    "Master Skull - Tier 1": "MASTER_SKULL_TIER_1",
    "Master Skull - Tier 2": "MASTER_SKULL_TIER_2",
    "Master Skull - Tier 3": "MASTER_SKULL_TIER_3",
    "Master Skull - Tier 4": "MASTER_SKULL_TIER_4",
    "Master Skull - Tier 5": "MASTER_SKULL_TIER_5",
    "First Master Star": "FIRST_MASTER_STAR",
    "Second Master Star": "SECOND_MASTER_STAR",
    "Third Master Star": "THIRD_MASTER_STAR",
    "Fourth Master Star": "FOURTH_MASTER_STAR",
    "Fifth Master Star": "FIFTH_MASTER_STAR",
    # F3 drops
    "Adaptive Blade": "STONE_BLADE",
    # F4 drops
    "Spirit Pet": "SPIRIT;4",
}

# Items that are cosmetic/untradeable and shouldn't be priced
UNPRICEABLE_ITEMS = {
    "Dungeon Disc", "Clown Disc", "Necron Disc", "Watcher Disc",
}

# Essence item IDs on Bazaar
ESSENCE_IDS = {
    "Wither Essence": "ESSENCE_WITHER",
    "Undead Essence": "ESSENCE_UNDEAD",
    "Dragon Essence": "ESSENCE_DRAGON",
    "Spider Essence": "ESSENCE_SPIDER",
    "Ice Essence": "ESSENCE_ICE",
    "Gold Essence": "ESSENCE_GOLD",
    "Diamond Essence": "ESSENCE_DIAMOND",
    "Crimson Essence": "ESSENCE_CRIMSON",
}

# Essence type per floor (what boss drops)
FLOOR_ESSENCE_TYPE = {
    "F1": "Undead", "F2": "Undead", "F3": "Undead", "F4": "Undead",
    "F5": "Undead", "F6": "Undead", "F7": "Wither",
    "M1": "Undead", "M2": "Undead", "M3": "Undead", "M4": "Undead",
    "M5": "Undead", "M6": "Undead", "M7": "Wither",
}

# Approximate guaranteed essence per run (from community data, varies with score)
# These are rough averages for S+ runs; actual amounts vary
FLOOR_ESSENCE_AMOUNT = {
    "F1": 4, "F2": 6, "F3": 8, "F4": 10,
    "F5": 12, "F6": 16, "F7": 24,
    "M1": 8, "M2": 12, "M3": 16, "M4": 20,
    "M5": 24, "M6": 32, "M7": 48,
}


# ─── Wikitext Parser ────────────────────────────────────────────────

def _clean_wiki_text(text):
    """Strip wikitext markup to get plain text."""
    # Remove [[links]] → display text
    text = re.sub(r'\[\[([^\]|]+\|)?([^\]]+)\]\]', r'\2', text)
    # Remove {{templates}} but extract certain ones
    text = re.sub(r'\{\{bc\}\}', '0', text)
    text = re.sub(r'\{\{Bc\}\}', '0', text)
    text = re.sub(r'\{\{C\|(\d+)\}\}', r'\1', text)
    text = re.sub(r'\{\{Ench\|([^}]+)\}\}', r'\1', text)
    text = re.sub(r'\{\{Dungeon Ranking\|([^}]+)\}\}', r'\1', text)
    # Remove remaining templates
    text = re.sub(r'\{\{[^}]*\}\}', '', text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Clean whitespace
    return text.strip()


def _parse_cost(cost_text):
    """Parse a cost string from the wiki into an integer."""
    cost_text = cost_text.strip()
    if not cost_text or cost_text == '0':
        return 0
    # Remove commas and extract digits
    digits = re.sub(r'[^\d]', '', cost_text)
    return int(digits) if digits else 0


def _parse_chance(chance_text):
    """Parse a chance string (e.g., '5.48%') into a float percent."""
    chance_text = chance_text.strip()
    m = re.search(r'([\d.]+)%', chance_text)
    if m:
        return float(m.group(1))
    return 0.0


def _extract_enchant_name(item_text):
    """Extract the enchantment name from 'Enchanted Book (Enchant Name Level)'."""
    m = re.match(r'Enchanted Book\s*\((.+)\)', item_text)
    if m:
        return m.group(1).strip()
    return item_text


def parse_wikitext_loot(wikitext):
    """Parse the Dungeon Reward Chest/Loot wikitext into structured data.

    Returns dict: {floor_key: {chest_name: [{item, chance_default, chance_splus, cost}, ...]}}
    """
    floors = {}

    # Split by tabber sections (|-|Floor I = ... |-|Floor II = ...)
    floor_sections = re.split(r'\|-\|Floor\s+([IVXL]+)\s*=', wikitext)

    for i in range(1, len(floor_sections), 2):
        floor_roman = floor_sections[i].strip()
        floor_num = _roman_to_int(floor_roman)
        content = floor_sections[i + 1] if i + 1 < len(floor_sections) else ""

        # Split into Normal and Master Mode sections
        mode_parts = re.split(r'==\s*Master Mode\s*==', content)
        normal_content = mode_parts[0]
        master_content = mode_parts[1] if len(mode_parts) > 1 else ""

        normal_key = f"F{floor_num}"
        master_key = f"M{floor_num}"

        if normal_content.strip():
            floors[normal_key] = _parse_loot_table(normal_content)
        if master_content.strip():
            floors[master_key] = _parse_loot_table(master_content)

    return floors


def _roman_to_int(roman):
    """Convert Roman numeral to integer."""
    values = {"I": 1, "V": 5, "X": 10, "L": 50}
    result = 0
    prev = 0
    for c in reversed(roman.strip()):
        val = values.get(c, 0)
        if val < prev:
            result -= val
        else:
            result += val
        prev = val
    return result


def _parse_loot_table(content):
    """Parse a single wikitable into chest → drops mapping.

    The fandom wiki uses this row format within a wikitable:
    - Chest names appear in bold with rowspan: | rowspan="N" | '''Gold'''
    - Item rows: | [[Item Name]] | chance% | chance% | {{C|cost}}
    - Enchant books: | [[Enchanted Book]] ({{Ench|Name Level}}) | ...
    - colspan="2" means same chance for Default and S+

    Returns: {chest_name: [{item, chance_default, chance_splus, cost, replaces_essence}, ...]}
    """
    chests = {}
    current_chest = None

    # Find the wikitable content
    table_match = re.search(r'\{\|\s*class="wikitable[^"]*"(.*?)\|\}', content, re.DOTALL)
    if not table_match:
        return chests

    table_content = table_match.group(1)

    # Split into rows at |-
    rows = re.split(r'\n\|-', table_content)

    for row in rows:
        row = row.strip()
        if not row:
            continue

        # Skip header rows (contain ! headers)
        if re.search(r'^!|^\n!', row):
            continue

        # Check for new chest name (bold text like '''Wood''' or '''Bedrock''')
        chest_match = re.search(r"'''\s*(\w+)\s*'''", row)
        if chest_match:
            name = chest_match.group(1)
            if name in ("Wood", "Gold", "Diamond", "Emerald", "Obsidian", "Bedrock"):
                current_chest = name
                if current_chest not in chests:
                    chests[current_chest] = []

        if not current_chest:
            continue

        # Extract item data from the row
        item_data = _extract_item_from_row(row)
        if item_data:
            chests[current_chest].append(item_data)

    return chests


def _extract_item_from_row(row):
    """Extract item data from a wiki table row.

    Handles these patterns:
    - | [[Item]] | colspan="2" | 5.08% | {{C|25000}}
    - | [[Item]] | 14.75% | 12.32% | {{C|50000}}
    - | [[Enchanted Book]] ({{Ench|Rejuvenate I}}) | 43.36% | 48.07% | {{C|50000}}
    - | [[Item]] | colspan="2" | 2%<br>(Replaces [[Essence]]) | {{bc}}

    The first item in a chest section may share its row with the chest name
    (e.g., '''Bedrock''' followed by [[Auto Recombobulator]]). We need to
    handle this by looking for the LAST [[link]] that isn't Essence.
    """
    # Check for "Replaces Essence" (music discs, etc.)
    replaces_essence = "Replaces" in row and "Essence" in row

    # Extract ALL [[links]] and enchanted book patterns from the row
    item_name = None

    # Check for enchanted book first
    ench_match = re.search(r'\[\[Enchanted Book\]\]\s*\(\s*\{\{Ench\|([^}]+)\}\}\s*\)', row)
    if ench_match:
        item_name = ench_match.group(1).strip()
    else:
        # Find all [[links]] — take the last one that isn't Essence or a chest name
        # This handles the case where chest label and first item share a row
        links = re.findall(r'\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]', row)
        skip = {"Essence", "Wood", "Gold", "Diamond", "Emerald", "Obsidian", "Bedrock",
                "Dungeon Score", "Class Milestones"}
        for link in reversed(links):
            link = link.strip()
            if link not in skip:
                item_name = link
                break

    if not item_name:
        return None

    # Extract percentages (all X.XX% patterns)
    percentages = re.findall(r'(\d+\.?\d*)%', row)

    # Check for colspan="2" — means one chance applies to both Default and S+
    has_colspan = 'colspan="2"' in row or "colspan='2'" in row

    # Extract cost: {{C|number}} or {{bc}} (free)
    cost_match = re.search(r'\{\{C\|(\d+)\}\}', row)
    if cost_match:
        cost = int(cost_match.group(1))
    else:
        cost = 0  # {{bc}} or no cost

    # Determine chances
    if not percentages:
        return None

    if has_colspan or len(percentages) == 1:
        chance = float(percentages[0])
        chance_default = chance
        chance_splus = chance
    else:
        chance_default = float(percentages[0])
        chance_splus = float(percentages[1]) if len(percentages) >= 2 else chance_default

    return {
        "item": item_name,
        "chance_default": chance_default,
        "chance_splus": chance_splus,
        "cost": cost,
        "replaces_essence": replaces_essence,
    }


# ─── Fandom Wiki HTML Scraper ───────────────────────────────────────

class WikiTableParser(HTMLParser):
    """Parse fandom wiki HTML loot tables."""

    def __init__(self):
        super().__init__()
        self.floors = {}
        self._in_tabber = False
        self._current_floor = None
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._is_header = False
        self._cell_text = ""
        self._row_cells = []
        self._current_chest = None
        self._current_mode = "normal"
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "table" and "wikitable" in attrs_dict.get("class", ""):
            self._in_table = True
        elif tag == "tr" and self._in_table:
            self._in_row = True
            self._row_cells = []
        elif tag in ("td", "th") and self._in_row:
            self._in_cell = True
            self._is_header = tag == "th"
            self._cell_text = ""
        elif tag == "b" and self._in_cell:
            pass  # bold text handled in data

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_cell:
            self._in_cell = False
            self._row_cells.append(self._cell_text.strip())
        elif tag == "tr" and self._in_row:
            self._in_row = False
            self._process_row()
        elif tag == "table":
            self._in_table = False

    def handle_data(self, data):
        if self._in_cell:
            self._cell_text += data

    def _process_row(self):
        pass  # Implemented in scrape function below


def scrape_fandom_wiki():
    """Scrape the fandom wiki live for dungeon loot data.

    Returns structured data in the same format as parse_wikitext_loot().
    """
    try:
        req = Request(FANDOM_LOOT_URL, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
        })
        with urlopen(req, timeout=30) as resp:
            html = resp.read().decode()
    except (HTTPError, URLError, OSError) as e:
        print(f"  [Wiki scrape error: {e}]", file=sys.stderr)
        return None

    # The fandom wiki serves the loot page with wikitext-style tables
    # rendered as HTML. We'll extract the source wikitext from the edit API
    # instead, which is much more reliable to parse.
    return _scrape_fandom_api()


def _scrape_fandom_api():
    """Fetch the wikitext source from the fandom wiki API."""
    api_url = ("https://hypixel-skyblock.fandom.com/api.php?"
               "action=query&titles=Dungeon_Reward_Chest/Loot"
               "&prop=revisions&rvprop=content&rvslots=main&format=json")
    try:
        req = Request(api_url, headers={
            "User-Agent": "SkyblockTools/1.0 (dungeon profit calculator)"
        })
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        pages = data.get("query", {}).get("pages", {})
        for page_id, page_data in pages.items():
            revisions = page_data.get("revisions", [])
            if revisions:
                wikitext = revisions[0].get("slots", {}).get("main", {}).get("*", "")
                if wikitext:
                    return parse_wikitext_loot(wikitext)

        print("  [Wiki API: no content found]", file=sys.stderr)
        return None
    except (HTTPError, URLError, OSError, json.JSONDecodeError) as e:
        print(f"  [Wiki API error: {e}]", file=sys.stderr)
        return None


# ─── Data Loading & Caching ─────────────────────────────────────────

def load_loot_data(force_refresh=False):
    """Load loot data from cache or wiki.

    Priority:
    1. Cached JSON (if fresh and not force_refresh)
    2. Local wiki dump (if available)
    3. Live wiki scrape
    """
    # Check cache
    if not force_refresh and LOOT_CACHE_PATH.exists():
        try:
            cache = json.loads(LOOT_CACHE_PATH.read_text())
            if time.time() - cache.get("timestamp", 0) < LOOT_CACHE_TTL:
                return cache.get("floors", {}), cache.get("source", "cache")
        except (json.JSONDecodeError, OSError):
            pass

    # Try local wiki dump first (fast, no network)
    local_wiki_path = WIKI_DIR / "Dungeon Reward Chest_SLASH_Loot.wiki"
    if local_wiki_path.exists() and not force_refresh:
        try:
            wikitext = local_wiki_path.read_text()
            floors = parse_wikitext_loot(wikitext)
            if floors:
                _save_cache(floors, "local_wiki")
                return floors, "local wiki dump"
        except OSError:
            pass

    # Live scrape
    print("  Fetching loot data from fandom wiki...", file=sys.stderr)
    floors = _scrape_fandom_api()
    if floors:
        _save_cache(floors, "fandom_wiki")
        return floors, "fandom wiki (live)"

    # Last resort: stale cache
    if LOOT_CACHE_PATH.exists():
        try:
            cache = json.loads(LOOT_CACHE_PATH.read_text())
            return cache.get("floors", {}), "cache (stale)"
        except (json.JSONDecodeError, OSError):
            pass

    return {}, "none"


def _save_cache(floors, source):
    """Save loot data to cache file."""
    try:
        LOOT_CACHE_PATH.write_text(json.dumps({
            "timestamp": time.time(),
            "source": source,
            "floors": floors,
        }, indent=2))
    except OSError as e:
        print(f"  [Cache write error: {e}]", file=sys.stderr)


# ─── Item ID Resolution ─────────────────────────────────────────────

_display_name_to_id = None


def _build_display_name_index():
    """Build a reverse index from display names to item IDs."""
    global _display_name_to_id
    if _display_name_to_id is not None:
        return
    _display_name_to_id = {}
    try:
        for item in get_items_data():
            item_id = item.get("id", "")
            name = item.get("name", "")
            if name and item_id:
                # Strip color codes
                clean = re.sub(r'§[0-9a-fk-or]', '', name).strip()
                _display_name_to_id[clean.lower()] = item_id
    except Exception:
        pass


def resolve_item_id(wiki_name):
    """Resolve a wiki item name to a priceable item ID.

    Checks the hardcoded mapping first (handles enchanted books, name
    mismatches), then falls back to items.py display name matching.
    """
    # Check hardcoded mapping first
    if wiki_name in ITEM_NAME_TO_ID:
        return ITEM_NAME_TO_ID[wiki_name]

    # Check with case variations
    for mapped_name, mapped_id in ITEM_NAME_TO_ID.items():
        if mapped_name.lower() == wiki_name.lower():
            return mapped_id

    # Check if it's an unpriceable item
    if wiki_name in UNPRICEABLE_ITEMS:
        return None

    # Fall back to items.py display name index
    _build_display_name_index()
    item_id = _display_name_to_id.get(wiki_name.lower())
    if item_id:
        return item_id

    # Try uppercased with underscores (common pattern)
    guess_id = wiki_name.upper().replace(" ", "_").replace("'", "")
    return guess_id


# ─── EV Calculation ─────────────────────────────────────────────────

def calculate_floor_ev(floor_key, floor_data, prices, use_splus=True):
    """Calculate EV for all chests on a floor.

    Uses per-item cost model: in SkyBlock dungeons, the player sees what's
    in each chest before deciding to pay. Each item has its own cost (base
    chest price + item-specific added cost). The EV calculation only counts
    items where market price exceeds the cost to claim:

        Chest EV = Σ(chance × max(price - item_cost, 0))

    This matches FluxCapacitor2's approach and reflects actual player
    decision-making.

    Returns dict of chest results:
    {
        chest_name: {
            "ev": float,           # total expected profit from chest
            "ev_no_rng": float,    # EV excluding RNG drops (< 1% chance)
            "drops": [{item, item_id, chance, price, cost, item_profit, ev, is_rng}, ...],
            "rng_drops": [{...same fields...}, ...],
        }
    }
    """
    results = {}

    for chest_name in CHEST_ORDER:
        drops = floor_data.get(chest_name, [])
        if not drops:
            continue

        chest_result = {
            "ev": 0.0,
            "ev_no_rng": 0.0,
            "drops": [],
            "rng_drops": [],
        }

        for drop in drops:
            item_name = drop["item"]
            chance = drop["chance_splus"] if use_splus else drop["chance_default"]
            cost = drop.get("cost", 0)
            replaces_essence = drop.get("replaces_essence", False)

            # Skip unpriceable items (cosmetic discs, etc.)
            if item_name in UNPRICEABLE_ITEMS:
                continue

            # Resolve item ID and get price
            item_id = resolve_item_id(item_name)
            price = prices.get(item_id, 0) if item_id else 0

            # Per-item profit (only count if price > cost)
            item_profit = max(price - cost, 0) if price > 0 else 0

            # EV = chance × max(price - cost, 0)
            drop_ev = item_profit * chance / 100.0
            is_rng = chance < RNG_THRESHOLD and chance > 0

            drop_info = {
                "item": item_name,
                "item_id": item_id,
                "chance": chance,
                "price": price,
                "cost": cost,
                "item_profit": item_profit,
                "ev": drop_ev,
                "is_rng": is_rng,
                "replaces_essence": replaces_essence,
            }

            chest_result["drops"].append(drop_info)
            chest_result["ev"] += drop_ev

            if is_rng:
                chest_result["rng_drops"].append(drop_info)
            else:
                chest_result["ev_no_rng"] += drop_ev

        results[chest_name] = chest_result

    return results


def calculate_essence_value(floor_key, prices):
    """Calculate the value of guaranteed essence drops per run."""
    essence_type = FLOOR_ESSENCE_TYPE.get(floor_key, "Undead")
    essence_amount = FLOOR_ESSENCE_AMOUNT.get(floor_key, 0)
    essence_name = f"{essence_type} Essence"
    essence_id = ESSENCE_IDS.get(essence_name)

    if not essence_id or essence_amount == 0:
        return {"type": essence_name, "amount": essence_amount, "price_each": 0, "total": 0}

    price_each = prices.get(essence_id, 0)
    return {
        "type": essence_name,
        "amount": essence_amount,
        "price_each": price_each,
        "total": price_each * essence_amount,
    }


# ─── Price Fetching ──────────────────────────────────────────────────

def fetch_all_prices(floors_data):
    """Fetch prices for all items across all floors.

    Returns dict: {item_id: weighted_price}
    """
    # Collect all unique item IDs
    item_ids = set()
    for floor_key, chests in floors_data.items():
        for chest_name, drops in chests.items():
            for drop in drops:
                item_id = resolve_item_id(drop["item"])
                if item_id:
                    item_ids.add(item_id)

    # Add essence IDs
    for eid in ESSENCE_IDS.values():
        item_ids.add(eid)

    # Add Kismet Feather
    item_ids.add("KISMET_FEATHER")

    # Fetch prices
    cache = PriceCache()
    cache.get_prices_bulk(list(item_ids))  # warm the cache

    prices = {}
    for item_id in item_ids:
        price = cache.weighted(item_id)
        if price:
            prices[item_id] = price

    cache.flush()
    return prices


# ─── Output Formatting ──────────────────────────────────────────────

def format_detailed_floor(floor_key, chest_results, essence, kismet_price,
                          runs_per_hour, talisman, luck, use_splus):
    """Format detailed output for a single floor."""
    lines = []

    # Header
    score = "S+" if use_splus else "Base"
    talisman_str = talisman.title() if talisman != "none" else "None"
    luck_str = str(luck)

    lines.append("═" * 60)
    lines.append(f"  DUNGEON PROFIT — {floor_key}")
    lines.append(f"  Score: {score} | Talisman: {talisman_str} | Boss Luck: {luck_str}")
    if talisman != "none" or luck > 0:
        lines.append("  Note: Wiki only provides Default/S+ rates;")
        lines.append("  Talisman/Boss Luck do not affect displayed rates.")
    lines.append("═" * 60)
    lines.append("")

    # Chest breakdown table
    # With per-item cost model, EV already represents expected profit
    # (only items where price > cost contribute)
    lines.append("  Chest Breakdown:")
    lines.append(f"    {'Chest':<12s} {'EV':>10s}  {'No-RNG EV':>10s}  Verdict")
    lines.append(f"    {'─' * 48}")

    total_ev = 0.0
    total_ev_no_rng = 0.0
    best_chest = None
    best_ev = float("-inf")

    for chest_name in CHEST_ORDER:
        if chest_name not in chest_results:
            continue
        cr = chest_results[chest_name]
        ev_str = _fmt(cr["ev"]) if cr["ev"] > 0 else "—"
        ev_no_rng_str = _fmt(cr["ev_no_rng"]) if cr["ev_no_rng"] > 0 else "—"

        # Every chest with positive EV is worth opening (cost already deducted per item)
        if cr["ev"] > 0:
            verdict = "OPEN"
            total_ev += cr["ev"]
            total_ev_no_rng += cr["ev_no_rng"]
        else:
            verdict = "SKIP"

        if cr["ev"] > best_ev:
            best_ev = cr["ev"]
            best_chest = chest_name

        lines.append(f"    {chest_name:<12s} {ev_str:>10s}  {ev_no_rng_str:>10s}  {verdict}")

    # Mark the best chest
    for i, line in enumerate(lines):
        if best_chest and best_chest in line and "OPEN" in line:
            lines[i] = line + " ★"
            break

    lines.append("")

    # Guaranteed essence
    if essence["amount"] > 0:
        lines.append("  Guaranteed Drops:")
        lines.append(f"    {essence['type']} ×{essence['amount']}"
                      f"{'':>22s}{_fmt(essence['total'])}")
        lines.append("")
        total_ev += essence["total"]
        total_ev_no_rng += essence["total"]

    # Summary
    lines.append(f"  {'─' * 56}")
    lines.append(f"  Optimal Run EV (all chests + essence):    {_fmt(total_ev)}")
    lines.append(f"  Optimal Run EV (excluding RNG drops):     {_fmt(total_ev_no_rng)}")
    lines.append(f"  Runs/hr estimate:                         {runs_per_hour}")
    hourly = total_ev * runs_per_hour
    hourly_no_rng = total_ev_no_rng * runs_per_hour
    lines.append(f"  Hourly rate:           {_fmt(hourly_no_rng)} - {_fmt(hourly)}")
    lines.append("")

    # High-Value RNG Drops
    all_rng = []
    for chest_name in CHEST_ORDER:
        if chest_name not in chest_results:
            continue
        for rng in chest_results[chest_name]["rng_drops"]:
            if rng["ev"] > 0:
                all_rng.append({**rng, "chest": chest_name})

    if all_rng:
        all_rng.sort(key=lambda x: x["ev"], reverse=True)
        lines.append("  High-Value RNG Drops:")
        lines.append(f"    {'Item':<26s} {'Chest':<10s} {'Chance':>7s}"
                      f"  {'Price':>8s}  {'Cost':>8s}  {'EV':>8s}")
        lines.append(f"    {'─' * 73}")
        for rng in all_rng[:10]:
            chance_str = f"{rng['chance']:.2f}%"
            if rng['chance'] < 0.01:
                chance_str = f"{rng['chance']:.3f}%"
            lines.append(f"    {rng['item']:<26s} {rng['chest']:<10s} {chance_str:>7s}"
                          f"  {_fmt(rng['price']):>8s}  {_fmt(rng['cost']):>8s}"
                          f"  {_fmt(rng['ev']):>8s}")
        lines.append("")

    # Kismet Analysis
    # Reroll EV = chest EV (with new roll) - Kismet price
    if kismet_price and kismet_price > 0:
        lines.append(f"  Kismet Analysis (Kismet Feather: {_fmt(kismet_price)}):")
        for chest_name in CHEST_ORDER:
            if chest_name not in chest_results:
                continue
            cr = chest_results[chest_name]
            if cr["ev"] <= 0:
                continue
            reroll_ev = cr["ev"] - kismet_price
            if reroll_ev > 0:
                verdict = "WORTH IT"
            else:
                verdict = "NOT WORTH"
            if reroll_ev >= 0:
                reroll_str = f"+{_fmt(reroll_ev)}"
            else:
                reroll_str = f"-{_fmt(abs(reroll_ev))}"
            lines.append(f"    {chest_name:<12s} EV {_fmt(cr['ev']):>8s}"
                          f"  Reroll EV {reroll_str:>10s}  {verdict}")
        lines.append("")

    return "\n".join(lines)


def format_summary(floors_data, prices, use_splus=True, runs_per_hour_override=None):
    """Format a compact summary of all floors."""
    lines = []
    lines.append("═" * 70)
    lines.append("  DUNGEON PROFIT SUMMARY")
    score_label = "S+" if use_splus else "Base"
    lines.append(f"  Score: {score_label} | Sorted by hourly rate (excluding RNG)")
    lines.append("═" * 70)
    lines.append("")
    lines.append(f"    {'Floor':<6s} {'Best Chest':>12s} {'Run EV':>10s}"
                  f" {'No-RNG EV':>10s} {'Runs/hr':>8s} {'Rate/hr':>10s}")
    lines.append(f"    {'─' * 62}")

    floor_summaries = []

    for floor_key in ALL_FLOORS:
        if floor_key not in floors_data:
            continue

        chest_results = calculate_floor_ev(floor_key, floors_data[floor_key], prices, use_splus)
        essence = calculate_essence_value(floor_key, prices)

        total_ev = essence["total"]
        total_ev_no_rng = essence["total"]
        best_chest_name = None
        best_chest_ev = float("-inf")

        for chest_name in CHEST_ORDER:
            if chest_name not in chest_results:
                continue
            cr = chest_results[chest_name]
            if cr["ev"] > 0:
                total_ev += cr["ev"]
                total_ev_no_rng += cr["ev_no_rng"]
            if cr["ev"] > best_chest_ev:
                best_chest_ev = cr["ev"]
                best_chest_name = chest_name

        rph = runs_per_hour_override or DEFAULT_RUNS_PER_HOUR.get(floor_key, 4)
        hourly_no_rng = total_ev_no_rng * rph

        floor_summaries.append({
            "floor": floor_key,
            "best_chest": best_chest_name or "—",
            "ev": total_ev,
            "ev_no_rng": total_ev_no_rng,
            "rph": rph,
            "hourly": hourly_no_rng,
        })

    # Sort by hourly rate descending
    floor_summaries.sort(key=lambda x: x["hourly"], reverse=True)

    for fs in floor_summaries:
        lines.append(f"    {fs['floor']:<6s} {fs['best_chest']:>12s}"
                      f" {_fmt(fs['ev']):>10s} {_fmt(fs['ev_no_rng']):>10s}"
                      f" {fs['rph']:>8d} {_fmt(fs['hourly']):>10s}")

    lines.append("")
    return "\n".join(lines)


def build_json_output(floor_key, chest_results, essence, kismet_price,
                      runs_per_hour, talisman, luck, use_splus):
    """Build JSON output for a single floor."""
    total_ev = essence["total"]
    total_ev_no_rng = essence["total"]

    chests_json = {}
    for chest_name in CHEST_ORDER:
        if chest_name not in chest_results:
            continue
        cr = chest_results[chest_name]
        if cr["ev"] > 0:
            total_ev += cr["ev"]
            total_ev_no_rng += cr["ev_no_rng"]

        chests_json[chest_name] = {
            "ev": round(cr["ev"], 2),
            "ev_no_rng": round(cr["ev_no_rng"], 2),
            "verdict": "OPEN" if cr["ev"] > 0 else "SKIP",
            "drops": [{
                "item": d["item"],
                "item_id": d["item_id"],
                "chance": d["chance"],
                "price": round(d["price"], 2) if d["price"] else 0,
                "cost": d["cost"],
                "item_profit": round(d["item_profit"], 2),
                "ev": round(d["ev"], 2),
                "is_rng": d["is_rng"],
            } for d in cr["drops"]],
        }

    kismet_analysis = {}
    if kismet_price:
        for chest_name, cr in chest_results.items():
            if cr["ev"] > 0:
                reroll_ev = cr["ev"] - kismet_price
                kismet_analysis[chest_name] = {
                    "chest_ev": round(cr["ev"], 2),
                    "reroll_ev": round(reroll_ev, 2),
                    "worth_it": reroll_ev > 0,
                }

    return {
        "floor": floor_key,
        "score": "S+" if use_splus else "base",
        "talisman": talisman,
        "boss_luck": luck,
        "chests": chests_json,
        "essence": essence,
        "kismet_price": round(kismet_price, 2) if kismet_price else 0,
        "kismet_analysis": kismet_analysis,
        "optimal_ev": round(total_ev, 2),
        "optimal_ev_no_rng": round(total_ev_no_rng, 2),
        "runs_per_hour": runs_per_hour,
        "hourly_rate": round(total_ev * runs_per_hour, 2),
        "hourly_rate_no_rng": round(total_ev_no_rng * runs_per_hour, 2),
    }


# ─── CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Dungeon Profit Calculator — expected value per floor and chest"
    )
    parser.add_argument("--floor", type=str, default=None,
                        help="Floor to analyze (e.g., f7, m5, F7, M5)")
    parser.add_argument("--talisman", type=str, default="none",
                        choices=["none", "talisman", "ring", "artifact"],
                        help="Treasure Talisman tier (rates reserved — wiki only has Default/S+)")
    parser.add_argument("--luck", type=int, default=0,
                        choices=[0, 1, 3, 5, 10],
                        help="Boss Luck level (rates reserved — wiki only has Default/S+)")
    parser.add_argument("--no-splus", action="store_true",
                        help="Use base score rates instead of S+ rates")
    parser.add_argument("--runs-per-hour", type=int, default=None,
                        help="Override runs/hour estimate")
    parser.add_argument("--json", action="store_true",
                        help="Machine-readable JSON output")
    parser.add_argument("--refresh", action="store_true",
                        help="Force re-scrape wiki data (ignore cache)")

    args = parser.parse_args()
    use_splus = not args.no_splus

    # Load loot data
    floors_data, source = load_loot_data(force_refresh=args.refresh)
    if not floors_data:
        print("Error: Could not load dungeon loot data.", file=sys.stderr)
        print("Try: python3 dungeons.py --refresh", file=sys.stderr)
        sys.exit(1)

    if not args.json:
        print(f"  [Data source: {source}]", file=sys.stderr)

    # Fetch prices
    if not args.json:
        print("  Fetching prices...", file=sys.stderr)
    prices = fetch_all_prices(floors_data)

    # Kismet price
    kismet_price = prices.get("KISMET_FEATHER", 0)

    if args.floor:
        # Detailed single floor view
        floor_key = args.floor.upper()
        if not floor_key.startswith(("F", "M")):
            floor_key = "F" + floor_key

        if floor_key not in floors_data:
            available = [f for f in ALL_FLOORS if f in floors_data]
            print(f"Error: Floor {floor_key} not found. Available: {', '.join(available)}",
                  file=sys.stderr)
            sys.exit(1)

        chest_results = calculate_floor_ev(
            floor_key, floors_data[floor_key], prices, use_splus
        )
        essence = calculate_essence_value(floor_key, prices)
        rph = args.runs_per_hour or DEFAULT_RUNS_PER_HOUR.get(floor_key, 4)

        if args.json:
            output = build_json_output(
                floor_key, chest_results, essence, kismet_price,
                rph, args.talisman, args.luck, use_splus
            )
            print(json.dumps(output, indent=2))
        else:
            print(format_detailed_floor(
                floor_key, chest_results, essence, kismet_price,
                rph, args.talisman, args.luck, use_splus
            ))
    else:
        # Summary of all floors
        if args.json:
            all_floors_json = []
            for floor_key in ALL_FLOORS:
                if floor_key not in floors_data:
                    continue
                chest_results = calculate_floor_ev(
                    floor_key, floors_data[floor_key], prices, use_splus
                )
                essence = calculate_essence_value(floor_key, prices)
                rph = args.runs_per_hour or DEFAULT_RUNS_PER_HOUR.get(floor_key, 4)
                all_floors_json.append(build_json_output(
                    floor_key, chest_results, essence, kismet_price,
                    rph, args.talisman, args.luck, use_splus
                ))
            print(json.dumps(all_floors_json, indent=2))
        else:
            print(format_summary(
                floors_data, prices, use_splus, args.runs_per_hour
            ))


if __name__ == "__main__":
    main()
