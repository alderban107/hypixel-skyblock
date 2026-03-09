#!/usr/bin/env python3
"""SkyBlock XP recommendation engine — analyze SBXP sources and suggest next gains.

Reads cached profile data from data/last_profile.json and cross-references with
the SBXP task database (data/sbxp_tasks.json) to show:
  - Current SBXP breakdown by source
  - XP needed for next SB level
  - Recommended tasks sorted by effort/XP ratio
  - Unclaimed formula-based gains

Run profile.py first to refresh data, then:
    python3 sbxp.py               # full analysis
    python3 sbxp.py --brief       # just recommendations
    python3 sbxp.py --category mining  # filter recommendations by category
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

DATA_DIR = Path(__file__).parent.parent / "data"
PROFILE_PATH = DATA_DIR / "last_profile.json"
TASKS_PATH = DATA_DIR / "sbxp_tasks.json"

# ─── Skill XP tables (same as profile.py, duplicated for standalone use) ───

SKILL_XP_THRESHOLDS = [
    0, 50, 175, 375, 675, 1175, 1925, 2925, 4425, 6425, 9925,
    14925, 22425, 32425, 47425, 67425, 97425, 147425, 222425, 322425, 522425,
    822425, 1222425, 1722425, 2322425, 3022425, 3822425, 4722425, 5722425, 6822425, 8022425,
    9322425, 10722425, 12222425, 13822425, 15522425, 17322425, 19222425, 21222425, 23322425, 25522425,
    27822425, 30222425, 32722425, 35322425, 38072425, 40972425, 44072425, 47472425, 51172425, 55172425,
    59472425, 64072425, 68972425, 74172425, 79672425, 85472425, 91572425, 97972425, 104672425, 111672425,
]
RUNECRAFTING_XP_THRESHOLDS = [
    0, 50, 150, 275, 435, 635, 885, 1200, 1600, 2100, 2725,
    3510, 4510, 5760, 7325, 9325, 11825, 14950, 18950, 23950, 30200,
    38050, 47850, 60100, 75400, 94450,
]
SKILL_MAX_LEVELS = {
    "farming": 60, "mining": 60, "combat": 60, "foraging": 54,
    "fishing": 50, "enchanting": 60, "alchemy": 50, "taming": 60,
    "carpentry": 50, "social": 25, "runecrafting": 25, "hunting": 25,
}
# All 13 skills that count for SBXP (not just skill average)
ALL_SKILLS = [
    "farming", "mining", "combat", "foraging", "fishing",
    "enchanting", "alchemy", "taming", "carpentry",
    "runecrafting", "social", "hunting",
]

DUNGEON_XP_THRESHOLDS = [
    0, 50, 125, 235, 395, 625, 955, 1425, 2095, 3045, 4385,
    6275, 8940, 12700, 17960, 25340, 35640, 50040, 70040, 97640, 135640,
    188140, 259640, 356640, 488640, 668640, 911640, 1239640, 1684640, 2284640, 3084640,
    4149640, 5559640, 7459640, 9959640, 13259640, 17559640, 23159640, 30359640, 39559640, 51559640,
    66559640, 85559640, 109559640, 139559640, 177559640, 225559640, 285559640, 360559640, 453559640, 569809640,
]

SLAYER_XP_THRESHOLDS = {
    "zombie":   [0, 5, 15, 200, 1000, 5000, 20000, 100000, 400000, 1000000],
    "spider":   [0, 5, 25, 200, 1000, 5000, 20000, 100000, 400000, 1000000],
    "wolf":     [0, 10, 30, 250, 1500, 5000, 20000, 100000, 400000, 1000000],
    "enderman": [0, 10, 30, 250, 1500, 5000, 20000, 100000, 400000, 1000000],
    "blaze":    [0, 10, 30, 250, 1500, 5000, 20000, 100000, 400000, 1000000],
    "vampire":  [0, 20, 75, 240, 840, 2400],
}

HOTM_XP_THRESHOLDS = [0, 3_000, 12_000, 37_000, 97_000, 197_000, 347_000, 557_000, 847_000, 1_247_000]

# SBXP per HotM tier
HOTM_TIER_XP = [35, 45, 60, 75, 90, 110, 130, 180, 210, 240]
# SBXP per PotM tier
POTM_TIER_XP = [25, 35, 50, 65, 75, 100, 125, 150, 175, 200]
# SBXP per slayer level
SLAYER_LEVEL_XP = [15, 25, 35, 50, 70, 100, 125, 150, 150]
# SBXP per commission milestone tier
COMMISSION_TIER_XP = [20, 30, 30, 50, 50, 75]
# SBXP per minion tier
MINION_TIER_XP = {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 2, 8: 3, 9: 4, 10: 6, 11: 12, 12: 24}

# Effort ordering for sorting (lower = easier)
EFFORT_ORDER = {"free": 0, "easy": 1, "medium": 2, "hard": 3, "extreme": 4}


def _fmt(n):
    """Format a number with commas."""
    if isinstance(n, float):
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 10_000:
            return f"{n / 1_000:.1f}K"
        return f"{n:,.1f}"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 10_000:
        return f"{n / 1_000:.1f}K"
    return f"{n:,}"


def xp_to_level(xp, thresholds, max_level=None):
    """Convert XP to level using cumulative thresholds."""
    level = 0
    for i, threshold in enumerate(thresholds):
        if xp >= threshold:
            level = i
        else:
            break
    if max_level:
        level = min(level, max_level)
    return level


# ─── Formula-based SBXP calculators ───

def calc_skill_sbxp(member):
    """Calculate SBXP from all skill levels.

    Returns (current_xp, max_xp, details) where details is a list of
    (skill_name, level, max_level, sbxp_from_this_skill).
    """
    skills_xp = member.get("player_data", {}).get("experience", {})
    total_sbxp = 0
    details = []

    for skill in ALL_SKILLS:
        raw_xp = skills_xp.get(f"SKILL_{skill.upper()}", 0)
        max_lvl = SKILL_MAX_LEVELS.get(skill, 50)
        if skill in ("runecrafting", "social"):
            thresholds = RUNECRAFTING_XP_THRESHOLDS
        else:
            thresholds = SKILL_XP_THRESHOLDS
        level = xp_to_level(raw_xp, thresholds, max_lvl)

        # Calculate SBXP for this skill
        sbxp = 0
        for lvl in range(1, level + 1):
            if lvl <= 10:
                sbxp += 5
            elif lvl <= 25:
                sbxp += 10
            elif lvl <= 50:
                sbxp += 20
            else:
                sbxp += 30

        total_sbxp += sbxp
        details.append((skill, level, max_lvl, sbxp))

    return total_sbxp, 7800, details


def calc_fairy_souls_sbxp(member):
    """Calculate SBXP from fairy soul exchanges."""
    fairy = member.get("fairy_soul", {})
    exchanges = fairy.get("fairy_exchanges", 0)
    collected = fairy.get("total_collected", 0)
    # Each exchange is 5 souls, gives +10 SBXP
    sbxp = exchanges * 10
    return sbxp, 490, {"collected": collected, "exchanges": exchanges, "max_exchanges": 49}


def calc_mp_sbxp(member):
    """Calculate SBXP from Magical Power."""
    mp = member.get("accessory_bag_storage", {}).get("highest_magical_power", 0)
    return mp, None, {"mp": mp}


def calc_pet_score_sbxp(member):
    """Calculate SBXP from pet score."""
    score = member.get("leveling", {}).get("highest_pet_score", 0)
    sbxp = score * 3
    return sbxp, None, {"score": score}


def calc_collections_sbxp(member):
    """Calculate SBXP from collection milestones.

    Fetches tier thresholds from API and counts how many milestones are reached.
    """
    collections = member.get("collection", {})
    if not collections:
        return 0, 2728, {"milestones": 0, "note": "no collection data"}

    # Fetch collection tier data from API
    try:
        req = Request("https://api.hypixel.net/v2/resources/skyblock/collections")
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        if not data.get("success"):
            raise ValueError("API failed")
    except Exception as e:
        return 0, 2728, {"milestones": 0, "error": str(e)}

    total_milestones = 0
    total_possible = 0
    for category_data in data.get("collections", {}).values():
        for item_id, item_data in category_data.get("items", {}).items():
            tiers = item_data.get("tiers", [])
            total_possible += len(tiers)
            count = collections.get(item_id, 0)
            for tier in tiers:
                if count >= tier["amountRequired"]:
                    total_milestones += 1

    sbxp = total_milestones * 4
    return sbxp, 2728, {"milestones": total_milestones, "possible": total_possible}


def calc_minions_sbxp(member):
    """Calculate SBXP from crafted minion tiers."""
    crafted = member.get("player_data", {}).get("crafted_generators",
              member.get("crafted_generators", []))
    total_sbxp = 0
    for entry in crafted:
        parts = entry.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            tier = int(parts[1])
            total_sbxp += MINION_TIER_XP.get(tier, 0)

    return total_sbxp, 2834, {"unique_crafts": len(crafted)}


def calc_catacombs_sbxp(member):
    """Calculate SBXP from catacombs level."""
    cata_xp = member.get("dungeons", {}).get("dungeon_types", {}).get(
        "catacombs", {}).get("experience", 0)
    level = xp_to_level(cata_xp, DUNGEON_XP_THRESHOLDS, 50)

    sbxp = 0
    for lvl in range(1, level + 1):
        if lvl <= 39:
            sbxp += 20
        else:
            sbxp += 40

    return sbxp, 1220, {"level": level, "xp": cata_xp}


def calc_class_levels_sbxp(member):
    """Calculate SBXP from dungeon class levels."""
    classes = member.get("dungeons", {}).get("player_classes", {})
    total_sbxp = 0
    details = []
    for cls_name in ["healer", "mage", "berserk", "archer", "tank"]:
        cls_xp = classes.get(cls_name, {}).get("experience", 0)
        level = xp_to_level(cls_xp, DUNGEON_XP_THRESHOLDS, 50)
        sbxp = level * 4
        total_sbxp += sbxp
        details.append((cls_name, level, sbxp))

    return total_sbxp, 1000, details


def calc_slayer_levels_sbxp(member):
    """Calculate SBXP from slayer levels."""
    slayer_data = member.get("slayer", {}).get("slayer_bosses",
                  member.get("slayer_bosses", {}))
    total_sbxp = 0
    details = []
    for slayer_name in ["zombie", "spider", "wolf", "enderman", "blaze", "vampire"]:
        xp = slayer_data.get(slayer_name, {}).get("xp", 0)
        thresholds = SLAYER_XP_THRESHOLDS.get(slayer_name, [])
        level = xp_to_level(xp, thresholds)

        sbxp = 0
        for lvl_idx in range(level):
            if lvl_idx < len(SLAYER_LEVEL_XP):
                sbxp += SLAYER_LEVEL_XP[lvl_idx]
        total_sbxp += sbxp
        details.append((slayer_name, level, sbxp))

    return total_sbxp, 3825, details


def calc_bestiary_sbxp(member):
    """Calculate SBXP from bestiary progress.

    Uses last_claimed_milestone as the bestiary tier count.
    Each tier: +1 XP. Every 10 milestones: +10 bonus.
    """
    bestiary = member.get("bestiary", {})
    milestone = bestiary.get("milestone", {}).get("last_claimed_milestone", 0)

    # Each tier gives +1, every 10 milestones gives +10 bonus
    sbxp = milestone + (milestone // 10) * 10
    return sbxp, 3770, {"milestones": milestone}


def calc_hotm_sbxp(member):
    """Calculate SBXP from HotM tiers (not including powder or PotM)."""
    hotm_xp = member.get("skill_tree", {}).get("experience", {}).get("mining", 0)

    # Calculate HotM level
    level = 1
    for i, threshold in enumerate(HOTM_XP_THRESHOLDS):
        if i + 1 > 10:
            break
        if hotm_xp >= threshold:
            level = i + 1

    sbxp = sum(HOTM_TIER_XP[:level])
    return sbxp, sum(HOTM_TIER_XP), {"level": level, "xp": hotm_xp}


def calc_powder_sbxp(member):
    """Calculate SBXP from powder (mithril, gemstone, glacite).

    Linear portion: mithril per 2400 up to 600K, gem/glacite per 2500 up to 600K.
    Above 600K: exponentially decreasing XP.
    """
    mc = member.get("mining_core", {})

    def powder_xp(available, spent, divisor, linear_cap, exp_cap):
        total = available + spent
        # Linear portion
        linear_xp = min(total, linear_cap) // divisor
        # Exponential decay portion (rough approximation)
        if total > linear_cap:
            excess = min(total, exp_cap) - linear_cap
            # The formula gives decreasing returns — approximate as sqrt-based
            # Based on wiki: "exponentially decreasing amount"
            # Rough model: additional XP ≈ linear_cap/divisor * (1 - e^(-excess/linear_cap))
            max_bonus = linear_cap // divisor  # roughly doubles at most
            decay_xp = int(max_bonus * (1 - (1 / (1 + excess / linear_cap))))
            linear_xp += decay_xp
        return linear_xp, total

    mithril_xp, mithril_total = powder_xp(
        mc.get("powder_mithril", 0), mc.get("powder_spent_mithril", 0),
        2400, 600_000, 12_500_000)
    gem_xp, gem_total = powder_xp(
        mc.get("powder_gemstone", 0), mc.get("powder_spent_gemstone", 0),
        2500, 600_000, 20_000_000)
    glacite_xp, glacite_total = powder_xp(
        mc.get("powder_glacite", 0), mc.get("powder_spent_glacite", 0),
        2500, 600_000, 20_000_000)

    total_sbxp = mithril_xp + gem_xp + glacite_xp
    return total_sbxp, 1942, {
        "mithril": {"total": mithril_total, "sbxp": mithril_xp},
        "gemstone": {"total": gem_total, "sbxp": gem_xp},
        "glacite": {"total": glacite_total, "sbxp": glacite_xp},
    }


def calc_potm_sbxp(member):
    """Calculate SBXP from Peak of the Mountain."""
    level = member.get("skill_tree", {}).get("nodes", {}).get(
        "mining", {}).get("core_of_the_mountain", 0)
    sbxp = sum(POTM_TIER_XP[:level])
    return sbxp, sum(POTM_TIER_XP), {"level": level}


def calc_fast_travels_sbxp(member):
    """Calculate SBXP from fast travel scrolls (counted from completed_tasks)."""
    completed = member.get("leveling", {}).get("completed_tasks", [])
    travel_tasks = [t for t in completed if t.startswith("FAST_TRAVEL_")]
    sbxp = len(travel_tasks) * 15
    return sbxp, 240, {"count": len(travel_tasks), "max": 16}


# ─── Phase 3 formula-based calculators ───

# Garden crop milestone thresholds (amount collected per crop to reach each milestone)
CROP_MILESTONE_THRESHOLDS = [
    100, 150, 250, 500, 1_500, 5_000, 15_000, 50_000, 100_000, 300_000,
    600_000, 1_000_000, 2_000_000, 5_000_000, 10_000_000, 20_000_000,
    35_000_000, 50_000_000, 75_000_000, 100_000_000,
]

# Garden level XP thresholds
GARDEN_LEVEL_THRESHOLDS = [
    0, 70, 100, 140, 240, 600, 1_500, 2_000, 2_500, 3_000,
    10_000, 10_000, 10_000, 10_000, 10_000,
]


def calc_museum_sbxp(data):
    """Calculate SBXP from museum donations.

    Museum XP is complex (per-item values based on rarity). We estimate from
    donated item count since exact per-item XP mapping isn't available.
    The API gives us item count + special count.
    """
    museum = data.get("museum", {}).get("members", {})
    if not museum:
        return 0, 2797, {"items": 0, "special": 0, "note": "no museum data"}

    # Get the first (only) member's museum data
    member_museum = list(museum.values())[0] if museum else {}
    items = member_museum.get("items", {})
    special = member_museum.get("special", [])
    item_count = len(items)
    special_count = len(special) if isinstance(special, list) else len(special) if isinstance(special, dict) else 0

    # Rough estimate: average ~15 XP per normal item, ~25 per special
    # This is approximate — actual values vary by item rarity
    estimated_xp = item_count * 15 + special_count * 25
    # Cap at max
    estimated_xp = min(estimated_xp, 2797)

    return estimated_xp, 2797, {
        "items": item_count, "special": special_count,
        "note": "estimated from item count (actual varies by item rarity)",
    }


def calc_garden_level_sbxp(data):
    """Calculate SBXP from garden level. +10 per level, max 14."""
    garden = data.get("garden", {}).get("garden", {})
    garden_xp = garden.get("garden_experience", 0)

    # Calculate garden level from XP thresholds
    level = 0
    cumulative = 0
    for i, threshold in enumerate(GARDEN_LEVEL_THRESHOLDS):
        cumulative += threshold
        if garden_xp >= cumulative:
            level = i + 1
        else:
            break

    sbxp = level * 10
    return sbxp, 140, {"level": level, "xp": garden_xp}


def calc_garden_visitors_sbxp(data):
    """Calculate SBXP from garden unique visitor milestones. +3 per milestone."""
    garden = data.get("garden", {}).get("garden", {})
    commission = garden.get("commission_data", {})
    unique_npcs = commission.get("unique_npcs_served", 0)

    # Milestones at: 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, ...
    # Actually the milestones are triggered at specific counts
    # Approximate: every 5 unique visitors after the first = 1 milestone
    if unique_npcs == 0:
        milestones = 0
    elif unique_npcs < 5:
        milestones = 1
    else:
        milestones = 1 + (unique_npcs - 1) // 5

    milestones = min(milestones, 32)  # max 32 milestones
    sbxp = milestones * 3
    return sbxp, 96, {"unique_npcs": unique_npcs, "milestones": milestones}


def calc_garden_plots_sbxp(data):
    """Calculate SBXP from unlocked garden plots. +5 per plot, max 24."""
    garden = data.get("garden", {}).get("garden", {})
    plots = garden.get("unlocked_plots_ids", [])
    count = len(plots)
    sbxp = count * 5
    return sbxp, 120, {"plots": count, "max": 24}


def calc_garden_crop_upgrades_sbxp(data):
    """Calculate SBXP from garden crop upgrades. +1 per upgrade."""
    garden = data.get("garden", {}).get("garden", {})
    upgrades = garden.get("crop_upgrade_levels", {})
    total_upgrades = sum(upgrades.values())
    sbxp = total_upgrades
    return sbxp, 90, {"upgrades": dict(upgrades), "total": total_upgrades}


def calc_garden_crop_milestones_sbxp(data):
    """Calculate SBXP from garden crop milestones. +1 per milestone, max 460."""
    garden = data.get("garden", {}).get("garden", {})
    resources = garden.get("resources_collected", {})

    total_milestones = 0
    for crop, amount in resources.items():
        for threshold in CROP_MILESTONE_THRESHOLDS:
            if amount >= threshold:
                total_milestones += 1
            else:
                break

    sbxp = total_milestones
    return sbxp, 460, {"crops_tracked": len(resources), "milestones": total_milestones}


def calc_garden_composter_sbxp(data):
    """Calculate SBXP from garden composter upgrades.

    5 upgrade types × 25 tiers each.
    T1-7: +1, T8-13: +2, T14-19: +3, T20-25: +4.
    """
    garden = data.get("garden", {}).get("garden", {})
    composter = garden.get("composter_data", {})
    upgrades = composter.get("upgrades", {})

    total_sbxp = 0
    for upgrade_name, tier in upgrades.items():
        for t in range(1, int(tier) + 1):
            if t <= 7:
                total_sbxp += 1
            elif t <= 13:
                total_sbxp += 2
            elif t <= 19:
                total_sbxp += 3
            else:
                total_sbxp += 4

    return total_sbxp, 305, {"upgrades": dict(upgrades)}


def calc_nucleus_sbxp(member):
    """Estimate SBXP from crystal nucleus runs.

    Estimated from min crystal placements across the 5 original crystals.
    """
    crystals = member.get("mining_core", {}).get("crystals", {})
    # Original 5 crystals required for nucleus
    original_crystals = ["jade_crystal", "amber_crystal", "amethyst_crystal",
                         "sapphire_crystal", "topaz_crystal"]
    placements = []
    for c in original_crystals:
        data = crystals.get(c, {})
        placed = data.get("total_placed", 0)
        placements.append(placed)

    if not placements or all(p == 0 for p in placements):
        runs = 0
    else:
        runs = min(placements)

    capped = min(runs, 50)
    sbxp = capped * 4
    return sbxp, 200, {"estimated_runs": runs, "capped": capped, "note": "estimated from crystal placements"}


def calc_commission_sbxp(member):
    """Estimate SBXP from commission milestones.

    Commission milestone tier isn't directly in the API. We estimate from HotM
    level since milestones are roughly tied to mining progression.
    Tier 4 unlocks at Dwarven Mines, Tier 6 at Crystal Nucleus.
    """
    # Try to find commission milestone data
    # Some profiles store it; it's not consistently available
    # Fall back to estimation from completed_tasks or HotM level
    hotm_xp = member.get("skill_tree", {}).get("experience", {}).get("mining", 0)
    level = 1
    for i, threshold in enumerate(HOTM_XP_THRESHOLDS):
        if i + 1 > 10:
            break
        if hotm_xp >= threshold:
            level = i + 1

    # Rough estimation: HotM 1-2 → milestone 1, HotM 3 → 2, HotM 4 → 3,
    # HotM 5 → 4, HotM 6 → 5, HotM 7+ → 6
    if level >= 7:
        tier = 6
    elif level >= 6:
        tier = 5
    elif level >= 5:
        tier = 4
    elif level >= 4:
        tier = 3
    elif level >= 3:
        tier = 2
    elif level >= 1:
        tier = 1
    else:
        tier = 0

    sbxp = sum(COMMISSION_TIER_XP[:tier])
    return sbxp, 255, {"estimated_tier": tier, "note": "estimated from HotM level"}


# ─── Main analysis ───

def load_profile():
    """Load cached profile data."""
    if not PROFILE_PATH.exists():
        print(f"Error: {PROFILE_PATH} not found. Run profile.py first.")
        sys.exit(1)
    data = json.loads(PROFILE_PATH.read_text())
    member = data.get("member", {})
    if not member:
        print("Error: No member data in profile.")
        sys.exit(1)
    return data, member


def load_tasks():
    """Load SBXP task database."""
    if not TASKS_PATH.exists():
        print(f"Error: {TASKS_PATH} not found.")
        sys.exit(1)
    return json.loads(TASKS_PATH.read_text())


def analyze_formula_sources(member, data=None):
    """Calculate SBXP from all formula-based sources.

    Returns list of (id, name, category, current_xp, max_xp, details).
    data is the full profile dict (needed for garden/museum which are top-level).
    """
    # Calculators that take `member`
    member_calculators = [
        ("skill_levels",         "Skill Level Up",          "Core",     calc_skill_sbxp),
        ("fairy_souls",          "Fairy Souls",             "Core",     calc_fairy_souls_sbxp),
        ("accessory_bag",        "Magical Power",           "Core",     calc_mp_sbxp),
        ("pet_score",            "Pet Score",               "Core",     calc_pet_score_sbxp),
        ("collections",          "Collections",             "Core",     calc_collections_sbxp),
        ("crafted_minions",      "Crafted Minions",         "Core",     calc_minions_sbxp),
        ("fast_travels",         "Fast Travels",            "Core",     calc_fast_travels_sbxp),
        ("catacombs_level",      "Catacombs Level",         "Dungeons", calc_catacombs_sbxp),
        ("class_levels",         "Class Levels",            "Dungeons", calc_class_levels_sbxp),
        ("slayer_levels",        "Slayer Levels",           "Slaying",  calc_slayer_levels_sbxp),
        ("bestiary",             "Bestiary",                "Slaying",  calc_bestiary_sbxp),
        ("hotm_tiers",           "HotM Tiers",              "Mining",   calc_hotm_sbxp),
        ("powder",               "Powder",                  "Mining",   calc_powder_sbxp),
        ("peak_of_mountain",     "Peak of the Mountain",    "Mining",   calc_potm_sbxp),
        ("nucleus_runs",         "Nucleus Runs",            "Mining",   calc_nucleus_sbxp),
        ("commission_milestones","Commission Milestones",   "Mining",   calc_commission_sbxp),
    ]

    # Calculators that take `data` (full profile dict for top-level fields)
    data_calculators = [
        ("museum",               "Museum Progression",      "Core",     calc_museum_sbxp),
        ("garden_level",         "Garden Level",            "Farming",  calc_garden_level_sbxp),
        ("garden_visitors",      "Garden Visitors",         "Farming",  calc_garden_visitors_sbxp),
        ("garden_plots",         "Garden Plots",            "Farming",  calc_garden_plots_sbxp),
        ("garden_crop_upgrades", "Garden Crop Upgrades",    "Farming",  calc_garden_crop_upgrades_sbxp),
        ("garden_crop_milestones","Garden Crop Milestones", "Farming",  calc_garden_crop_milestones_sbxp),
        ("garden_composter",     "Garden Composter",        "Farming",  calc_garden_composter_sbxp),
    ]

    results = []
    for src_id, name, category, calc_fn in member_calculators:
        current, max_xp, details = calc_fn(member)
        results.append({
            "id": src_id, "name": name, "category": category,
            "current": current, "max": max_xp, "details": details,
        })

    if data:
        for src_id, name, category, calc_fn in data_calculators:
            current, max_xp, details = calc_fn(data)
            results.append({
                "id": src_id, "name": name, "category": category,
                "current": current, "max": max_xp, "details": details,
            })

    return results


def analyze_individual_tasks(member, tasks_db):
    """Cross-reference completed_tasks with task database.

    Returns (completed, available) where each is a list of task dicts
    with added 'completed' field.
    """
    completed_set = set(member.get("leveling", {}).get("completed_tasks", []))
    individual = tasks_db.get("individual_tasks", [])

    completed = []
    available = []
    for task in individual:
        task_copy = dict(task)
        if task["id"] in completed_set:
            task_copy["completed"] = True
            completed.append(task_copy)
        else:
            task_copy["completed"] = False
            available.append(task_copy)

    return completed, available


def print_header(title):
    """Print a section header."""
    print(f"\n{'=' * 68}")
    print(f"  {title}")
    print(f"{'=' * 68}")


def print_summary(member, formula_results, completed_tasks, available_tasks):
    """Print overall SBXP summary."""
    leveling = member.get("leveling", {})
    actual_xp = leveling.get("experience", 0)
    sb_level = int(actual_xp / 100)
    xp_in_level = actual_xp % 100
    xp_to_next = 100 - xp_in_level

    print_header("SKYBLOCK XP SUMMARY")
    print(f"  SB Level:    {sb_level} ({_fmt(actual_xp)} XP)")
    print(f"  Next Level:  {sb_level + 1} — need {xp_to_next} more XP ({xp_in_level}/100)")
    print()

    formula_total = sum(r["current"] for r in formula_results)
    task_total = sum(t["xp"] for t in completed_tasks)
    calculated_total = formula_total + task_total
    gap = actual_xp - calculated_total

    print(f"  Formula sources:     {_fmt(formula_total)} XP")
    print(f"  Individual tasks:    {_fmt(task_total)} XP  ({len(completed_tasks)} tasks)")
    print(f"  Calculated total:    {_fmt(calculated_total)} XP")
    print(f"  Actual total:        {_fmt(actual_xp)} XP")
    if gap != 0:
        print(f"  Unmapped gap:        {gap:+d} XP  (from untracked sources: objectives, events, etc.)")


def print_formula_breakdown(formula_results):
    """Print detailed breakdown of formula-based SBXP sources."""
    print_header("FORMULA-BASED SBXP BREAKDOWN")

    # Group by category
    categories = {}
    for r in formula_results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)

    for cat_name in ["Core", "Dungeons", "Slaying", "Mining", "Farming"]:
        items = categories.get(cat_name, [])
        if not items:
            continue
        cat_total = sum(r["current"] for r in items)
        cat_max = sum(r["max"] for r in items if r["max"] is not None)
        max_str = f"/{_fmt(cat_max)}" if cat_max else ""
        print(f"\n  {cat_name} ({_fmt(cat_total)}{max_str} XP)")
        print(f"  {'─' * 60}")

        for r in items:
            current = r["current"]
            max_xp = r["max"]
            remaining = max_xp - current if max_xp is not None else None

            if max_xp is not None:
                pct = current / max_xp * 100 if max_xp > 0 else 100
                bar_width = 20
                filled = int(pct / 100 * bar_width)
                bar = f"[{'█' * filled}{'░' * (bar_width - filled)}]"
                remain_str = f"  (+{remaining} avail)" if remaining and remaining > 0 else ""
                print(f"    {r['name']:26s} {current:>5d}/{max_xp:<5d} {bar} {pct:5.1f}%{remain_str}")
            else:
                print(f"    {r['name']:26s} {current:>5d}       (no cap)")

            # Show skill details for skills
            details = r["details"]
            if r["id"] == "skill_levels" and isinstance(details, list):
                low_skills = [(name, lvl, mx, xp) for name, lvl, mx, xp in details
                              if lvl < mx]
                low_skills.sort(key=lambda x: x[1])
                for name, lvl, mx, xp in low_skills[:5]:
                    # How much SBXP would next level give?
                    next_lvl = lvl + 1
                    if next_lvl <= 10:
                        next_gain = 5
                    elif next_lvl <= 25:
                        next_gain = 10
                    elif next_lvl <= 50:
                        next_gain = 20
                    else:
                        next_gain = 30
                    print(f"      {name:14s} Lv {lvl:2d}/{mx}  (next level → +{next_gain} SBXP)")

            elif r["id"] == "class_levels" and isinstance(details, list):
                for cls_name, lvl, xp in details:
                    if lvl < 50:
                        print(f"      {cls_name:14s} Lv {lvl:2d}/50  (next → +4 SBXP)")

            elif r["id"] == "slayer_levels" and isinstance(details, list):
                for sl_name, lvl, xp in details:
                    max_lvl = 5 if sl_name == "vampire" else 9
                    if lvl < max_lvl and lvl < len(SLAYER_LEVEL_XP):
                        next_gain = SLAYER_LEVEL_XP[lvl]
                        print(f"      {sl_name:14s} Lv {lvl}/{max_lvl}  (next → +{next_gain} SBXP)")


def print_recommendations(available_tasks, formula_results, member, category_filter=None):
    """Print ranked recommendations for gaining SBXP."""
    print_header("RECOMMENDATIONS")

    leveling = member.get("leveling", {})
    actual_xp = leveling.get("experience", 0)
    xp_to_next = 100 - (actual_xp % 100)
    sb_level = int(actual_xp / 100)

    print(f"  Need {xp_to_next} XP for SB Level {sb_level + 1}\n")

    # ── Formula-based gains (things that would give XP by improving stats) ──
    formula_recs = []

    for r in formula_results:
        if r["max"] is None:
            # Uncapped sources: MP, pet score
            if r["id"] == "accessory_bag":
                formula_recs.append({
                    "name": "Gain Magical Power",
                    "category": "Core",
                    "xp_per_unit": 1,
                    "effort": "medium",
                    "notes": f"Currently {r['details']['mp']} MP. Each MP = +1 SBXP. Buy/upgrade accessories",
                    "current": r["current"],
                })
            elif r["id"] == "pet_score":
                formula_recs.append({
                    "name": "Increase Pet Score",
                    "category": "Core",
                    "xp_per_unit": 3,
                    "effort": "medium",
                    "notes": f"Currently {r['details']['score']} score. Each unique pet rarity = +3 SBXP",
                    "current": r["current"],
                })
            continue

        remaining = r["max"] - r["current"]
        if remaining <= 0:
            continue

        details = r["details"]

        if r["id"] == "skill_levels":
            # Recommend easiest skill levels to gain
            for name, lvl, mx, xp in details:
                if lvl < mx:
                    next_lvl = lvl + 1
                    if next_lvl <= 10:
                        gain = 5
                    elif next_lvl <= 25:
                        gain = 10
                    elif next_lvl <= 50:
                        gain = 20
                    else:
                        gain = 30
                    # Effort depends on current level
                    if lvl < 15:
                        effort = "easy"
                    elif lvl < 25:
                        effort = "medium"
                    elif lvl < 40:
                        effort = "hard"
                    else:
                        effort = "extreme"
                    formula_recs.append({
                        "name": f"Level {name.capitalize()} to {next_lvl}",
                        "category": "Skills",
                        "xp_per_unit": gain,
                        "effort": effort,
                        "notes": f"Currently Lv {lvl}. +{gain} SBXP per level",
                        "current": xp,
                    })

        elif r["id"] == "fairy_souls":
            uncollected = 253 - details["collected"]
            if uncollected > 0:
                potential_exchanges = uncollected // 5
                if potential_exchanges > 0:
                    formula_recs.append({
                        "name": f"Collect Fairy Souls ({uncollected} remaining)",
                        "category": "Core",
                        "xp_per_unit": potential_exchanges * 10,
                        "effort": "medium",
                        "notes": f"{details['collected']}/253 found. Each 5 souls = +10 SBXP. Use NEU/SBA soul finder",
                        "current": r["current"],
                    })

        elif r["id"] == "collections":
            if remaining > 0:
                formula_recs.append({
                    "name": "Unlock Collection Milestones",
                    "category": "Core",
                    "xp_per_unit": 4,
                    "effort": "medium",
                    "notes": f"{details.get('milestones', '?')}/{details.get('possible', '?')} milestones. Each = +4 SBXP. Gather materials manually (Bazaar doesn't count!)",
                    "current": r["current"],
                })

        elif r["id"] == "crafted_minions":
            if remaining > 0:
                formula_recs.append({
                    "name": "Craft Unique Minions",
                    "category": "Core",
                    "xp_per_unit": 1,
                    "effort": "medium",
                    "notes": f"{details['unique_crafts']} unique crafts. T1-6 = +1, T7 = +2, ... T12 = +24 SBXP each",
                    "current": r["current"],
                })

        elif r["id"] == "bestiary":
            if remaining > 0:
                formula_recs.append({
                    "name": "Progress Bestiary",
                    "category": "Slaying",
                    "xp_per_unit": 1,
                    "effort": "medium",
                    "notes": f"{details['milestones']} milestones. Each tier +1, every 10th +10 bonus. Kill varied mobs",
                    "current": r["current"],
                })

        elif r["id"] == "powder":
            for powder_type in ["mithril", "gemstone", "glacite"]:
                pd = details.get(powder_type, {})
                total = pd.get("total", 0)
                if total < 600_000:
                    divisor = 2400 if powder_type == "mithril" else 2500
                    remaining_linear = (600_000 - total) // divisor
                    if remaining_linear > 0:
                        formula_recs.append({
                            "name": f"Earn {powder_type.capitalize()} Powder",
                            "category": "Mining",
                            "xp_per_unit": remaining_linear,
                            "effort": "medium" if powder_type == "mithril" else "hard",
                            "notes": f"{_fmt(total)}/{_fmt(600_000)} powder. Mine in Dwarven Mines/Crystal Hollows",
                            "current": pd.get("sbxp", 0),
                        })

    # ── Individual task gains ──
    task_recs = []
    for task in available_tasks:
        task_recs.append({
            "name": task["name"],
            "category": task["category"],
            "xp_per_unit": task["xp"],
            "effort": task.get("effort", "medium"),
            "notes": task.get("notes", ""),
        })

    # ── Combine and sort ──
    all_recs = formula_recs + task_recs

    if category_filter:
        cf = category_filter.lower()
        all_recs = [r for r in all_recs if cf in r["category"].lower()]

    # Sort by: effort (ascending), then XP value (descending)
    all_recs.sort(key=lambda r: (EFFORT_ORDER.get(r["effort"], 2), -r["xp_per_unit"]))

    # Group by effort
    for effort_name in ["easy", "medium", "hard", "extreme"]:
        group = [r for r in all_recs if r["effort"] == effort_name]
        if not group:
            continue

        total_xp = sum(r["xp_per_unit"] for r in group)
        emoji = {"easy": "🟢", "medium": "🟡", "hard": "🟠", "extreme": "🔴"}.get(effort_name, "⚪")
        print(f"  {emoji} {effort_name.upper()} ({total_xp} XP available)")
        print(f"  {'─' * 60}")

        for r in group:
            xp_str = f"+{r['xp_per_unit']}" if r['xp_per_unit'] < 1000 else f"+{_fmt(r['xp_per_unit'])}"
            notes = f"  — {r['notes']}" if r.get("notes") else ""
            cat_tag = f"[{r['category']}]"
            print(f"    {xp_str:>6s} XP  {r['name']:<36s} {cat_tag}")
            if notes and len(notes) < 80:
                print(f"             {notes.strip()}")
        print()

    # Quick wins: tasks that together would get to next level
    print(f"  {'─' * 60}")
    easy_medium = [r for r in all_recs if r["effort"] in ("easy", "medium")]
    cumulative = 0
    quick_wins = []
    for r in easy_medium:
        cumulative += r["xp_per_unit"]
        quick_wins.append(r)
        if cumulative >= xp_to_next:
            break

    if quick_wins and cumulative >= xp_to_next:
        print(f"  ⚡ QUICK PATH TO LEVEL {sb_level + 1} ({xp_to_next} XP needed):")
        for r in quick_wins:
            print(f"     +{r['xp_per_unit']:>3d} XP  {r['name']}")
        print(f"     = {cumulative} XP total")
    else:
        total_easy_medium = sum(r["xp_per_unit"] for r in easy_medium)
        if total_easy_medium > 0:
            print(f"  ⚡ Easy+Medium tasks give {total_easy_medium} XP (need {xp_to_next} for next level)")


# ─── Phase 4: Smart recommendation helpers ───

# Essence costs per tier, parsed from wiki shop pages (as of Feb 2026).
# Source: https://hypixel-skyblock.fandom.com/wiki/Essence_Shop
# Format: {ESSENCE_TYPE: {PERK_ID: [cost_tier_1, cost_tier_2, ...]}}
# TODO: Consider generating this from wiki_dump.py parsed data or the API
#       to avoid manual maintenance when Hypixel adds/changes perks.
ESSENCE_SHOP_COSTS = {
    "GOLD": {
        "HEART_OF_GOLD": [1000, 1500, 2000, 3000, 5000],
        "TREASURES_OF_THE_EARTH": [150, 500, 1250, 2000, 3000],
        "DWARVEN_TRAINING": [250, 1250, 5000],
        "UNBREAKING": [150, 500, 1250, 2000, 3000],
        "EAGER_MINER": [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
        "MIDAS_LURE": [200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000],
    },
    "DRAGON": {
        "ONE_PUNCH": [100, 200, 300, 400, 500],
        "RECHARGE": [100, 100, 100, 100, 100, 100, 100, 100, 100, 100],
        "RAGEBORN": [125, 250, 500, 1000, 1500],
        "ZEALUCK": [150, 500, 1250, 2000, 3000],
        "ENDER_TRAINING": [250, 1250, 5000],
        "INFUSED_DRAGON": [500, 1500, 2500, 3500, 4000],
        "UNBRIDLED_RAGE": [1000, 1500, 2000, 3000, 5000],
        "TWO_HEADED_STRIKE": [1500, 2250, 3250, 4500, 6500],
        "DRAGON_PIPER": [2000],
    },
    "ICE": {
        "COLD_EFFICIENCY": [1000, 1500, 2000, 3000, 5000],
        "COOLED_FORGES": [100, 1000, 2000, 3000, 5000],
        "FROZEN_SKIN": [1000, 1500, 2000, 3000, 5000],
        "SEASON_OF_JOY": [200, 400, 800, 1500, 2100, 3000, 3000, 4000, 4000, 4000],
        "DRAKE_PIPER": [2000],
    },
    "SPIDER": {
        "EMPOWERED_AGILITY": [50, 75, 100, 150, 250, 400, 750, 1000, 1750, 2500],
        "VERMIN_CONTROL": [100, 500, 1000, 3000, 5000],
        "BANE": [100, 500, 1000, 3000, 5000],
        "SPIDER_TRAINING": [250, 1250, 5000],
        "TOXOPHILITE": [1000, 1500, 2000, 3000, 5000],
    },
    "UNDEAD": {
        "CATACOMBS_BOSS_LUCK": [100, 1000, 10000, 100000],
        "LOOTING": [1000, 2000, 3000, 4000, 5000],
        "HELP_OF_THE_FAIRIES": [200000],
        "HEALTH_ESSENCE": [1000, 2500, 5000, 10000, 25000],
        "DEFENSE_ESSENCE": [1000, 4000, 6000, 8000, 10000],
        "STRENGTH_ESSENCE": [1000, 4000, 6000, 8000, 10000],
        "INTELLIGENCE_ESSENCE": [1000, 4000, 6000, 8000, 10000],
        "CRITICAL_ESSENCE": [1000, 3000, 10000, 20000, 50000],
    },
    "WITHER": {
        "FORBIDDEN_HEALTH": [100, 250, 500, 1000, 1500],
        "FORBIDDEN_DEFENSE": [100, 250, 500, 1000, 1500],
        "FORBIDDEN_SPEED": [100, 250],
        "FORBIDDEN_INTELLIGENCE": [100, 250, 500, 1000, 1500],
        "FORBIDDEN_STRENGTH": [100, 250, 500, 1000, 1500],
        "FORBIDDEN_BLESSING": [200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000],
    },
    "CRIMSON": {
        "STRONGARM": [1000, 2000],
        "FRESH_TOOLS": [200, 400, 600, 800, 1000],
        "HEADSTART": [100, 200, 300, 400, 500],
        "KUUDRA_MASTER": [5000],
        "FUNGUS_FORTUNA": [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
        "HARENA_FORTUNA": [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
        "CRIMSON_TRAINING": [250, 1250, 5000],
        "WITHER_PIPER": [500, 750, 1250, 2000, 3000],
    },
    "DIAMOND": {
        "RADIANT_FISHER": [200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000],
        "DIAMOND_IN_THE_ROUGH": [1000, 1500, 2000, 3000, 5000],
        "RHINESTONE_INFUSION": [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
        "UNDER_PRESSURE": [125, 250, 500, 1000, 1500],
        "HIGH_ROLLER": [5000],
        "RETURN_TO_SENDER": [50, 75, 100, 150, 250, 400, 750, 1000, 1750, 2500],
    },
}

# XP per tier for task DB cross-reference
XP_PER_TIER = {
    1: [2], 2: [2, 2], 3: [2, 2, 3], 4: [2, 2, 3, 5],
    5: [2, 2, 3, 5, 7], 10: [2, 2, 3, 5, 7, 8, 8, 8, 9, 10],
}


def find_affordable_essence_perks(member, completed_set):
    """Cross-reference essence stockpiles vs shop costs → find purchasable perks.

    Returns list of {task_id, name, xp, essence_type, cost, available_essence}.
    """
    # Get essence amounts
    currencies = member.get("currencies", {})
    essence = currencies.get("essence", {})
    essence_amounts = {}
    for etype in ("GOLD", "DRAGON", "ICE", "SPIDER", "UNDEAD", "WITHER", "CRIMSON", "DIAMOND"):
        essence_amounts[etype] = essence.get(etype, {}).get("current", 0)

    affordable = []
    for etype, perks in ESSENCE_SHOP_COSTS.items():
        available = essence_amounts.get(etype, 0)
        if available <= 0:
            continue

        for perk_id, costs in perks.items():
            # Find the next unpurchased tier
            for tier_idx, cost in enumerate(costs):
                tier = tier_idx + 1
                task_id = f"{etype}_ESSENCE_{perk_id}_{tier}"
                if task_id in completed_set:
                    continue  # Already purchased
                if cost <= available:
                    # This tier is affordable!
                    max_tier = len(costs)
                    xp_values = XP_PER_TIER.get(max_tier, [2] * max_tier)
                    xp = xp_values[tier_idx] if tier_idx < len(xp_values) else 2
                    affordable.append({
                        "task_id": task_id,
                        "name": f"{etype.title()} — {perk_id.replace('_', ' ').title()} T{tier}",
                        "xp": xp,
                        "essence_type": etype,
                        "cost": cost,
                        "available": available,
                    })
                break  # Only suggest next unpurchased tier per perk

    # Sort by cost (cheapest first)
    affordable.sort(key=lambda x: x["cost"])
    return affordable


def find_close_collection_milestones(member):
    """Find collection milestones close to completion (>80% progress).

    Returns list of {collection, current, needed, tier, sbxp}.
    """
    collections = member.get("collection", {})
    if not collections:
        return []

    # Fetch collection tier data from API
    try:
        req = Request("https://api.hypixel.net/v2/resources/skyblock/collections")
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        if not data.get("success"):
            return []
    except Exception:
        return []

    close = []
    for category_data in data.get("collections", {}).values():
        for item_id, item_data in category_data.get("items", {}).items():
            tiers = item_data.get("tiers", [])
            count = collections.get(item_id, 0)
            if count <= 0:
                continue

            for tier in tiers:
                required = tier["amountRequired"]
                if count >= required:
                    continue  # Already reached this tier
                # Check if we're close (>60% for small, >80% for large)
                progress = count / required
                threshold = 0.6 if required < 10_000 else 0.8
                if progress >= threshold:
                    remaining = required - count
                    display_name = item_id.replace("_", " ").title()
                    close.append({
                        "collection": display_name,
                        "item_id": item_id,
                        "current": count,
                        "needed": required,
                        "remaining": remaining,
                        "tier": tier["tier"],
                        "progress_pct": progress * 100,
                        "sbxp": 4,  # Each collection milestone = +4 SBXP
                    })
                break  # Only show next unfinished tier per collection

    # Sort by remaining (closest first)
    close.sort(key=lambda x: x["remaining"])
    return close


def print_smart_recommendations(member, completed_set, data=None):
    """Print Phase 4 smart recommendations — free XP detection."""
    print_header("SMART RECOMMENDATIONS (Free/Cheap XP)")

    found_any = False

    # ── Affordable essence shop perks ──
    affordable = find_affordable_essence_perks(member, completed_set)
    if affordable:
        found_any = True
        total_xp = sum(a["xp"] for a in affordable)
        print(f"\n  💎 AFFORDABLE ESSENCE PERKS ({total_xp} XP available right now)")
        print(f"  {'─' * 60}")
        # Group by essence type
        by_type = {}
        for a in affordable:
            et = a["essence_type"]
            if et not in by_type:
                by_type[et] = []
            by_type[et].append(a)

        for etype, perks in by_type.items():
            avail = perks[0]["available"]
            total_cost = sum(p["cost"] for p in perks)
            type_xp = sum(p["xp"] for p in perks)
            can_afford_all = total_cost <= avail
            print(f"    {etype.title()} Essence: {_fmt(avail)} available")
            for p in perks:
                print(f"      +{p['xp']} XP  {p['name']}  (costs {_fmt(p['cost'])})")
            if can_afford_all and len(perks) > 1:
                print(f"      → Can buy all {len(perks)} for {_fmt(total_cost)} = +{type_xp} XP")
            print()

    # ── Close collection milestones ──
    close_collections = find_close_collection_milestones(member)
    if close_collections:
        found_any = True
        print(f"\n  📦 COLLECTION MILESTONES ALMOST DONE (+4 XP each)")
        print(f"  {'─' * 60}")
        for c in close_collections[:15]:
            pct = c["progress_pct"]
            bar_width = 15
            filled = int(pct / 100 * bar_width)
            bar = f"[{'█' * filled}{'░' * (bar_width - filled)}]"
            print(f"    {c['collection']:25s} {bar} {pct:5.1f}%  "
                  f"({_fmt(c['current'])}/{_fmt(c['needed'])}, need {_fmt(c['remaining'])} more)")
        if len(close_collections) > 15:
            print(f"    ... and {len(close_collections) - 15} more")
        print(f"    Total: +{len(close_collections) * 4} XP from {len(close_collections)} milestones")
        print(f"    ⚠ Remember: Bazaar purchases don't count — gather manually!")
        print()

    # ── Garden quick wins ──
    if data:
        garden = data.get("garden", {}).get("garden", {})
        garden_xp = garden.get("garden_experience", 0)
        plots = len(garden.get("unlocked_plots_ids", []))
        crop_upgrades = sum(garden.get("crop_upgrade_levels", {}).values())
        resources = garden.get("resources_collected", {})

        garden_tips = []
        if garden_xp > 0 and plots < 24:
            garden_tips.append(f"Unlock more garden plots ({plots}/24, +5 XP each)")
        if crop_upgrades < 90:
            garden_tips.append(f"Buy crop upgrades ({crop_upgrades}/90, +1 XP each)")
        # Check for crop milestones close to thresholds
        for crop, amount in resources.items():
            for threshold in CROP_MILESTONE_THRESHOLDS:
                if amount < threshold:
                    progress = amount / threshold
                    if progress >= 0.75:
                        remaining = threshold - amount
                        crop_name = crop.replace("_", " ").replace("ITEM", "").strip().title()
                        garden_tips.append(
                            f"{crop_name}: {_fmt(remaining)} more for milestone "
                            f"({_fmt(amount)}/{_fmt(threshold)}, +1 XP)")
                    break

        if garden_tips:
            found_any = True
            print(f"\n  🌱 GARDEN OPPORTUNITIES")
            print(f"  {'─' * 60}")
            for tip in garden_tips:
                print(f"    • {tip}")
            print()

    if not found_any:
        print("\n  No smart recommendations available right now.")
        print("  (Run profile.py to refresh data)")


def main():
    parser = argparse.ArgumentParser(
        description="SkyBlock XP analysis and recommendations")
    parser.add_argument("--brief", "-b", action="store_true",
                        help="Show only recommendations, skip breakdown")
    parser.add_argument("--category", "-c", type=str, default="",
                        help="Filter recommendations by category (e.g., mining, dungeons)")
    parser.add_argument("--json", action="store_true",
                        help="Output raw analysis as JSON")
    args = parser.parse_args()

    data, member = load_profile()
    tasks_db = load_tasks()

    player_name = data.get("player", "Unknown")

    if not args.json:
        print(f"SkyBlock XP Analysis for {player_name}")
        print("  Calculating formula-based sources...")

    # Analyze formula sources
    formula_results = analyze_formula_sources(member, data)

    # Analyze individual tasks
    completed_tasks, available_tasks = analyze_individual_tasks(member, tasks_db)

    if args.json:
        output = {
            "player": player_name,
            "sb_level": int(member.get("leveling", {}).get("experience", 0) / 100),
            "total_xp": member.get("leveling", {}).get("experience", 0),
            "formula_sources": formula_results,
            "completed_tasks": len(completed_tasks),
            "available_tasks": [{"id": t["id"], "name": t["name"], "xp": t["xp"],
                                 "effort": t.get("effort")} for t in available_tasks],
        }
        print(json.dumps(output, indent=2))
        return

    # Print results
    completed_set = set(member.get("leveling", {}).get("completed_tasks", []))

    print_summary(member, formula_results, completed_tasks, available_tasks)

    if not args.brief:
        print_formula_breakdown(formula_results)

    print_recommendations(
        available_tasks, formula_results, member,
        category_filter=args.category or None)

    # Phase 4: Smart recommendations
    if not args.brief:
        print_smart_recommendations(member, completed_set, data)


if __name__ == "__main__":
    main()
