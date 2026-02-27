#!/usr/bin/env python3
"""Fetch and display Hypixel SkyBlock profile data."""

import argparse
import base64
import gzip
import json
import os
import re
import struct
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from pricing import PriceCache, _fmt as fmt_price_num, display_name
from crafts import (parse_recipes, load_craft_cache, load_collections_data,
                    load_slayer_thresholds, resolve_collection_requirement,
                    resolve_slayer_requirement, filter_craft_flips,
                    calculate_craft_cost, check_unlocked, CRAFT_CACHE_PATH)

DATA_DIR = Path(__file__).parent.parent / "data"

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

API_KEY = os.environ.get("HYPIXEL_API_KEY", "")

# --- Section definitions ---
CORE_SECTIONS = [
    "general", "dailies", "skills", "slayers", "dungeons", "hotm",
    "effects", "pets", "inventories",
]
EXTENDED_SECTIONS = [
    "collections", "minions", "garden", "museum", "rift",
    "sacks", "jacob", "crystals", "bestiary", "stats",
    "foraging", "chocolate", "community", "misc", "crafts",
]
ALL_SECTIONS = CORE_SECTIONS + EXTENDED_SECTIONS


def api_get(url, headers=None):
    req = Request(url, headers=headers or {})
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code}: {body}")
        sys.exit(1)


def resolve_uuid(username):
    data = api_get(f"https://api.mojang.com/users/profiles/minecraft/{username}")
    return data["id"], data["name"]


def get_profiles(uuid):
    return api_get(
        f"https://api.hypixel.net/v2/skyblock/profiles?uuid={uuid}",
        headers={"API-Key": API_KEY},
    )


def get_garden(profile_id):
    try:
        return api_get(
            f"https://api.hypixel.net/v2/skyblock/garden?profile={profile_id}",
            headers={"API-Key": API_KEY},
        )
    except SystemExit:
        return None


def get_museum(profile_id):
    try:
        return api_get(
            f"https://api.hypixel.net/v2/skyblock/museum?profile={profile_id}",
            headers={"API-Key": API_KEY},
        )
    except SystemExit:
        return None


# --- Skill XP tables ---
# Fallback thresholds in case the API fetch fails
_FALLBACK_SKILL_XP = [
    0, 50, 175, 375, 675, 1175, 1925, 2925, 4425, 6425, 9925,
    14925, 22425, 32425, 47425, 67425, 97425, 147425, 222425, 322425, 522425,
    822425, 1222425, 1722425, 2322425, 3022425, 3822425, 4722425, 5722425, 6822425, 8022425,
    9322425, 10722425, 12222425, 13822425, 15522425, 17322425, 19222425, 21222425, 23322425, 25522425,
    27822425, 30222425, 32722425, 35322425, 38072425, 40972425, 44072425, 47472425, 51172425, 55172425,
    59472425, 64072425, 68972425, 74172425, 79672425, 85472425, 91572425, 97972425, 104672425, 111672425,
]
_FALLBACK_RUNECRAFTING_XP = [
    0, 50, 150, 275, 435, 635, 885, 1200, 1600, 2100, 2725,
    3510, 4510, 5760, 7325, 9325, 11825, 14950, 18950, 23950, 30200,
    38050, 47850, 60100, 75400, 94450,
]
_FALLBACK_MAX_LEVELS = {
    "farming": 60, "mining": 60, "combat": 60, "foraging": 54,
    "fishing": 50, "enchanting": 60, "alchemy": 50, "taming": 60,
    "carpentry": 50, "social": 25, "runecrafting": 25, "hunting": 25,
}

# These get populated by fetch_skill_tables() or fall back to hardcoded
SKILL_THRESHOLDS = {}  # skill_name -> [0, xp1, xp2, ...]
SKILL_MAX_LEVELS = {}
COLLECTION_TIERS = {}  # item_id -> {name, tiers: [{tier, amountRequired, unlocks}]}


def fetch_skill_tables():
    """Fetch skill XP tables from the Hypixel API (no auth needed)."""
    global SKILL_THRESHOLDS, SKILL_MAX_LEVELS
    try:
        data = api_get("https://api.hypixel.net/v2/resources/skyblock/skills")
        if not data.get("success"):
            raise ValueError("API returned success=false")
        skills = data["skills"]
        for skill_id, skill_data in skills.items():
            name = skill_id.lower()
            max_level = skill_data["maxLevel"]
            thresholds = [0] + [int(l["totalExpRequired"]) for l in skill_data["levels"]]
            SKILL_THRESHOLDS[name] = thresholds
            SKILL_MAX_LEVELS[name] = max_level
        print(f"  Loaded {len(SKILL_THRESHOLDS)} skill tables from API")
    except Exception as e:
        print(f"  Could not fetch skill tables ({e}), using fallback")
        SKILL_MAX_LEVELS.update(_FALLBACK_MAX_LEVELS)
        for name in _FALLBACK_MAX_LEVELS:
            if name in ("runecrafting", "social"):
                SKILL_THRESHOLDS[name] = _FALLBACK_RUNECRAFTING_XP
            else:
                SKILL_THRESHOLDS[name] = _FALLBACK_SKILL_XP


def fetch_collection_tiers():
    """Fetch collection tier thresholds from the Hypixel API (no auth needed)."""
    global COLLECTION_TIERS
    try:
        data = api_get("https://api.hypixel.net/v2/resources/skyblock/collections")
        if not data.get("success"):
            raise ValueError("API returned success=false")
        collections = data.get("collections", {})
        for category_id, category_data in collections.items():
            items = category_data.get("items", {})
            for item_id, item_data in items.items():
                tiers = item_data.get("tiers", [])
                tier_reqs = []
                for tier in tiers:
                    tier_reqs.append({
                        "tier": tier["tier"],
                        "amountRequired": tier["amountRequired"],
                        "unlocks": tier.get("unlocks", []),
                    })
                COLLECTION_TIERS[item_id] = {
                    "name": item_data.get("name", item_id),
                    "tiers": tier_reqs,
                }
        print(f"  Loaded collection tier data ({len(COLLECTION_TIERS)} items)")
    except Exception as e:
        print(f"  Could not fetch collection tiers ({e})")


# Dungeon XP thresholds (catacombs + classes) up to level 50
DUNGEON_XP_THRESHOLDS = [
    0, 50, 125, 235, 395, 625, 955, 1425, 2095, 3045, 4385,
    6275, 8940, 12700, 17960, 25340, 35640, 50040, 70040, 97640, 135640,
    188140, 259640, 356640, 488640, 668640, 911640, 1239640, 1684640, 2284640, 3084640,
    4149640, 5559640, 7459640, 9959640, 13259640, 17559640, 23159640, 30359640, 39559640, 51559640,
    66559640, 85559640, 109559640, 139559640, 177559640, 225559640, 285559640, 360559640, 453559640, 569809640,
]

# Slayer XP thresholds
SLAYER_XP_THRESHOLDS = {
    "zombie": [0, 5, 15, 200, 1000, 5000, 20000, 100000, 400000, 1000000],
    "spider": [0, 5, 25, 200, 1000, 5000, 20000, 100000, 400000, 1000000],
    "wolf": [0, 10, 30, 250, 1500, 5000, 20000, 100000, 400000, 1000000],
    "enderman": [0, 10, 30, 250, 1500, 5000, 20000, 100000, 400000, 1000000],
    "blaze": [0, 10, 30, 250, 1500, 5000, 20000, 100000, 400000, 1000000],
    "vampire": [0, 20, 75, 240, 840, 2400],
}


def xp_to_level(xp, thresholds, max_level=None):
    level = 0
    for i, threshold in enumerate(thresholds):
        if xp >= threshold:
            level = i
        else:
            break
    if max_level:
        level = min(level, max_level)
    return level


def xp_to_level_progress(xp, thresholds, max_level=None):
    level = xp_to_level(xp, thresholds, max_level)
    if max_level and level >= max_level:
        return level, 1.0
    if level + 1 < len(thresholds):
        current = thresholds[level]
        next_thresh = thresholds[level + 1]
        progress = (xp - current) / (next_thresh - current) if next_thresh > current else 1.0
        return level, progress
    return level, 1.0


def format_number(n):
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        val = n / 1_000_000
        return f"{val:.1f}B" if val >= 999.95 else f"{val:.1f}M"  # avoid "1000.0M"
    if n >= 1_000:
        val = n / 1_000
        return f"{val:.1f}M" if val >= 999.95 else f"{val:.1f}K"  # avoid "1000.0K"
    return str(int(n))


def format_progress_bar(progress, width=20):
    filled = int(progress * width)
    return f"[{'█' * filled}{'░' * (width - filled)}] {progress * 100:.1f}%"


def print_section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def get_real_day_number():
    """Return floor(unix_time / 86400) — the real-world day counter used by the API."""
    return int(time.time() / 86400)


def print_daily_checklist(member):
    print_section("DAILY CHECKLIST")
    today = get_real_day_number()
    now = time.time()

    # Mining
    mc = member.get("mining_core", {})
    mining_day = mc.get("daily_ores_mined_day", 0)
    mining_count = mc.get("daily_ores_mined", 0)
    if mining_day == today:
        print(f"  Mining:          {mining_count} ores mined today")
    else:
        days_ago = today - mining_day if mining_day else None
        ago_str = f" (last: {days_ago}d ago)" if days_ago else ""
        print(f"  Mining:          Not yet{ago_str}")

    # Foraging
    fc = member.get("foraging_core", {})
    forage_day = fc.get("daily_trees_cut_day", 0)
    forage_count = fc.get("daily_trees_cut", 0)
    if forage_day == today:
        print(f"  Foraging:        {forage_count} trees cut today")
    else:
        days_ago = today - forage_day if forage_day else None
        ago_str = f" (last: {days_ago}d ago)" if days_ago else ""
        print(f"  Foraging:        Not yet{ago_str}")

    # Experiments
    # Superpairs is the main experiment; Chronomatron/Ultrasequencer are add-ons
    # that earn extra clicks on the next Superpairs round.
    exp = member.get("experimentation", {})
    pairings = exp.get("pairings", {})
    simon = exp.get("simon", {})
    superpairs_done = pairings.get("claimed", False)
    addon_done = simon.get("claimed", False)
    bonus_clicks = simon.get("bonus_clicks", 0)
    line = "Superpairs done" if superpairs_done else "Superpairs not done"
    if addon_done:
        line += f", add-ons claimed"
    elif bonus_clicks:
        line += f", add-on: {bonus_clicks} bonus clicks (not claimed)"
    else:
        line += ", add-ons not done"
    print(f"  Experiments:     {line}")

    # Rift entries
    rift_charge_ts = member.get("rift", {}).get("access", {}).get("charge_track_timestamp")
    if rift_charge_ts:
        elapsed_sec = now - (rift_charge_ts / 1000)
        CHARGE_COOLDOWN_HOURS = 4
        MAX_CHARGES = 3
        charges = min(int(elapsed_sec / (CHARGE_COOLDOWN_HOURS * 3600)), MAX_CHARGES)
        if charges >= MAX_CHARGES:
            print(f"  Rift Entries:    {charges}/{MAX_CHARGES} (full)")
        else:
            next_sec = (CHARGE_COOLDOWN_HOURS * 3600) - (elapsed_sec % (CHARGE_COOLDOWN_HOURS * 3600))
            next_h = int(next_sec / 3600)
            next_m = int((next_sec % 3600) / 60)
            print(f"  Rift Entries:    {charges}/{MAX_CHARGES} (next in {next_h}h {next_m:02d}m)")
    else:
        print(f"  Rift Entries:    N/A")


def print_skills(member):
    print_section("SKILLS")
    skills = {}
    # v2: skills are under player_data.experience as SKILL_MINING etc.
    for key, val in member.get("player_data", {}).get("experience", {}).items():
        name = key.replace("SKILL_", "").lower()
        skills[name] = val
    # v1 fallback: flat experience_skill_* keys at top level
    if not skills:
        for key, val in member.items():
            if key.startswith("experience_skill_"):
                name = key.replace("experience_skill_", "")
                skills[name] = val

    if not skills:
        print("  Skills API disabled or no data")
        return

    total_level = 0
    skill_count = 0
    # Cosmetic skills excluded from skill average
    excluded_from_avg = {"runecrafting", "social", "hunting"}
    for name in ["farming", "mining", "combat", "foraging", "fishing",
                  "enchanting", "alchemy", "taming", "carpentry",
                  "runecrafting", "social", "hunting"]:
        xp = skills.get(name, 0)
        max_lvl = SKILL_MAX_LEVELS.get(name, 50)
        thresholds = SKILL_THRESHOLDS.get(name, _FALLBACK_SKILL_XP)

        level, progress = xp_to_level_progress(xp, thresholds, max_lvl)
        bar = format_progress_bar(progress)
        print(f"  {name.capitalize():14s} {level:3d}/{max_lvl}  {bar}  ({format_number(xp)} XP)")

        if name not in excluded_from_avg:
            total_level += level
            skill_count += 1

    if skill_count:
        print(f"\n  Skill Average: {total_level / skill_count:.1f}")


def print_slayers(member):
    print_section("SLAYERS")
    # v2: slayer.slayer_bosses, v1: slayer_bosses
    slayer_wrapper = member.get("slayer", {})
    slayer_data = slayer_wrapper.get("slayer_bosses", member.get("slayer_bosses", {}))
    if not slayer_data:
        print("  No slayer data")
        return

    total_xp = 0
    for name in ["zombie", "spider", "wolf", "enderman", "blaze", "vampire"]:
        data = slayer_data.get(name, {})
        xp = data.get("xp", 0)
        total_xp += xp
        thresholds = SLAYER_XP_THRESHOLDS.get(name, [])
        level = xp_to_level(xp, thresholds)
        max_lvl = len(thresholds) - 1

        kills = []
        for tier in range(5):
            k = data.get(f"boss_kills_tier_{tier}", 0)
            if k > 0:
                kills.append(f"T{tier + 1}:{k}")
        kills_str = ", ".join(kills) if kills else "none"

        print(f"  {name.capitalize():12s} Level {level}/{max_lvl}  ({format_number(xp)} XP)  Kills: {kills_str}")

    print(f"\n  Total Slayer XP: {format_number(total_xp)}")


def format_time_ms(ms):
    """Format milliseconds as mm:ss."""
    total_seconds = int(ms / 1000)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}"


def print_dungeons(member):
    print_section("DUNGEONS")
    dungeons = member.get("dungeons", {})
    if not dungeons:
        print("  No dungeon data")
        return

    # Catacombs level
    cata = dungeons.get("dungeon_types", {}).get("catacombs", {})
    cata_xp = cata.get("experience", 0)
    cata_level, cata_progress = xp_to_level_progress(cata_xp, DUNGEON_XP_THRESHOLDS, 50)
    bar = format_progress_bar(cata_progress)
    print(f"  Catacombs     {cata_level:3d}/50  {bar}  ({format_number(cata_xp)} XP)")

    # Global stats
    total_secrets = dungeons.get("secrets", 0)
    last_run = dungeons.get("last_dungeon_run", "")
    if total_secrets:
        print(f"  Secrets Found: {total_secrets}")
    if last_run:
        # Format "CATACOMBS_FLOOR_TWO" -> "Catacombs Floor Two"
        print(f"  Last Run:      {last_run.replace('_', ' ').title()}")

    # Per-floor stats table
    completions = cata.get("tier_completions", {})
    best_scores = cata.get("best_score", {})
    fastest = cata.get("fastest_time", {})
    fastest_s = cata.get("fastest_time_s", {})
    fastest_sp = cata.get("fastest_time_s_plus", {})
    times_played = cata.get("times_played", {})

    # Gather all floors that have any data
    all_floors = set()
    for d in [completions, best_scores, fastest, times_played]:
        all_floors.update(k for k in d if k.isdigit())

    if all_floors:
        print(f"\n  {'Floor':>8s}  {'Runs':>5s}  {'Clears':>6s}  {'Score':>5s}  {'Fastest':>8s}  {'Fast S':>8s}  {'Fast S+':>8s}")
        print(f"  {'─' * 8}  {'─' * 5}  {'─' * 6}  {'─' * 5}  {'─' * 8}  {'─' * 8}  {'─' * 8}")
        for floor in sorted(all_floors, key=int):
            label = "Entrance" if floor == "0" else f"F{floor}"
            runs = int(times_played.get(floor, 0))
            clears = int(completions.get(floor, 0))
            score = best_scores.get(floor, "")
            ft = format_time_ms(fastest[floor]) if floor in fastest else "—"
            fs = format_time_ms(fastest_s[floor]) if floor in fastest_s else "—"
            fsp = format_time_ms(fastest_sp[floor]) if floor in fastest_sp else "—"
            score_str = str(int(score)) if score else "—"
            print(f"  {label:>8s}  {runs:>5d}  {clears:>6d}  {score_str:>5s}  {ft:>8s}  {fs:>8s}  {fsp:>8s}")

    # Master mode
    master = dungeons.get("dungeon_types", {}).get("master_catacombs", {})
    m_completions = master.get("tier_completions", {})
    m_floors = {k for k in m_completions if k.isdigit() and m_completions[k] > 0}
    if m_floors:
        m_best_scores = master.get("best_score", {})
        m_fastest = master.get("fastest_time", {})
        m_fastest_s = master.get("fastest_time_s", {})
        m_fastest_sp = master.get("fastest_time_s_plus", {})
        m_times_played = master.get("times_played", {})
        print(f"\n  {'Master':>8s}  {'Runs':>5s}  {'Clears':>6s}  {'Score':>5s}  {'Fastest':>8s}  {'Fast S':>8s}  {'Fast S+':>8s}")
        print(f"  {'─' * 8}  {'─' * 5}  {'─' * 6}  {'─' * 5}  {'─' * 8}  {'─' * 8}  {'─' * 8}")
        for floor in sorted(m_floors, key=int):
            label = f"M{floor}"
            runs = int(m_times_played.get(floor, 0))
            clears = int(m_completions.get(floor, 0))
            score = m_best_scores.get(floor, "")
            ft = format_time_ms(m_fastest[floor]) if floor in m_fastest else "—"
            fs = format_time_ms(m_fastest_s[floor]) if floor in m_fastest_s else "—"
            fsp = format_time_ms(m_fastest_sp[floor]) if floor in m_fastest_sp else "—"
            score_str = str(int(score)) if score else "—"
            print(f"  {label:>8s}  {runs:>5d}  {clears:>6d}  {score_str:>5s}  {ft:>8s}  {fs:>8s}  {fsp:>8s}")

    # Best damage records
    damage_classes = ["berserk", "mage", "healer", "archer", "tank"]
    has_damage = False
    for cls in damage_classes:
        dmg_data = cata.get(f"most_damage_{cls}", {})
        floor_keys = [k for k in dmg_data if k.isdigit()]
        if floor_keys:
            if not has_damage:
                print(f"\n  Best Damage:")
                has_damage = True
            floors_str = ", ".join(
                f"{'Entrance' if f == '0' else 'F' + f}: {format_number(dmg_data[f])}"
                for f in sorted(floor_keys, key=int)
            )
            best = dmg_data.get("best", 0)
            print(f"    {cls.capitalize():10s} {floors_str}  (best: {format_number(best)})")

    # Best runs per floor
    best_runs = cata.get("best_runs", {})
    if best_runs:
        print(f"\n  Best Runs:")
        for floor in sorted((k for k in best_runs if k.isdigit()), key=int):
            runs = best_runs[floor]
            if not runs:
                continue
            run = runs[0]  # Top run (highest score)
            label = "Entrance" if floor == "0" else f"F{floor}"

            exploration = run.get("score_exploration", 0)
            speed = run.get("score_speed", 0)
            skill = run.get("score_skill", 0)
            bonus = run.get("score_bonus", 0)
            total = exploration + speed + skill + bonus

            elapsed = run.get("elapsed_time", 0)
            damage = run.get("damage_dealt", 0)
            deaths = run.get("deaths", 0)
            mobs = run.get("mobs_killed", 0)
            secrets = run.get("secrets_found", 0)
            mitigated = run.get("damage_mitigated", 0)
            cls = run.get("dungeon_class", "?")
            ts = run.get("timestamp", 0)

            date_str = ""
            if ts:
                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                date_str = dt.strftime("%Y-%m-%d")

            print(f"    {label} — Score {total} (E:{exploration} Sp:{speed} Sk:{skill} B:{bonus})  "
                  f"Time: {format_time_ms(elapsed)}  Class: {cls.capitalize()}")
            print(f"         Damage: {format_number(damage)}  Mitigated: {format_number(mitigated)}  "
                  f"Deaths: {deaths}  Mobs: {mobs}  Secrets: {secrets}"
                  + (f"  ({date_str})" if date_str else ""))

    # Class levels
    classes = dungeons.get("player_classes", {})
    selected = dungeons.get("selected_dungeon_class", "unknown")
    if classes:
        print(f"\n  Classes (selected: {selected}):")
        for cls_name in ["healer", "mage", "berserk", "archer", "tank"]:
            cls_data = classes.get(cls_name, {})
            cls_xp = cls_data.get("experience", 0)
            cls_level, cls_progress = xp_to_level_progress(cls_xp, DUNGEON_XP_THRESHOLDS, 50)
            marker = " *" if cls_name == selected else ""
            print(f"    {cls_name.capitalize():10s} Level {cls_level:3d}/50  ({format_number(cls_xp)} XP){marker}")



# HotM / HotF XP thresholds (cumulative XP required for each level)
# Source: wiki.hypixel.net — Heart of the Mountain / Heart of the Forest
HOTM_XP_THRESHOLDS = [0, 3_000, 12_000, 37_000, 97_000, 197_000, 347_000, 557_000, 847_000, 1_247_000]
# Index 0 = level 1 (0 XP), index 1 = level 2 (3K cumulative), etc.
# Both HotM and HotF share the same XP table (HotF caps at level 7)

HOTM_TOKENS_PER_LEVEL = [1, 2, 2, 2, 2, 2, 3, 2, 2, 2]  # levels 1-10


def calc_hotx_level(xp, max_level=10):
    """Calculate HotM or HotF level from cumulative XP."""
    level = 1
    for i, threshold in enumerate(HOTM_XP_THRESHOLDS):
        if i + 1 > max_level:
            break
        if xp >= threshold:
            level = i + 1
        else:
            break
    # Progress toward next level
    if level >= max_level or level >= len(HOTM_XP_THRESHOLDS):
        return level, 1.0, 0  # maxed
    current_threshold = HOTM_XP_THRESHOLDS[level - 1]
    next_threshold = HOTM_XP_THRESHOLDS[level]
    xp_into_level = xp - current_threshold
    xp_needed = next_threshold - current_threshold
    progress = xp_into_level / xp_needed if xp_needed > 0 else 1.0
    xp_remaining = next_threshold - xp
    return level, progress, xp_remaining


def print_hotm(member):
    print_section("HEART OF THE MOUNTAIN")
    mining_core = member.get("mining_core", {})
    skill_tree = member.get("skill_tree", {})

    if not mining_core and not skill_tree:
        print("  No HotM data")
        return

    # HotM XP and tokens (under skill_tree, keyed by type)
    xp_data = skill_tree.get("experience", {})
    tokens_data = skill_tree.get("tokens_spent", {})
    abilities = skill_tree.get("selected_ability", {})

    mining_xp = xp_data.get("mining", 0) if isinstance(xp_data, dict) else 0
    foraging_xp = xp_data.get("foraging", 0) if isinstance(xp_data, dict) else 0
    mining_tokens = tokens_data.get("mountain", 0) if isinstance(tokens_data, dict) else 0
    foraging_tokens = tokens_data.get("forest", 0) if isinstance(tokens_data, dict) else 0

    # Calculate and display HotM level
    if mining_xp is not None:
        hotm_level, hotm_progress, hotm_remaining = calc_hotx_level(mining_xp, max_level=10)
        if hotm_level >= 10:
            print(f"  HotM Level:     {hotm_level}/10 (MAX)")
        else:
            print(f"  HotM Level:     {hotm_level}/10  ({hotm_progress:.0%} to {hotm_level + 1}, {format_number(hotm_remaining)} XP needed)")
        print(f"  Mining Tokens:  {mining_tokens} spent")

    if foraging_xp is not None:
        hotf_level, hotf_progress, hotf_remaining = calc_hotx_level(foraging_xp, max_level=7)
        if hotf_level >= 7:
            print(f"  HotF Level:     {hotf_level}/7 (MAX)")
        else:
            print(f"  HotF Level:     {hotf_level}/7  ({hotf_progress:.0%} to {hotf_level + 1}, {format_number(hotf_remaining)} XP needed)")
        print(f"  Forest Tokens:  {foraging_tokens} spent")

    # Powder (under mining_core)
    # API fields: powder_mithril = available (unspent), powder_spent_mithril = spent.
    # NOTE: powder_mithril_total is misleadingly named — it equals powder_mithril, NOT the
    # lifetime total. Compute lifetime as available + spent.
    powder_mithril_avail = mining_core.get("powder_mithril", 0)
    powder_spent_mithril = mining_core.get("powder_spent_mithril", 0)
    powder_gem_avail = mining_core.get("powder_gemstone", 0)
    powder_spent_gemstone = mining_core.get("powder_spent_gemstone", 0)
    powder_glacite_avail = mining_core.get("powder_glacite", 0)
    powder_spent_glacite = mining_core.get("powder_spent_glacite", 0)
    if powder_mithril_avail or powder_spent_mithril:
        print(f"  Mithril Powder: {format_number(powder_mithril_avail)} available ({format_number(powder_mithril_avail + powder_spent_mithril)} lifetime)")
    if powder_gem_avail or powder_spent_gemstone:
        print(f"  Gemstone Powder: {format_number(powder_gem_avail)} available ({format_number(powder_gem_avail + powder_spent_gemstone)} lifetime)")
    if powder_glacite_avail or powder_spent_glacite:
        print(f"  Glacite Powder: {format_number(powder_glacite_avail)} available ({format_number(powder_glacite_avail + powder_spent_glacite)} lifetime)")

    # Last mining access
    last_access = mining_core.get("greater_mines_last_access", 0)
    if last_access:
        elapsed_ms = int(time.time() * 1000) - last_access
        elapsed_h = elapsed_ms / 3600000
        if elapsed_h < 1:
            elapsed_str = f"{elapsed_ms // 60000}m ago"
        elif elapsed_h < 24:
            elapsed_str = f"{elapsed_h:.1f}h ago"
        else:
            elapsed_str = f"{elapsed_h / 24:.1f}d ago"
        print(f"  Last Mining:    {elapsed_str}")

    # Selected abilities
    if isinstance(abilities, dict):
        for tree, ability in abilities.items():
            if ability:
                print(f"  {tree.capitalize()} Ability: {ability.replace('_', ' ').title()}")

    # Mining perks (under skill_tree.nodes.mining)
    nodes = skill_tree.get("nodes", {})
    mining_nodes = nodes.get("mining", {})
    if mining_nodes:
        print(f"\n  Mining Perks:")
        for perk, level in sorted(mining_nodes.items()):
            if perk.startswith("toggle_"):
                continue  # Skip toggle flags
            if isinstance(level, int) and level > 0:
                display = perk.replace("_", " ").title()
                print(f"    {display:30s} Level {level}")

    # Foraging perks (under skill_tree.nodes.foraging)
    foraging_nodes = nodes.get("foraging", {})
    if foraging_nodes:
        print(f"\n  Foraging Perks:")
        for perk, level in sorted(foraging_nodes.items()):
            if perk.startswith("toggle_"):
                continue
            if isinstance(level, int) and level > 0:
                display = perk.replace("_", " ").title()
                print(f"    {display:30s} Level {level}")


def print_effects(member):
    print_section("ACTIVE EFFECTS")
    effects = member.get("player_data", {}).get("active_effects", [])
    if not effects:
        print("  No active effects")
        return

    for eff in effects:
        name = eff.get("effect", "unknown").replace("_", " ").title()
        level = eff.get("level", 0)
        infinite = eff.get("infinite", False)
        ticks = eff.get("ticks_remaining", 0)

        level_str = f" {_roman(level)}" if level > 0 else ""
        if infinite:
            time_str = "Infinite"
        else:
            seconds = ticks // 20
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            if hours > 0:
                time_str = f"{hours}h {minutes}m"
            elif minutes > 0:
                time_str = f"{minutes}m {secs}s"
            else:
                time_str = f"{secs}s"
        print(f"  {name}{level_str} — {time_str}")


def _roman(n):
    """Convert small int to Roman numeral."""
    if n <= 0 or n > 10:
        return str(n)
    numerals = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    return numerals[n]


def _load_pet_levels():
    """Load pet leveling tables from NEU repo."""
    pet_json = DATA_DIR / "neu-repo" / "constants" / "pets.json"
    if not pet_json.exists():
        return [], {}
    try:
        data = json.loads(pet_json.read_text())
        return data.get("pet_levels", []), data.get("pet_rarity_offset", {})
    except (json.JSONDecodeError, OSError):
        return [], {}


def _calc_pet_level(xp, rarity, pet_levels, rarity_offsets):
    """Calculate pet level from XP and rarity."""
    if not pet_levels:
        return None
    offset = rarity_offsets.get(rarity, 0)
    remaining = xp
    for i in range(offset, min(offset + 99, len(pet_levels))):
        if remaining < pet_levels[i]:
            return i - offset + 1
        remaining -= pet_levels[i]
    return 100


def print_pets(member):
    print_section("PETS")
    pets = member.get("pets_data", {}).get("pets", member.get("pets", []))
    if not pets:
        print("  No pets")
        return

    pet_levels, rarity_offsets = _load_pet_levels()

    # Sort by rarity then XP
    rarity_order = {"COMMON": 0, "UNCOMMON": 1, "RARE": 2, "EPIC": 3, "LEGENDARY": 4, "MYTHIC": 5}
    pets_sorted = sorted(pets, key=lambda p: (rarity_order.get(p.get("tier", ""), 0), p.get("exp", 0)), reverse=True)

    active = [p for p in pets_sorted if p.get("active")]
    if active:
        p = active[0]
        lvl = _calc_pet_level(p.get("exp", 0), p.get("tier", ""), pet_levels, rarity_offsets)
        lvl_str = f" Lvl {lvl}" if lvl else ""
        print(f"  Active: [{p.get('tier', '?')}] {p.get('type', '?')}{lvl_str}")
        print()

    for p in pets_sorted[:20]:  # Show top 20
        marker = " (active)" if p.get("active") else ""
        held = p.get("heldItem")
        held_str = f" [{held}]" if held else ""
        lvl = _calc_pet_level(p.get("exp", 0), p.get("tier", ""), pet_levels, rarity_offsets)
        lvl_str = f" Lvl {lvl}" if lvl else ""
        print(f"  [{p.get('tier', '?'):9s}] {p.get('type', '?')}{lvl_str}{held_str}{marker}")

    if len(pets_sorted) > 20:
        print(f"  ... and {len(pets_sorted) - 20} more")

    print(f"\n  Total pets: {len(pets_sorted)}")


def print_collections(member):
    print_section("COLLECTIONS")
    collections = member.get("collection", {})
    if not collections:
        print("  Collections API disabled or no data")
        return

    # Sort by count descending, show top items
    sorted_colls = sorted(collections.items(), key=lambda x: x[1], reverse=True)

    print(f"  Total unique items collected: {len(sorted_colls)}")
    print(f"\n  Top 20 collections:")
    for name, count in sorted_colls[:20]:
        dn = name.replace("_", " ").title()
        print(f"    {dn:30s} {format_number(count):>10s}")

    # Close to next tier
    # Tiers auto-unlock based on count, so calculate current tier directly
    # from the collection count + tier thresholds (don't rely on unlocked_coll_tiers).
    if COLLECTION_TIERS:
        close_to_next = []
        for item_id, count in collections.items():
            tier_data = COLLECTION_TIERS.get(item_id, {})
            tiers = tier_data.get("tiers", [])
            if not tiers:
                continue
            # Find highest tier where count >= amountRequired
            current_tier = 0
            for t in tiers:
                if count >= t["amountRequired"]:
                    current_tier = t["tier"]
                else:
                    break
            # Find next tier after current
            next_tier = None
            for t in tiers:
                if t["tier"] > current_tier:
                    next_tier = t
                    break
            if not next_tier:
                continue
            required = next_tier["amountRequired"]
            if required <= 0:
                continue
            progress = count / required
            if progress >= 0.40:
                unlocks = next_tier.get("unlocks", [])
                reward = unlocks[0] if unlocks else ""
                close_to_next.append({
                    "name": tier_data.get("name", item_id),
                    "tier": next_tier["tier"],
                    "count": count,
                    "required": required,
                    "progress": progress,
                    "reward": reward,
                })

        close_to_next.sort(key=lambda x: x["progress"], reverse=True)
        if close_to_next:
            print(f"\n  Close to Next Tier:")
            for c in close_to_next[:10]:
                name = c["name"]
                tier = c["tier"]
                count_str = format_number(c["count"])
                req_str = format_number(c["required"])
                pct = c["progress"] * 100
                reward = c["reward"]
                reward_str = f"  \u2192 {reward}" if reward else ""
                print(f"    {name:20s} Tier {tier:>2d}   {count_str:>6s}/{req_str:<6s} ({pct:.0f}%){reward_str}")


def print_misc(member, profile):
    print_section("GENERAL")

    # First Join
    first_join_ts = member.get("profile", {}).get("first_join")
    if first_join_ts:
        dt = datetime.fromtimestamp(first_join_ts / 1000, tz=timezone.utc)
        days_ago = (datetime.now(timezone.utc) - dt).days
        print(f"  First Join:     {dt.strftime('%Y-%m-%d')} ({days_ago} days ago)")

    # Fairy souls (v2: nested under fairy_soul)
    fairy_data = member.get("fairy_soul", {})
    fairy = fairy_data.get("total_collected", member.get("fairy_souls_collected", 0))
    fairy_unspent = fairy_data.get("unspent_souls", 0)
    fairy_exchanges = fairy_data.get("fairy_exchanges", 0)
    unspent_str = f"  ({fairy_unspent} unspent)" if fairy_unspent else ""
    print(f"  Fairy Souls:    {fairy}/253{unspent_str}")

    # Purse (v2: nested under currencies)
    currencies = member.get("currencies", {})
    purse = currencies.get("coin_purse", member.get("coin_purse", 0))
    print(f"  Purse:          {format_number(purse)}")

    # Motes
    motes = currencies.get("motes_purse", 0)
    if motes:
        print(f"  Motes:          {format_number(motes)}")

    # Bank
    banking = profile.get("banking", {})
    bank = banking.get("balance", None)
    if bank is not None:
        print(f"  Bank:           {format_number(bank)}")
    else:
        print(f"  Bank:           (not in API — check Banking API setting in-game)")

    # Essence
    essence_data = member.get("currencies", {}).get("essence", {})
    if essence_data:
        essence_parts = []
        for etype in ["WITHER", "UNDEAD", "DRAGON", "GOLD", "DIAMOND", "ICE", "SPIDER", "CRIMSON"]:
            count = essence_data.get(etype, {}).get("current", 0)
            if count > 0:
                essence_parts.append(f"{etype} {format_number(count)}")
        if essence_parts:
            print(f"  Essence:        {', '.join(essence_parts)}")

    # SkyBlock level
    leveling = member.get("leveling", {})
    sb_xp = leveling.get("experience", 0)
    sb_level = int(sb_xp / 100)
    print(f"  SkyBlock Level: {sb_level} ({format_number(sb_xp)} XP)")

    # Cookie buff
    cookie_active = member.get("profile", {}).get("cookie_buff_active", False)
    print(f"  Cookie Buff:    {'Active' if cookie_active else 'Inactive'}")

    # Bestiary
    bestiary = member.get("bestiary", {})
    if bestiary:
        bestiary_kills = bestiary.get("kills", {})
        total_kills = sum(int(v) for v in bestiary_kills.values() if str(v).isdigit()) if bestiary_kills else 0
        if total_kills:
            print(f"  Bestiary Kills: {format_number(total_kills)}")

    # Accessory bag
    accessory_bag = member.get("accessory_bag_storage", {})
    if accessory_bag:
        highest_mp = accessory_bag.get("highest_magical_power", 0)
        if highest_mp:
            print(f"  Magical Power:  {highest_mp}")

        # Selected power
        selected_power = accessory_bag.get("selected_power", "")
        if selected_power:
            unlocked = accessory_bag.get("unlocked_powers", [])
            unlocked_str = f" (unlocked: {', '.join(p.capitalize() for p in unlocked)})" if unlocked else ""
            print(f"  Power:          {selected_power.capitalize()}{unlocked_str}")

        # Tuning
        tuning = accessory_bag.get("tuning", {})
        if tuning:
            tuning_parts = []
            for slot_key, slot_data in sorted(tuning.items()):
                if isinstance(slot_data, dict):
                    for stat, val in slot_data.items():
                        if val > 0:
                            tuning_parts.append(f"{stat.replace('_', ' ').title()} +{val}")
            if tuning_parts:
                print(f"  Tuning:         {', '.join(tuning_parts)}")



def print_minions(member):
    crafted = member.get("player_data", {}).get("crafted_generators", member.get("crafted_generators", []))
    if not crafted:
        return

    print_section("MINIONS")
    # Each tier of each minion type counts as a unique craft for minion slot unlocks
    total_crafts = len(crafted)

    # Group by type for display
    minions = {}
    for entry in crafted:
        parts = entry.rsplit("_", 1)
        if len(parts) == 2:
            name, tier = parts[0], int(parts[1])
            if name not in minions:
                minions[name] = []
            minions[name].append(tier)

    for name in minions:
        minions[name].sort()

    sorted_minions = sorted(minions.items(), key=lambda x: max(x[1]), reverse=True)
    print(f"  Unique minion crafts: {total_crafts} ({len(sorted_minions)} types)")

    for name, tiers in sorted_minions:
        display = name.replace("_", " ").title()
        tier_str = ", ".join(str(t) for t in tiers)
        print(f"    {display:25s} Tiers: {tier_str}")


def print_garden(garden_data):
    if not garden_data or not garden_data.get("success"):
        return
    garden = garden_data.get("garden", {})
    if not garden:
        return

    print_section("GARDEN")
    garden_xp = garden.get("garden_experience", 0)
    # Garden level: 0-4 XP per level at low levels, scales up
    print(f"  Garden XP:      {format_number(garden_xp)}")

    plots = garden.get("unlocked_plots_ids", [])
    print(f"  Plots Unlocked: {len(plots)}")

    crops = garden.get("resources_collected", {})
    if crops:
        sorted_crops = sorted(crops.items(), key=lambda x: x[1], reverse=True)
        print(f"  Crops Collected:")
        for crop, count in sorted_crops[:10]:
            display = crop.replace("_", " ").title()
            print(f"    {display:25s} {format_number(count):>10s}")

    upgrades = garden.get("crop_upgrade_levels", {})
    if upgrades:
        sorted_upgrades = sorted(upgrades.items(), key=lambda x: x[1], reverse=True)
        upgrade_strs = [f"{k.replace('_', ' ').title()} {v}" for k, v in sorted_upgrades]
        print(f"  Crop Upgrades:  {', '.join(upgrade_strs)}")

    composter = garden.get("composter_data", {})
    if composter:
        organic = composter.get("organic_matter", 0)
        fuel = composter.get("fuel_units", 0)
        compost = composter.get("compost_units", 0)
        if organic or fuel or compost:
            print(f"  Composter:      {format_number(organic)} organic, {format_number(fuel)} fuel, {format_number(compost)} compost")

    commissions = garden.get("commission_data", {})
    if commissions:
        total = commissions.get("total_completed", 0)
        unique = commissions.get("unique_npcs_served", 0)
        if total:
            print(f"  Visitors:       {total} completed, {unique} unique NPCs")


def print_museum(museum_data, uuid):
    if not museum_data or not museum_data.get("success"):
        return
    # Museum response has members keyed by UUID
    members = museum_data.get("members", {})
    member_museum = None
    for key, val in members.items():
        if key.replace("-", "") == uuid:
            member_museum = val
            break
    if not member_museum:
        return

    print_section("MUSEUM")
    value = member_museum.get("value", 0)
    items = member_museum.get("items", {})
    special = member_museum.get("special", [])
    print(f"  Museum Value:   {format_number(value)}")
    print(f"  Items Donated:  {len(items)}")
    if special:
        print(f"  Special Items:  {len(special)}")


def print_rift(member):
    print_section("RIFT PROGRESS")
    rift = member.get("rift", {})
    if not rift:
        print("  No Rift data (haven't entered the Rift yet)")
        return

    # Access & charge tracking
    access = rift.get("access", {})
    if access:
        charge_ts = access.get("charge_track_timestamp")
        if charge_ts:
            import time as _time
            elapsed_sec = _time.time() - (charge_ts / 1000)
            elapsed_hours = elapsed_sec / 3600
            CHARGE_COOLDOWN_HOURS = 4
            MAX_CHARGES = 3
            charges_regenerated = int(elapsed_hours / CHARGE_COOLDOWN_HOURS)
            charges_available = min(charges_regenerated, MAX_CHARGES)
            if charges_available >= MAX_CHARGES:
                charge_str = f"{charges_available}/{MAX_CHARGES} (full)"
            else:
                next_charge_sec = (CHARGE_COOLDOWN_HOURS * 3600) - (elapsed_sec % (CHARGE_COOLDOWN_HOURS * 3600))
                next_m, next_s = divmod(int(next_charge_sec), 60)
                next_h, next_m = divmod(next_m, 60)
                charge_str = f"{charges_available}/{MAX_CHARGES} (next in {next_h}h {next_m:02d}m)"
            print(f"  Rift access:    Unlocked — Free entries: {charge_str}")
            print(f"                  (Can also buy: 32 Grand XP Bottles ~144K or 200 Bits per entry)")
        else:
            print("  Rift access:    Unlocked")

    # Wizard Tower quest
    wizard = rift.get("wizard_tower", {})
    wiz_step = wizard.get("wizard_quest_step", 0)
    if wiz_step:
        print(f"  Wizard Quest:   Step {wiz_step}")
    crumbs = wizard.get("crumbs_laid_out", 0)
    if crumbs:
        print(f"  Wizard Crumbs:  {crumbs}")

    # Enigma souls
    enigma = rift.get("enigma", {})
    found_souls = enigma.get("found_souls", [])
    bought_cloak = enigma.get("bought_cloak", False)
    claimed_bonus = enigma.get("claimed_bonus_index", 0)
    if found_souls:
        print(f"  Enigma Souls:   {len(found_souls)}/52 found")
    if bought_cloak:
        print(f"  Enigma Cloak:   Purchased")

    # Dead cats (Montezuma quest)
    dead_cats = rift.get("dead_cats", {})
    found_cats = dead_cats.get("found_cats", [])
    has_detector = dead_cats.get("picked_up_detector", False)
    unlocked_pet = dead_cats.get("unlocked_pet", False)
    if found_cats or has_detector:
        pet_str = " (Montezuma unlocked)" if unlocked_pet else ""
        print(f"  Dead Cats:      {len(found_cats)}/9 found{pet_str}")

    # Wyld Woods
    wyld = rift.get("wyld_woods", {})
    bughunter = wyld.get("bughunter_step", 0)
    sirius_done = wyld.get("sirius_q_a_chain_done", False)
    if bughunter:
        print(f"  Bughunter:      Step {bughunter}")
    if sirius_done:
        print(f"  Sirius Q&A:     Complete")

    # Black Lagoon
    lagoon = rift.get("black_lagoon", {})
    if lagoon:
        delivered_eyes = lagoon.get("delivered_eyes", {})
        if delivered_eyes:
            print(f"  Black Lagoon:   {len(delivered_eyes)} eye types delivered")
        received_paper = lagoon.get("received_science_paper", False)
        delivered_paper = lagoon.get("delivered_science_paper", False)
        if received_paper or delivered_paper:
            if delivered_paper:
                print(f"  Science Paper:  Delivered")
            elif received_paper:
                print(f"  Science Paper:  Received (not delivered)")

    # Gallery (Elise / timecharm securing)
    gallery = rift.get("gallery", {})
    elise_step = gallery.get("elise_step", 0)
    secured = gallery.get("secured_trophies", [])
    if elise_step or secured:
        secured_str = f", {len(secured)} timecharm(s) secured" if secured else ""
        print(f"  Gallery:        Elise step {elise_step}{secured_str}")

    # Dreadfarm
    dreadfarm = rift.get("dreadfarm", {})
    if dreadfarm:
        shania = dreadfarm.get("shania_stage", 0)
        if shania:
            print(f"  Dreadfarm:      Shania stage {shania}")

    # Village Plaza
    plaza = rift.get("village_plaza", {})
    if plaza:
        murder = plaza.get("murder", {})
        if murder.get("step_index", 0):
            print(f"  Murder Mystery: Step {murder['step_index']}")

    # Castle
    castle = rift.get("castle", {})
    if castle:
        grubber = castle.get("grubber_stacks", 0)
        if grubber:
            print(f"  Castle Grubber: {grubber} stacks")

    # Purchased boundaries
    boundaries = rift.get("lifetime_purchased_boundaries", [])
    if boundaries:
        boundary_names = [b.replace("_", " ").title() for b in boundaries]
        print(f"  Paid Entries:   {', '.join(boundary_names)}")

    # Rift lifetime stats
    rift_stats = member.get("player_stats", {}).get("rift", {})
    if rift_stats:
        visits = int(rift_stats.get("visits", 0))
        lifetime_motes = int(rift_stats.get("lifetime_motes_earned", 0))
        parts = []
        if visits:
            parts.append(f"{visits} visits")
        if lifetime_motes:
            parts.append(f"{format_number(lifetime_motes)} lifetime motes")
        if parts:
            print(f"  Rift Stats:     {', '.join(parts)}")

    # Vampire slayer (check slayer data)
    slayer_data = member.get("slayer", {}).get("slayer_bosses", {}).get("vampire", {})
    vamp_xp = slayer_data.get("xp", 0)
    if vamp_xp > 0:
        print(f"  Vampire Slayer: {format_number(vamp_xp)} XP")


def decode_nbt_inventory(b64_data):
    """Decode a base64-encoded gzipped NBT inventory blob.

    Returns (item_ids, total_slots) where total_slots is the inventory size.
    """
    if not b64_data:
        return [], 0
    try:
        raw = gzip.decompress(base64.b64decode(b64_data))
        text = raw.decode("latin-1")
        items = re.findall(r"[\x00-\x1f]id[\x00-\x1f]{1,3}([A-Z][A-Z0-9_]{3,50})", text)
        # Slot count is a big-endian int32 at offset 8 in the NBT
        # (after root TAG_Compound + TAG_List header for "i")
        total_slots = struct.unpack(">i", raw[8:12])[0] if len(raw) >= 12 else 0
        return items, total_slots
    except Exception:
        return [], 0


class NBTReader:
    """Minimal NBT parser for extracting item IDs from inventory blobs."""

    def __init__(self, data):
        self.data = data
        self.pos = 0

    def read_byte(self):
        val = self.data[self.pos]
        self.pos += 1
        return val

    def read_short(self):
        val = struct.unpack_from(">h", self.data, self.pos)[0]
        self.pos += 2
        return val

    def read_int(self):
        val = struct.unpack_from(">i", self.data, self.pos)[0]
        self.pos += 4
        return val

    def read_string(self):
        length = self.read_short()
        val = self.data[self.pos:self.pos + length].decode("utf-8", errors="replace")
        self.pos += length
        return val

    def skip_tag_value(self, tag_type):
        if tag_type == 1:    self.pos += 1       # Byte
        elif tag_type == 2:  self.pos += 2       # Short
        elif tag_type == 3:  self.pos += 4       # Int
        elif tag_type == 4:  self.pos += 8       # Long
        elif tag_type == 5:  self.pos += 4       # Float
        elif tag_type == 6:  self.pos += 8       # Double
        elif tag_type == 7:  self.pos += self.read_int()  # Byte Array
        elif tag_type == 8:                      # String
            length = self.read_short()
            self.pos += length
        elif tag_type == 9:                      # List
            elem_type = self.read_byte()
            count = self.read_int()
            for _ in range(count):
                self.skip_tag_value(elem_type)
        elif tag_type == 10:                     # Compound
            self._skip_compound()
        elif tag_type == 11: self.pos += self.read_int() * 4  # Int Array
        elif tag_type == 12: self.pos += self.read_int() * 8  # Long Array

    def _skip_compound(self):
        while True:
            tag_type = self.read_byte()
            if tag_type == 0:
                break
            self.read_string()  # tag name
            self.skip_tag_value(tag_type)

    def _read_string_list(self):
        """Read a TAG_List of TAG_String and return as a Python list."""
        elem_type = self.read_byte()
        count = self.read_int()
        if elem_type != 8:  # Not strings — skip
            for _ in range(count):
                self.skip_tag_value(elem_type)
            return []
        return [self.read_string() for _ in range(count)]

    def read_compound_find_id(self):
        """Read a TAG_Compound and find the SkyBlock item 'id' at any nesting depth.

        Returns a dict with: id, reforge, enchants, stars, hpb, lore.
        """
        item_info = {}
        while True:
            tag_type = self.read_byte()
            if tag_type == 0:
                break
            name = self.read_string()
            if tag_type == 8 and name == "id":
                val = self.read_string()
                # SkyBlock item IDs are uppercase (e.g., SHADOW_ASSASSIN_BOOTS)
                # Minecraft IDs are lowercase namespaced (e.g., minecraft:diamond_sword)
                if val and val[0].isupper():
                    item_info["id"] = val
            elif tag_type == 8 and name == "modifier":
                item_info["reforge"] = self.read_string()
            elif tag_type == 3 and name == "upgrade_level":
                item_info["stars"] = self.read_int()
            elif tag_type == 3 and name == "hot_potato_count":
                item_info["hpb"] = self.read_int()
            elif tag_type == 10 and name == "enchantments":
                item_info["enchants"] = self._read_compound_as_dict()
            elif tag_type == 9 and name == "Lore":
                item_info["lore"] = self._read_string_list()
            elif tag_type == 10:
                nested = self.read_compound_find_id()
                if nested:
                    # Merge nested results, but don't overwrite existing
                    for k, v in nested.items():
                        if k not in item_info:
                            item_info[k] = v
            else:
                self.skip_tag_value(tag_type)
        return item_info

    def _read_compound_as_dict(self):
        """Read a TAG_Compound and return all entries as {name: value} for simple types."""
        result = {}
        while True:
            tag_type = self.read_byte()
            if tag_type == 0:
                break
            name = self.read_string()
            if tag_type == 3:  # Int (enchantment levels)
                result[name] = self.read_int()
            elif tag_type == 2:  # Short
                result[name] = self.read_short()
            elif tag_type == 8:  # String
                result[name] = self.read_string()
            else:
                self.skip_tag_value(tag_type)
        return result


def decode_nbt_inventory_slots(b64_data):
    """Decode NBT inventory and return a list of item info dicts indexed by slot.

    Returns (slot_list, total_slots) where slot_list[i] is an item dict or None.
    Each dict has: id, reforge, enchants, stars, hpb (all optional).
    """
    if not b64_data:
        return [], 0
    try:
        raw = gzip.decompress(base64.b64decode(b64_data))
        reader = NBTReader(raw)

        # Root TAG_Compound header
        reader.read_byte()    # type (10)
        reader.read_string()  # name (empty)

        # Find the TAG_List named "i"
        while True:
            tag_type = reader.read_byte()
            if tag_type == 0:
                return [], 0
            name = reader.read_string()
            if tag_type == 9 and name == "i":
                elem_type = reader.read_byte()  # 10 (TAG_Compound)
                count = reader.read_int()
                slot_items = []
                for _ in range(count):
                    item_info = reader.read_compound_find_id()
                    slot_items.append(item_info if item_info.get("id") else None)
                return slot_items, count
            else:
                reader.skip_tag_value(tag_type)
    except Exception:
        return [], 0


def decode_wardrobe_slots(b64_data):
    """Decode wardrobe NBT and group items by wardrobe slot.

    Wardrobe layout: pages of 36 slots each (9 helmets + 9 chests + 9 legs + 9 boots).
    Returns dict of {slot_number: [helmet_dict, chest_dict, legs_dict, boots_dict]}.
    """
    slot_items, total_slots = decode_nbt_inventory_slots(b64_data)
    if not slot_items or total_slots == 0:
        return {}

    slots_per_page = 9
    page_size = slots_per_page * 4  # 36
    num_pages = total_slots // page_size

    def get_item(idx):
        return slot_items[idx] if 0 <= idx < len(slot_items) else None

    wardrobe_sets = {}
    for page in range(num_pages):
        for slot_in_page in range(slots_per_page):
            slot_num = page * slots_per_page + slot_in_page + 1  # 1-indexed
            base = page * page_size
            armor_set = [
                get_item(base + slot_in_page),                          # helmet
                get_item(base + slots_per_page + slot_in_page),         # chestplate
                get_item(base + 2 * slots_per_page + slot_in_page),     # leggings
                get_item(base + 3 * slots_per_page + slot_in_page),     # boots
            ]
            if any(piece is not None for piece in armor_set):
                wardrobe_sets[slot_num] = armor_set

    return wardrobe_sets


def parse_rarity_from_lore(lore):
    """Extract the rarity tag string from item lore (last line, strip §-codes)."""
    if not lore:
        return None
    last = lore[-1]
    # Strip Minecraft color/formatting codes (§ followed by any character)
    cleaned = re.sub(r"§.", "", last).strip()
    return cleaned if cleaned else None


def format_item(item_info, detailed=True):
    """Format an item dict into a display string.

    If detailed=True, shows reforge, enchants, stars, HPBs.
    If detailed=False, shows just ID + reforge.
    """
    if not item_info or not item_info.get("id"):
        return None
    parts = [item_info["id"]]

    rarity = parse_rarity_from_lore(item_info.get("lore"))
    if rarity:
        parts.append(f"[{rarity.title()}]")

    reforge = item_info.get("reforge")
    if reforge:
        parts.append(f"[{reforge.capitalize()}]")

    if detailed:
        stars = item_info.get("stars")
        if stars:
            parts.append(f"[{stars}\u2605]")

        hpb = item_info.get("hpb")
        if hpb:
            parts.append(f"[{hpb} HPB]")

        enchants = item_info.get("enchants")
        if enchants:
            enc_strs = [f"{k.replace('_', ' ').title()} {v}" for k, v in sorted(enchants.items())]
            # Show up to 5 enchants inline, summarize rest
            if len(enc_strs) <= 5:
                parts.append(f"[{', '.join(enc_strs)}]")
            else:
                parts.append(f"[{', '.join(enc_strs[:5])}, +{len(enc_strs) - 5} more]")

    return " ".join(parts)


def print_inventories(member):
    print_section("INVENTORIES")
    inv = member.get("inventory", {})

    # Sections that get full item details via NBTReader
    detail_sections = [
        ("Armor", inv.get("inv_armor", {}).get("data", "")),
        ("Equipment", inv.get("equipment_contents", {}).get("data", "")),
        ("Inventory", inv.get("inv_contents", {}).get("data", "")),
    ]

    # Sections that get compact display (ID + reforge only)
    compact_sections = [
        ("Accessory Bag", inv.get("bag_contents", {}).get("talisman_bag", {}).get("data", "")),
    ]

    # Ender chest and backpacks get full detail
    ender_data = inv.get("ender_chest_contents", {}).get("data", "")
    if ender_data:
        detail_sections.append(("Ender Chest", ender_data))

    backpacks = inv.get("backpack_contents", {})
    for slot in sorted(backpacks.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        bp_data = backpacks[slot].get("data", "") if isinstance(backpacks[slot], dict) else ""
        if bp_data:
            detail_sections.append((f"Backpack {slot}", bp_data))

    # Personal vault
    vault_data = inv.get("personal_vault_contents", {}).get("data", "")
    if vault_data:
        detail_sections.append(("Personal Vault", vault_data))

    # Fishing bag
    fishing_data = inv.get("bag_contents", {}).get("fishing_bag", {}).get("data", "")
    if fishing_data:
        detail_sections.append(("Fishing Bag", fishing_data))

    # Quiver
    quiver_data = inv.get("bag_contents", {}).get("quiver", {}).get("data", "")
    if quiver_data:
        detail_sections.append(("Quiver", quiver_data))

    # Detailed sections — one item per line with full info
    for label, data in detail_sections:
        slot_items, total_slots = decode_nbt_inventory_slots(data)
        items = [i for i in slot_items if i]
        if items:
            print(f"  {label}:")
            for item in items:
                formatted = format_item(item, detailed=True)
                if formatted:
                    print(f"    {formatted}")

    # Compact sections — comma-separated with reforge only
    for label, data in compact_sections:
        slot_items, total_slots = decode_nbt_inventory_slots(data)
        items = [i for i in slot_items if i]
        if items:
            formatted = [format_item(i, detailed=False) for i in items]
            formatted = [f for f in formatted if f]
            print(f"  {label} ({len(formatted)}/{total_slots} slots): {', '.join(formatted)}")

    # Wardrobe — compact (just IDs)
    wardrobe_data = inv.get("wardrobe_contents", {}).get("data", "")
    wardrobe_equipped = inv.get("wardrobe_equipped_slot", -1)
    if wardrobe_data:
        wardrobe_sets = decode_wardrobe_slots(wardrobe_data)
        if wardrobe_sets:
            equipped_str = f" (slot {wardrobe_equipped} equipped)" if wardrobe_equipped > 0 else ""
            print(f"  Wardrobe{equipped_str}:")
            for slot_num, armor_set in sorted(wardrobe_sets.items()):
                pieces = [p.get("id", "?") if isinstance(p, dict) else str(p) for p in armor_set if p]
                if pieces:
                    print(f"    Slot {slot_num}: {', '.join(pieces)}")


def print_sacks(member):
    print_section("SACK CONTENTS")
    sacks = member.get("inventory", {}).get("sacks_counts", {})
    if not sacks:
        print("  No sack data")
        return

    non_zero = {k: int(v) for k, v in sacks.items() if v > 0}
    if not non_zero:
        print("  All sacks empty")
        return

    for item, count in sorted(non_zero.items(), key=lambda x: x[1], reverse=True):
        display = item.replace("_", " ").title()
        print(f"  {display:30s} {format_number(count):>10s}")


def print_jacob(member):
    print_section("JACOB'S CONTESTS")
    jc = member.get("jacobs_contest", {})
    if not jc:
        print("  No Jacob's contest data")
        return

    contests = jc.get("contests", {})
    print(f"  Contests Participated: {len(contests)}")

    medals = jc.get("medals_inv", {})
    if medals:
        medal_parts = [f"{count} {tier.capitalize()}" for tier, count in medals.items() if count > 0]
        if medal_parts:
            print(f"  Medals: {', '.join(medal_parts)}")

    unique = jc.get("unique_brackets", {})
    if unique:
        for bracket, crops in unique.items():
            crop_names = [c.replace("_", " ").replace(":", " ").title() for c in crops]
            print(f"  Unique {bracket.capitalize()}: {', '.join(crop_names)}")

    bests = jc.get("personal_bests", {})
    if bests:
        print(f"  Personal Bests:")
        for crop, score in sorted(bests.items(), key=lambda x: x[1], reverse=True):
            display = crop.replace("_", " ").replace(":", " ").title()
            print(f"    {display:25s} {format_number(score)}")


def print_crystals(member):
    print_section("CRYSTAL HOLLOWS")
    mc = member.get("mining_core", {})
    crystals = mc.get("crystals", {})
    biomes = mc.get("biomes", {})
    forge = member.get("forge", {}).get("forge_processes", {})

    if not crystals and not biomes and not forge:
        print("  No Crystal Hollows data")
        return

    # Crystals
    if crystals:
        found = []
        not_found = []
        for name, data in sorted(crystals.items()):
            display = name.replace("_crystal", "").replace("_", " ").title()
            if data.get("state") == "FOUND" or data.get("total_found", 0) > 0:
                total = data.get("total_found", 1)
                found.append(f"{display} ({total}x)" if total > 1 else display)
            else:
                not_found.append(display)
        if found:
            print(f"  Crystals Found:  {', '.join(found)}")
        if not_found:
            print(f"  Not Found:       {', '.join(not_found)}")

    # Biomes
    if biomes:
        precursor = biomes.get("precursor", {})
        goblin = biomes.get("goblin", {})
        jungle = biomes.get("jungle", {})
        if precursor:
            parts = precursor.get("parts_delivered", [])
            talked = precursor.get("talked_to_professor", False)
            parts_str = f"{len(parts)} parts delivered" if parts else ""
            prof_str = "talked to professor" if talked else ""
            info = ", ".join(s for s in [parts_str, prof_str] if s)
            if info:
                print(f"  Precursor:       {info}")
        if goblin:
            kq = goblin.get("king_quests_completed", 0)
            if kq:
                print(f"  Goblin King:     {kq} quest(s) completed")
        if jungle:
            temple = jungle.get("jungle_temple_open", False)
            print(f"  Jungle Temple:   {'Open' if temple else 'Not open'}")

    # Forge
    has_forge = False
    for slot_name, slot_data in forge.items():
        if slot_data:
            has_forge = True
            item = slot_data.get("id", "unknown").replace("_", " ").title()
            start = slot_data.get("startTime", 0)
            duration = slot_data.get("notifyAt", 0)
            if start and duration:
                remaining_ms = duration - int(datetime.now(timezone.utc).timestamp() * 1000)
                if remaining_ms > 0:
                    hours = remaining_ms // 3600000
                    mins = (remaining_ms % 3600000) // 60000
                    print(f"  Forge {slot_name}:  {item} — {hours}h {mins}m remaining")
                else:
                    print(f"  Forge {slot_name}:  {item} — READY")
            else:
                print(f"  Forge {slot_name}:  {item}")
    if not has_forge:
        print(f"  Forge:           Empty")


def print_bestiary(member):
    print_section("BESTIARY")
    bestiary = member.get("bestiary", {})
    if not bestiary:
        print("  No bestiary data")
        return

    milestone = bestiary.get("milestone", {})
    last_claimed = milestone.get("last_claimed_milestone", 0)
    if last_claimed:
        print(f"  Last Milestone:  {last_claimed}")

    kills = bestiary.get("kills", {})
    numeric_kills = {k: int(v) for k, v in kills.items() if isinstance(v, (int, float))}
    if numeric_kills:
        top = sorted(numeric_kills.items(), key=lambda x: x[1], reverse=True)[:10]
        print(f"  Top Kills:")
        for mob, count in top:
            display = mob.rsplit("_", 1)[0].replace("_", " ").title() if mob[-1].isdigit() else mob.replace("_", " ").title()
            print(f"    {display:30s} {count:>6d}")

    deaths = bestiary.get("deaths", {})
    numeric_deaths = {k: int(v) for k, v in deaths.items() if isinstance(v, (int, float))}
    if numeric_deaths:
        top_d = sorted(numeric_deaths.items(), key=lambda x: x[1], reverse=True)[:10]
        print(f"  Top Deaths:")
        for mob, count in top_d:
            display = mob.rsplit("_", 1)[0].replace("_", " ").title() if mob[-1].isdigit() else mob.replace("_", " ").title()
            print(f"    {display:30s} {count:>6d}")


def print_player_stats(member):
    print_section("PLAYER STATS (LIFETIME)")
    ps = member.get("player_stats", {})
    pd = member.get("player_data", {})

    # Combat stats
    highest = ps.get("highest_damage", 0)
    highest_crit = ps.get("highest_critical_damage", 0)
    death_count = pd.get("death_count", 0)
    if highest:
        print(f"  Highest Damage:  {format_number(highest)}")
    if highest_crit and highest_crit != highest:
        print(f"  Highest Crit:    {format_number(highest_crit)}")
    if death_count:
        print(f"  Total Deaths:    {death_count}")

    # Items fished
    fished = ps.get("items_fished", {})
    if fished:
        total = int(fished.get("total", 0))
        treasure = int(fished.get("treasure", 0))
        print(f"  Items Fished:    {total} ({treasure} treasure)")

    # Gifts
    gifts = ps.get("gifts", {})
    if gifts:
        received = int(gifts.get("total_received", 0))
        given = int(gifts.get("total_given", 0))
        if received or given:
            print(f"  Gifts:           {received} received, {given} given")

    # Auctions
    auctions = ps.get("auctions", {})
    if auctions:
        created = int(auctions.get("created", 0))
        sold = int(auctions.get("completed", 0))
        earned = auctions.get("gold_earned", 0)
        bought = int(auctions.get("won", 0))
        spent = auctions.get("gold_spent", 0)
        highest_bid = auctions.get("highest_bid", 0)
        print(f"  Auctions:        {created} created, {sold} sold ({format_number(earned)} earned)")
        print(f"                   {bought} bought ({format_number(spent)} spent), highest bid {format_number(highest_bid)}")

    # End island
    end = ps.get("end_island", {})
    if end:
        eyes = int(end.get("summoning_eyes_collected", 0))
        zealot_loot = int(end.get("special_zealot_loot_collected", 0))
        if eyes or zealot_loot:
            print(f"  End Island:      {eyes} summoning eyes, {zealot_loot} special zealot loot")
        dragon = end.get("dragon_fight", {})
        fastest = dragon.get("fastest_kill", {})
        if fastest:
            kills_str = ", ".join(f"{k.capitalize()} {v/1000:.1f}s" for k, v in fastest.items() if k != "best")
            if kills_str:
                print(f"  Dragon Kills:    {kills_str}")

    # Pet milestones
    pet_stats = ps.get("pets", {})
    if pet_stats:
        milestones = pet_stats.get("milestone", {})
        total_pet_xp = pet_stats.get("total_exp_gained", 0)
        if milestones or total_pet_xp:
            parts = []
            ores = int(milestones.get("ores_mined", 0))
            sc = int(milestones.get("sea_creatures_killed", 0))
            if ores:
                parts.append(f"Ores Mined {format_number(ores)}")
            if sc:
                parts.append(f"Sea Creatures {sc}")
            if total_pet_xp:
                parts.append(f"Total XP {format_number(total_pet_xp)}")
            print(f"  Pet Milestones:  {', '.join(parts)}")

    # Misc numeric stats
    glowing = ps.get("glowing_mushrooms_broken", 0)
    sc_kills = ps.get("sea_creature_kills", 0)
    if glowing:
        print(f"  Mushrooms:       {format_number(int(glowing))} glowing mushrooms broken")
    if sc_kills:
        print(f"  Sea Creatures:   {int(sc_kills)} killed")

    # Spooky candy (lifetime counter from player_stats.candy_collected)
    candy = ps.get("candy_collected", {})
    if candy:
        total = int(candy.get("total", 0))
        green = int(candy.get("green_candy", 0))
        purple = int(candy.get("purple_candy", 0))
        if total:
            print(f"  Spooky Candy:    {total} ({green} green, {purple} purple)")

    # Races
    races = ps.get("races", {})
    if races:
        parts = []
        end_race = races.get("end_race_best_time", 0)
        if end_race:
            parts.append(f"End race {end_race/1000:.1f}s")
        dh = races.get("dungeon_hub", {})
        for k, v in dh.items():
            name = k.replace("_best_time", "").replace("_", " ").title()
            parts.append(f"{name} {v/1000:.1f}s")
        if parts:
            print(f"  Races:           {', '.join(parts)}")


def print_foraging_detail(member):
    print_section("FORAGING DETAILS")
    fc = member.get("foraging_core", {})
    fg = member.get("foraging", {})

    if not fc and not fg:
        print("  No foraging data")
        return

    # Forest Whispers
    whispers = fc.get("forests_whispers", 0)
    spent = fc.get("forests_whispers_spent", 0)
    if whispers or spent:
        print(f"  Forest Whispers: {format_number(whispers)} available ({format_number(spent)} spent)")

    # Tree gifts
    tree_gifts = fg.get("tree_gifts", {})
    fig = tree_gifts.get("FIG", 0)
    mangrove = tree_gifts.get("MANGROVE", 0)
    if fig or mangrove:
        print(f"  Tree Gifts:      Fig {fig}, Mangrove {mangrove}")
    milestone = tree_gifts.get("milestone_tier_claimed", {})
    if milestone:
        parts = [f"{k.capitalize()} tier {v}" for k, v in milestone.items()]
        print(f"  Gift Milestones: {', '.join(parts)}")

    # Starlyn personal bests
    starlyn = fg.get("starlyn", {})
    if starlyn:
        bests = starlyn.get("personal_bests", {})
        if bests:
            parts = [f"{k.replace('_', ' ').title()} {format_number(v)}" for k, v in bests.items()]
            print(f"  Starlyn Bests:   {', '.join(parts)}")

    # Hina tasks
    hina = fg.get("hina", {})
    if hina:
        tasks = hina.get("tasks", {})
        claimed = tasks.get("claimed_rewards", [])
        tier = tasks.get("tier_claimed", 0)
        if claimed or tier:
            print(f"  Hina Tasks:      {len(claimed)} rewards claimed, tier {tier}")

    # Harp
    songs = fg.get("songs", {})
    if songs:
        harp = songs.get("harp", {})
        if harp:
            selected = harp.get("selected_song", "")
            best = harp.get(f"song_{selected}_best_completion", 0) if selected else 0
            if selected:
                display = selected.replace("_", " ").title()
                print(f"  Harp:            {display} ({best*100:.0f}% best)")


def print_chocolate(member):
    print_section("CHOCOLATE FACTORY")
    easter = member.get("events", {}).get("easter", {})
    if not easter:
        print("  No chocolate factory data")
        return

    total = easter.get("total_chocolate", 0)
    current = easter.get("chocolate", 0)
    level = easter.get("chocolate_level", 0)
    barn = easter.get("rabbit_barn_capacity_level", 0)

    print(f"  Lifetime:        {format_number(total)}")
    print(f"  Current:         {format_number(current)}")
    print(f"  Level:           {level}")
    print(f"  Barn Capacity:   {barn}")

    # Rabbits
    rabbits = easter.get("rabbits", {})
    # Count rabbit entries (exclude collected_locations and collected_eggs)
    rabbit_count = sum(1 for k, v in rabbits.items()
                       if k not in ("collected_locations", "collected_eggs") and isinstance(v, int) and v > 0)
    if rabbit_count:
        print(f"  Rabbits Found:   {rabbit_count}")

    # Prestige progress
    choc_since_prestige = easter.get("chocolate_since_prestige", 0)
    if total and choc_since_prestige:
        prestige_pct = choc_since_prestige / total * 100 if total else 0
        print(f"  Since Prestige:  {format_number(choc_since_prestige)} ({prestige_pct:.1f}% of lifetime)")

    # Time tower
    tt = easter.get("time_tower", {})
    if tt:
        charges = tt.get("charges", 0)
        tt_level = tt.get("level", 0)
        activation_ts = tt.get("activation_time", 0)
        active_str = ""
        if activation_ts:
            elapsed_ms = int(time.time() * 1000) - activation_ts
            if elapsed_ms < 3600000:  # 1 hour
                remaining_m = (3600000 - elapsed_ms) // 60000
                active_str = f" — ACTIVE ({remaining_m}m remaining)"
            else:
                hours_ago = elapsed_ms / 3600000
                active_str = f" — last activated {hours_ago:.1f}h ago"
        print(f"  Time Tower:      Level {tt_level}, {charges} charges{active_str}")

    # Employees
    employees = easter.get("employees", {})
    if employees:
        emp_str = ", ".join(f"{k.replace('rabbit_', '')} {v}" for k, v in
                           sorted(employees.items(), key=lambda x: x[1], reverse=True))
        print(f"  Employees:       {emp_str}")

    # Collected eggs (egg meals)
    collected_eggs = rabbits.get("collected_eggs", {})
    if collected_eggs:
        egg_names = sorted(collected_eggs.keys())
        print(f"  Egg Meals:       {', '.join(n.capitalize() for n in egg_names)} ({len(egg_names)}/6)")


def print_community(profile):
    print_section("COMMUNITY UPGRADES")
    cu = profile.get("community_upgrades", {})
    if not cu:
        print("  No community upgrade data")
        return

    states = cu.get("upgrade_states", [])
    if states:
        for s in states:
            name = s.get("upgrade", "?").replace("_", " ").title()
            tier = s.get("tier", 0)
            print(f"  Completed:       {name} Tier {tier}")

    current = cu.get("currently_upgrading", {})
    if current:
        name = current.get("upgrade", "?").replace("_", " ").title()
        tier = current.get("new_tier", 0)
        print(f"  In Progress:     {name} Tier {tier}")


def print_misc_extras(member):
    print_section("MISCELLANEOUS")
    pd = member.get("player_data", {})
    ps = member.get("player_stats", {})
    leveling = member.get("leveling", {})

    # BOP bonus
    bop = leveling.get("bop_bonus")
    if bop:
        print(f"  BOP Bonus:       {bop.replace('_', ' ').title()}")

    # Pet score
    pet_score = leveling.get("highest_pet_score", 0)
    if pet_score:
        print(f"  Pet Score:       {pet_score}")

    # Trapper pelts
    pelt_count = member.get("quests", {}).get("trapper_quest", {}).get("pelt_count", 0)
    if pelt_count:
        print(f"  Trapper:         {pelt_count} pelts")

    # Abiphone
    abiphone = member.get("nether_island_player_data", {}).get("abiphone", {})
    if abiphone:
        contacts = abiphone.get("contact_data", {})
        if contacts:
            names = list(contacts.keys())
            print(f"  Abiphone:        {len(names)} contacts ({', '.join(names)})")

    # Crimson Isle / Kuudra
    nether = member.get("nether_island_player_data", {})
    faction = nether.get("selected_faction")
    if faction:
        rep = nether.get("mages_reputation", 0) if faction == "mages" else nether.get("barbarians_reputation", 0)
        print(f"  Faction:         {faction.title()} (rep: {format_number(rep)})")
    kuudra = nether.get("kuudra_completed_tiers", {})
    if kuudra:
        tier_names = {"none": "Basic", "hot": "Hot", "burning": "Burning",
                      "fiery": "Fiery", "infernal": "Infernal"}
        parts = []
        for k, v in kuudra.items():
            if v and v > 0:
                name = tier_names.get(k, k.title())
                parts.append(f"{name}: {v}")
        if parts:
            print(f"  Kuudra:          {', '.join(parts)}")
    dojo = nether.get("dojo", {})
    if dojo:
        # Dojo stores scores as dojo_points_<test> and dojo_time_<test>
        tests = set()
        for key in dojo:
            if key.startswith("dojo_points_"):
                tests.add(key.replace("dojo_points_", ""))
        if tests:
            parts = []
            for test in sorted(tests):
                pts = dojo.get(f"dojo_points_{test}", 0)
                if pts > 0:
                    parts.append(f"{test.title()}: {pts}")
            if parts:
                print(f"  Dojo:            {', '.join(parts)}")

    # Shards
    shards = member.get("shards", {})
    if shards:
        owned = shards.get("owned", [])
        fused = shards.get("fused", 0)
        fused_count = fused if isinstance(fused, int) else len(fused)
        if owned:
            types = [s.get("type", "?").replace("_", " ").title() for s in owned]
            print(f"  Shards:          {len(owned)} types ({', '.join(types)}), {fused_count} fused")

    # Experimentation (3 table types: Superpairs, Chronomatron, Ultrasequencer)
    exp = member.get("experimentation", {})
    if exp:
        pairings = exp.get("pairings", {})
        exp_names = {0: "Superpairs", 1: "Chronomatron", 2: "Ultrasequencer"}
        exp_parts = []
        total_claims = 0
        for i in range(3):
            c = pairings.get(f"claims_{i}", 0)
            if c:
                total_claims += c
                best = pairings.get(f"best_score_{i}", 0)
                exp_parts.append(f"{exp_names[i]}: {c} claims (best {best})")
        if total_claims:
            print(f"  Experimentation: {total_claims} total claims")
            for part in exp_parts:
                print(f"    {part}")
        # Experimentation cooldown
        charge_ts = exp.get("charge_track_timestamp", 0)
        if charge_ts:
            elapsed_ms = int(time.time() * 1000) - charge_ts
            # Experiments recharge every 24h, check if ready
            hours_since = elapsed_ms / 3600000
            if hours_since >= 24:
                print(f"    Experiments: READY ({hours_since:.0f}h since last)")
            else:
                remaining_h = 24 - hours_since
                print(f"    Experiments: {remaining_h:.1f}h until ready")

    # Attribute stacks
    attr_stacks = member.get("attributes", {}).get("stacks", {})
    if attr_stacks:
        total_stacks = sum(attr_stacks.values())
        top_5 = sorted(attr_stacks.items(), key=lambda x: x[1], reverse=True)[:5]
        top_str = ", ".join(f"{k.replace('_', ' ').title()} {v}" for k, v in top_5)
        print(f"  Attributes:      {len(attr_stacks)} types, {total_stacks} total — top: {top_str}")

    # Perks
    perks = pd.get("perks", {})
    if perks:
        perk_names = [k.replace("_", " ").title() for k in perks.keys()]
        print(f"  Perks:           {', '.join(perk_names)}")

    # Garden copper
    garden_pd = member.get("garden_player_data", {})
    copper = garden_pd.get("copper", 0)
    if copper:
        print(f"  Garden Copper:   {copper}")

    # Objectives
    objectives = member.get("objectives", {})
    if objectives:
        completed = sum(1 for v in objectives.values() if isinstance(v, dict) and v.get("status") == "COMPLETE")
        print(f"  Objectives:      {completed}/{len(objectives)} completed")

    # Visited zones
    zones = pd.get("visited_zones", [])
    if zones:
        print(f"  Zones Visited:   {len(zones)}")

    # Fishing treasure
    fishing_treasure = pd.get("fishing_treasure_caught", 0)
    if fishing_treasure:
        print(f"  Fishing Treasure:{fishing_treasure} caught")

    # Quiver
    inv = member.get("inventory", {})
    quiver_data = inv.get("bag_contents", {}).get("quiver", {}).get("data", "")
    if quiver_data:
        items, _ = decode_nbt_inventory(quiver_data)
        if items:
            counts = Counter(items)
            parts = [f"{count}x {name}" for name, count in counts.items()]
            print(f"  Quiver:          {', '.join(parts)}")

    # Garden chips
    chips = pd.get("garden_chips", {})
    if chips:
        chip_names = [k.replace("_", " ").title() for k in chips.keys()]
        print(f"  Garden Chips:    {', '.join(chip_names)}")


def collect_gear_ids(member):
    """Extract all unique item IDs from armor, equipment, inventory, and accessories."""
    inv = member.get("inventory", {})
    item_ids = set()

    sections = [
        inv.get("inv_armor", {}).get("data", ""),
        inv.get("equipment_contents", {}).get("data", ""),
        inv.get("inv_contents", {}).get("data", ""),
        inv.get("bag_contents", {}).get("talisman_bag", {}).get("data", ""),
    ]

    # Ender chest
    ender_data = inv.get("ender_chest_contents", {}).get("data", "")
    if ender_data:
        sections.append(ender_data)

    # Wardrobe
    wardrobe_data = inv.get("wardrobe_contents", {}).get("data", "")
    if wardrobe_data:
        sections.append(wardrobe_data)

    for data in sections:
        slot_items, _ = decode_nbt_inventory_slots(data)
        for item in slot_items:
            if item and item.get("id"):
                item_ids.add(item["id"])

    return item_ids


# Common upgrade targets by progression stage
UPGRADE_TARGETS = {
    "pre_dungeon": [
        # Dragon armor
        "YOUNG_DRAGON_CHESTPLATE", "YOUNG_DRAGON_LEGGINGS", "YOUNG_DRAGON_BOOTS",
        "STRONG_DRAGON_CHESTPLATE", "STRONG_DRAGON_LEGGINGS", "STRONG_DRAGON_BOOTS",
        "UNSTABLE_DRAGON_CHESTPLATE", "UNSTABLE_DRAGON_LEGGINGS", "UNSTABLE_DRAGON_BOOTS",
        # Weapons
        "ASPECT_OF_THE_DRAGON", "JUJU_SHORTBOW",
    ],
    "early_dungeon": [
        "SHADOW_ASSASSIN_CHESTPLATE", "SHADOW_ASSASSIN_LEGGINGS",
        "SHADOW_ASSASSIN_BOOTS", "BONZO_MASK",
        "SPIRIT_SCEPTRE", "BONZO_STAFF", "LIVID_DAGGER",
        "SHADOW_FURY", "SPIRIT_BOOTS",
    ],
    "mid_dungeon": [
        "POWER_WITHER_CHESTPLATE", "POWER_WITHER_LEGGINGS", "POWER_WITHER_BOOTS",
        "TANK_WITHER_CHESTPLATE", "TANK_WITHER_LEGGINGS", "TANK_WITHER_BOOTS",
        "WISE_WITHER_CHESTPLATE", "WISE_WITHER_LEGGINGS", "WISE_WITHER_BOOTS",
        "WITHER_CLOAK", "HYPERION", "SCYLLA", "ASTRAEA", "VALKYRIE",
    ],
    "slayer": [
        "REVENANT_CHESTPLATE", "REVENANT_LEGGINGS", "REVENANT_BOOTS",
        "TARANTULA_HELMET", "TARANTULA_CHESTPLATE", "TARANTULA_LEGGINGS", "TARANTULA_BOOTS",
        "FINAL_DESTINATION_HELMET", "FINAL_DESTINATION_CHESTPLATE",
        "FINAL_DESTINATION_LEGGINGS", "FINAL_DESTINATION_BOOTS",
    ],
    "mining": [
        "SORROW_HELMET", "SORROW_CHESTPLATE", "SORROW_LEGGINGS", "SORROW_BOOTS",
        "DIVAN_HELMET", "DIVAN_CHESTPLATE", "DIVAN_LEGGINGS", "DIVAN_BOOTS",
    ],
    "equipment": [
        # Necklaces
        "LAVA_SHELL_NECKLACE", "MOLTEN_NECKLACE",
        # Cloaks
        "MOLTEN_CLOAK",
        # Belts
        "IMPLOSION_BELT", "MOLTEN_BELT",
        # Gloves
        "GAUNTLET_OF_CONTAGION", "SOULWEAVER_GLOVES", "MOLTEN_BRACELET",
    ],
}


def print_craft_flips(member, price_cache):
    """Print profitable craft flips filtered by player unlocks."""
    print_section("CRAFT FLIPS")

    # Load craft cache — reads Moulberry bulk data (no API calls)
    craft_cache = load_craft_cache()
    mb = craft_cache.get("moulberry", {})
    avg_lbin = mb.get("avg_lbin", {})
    auction_averages = mb.get("auction_averages", {})
    lowestbin = mb.get("lowestbin", {})
    cache_ts = mb.get("ts", 0)
    cache_age = time.time() - cache_ts if cache_ts else None

    if not avg_lbin or (cache_age and cache_age > 86400):
        print("  Run 'python3 crafts.py' to scan craft flips")
        return

    # Parse recipes and filter
    all_recipes = parse_recipes()
    all_items, name_to_key = load_collections_data(craft_cache)
    slayer_thresholds = load_slayer_thresholds()

    for recipe in all_recipes:
        if recipe["requirement"]:
            resolve_collection_requirement(recipe["requirement"], name_to_key)
            resolve_slayer_requirement(recipe["requirement"], slayer_thresholds)

    valid = filter_craft_flips(all_recipes, price_cache)

    # Calculate profits using cached Moulberry data
    flips = []
    for recipe in valid:
        item_id = recipe["item_id"]
        cost = calculate_craft_cost(recipe, price_cache)
        if cost is None:
            continue
        item_avg = avg_lbin.get(item_id)
        if not item_avg or item_avg <= 0:
            continue
        avg_data = auction_averages.get(item_id)
        if not avg_data:
            continue
        sales_per_day = avg_data.get("sales", 0) / 3.0
        if sales_per_day < 1:
            continue
        profit = item_avg * 0.99 - cost
        if profit < 10_000:
            continue
        flips.append({
            "item_id": item_id,
            "cost": cost,
            "avg_lbin": item_avg,
            "lbin": lowestbin.get(item_id, 0),
            "profit": profit,
            "sales_per_day": sales_per_day,
            "requirement": recipe["requirement"],
        })

    flips.sort(key=lambda x: x["profit"], reverse=True)

    # Split into unlocked and almost-unlocked
    unlocked = []
    almost = []
    for flip in flips:
        is_ok, progress, needed = check_unlocked(flip["requirement"], member, slayer_thresholds)
        if is_ok:
            unlocked.append(flip)
        elif progress is not None and needed and needed > 0:
            pct = progress / needed
            almost.append({**flip, "progress": progress, "needed": needed, "pct": pct})

    # Top 10 unlocked
    print(f"  Unlocked ({len(unlocked)} total, showing top 10):")
    if unlocked:
        for flip in unlocked[:10]:
            name = display_name(flip["item_id"])
            if len(name) > 28:
                name = name[:25] + "..."
            spd = flip.get("sales_per_day", 0)
            spd_str = f"{spd:.0f}/d" if spd >= 10 else f"{spd:.1f}/d"
            print(f"    {name:<28s} {fmt_price_num(flip['cost']):>8s} -> "
                  f"{fmt_price_num(flip['avg_lbin']):>8s}  "
                  f"profit {fmt_price_num(flip['profit']):>8s}  ({spd_str} sales)")
    else:
        print("    No unlocked profitable crafts found.")

    # Top 5 almost unlocked
    almost.sort(key=lambda x: x["pct"], reverse=True)
    if almost:
        print(f"\n  Almost Unlocked:")
        for flip in almost[:5]:
            name = display_name(flip["item_id"])
            if len(name) > 24:
                name = name[:21] + "..."
            req_text = flip["requirement"]["text"] if flip["requirement"] else ""
            prog_str = f"{format_number(flip['progress'])}/{format_number(flip['needed'])}"
            if flip["requirement"]["type"] == "slayer":
                prog_str += " XP"
            print(f"    {name:<24s} {fmt_price_num(flip['profit']):>8s} profit  "
                  f"{req_text:<22s} {prog_str} ({flip['pct']*100:.0f}%)")

    hours_ago = cache_age / 3600 if cache_age else 0
    print(f"\n  (Prices cached {hours_ago:.1f}h ago. Run 'python3 crafts.py' to refresh)")


def print_market_prices(member, price_cache):
    """Print current market prices for equipped gear and upgrade targets."""
    print_section("MARKET PRICES")

    gear_ids = collect_gear_ids(member)
    if not gear_ids:
        print("  No gear found")
        return

    # Separate into armor/weapons vs accessories for display
    inv = member.get("inventory", {})

    # Get armor + equipment IDs specifically
    armor_data = inv.get("inv_armor", {}).get("data", "")
    equip_data = inv.get("equipment_contents", {}).get("data", "")
    armor_items, _ = decode_nbt_inventory_slots(armor_data)
    equip_items, _ = decode_nbt_inventory_slots(equip_data)
    equipped_ids = set()
    for item in armor_items + equip_items:
        if item and item.get("id"):
            equipped_ids.add(item["id"])

    # Get weapons from inventory (first few slots typically)
    inv_data = inv.get("inv_contents", {}).get("data", "")
    inv_items, _ = decode_nbt_inventory_slots(inv_data)
    weapon_keywords = {"SWORD", "BOW", "BLADE", "DAGGER", "WAND", "STAFF", "SCEPTRE",
                       "SCYTHE", "AXE", "CLEAVER", "ASPECT", "HYPERION", "VALKYRIE",
                       "ASTRAEA", "SCYLLA", "FURY", "AURORA", "ZOMBIE_SWORD"}
    weapon_ids = set()
    for item in inv_items:
        if item and item.get("id"):
            iid = item["id"]
            if any(kw in iid for kw in weapon_keywords):
                weapon_ids.add(iid)

    # Print equipped gear prices
    show_ids = sorted(equipped_ids | weapon_ids)
    if show_ids:
        print("  Current Gear:")
        for item_id in show_ids:
            display = display_name(item_id)
            price_str = price_cache.format_price(item_id)
            print(f"    {display:40s} {price_str}")

    # Accessories
    acc_data = inv.get("bag_contents", {}).get("talisman_bag", {}).get("data", "")
    acc_items, _ = decode_nbt_inventory_slots(acc_data)
    acc_ids = set()
    for item in acc_items:
        if item and item.get("id"):
            acc_ids.add(item["id"])

    if acc_ids:
        # Just show total count and top 5 most expensive
        prices = price_cache.get_prices_bulk(sorted(acc_ids))
        valued = []
        for iid, p in prices.items():
            val = p.get("lowest_bin") or p.get("buy") or 0
            if val > 0:
                valued.append((iid, val, p))
        valued.sort(key=lambda x: x[1], reverse=True)
        total_value = sum(v for _, v, _ in valued)

        print(f"\n  Accessories ({len(acc_ids)} items, ~{fmt_price_num(total_value)} total):")
        for iid, val, p in valued[:5]:
            display = display_name(iid)
            price_str = price_cache.format_price(iid)
            print(f"    {display:40s} {price_str}")
        if len(valued) > 5:
            print(f"    ... and {len(valued) - 5} more")

    # Upgrade targets — show relevant next-tier gear across multiple paths
    has_sa = any("SHADOW_ASSASSIN" in i for i in gear_ids)
    has_necron = any("POWER_WITHER" in i or "WISE_WITHER" in i or "TANK_WITHER" in i
                     or "SPEED_WITHER" in i for i in gear_ids)
    has_dragon = any("DRAGON" in i for i in gear_ids)
    has_slayer_gear = any(k in i for i in gear_ids for k in ("REVENANT", "TARANTULA", "FINAL_DESTINATION"))
    has_mining_gear = any(k in i for i in gear_ids for k in ("SORROW", "DIVAN"))

    target_groups = []
    # Dungeon progression
    if has_necron:
        pass  # already endgame dungeon gear
    elif has_sa:
        target_groups.append(("Dungeon Upgrades", UPGRADE_TARGETS["mid_dungeon"]))
    elif has_dragon:
        target_groups.append(("Dungeon Gear", UPGRADE_TARGETS["early_dungeon"]))
    else:
        target_groups.append(("Combat Gear", UPGRADE_TARGETS["pre_dungeon"]))

    # Slayer gear — always show if they don't have it
    if not has_slayer_gear:
        target_groups.append(("Slayer Gear", UPGRADE_TARGETS["slayer"]))

    # Mining gear — always show if they don't have it
    if not has_mining_gear:
        target_groups.append(("Mining Gear", UPGRADE_TARGETS["mining"]))

    # Equipment upgrades — show if not already wearing Molten set
    has_molten_equip = any("MOLTEN" in i for i in equipped_ids)
    if not has_molten_equip:
        target_groups.append(("Equipment Upgrades", UPGRADE_TARGETS["equipment"]))

    for group_name, group_targets in target_groups:
        targets = [t for t in group_targets if t not in gear_ids]
        if not targets:
            continue
        print(f"\n  {group_name}:")
        for item_id in targets:
            display = display_name(item_id)
            price_str = price_cache.format_price(item_id)
            print(f"    {display:40s} {price_str}")


def main():
    parser = argparse.ArgumentParser(description="Fetch and display Hypixel SkyBlock profile data.")
    parser.add_argument("username", nargs="?", default=os.environ.get("MINECRAFT_USERNAME", ""))
    parser.add_argument("--full", "-f", action="store_true", help="Show all sections")
    parser.add_argument("--section", "-s", type=str, default="", help="Comma-separated extra sections to show")
    args = parser.parse_args()

    USERNAME = args.username
    if not API_KEY:
        print("Error: HYPIXEL_API_KEY not set in .env or environment")
        sys.exit(1)
    if not USERNAME:
        print("Usage: python profile.py [username]")
        print("Or set MINECRAFT_USERNAME in .env")
        sys.exit(1)

    # Determine which sections to show
    if args.full:
        active_sections = set(ALL_SECTIONS)
    else:
        active_sections = set(CORE_SECTIONS)
        if args.section:
            for s in args.section.split(","):
                s = s.strip().lower()
                if s in ALL_SECTIONS:
                    active_sections.add(s)
                else:
                    print(f"Warning: unknown section '{s}'. Available: {', '.join(ALL_SECTIONS)}")

    def show(section):
        return section in active_sections

    print(f"Resolving UUID for {USERNAME}...")
    uuid, display_name = resolve_uuid(USERNAME)
    print(f"Player: {display_name} ({uuid})")

    print("Fetching profiles...")
    data = get_profiles(uuid)

    if not data.get("success") or not data.get("profiles"):
        print("No profiles found!")
        sys.exit(1)

    # Find the selected (active) profile
    profiles = data["profiles"]
    active = None
    for p in profiles:
        if p.get("selected"):
            active = p
            break
    if not active:
        active = profiles[0]

    profile_name = active.get("cute_name", "Unknown")
    game_mode = active.get("game_mode", "normal")
    mode_str = f" ({game_mode})" if game_mode != "normal" else ""
    print(f"Profile: {profile_name}{mode_str}")

    member = active["members"].get(uuid, {})
    if not member:
        # Try with dashes
        formatted = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
        member = active["members"].get(formatted, {})
    if not member:
        # Just grab the first member that looks like ours
        for key, val in active["members"].items():
            if key.replace("-", "") == uuid:
                member = val
                break

    if not member:
        print("Could not find member data in profile!")
        sys.exit(1)

    # Fetch dynamic skill XP tables and collection tiers from the API
    fetch_skill_tables()
    if show("collections"):
        fetch_collection_tiers()

    # Fetch supplementary data
    profile_id = active["profile_id"]
    garden_data = get_garden(profile_id)
    museum_data = get_museum(profile_id)

    # --- Core sections ---
    if show("general"):     print_misc(member, active)
    if show("dailies"):     print_daily_checklist(member)
    if show("skills"):      print_skills(member)
    if show("slayers"):     print_slayers(member)
    if show("dungeons"):    print_dungeons(member)
    if show("hotm"):        print_hotm(member)
    if show("effects"):     print_effects(member)
    if show("pets"):        print_pets(member)
    if show("inventories"): print_inventories(member)

    # --- Extended sections ---
    if show("collections"): print_collections(member)
    if show("minions"):     print_minions(member)
    if show("garden"):      print_garden(garden_data)
    if show("museum"):      print_museum(museum_data, uuid)
    if show("rift"):        print_rift(member)
    if show("sacks"):       print_sacks(member)
    if show("jacob"):       print_jacob(member)
    if show("crystals"):    print_crystals(member)
    if show("bestiary"):    print_bestiary(member)
    if show("stats"):       print_player_stats(member)
    if show("foraging"):    print_foraging_detail(member)
    if show("chocolate"):   print_chocolate(member)
    if show("community"):   print_community(active)
    if show("misc"):        print_misc_extras(member)

    # --- Market prices (always shown) ---
    price_cache = PriceCache()
    print_market_prices(member, price_cache)

    # --- Craft flips (extended) ---
    if show("crafts"):      print_craft_flips(member, price_cache)

    price_cache.flush()

    if not args.full and active_sections == set(CORE_SECTIONS):
        print(f"\n  (Showing core sections only. Use --full for all, or -s section1,section2)")
        print(f"  Extended: {', '.join(EXTENDED_SECTIONS)}")

    # Also dump raw JSON for detailed analysis
    raw_path = Path(__file__).parent.parent / "data" / "last_profile.json"
    raw_data = {
        "player": display_name,
        "uuid": uuid,
        "profile_name": profile_name,
        "profile": active,
        "garden": garden_data,
        "museum": museum_data,
        "market_prices": price_cache.export(),
    }
    raw_path.write_text(json.dumps(raw_data, indent=2))
    print(f"\n{'=' * 60}")
    print(f"  Raw profile data saved to: {raw_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
