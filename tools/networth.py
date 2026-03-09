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
from crafts import parse_recipes, find_recipe
from profile import decode_nbt_inventory_slots

DATA_DIR = Path(__file__).parent.parent / "data"
LAST_PROFILE_PATH = DATA_DIR / "last_profile.json"
NEU_ITEMS_DIR = DATA_DIR / "neu-repo" / "items"
ESSENCECOSTS_PATH = DATA_DIR / "neu-repo" / "constants" / "essencecosts.json"

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
    "master_stars": 1.0,     # First/Second/Third/Fourth/Fifth Master Star
    "scrolls": 1.0,          # Necron Blade Scrolls
    "art_of_war": 0.6,       # Art of War
    "art_of_peace": 0.8,     # Art of Peace
    "drill_parts": 1.0,      # Drill engine/fuel tank/upgrade module
    "dye": 0.9,              # Dyes
    "pet_candy": 0.65,       # Pet Candy Used
    "pet_item": 1.0,         # Held pet item
    "wood_singularity": 0.5, # Wood Singularity
    "farming_for_dummies": 0.5,  # Farming for Dummies
    "etherwarp": 1.0,        # Etherwarp Conduit
    "transmission_tuner": 0.7,   # Transmission Tuners
    "mana_disintegrator": 0.8,   # Mana Disintegrator
}

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
    "chomp": "KUUDRA_MANDIBLE", "coldfused": "ENTROPY_SUPPRESSOR",
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
    "warped": "AOTE_STONE", "waxed": "BLAZE_WAX",
    "withered": "WITHER_BLOOD",
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
    """Check if an item is cosmetic (dye, skin, rune, cosmetic category)."""
    item_id = item.get("id", "")
    cat = get_category(item_id)
    if cat in COSMETIC_CATEGORIES:
        return True
    for pattern in COSMETIC_PATTERNS:
        if pattern in item_id:
            return True
    if item.get("dye_item"):
        return True
    if item.get("skin"):
        return True
    if item.get("rune"):
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
    """Price enchantments by looking up each enchanted book on AH."""
    enchants = item.get("enchants", {})
    if not enchants:
        return 0, ""

    total = 0
    for ench_name, level in enchants.items():
        # Enchanted book ID format: ENCHANTMENT_{NAME}_{LEVEL}
        book_id = f"ENCHANTMENT_{ench_name.upper()}_{level}"
        p = price_cache.weighted(book_id)
        if p:
            total += p * MULTIPLIERS["enchantments"]

    if total > 0:
        return total, f"Enchants({len(enchants)}): {_fmt(total)}"
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


# All modifier pricing functions
MODIFIER_PRICERS = [
    price_stars,        # needs essence_costs arg
    price_master_stars,
    price_hpb,
    price_recombobulator,
    price_enchantments,
    price_reforge,
    price_gemstones,
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


# ─── Soulbound Craft Cost ────────────────────────────────────────────


def calculate_recursive_craft_cost(item_id, price_cache, recipes=None, visited=None):
    """Calculate crafting cost for an item, recursively pricing ingredients.

    For each ingredient:
    1. Try Bazaar weighted price
    2. Try AH LBIN
    3. If neither, try recursive recipe lookup
    Returns cost or None if unpriceable.
    """
    if visited is None:
        visited = set()
    if item_id in visited:
        return None  # circular recipe
    visited.add(item_id)

    recipe = find_recipe(item_id, recipes)
    if not recipe:
        return None

    total = 0
    for ing_id, qty in recipe["ingredients"].items():
        # Try market price first
        p = price_cache.weighted(ing_id)
        if p:
            total += p * qty
            continue

        # Try recursive recipe
        sub_cost = calculate_recursive_craft_cost(ing_id, price_cache, recipes, visited.copy())
        if sub_cost is not None:
            total += sub_cost * qty
        else:
            return None  # can't price this ingredient

    return total / recipe["output_count"]


# ─── Item Valuation ──────────────────────────────────────────────────


def price_single_item(item, price_cache, essence_costs, recipes=None, no_cosmetic=False):
    """Price a single item with base value + modifiers.

    Returns dict with:
        id, name, base_value, modifier_value, total_value, soulbound,
        cosmetic, breakdown, source, count
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
        }

    # Get base item price
    base_value = 0
    source = "unknown"

    if soulbound:
        # Try craft cost for soulbound items
        craft_cost = calculate_recursive_craft_cost(item_id, price_cache, recipes)
        if craft_cost is not None:
            base_value = craft_cost
            source = "craft_cost"
        else:
            # Fallback: try market price anyway (some soulbound items have
            # tradeable versions, gives a reference value)
            p = price_cache.weighted(item_id)
            if p:
                base_value = p
                source = "market_ref"
    else:
        p = price_cache.weighted(item_id)
        if p:
            base_value = p
            pi = price_cache.get_price(item_id)
            source = pi.get("source", "unknown")

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
    }


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
                nbt = slot_data.get("items", {}).get("data", "")
                items = extract_nbt_items(nbt)
                for item in items:
                    item["donated_museum"] = True  # mark as soulbound
                museum_items.extend(items)
            # Also handle special items
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
                pet_item = {
                    "id": f"{pet_type};{rarity_num}",
                    "count": 1,
                    "pet_held_item": pet.get("heldItem"),
                    "pet_candy_used": pet.get("candyUsed", 0),
                    "pet_active": pet.get("active", False),
                    "lore": [],  # pets don't have lore in this format
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


def price_pet_item(item, price_cache):
    """Price a pet with its held item and candy. Returns priced item dict."""
    item_id = item.get("id", "")
    base = price_cache.weighted(item_id) or 0

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

    total = base + modifier_value

    pi = price_cache.get_price(item_id)
    source = pi.get("source", "unknown") if base > 0 else "unknown"

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
    recipes = parse_recipes()

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
                    item, price_cache, essence_costs, recipes, no_cosmetic)

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

        print()

    # Soulbound summary
    sb_items = [i for i in all_items if i.get("soulbound")]
    if sb_items:
        sb_total = sum(i["total_value"] for i in sb_items)
        craft_cost_items = [i for i in sb_items if i.get("source") == "craft_cost"]
        print(f"  Soulbound Items (valued at craft cost):     {_fmt(sb_total)}")
        if craft_cost_items:
            print(f"    {len(craft_cost_items)} items priced via recursive recipe lookup")
        print()

    # Unpriced items (only show when not filtering by category)
    if not category_filter:
        unpriced = totals.get("unpriced_items", [])
        if unpriced:
            unique = list(dict.fromkeys(unpriced))
            print(f"  Unpriced Items (no market/recipe data):     {len(unique)} items")
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
