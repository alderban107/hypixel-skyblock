#!/usr/bin/env python3
"""Minion profit calculator for Hypixel SkyBlock.

Calculates daily revenue for minion setups using live Bazaar prices.
Supports fuel, Super Compactor 3000, Diamond Spreading, and hopper
configurations. Action speeds are parsed from the NEU repo.

Usage:
    python3 minions.py                              # ranked table, default setup
    python3 minions.py --minions 25                 # set minion count
    python3 minions.py --fuel plasma                # change fuel
    python3 minions.py --no-sc3000                  # disable super compactor
    python3 minions.py --no-diamond                 # disable diamond spreading
    python3 minions.py --npc                        # use NPC prices instead of bazaar
    python3 minions.py --tier 11                    # show specific tier only
    python3 minions.py --item snow                  # detailed view for one minion
    python3 minions.py --item snow --roi            # include setup cost + ROI days
    python3 minions.py --sort roi                   # sort by ROI instead of profit
    python3 minions.py --top 20                     # show only top N
    python3 minions.py --slots                      # cheapest crafts for next slot unlock
"""

import argparse
import json
import re
import sys
from pathlib import Path

from items import display_name, get_npc_sell_price
from pricing import PriceCache, _fmt

DATA_DIR = Path(__file__).parent.parent / "data"
NEU_ITEMS_DIR = DATA_DIR / "neu-repo" / "items"

# ─── Minion drop tables ─────────────────────────────────────────────
# Each minion's drops per action, NPC sell prices, and SC3000 compaction.
# Drop amounts are averages where ranges exist (e.g., 2-4 → 3).

MINIONS = {
    # ── Farming ──
    "snow": {
        "name": "Snow Minion",
        "generator_id": "SNOW_GENERATOR",
        "drops": [
            {"item": "SNOW_BALL", "amount": 4, "chance": 1.0, "npc": 1,
             "sc3000_item": "ENCHANTED_SNOW_BLOCK", "sc3000_ratio": 640},
        ],
    },
    "clay": {
        "name": "Clay Minion",
        "generator_id": "CLAY_GENERATOR",
        "drops": [
            {"item": "CLAY_BALL", "amount": 4, "chance": 1.0, "npc": 3,
             "sc3000_item": "ENCHANTED_CLAY_BALL", "sc3000_ratio": 160},
        ],
    },
    "wheat": {
        "name": "Wheat Minion",
        "generator_id": "WHEAT_GENERATOR",
        "drops": [
            {"item": "WHEAT", "amount": 1, "chance": 1.0, "npc": 6,
             "sc3000_item": "ENCHANTED_WHEAT", "sc3000_ratio": 160},
            {"item": "SEEDS", "amount": 1, "chance": 1.0, "npc": 3,
             "sc3000_item": "ENCHANTED_SEEDS", "sc3000_ratio": 160},
        ],
    },
    "sugar_cane": {
        "name": "Sugar Cane Minion",
        "generator_id": "SUGAR_CANE_GENERATOR",
        "drops": [
            {"item": "SUGAR_CANE", "amount": 3, "chance": 1.0, "npc": 4,
             "sc3000_item": "ENCHANTED_SUGAR", "sc3000_ratio": 160},
        ],
    },
    "potato": {
        "name": "Potato Minion",
        "generator_id": "POTATO_GENERATOR",
        "drops": [
            {"item": "POTATO_ITEM", "amount": 3, "chance": 1.0, "npc": 3,
             "sc3000_item": "ENCHANTED_POTATO", "sc3000_ratio": 160},
        ],
    },
    "carrot": {
        "name": "Carrot Minion",
        "generator_id": "CARROT_GENERATOR",
        "drops": [
            {"item": "CARROT_ITEM", "amount": 3, "chance": 1.0, "npc": 3,
             "sc3000_item": "ENCHANTED_CARROT", "sc3000_ratio": 160},
        ],
    },
    "melon": {
        "name": "Melon Minion",
        "generator_id": "MELON_GENERATOR",
        "drops": [
            {"item": "MELON", "amount": 5, "chance": 1.0, "npc": 2,
             "sc3000_item": "ENCHANTED_MELON", "sc3000_ratio": 160},
        ],
    },
    "pumpkin": {
        "name": "Pumpkin Minion",
        "generator_id": "PUMPKIN_GENERATOR",
        "drops": [
            {"item": "PUMPKIN", "amount": 1, "chance": 1.0, "npc": 10,
             "sc3000_item": "ENCHANTED_PUMPKIN", "sc3000_ratio": 160},
        ],
    },
    "cocoa": {
        "name": "Cocoa Beans Minion",
        "generator_id": "COCOA_GENERATOR",
        "drops": [
            {"item": "INK_SACK:3", "amount": 3, "chance": 1.0, "npc": 3,
             "sc3000_item": "ENCHANTED_COCOA", "sc3000_ratio": 160},
        ],
    },
    "nether_wart": {
        "name": "Nether Wart Minion",
        "generator_id": "NETHER_WARTS_GENERATOR",
        "drops": [
            {"item": "NETHER_STALK", "amount": 3, "chance": 1.0, "npc": 4,
             "sc3000_item": "ENCHANTED_NETHER_STALK", "sc3000_ratio": 160},
        ],
    },
    "mushroom": {
        "name": "Mushroom Minion",
        "generator_id": "MUSHROOM_GENERATOR",
        "drops": [
            {"item": "RED_MUSHROOM", "amount": 1, "chance": 0.5, "npc": 10,
             "sc3000_item": "ENCHANTED_RED_MUSHROOM", "sc3000_ratio": 160},
            {"item": "BROWN_MUSHROOM", "amount": 1, "chance": 0.5, "npc": 10,
             "sc3000_item": "ENCHANTED_BROWN_MUSHROOM", "sc3000_ratio": 160},
        ],
    },
    "cactus": {
        "name": "Cactus Minion",
        "generator_id": "CACTUS_GENERATOR",
        "drops": [
            {"item": "CACTUS", "amount": 3, "chance": 1.0, "npc": 3,
             "sc3000_item": "ENCHANTED_CACTUS_GREEN", "sc3000_ratio": 160},
        ],
    },
    # ── Combat ──
    "slime": {
        "name": "Slime Minion",
        "generator_id": "SLIME_GENERATOR",
        "drops": [
            {"item": "SLIME_BALL", "amount": 2, "chance": 1.0, "npc": 5,
             "sc3000_item": "ENCHANTED_SLIME_BALL", "sc3000_ratio": 160},
        ],
    },
    "rabbit": {
        "name": "Rabbit Minion",
        "generator_id": "RABBIT_GENERATOR",
        "drops": [
            {"item": "RABBIT", "amount": 1, "chance": 1.0, "npc": 4,
             "sc3000_item": "ENCHANTED_RABBIT", "sc3000_ratio": 160},
            {"item": "RABBIT_HIDE", "amount": 1, "chance": 0.7, "npc": 5,
             "sc3000_item": "ENCHANTED_RABBIT_HIDE", "sc3000_ratio": 160},
            {"item": "RABBIT_FOOT", "amount": 1, "chance": 0.7, "npc": 5,
             "sc3000_item": "ENCHANTED_RABBIT_FOOT", "sc3000_ratio": 160},
        ],
    },
    "sheep": {
        "name": "Sheep Minion",
        "generator_id": "SHEEP_GENERATOR",
        "drops": [
            {"item": "MUTTON", "amount": 1, "chance": 1.0, "npc": 5,
             "sc3000_item": "ENCHANTED_MUTTON", "sc3000_ratio": 160},
            {"item": "WOOL", "amount": 1, "chance": 1.0, "npc": 2,
             "sc3000_item": "ENCHANTED_WOOL", "sc3000_ratio": 160},
        ],
    },
    "magma_cube": {
        "name": "Magma Cube Minion",
        "generator_id": "MAGMA_CUBE_GENERATOR",
        "drops": [
            {"item": "MAGMA_CREAM", "amount": 2, "chance": 1.0, "npc": 8,
             "sc3000_item": "ENCHANTED_MAGMA_CREAM", "sc3000_ratio": 160},
        ],
    },
    "tarantula": {
        "name": "Tarantula Minion",
        "generator_id": "TARANTULA_GENERATOR",
        "drops": [
            {"item": "STRING", "amount": 3.5, "chance": 1.0, "npc": 3,
             "sc3000_item": "ENCHANTED_STRING", "sc3000_ratio": 160},
            {"item": "SPIDER_EYE", "amount": 1, "chance": 1.0, "npc": 3,
             "sc3000_item": "ENCHANTED_SPIDER_EYE", "sc3000_ratio": 160},
        ],
    },
    "revenant": {
        "name": "Revenant Minion",
        "generator_id": "REVENANT_GENERATOR",
        "drops": [
            {"item": "ROTTEN_FLESH", "amount": 3.5, "chance": 1.0, "npc": 2,
             "sc3000_item": "ENCHANTED_ROTTEN_FLESH", "sc3000_ratio": 160},
            {"item": "DIAMOND", "amount": 1, "chance": 0.2, "npc": 8,
             "sc3000_item": "ENCHANTED_DIAMOND", "sc3000_ratio": 160},
        ],
    },
    "skeleton": {
        "name": "Skeleton Minion",
        "generator_id": "SKELETON_GENERATOR",
        "drops": [
            {"item": "BONE", "amount": 1, "chance": 1.0, "npc": 2,
             "sc3000_item": "ENCHANTED_BONE", "sc3000_ratio": 160},
        ],
    },
    "zombie": {
        "name": "Zombie Minion",
        "generator_id": "ZOMBIE_GENERATOR",
        "drops": [
            {"item": "ROTTEN_FLESH", "amount": 1, "chance": 1.0, "npc": 2,
             "sc3000_item": "ENCHANTED_ROTTEN_FLESH", "sc3000_ratio": 160},
        ],
    },
    # ── Mining ──
    "cobblestone": {
        "name": "Cobblestone Minion",
        "generator_id": "COBBLESTONE_GENERATOR",
        "drops": [
            {"item": "COBBLESTONE", "amount": 1, "chance": 1.0, "npc": 1,
             "sc3000_item": "ENCHANTED_COBBLESTONE", "sc3000_ratio": 160},
        ],
    },
    "coal": {
        "name": "Coal Minion",
        "generator_id": "COAL_GENERATOR",
        "drops": [
            {"item": "COAL", "amount": 1, "chance": 1.0, "npc": 2,
             "sc3000_item": "ENCHANTED_COAL", "sc3000_ratio": 160},
        ],
    },
    "iron": {
        "name": "Iron Minion",
        "generator_id": "IRON_GENERATOR",
        "drops": [
            {"item": "IRON_INGOT", "amount": 1, "chance": 1.0, "npc": 3,
             "sc3000_item": "ENCHANTED_IRON", "sc3000_ratio": 160},
        ],
    },
    "gold": {
        "name": "Gold Minion",
        "generator_id": "GOLD_GENERATOR",
        "drops": [
            {"item": "GOLD_INGOT", "amount": 1, "chance": 1.0, "npc": 4,
             "sc3000_item": "ENCHANTED_GOLD", "sc3000_ratio": 160},
        ],
    },
    "diamond": {
        "name": "Diamond Minion",
        "generator_id": "DIAMOND_GENERATOR",
        "drops": [
            {"item": "DIAMOND", "amount": 1, "chance": 1.0, "npc": 8,
             "sc3000_item": "ENCHANTED_DIAMOND", "sc3000_ratio": 160},
        ],
    },
    "lapis": {
        "name": "Lapis Minion",
        "generator_id": "LAPIS_GENERATOR",
        "drops": [
            {"item": "INK_SACK:4", "amount": 4.5, "chance": 1.0, "npc": 1,
             "sc3000_item": "ENCHANTED_LAPIS_LAZULI", "sc3000_ratio": 160},
        ],
    },
    "redstone": {
        "name": "Redstone Minion",
        "generator_id": "REDSTONE_GENERATOR",
        "drops": [
            {"item": "REDSTONE", "amount": 4.5, "chance": 1.0, "npc": 1,
             "sc3000_item": "ENCHANTED_REDSTONE", "sc3000_ratio": 160},
        ],
    },
    "emerald": {
        "name": "Emerald Minion",
        "generator_id": "EMERALD_GENERATOR",
        "drops": [
            {"item": "EMERALD", "amount": 1, "chance": 1.0, "npc": 6,
             "sc3000_item": "ENCHANTED_EMERALD", "sc3000_ratio": 160},
        ],
    },
    "quartz": {
        "name": "Quartz Minion",
        "generator_id": "QUARTZ_GENERATOR",
        "drops": [
            {"item": "QUARTZ", "amount": 1, "chance": 1.0, "npc": 4,
             "sc3000_item": "ENCHANTED_QUARTZ", "sc3000_ratio": 160},
        ],
    },
    "glowstone": {
        "name": "Glowstone Minion",
        "generator_id": "GLOWSTONE_GENERATOR",
        "drops": [
            {"item": "GLOWSTONE_DUST", "amount": 3, "chance": 1.0, "npc": 2,
             "sc3000_item": "ENCHANTED_GLOWSTONE_DUST", "sc3000_ratio": 160},
        ],
    },
    # ── Foraging ──
    "oak": {
        "name": "Oak Minion",
        "generator_id": "OAK_GENERATOR",
        "drops": [
            {"item": "LOG", "amount": 1, "chance": 1.0, "npc": 2,
             "sc3000_item": "ENCHANTED_OAK", "sc3000_ratio": 160},
        ],
    },
    "spruce": {
        "name": "Spruce Minion",
        "generator_id": "SPRUCE_GENERATOR",
        "drops": [
            {"item": "LOG:1", "amount": 1, "chance": 1.0, "npc": 2,
             "sc3000_item": "ENCHANTED_SPRUCE", "sc3000_ratio": 160},
        ],
    },
    "birch": {
        "name": "Birch Minion",
        "generator_id": "BIRCH_GENERATOR",
        "drops": [
            {"item": "LOG:2", "amount": 1, "chance": 1.0, "npc": 2,
             "sc3000_item": "ENCHANTED_BIRCH", "sc3000_ratio": 160},
        ],
    },
    "jungle": {
        "name": "Jungle Minion",
        "generator_id": "JUNGLE_GENERATOR",
        "drops": [
            {"item": "LOG:3", "amount": 1, "chance": 1.0, "npc": 2,
             "sc3000_item": "ENCHANTED_JUNGLE", "sc3000_ratio": 160},
        ],
    },
    "dark_oak": {
        "name": "Dark Oak Minion",
        "generator_id": "DARK_OAK_GENERATOR",
        "drops": [
            {"item": "LOG_2:1", "amount": 1, "chance": 1.0, "npc": 2,
             "sc3000_item": "ENCHANTED_DARK_OAK", "sc3000_ratio": 160},
        ],
    },
    "acacia": {
        "name": "Acacia Minion",
        "generator_id": "ACACIA_GENERATOR",
        "drops": [
            {"item": "LOG_2", "amount": 1, "chance": 1.0, "npc": 2,
             "sc3000_item": "ENCHANTED_ACACIA", "sc3000_ratio": 160},
        ],
    },
    # ── Remaining combat ──
    "spider": {
        "name": "Spider Minion",
        "generator_id": "SPIDER_GENERATOR",
        "drops": [
            {"item": "STRING", "amount": 1, "chance": 1.0, "npc": 3,
             "sc3000_item": "ENCHANTED_STRING", "sc3000_ratio": 160},
            {"item": "SPIDER_EYE", "amount": 1, "chance": 0.5, "npc": 3,
             "sc3000_item": "ENCHANTED_SPIDER_EYE", "sc3000_ratio": 160},
        ],
    },
    "cave_spider": {
        "name": "Cave Spider Minion",
        "generator_id": "CAVESPIDER_GENERATOR",
        "drops": [
            {"item": "STRING", "amount": 1, "chance": 1.0, "npc": 3,
             "sc3000_item": "ENCHANTED_STRING", "sc3000_ratio": 160},
            {"item": "SPIDER_EYE", "amount": 1, "chance": 0.5, "npc": 3,
             "sc3000_item": "ENCHANTED_SPIDER_EYE", "sc3000_ratio": 160},
        ],
    },
    "blaze": {
        "name": "Blaze Minion",
        "generator_id": "BLAZE_GENERATOR",
        "drops": [
            {"item": "BLAZE_ROD", "amount": 1, "chance": 1.0, "npc": 9,
             "sc3000_item": "ENCHANTED_BLAZE_POWDER", "sc3000_ratio": 160},
        ],
    },
    "creeper": {
        "name": "Creeper Minion",
        "generator_id": "CREEPER_GENERATOR",
        "drops": [
            {"item": "SULPHUR", "amount": 1, "chance": 1.0, "npc": 3,
             "sc3000_item": "ENCHANTED_GUNPOWDER", "sc3000_ratio": 160},
        ],
    },
    "enderman": {
        "name": "Enderman Minion",
        "generator_id": "ENDERMAN_GENERATOR",
        "drops": [
            {"item": "ENDER_PEARL", "amount": 1, "chance": 1.0, "npc": 7,
             "sc3000_item": "ENCHANTED_ENDER_PEARL", "sc3000_ratio": 20},
        ],
    },
    "ghast": {
        "name": "Ghast Minion",
        "generator_id": "GHAST_GENERATOR",
        "drops": [
            {"item": "GHAST_TEAR", "amount": 1, "chance": 1.0, "npc": 9,
             "sc3000_item": "ENCHANTED_GHAST_TEAR", "sc3000_ratio": 5},
        ],
    },
    # ── Remaining farming ──
    "chicken": {
        "name": "Chicken Minion",
        "generator_id": "CHICKEN_GENERATOR",
        "drops": [
            {"item": "RAW_CHICKEN", "amount": 1, "chance": 1.0, "npc": 4,
             "sc3000_item": "ENCHANTED_RAW_CHICKEN", "sc3000_ratio": 160},
            {"item": "FEATHER", "amount": 1, "chance": 1.0, "npc": 3,
             "sc3000_item": "ENCHANTED_FEATHER", "sc3000_ratio": 160},
        ],
    },
    "cow": {
        "name": "Cow Minion",
        "generator_id": "COW_GENERATOR",
        "drops": [
            {"item": "RAW_BEEF", "amount": 1, "chance": 1.0, "npc": 4,
             "sc3000_item": "ENCHANTED_RAW_BEEF", "sc3000_ratio": 160},
            {"item": "LEATHER", "amount": 1, "chance": 1.0, "npc": 3,
             "sc3000_item": "ENCHANTED_LEATHER", "sc3000_ratio": 160},
        ],
    },
    "pig": {
        "name": "Pig Minion",
        "generator_id": "PIG_GENERATOR",
        "drops": [
            {"item": "PORK", "amount": 1, "chance": 1.0, "npc": 5,
             "sc3000_item": "ENCHANTED_PORK", "sc3000_ratio": 160},
        ],
    },
    # ── Other ──
    "sand": {
        "name": "Sand Minion",
        "generator_id": "SAND_GENERATOR",
        "drops": [
            {"item": "SAND", "amount": 1, "chance": 1.0, "npc": 2,
             "sc3000_item": "ENCHANTED_SAND", "sc3000_ratio": 160},
        ],
    },
    "end_stone": {
        "name": "End Stone Minion",
        "generator_id": "ENDER_STONE_GENERATOR",
        "drops": [
            {"item": "ENDER_STONE", "amount": 1, "chance": 1.0, "npc": 3,
             "sc3000_item": "ENCHANTED_END_STONE", "sc3000_ratio": 160},
        ],
    },
    "obsidian": {
        "name": "Obsidian Minion",
        "generator_id": "OBSIDIAN_GENERATOR",
        "drops": [
            {"item": "OBSIDIAN", "amount": 1, "chance": 1.0, "npc": 9,
             "sc3000_item": "ENCHANTED_OBSIDIAN", "sc3000_ratio": 160},
        ],
    },
    "gravel": {
        "name": "Gravel Minion",
        "generator_id": "GRAVEL_GENERATOR",
        "drops": [
            {"item": "GRAVEL", "amount": 1, "chance": 1.0, "npc": 3,
             "sc3000_item": None, "sc3000_ratio": None},
        ],
    },
    "ice": {
        "name": "Ice Minion",
        "generator_id": "ICE_GENERATOR",
        "drops": [
            {"item": "ICE", "amount": 1, "chance": 1.0, "npc": 1,
             "sc3000_item": "ENCHANTED_ICE", "sc3000_ratio": 160},
        ],
    },
    "red_sand": {
        "name": "Red Sand Minion",
        "generator_id": "RED_SAND_GENERATOR",
        "drops": [
            {"item": "SAND:1", "amount": 1, "chance": 1.0, "npc": 2,
             "sc3000_item": "ENCHANTED_RED_SAND", "sc3000_ratio": 160},
        ],
    },
    "mithril": {
        "name": "Mithril Minion",
        "generator_id": "MITHRIL_GENERATOR",
        "drops": [
            {"item": "MITHRIL_ORE", "amount": 1, "chance": 1.0, "npc": 5,
             "sc3000_item": "ENCHANTED_MITHRIL", "sc3000_ratio": 160},
        ],
    },
    "hard_stone": {
        "name": "Hard Stone Minion",
        "generator_id": "HARD_STONE_GENERATOR",
        "drops": [
            {"item": "HARD_STONE", "amount": 1, "chance": 1.0, "npc": 1,
             "sc3000_item": "ENCHANTED_HARD_STONE", "sc3000_ratio": 576},
        ],
    },
    "flower": {
        "name": "Flower Minion",
        "generator_id": "FLOWER_GENERATOR",
        "drops": [
            {"item": "DOUBLE_PLANT", "amount": 1, "chance": 1.0, "npc": 3,
             "sc3000_item": None, "sc3000_ratio": None},
        ],
    },
    "fishing": {
        "name": "Fishing Minion",
        "generator_id": "FISHING_GENERATOR",
        "drops": [
            {"item": "RAW_FISH", "amount": 1, "chance": 1.0, "npc": 5,
             "sc3000_item": "ENCHANTED_RAW_FISH", "sc3000_ratio": 160},
        ],
    },
    "sunflower": {
        "name": "Sunflower Minion",
        "generator_id": "SUNFLOWER_GENERATOR",
        "drops": [
            {"item": "DOUBLE_PLANT", "amount": 1, "chance": 1.0, "npc": 3,
             "sc3000_item": None, "sc3000_ratio": None},
        ],
    },
    "mycelium": {
        "name": "Mycelium Minion",
        "generator_id": "MYCELIUM_GENERATOR",
        "drops": [
            {"item": "MYCEL", "amount": 1, "chance": 1.0, "npc": 3,
             "sc3000_item": None, "sc3000_ratio": None},
        ],
    },
}

# ─── Minion slot unlock thresholds ────────────────────────────────────
# Unique craft thresholds for bonus minion slots (from wiki).
# Index = bonus slots, value = required crafts. Total slots = 5 + index.
SLOT_THRESHOLDS = [0, 5, 15, 30, 50, 75, 100, 125, 150, 175, 200,
                   225, 250, 275, 300, 350, 400, 450, 500, 550, 600, 650]

# ─── Fuel types ──────────────────────────────────────────────────────

FUELS = {
    "none":       {"speed_mult": 0.00, "item_id": None},
    "coal":       {"speed_mult": 0.05, "item_id": "COAL"},
    "block_coal": {"speed_mult": 0.05, "item_id": "COAL_BLOCK"},
    "e_charcoal": {"speed_mult": 0.10, "item_id": "ENCHANTED_CHARCOAL"},
    "e_coal":     {"speed_mult": 0.10, "item_id": "ENCHANTED_COAL"},
    "e_lava":     {"speed_mult": 0.25, "item_id": "ENCHANTED_LAVA_BUCKET"},
    "magma":      {"speed_mult": 0.30, "item_id": "MAGMA_BUCKET"},
    "plasma":     {"speed_mult": 0.35, "item_id": "PLASMA_BUCKET"},
    "hamster":    {"speed_mult": 0.50, "item_id": "HAMSTER_WHEEL"},
    "catalyst":   {"speed_mult": 2.00, "item_id": "CATALYST"},
    "hyper_cat":  {"speed_mult": 3.00, "item_id": "HYPER_CATALYST"},
}

# ─── Hopper types ────────────────────────────────────────────────────
# Used with --npc. Multiplier on NPC sell price.

HOPPERS = {
    "budget":    {"sell_mult": 0.5},
    "enchanted": {"sell_mult": 0.9},
}

# ─── Action speed parsing ───────────────────────────────────────────

_SPEED_RE = re.compile(r"Time Between Actions: §a([\d.]+)s")

_action_speeds = None  # lazy cache: {generator_id: {tier: seconds}}


def load_action_speeds():
    """Parse action speeds from NEU repo lore text.

    Returns {generator_id: {tier: speed_seconds}}.
    """
    global _action_speeds
    if _action_speeds is not None:
        return _action_speeds

    _action_speeds = {}
    if not NEU_ITEMS_DIR.exists():
        print("  [Warning: NEU repo not found, using fallback speeds]",
              file=sys.stderr)
        return _action_speeds

    for path in NEU_ITEMS_DIR.glob("*_GENERATOR_*.json"):
        name = path.stem  # e.g. SNOW_GENERATOR_11
        parts = name.rsplit("_", 1)
        if len(parts) != 2:
            continue
        gen_id = parts[0]  # SNOW_GENERATOR
        try:
            tier = int(parts[1])
        except ValueError:
            continue

        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        for line in data.get("lore", []):
            m = _SPEED_RE.search(line)
            if m:
                speed = float(m.group(1))
                _action_speeds.setdefault(gen_id, {})[tier] = speed
                break

    return _action_speeds


def get_max_tier(generator_id):
    """Get the highest tier available for a generator."""
    speeds = load_action_speeds()
    tiers = speeds.get(generator_id, {})
    return max(tiers.keys()) if tiers else 11


# ─── Price helpers ───────────────────────────────────────────────────

def _get_sell_price(item_id, pc, use_npc=False, hopper=None):
    """Get the sell price for an item.

    With use_npc: returns NPC sell price × hopper multiplier.
    Without: returns bazaar sell order price, falling back to NPC.
    """
    if use_npc:
        npc = get_npc_sell_price(item_id)
        price = npc if npc else 0
        if hopper and hopper in HOPPERS:
            price *= HOPPERS[hopper]["sell_mult"]
        return price

    p = pc.get_price(item_id)
    if p["source"] == "bazaar" and p.get("sell", 0) > 0:
        return p["sell"]
    # Fall back to NPC
    npc = get_npc_sell_price(item_id)
    return npc if npc else 0


# ─── Core profit calculation ────────────────────────────────────────

def calc_profit(minion_key, tier, num_minions, fuel, use_sc3000,
                use_diamond, use_npc, hopper, pc):
    """Calculate daily profit for a minion configuration.

    Returns dict with:
        profit_day: total daily revenue for all minions
        per_minion: daily revenue per minion
        actions_day: actions per day per minion
        effective_speed: seconds between actions after fuel
        base_speed: raw action speed from NEU repo
        coins_per_action: revenue per action per minion
        drop_details: list of {item, raw_per_action, price, coins} per drop
    """
    speeds = load_action_speeds()
    minion = MINIONS[minion_key]
    gen_id = minion["generator_id"]

    # Get action speed
    tier_speeds = speeds.get(gen_id, {})
    if tier not in tier_speeds:
        return None  # tier not available
    base_speed = tier_speeds[tier]

    # Apply fuel bonus
    fuel_mult = FUELS[fuel]["speed_mult"]
    effective_speed = base_speed / (1 + fuel_mult)
    actions_per_day = 86400 / (effective_speed * 2)

    # Calculate coins per action from drops
    coins_per_action = 0
    drop_details = []

    for drop in minion["drops"]:
        raw_per_action = drop["amount"] * drop["chance"]

        if use_sc3000 and drop["sc3000_item"]:
            # SC3000: compact raw drops into enchanted form
            items_per_action = raw_per_action / drop["sc3000_ratio"]
            price = _get_sell_price(drop["sc3000_item"], pc, use_npc, hopper)
            coins = items_per_action * price
            drop_details.append({
                "raw_item": drop["item"],
                "raw_per_action": raw_per_action,
                "sell_item": drop["sc3000_item"],
                "items_per_action": items_per_action,
                "price": price,
                "coins": coins,
                "ratio": drop["sc3000_ratio"],
            })
        else:
            # No SC3000: sell raw items
            if use_npc:
                price = drop["npc"]
                if hopper and hopper in HOPPERS:
                    price *= HOPPERS[hopper]["sell_mult"]
            else:
                price = _get_sell_price(drop["item"], pc, use_npc, hopper)
                if price == 0:
                    price = drop["npc"]
            coins = raw_per_action * price
            drop_details.append({
                "raw_item": drop["item"],
                "raw_per_action": raw_per_action,
                "sell_item": drop["item"],
                "items_per_action": raw_per_action,
                "price": price,
                "coins": coins,
                "ratio": 1,
            })
        coins_per_action += coins

    # Diamond Spreading: ~10% chance per action
    diamond_detail = None
    if use_diamond:
        ds_per_action = 0.1
        if use_sc3000:
            ds_items = ds_per_action / 160
            ds_price = _get_sell_price("ENCHANTED_DIAMOND", pc, use_npc,
                                       hopper)
            ds_coins = ds_items * ds_price
            diamond_detail = {
                "raw_item": "DIAMOND (spreading)",
                "raw_per_action": ds_per_action,
                "sell_item": "ENCHANTED_DIAMOND",
                "items_per_action": ds_items,
                "price": ds_price,
                "coins": ds_coins,
                "ratio": 160,
            }
        else:
            ds_price = 8  # NPC diamond price
            if use_npc and hopper and hopper in HOPPERS:
                ds_price *= HOPPERS[hopper]["sell_mult"]
            elif not use_npc:
                p = _get_sell_price("DIAMOND", pc, False, None)
                if p > 0:
                    ds_price = p
            ds_coins = ds_per_action * ds_price
            diamond_detail = {
                "raw_item": "DIAMOND (spreading)",
                "raw_per_action": ds_per_action,
                "sell_item": "DIAMOND",
                "items_per_action": ds_per_action,
                "price": ds_price,
                "coins": ds_coins,
                "ratio": 1,
            }
        coins_per_action += diamond_detail["coins"]
        drop_details.append(diamond_detail)

    per_minion = actions_per_day * coins_per_action
    profit_day = per_minion * num_minions

    return {
        "profit_day": profit_day,
        "per_minion": per_minion,
        "actions_day": actions_per_day,
        "effective_speed": effective_speed,
        "base_speed": base_speed,
        "coins_per_action": coins_per_action,
        "drop_details": drop_details,
    }


# ─── Minion craft cost ─────────────────────────────────────────────

_craft_cost_cache = {}  # {item_id: cost_or_None}


def calc_minion_craft_cost(generator_id, tier, pc):
    """Calculate recursive craft cost for a minion from NEU recipes.

    Sums Bazaar material costs from T1 through the target tier.
    Returns total cost, or None if recipe not found (e.g., T12 NPC upgrade).
    """
    item_id = f"{generator_id}_{tier}"

    if item_id in _craft_cost_cache:
        return _craft_cost_cache[item_id]

    # Load recipe file
    recipe_path = NEU_ITEMS_DIR / f"{item_id}.json"
    if not recipe_path.exists():
        _craft_cost_cache[item_id] = None
        return None

    try:
        data = json.loads(recipe_path.read_text())
    except (json.JSONDecodeError, OSError):
        _craft_cost_cache[item_id] = None
        return None

    recipe = data.get("recipe")
    if not recipe:
        # No recipe (T12 NPC upgrade, or quest-only T1 like Snow/Flower)
        _craft_cost_cache[item_id] = None
        return None

    total = 0
    for slot in ("A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3"):
        entry = recipe.get(slot, "")
        if not entry:
            continue

        # Parse "ITEM_ID:QUANTITY" (rsplit handles IDs with colons)
        parts = entry.rsplit(":", 1)
        if len(parts) != 2:
            continue
        ing_id, qty_str = parts
        try:
            qty = int(qty_str)
        except ValueError:
            continue
        if not ing_id or qty <= 0:
            continue

        if "_GENERATOR_" in ing_id:
            # Previous tier minion → recurse
            gen_parts = ing_id.rsplit("_", 1)
            if len(gen_parts) == 2:
                sub_gen_id, sub_tier_str = gen_parts
                try:
                    sub_tier = int(sub_tier_str)
                except ValueError:
                    continue
                sub_cost = calc_minion_craft_cost(sub_gen_id, sub_tier, pc)
                if sub_cost is not None:
                    total += sub_cost * qty
                # No recipe for sub-tier (e.g., Snow T1) → treat as 0
        else:
            # Material → look up Bazaar buy price
            p = pc.get_price(ing_id)
            if p["source"] == "bazaar" and p.get("buy", 0) > 0:
                total += p["buy"] * qty
            # Not on Bazaar (wooden tools, etc.) → cost 0

    _craft_cost_cache[item_id] = total
    return total


# ─── ROI calculation ────────────────────────────────────────────────

def calc_setup_cost(minion_key, tier, use_sc3000, use_diamond, fuel, pc):
    """Estimate per-minion setup cost from craft + Bazaar prices.

    Returns dict with item costs and total.
    """
    costs = {}
    minion = MINIONS[minion_key]
    gen_id = minion["generator_id"]

    # Minion craft cost (recursive from T1)
    craft_cost = calc_minion_craft_cost(gen_id, tier, pc)
    if craft_cost is not None:
        costs["minion"] = craft_cost
    else:
        costs["minion"] = 0  # no recipe (T12 NPC upgrade, quest-only T1)

    # SC3000
    unpriced = []
    if use_sc3000:
        p = pc.get_price("SUPER_COMPACTOR_3000")
        if p["source"] != "unknown":
            costs["sc3000"] = (p.get("lowest_bin") or p.get("buy") or 0)
        else:
            unpriced.append("SC3000")

    # Diamond Spreading
    if use_diamond:
        p = pc.get_price("DIAMOND_SPREADING")
        if p["source"] != "unknown":
            costs["diamond_spreading"] = (p.get("lowest_bin")
                                          or p.get("buy") or 0)
        else:
            unpriced.append("Diamond Spreading")

    # Fuel
    fuel_id = FUELS[fuel]["item_id"]
    if fuel_id:
        p = pc.get_price(fuel_id)
        if p["source"] != "unknown":
            costs["fuel"] = (p.get("buy") or p.get("lowest_bin") or 0)
        else:
            unpriced.append(fuel)

    costs["total"] = sum(costs.values())
    if unpriced:
        costs["unpriced"] = unpriced
    return costs


# ─── Minion slot unlock ──────────────────────────────────────────────

def _neu_to_bazaar_id(ing_id):
    """Convert NEU item IDs to Bazaar format (hyphens → colons for damage values)."""
    # NEU uses LOG-2, Bazaar uses LOG:2. Only convert trailing -N patterns
    # where the base item is known to use damage values.
    m = re.match(r"^(.+)-(\d+)$", ing_id)
    if m:
        return f"{m.group(1)}:{m.group(2)}"
    return ing_id


def calc_tier_material_cost(generator_id, tier, pc):
    """Calculate Bazaar material cost for one tier's recipe (non-recursive).

    Only prices the 8 surrounding slots, skipping B2 (center slot) which
    is always the previous-tier minion or a wooden tool. This gives the
    out-of-pocket cost to craft that specific tier.

    Returns cost in coins, or None if no recipe found.
    """
    item_id = f"{generator_id}_{tier}"
    recipe_path = NEU_ITEMS_DIR / f"{item_id}.json"
    if not recipe_path.exists():
        return None

    try:
        data = json.loads(recipe_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    recipe = data.get("recipe")
    if not recipe:
        return None

    total = 0
    for slot in ("A1", "A2", "A3", "B1", "B3", "C1", "C2", "C3"):
        entry = recipe.get(slot, "")
        if not entry:
            continue

        parts = entry.rsplit(":", 1)
        if len(parts) != 2:
            continue
        ing_id, qty_str = parts
        try:
            qty = int(qty_str)
        except ValueError:
            continue
        if not ing_id or qty <= 0:
            continue

        # Skip minion ingredients in non-center slots (T12 recipes put the
        # previous-tier minion in C2 instead of B2)
        if "_GENERATOR_" in ing_id:
            continue

        # NEU uses hyphens for damage values (LOG-2), Bazaar uses colons (LOG:2)
        bazaar_id = _neu_to_bazaar_id(ing_id)

        # Look up Bazaar buy price
        p = pc.get_price(bazaar_id)
        if p["source"] == "bazaar" and p.get("buy", 0) > 0:
            total += p["buy"] * qty
        # Not on Bazaar (wooden tools, etc.) → cost 0

    return total


def _generator_display_name(generator_id, tier):
    """Get a readable name for a generator tier, e.g. 'Snow Minion IV'."""
    tier_roman = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI",
                  7: "VII", 8: "VIII", 9: "IX", 10: "X", 11: "XI", 12: "XII"}
    # Try to read display name from NEU file
    item_id = f"{generator_id}_{tier}"
    recipe_path = NEU_ITEMS_DIR / f"{item_id}.json"
    if recipe_path.exists():
        try:
            data = json.loads(recipe_path.read_text())
            raw = data.get("displayname", "")
            # Strip color codes (§X)
            name = re.sub(r"§.", "", raw)
            if name:
                return name
        except (json.JSONDecodeError, OSError):
            pass
    # Fallback: format from generator_id
    base = generator_id.replace("_GENERATOR", "").replace("_", " ").title()
    roman = tier_roman.get(tier, str(tier))
    return f"{base} Minion {roman}"


def show_slots(pc):
    """Show cheapest uncrafted minion tiers for the next slot unlock."""
    profile_path = DATA_DIR / "last_profile.json"
    if not profile_path.exists():
        print("  No profile data found. Run 'python3 profile.py' first.")
        return

    try:
        profile = json.loads(profile_path.read_text())
    except (json.JSONDecodeError, OSError):
        print("  Could not read profile data.")
        return

    member = profile.get("member", profile)
    crafted = set(
        member.get("player_data", {}).get("crafted_generators", [])
    )
    num_crafted = len(crafted)

    # Determine current and next slot info
    current_bonus = 0
    for i, threshold in enumerate(SLOT_THRESHOLDS):
        if num_crafted >= threshold:
            current_bonus = i
        else:
            break
    current_slots = 5 + current_bonus

    # Next threshold
    next_idx = current_bonus + 1
    if next_idx < len(SLOT_THRESHOLDS):
        next_threshold = SLOT_THRESHOLDS[next_idx]
        crafts_needed = next_threshold - num_crafted
        next_slots = 5 + next_idx
    else:
        next_threshold = None
        crafts_needed = 0
        next_slots = None

    # Scan NEU repo for all generator tiers
    all_tiers = []  # [(generator_id, tier), ...]
    for path in NEU_ITEMS_DIR.glob("*_GENERATOR_*.json"):
        parts = path.stem.rsplit("_", 1)
        if len(parts) != 2:
            continue
        gen_id = parts[0]
        try:
            tier = int(parts[1])
        except ValueError:
            continue
        all_tiers.append((gen_id, tier))

    # Filter to uncrafted tiers that have recipes
    uncrafted = []
    for gen_id, tier in all_tiers:
        # crafted_generators uses format without _GENERATOR:
        # COBBLESTONE_GENERATOR → COBBLESTONE, tier 1 → COBBLESTONE_1
        craft_key = gen_id.replace("_GENERATOR", "") + f"_{tier}"
        if craft_key in crafted:
            continue

        cost = calc_tier_material_cost(gen_id, tier, pc)
        if cost is not None and cost > 0:
            uncrafted.append((gen_id, tier, cost))

    # Sort by cost
    uncrafted.sort(key=lambda x: x[2])

    # Display
    print(f"\n  Minion Slot Unlock Guide")
    print(f"  {'─' * 58}")
    print(f"  Unique crafts: {num_crafted}")
    print(f"  Current slots: {current_slots} ({5} base + {current_bonus} bonus)")
    if next_threshold is not None:
        print(f"  Next slot:     {next_slots} at {next_threshold} crafts"
              f" ({crafts_needed} more needed)")
    else:
        print(f"  All slots unlocked!")
    print()

    if not uncrafted:
        print("  No uncrafted tiers with recipes found.")
        print()
        return

    # Show enough to reach next slot + 5 extra, minimum 15
    show_count = max(15, crafts_needed + 5) if crafts_needed > 0 else 15
    show_count = min(show_count, len(uncrafted))

    print(f"  {'#':<4s}{'Minion':<30s}{'Cost':>12s}{'Running':>12s}")
    print(f"  {'─' * 58}")

    running_total = 0
    slot_line_shown = False
    for i, (gen_id, tier, cost) in enumerate(uncrafted[:show_count]):
        name = _generator_display_name(gen_id, tier)
        running_total += cost
        marker = ""
        if (not slot_line_shown and next_threshold is not None
                and i + 1 >= crafts_needed):
            marker = " ◄ next slot"
            slot_line_shown = True
        print(f"  {i+1:<4d}{name:<30s}{_fmt(cost):>12s}"
              f"{_fmt(running_total):>12s}{marker}")

    print(f"\n  Total for {show_count} cheapest: {_fmt(running_total)}")
    if next_threshold is not None and crafts_needed <= len(uncrafted):
        slot_cost = sum(x[2] for x in uncrafted[:crafts_needed])
        print(f"  Cost for next slot ({crafts_needed} crafts): {_fmt(slot_cost)}")
    print()


# ─── Output formatting ──────────────────────────────────────────────

def _config_str(num_minions, tier, use_sc3000, use_diamond, fuel, use_npc,
                hopper):
    """Build a human-readable configuration summary string."""
    parts = [f"{num_minions}\u00d7 T{tier}"]
    upgrades = []
    if use_sc3000:
        upgrades.append("SC3000")
    if use_diamond:
        upgrades.append("Diamond Spreading")
    if upgrades:
        parts.append(" + ".join(upgrades))
    if fuel != "none":
        fuel_names = {
            "coal": "Coal", "block_coal": "Coal Block",
            "e_charcoal": "Enchanted Charcoal", "e_coal": "Enchanted Coal",
            "e_lava": "E-Lava Bucket", "magma": "Magma Bucket",
            "plasma": "Plasma Bucket", "hamster": "Hamster Wheel",
            "catalyst": "Catalyst", "hyper_cat": "Hyper Catalyst",
        }
        parts.append(fuel_names.get(fuel, fuel))
    if use_npc:
        if hopper:
            hopper_names = {"budget": "Budget Hopper", "enchanted": "Enchanted Hopper"}
            parts.append(f"NPC ({hopper_names.get(hopper, hopper)})")
        else:
            parts.append("NPC sell")
    else:
        parts.append("bazaar sell order")
    return ", ".join(parts)


def show_ranked_table(results, num_minions, tier, use_sc3000, use_diamond,
                      fuel, use_npc, hopper, top_n, sort_key):
    """Display the ranked profit table."""
    config = _config_str(num_minions, tier, use_sc3000, use_diamond, fuel,
                         use_npc, hopper)
    print(f"\n  Minion Profit Calculator \u2014 {config}")
    print(f"  {'─' * 65}")
    header = (f"  {'Minion':<24s}{'Profit/Day':>12s}{'Per Minion':>12s}"
              f"{'Actions/Day':>14s}")
    if sort_key == "roi":
        header += f"{'ROI Days':>10s}"
    print(header)
    print(f"  {'─' * 65}")

    for name, r in results:
        tier_label = f"T{tier} {name}"
        profit = _fmt(r["profit_day"])
        per_min = _fmt(r["per_minion"])
        actions = f"{r['actions_day']:,.0f}"
        line = f"  {tier_label:<24s}{profit:>12s}{per_min:>12s}{actions:>14s}"
        if sort_key == "roi" and "roi_days" in r:
            roi = r["roi_days"]
            line += f"{roi:>9.1f}d" if roi < 999 else "       N/A"
        print(line)

    if top_n and top_n < len(results):
        print(f"  ... showing top {top_n} of {len(results)}")

    if not use_sc3000:
        print(f"  ⚠ Without Super Compactor, minion storage fills quickly with raw drops.")
        print(f"    Profits assume all items are collected and sold — actual yield depends")
        print(f"    on collection frequency. High-action minions are most affected.")
    print()


def show_detail(minion_key, tier, num_minions, fuel, use_sc3000, use_diamond,
                use_npc, hopper, show_roi, pc):
    """Display detailed breakdown for a single minion."""
    minion = MINIONS[minion_key]
    result = calc_profit(minion_key, tier, num_minions, fuel, use_sc3000,
                         use_diamond, use_npc, hopper, pc)
    if not result:
        print(f"  {minion['name']} T{tier}: tier not available")
        return

    fuel_pct = int(FUELS[fuel]["speed_mult"] * 100)
    fuel_name = fuel.replace("_", " ").title() if fuel != "none" else "None"

    print(f"\n  {minion['name']} T{tier} \u2014 Detailed Breakdown")
    print(f"  {'─' * 50}")
    print(f"  Action speed:      {result['base_speed']:.1f}s (base)"
          f" \u2192 {result['effective_speed']:.1f}s"
          f" ({fuel_name} +{fuel_pct}%)")
    print(f"  Actions/day:       {result['actions_day']:,.0f} (per minion)")
    print()

    # Drop breakdown
    print("  Drops per action:")
    for d in result["drop_details"]:
        raw_name = display_name(d["raw_item"])
        sell_name = display_name(d["sell_item"])
        if d["ratio"] > 1:
            print(f"    {d['raw_per_action']:.1f}\u00d7 {raw_name}"
                  f" \u2192 SC3000 \u2192"
                  f" {d['items_per_action']:.6f}\u00d7 {sell_name}"
                  f" @ {_fmt(d['price'])} = {d['coins']:.2f}")
        else:
            print(f"    {d['raw_per_action']:.1f}\u00d7 {raw_name}"
                  f" @ {_fmt(d['price'])} = {d['coins']:.2f}")
    print(f"    Total: {result['coins_per_action']:.2f} coins/action")
    print()

    print(f"  Per minion:        {_fmt(result['per_minion'])}/day")
    print(f"  {num_minions} minions:        "
          f"{_fmt(result['profit_day'])}/day")

    if not use_sc3000:
        # Calculate storage fill time: 15 slots × 64 = 960 items capacity
        storage_cap = 15 * 64
        total_drops = sum(d["raw_per_action"] for d in result["drop_details"])
        if total_drops > 0 and result["actions_day"] > 0:
            drops_per_day = total_drops * result["actions_day"]
            fill_days = storage_cap / drops_per_day
            if fill_days < 1/24:
                fill_str = f"{fill_days * 24 * 60:.0f} minutes"
            elif fill_days < 1:
                fill_str = f"{fill_days * 24:.1f} hours"
            else:
                fill_str = f"{fill_days:.1f} days"
            print(f"\n  ⚠ No Super Compactor — storage fills in ~{fill_str}")
            print(f"    Storage: 15 slots × 64 = 960 items. "
                  f"At {total_drops:.1f} drops/action and "
                  f"{result['actions_day']:,.0f} actions/day, "
                  f"fills in ~{fill_str}.")

    # ROI
    if show_roi:
        costs = calc_setup_cost(minion_key, tier, use_sc3000, use_diamond,
                                fuel, pc)
        print()
        print("  Setup cost per minion:")
        labels = {
            "minion": f"Minion T{tier} (craft)",
            "sc3000": "SC3000",
            "diamond_spreading": "Diamond Spreading",
            "fuel": f"Fuel ({fuel})",
        }
        for key, label in labels.items():
            if key in costs and costs[key] > 0:
                print(f"    {label:<25s}{_fmt(costs[key]):>10s}")
        print(f"    {'Total':<25s}{_fmt(costs['total']):>10s}")

        total_cost = costs["total"] * num_minions
        print(f"\n  {num_minions} minions total:   {_fmt(total_cost)}")
        if result["per_minion"] > 0 and costs["total"] > 0:
            roi = costs["total"] / result["per_minion"]
            print(f"  ROI:                {roi:.1f} days")
        else:
            print("  ROI:                N/A")

    print()


# ─── CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Minion profit calculator for Hypixel SkyBlock")
    parser.add_argument("--minions", "-m", type=int, default=25,
                        help="number of minions (default: 25)")
    parser.add_argument("--tier", "-t", type=int, default=11,
                        help="minion tier (default: 11)")
    parser.add_argument("--fuel", "-f", default="e_lava",
                        choices=list(FUELS.keys()),
                        help="fuel type (default: e_lava)")
    parser.add_argument("--no-sc3000", action="store_true",
                        help="disable Super Compactor 3000")
    parser.add_argument("--no-diamond", action="store_true",
                        help="disable Diamond Spreading")
    parser.add_argument("--npc", action="store_true",
                        help="use NPC prices instead of bazaar")
    parser.add_argument("--hopper", choices=list(HOPPERS.keys()),
                        help="hopper type for NPC pricing")
    parser.add_argument("--item", "-i",
                        help="show detailed view for one minion type")
    parser.add_argument("--roi", action="store_true",
                        help="include setup cost + ROI calculation")
    parser.add_argument("--sort", "-s", choices=["profit", "roi"],
                        default="profit",
                        help="sort order (default: profit)")
    parser.add_argument("--top", type=int,
                        help="show only top N minions")
    parser.add_argument("--list", action="store_true",
                        help="list all available minion types")
    parser.add_argument("--slots", action="store_true",
                        help="show cheapest minion crafts for next slot unlock")
    args = parser.parse_args()

    if args.list:
        print("\n  Available minion types:")
        for key, m in sorted(MINIONS.items()):
            max_t = get_max_tier(m["generator_id"])
            print(f"    {key:<20s} {m['name']:<30s} (max T{max_t})")
        print()
        return

    if args.slots:
        pc = PriceCache()
        show_slots(pc)
        pc.flush()
        return

    use_sc3000 = not args.no_sc3000
    use_diamond = not args.no_diamond

    pc = PriceCache()

    # Detailed single-minion view
    if args.item:
        key = args.item.lower().replace(" ", "_")
        if key not in MINIONS:
            # Try fuzzy match
            matches = [k for k in MINIONS if key in k]
            if len(matches) == 1:
                key = matches[0]
            elif matches:
                print(f"  Ambiguous: {', '.join(matches)}")
                pc.flush()
                return
            else:
                print(f"  Unknown minion: {args.item}")
                print(f"  Use --list to see available types")
                pc.flush()
                return

        show_detail(key, args.tier, args.minions, args.fuel, use_sc3000,
                    use_diamond, args.npc, args.hopper, args.roi, pc)
        pc.flush()
        return

    # Ranked table for all minions
    results = []
    for key, minion in MINIONS.items():
        r = calc_profit(key, args.tier, args.minions, args.fuel, use_sc3000,
                        use_diamond, args.npc, args.hopper, pc)
        if r is None:
            continue

        # Calculate ROI if needed
        if args.sort == "roi" or args.roi:
            costs = calc_setup_cost(key, args.tier, use_sc3000, use_diamond,
                                    args.fuel, pc)
            if r["per_minion"] > 0 and costs["total"] > 0:
                r["roi_days"] = costs["total"] / r["per_minion"]
            else:
                r["roi_days"] = 9999

        results.append((minion["name"], r))

    # Sort
    if args.sort == "roi":
        results.sort(key=lambda x: x[1].get("roi_days", 9999))
    else:
        results.sort(key=lambda x: x[1]["profit_day"], reverse=True)

    # Limit
    if args.top:
        results = results[:args.top]

    show_ranked_table(results, args.minions, args.tier, use_sc3000,
                      use_diamond, args.fuel, args.npc, args.hopper,
                      args.top, args.sort)
    pc.flush()


if __name__ == "__main__":
    main()
