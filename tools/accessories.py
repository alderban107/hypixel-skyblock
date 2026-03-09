#!/usr/bin/env python3
"""Missing Accessories Finder for Hypixel SkyBlock.

Compares the player's accessories against the full list from the Hypixel
items API, handles upgrade chains and aliases (ported from SkyCrypt),
calculates Magical Power, and ranks missing accessories by cost-efficiency.

Usage:
    python3 accessories.py                    # full missing accessories report
    python3 accessories.py --budget 10m       # only show within 10M total budget
    python3 accessories.py --sort cost        # sort by absolute cost instead of coins/MP
    python3 accessories.py --upgrades-only    # only show upgrade opportunities
    python3 accessories.py --inactive         # focus on inactive/duplicate cleanup
    python3 accessories.py --available-only   # hide locked/unobtainable
    python3 accessories.py --json             # machine-readable output
"""

import argparse
import json
import re
import sys
from pathlib import Path

from items import (display_name, get_item, get_items_data, get_category,
                   get_tier, check_requirements, get_all_requirements)
from pricing import PriceCache, _fmt
from crafts import find_recipe, calculate_craft_cost
from profile import decode_nbt_inventory_slots

DATA_DIR = Path(__file__).parent.parent / "data"
LAST_PROFILE_PATH = DATA_DIR / "last_profile.json"
NEU_ITEMS_DIR = DATA_DIR / "neu-repo" / "items"

# ─── Magical Power per rarity ─────────────────────────────────────────

MP_PER_RARITY = {
    "COMMON": 3,
    "UNCOMMON": 5,
    "RARE": 8,
    "EPIC": 12,
    "LEGENDARY": 16,
    "MYTHIC": 22,
    "SPECIAL": 3,
    "VERY_SPECIAL": 5,
    "VERY SPECIAL": 5,
    "SUPREME": 22,  # Treat same as mythic
}

# ─── Upgrade chains (ported from SkyCrypt) ─────────────────────────────

UPGRADE_CHAINS = [
    ["WOLF_TALISMAN", "WOLF_RING"],
    ["POTION_AFFINITY_TALISMAN", "RING_POTION_AFFINITY", "ARTIFACT_POTION_AFFINITY"],
    ["FEATHER_TALISMAN", "FEATHER_RING", "FEATHER_ARTIFACT"],
    ["SEA_CREATURE_TALISMAN", "SEA_CREATURE_RING", "SEA_CREATURE_ARTIFACT"],
    ["HEALING_TALISMAN", "HEALING_RING"],
    ["CANDY_TALISMAN", "CANDY_RING", "CANDY_ARTIFACT", "CANDY_RELIC"],
    ["INTIMIDATION_TALISMAN", "INTIMIDATION_RING", "INTIMIDATION_ARTIFACT", "INTIMIDATION_RELIC"],
    ["SPIDER_TALISMAN", "SPIDER_RING", "SPIDER_ARTIFACT"],
    ["RED_CLAW_TALISMAN", "RED_CLAW_RING", "RED_CLAW_ARTIFACT"],
    ["HUNTER_TALISMAN", "HUNTER_RING"],
    ["ZOMBIE_TALISMAN", "ZOMBIE_RING", "ZOMBIE_ARTIFACT"],
    ["BAT_TALISMAN", "BAT_RING", "BAT_ARTIFACT"],
    ["SPEED_TALISMAN", "SPEED_RING", "SPEED_ARTIFACT"],
    ["PERSONAL_COMPACTOR_4000", "PERSONAL_COMPACTOR_5000", "PERSONAL_COMPACTOR_6000", "PERSONAL_COMPACTOR_7000"],
    ["PERSONAL_DELETOR_4000", "PERSONAL_DELETOR_5000", "PERSONAL_DELETOR_6000", "PERSONAL_DELETOR_7000"],
    ["SCARF_STUDIES", "SCARF_THESIS", "SCARF_GRIMOIRE"],
    ["CAT_TALISMAN", "LYNX_TALISMAN", "CHEETAH_TALISMAN"],
    ["SHADY_RING", "CROOKED_ARTIFACT", "SEAL_OF_THE_FAMILY"],
    ["TREASURE_TALISMAN", "TREASURE_RING", "TREASURE_ARTIFACT"],
    ["BEASTMASTER_CREST_COMMON", "BEASTMASTER_CREST_UNCOMMON", "BEASTMASTER_CREST_RARE",
     "BEASTMASTER_CREST_EPIC", "BEASTMASTER_CREST_LEGENDARY"],
    ["RAGGEDY_SHARK_TOOTH_NECKLACE", "DULL_SHARK_TOOTH_NECKLACE", "HONED_SHARK_TOOTH_NECKLACE",
     "SHARP_SHARK_TOOTH_NECKLACE", "RAZOR_SHARP_SHARK_TOOTH_NECKLACE"],
    ["BAT_PERSON_TALISMAN", "BAT_PERSON_RING", "BAT_PERSON_ARTIFACT"],
    ["LUCKY_HOOF", "ETERNAL_HOOF"],
    ["WITHER_ARTIFACT", "WITHER_RELIC"],
    ["WEDDING_RING_0", "WEDDING_RING_2", "WEDDING_RING_4", "WEDDING_RING_7", "WEDDING_RING_9"],
    ["CAMPFIRE_TALISMAN_1", "CAMPFIRE_TALISMAN_4", "CAMPFIRE_TALISMAN_8",
     "CAMPFIRE_TALISMAN_13", "CAMPFIRE_TALISMAN_21"],
    ["JERRY_TALISMAN_GREEN", "JERRY_TALISMAN_BLUE", "JERRY_TALISMAN_PURPLE", "JERRY_TALISMAN_GOLDEN"],
    ["TITANIUM_TALISMAN", "TITANIUM_RING", "TITANIUM_ARTIFACT", "TITANIUM_RELIC"],
    ["BAIT_RING", "SPIKED_ATROCITY"],
    ["MASTER_SKULL_TIER_1", "MASTER_SKULL_TIER_2", "MASTER_SKULL_TIER_3",
     "MASTER_SKULL_TIER_4", "MASTER_SKULL_TIER_5", "MASTER_SKULL_TIER_6", "MASTER_SKULL_TIER_7"],
    ["SOULFLOW_PILE", "SOULFLOW_BATTERY", "SOULFLOW_SUPERCELL"],
    ["ENDER_ARTIFACT", "ENDER_RELIC"],
    ["POWER_TALISMAN", "POWER_RING", "POWER_ARTIFACT", "POWER_RELIC"],
    ["BINGO_TALISMAN", "BINGO_RING", "BINGO_ARTIFACT", "BINGO_RELIC"],
    ["BURSTSTOPPER_TALISMAN", "BURSTSTOPPER_ARTIFACT"],
    ["ODGERS_BRONZE_TOOTH", "ODGERS_SILVER_TOOTH", "ODGERS_GOLD_TOOTH", "ODGERS_DIAMOND_TOOTH"],
    ["GREAT_SPOOK_TALISMAN", "GREAT_SPOOK_RING", "GREAT_SPOOK_ARTIFACT"],
    ["DRACONIC_TALISMAN", "DRACONIC_RING", "DRACONIC_ARTIFACT"],
    ["BURNING_KUUDRA_CORE", "FIERY_KUUDRA_CORE", "INFERNAL_KUUDRA_CORE"],
    ["VACCINE_TALISMAN", "VACCINE_RING", "VACCINE_ARTIFACT"],
    ["WHITE_GIFT_TALISMAN", "GREEN_GIFT_TALISMAN", "BLUE_GIFT_TALISMAN",
     "PURPLE_GIFT_TALISMAN", "GOLD_GIFT_TALISMAN"],
    ["GLACIAL_TALISMAN", "GLACIAL_RING", "GLACIAL_ARTIFACT"],
    ["CROPIE_TALISMAN", "SQUASH_RING", "FERMENTO_ARTIFACT"],
    ["KUUDRA_FOLLOWER_ARTIFACT", "KUUDRA_FOLLOWER_RELIC"],
    ["AGARIMOO_TALISMAN", "AGARIMOO_RING", "AGARIMOO_ARTIFACT"],
    ["BLOOD_DONOR_TALISMAN", "BLOOD_DONOR_RING", "BLOOD_DONOR_ARTIFACT"],
    ["LUSH_TALISMAN", "LUSH_RING", "LUSH_ARTIFACT"],
    ["ANITA_TALISMAN", "ANITA_RING", "ANITA_ARTIFACT"],
    ["PESTHUNTER_BADGE", "PESTHUNTER_RING", "PESTHUNTER_ARTIFACT"],
    ["NIBBLE_CHOCOLATE_STICK", "SMOOTH_CHOCOLATE_BAR", "RICH_CHOCOLATE_CHUNK",
     "GANACHE_CHOCOLATE_SLAB", "PRESTIGE_CHOCOLATE_REALM"],
    ["COIN_TALISMAN", "RING_OF_COINS", "ARTIFACT_OF_COINS", "RELIC_OF_COINS"],
    ["SCAVENGER_TALISMAN", "SCAVENGER_RING", "SCAVENGER_ARTIFACT"],
    ["EMERALD_RING", "EMERALD_ARTIFACT"],
    ["MINERAL_TALISMAN", "GLOSSY_MINERAL_TALISMAN"],
    ["HASTE_RING", "HASTE_ARTIFACT"],
]

# ─── Aliases (ported from SkyCrypt) ────────────────────────────────────
# Maps canonical ID → list of alternate IDs that represent the same accessory

ACCESSORY_ALIASES = {
    "WEDDING_RING_0": ["WEDDING_RING_1"],
    "WEDDING_RING_2": ["WEDDING_RING_3"],
    "WEDDING_RING_4": ["WEDDING_RING_5", "WEDDING_RING_6"],
    "WEDDING_RING_7": ["WEDDING_RING_8"],
    "CAMPFIRE_TALISMAN_1": ["CAMPFIRE_TALISMAN_2", "CAMPFIRE_TALISMAN_3"],
    "CAMPFIRE_TALISMAN_4": ["CAMPFIRE_TALISMAN_5", "CAMPFIRE_TALISMAN_6", "CAMPFIRE_TALISMAN_7"],
    "CAMPFIRE_TALISMAN_8": ["CAMPFIRE_TALISMAN_9", "CAMPFIRE_TALISMAN_10",
                            "CAMPFIRE_TALISMAN_11", "CAMPFIRE_TALISMAN_12"],
    "CAMPFIRE_TALISMAN_13": ["CAMPFIRE_TALISMAN_14", "CAMPFIRE_TALISMAN_15",
                             "CAMPFIRE_TALISMAN_16", "CAMPFIRE_TALISMAN_17",
                             "CAMPFIRE_TALISMAN_18", "CAMPFIRE_TALISMAN_19",
                             "CAMPFIRE_TALISMAN_20"],
    "CAMPFIRE_TALISMAN_21": ["CAMPFIRE_TALISMAN_22", "CAMPFIRE_TALISMAN_23",
                             "CAMPFIRE_TALISMAN_24", "CAMPFIRE_TALISMAN_25",
                             "CAMPFIRE_TALISMAN_26", "CAMPFIRE_TALISMAN_27",
                             "CAMPFIRE_TALISMAN_28", "CAMPFIRE_TALISMAN_29"],
    "PARTY_HAT_CRAB": ["PARTY_HAT_CRAB_ANIMATED", "PARTY_HAT_SLOTH", "BALLOON_HAT_2024"],
    "PIGGY_BANK": ["BROKEN_PIGGY_BANK", "CRACKED_PIGGY_BANK"],
    "DANTE_TALISMAN": ["DANTE_RING"],
}

# ─── Ignored accessories (ported from SkyCrypt) ───────────────────────
# Items that exist in the API but are unobtainable or shouldn't count

IGNORED_ACCESSORIES = {
    "BINGO_HEIRLOOM", "LUCK_TALISMAN", "TALISMAN_OF_SPACE", "RING_OF_SPACE",
    "MASTER_SKULL_TIER_8", "MASTER_SKULL_TIER_9", "MASTER_SKULL_TIER_10",
    "COMPASS_TALISMAN", "ARTIFACT_OF_SPACE", "GRIZZLY_PAW", "ETERNAL_CRYSTAL",
    "OLD_BOOT", "ARGOFAY_TRINKET", "DEFECTIVE_MONITOR", "PUNCHCARD_ARTIFACT",
    "HARMONIOUS_SURGERY_TOOLKIT", "CRUX_TALISMAN_1", "CRUX_TALISMAN_2",
    "CRUX_TALISMAN_3", "CRUX_TALISMAN_4", "CRUX_TALISMAN_5", "CRUX_TALISMAN_6",
    "WARDING_TRINKET", "RING_OF_BROKEN_LOVE", "GARLIC_FLAVORED_GUMMY_BEAR",
    "GENERAL_MEDALLION",
}

# ─── Special accessories ──────────────────────────────────────────────

SPECIAL_ACCESSORIES = {
    "BOOK_OF_PROGRESSION": {"allows_recomb": False},
    "PANDORAS_BOX": {"allows_recomb": False},
    "RIFT_PRISM": {"allows_recomb": False},
    "HOCUS_POCUS_CIPHER": {"allows_recomb": True},
    "TRAPPER_CREST": {},
    "PULSE_RING": {},
    "POWER_ARTIFACT": {},
}

# Rarity tag pattern from lore (last line)
_COLOR_CODE_RE = re.compile(r"§[0-9a-fk-or]")
_RARITY_TAG_RE = re.compile(
    r"(COMMON|UNCOMMON|RARE|EPIC|LEGENDARY|MYTHIC|SPECIAL|VERY SPECIAL|SUPREME)"
    r"\s+(DUNGEON\s+)?ACCESSORY"
)


# ─── Profile Loading ──────────────────────────────────────────────────

def load_profile():
    """Load last_profile.json. Returns (member, profile, data) or exits."""
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


# ─── Rarity Resolution ────────────────────────────────────────────────

def _rarity_from_neu(item_id):
    """Try to get rarity from NEU repo lore (last line)."""
    neu_path = NEU_ITEMS_DIR / f"{item_id}.json"
    if not neu_path.exists():
        return None
    try:
        data = json.loads(neu_path.read_text())
        lore = data.get("lore", [])
        if not lore:
            return None
        last = _COLOR_CODE_RE.sub("", lore[-1]).strip()
        m = _RARITY_TAG_RE.search(last)
        if m:
            return m.group(1).replace(" ", "_")
        return None
    except (json.JSONDecodeError, OSError):
        return None


def get_accessory_rarity(item_id, item_data=None):
    """Get the base rarity for an accessory. Tries API tier, then NEU lore."""
    if item_data and item_data.get("tier"):
        return item_data["tier"]
    tier = get_tier(item_id)
    if tier:
        return tier
    return _rarity_from_neu(item_id)


def rarity_from_lore(lore_lines):
    """Extract rarity from item lore lines (handles recombobulated items)."""
    if not lore_lines:
        return None
    last = _COLOR_CODE_RE.sub("", lore_lines[-1]).strip()
    m = _RARITY_TAG_RE.search(last)
    if m:
        return m.group(1).replace(" ", "_")
    return None


# ─── Upgrade Chain Lookups ─────────────────────────────────────────────

def _build_chain_index():
    """Build item_id → chain list mapping."""
    index = {}
    for chain in UPGRADE_CHAINS:
        for item_id in chain:
            index[item_id] = chain
    return index

_CHAIN_INDEX = _build_chain_index()


def _build_alias_reverse():
    """Build alias → canonical mapping."""
    reverse = {}
    for canonical, aliases in ACCESSORY_ALIASES.items():
        for alias in aliases:
            reverse[alias] = canonical
    return reverse

_ALIAS_REVERSE = _build_alias_reverse()

# Build set of all alias IDs (these are filtered out of the master list)
_ALL_ALIAS_IDS = set()
for aliases in ACCESSORY_ALIASES.values():
    _ALL_ALIAS_IDS.update(aliases)


def get_canonical_id(item_id):
    """Resolve an item ID to its canonical form (handles aliases)."""
    return _ALIAS_REVERSE.get(item_id, item_id)


def get_chain(item_id):
    """Get the upgrade chain for an item, or None."""
    canonical = get_canonical_id(item_id)
    return _CHAIN_INDEX.get(canonical)


def chain_position(item_id):
    """Return (chain, index) for an item in its upgrade chain, or (None, -1)."""
    canonical = get_canonical_id(item_id)
    chain = _CHAIN_INDEX.get(canonical)
    if chain:
        try:
            return chain, chain.index(canonical)
        except ValueError:
            pass
    return None, -1


# ─── Scan Player Accessories ──────────────────────────────────────────

def scan_player_accessories(member):
    """Scan ALL inventory locations for accessories.

    Returns list of dicts: {id, canonical_id, rarity, recombed, location, lore}
    """
    inv = member.get("inventory", {})
    locations = {
        "accessory_bag": inv.get("bag_contents", {}).get("talisman_bag", {}).get("data", ""),
        "inventory": inv.get("inv_contents", {}).get("data", ""),
        "ender_chest": inv.get("ender_chest_contents", {}).get("data", ""),
        "armor": inv.get("inv_armor", {}).get("data", ""),
        "equipment": inv.get("equipment_contents", {}).get("data", ""),
        "personal_vault": inv.get("personal_vault_contents", {}).get("data", ""),
        "wardrobe": inv.get("wardrobe_contents", {}).get("data", ""),
    }
    # Storage backpacks
    backpacks = inv.get("backpack_contents", {})
    for slot, bp in backpacks.items():
        bp_data = bp.get("data", "") if isinstance(bp, dict) else ""
        if bp_data:
            locations[f"storage_{slot}"] = bp_data

    found = []
    for loc_name, b64_data in locations.items():
        if not b64_data:
            continue
        slots, _ = decode_nbt_inventory_slots(b64_data)
        for item in slots:
            if not item or not item.get("id"):
                continue
            item_id = item["id"]
            # Check if it's an accessory by API category or by being in our chain/alias data
            cat = get_category(item_id)
            canonical = get_canonical_id(item_id)
            is_accessory = (
                cat == "ACCESSORY"
                or canonical in _CHAIN_INDEX
                or item_id in _ALL_ALIAS_IDS
                or item_id in IGNORED_ACCESSORIES
            )
            if not is_accessory:
                continue

            # Determine effective rarity from lore (includes recombobulated)
            lore_rarity = rarity_from_lore(item.get("lore", []))
            base_rarity = get_accessory_rarity(canonical)
            recombed = item.get("rarity_upgrades", 0) > 0

            found.append({
                "id": item_id,
                "canonical_id": canonical,
                "rarity": lore_rarity or base_rarity or "COMMON",
                "base_rarity": base_rarity or "COMMON",
                "recombed": recombed,
                "location": loc_name,
            })

    return found


# ─── Build Master Accessory List ──────────────────────────────────────

def build_master_list():
    """Build the authoritative list of all countable accessories.

    Returns dict of canonical_id → {id, name, rarity, chain, chain_pos, is_max_tier}
    Filters out ignored accessories and alias IDs.
    """
    items = get_items_data()
    master = {}

    for item in items:
        item_id = item.get("id", "")
        if item.get("category") != "ACCESSORY":
            continue
        if item_id in IGNORED_ACCESSORIES:
            continue
        if item_id in _ALL_ALIAS_IDS:
            continue

        rarity = get_accessory_rarity(item_id, item)
        chain = _CHAIN_INDEX.get(item_id)
        chain_pos = -1
        is_max_tier = True
        if chain:
            try:
                chain_pos = chain.index(item_id)
                is_max_tier = (chain_pos == len(chain) - 1)
            except ValueError:
                pass

        master[item_id] = {
            "id": item_id,
            "name": display_name(item_id),
            "rarity": rarity,
            "chain": chain,
            "chain_pos": chain_pos,
            "is_max_tier": is_max_tier,
        }

    return master


# ─── Analyze Accessories ──────────────────────────────────────────────

def analyze_accessories(player_accs, master_list):
    """Analyze player's accessories against master list.

    Returns:
        active: list of active accessory dicts (contributing MP)
        inactive: list of {acc, reason} dicts
        owned_canonical: set of canonical IDs the player owns
        recombed_count: number of recombobulated active accessories
        recombable_count: number of active accessories that allow recombobulation
    """
    # Group player accessories by canonical ID
    by_canonical = {}
    for acc in player_accs:
        cid = acc["canonical_id"]
        if cid not in by_canonical:
            by_canonical[cid] = []
        by_canonical[cid].append(acc)

    active = []
    inactive = []
    owned_canonical = set(by_canonical.keys())

    # For each canonical ID the player has, determine which copy is active
    for cid, copies in by_canonical.items():
        chain = get_chain(cid)

        if chain:
            # Check if a higher-tier version exists in the player's collection
            try:
                my_pos = chain.index(cid)
            except ValueError:
                my_pos = -1

            higher_owned = False
            for higher_id in chain[my_pos + 1:]:
                if higher_id in by_canonical:
                    higher_owned = True
                    break

            if higher_owned:
                # All copies of this lower tier are inactive
                higher_id_found = None
                for hid in chain[my_pos + 1:]:
                    if hid in by_canonical:
                        higher_id_found = hid
                        break
                for copy in copies:
                    inactive.append({
                        "acc": copy,
                        "reason": f"Have {display_name(higher_id_found)} (higher tier)",
                    })
                continue

        # First copy is active, rest are duplicates
        # Pick the recombed copy as active if available
        copies_sorted = sorted(copies, key=lambda c: (c["recombed"], 0), reverse=True)
        active.append(copies_sorted[0])
        for dup in copies_sorted[1:]:
            inactive.append({
                "acc": dup,
                "reason": "Duplicate",
            })

    # Count recombobulated and recombable
    recombed_count = sum(1 for a in active if a["recombed"])
    recombable_count = 0
    for a in active:
        cid = a["canonical_id"]
        if cid in SPECIAL_ACCESSORIES:
            if SPECIAL_ACCESSORIES[cid].get("allows_recomb") is False:
                continue
        recombable_count += 1

    return active, inactive, owned_canonical, recombed_count, recombable_count


def calculate_mp(active_accessories):
    """Calculate total Magical Power from active accessories."""
    total_mp = 0
    for acc in active_accessories:
        rarity = acc["rarity"]
        mp = MP_PER_RARITY.get(rarity, 0)

        # Hegemony Artifact doubles its own MP
        if acc["canonical_id"] == "HEGEMONY_ARTIFACT":
            mp *= 2

        total_mp += mp
    return total_mp


def calculate_recomb_potential(active_accessories):
    """Calculate how much extra MP could be gained from recombobulating remaining accessories."""
    # Rarity upgrade order
    rarity_upgrade = {
        "COMMON": "UNCOMMON",
        "UNCOMMON": "RARE",
        "RARE": "EPIC",
        "EPIC": "LEGENDARY",
        "LEGENDARY": "MYTHIC",
    }

    extra_mp = 0
    count_unrecomed = 0
    for acc in active_accessories:
        if acc["recombed"]:
            continue
        cid = acc["canonical_id"]
        if cid in SPECIAL_ACCESSORIES:
            if SPECIAL_ACCESSORIES[cid].get("allows_recomb") is False:
                continue
        base_rarity = acc["base_rarity"]
        upgraded = rarity_upgrade.get(base_rarity)
        if upgraded:
            base_mp = MP_PER_RARITY.get(base_rarity, 0)
            new_mp = MP_PER_RARITY.get(upgraded, 0)
            if cid == "HEGEMONY_ARTIFACT":
                base_mp *= 2
                new_mp *= 2
            extra_mp += (new_mp - base_mp)
            count_unrecomed += 1

    return extra_mp, count_unrecomed


# ─── Find Missing Accessories ─────────────────────────────────────────

def find_missing(master_list, owned_canonical, active_accessories, price_cache, member):
    """Find missing accessories with pricing and MP calculations.

    Returns:
        missing: list of dicts with id, name, rarity, mp_gain, cost, coins_per_mp,
                 source, is_upgrade, upgrade_from, requirements, obtainable
        upgrades: list of upgrade opportunities (have lower tier, can upgrade)
    """
    missing = []
    upgrades = []

    # Build set of active canonical IDs (highest owned tier in each chain)
    active_ids = {a["canonical_id"] for a in active_accessories}

    for item_id, info in master_list.items():
        if item_id in owned_canonical:
            continue

        rarity = info["rarity"]
        mp = MP_PER_RARITY.get(rarity, 0) if rarity else 0
        chain = info["chain"]

        # Determine if this is an upgrade opportunity
        is_upgrade = False
        upgrade_from = None
        mp_gain = mp
        incremental_cost = None

        if chain:
            # Only suggest the next upgrade in the chain, not skipping tiers
            # Also only suggest max-tier or next-tier items
            my_pos = info["chain_pos"]

            # Check if player has any item in this chain
            owned_in_chain = []
            for i, chain_id in enumerate(chain):
                if chain_id in owned_canonical:
                    owned_in_chain.append((i, chain_id))

            if owned_in_chain:
                highest_owned_pos, highest_owned_id = max(owned_in_chain, key=lambda x: x[0])
                if my_pos <= highest_owned_pos:
                    # Player already has this or a higher tier — skip
                    continue

                # This is an upgrade from what they have
                is_upgrade = True
                upgrade_from = highest_owned_id
                owned_rarity = master_list.get(highest_owned_id, {}).get("rarity")
                owned_mp = MP_PER_RARITY.get(owned_rarity, 0) if owned_rarity else 0
                mp_gain = mp - owned_mp

                # If they don't have the tier immediately below, skip
                # (suggest the next step up, not skipping)
                if my_pos > highest_owned_pos + 1:
                    # Only show the next tier up, not ones further away
                    next_tier_id = chain[highest_owned_pos + 1]
                    if next_tier_id != item_id:
                        continue
            else:
                # Nobody in chain owned — only suggest the lowest tier
                if my_pos > 0:
                    continue

        if mp_gain == 0 and not is_upgrade:
            continue  # Skip items with no MP value

        # Get price
        cost = _get_accessory_price(item_id, price_cache)

        # Calculate incremental cost for upgrades (new price - value of current)
        if is_upgrade and upgrade_from and cost is not None:
            current_value = _get_accessory_price(upgrade_from, price_cache)
            if current_value is not None:
                incremental_cost = max(0, cost - current_value)

        # Coins per MP
        effective_cost = incremental_cost if incremental_cost is not None else cost
        coins_per_mp = None
        if effective_cost is not None and mp_gain > 0:
            coins_per_mp = effective_cost / mp_gain

        # Source classification
        source = _classify_source(item_id, cost)

        # Check requirements
        reqs = get_all_requirements(item_id)
        req_check = check_requirements(item_id, member) if reqs else []
        all_met = all(r.get("met", False) for r in req_check) if req_check else True
        obtainable = source != "unobtainable"

        entry = {
            "id": item_id,
            "name": info["name"],
            "rarity": rarity,
            "mp_gain": mp_gain,
            "cost": cost,
            "incremental_cost": incremental_cost,
            "coins_per_mp": coins_per_mp,
            "source": source,
            "is_upgrade": is_upgrade,
            "upgrade_from": upgrade_from,
            "requirements": req_check,
            "requirements_met": all_met,
            "obtainable": obtainable,
        }

        if is_upgrade:
            upgrades.append(entry)

        missing.append(entry)

    return missing, upgrades


def _get_accessory_price(item_id, price_cache):
    """Get price for an accessory: AH LBIN, then craft cost."""
    price = price_cache.weighted(item_id)
    if price is not None and price > 0:
        return price

    # Try craft cost
    recipe = find_recipe(item_id)
    if recipe:
        cost = calculate_craft_cost(recipe, price_cache)
        if cost is not None and cost > 0:
            return cost

    return None


def _classify_source(item_id, cost):
    """Classify how an accessory is obtained."""
    if cost is not None and cost > 0:
        return "AH"  # Available on market or craftable

    # Check if it has a recipe
    recipe = find_recipe(item_id)
    if recipe:
        return "craft"

    # Check if it has requirements that suggest quest/progression
    reqs = get_all_requirements(item_id)
    if reqs:
        return "progression"

    return "unobtainable"


# ─── Budget Parsing ───────────────────────────────────────────────────

def parse_budget(budget_str):
    """Parse budget string like '10m', '500k', '1.5b' into a number."""
    if not budget_str:
        return None
    budget_str = budget_str.strip().lower()
    multipliers = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
    for suffix, mult in multipliers.items():
        if budget_str.endswith(suffix):
            try:
                return float(budget_str[:-1]) * mult
            except ValueError:
                return None
    try:
        return float(budget_str)
    except ValueError:
        return None


# ─── Output Formatting ────────────────────────────────────────────────

_RARITY_SHORT = {
    "COMMON": "Common",
    "UNCOMMON": "Uncommon",
    "RARE": "Rare",
    "EPIC": "Epic",
    "LEGENDARY": "Legendary",
    "MYTHIC": "Mythic",
    "SPECIAL": "Special",
    "VERY_SPECIAL": "Very Special",
    "SUPREME": "Supreme",
}


def print_report(active, inactive, missing, upgrades, owned_canonical,
                 master_list, recombed_count, recombable_count, member,
                 budget=None, sort_key="coins_per_mp", upgrades_only=False,
                 inactive_only=False, available_only=False):
    """Print the full missing accessories report."""
    total_mp = calculate_mp(active)
    recomb_mp, recomb_remaining = calculate_recomb_potential(active)

    # Count max accessories (only max tier in each chain)
    max_tier_count = sum(1 for v in master_list.values() if v["is_max_tier"])

    # Player name
    player = ""
    try:
        data = json.loads(LAST_PROFILE_PATH.read_text())
        player = data.get("player", data.get("uuid", ""))
    except Exception:
        pass

    # Header
    print(f"{'═' * 70}")
    print(f"  MISSING ACCESSORIES — {player}")
    print(f"  Active: {len(active)} owned ({total_mp} MP)")
    print(f"  Inactive: {len(inactive)} (duplicates or lower-tier)")
    print(f"  Recombobulated: {recombed_count}/{recombable_count}"
          f" (could gain +{recomb_mp} MP from recombs)")
    print(f"{'═' * 70}")

    if inactive_only:
        _print_inactive(inactive)
        return

    # Filter and sort missing list
    show_missing = list(missing)
    if upgrades_only:
        show_missing = [m for m in show_missing if m["is_upgrade"]]
    if available_only:
        show_missing = [m for m in show_missing if m["obtainable"] and m["cost"] is not None]

    # Sort
    if sort_key == "cost":
        show_missing.sort(key=lambda m: (m["cost"] if m["cost"] is not None else float("inf")))
    else:  # coins_per_mp
        show_missing.sort(key=lambda m: (
            m["coins_per_mp"] if m["coins_per_mp"] is not None else float("inf")
        ))

    # Apply budget filter
    if budget is not None:
        budget_remaining = budget
        budget_missing = []
        for m in show_missing:
            effective_cost = m["incremental_cost"] if m["incremental_cost"] is not None else m["cost"]
            if effective_cost is not None and effective_cost <= budget_remaining:
                budget_missing.append(m)
                budget_remaining -= effective_cost
        show_missing = budget_missing

    # Print ranked missing list
    available = [m for m in show_missing if m["cost"] is not None and m["obtainable"]
                 and m.get("requirements_met", True)]
    locked = [m for m in show_missing if m["obtainable"]
              and m.get("requirements") and not m["requirements_met"]]
    unobtainable = [m for m in missing if not m["obtainable"]]

    if available:
        print(f"\n  Best Upgrades by {'Cost' if sort_key == 'cost' else 'Coins/MP'}:")
        print(f"    {'#':>3s}   {'Accessory':<28s} {'Rarity':<12s} {'MP':>4s}"
              f"    {'Cost':>10s}   {'Coins/MP':>10s}   Source")
        print(f"    {'─' * 3}   {'─' * 28} {'─' * 12} {'─' * 4}"
              f"    {'─' * 10}   {'─' * 10}   {'─' * 12}")

        for i, m in enumerate(available[:30], 1):
            name = m["name"]
            if len(name) > 28:
                name = name[:25] + "..."
            rarity_str = _RARITY_SHORT.get(m["rarity"], m["rarity"] or "?")
            mp_str = f"+{m['mp_gain']}"

            effective_cost = m["incremental_cost"] if m["incremental_cost"] is not None else m["cost"]
            cost_str = _fmt(effective_cost) if effective_cost is not None else "?"
            cpm_str = _fmt(m["coins_per_mp"]) if m["coins_per_mp"] is not None else "?"

            source = m["source"]
            upgrade_tag = " (upgrade)" if m["is_upgrade"] else ""

            print(f"    {i:>3d}.  {name:<28s} {rarity_str:<12s} {mp_str:>4s}"
                  f"    {cost_str:>10s}   {cpm_str:>10s}   {source}{upgrade_tag}")

            if m["is_upgrade"] and m["upgrade_from"]:
                from_name = display_name(m["upgrade_from"])
                from_rarity = master_list.get(m["upgrade_from"], {}).get("rarity", "")
                from_rarity_str = _RARITY_SHORT.get(from_rarity, from_rarity or "?")
                print(f"          └─ You have: {from_name} [{from_rarity_str}]")

        if len(available) > 30:
            print(f"\n    ... and {len(available) - 30} more (use --json for full list)")

    # Inactive section
    if inactive and not upgrades_only:
        _print_inactive(inactive)

    # Locked behind progression
    if locked and not upgrades_only:
        print(f"\n  Locked Behind Progression:")
        print(f"    {'Accessory':<28s} {'Requirement':<28s} {'MP':>4s}    {'Cost':>10s}")
        print(f"    {'─' * 28} {'─' * 28} {'─' * 4}    {'─' * 10}")
        for m in locked[:15]:
            name = m["name"]
            if len(name) > 28:
                name = name[:25] + "..."
            mp_str = f"+{m['mp_gain']}"
            cost_str = _fmt(m["cost"]) if m["cost"] is not None else "?"
            # Show first unmet requirement
            unmet = [r for r in m.get("requirements", []) if not r.get("met", True)]
            if unmet:
                req_text = unmet[0].get("text", "Unknown")
                met_marker = "✗" if not unmet[0].get("met", True) else "✓"
                req_display = f"{req_text} ({met_marker})"
            else:
                req_display = "Unknown requirement"
            if len(req_display) > 28:
                req_display = req_display[:25] + "..."
            print(f"    {name:<28s} {req_display:<28s} {mp_str:>4s}    {cost_str:>10s}")

    # Unobtainable
    if unobtainable and not upgrades_only and not available_only:
        print(f"\n  Unobtainable / Event-Only:")
        for m in unobtainable[:10]:
            print(f"    - {m['name']}")
        if len(unobtainable) > 10:
            print(f"    ... and {len(unobtainable) - 10} more")

    # Summary
    all_available = [m for m in missing if m["cost"] is not None and m["obtainable"]]
    total_missing_mp = sum(m["mp_gain"] for m in missing if m["obtainable"])
    print(f"\n  Summary:")
    print(f"    Missing accessories:           {len(missing)}")
    print(f"    Available now (priced):         {len(all_available)}")
    print(f"    Total MP if all obtained:      +{total_missing_mp} MP (→ {total_mp + total_missing_mp} MP)")

    if all_available:
        # Find cheapest 50 MP
        sorted_by_cpm = sorted(all_available,
                                key=lambda m: m["coins_per_mp"] if m["coins_per_mp"] is not None else float("inf"))
        mp_so_far = 0
        cost_so_far = 0
        count_so_far = 0
        for m in sorted_by_cpm:
            if mp_so_far >= 50:
                break
            ec = m["incremental_cost"] if m["incremental_cost"] is not None else m["cost"]
            if ec is None:
                continue
            mp_so_far += m["mp_gain"]
            cost_so_far += ec
            count_so_far += 1
        if mp_so_far > 0:
            print(f"    Cheapest {mp_so_far} MP:              ~{_fmt(cost_so_far)} ({count_so_far} accessories)")

    if recomb_remaining > 0:
        recomb_price = price_cache_ref.weighted("RECOMBOBULATOR_3000")
        if recomb_price:
            total_recomb = recomb_price * recomb_remaining
            print(f"    Full recomb potential:          +{recomb_mp} MP"
                  f" ({recomb_remaining} remaining × ~{_fmt(recomb_price)} each"
                  f" = ~{_fmt(total_recomb)})")


def _print_inactive(inactive):
    """Print inactive accessories section."""
    if not inactive:
        return
    print(f"\n  Inactive Accessories (wasted bag slots):")
    print(f"    {'Accessory':<32s} {'Reason'}")
    print(f"    {'─' * 32} {'─' * 35}")

    # Group duplicates
    seen = {}
    for entry in inactive:
        name = display_name(entry["acc"]["canonical_id"])
        reason = entry["reason"]
        key = (name, reason)
        seen[key] = seen.get(key, 0) + 1

    for (name, reason), count in sorted(seen.items()):
        count_str = f" (×{count})" if count > 1 else ""
        if len(name) > 32:
            name = name[:29] + "..."
        print(f"    {name}{count_str:<{32 - len(name)}s} {reason}")


# ─── JSON Output ──────────────────────────────────────────────────────

def json_output(active, inactive, missing, upgrades, owned_canonical,
                master_list, recombed_count, recombable_count, total_mp):
    """Output machine-readable JSON."""
    recomb_mp, recomb_remaining = calculate_recomb_potential(active)
    result = {
        "summary": {
            "active_count": len(active),
            "inactive_count": len(inactive),
            "total_mp": total_mp,
            "recombed": recombed_count,
            "recombable": recombable_count,
            "recomb_potential_mp": recomb_mp,
            "recomb_remaining": recomb_remaining,
            "missing_count": len(missing),
        },
        "active": [{
            "id": a["canonical_id"],
            "rarity": a["rarity"],
            "recombed": a["recombed"],
            "mp": MP_PER_RARITY.get(a["rarity"], 0),
            "location": a["location"],
        } for a in active],
        "inactive": [{
            "id": e["acc"]["canonical_id"],
            "rarity": e["acc"]["rarity"],
            "reason": e["reason"],
            "location": e["acc"]["location"],
        } for e in inactive],
        "missing": [{
            "id": m["id"],
            "name": m["name"],
            "rarity": m["rarity"],
            "mp_gain": m["mp_gain"],
            "cost": m["cost"],
            "incremental_cost": m["incremental_cost"],
            "coins_per_mp": m["coins_per_mp"],
            "source": m["source"],
            "is_upgrade": m["is_upgrade"],
            "upgrade_from": m["upgrade_from"],
            "requirements_met": m["requirements_met"],
            "obtainable": m["obtainable"],
        } for m in missing],
    }
    print(json.dumps(result, indent=2))


# Module-level ref for recomb pricing in print_report
price_cache_ref = None


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    global price_cache_ref

    parser = argparse.ArgumentParser(
        description="Find missing accessories and rank by cost-efficiency."
    )
    parser.add_argument("--budget", type=str, default=None,
                        help="Max total budget (e.g., 10m, 500k, 1.5b)")
    parser.add_argument("--sort", choices=["coins_per_mp", "cost"], default="coins_per_mp",
                        help="Sort order (default: coins_per_mp)")
    parser.add_argument("--upgrades-only", action="store_true",
                        help="Only show upgrade opportunities (have lower tier)")
    parser.add_argument("--inactive", action="store_true",
                        help="Focus on inactive/duplicate cleanup")
    parser.add_argument("--available-only", action="store_true",
                        help="Hide locked/unobtainable accessories")
    parser.add_argument("--json", action="store_true",
                        help="Machine-readable JSON output")
    args = parser.parse_args()

    budget = parse_budget(args.budget) if args.budget else None

    # Status messages go to stderr so --json output is clean
    def status(msg):
        print(msg, file=sys.stderr)

    # Load profile
    member, profile, data = load_profile()

    # Initialize pricing
    price_cache = PriceCache()
    price_cache_ref = price_cache

    status("Loading accessory data...")

    # Build master list from Hypixel items API
    master_list = build_master_list()
    status(f"  {len(master_list)} accessories in master list")

    # Scan player's accessories from all locations
    player_accs = scan_player_accessories(member)
    status(f"  {len(player_accs)} accessories found in player inventory")

    # Analyze active/inactive
    active, inactive, owned_canonical, recombed_count, recombable_count = \
        analyze_accessories(player_accs, master_list)
    total_mp = calculate_mp(active)
    status(f"  {len(active)} active, {len(inactive)} inactive, {total_mp} MP")

    # Fetch prices for all accessories (bulk)
    all_ids = list(master_list.keys())
    status("Fetching prices...")
    price_cache.get_prices_bulk(all_ids)

    # Find missing accessories
    missing, upgrades = find_missing(master_list, owned_canonical, active,
                                     price_cache, member)
    status(f"  {len(missing)} missing accessories found\n")

    # Output
    if args.json:
        json_output(active, inactive, missing, upgrades, owned_canonical,
                    master_list, recombed_count, recombable_count, total_mp)
    else:
        print_report(active, inactive, missing, upgrades, owned_canonical,
                     master_list, recombed_count, recombable_count, member,
                     budget=budget, sort_key=args.sort,
                     upgrades_only=args.upgrades_only,
                     inactive_only=args.inactive,
                     available_only=args.available_only)

    price_cache.flush()


if __name__ == "__main__":
    main()
