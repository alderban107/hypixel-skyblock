#!/usr/bin/env python3
"""Networth calculator for Hypixel SkyBlock.

Calculates total profile value by pricing every item across all storage
locations. Uses weighted average Bazaar pricing and LBIN for AH items,
with full modifier pricing (stars, HPB, enchants, reforges, gems, etc.)
and application worth multipliers.

Reports dual networth (total + unsoulbound), category breakdown,
top valuable items with modifier price breakdown, soulbound summary,
and unpriced items.

Usage:
    python3 networth.py                    # full networth breakdown
    python3 networth.py --category pets    # just pets breakdown
    python3 networth.py --top 20          # top 20 most valuable items
    python3 networth.py --no-cosmetic     # exclude cosmetic items
    python3 networth.py --json            # machine-readable output
    python3 networth.py --verbose         # list every item with price
"""

import argparse
import json
import re
import sys
from pathlib import Path

from items import display_name, get_item, get_items_data, get_upgrade_costs, get_category
from pricing import PriceCache, _fmt, RARITY_NUM, RARITY_NAME
from profile import decode_nbt_inventory_slots

DATA_DIR = Path(__file__).parent.parent / "data"
LAST_PROFILE_PATH = DATA_DIR / "last_profile.json"
NEU_ITEMS_DIR = DATA_DIR / "neu-repo" / "items"
ESSENCECOSTS_PATH = DATA_DIR / "neu-repo" / "constants" / "essencecosts.json"
GEMSTONECOSTS_PATH = DATA_DIR / "neu-repo" / "constants" / "gemstonecosts.json"
EXTERNAL_DIR = DATA_DIR / "external"
ENCHANT_RULES_PATH = EXTERNAL_DIR / "enchant_rules.json"
STACKING_ENCHANTS_PATH = EXTERNAL_DIR / "StackingEnchants.json"
PRESTIGE_COSTS_PATH = EXTERNAL_DIR / "prestige_costs.json"
GOOD_ROLLS_PATH = EXTERNAL_DIR / "AttributeGoodRolls.json"

# ─── Application Worth Multipliers ────────────────────────────────────
# How much of a modifier's market price counts toward item value.
# Based on SkyHelper-Networth's handler system.

MULTIPLIERS = {
    "stars": 0.75,           # Essence stars
    "hpb": 1.0,              # Hot Potato Books (first 10)
    "fuming": 0.6,           # Fuming Potato Books (11-15)
    "recombobulator": 0.8,   # Recombobulator 3000
    "enchantments": 0.85,    # Enchantment books
    "reforge": 1.0,          # Reforge stone
    "gemstones": 1.0,        # Applied gemstones
    "gemstone_slots": 0.6,   # Gemstone slot unlocks
    "gemstone_chambers": 0.9, # Gemstone chambers
    "master_stars": 1.0,     # First/Second/Third/Fourth/Fifth Master Star
    "scrolls": 1.0,          # Necron Blade Scrolls
    "art_of_war": 0.6,       # Art of War
    "art_of_peace": 0.8,     # Art of Peace
    "drill_parts": 1.0,      # Drill engine/fuel tank/upgrade module
    "rod_parts": 1.0,        # Rod of the Sea parts
    "dye": 0.9,              # Dyes
    "pet_candy": 0.65,       # Pet Candy Used
    "pet_item": 1.0,         # Held pet item
    "pet_skin": 0.9,         # Pet skins (non-soulbound)
    "wood_singularity": 0.5, # Wood Singularity
    "farming_for_dummies": 0.5,  # Farming for Dummies
    "etherwarp": 1.0,        # Etherwarp Conduit
    "transmission_tuner": 0.7,   # Transmission Tuners
    "mana_disintegrator": 0.8,   # Mana Disintegrator
    "enrichment": 0.5,       # Talisman enrichment
    "silex": 0.75,           # Silex (efficiency upgrade)
    "prestige": 1.0,         # Kuudra prestige materials
    "jalapeno": 0.8,         # Jalapeno Book
    "polarvoid": 1.0,        # Polarvoid Book
    "runes": 0.6,            # Applied runes
    "overclocker": 0.9,      # Overclocker 3000
    "soulbound_skin": 0.8,   # Soulbound pet/item skins
    "booster": 0.8,          # Booster cookie effects
    "shens_auction": 0.85,   # Shen's Auction price
    "gemstone_power_scroll": 0.5,  # Gemstone Power Scroll
    "divan_powder_coating": 0.8,   # Divan's Powder Coating
}

# Per-enchantment multiplier overrides are loaded from enchant_rules.json
# ("enchant_multiplier_overrides" section). Values there override the default
# MULTIPLIERS["enchantments"] rate for specific enchantments. The JSON is the
# single source of truth — edit it there, not here.

# ─── Reforge Modifier → Stone Item ID ────────────────────────────────
# Built from NEU repo lore data: "Applies the X reforge"

REFORGE_STONES = {
    "ambered": "AMBER_MATERIAL", "ancient": "PRECURSOR_GEAR",
    "auspicious": "ROCK_GEMSTONE", "beady": "BEADY_EYES",
    "blazing": "BLAZEN_SPHERE", "blessed": "BLESSED_FRUIT",
    "bloodshot": "SHRIVELED_CORNEA", "blooming": "FLOWERING_BOUQUET",
    "bountiful": "GOLDEN_BALL", "bulky": "BULKY_STONE",
    "bustling": "SKYMART_BROCHURE", "buzzing": "CLIPPED_WINGS",
    "calcified": "CALCIFIED_HEART", "candied": "CANDY_CORN",
    "chomp": "KUUDRA_MANDIBLE",
    "coldfused": "ENTROPY_SUPPRESSOR", "coldfusion": "ENTROPY_SUPPRESSOR",
    "cubic": "MOLTEN_CUBE", "dimensional": "TITANIUM_TESSERACT",
    "dirty": "DIRT_BOTTLE", "earthy": "LARGE_WALNUT",
    "empowered": "SADAN_BROOCH", "erudite": "DAEDALUS_NOTES",
    "fabled": "DRAGON_CLAW", "fanged": "FULL_JAW_FANGING_KIT",
    "festive": "FROZEN_BAUBLE", "fleet": "DIAMONITE",
    "fortified": "METEOR_SHARD", "fruitful": "ONYX",
    "giant": "GIANT_TOOTH", "gilded": "MIDAS_JEWEL",
    "glacial": "FRIGID_HUSK", "glistening": "SHINY_PRISM",
    "groovy": "MANGROVE_GEM", "headstrong": "SALMON_OPAL",
    "heated": "HOT_STUFF", "hyper": "ENDSTONE_GEODE",
    "jaded": "JADERALD", "loving": "RED_SCARF",
    "lucky": "LUCKY_DICE", "lunar": "MOONSTONE",
    "lustrous": "GLEAMING_CRYSTAL", "magnetic": "LAPIS_CRYSTAL",
    "mantid": "MANTID_CLAW", "mithraic": "PURE_MITHRIL",
    "moil": "MOIL_LOG", "moonglade": "MOONGLADE_JEWEL",
    "mossy": "OVERGROWN_GRASS", "necrotic": "NECROMANCER_BROOCH",
    "perfect": "DIAMOND_ATOM", "precise": "OPTICAL_LENS",
    "refined": "REFINED_AMBER", "reinforced": "RARE_DIAMOND",
    "renowned": "DRAGON_HORN", "ridiculous": "RED_NOSE",
    "rooted": "BURROWING_SPORES", "royal": "DWARVEN_TREASURE",
    "salty": "SALT_CUBE", "scraped": "POCKET_ICEBERG",
    "snowy": "TERRY_SNOWGLOBE", "spiked": "DRAGON_SCALE",
    "spiritual": "SPIRIT_DECOY", "squeaky": "SQUEAKY_TOY",
    "stellar": "PETRIFIED_STARFALL", "stiff": "HARDENED_WOOD",
    "strengthened": "SEARING_STONE", "submerged": "DEEP_SEA_ORB",
    "sunny": "SUNSTONE", "suspicious": "SUSPICIOUS_VIAL",
    "toil": "TOIL_LOG", "trashy": "OVERFLOWING_TRASH_CAN",
    "treacherous": "RUSTY_ANCHOR", "undead": "PREMIUM_FLESH",
    "warped": "AOTE_STONE", "aote_stone": "AOTE_STONE",
    "waxed": "BLAZE_WAX", "withered": "WITHER_BLOOD",
    # Additional reforge stones from SkyHelper
    "pitchin": "PITCHIN_KOI", "blood_soaked": "PRESUMED_GALLON_OF_RED_PAINT",
    "jerry_stone": "JERRY_STONE", "greater_spook": "BOO_STONE",
}

# Basic reforges that don't use a stone (free from reforge anvil)
BASIC_REFORGES = {
    "gentle", "odd", "fast", "fair", "epic", "sharp", "heroic", "spicy",
    "legendary", "deadly", "fine", "grand", "hasty", "keen", "rapid",
    "unreal", "awkward", "rich", "clean", "fierce", "heavy", "light",
    "mythic", "pure", "smart", "strong", "superior", "titanic", "wise",
    "bizarre", "itchy", "ominous", "pleasant", "pretty", "shiny",
    "simple", "strange", "vivid", "godly", "demonic", "forceful",
    "hurtful", "silky", "bloody", "unpleasant", "double-bit",
    "lumberjack", "great", "rugged", "exceptional",
}

# Master Star item IDs (in order)
MASTER_STARS = [
    "FIRST_MASTER_STAR", "SECOND_MASTER_STAR", "THIRD_MASTER_STAR",
    "FOURTH_MASTER_STAR", "FIFTH_MASTER_STAR",
]

# Necron Blade scroll item IDs
NECRON_SCROLLS = {
    "IMPLOSION_SCROLL": "IMPLOSION_SCROLL",
    "SHADOW_WARP_SCROLL": "SHADOW_WARP_SCROLL",
    "WITHER_SHIELD_SCROLL": "WITHER_SHIELD_SCROLL",
}

# Gemstone quality → item ID prefix
GEMSTONE_QUALITIES = {
    "ROUGH": "ROUGH",
    "FLAWED": "FLAWED",
    "FINE": "FINE",
    "FLAWLESS": "FLAWLESS",
    "PERFECT": "PERFECT",
}

# Cosmetic item categories (for --no-cosmetic filtering)
COSMETIC_CATEGORIES = {"COSMETIC"}

# Cosmetic item ID patterns
COSMETIC_PATTERNS = {"DYE_", "RUNE_", "PET_SKIN_"}

# Essence type -> Bazaar ID
ESSENCE_BAZAAR = {
    "WITHER": "ESSENCE_WITHER",
    "UNDEAD": "ESSENCE_UNDEAD",
    "DRAGON": "ESSENCE_DRAGON",
    "GOLD": "ESSENCE_GOLD",
    "DIAMOND": "ESSENCE_DIAMOND",
    "ICE": "ESSENCE_ICE",
    "SPIDER": "ESSENCE_SPIDER",
    "CRIMSON": "ESSENCE_CRIMSON",
}

# Pet rarity number -> name mapping
PET_RARITY = {0: "COMMON", 1: "UNCOMMON", 2: "RARE", 3: "EPIC", 4: "LEGENDARY", 5: "MYTHIC"}

# ─── Data Loading ─────────────────────────────────────────────────────


def load_profile():
    """Load last_profile.json. Returns (member, profile, uuid) or exits."""
    if not LAST_PROFILE_PATH.exists():
        print("Error: data/last_profile.json not found.", file=sys.stderr)
        print("Run 'python3 profile.py' first to fetch profile data.", file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(LAST_PROFILE_PATH.read_text())
        uuid = data.get("uuid", "")
        profile = data.get("profile", {})
        members = profile.get("members", {})
        member = None
        for key, val in members.items():
            if key.replace("-", "") == uuid:
                member = val
                break
        if not member:
            print("Error: Could not find member data in last_profile.json.", file=sys.stderr)
            sys.exit(1)
        return member, profile, data
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error reading last_profile.json: {e}", file=sys.stderr)
        sys.exit(1)


def load_essence_costs():
    """Load essence upgrade costs from NEU repo constants."""
    if not ESSENCECOSTS_PATH.exists():
        return {}
    try:
        return json.loads(ESSENCECOSTS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _load_json(path):
    """Load a JSON file, returning {} on failure."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


# Lazy-loaded external data (module-level singletons)
_enchant_rules = None
_stacking_thresholds = None
_prestige_costs = None
_gemstone_costs = None
_good_rolls = None


def get_enchant_rules():
    global _enchant_rules
    if _enchant_rules is None:
        _enchant_rules = _load_json(ENCHANT_RULES_PATH)
    return _enchant_rules


def get_stacking_thresholds():
    global _stacking_thresholds
    if _stacking_thresholds is None:
        _stacking_thresholds = _load_json(STACKING_ENCHANTS_PATH)
    return _stacking_thresholds


def get_prestige_costs():
    global _prestige_costs
    if _prestige_costs is None:
        _prestige_costs = _load_json(PRESTIGE_COSTS_PATH)
    return _prestige_costs


def get_gemstone_costs():
    global _gemstone_costs
    if _gemstone_costs is None:
        _gemstone_costs = _load_json(GEMSTONECOSTS_PATH)
    return _gemstone_costs


def get_good_rolls():
    global _good_rolls
    if _good_rolls is None:
        _good_rolls = _load_json(GOOD_ROLLS_PATH)
    return _good_rolls


# ─── Pet Level Calculation ────────────────────────────────────────────

# XP required for each level (from SkyHelper-Networth constants/pets.js)
# Index 0 = XP to go from level 1→2, index 1 = level 2→3, etc.
_PET_LEVELS_XP = [
    100, 110, 120, 130, 145, 160, 175, 190, 210, 230, 250, 275, 300, 330, 360,
    400, 440, 490, 540, 600, 660, 730, 800, 880, 960, 1050, 1150, 1260, 1380,
    1510, 1650, 1800, 1960, 2130, 2310, 2500, 2700, 2920, 3160, 3420, 3700,
    4000, 4350, 4750, 5200, 5700, 6300, 7000, 7800, 8700, 9700, 10800, 12000,
    13300, 14700, 16200, 17800, 19500, 21300, 23200, 25200, 27400, 29800, 32400,
    35200, 38200, 41400, 44800, 48400, 52200, 56200, 60400, 64800, 69400, 74200,
    79200, 84700, 90700, 97200, 104200, 111700, 119700, 128200, 137200, 146700,
    156700, 167700, 179700, 192700, 206700, 221700, 237700, 254700, 272700,
    291700, 311700, 333700, 357700, 383700, 411700, 441700,
    # Levels 101-200 (for Golden Dragon, Jade Dragon, Rose Dragon)
    476700, 516700, 561700, 611700, 666700, 726700, 791700, 861700, 936700,
    1016700, 1101700, 1191700, 1286700, 1386700, 1496700, 1616700, 1746700,
    1886700, 0, 5555,  # level 119-120 gap
    1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700,
    1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700,
    1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700,
    1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700,
    1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700,
    1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700,
    1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700,
    1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700,
    1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700,
    1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700, 1886700,
]

# Rarity → starting level offset (how many early levels to skip)
_PET_RARITY_OFFSET = {0: 0, 1: 6, 2: 11, 3: 16, 4: 20, 5: 20}

# Pets that can go to level 200
_PET_MAX_200 = {"GOLDEN_DRAGON", "JADE_DRAGON", "ROSE_DRAGON"}


def _estimate_pet_level(xp, rarity_num, pet_type=""):
    """Calculate pet level from XP using the actual XP table.

    Returns level 1-100 (or 1-200 for special pets like Golden Dragon).
    """
    offset = _PET_RARITY_OFFSET.get(rarity_num, 0)
    max_level = 200 if pet_type in _PET_MAX_200 else 100

    level = 1
    remaining_xp = xp
    for i in range(offset, min(offset + max_level - 1, len(_PET_LEVELS_XP))):
        xp_needed = _PET_LEVELS_XP[i]
        if xp_needed <= 0:
            continue
        if remaining_xp >= xp_needed:
            remaining_xp -= xp_needed
            level += 1
        else:
            break

    return min(level, max_level)


# ─── Soulbound Detection ─────────────────────────────────────────────


def is_soulbound(item):
    """Check if an item is soulbound from lore lines or donated_museum flag."""
    if item.get("donated_museum"):
        return True
    lore = item.get("lore", [])
    for line in lore:
        clean = re.sub(r"§.", "", line).strip()
        if "✦ Soulbound" in clean or "* Soulbound *" in clean or "Co-op Soulbound" in clean:
            return True
    return False


def is_cosmetic(item):
    """Check if an item is cosmetic (dye, skin, standalone rune, cosmetic category).

    Items with runes/dyes/skins APPLIED are not cosmetic — only standalone
    cosmetic items are. Matches SkyHelper-Networth's isCosmetic() logic.
    """
    item_id = item.get("id", "")
    cat = get_category(item_id)
    if cat in COSMETIC_CATEGORIES:
        return True
    for pattern in COSMETIC_PATTERNS:
        if pattern in item_id:
            return True
    # Standalone rune items (not items with runes applied)
    if item_id in ("RUNE", "UNIQUE_RUNE"):
        return True
    # Check lore for COSMETIC tag (some items aren't in the category map)
    lore = item.get("lore", [])
    for line in lore:
        clean = re.sub(r"§.", "", line).strip()
        if "COSMETIC" in clean and ("§" in line or clean.endswith("COSMETIC")):
            return True
    return False


# ─── Modifier Pricing ────────────────────────────────────────────────


def price_stars(item, price_cache, essence_costs):
    """Price essence star upgrades. Returns (value, breakdown_str)."""
    stars = item.get("stars") or item.get("dungeon_item_level") or 0
    if stars <= 0:
        return 0, ""

    item_id = item.get("id", "")

    # Try NEU essencecosts.json first (more complete)
    ess_data = essence_costs.get(item_id, {})
    if ess_data:
        ess_type = ess_data.get("type", "").upper()
        bz_id = ESSENCE_BAZAAR.get(ess_type)
        if not bz_id:
            return 0, ""
        ess_price = price_cache.weighted(bz_id) or 0
        total_essence = 0
        for star_level in range(1, stars + 1):
            total_essence += ess_data.get(str(star_level), 0)
        value = total_essence * ess_price * MULTIPLIERS["stars"]
        return value, f"Stars({stars}★): {_fmt(value)}"

    # Fallback: Hypixel items API upgrade_costs
    upgrade_costs = get_upgrade_costs(item_id)
    if not upgrade_costs:
        return 0, ""

    total_value = 0
    for star_level in range(min(stars, len(upgrade_costs))):
        costs = upgrade_costs[star_level]
        for cost in costs:
            if cost.get("type") == "ESSENCE":
                ess_type = cost.get("essence_type", "")
                amount = cost.get("amount", 0)
                bz_id = ESSENCE_BAZAAR.get(ess_type)
                if bz_id:
                    ess_price = price_cache.weighted(bz_id) or 0
                    total_value += amount * ess_price
            elif cost.get("type") == "ITEM":
                cost_id = cost.get("item_id", "")
                amount = cost.get("amount", 1)
                p = price_cache.weighted(cost_id)
                if p:
                    total_value += p * amount

    value = total_value * MULTIPLIERS["stars"]
    return value, f"Stars({stars}★): {_fmt(value)}"


def price_master_stars(item, price_cache):
    """Price master stars (stars 6-10). Returns (value, breakdown_str)."""
    stars = item.get("stars") or item.get("dungeon_item_level") or 0
    if stars <= 5:
        return 0, ""

    total = 0
    for i in range(min(stars - 5, 5)):
        p = price_cache.weighted(MASTER_STARS[i])
        if p:
            total += p * MULTIPLIERS["master_stars"]

    if total > 0:
        count = min(stars - 5, 5)
        return total, f"Master Stars(×{count}): {_fmt(total)}"
    return 0, ""


def price_hpb(item, price_cache):
    """Price Hot Potato Books and Fuming Potato Books."""
    count = item.get("hpb", 0)
    if count <= 0:
        return 0, ""

    hpb_count = min(count, 10)
    fuming_count = max(count - 10, 0)

    hpb_price = price_cache.weighted("HOT_POTATO_BOOK") or 0
    fuming_price = price_cache.weighted("FUMING_POTATO_BOOK") or 0

    value = (hpb_count * hpb_price * MULTIPLIERS["hpb"] +
             fuming_count * fuming_price * MULTIPLIERS["fuming"])

    parts = []
    if hpb_count:
        parts.append(f"HPB(×{hpb_count})")
    if fuming_count:
        parts.append(f"Fuming(×{fuming_count})")
    return value, f"{'+'.join(parts)}: {_fmt(value)}" if value else (0, "")


def price_recombobulator(item, price_cache):
    """Price Recombobulator 3000 (rarity upgrade)."""
    if not item.get("rarity_upgrades"):
        return 0, ""
    p = price_cache.weighted("RECOMBOBULATOR_3000")
    if not p:
        return 0, ""
    value = p * MULTIPLIERS["recombobulator"]
    return value, f"Recomb: {_fmt(value)}"


def price_enchantments(item, price_cache):
    """Price enchantments with edge case handling.

    Handles: always-active (skip), endcap (price via special item),
    only_tier_one/five (use specific tier), stacking (value by counter level),
    ignored (skip at threshold), per-enchant multiplier overrides.
    """
    enchants = item.get("enchants", {})
    if not enchants:
        return 0, ""

    rules = get_enchant_rules()
    always_active = rules.get("always_active", {})
    only_t1 = rules.get("only_tier_one_prices", [])
    only_t5 = rules.get("only_tier_five_prices", [])
    endcaps = rules.get("endcap_enchants", {})
    ignored = rules.get("ignored_enchants", {})
    multiplier_overrides = rules.get("enchant_multiplier_overrides", {})
    stacking_list = rules.get("stacking_enchants", [])

    item_id = item.get("id", "")

    total = 0
    counted = 0
    for ench_name, level in enchants.items():
        ench_lower = ench_name.lower()
        ench_upper = ench_name.upper()

        # 1. Always-active: skip if this enchant comes free on this item
        active_rule = always_active.get(ench_lower)
        if active_rule:
            if level <= active_rule.get("level", 0) and item_id in active_rule.get("items", []):
                continue

        # 2. Stacking enchants: don't price by book value (value comes from usage)
        if ench_lower in stacking_list:
            continue

        # 3. Ignored enchants: skip at or above threshold
        ignore_threshold = ignored.get(ench_upper)
        if ignore_threshold is not None and level >= ignore_threshold:
            continue

        # 4. Endcap enchants: at max level, price via special item
        endcap = endcaps.get(ench_lower)
        if endcap and level >= endcap.get("required_level", 999):
            endcap_item = endcap.get("endcap_item")
            if endcap_item:
                p = price_cache.weighted(endcap_item)
                if p:
                    mult = multiplier_overrides.get(ench_lower, MULTIPLIERS["enchantments"])
                    total += p * mult
                    counted += 1
                continue

        # 5. Only-tier-one: price at tier 1 regardless of actual level
        if ench_lower in only_t1:
            book_id = f"ENCHANTMENT_{ench_upper}_1"
            p = price_cache.weighted(book_id)
            if p:
                mult = multiplier_overrides.get(ench_lower, MULTIPLIERS["enchantments"])
                total += p * mult
                counted += 1
            continue

        # 6. Only-tier-five: price at tier 5
        if ench_lower in only_t5:
            book_id = f"ENCHANTMENT_{ench_upper}_5"
            p = price_cache.weighted(book_id)
            if p:
                mult = multiplier_overrides.get(ench_lower, MULTIPLIERS["enchantments"])
                total += p * mult
                counted += 1
            continue

        # 7. Standard: price the book at its actual level
        book_id = f"ENCHANTMENT_{ench_upper}_{level}"
        p = price_cache.weighted(book_id)
        if p:
            mult = multiplier_overrides.get(ench_lower, MULTIPLIERS["enchantments"])
            total += p * mult
            counted += 1

    if total > 0:
        return total, f"Enchants({counted}): {_fmt(total)}"
    return 0, ""


def price_reforge(item, price_cache):
    """Price the reforge stone used."""
    reforge = item.get("reforge", "")
    if not reforge:
        return 0, ""

    reforge_lower = reforge.lower()
    if reforge_lower in BASIC_REFORGES:
        return 0, ""  # Basic reforges are free

    stone_id = REFORGE_STONES.get(reforge_lower)
    if not stone_id:
        return 0, ""

    p = price_cache.weighted(stone_id)
    if not p:
        return 0, ""

    value = p * MULTIPLIERS["reforge"]
    return value, f"Reforge({reforge.title()}): {_fmt(value)}"


def price_gemstones(item, price_cache):
    """Price applied gemstones from gems NBT data."""
    gems = item.get("gems", {})
    if not gems:
        return 0, ""

    total = 0
    count = 0
    # gems dict structure: slot_name -> quality OR slot_name_gem -> gem_type
    # e.g. {"COMBAT_0": "PERFECT", "COMBAT_0_gem": "JASPER"}
    processed = set()
    for key, val in gems.items():
        if key.endswith("_gem") or key in processed:
            continue
        slot = key
        gem_key = f"{slot}_gem"
        quality = val if isinstance(val, str) else None
        gem_type = gems.get(gem_key)

        if not quality or not gem_type:
            # Sometimes quality is stored differently
            if isinstance(val, dict):
                quality = val.get("quality")
                gem_type = val.get("type") or gems.get(gem_key)
            if not quality:
                continue

        processed.add(slot)
        processed.add(gem_key)

        # Gem item ID: e.g. PERFECT_JASPER_GEM
        gem_item_id = f"{quality}_{gem_type}_GEM"
        p = price_cache.weighted(gem_item_id)
        if p:
            total += p * MULTIPLIERS["gemstones"]
            count += 1

    if total > 0:
        return total, f"Gems(×{count}): {_fmt(total)}"
    return 0, ""


def price_scrolls(item, price_cache):
    """Price Necron Blade scrolls (ability_scroll NBT)."""
    scrolls = item.get("ability_scroll", [])
    if not scrolls:
        return 0, ""

    total = 0
    count = 0
    for scroll_id in scrolls:
        # Scroll IDs in NBT: IMPLOSION_SCROLL, SHADOW_WARP_SCROLL, WITHER_SHIELD_SCROLL
        p = price_cache.weighted(scroll_id)
        if p:
            total += p * MULTIPLIERS["scrolls"]
            count += 1

    if total > 0:
        return total, f"Scrolls(×{count}): {_fmt(total)}"
    return 0, ""


def price_art_of_war(item, price_cache):
    """Price Art of War."""
    count = item.get("art_of_war_count", 0)
    if not count:
        return 0, ""
    p = price_cache.weighted("ART_OF_WAR")
    if not p:
        return 0, ""
    value = p * MULTIPLIERS["art_of_war"]
    return value, f"Art of War: {_fmt(value)}"


def price_art_of_peace(item, price_cache):
    """Price Art of Peace."""
    if not item.get("art_of_peace"):
        return 0, ""
    p = price_cache.weighted("ART_OF_PEACE")
    if not p:
        return 0, ""
    value = p * MULTIPLIERS["art_of_peace"]
    return value, f"Art of Peace: {_fmt(value)}"


def price_drill_parts(item, price_cache):
    """Price drill engine, fuel tank, and upgrade module."""
    total = 0
    parts = []
    for field in ["drill_part_engine", "drill_part_fuel_tank", "drill_part_upgrade_module"]:
        part_id = item.get(field)
        if part_id:
            p = price_cache.weighted(part_id)
            if p:
                val = p * MULTIPLIERS["drill_parts"]
                total += val
                parts.append(display_name(part_id))

    if total > 0:
        return total, f"Drill Parts({', '.join(parts)}): {_fmt(total)}"
    return 0, ""


def price_dye(item, price_cache):
    """Price applied dye."""
    dye_id = item.get("dye_item")
    if not dye_id:
        return 0, ""
    p = price_cache.weighted(dye_id)
    if not p:
        return 0, ""
    value = p * MULTIPLIERS["dye"]
    return value, f"Dye: {_fmt(value)}"


def price_wood_singularity(item, price_cache):
    """Price Wood Singularity."""
    if not item.get("wood_singularity_count"):
        return 0, ""
    p = price_cache.weighted("WOOD_SINGULARITY")
    if not p:
        return 0, ""
    value = p * MULTIPLIERS["wood_singularity"]
    return value, f"Wood Singularity: {_fmt(value)}"


def price_farming_for_dummies(item, price_cache):
    """Price Farming for Dummies."""
    count = item.get("farming_for_dummies_count", 0)
    if not count:
        return 0, ""
    p = price_cache.weighted("FARMING_FOR_DUMMIES")
    if not p:
        return 0, ""
    value = count * p * MULTIPLIERS["farming_for_dummies"]
    return value, f"FFD(×{count}): {_fmt(value)}"


def price_etherwarp(item, price_cache):
    """Price Etherwarp Conduit (ethermerge NBT flag)."""
    if not item.get("ethermerge"):
        return 0, ""
    # Etherwarp requires Etherwarp Conduit + Etherwarp Merger
    conduit = price_cache.weighted("ETHERWARP_CONDUIT") or 0
    merger = price_cache.weighted("ETHERWARP_MERGER") or 0
    value = (conduit + merger) * MULTIPLIERS["etherwarp"]
    if value > 0:
        return value, f"Etherwarp: {_fmt(value)}"
    return 0, ""


def price_transmission_tuners(item, price_cache):
    """Price Transmission Tuners."""
    count = item.get("tuned_transmission", 0)
    if not count:
        return 0, ""
    p = price_cache.weighted("TRANSMISSION_TUNER")
    if not p:
        return 0, ""
    value = count * p * MULTIPLIERS["transmission_tuner"]
    return value, f"Tuners(×{count}): {_fmt(value)}"


def price_mana_disintegrator(item, price_cache):
    """Price Mana Disintegrator."""
    count = item.get("mana_disintegrator_count", 0)
    if not count:
        return 0, ""
    p = price_cache.weighted("MANA_DISINTEGRATOR")
    if not p:
        return 0, ""
    value = count * p * MULTIPLIERS["mana_disintegrator"]
    return value, f"Mana Disintegrator(×{count}): {_fmt(value)}"


# ─── Phase 1 New Modifier Handlers ────────────────────────────────────


def price_gemstone_slots(item, price_cache):
    """Price gemstone slot unlock costs (Divan's, Crimson Isle armor).

    Uses gemstonecosts.json to sum the material costs for unlocked slots.
    """
    gems = item.get("gems", {})
    if not gems:
        return 0, ""

    item_id = item.get("id", "")
    costs_data = get_gemstone_costs()
    item_costs = costs_data.get(item_id, {})
    if not item_costs:
        return 0, ""

    # Determine which slots are unlocked by checking which slots have data
    total = 0
    unlocked_count = 0
    for slot_key in gems:
        if slot_key.endswith("_gem"):
            continue
        # Find matching cost entry (e.g., "COMBAT_0" matches costs key)
        slot_cost = item_costs.get(slot_key, [])
        if not slot_cost:
            continue
        slot_value = 0
        for cost_entry in slot_cost:
            if isinstance(cost_entry, str) and ":" in cost_entry:
                mat_id, qty_str = cost_entry.rsplit(":", 1)
                try:
                    qty = int(qty_str)
                except ValueError:
                    continue
                if mat_id == "SKYBLOCK_COIN":
                    slot_value += qty
                else:
                    p = price_cache.weighted(mat_id)
                    if p:
                        slot_value += p * qty
        if slot_value > 0:
            total += slot_value
            unlocked_count += 1

    if total > 0:
        value = total * MULTIPLIERS["gemstone_slots"]
        return value, f"Gem Slots(×{unlocked_count}): {_fmt(value)}"
    return 0, ""


def price_prestige(item, price_cache):
    """Price Kuudra/Crimson prestige upgrade chain.

    Detects prestige tier from item ID prefix (HOT_, BURNING_, FIERY_, INFERNAL_)
    and sums the material costs for each tier applied.
    """
    item_id = item.get("id", "")
    prestige_data = get_prestige_costs()
    if not prestige_data:
        return 0, ""

    tier_order = prestige_data.get("tier_order", [])
    armor_sets = prestige_data.get("armor_sets", [])
    costs = prestige_data.get("costs", {})

    # Check if this item is a prestiged crimson armor piece
    item_tier = None
    for tier in tier_order:
        if item_id.startswith(f"{tier}_"):
            item_tier = tier
            break

    if not item_tier:
        return 0, ""

    # Verify it's from a valid armor set
    remainder = item_id[len(item_tier) + 1:]  # e.g., "CRIMSON_CHESTPLATE"
    valid = False
    for armor_set in armor_sets:
        if remainder.startswith(armor_set + "_"):
            valid = True
            break
    if not valid:
        return 0, ""

    # Sum costs for all tiers up to and including this one
    total = 0
    for tier in tier_order:
        tier_costs = costs.get(tier, {})
        for mat_id, qty in tier_costs.items():
            if mat_id == "SKYBLOCK_COIN":
                total += qty
            elif mat_id == "CRIMSON_ESSENCE":
                p = price_cache.weighted("ESSENCE_CRIMSON") or 0
                total += p * qty
            else:
                p = price_cache.weighted(mat_id)
                if p:
                    total += p * qty
                else:
                    # Try override price (e.g., HEAVY_PEARL, KUUDRA_TEETH)
                    override = price_cache.get_override_price(mat_id)
                    if override:
                        total += override * qty
        if tier == item_tier:
            break

    if total > 0:
        return total, f"Prestige({item_tier.title()}): {_fmt(total)}"
    return 0, ""


def price_enrichment(item, price_cache):
    """Price talisman enrichment (0.5× — applied to accessories)."""
    enrichment = item.get("talisman_enrichment")
    if not enrichment:
        return 0, ""
    # All enrichments have similar prices; use the specific one if available
    enrich_id = f"TALISMAN_ENRICHMENT_{enrichment.upper()}"
    p = price_cache.weighted(enrich_id)
    if not p:
        # Try generic "cheapest enrichment" approach — use attack speed as baseline
        p = price_cache.weighted("TALISMAN_ENRICHMENT_ATTACK_SPEED")
    if not p:
        return 0, ""
    value = p * MULTIPLIERS["enrichment"]
    return value, f"Enrichment({enrichment.replace('_', ' ').title()}): {_fmt(value)}"


def price_jalapeno_book(item, price_cache):
    """Price Jalapeno Book (0.8×)."""
    count = item.get("jalapeno_count", 0)
    if not count:
        return 0, ""
    p = price_cache.weighted("JALAPENO_BOOK")
    if not p:
        return 0, ""
    value = count * p * MULTIPLIERS["jalapeno"]
    return value, f"Jalapeño(×{count}): {_fmt(value)}"


def price_polarvoid_book(item, price_cache):
    """Price Polarvoid Book (1.0×)."""
    count = item.get("polarvoid", 0)
    if not count:
        return 0, ""
    p = price_cache.weighted("POLARVOID_BOOK")
    if not p:
        return 0, ""
    value = count * p * MULTIPLIERS["polarvoid"]
    return value, f"Polarvoid(×{count}): {_fmt(value)}"


def price_runes(item, price_cache):
    """Price applied runes (0.6× — cosmetic but tradeable)."""
    runes = item.get("rune")
    if not runes or not isinstance(runes, dict):
        return 0, ""
    total = 0
    for rune_type, rune_level in runes.items():
        rune_id = f"RUNE_{rune_type.upper()}_{rune_level}"
        p = price_cache.weighted(rune_id)
        if p:
            total += p * MULTIPLIERS["runes"]
    if total > 0:
        return total, f"Rune: {_fmt(total)}"
    return 0, ""


def price_midas(item, price_cache):
    """Price Midas weapons based on winning bid amount."""
    item_id = item.get("id", "")
    if "MIDAS" not in item_id:
        return 0, ""
    bid = item.get("winning_bid", 0)
    if not bid:
        return 0, ""
    # Midas items have value based on the coins paid at Dark Auction
    # The bid amount IS the base value (replaces normal base price)
    # We return 0 here since the bid affects base price, handled in price_single_item
    return 0, ""


# All modifier pricing functions
MODIFIER_PRICERS = [
    price_stars,        # needs essence_costs arg
    price_master_stars,
    price_hpb,
    price_recombobulator,
    price_enchantments,
    price_reforge,
    price_gemstones,
    price_gemstone_slots,  # Phase 1: slot unlock costs
    price_scrolls,
    price_art_of_war,
    price_art_of_peace,
    price_drill_parts,
    price_dye,
    price_wood_singularity,
    price_farming_for_dummies,
    price_etherwarp,
    price_transmission_tuners,
    price_mana_disintegrator,
    price_prestige,        # Phase 1: Kuudra prestige chain
    price_enrichment,      # Phase 1: talisman enrichment
    price_jalapeno_book,   # Phase 1
    price_polarvoid_book,  # Phase 1
    price_runes,           # Phase 1
]


def price_item_modifiers(item, price_cache, essence_costs):
    """Price all modifiers on an item. Returns (total_modifier_value, breakdown_list)."""
    total = 0
    breakdown = []

    for pricer in MODIFIER_PRICERS:
        if pricer == price_stars:
            value, desc = pricer(item, price_cache, essence_costs)
        else:
            value, desc = pricer(item, price_cache)
        if value > 0:
            total += value
            breakdown.append(desc)

    return total, breakdown


# ─── Item Valuation ──────────────────────────────────────────────────


def price_single_item(item, price_cache, essence_costs, no_cosmetic=False):
    """Price a single item with base value + modifiers.

    Uses variant-aware pricing (SkyHelper) for attribute rolls, skins,
    shiny items, and editioned items. Falls back to standard pricing.

    Returns dict with:
        id, name, base_value, modifier_value, total_value, soulbound,
        cosmetic, breakdown, source, count, variant_key, good_roll
    """
    item_id = item.get("id", "")
    if not item_id:
        return None

    count = item.get("count", 1)
    if count <= 0:
        count = 1

    soulbound = is_soulbound(item)
    cosmetic = is_cosmetic(item)

    if no_cosmetic and cosmetic:
        return {
            "id": item_id, "name": display_name(item_id),
            "base_value": 0, "modifier_value": 0, "total_value": 0,
            "soulbound": soulbound, "cosmetic": True,
            "breakdown": [], "source": "excluded", "count": count,
            "variant_key": None, "good_roll": None,
        }

    # Get base item price — try variant pricing first
    base_value = 0
    source = "unknown"
    variant_key = None
    good_roll = None

    # Check for Midas weapon special pricing
    if "MIDAS" in item_id:
        bid = item.get("winning_bid", 0)
        if bid and bid > 0:
            base_value = bid
            source = "midas_bid"

    if base_value == 0:
        # Try variant pricing (attribute rolls, skins, shiny, editioned)
        variant_price, vk = price_cache.variant_price(item_id, item)
        if vk:
            base_value = variant_price
            source = "skyhelper_variant"
            variant_key = vk
        elif variant_price:
            base_value = variant_price
            pi = price_cache.get_price(item_id)
            source = pi.get("source", "unknown")

    if base_value == 0 and soulbound:
        # Soulbound items: use market price if available, otherwise 0.
        # Don't use recursive craft cost — it inflates values for items
        # that can't actually be sold. Matches SkyHelper-Networth behavior.
        p = price_cache.weighted(item_id)
        if p:
            base_value = p
            source = "market_ref"
    elif base_value == 0:
        p = price_cache.weighted(item_id)
        if p:
            base_value = p
            pi = price_cache.get_price(item_id)
            source = pi.get("source", "unknown")

    # Check for good attribute rolls (informational)
    attributes = item.get("attributes")
    if attributes and isinstance(attributes, dict) and len(attributes) >= 2:
        good_roll = _check_good_roll(item_id, attributes)

    # Price modifiers
    modifier_value, breakdown = price_item_modifiers(item, price_cache, essence_costs)

    total = (base_value + modifier_value) * count

    return {
        "id": item_id,
        "name": display_name(item_id),
        "base_value": base_value * count,
        "modifier_value": modifier_value * count,
        "total_value": total,
        "soulbound": soulbound,
        "cosmetic": cosmetic,
        "breakdown": breakdown,
        "source": source,
        "count": count,
        "variant_key": variant_key,
        "good_roll": good_roll,
    }


def _check_good_roll(item_id, attributes):
    """Check if an item's attribute combo is a 'good roll' per SkyHanni data.

    Returns a short description string if good, or None.
    """
    good_rolls_data = get_good_rolls()
    if not good_rolls_data:
        return None

    sorted_attrs = sorted(attributes.keys())
    attr_pair = tuple(sorted_attrs[:2])

    # AttributeGoodRolls.json maps display name patterns to good combos
    # We need to match item_id against the patterns
    for pattern_name, roll_data in good_rolls_data.items():
        if not isinstance(roll_data, dict):
            continue
        # Check regex patterns against item_id
        for regex_pattern, combos in roll_data.items():
            try:
                if re.match(regex_pattern, item_id):
                    for combo in combos:
                        if isinstance(combo, list) and len(combo) >= 2:
                            combo_sorted = tuple(sorted(c.lower() for c in combo))
                            attr_sorted = tuple(a.lower() for a in attr_pair)
                            if combo_sorted == attr_sorted:
                                nice_names = [a.replace("_", " ").title() for a in attr_pair]
                                return f"{nice_names[0]}+{nice_names[1]}"
            except re.error:
                continue
    return None


# ─── Inventory Extraction ────────────────────────────────────────────


def extract_nbt_items(b64_data):
    """Decode a base64 NBT inventory blob and return list of item dicts."""
    if not b64_data:
        return []
    slot_items, _ = decode_nbt_inventory_slots(b64_data)
    return [item for item in slot_items if item and item.get("id")]


def extract_all_items(member, profile, raw_data):
    """Extract items from all storage locations.

    Returns dict of {category_name: [item_dicts]}.
    """
    categories = {}
    inv = member.get("inventory", {})

    # ── NBT inventory locations ──
    nbt_sources = {
        "Inventory": inv.get("inv_contents", {}).get("data", ""),
        "Armor": inv.get("inv_armor", {}).get("data", ""),
        "Ender Chest": inv.get("ender_chest_contents", {}).get("data", ""),
        "Accessory Bag": inv.get("bag_contents", {}).get("talisman_bag", {}).get("data", ""),
        "Wardrobe": inv.get("wardrobe_contents", {}).get("data", ""),
        "Equipment": inv.get("equipment_contents", {}).get("data", ""),
        "Personal Vault": inv.get("personal_vault_contents", {}).get("data", ""),
    }

    for name, data in nbt_sources.items():
        items = extract_nbt_items(data)
        if items:
            categories[name] = items

    # Backpacks (storage)
    backpacks = inv.get("backpack_contents", {})
    storage_items = []
    for slot in sorted(backpacks.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        bp_data = backpacks[slot].get("data", "") if isinstance(backpacks[slot], dict) else ""
        storage_items.extend(extract_nbt_items(bp_data))
    if storage_items:
        categories["Storage"] = storage_items

    # ── Museum ──
    # Items with borrowing=True are currently in the player's inventory,
    # so they're already counted in another category. Only include items
    # that are physically in the museum (borrowing=False or absent).
    # This matches SkyHelper-Networth's approach.
    museum_data = raw_data.get("museum")
    if museum_data and museum_data.get("success"):
        uuid = raw_data.get("uuid", "")
        members_museum = museum_data.get("members", {})
        member_museum = None
        for key, val in members_museum.items():
            if key.replace("-", "") == uuid:
                member_museum = val
                break
        if member_museum:
            museum_items_data = member_museum.get("items", {})
            museum_items = []
            for slot_name, slot_data in museum_items_data.items():
                if slot_data.get("borrowing"):
                    continue  # item is in player's inventory, skip
                nbt = slot_data.get("items", {}).get("data", "")
                items = extract_nbt_items(nbt)
                for item in items:
                    item["donated_museum"] = True  # mark as soulbound
                museum_items.extend(items)
            # Special items (no borrowing flag — always in museum)
            special = member_museum.get("special", [])
            for special_entry in special:
                nbt = special_entry.get("items", {}).get("data", "")
                items = extract_nbt_items(nbt)
                for item in items:
                    item["donated_museum"] = True
                museum_items.extend(items)
            if museum_items:
                categories["Museum"] = museum_items

    # ── Pets ──
    pets_data = member.get("pets_data", {}).get("pets", member.get("pets", []))
    if pets_data:
        pet_items = []
        for pet in pets_data:
            pet_type = pet.get("type", "")
            rarity = pet.get("tier", "")
            rarity_num = RARITY_NUM.get(rarity.lower(), -1)
            if pet_type and rarity_num >= 0:
                # Calculate pet level from XP (approximate — SkyHelper uses specific anchors)
                pet_xp = pet.get("exp", 0)
                pet_level = _estimate_pet_level(pet_xp, rarity_num, pet_type)
                pet_item = {
                    "id": f"{pet_type};{rarity_num}",
                    "count": 1,
                    "pet_held_item": pet.get("heldItem"),
                    "pet_candy_used": pet.get("candyUsed", 0),
                    "pet_active": pet.get("active", False),
                    "pet_level": pet_level,
                    "skin": pet.get("skin"),
                    "lore": [],
                }
                pet_items.append(pet_item)
        if pet_items:
            categories["Pets"] = pet_items

    # ── Sacks ──
    sacks = inv.get("sacks_counts", {})
    if sacks:
        sack_items = []
        for item_id, count_val in sacks.items():
            count = int(count_val) if count_val else 0
            if count > 0:
                sack_items.append({"id": item_id, "count": count, "lore": []})
        if sack_items:
            categories["Sacks"] = sack_items

    return categories


# ─── Pet-specific Pricing ─────────────────────────────────────────────


def _xp_fraction_for_level(level, rarity_num):
    """Calculate what fraction of total XP (to reach level 100) a given level represents.

    Uses the actual XP table. A level 90 pet might have used ~70% of the total
    XP because late levels cost exponentially more. This gives a much better
    interpolation curve than linear level-based interpolation.
    """
    offset = _PET_RARITY_OFFSET.get(rarity_num, 0)
    max_idx = offset + 99  # indices for levels 1→100

    # Total XP for level 100
    total_xp = sum(_PET_LEVELS_XP[offset:max_idx])
    if total_xp <= 0:
        return (level - 1) / 99  # fallback to linear

    # XP accumulated at the given level
    levels_gained = level - 1
    accum = sum(_PET_LEVELS_XP[offset:offset + levels_gained])

    return accum / total_xp


def _interpolate_pet_price(price_cache, pet_type, rarity_name, level,
                           rarity_num=None, skin=None):
    """Interpolate pet price between SkyHelper level anchors (1, 100, 200).

    Uses XP-fraction interpolation: a pet at X% of the total XP to level 100
    is priced at X% between LVL_1 and LVL_100 prices. This reflects the
    exponential XP curve — early levels are cheap, most value is in the
    last 10-20 levels.
    """
    prefix = f"{rarity_name}_{pet_type}"
    if skin:
        prefix = f"{rarity_name}_{pet_type}_SKINNED_{skin}"

    p1 = price_cache.get_skyhelper_price(f"LVL_1_{prefix}")
    p100 = price_cache.get_skyhelper_price(f"LVL_100_{prefix}")
    p200 = price_cache.get_skyhelper_price(f"LVL_200_{prefix}")

    if level <= 1 and p1:
        return p1, f"LVL_1_{prefix}"

    if level >= 200 and p200:
        return p200, f"LVL_200_{prefix}"

    if level >= 100 and p100:
        if level == 100:
            return p100, f"LVL_100_{prefix}"
        if p200:
            # For 100→200, use linear level interpolation (all levels cost the same)
            frac = (level - 100) / 100
            price = p100 + (p200 - p100) * frac
            return price, f"LVL_{level}_{prefix}(interp)"
        return p100, f"LVL_100_{prefix}"

    # Interpolate 1→100 using XP fraction
    if p1 and p100:
        if rarity_num is not None:
            frac = _xp_fraction_for_level(level, rarity_num)
        else:
            frac = (level - 1) / 99  # fallback to linear
        price = p1 + (p100 - p1) * frac
        return price, f"LVL_{level}_{prefix}(interp)"

    if p1:
        return p1, f"LVL_1_{prefix}"

    return None, None


def price_pet_item(item, price_cache):
    """Price a pet with its held item and candy.

    Uses SkyHelper level anchors (LVL_1, LVL_100, LVL_200) with linear
    interpolation for intermediate levels. Falls back to Moulberry LBIN.
    """
    item_id = item.get("id", "")
    base = 0
    source = "unknown"
    variant_key = None

    if ";" in item_id:
        pet_type, rarity_str = item_id.split(";", 1)
        try:
            rarity_num = int(rarity_str)
        except ValueError:
            rarity_num = -1

        pet_level = item.get("pet_level")
        pet_skin = item.get("skin")

        if pet_level is not None and rarity_num >= 0:
            rarity_name = RARITY_NAME.get(rarity_num, "")

            # Try skinned variant first, then base
            if pet_skin:
                price, vk = _interpolate_pet_price(
                    price_cache, pet_type, rarity_name, pet_level,
                    rarity_num=rarity_num, skin=pet_skin)
                if price:
                    base = price
                    source = "skyhelper_variant"
                    variant_key = vk

            if base == 0:
                price, vk = _interpolate_pet_price(
                    price_cache, pet_type, rarity_name, pet_level,
                    rarity_num=rarity_num)
                if price:
                    base = price
                    source = "skyhelper_variant"
                    variant_key = vk

    if base == 0:
        base = price_cache.weighted(item_id) or 0
        if base > 0:
            pi = price_cache.get_price(item_id)
            source = pi.get("source", "unknown")

    modifier_value = 0
    breakdown = []

    # Held item
    held = item.get("pet_held_item")
    if held:
        p = price_cache.weighted(held)
        if p:
            val = p * MULTIPLIERS["pet_item"]
            modifier_value += val
            breakdown.append(f"Held({display_name(held)}): {_fmt(val)}")

    # Pet candy
    candy = item.get("pet_candy_used", 0)
    if candy:
        p = price_cache.weighted("PET_ITEM_CANDY") or 0
        if p:
            val = candy * p * MULTIPLIERS["pet_candy"]
            modifier_value += val
            breakdown.append(f"Candy(×{candy}): {_fmt(val)}")

    # Pet skin (if not already priced via variant key)
    skin = item.get("skin")
    if skin and not variant_key:
        skin_id = f"PET_SKIN_{skin}"
        p = price_cache.weighted(skin_id)
        if p:
            val = p * MULTIPLIERS.get("pet_skin", 0.9)
            modifier_value += val
            breakdown.append(f"Skin: {_fmt(val)}")

    total = base + modifier_value

    return {
        "id": item_id,
        "name": display_name(item_id),
        "base_value": base,
        "modifier_value": modifier_value,
        "total_value": total,
        "soulbound": False,
        "cosmetic": False,
        "breakdown": breakdown,
        "source": source,
        "count": 1,
        "variant_key": variant_key,
        "good_roll": None,
    }


# ─── Main Calculation ────────────────────────────────────────────────


def calculate_networth(member, profile, raw_data, price_cache,
                       no_cosmetic=False):
    """Calculate full networth across all categories.

    Returns dict with:
        categories: {name: {items: [priced_items], total: float, soulbound_total: float}}
        totals: {total, unsoulbound, soulbound, cosmetic, unpriced_count, unpriced_items}
    """
    essence_costs = load_essence_costs()

    # Pre-fetch all prices in bulk
    price_cache._fetch_bazaar()
    price_cache._fetch_moulberry()

    # Extract all items from all storage locations
    raw_categories = extract_all_items(member, profile, raw_data)

    result = {"categories": {}, "totals": {
        "total": 0, "unsoulbound": 0, "soulbound": 0,
        "cosmetic": 0, "unpriced_count": 0, "unpriced_items": [],
    }}

    for cat_name, items in raw_categories.items():
        cat_total = 0
        cat_soulbound = 0
        priced_items = []

        for item in items:
            item_id = item.get("id", "")

            # Pets get special handling
            if ";" in item_id and cat_name == "Pets":
                priced = price_pet_item(item, price_cache)
            # Sacks are simple: count × weighted price
            elif cat_name == "Sacks":
                count = item.get("count", 1)
                p = price_cache.weighted(item_id)
                val = (p or 0) * count
                priced = {
                    "id": item_id, "name": display_name(item_id),
                    "base_value": val, "modifier_value": 0,
                    "total_value": val, "soulbound": False,
                    "cosmetic": False, "breakdown": [],
                    "source": "bazaar" if p else "unknown",
                    "count": count,
                }
            else:
                priced = price_single_item(
                    item, price_cache, essence_costs, no_cosmetic)

            if priced is None:
                continue

            cat_total += priced["total_value"]
            if priced["soulbound"]:
                cat_soulbound += priced["total_value"]

            if priced["total_value"] == 0 and priced["source"] == "unknown":
                result["totals"]["unpriced_count"] += 1
                result["totals"]["unpriced_items"].append(priced["id"])

            priced_items.append(priced)

        result["categories"][cat_name] = {
            "items": priced_items,
            "total": cat_total,
            "soulbound_total": cat_soulbound,
        }
        result["totals"]["total"] += cat_total
        result["totals"]["soulbound"] += cat_soulbound

    # ── Purse ──
    currencies = member.get("currencies", {})
    purse = currencies.get("coin_purse", member.get("coin_purse", 0))
    result["categories"]["Purse"] = {
        "items": [{"id": "COINS", "name": "Coins", "total_value": purse,
                   "base_value": purse, "modifier_value": 0, "soulbound": False,
                   "cosmetic": False, "breakdown": [], "source": "coins", "count": 1}],
        "total": purse, "soulbound_total": 0,
    }
    result["totals"]["total"] += purse

    # ── Bank ──
    banking = profile.get("banking", {})
    bank = banking.get("balance")
    if bank is not None:
        result["categories"]["Bank"] = {
            "items": [{"id": "BANK", "name": "Bank Balance", "total_value": bank,
                       "base_value": bank, "modifier_value": 0, "soulbound": False,
                       "cosmetic": False, "breakdown": [], "source": "coins", "count": 1}],
            "total": bank, "soulbound_total": 0,
        }
        result["totals"]["total"] += bank

    # ── Essence (tracked but flagged — may not be tradeable) ──
    essence_data = member.get("currencies", {}).get("essence", {})
    if essence_data:
        essence_items = []
        essence_total = 0
        for etype in ESSENCE_BAZAAR:
            count = essence_data.get(etype, {}).get("current", 0)
            if count > 0:
                bz_id = ESSENCE_BAZAAR[etype]
                p = price_cache.weighted(bz_id) or 0
                val = p * count
                essence_total += val
                essence_items.append({
                    "id": bz_id, "name": f"{etype.title()} Essence",
                    "total_value": val, "base_value": val, "modifier_value": 0,
                    "soulbound": False, "cosmetic": False,
                    "breakdown": [], "source": "bazaar", "count": count,
                })
        if essence_items:
            result["categories"]["Essence"] = {
                "items": essence_items, "total": essence_total,
                "soulbound_total": 0,
            }
            result["totals"]["total"] += essence_total

    # Calculate unsoulbound
    result["totals"]["unsoulbound"] = (
        result["totals"]["total"] - result["totals"]["soulbound"]
    )

    return result


# ─── Output Formatting ───────────────────────────────────────────────


# Preferred category display order
CATEGORY_ORDER = [
    "Purse", "Bank", "Inventory", "Armor", "Ender Chest", "Accessory Bag",
    "Wardrobe", "Equipment", "Pets", "Museum", "Sacks", "Storage",
    "Personal Vault", "Essence",
]


def print_networth(result, player_name, top_n=10, category_filter=None,
                   verbose=False):
    """Print formatted networth output."""
    totals = result["totals"]
    categories = result["categories"]

    print()
    print("═" * 55)
    print(f"  NETWORTH SUMMARY — {player_name}")
    print("═" * 55)
    print()

    # Category breakdown
    print(f"  {'Category':<25s} {'Value':>12s}")
    print(f"  {'─' * 25} {'─' * 12}")

    # Sort categories in display order, unknown ones at end
    cat_order = {name: i for i, name in enumerate(CATEGORY_ORDER)}
    sorted_cats = sorted(categories.keys(),
                         key=lambda x: cat_order.get(x, 999))

    for cat_name in sorted_cats:
        if category_filter and cat_name.lower() != category_filter.lower():
            continue
        cat = categories[cat_name]
        val_str = _fmt(cat["total"])
        sb_str = ""
        if cat["soulbound_total"] > 0:
            sb_str = f"  ({_fmt(cat['soulbound_total'])} SB)"
        print(f"  {cat_name:<25s} {val_str:>12s}{sb_str}")

    print(f"  {'─' * 25} {'─' * 12}")
    print(f"  {'TOTAL NETWORTH':<25s} {_fmt(totals['total']):>12s}")
    print(f"  {'UNSOULBOUND NETWORTH':<25s} {_fmt(totals['unsoulbound']):>12s}")
    print()

    # Top valuable items
    all_items = []
    for cat_name, cat in categories.items():
        for item in cat["items"]:
            if item["total_value"] > 0 and item["id"] not in ("COINS", "BANK"):
                item["_category"] = cat_name
                all_items.append(item)

    all_items.sort(key=lambda x: x["total_value"], reverse=True)

    if category_filter:
        all_items = [i for i in all_items
                     if i.get("_category", "").lower() == category_filter.lower()]

    if verbose:
        display_items = all_items
        label = "All Items"
    else:
        display_items = all_items[:top_n]
        label = f"Top {min(top_n, len(all_items))} Most Valuable Items"

    if display_items:
        print(f"  {label}:")
        for i, item in enumerate(display_items, 1):
            name = item["name"]
            tags = []
            if item.get("soulbound"):
                tags.append("Soulbound")
            if item.get("cosmetic"):
                tags.append("Cosmetic")
            if item.get("count", 1) > 1:
                tags.append(f"×{item['count']}")
            tag_str = f"  [{', '.join(tags)}]" if tags else ""
            source_note = ""
            if item.get("source") == "craft_cost":
                source_note = " (craft cost)"
            elif item.get("source") == "market_ref":
                source_note = " (market ref)"

            print(f"    {i:>3d}. {name:<35s} {_fmt(item['total_value']):>10s}{tag_str}{source_note}")

            # Show modifier breakdown for high-value items
            if item.get("breakdown"):
                bd_str = " | ".join(item["breakdown"])
                base_str = f"Base: {_fmt(item['base_value'])}"
                print(f"         {base_str} | {bd_str}")

            # Show variant pricing and good roll info
            if item.get("variant_key"):
                print(f"         Variant: {item['variant_key']}")
            if item.get("good_roll"):
                print(f"         ✓ Good roll: {item['good_roll']}")

        print()

    # Soulbound summary
    sb_items = [i for i in all_items if i.get("soulbound")]
    if sb_items:
        sb_total = sum(i["total_value"] for i in sb_items)
        market_ref_items = [i for i in sb_items if i.get("source") == "market_ref"]
        print(f"  Soulbound Items (valued at market price):   {_fmt(sb_total)}")
        unpriced_sb = [i for i in sb_items if i["total_value"] == 0 and i["base_value"] == 0]
        if unpriced_sb:
            print(f"    {len(unpriced_sb)} soulbound items with no market price (valued at 0)")
        print()

    # Unpriced items (only show when not filtering by category)
    if not category_filter:
        unpriced = totals.get("unpriced_items", [])
        if unpriced:
            unique = list(dict.fromkeys(unpriced))
            print(f"  Unpriced Items (no market data):            {len(unique)} items")
            for uid in unique[:10]:
                print(f"    - {display_name(uid)} ({uid})")
            if len(unique) > 10:
                print(f"    ... and {len(unique) - 10} more")
            print()


def print_json(result, player_name):
    """Print machine-readable JSON output."""
    output = {
        "player": player_name,
        "total_networth": result["totals"]["total"],
        "unsoulbound_networth": result["totals"]["unsoulbound"],
        "soulbound_value": result["totals"]["soulbound"],
        "unpriced_count": result["totals"]["unpriced_count"],
        "categories": {},
    }
    for cat_name, cat in result["categories"].items():
        output["categories"][cat_name] = {
            "total": cat["total"],
            "soulbound_total": cat["soulbound_total"],
            "item_count": len(cat["items"]),
            "items": [
                {
                    "id": i["id"], "name": i["name"],
                    "total_value": i["total_value"],
                    "base_value": i["base_value"],
                    "modifier_value": i["modifier_value"],
                    "soulbound": i["soulbound"],
                    "source": i["source"],
                }
                for i in cat["items"] if i["total_value"] > 0
            ],
        }
    print(json.dumps(output, indent=2))


# ─── Main ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="SkyBlock Networth Calculator")
    parser.add_argument("--category", type=str, metavar="NAME",
                        help="Show only a specific category (e.g., pets, wardrobe)")
    parser.add_argument("--top", type=int, default=10, metavar="N",
                        help="Show top N most valuable items (default: 10)")
    parser.add_argument("--no-cosmetic", action="store_true",
                        help="Exclude cosmetic items (dyes, skins, runes)")
    parser.add_argument("--json", action="store_true",
                        help="Machine-readable JSON output")
    parser.add_argument("--verbose", action="store_true",
                        help="List every priced item, not just top N")
    args = parser.parse_args()

    # Load profile data
    member, profile, raw_data = load_profile()
    player_name = raw_data.get("player", "Unknown")

    print(f"  Calculating networth for {player_name}...", file=sys.stderr)

    # Initialize price cache and fetch bulk data
    price_cache = PriceCache()

    # Calculate networth
    result = calculate_networth(
        member, profile, raw_data, price_cache,
        no_cosmetic=args.no_cosmetic,
    )

    price_cache.flush()

    # Output
    if args.json:
        print_json(result, player_name)
    else:
        print_networth(
            result, player_name,
            top_n=args.top,
            category_filter=args.category,
            verbose=args.verbose,
        )


if __name__ == "__main__":
    main()
