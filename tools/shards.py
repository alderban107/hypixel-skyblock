#!/usr/bin/env python3
"""
Shard Fusion Advisor — "What should I fuse? What should I farm?"

The core insight: no base-chain fusion is profitable at instant buy/sell.
People doing fusions aren't buying inputs — they're farming them. So the
real questions are:
  1. I have this shard from farming. Should I sell it or fuse it forward?
  2. What's the most valuable shard I can farm, considering filler costs?
  3. What are the cheapest fillers for each rarity?
  4. Which shards have dead markets I should avoid fusing into?

Usage:
    python3 shards.py chain <shard_name>   — Trace a shard's full fusion chain
    python3 shards.py farm                 — Rank farmable shards by chain value
    python3 shards.py fillers              — Show cheapest fillers per rarity
    python3 shards.py health               — Market health check (dead/thin markets)
    python3 shards.py                      — Quick summary of all the above

Fusion mechanics (verified):
    - Base/ID fusion: Shard A (slot 1) + same-rarity filler (slot 2) → next in A's chain
    - Both slots consume the INPUT shard's fusion_quantity
    - Elementals/Reptiles/Amphibians = 2 per slot, most others = 5
    - Bird family shards get skipped in chains
    - Output is always 1 shard (special fusions yield 2, but recipe data is unreliable)
"""

import sys
from pathlib import Path

from pricing import PriceCache, _fmt

# ── Complete shard data (141 shards from GiantWizard's Hypixel forum post) ──
shards_data = [
    {'id': 'C1', 'name': 'Grove', 'fusion_quantity': 2, 'rarity': 'Common', 'category': 'Forest', 'families': ['Elemental'], 'fusion_results': {'base': 'C4'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Common Forest Shard + Uncommon+ Shard', 'components': ['Common', 'Forest', '+', 'Uncommon+']}]}},
    {'id': 'C2', 'name': 'Mist', 'fusion_quantity': 2, 'rarity': 'Common', 'category': 'Water', 'families': ['Elemental'], 'fusion_results': {'base': 'C5'}, 'fusion_sources': {'base': 'C1'}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Common Water Shard + Uncommon+ Shard', 'components': ['Common', 'Water', '+', 'Uncommon+']}]}},
    {'id': 'C3', 'name': 'Flash', 'fusion_quantity': 2, 'rarity': 'Common', 'category': 'Combat', 'families': ['Elemental'], 'fusion_results': {'base': 'C9'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Common Combat Shard + Uncommon+ Shard', 'components': ['Common', 'Combat', '+', 'Uncommon+']}]}},
    {'id': 'C4', 'name': 'Phanpyre', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Forest', 'families': ['Phantom'], 'fusion_results': {'base': 'C7'}, 'fusion_sources': {'base': 'C1'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C5', 'name': 'Cod', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Water', 'families': ['Tropical Fish'], 'fusion_results': {'base': 'C8'}, 'fusion_sources': {'base': 'C2'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C7', 'name': 'Phanflare', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Forest', 'families': ['Phantom'], 'fusion_results': {'base': 'C10'}, 'fusion_sources': {'base': 'C4'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C8', 'name': 'Night Squid', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Water', 'families': ['Squid'], 'fusion_results': {'base': 'C11'}, 'fusion_sources': {'base': 'C5'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C9', 'name': 'Lapis Zombie', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Combat', 'families': ['Lapis'], 'fusion_results': {'base': 'C12'}, 'fusion_sources': {'base': 'C3'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C10', 'name': 'Hideonleaf', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Forest', 'families': ['Shulker'], 'fusion_results': {'base': 'C25'}, 'fusion_sources': {'base': 'C7'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C11', 'name': 'Verdant', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Water', 'families': ['Tropical Fish'], 'fusion_results': {'base': 'C14'}, 'fusion_sources': {'base': 'C8'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C12', 'name': 'Chill', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'C15'}, 'fusion_sources': {'base': 'C9'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C14', 'name': 'Sea Archer', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Water', 'families': [], 'fusion_results': {'base': 'C17'}, 'fusion_sources': {'base': 'C11'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C15', 'name': 'Voracious Spider', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'C18'}, 'fusion_sources': {'base': 'C12'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C16', 'name': 'Hideongift', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Forest', 'families': ['Shulker'], 'fusion_results': {'base': 'C25'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Shulker Shard + Common+ Shard'}]}},
    {'id': 'C17', 'name': 'Birries', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Water', 'families': [], 'fusion_results': {'base': 'C20'}, 'fusion_sources': {'base': 'C14'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C18', 'name': 'Tank Zombie', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'C21'}, 'fusion_sources': {'base': 'C15'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C19', 'name': 'Crow', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Forest', 'families': ['Bird'], 'fusion_results': {'base': 'C25'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'direct'}, 'shop_cost': {'currency': 'AGATHA_COUPON', 'currency_name': "Agatha's Coupon", 'amount': 15}},
    {'id': 'C20', 'name': 'Tadgang', 'fusion_quantity': 2, 'rarity': 'Common', 'category': 'Water', 'families': ['Amphibian', 'Frog'], 'fusion_results': {'base': 'C23'}, 'fusion_sources': {'base': 'C17'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C21', 'name': 'Zealot', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'C27'}, 'fusion_sources': {'base': 'C18'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C23', 'name': 'Coralot', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Water', 'families': ['Axolotl'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': 'C20'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C24', 'name': 'Harpy', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Combat', 'families': ['Bird'], 'fusion_results': {'base': 'C27'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Bird Shard + Combat Shard'}]}},
    {'id': 'C25', 'name': 'Mudworm', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Forest', 'families': [], 'fusion_results': {'base': None}, 'fusion_sources': {'base': ['C10', 'C16', 'C19']}, 'acquisition': {'type': 'direct'}},
    {'id': 'C27', 'name': 'Golden Ghoul', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'C29'}, 'fusion_sources': {'base': ['C21', 'C24']}, 'acquisition': {'type': 'direct'}},
    {'id': 'C29', 'name': 'Azure', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Combat', 'families': ['Tropical Fish'], 'fusion_results': {'base': 'C30'}, 'fusion_sources': {'base': 'C27'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C30', 'name': 'Bezal', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'C33'}, 'fusion_sources': {'base': 'C29'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C33', 'name': 'Yog', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'C36'}, 'fusion_sources': {'base': 'C30'}, 'acquisition': {'type': 'direct'}},
    {'id': 'C34', 'name': 'Boreal Owl', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Forest', 'families': ['Bird'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Bird Shard + Common+ Shard'}]}},
    {'id': 'C35', 'name': 'Newt', 'fusion_quantity': 2, 'rarity': 'Common', 'category': 'Water', 'families': ['Lizard', 'Reptile'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Axolotl Shard + Water Shard'}]}},
    {'id': 'C36', 'name': 'Miner Zombie', 'fusion_quantity': 5, 'rarity': 'Common', 'category': 'Combat', 'families': ['Cave Dweller'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': 'C33'}, 'acquisition': {'type': 'direct'}},
    {'id': 'U1', 'name': 'Bramble', 'fusion_quantity': 2, 'rarity': 'Uncommon', 'category': 'Forest', 'families': ['Elemental'], 'fusion_results': {'base': 'U10'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Uncommon Forest Shard + Rare+ Shard'}]}},
    {'id': 'U2', 'name': 'Tide', 'fusion_quantity': 2, 'rarity': 'Uncommon', 'category': 'Water', 'families': ['Elemental'], 'fusion_results': {'base': 'U11'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Uncommon Water Shard + Rare+ Shard'}]}},
    {'id': 'U3', 'name': 'Quake', 'fusion_quantity': 2, 'rarity': 'Uncommon', 'category': 'Combat', 'families': ['Elemental'], 'fusion_results': {'base': 'U12'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Uncommon Combat Shard + Rare+ Shard'}]}},
    {'id': 'U4', 'name': 'Sparrow', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Forest', 'families': ['Bird'], 'fusion_results': {'base': 'U10'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'direct'}},
    {'id': 'U5', 'name': 'Goldfin', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Water', 'families': [], 'fusion_results': {'base': 'U11'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Golden Ghoul Shard + Water Shard'}]}},
    {'id': 'U6', 'name': 'Troglobyte', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Combat', 'families': ['Cave Dweller'], 'fusion_results': {'base': 'U12'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Cave Dweller Shard + Combat Shard'}]}},
    {'id': 'U7', 'name': 'Hideoncave', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Forest', 'families': ['Shulker'], 'fusion_results': {'base': 'U10'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Cave Dweller Shard + Shulker Shard'}]}},
    {'id': 'U8', 'name': 'Salamander', 'fusion_quantity': 2, 'rarity': 'Uncommon', 'category': 'Water', 'families': ['Lizard', 'Reptile'], 'fusion_results': {'base': 'U11'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Lizard Shard + Water Shard'}]}},
    {'id': 'U9', 'name': 'Cuboa', 'fusion_quantity': 2, 'rarity': 'Uncommon', 'category': 'Combat', 'families': ['Reptile', 'Serpent'], 'fusion_results': {'base': 'U12'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Shulker Shard + Reptile Shard'}]}},
    {'id': 'U10', 'name': 'Pest', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Forest', 'families': ['Bug'], 'fusion_results': {'base': 'U25'}, 'fusion_sources': {'base': ['U1', 'U4', 'U7']}, 'acquisition': {'type': 'direct'}},
    {'id': 'U11', 'name': 'Mossybit', 'fusion_quantity': 2, 'rarity': 'Uncommon', 'category': 'Water', 'families': ['Amphibian', 'Frog'], 'fusion_results': {'base': 'U20'}, 'fusion_sources': {'base': ['U2', 'U5', 'U8']}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Tadgang Shard + Forest Shard'}]}},
    {'id': 'U12', 'name': 'Rain Slime', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'U15'}, 'fusion_sources': {'base': ['U3', 'U6', 'U9']}, 'acquisition': {'type': 'direct'}},
    {'id': 'U15', 'name': 'Seer', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'U18'}, 'fusion_sources': {'base': 'U12'}, 'acquisition': {'type': 'direct'}},
    {'id': 'U16', 'name': 'Heron', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Forest', 'families': ['Bird'], 'fusion_results': {'base': 'U25'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'direct'}, 'shop_cost': {'currency': 'AGATHA_COUPON', 'currency_name': "Agatha's Coupon", 'amount': 15}},
    {'id': 'U18', 'name': 'Obsidian Defender', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'U24'}, 'fusion_sources': {'base': 'U15'}, 'acquisition': {'type': 'direct'}},
    {'id': 'U20', 'name': 'Salmon', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Water', 'families': [], 'fusion_results': {'base': 'U29'}, 'fusion_sources': {'base': 'U11'}, 'acquisition': {'type': 'direct'}},
    {'id': 'U21', 'name': 'Viper', 'fusion_quantity': 2, 'rarity': 'Uncommon', 'category': 'Combat', 'families': ['Reptile', 'Serpent'], 'fusion_results': {'base': 'U24'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Cuboa Shard + Combat Shard'}]}},
    {'id': 'U22', 'name': 'Praying Mantis', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Forest', 'families': ['Bug'], 'fusion_results': {'base': 'U25'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Pest Shard + Pest Shard'}]}},
    {'id': 'U24', 'name': 'Zombie Soldier', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'U27'}, 'fusion_sources': {'base': ['U18', 'U21']}, 'acquisition': {'type': 'direct'}},
    {'id': 'U25', 'name': 'Bambuleaf', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Forest', 'families': ['Panda'], 'fusion_results': {'base': 'U31'}, 'fusion_sources': {'base': ['U10', 'U16', 'U22']}, 'acquisition': {'type': 'direct'}},
    {'id': 'U27', 'name': 'Sycophant', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'U30'}, 'fusion_sources': {'base': 'U24'}, 'acquisition': {'type': 'direct'}},
    {'id': 'U28', 'name': 'Seagull', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Forest', 'families': ['Bird'], 'fusion_results': {'base': 'U31'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'direct'}},
    {'id': 'U29', 'name': 'Ent', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Water', 'families': [], 'fusion_results': {'base': 'U32'}, 'fusion_sources': {'base': 'U20'}, 'acquisition': {'type': 'direct'}},
    {'id': 'U30', 'name': 'Soul of the Alpha', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'U33'}, 'fusion_sources': {'base': 'U27'}, 'acquisition': {'type': 'direct'}},
    {'id': 'U31', 'name': 'Mochibear', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Forest', 'families': ['Panda'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': ['U25', 'U28']}, 'acquisition': {'type': 'direct'}},
    {'id': 'U32', 'name': 'Magma Slug', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Water', 'families': [], 'fusion_results': {'base': 'U38'}, 'fusion_sources': {'base': 'U29'}, 'acquisition': {'type': 'direct'}},
    {'id': 'U33', 'name': 'Flaming Spider', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'U36'}, 'fusion_sources': {'base': 'U30'}, 'acquisition': {'type': 'direct'}},
    {'id': 'U34', 'name': 'Kiwi', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Forest', 'families': ['Bird'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Bird Shard + Uncommon+ Shard'}]}},
    {'id': 'U36', 'name': 'Bruiser', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Combat', 'families': [], 'fusion_results': {'base': None}, 'fusion_sources': {'base': 'U33'}, 'acquisition': {'type': 'direct'}},
    {'id': 'U38', 'name': 'Stridersurfer', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Water', 'families': ['Drowned'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': 'U32'}, 'acquisition': {'type': 'direct'}},
    {'id': 'U39', 'name': 'Rana', 'fusion_quantity': 2, 'rarity': 'Uncommon', 'category': 'Combat', 'families': ['Amphibian', 'Frog'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Frog Shard + Combat Shard'}]}},
    {'id': 'U40', 'name': 'Termite', 'fusion_quantity': 5, 'rarity': 'Uncommon', 'category': 'Forest', 'families': ['Bug'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Bug Shard + Praying Mantis Shard'}]}},
    {'id': 'R1', 'name': 'Sylvan', 'fusion_quantity': 2, 'rarity': 'Rare', 'category': 'Forest', 'families': ['Elemental'], 'fusion_results': {'base': 'R7'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Rare Forest Shard + Epic+ Shard'}]}},
    {'id': 'R2', 'name': 'Cascade', 'fusion_quantity': 2, 'rarity': 'Rare', 'category': 'Water', 'families': ['Elemental'], 'fusion_results': {'base': 'R11'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Rare Water Shard + Epic+ Shard'}]}},
    {'id': 'R3', 'name': 'Bolt', 'fusion_quantity': 2, 'rarity': 'Rare', 'category': 'Combat', 'families': ['Elemental'], 'fusion_results': {'base': 'R6'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Rare Combat Shard + Epic+ Shard'}]}},
    {'id': 'R4', 'name': 'Bambloom', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Forest', 'families': ['Panda'], 'fusion_results': {'base': 'R7'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Panda Shard + Uncommon+ Shard'}]}},
    {'id': 'R5', 'name': 'Toad', 'fusion_quantity': 2, 'rarity': 'Rare', 'category': 'Water', 'families': ['Amphibian', 'Frog'], 'fusion_results': {'base': 'R11'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Frog Shard + Uncommon+ Forest Shard'}]}},
    {'id': 'R6', 'name': 'Glacite Walker', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'R18'}, 'fusion_sources': {'base': 'R3'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R7', 'name': 'Beaconmite', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Forest', 'families': ['Bug'], 'fusion_results': {'base': 'R10'}, 'fusion_sources': {'base': ['R1', 'R4']}, 'acquisition': {'type': 'direct'}},
    {'id': 'R8', 'name': 'Lizard King', 'fusion_quantity': 2, 'rarity': 'Rare', 'category': 'Water', 'families': ['Lizard', 'Reptile'], 'fusion_results': {'base': 'R11'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Lizard Shard + Uncommon+ Water Shard'}]}},
    {'id': 'R9', 'name': 'Python', 'fusion_quantity': 2, 'rarity': 'Rare', 'category': 'Combat', 'families': ['Reptile', 'Serpent'], 'fusion_results': {'base': 'R18'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Viper Shard + Uncommon+ Combat Shard'}]}},
    {'id': 'R10', 'name': 'Invisibug', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Forest', 'families': ['Bug'], 'fusion_results': {'base': 'R49'}, 'fusion_sources': {'base': 'R7'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R11', 'name': 'Piranha', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Water', 'families': ['Treasure Fish'], 'fusion_results': {'base': 'R23'}, 'fusion_sources': {'base': ['R2', 'R5', 'R8']}, 'acquisition': {'type': 'direct'}},
    {'id': 'R13', 'name': 'Hideongeon', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Forest', 'families': ['Shulker'], 'fusion_results': {'base': 'R49'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Shulker Shard + Wither Shard'}]}},
    {'id': 'R15', 'name': 'Lapis Skeleton', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Combat', 'families': ['Lapis'], 'fusion_results': {'base': 'R18'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Lapis Zombie Shard + Rare+ Shard'}]}},
    {'id': 'R16', 'name': 'Cropeetle', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Forest', 'families': ['Bug'], 'fusion_results': {'base': 'R49'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Forest Shard + Invisibug Shard', 'components': ['Forest', '+', 'Invisibug']}, {'recipe_string': 'Forest Shard + Termite Shard', 'components': ['Forest', '+', 'Termite']}]}},
    {'id': 'R18', 'name': 'Drowned', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'R21'}, 'fusion_sources': {'base': ['R6', 'R9', 'R15']}, 'acquisition': {'type': 'direct'}},
    {'id': 'R21', 'name': 'Star Sentry', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'R24'}, 'fusion_sources': {'base': 'R18'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R22', 'name': 'Hideondra', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Forest', 'families': ['Shulker'], 'fusion_results': {'base': 'R49'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Shulker Shard + Demon Shard'}]}},
    {'id': 'R23', 'name': 'Abyssal Lanternfish', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Water', 'families': ['Treasure Fish'], 'fusion_results': {'base': 'R29'}, 'fusion_sources': {'base': 'R11'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R24', 'name': 'Arachne', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Combat', 'families': ['Spider'], 'fusion_results': {'base': 'R27'}, 'fusion_sources': {'base': 'R21'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R25', 'name': 'Bitbug', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Forest', 'families': ['Bug'], 'fusion_results': {'base': 'R49'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'direct'}},
    {'id': 'R27', 'name': 'Revenant', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'R30'}, 'fusion_sources': {'base': 'R24'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R29', 'name': 'Silentdepth', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Water', 'families': ['Treasure Fish'], 'fusion_results': {'base': 'R35'}, 'fusion_sources': {'base': 'R23'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R30', 'name': 'Skeletor', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'R31'}, 'fusion_sources': {'base': 'R27'}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Lapis Skeleton Shard + Rare+ Shard'}]}},
    {'id': 'R31', 'name': 'Thyst', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Combat', 'families': ['Cave Dweller'], 'fusion_results': {'base': 'R36'}, 'fusion_sources': {'base': 'R30'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R33', 'name': 'Quartzfang', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Combat', 'families': ['Cave Dweller'], 'fusion_results': {'base': 'R36'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Troglobyte Shard + Cave Dweller Shard'}]}},
    {'id': 'R34', 'name': 'Hideonring', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Forest', 'families': ['Shulker'], 'fusion_results': {'base': 'R49'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Rare+ Shulker Shard + Rare+ Shard'}]}},
    {'id': 'R35', 'name': 'Snowfin', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Water', 'families': ['Treasure Fish'], 'fusion_results': {'base': 'R38'}, 'fusion_sources': {'base': 'R29'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R36', 'name': 'Kada Knight', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'R39'}, 'fusion_sources': {'base': ['R31', 'R33']}, 'acquisition': {'type': 'direct'}},
    {'id': 'R38', 'name': 'Carrot King', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Water', 'families': [], 'fusion_results': {'base': 'R44'}, 'fusion_sources': {'base': 'R35'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R39', 'name': 'Wither Specter', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'R42'}, 'fusion_sources': {'base': 'R36'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R42', 'name': 'Matcho', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'R45'}, 'fusion_sources': {'base': 'R39'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R43', 'name': 'Ladybug', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Forest', 'families': ['Bug'], 'fusion_results': {'base': 'R49'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Cropeetle Shard + Bug Shard'}]}},
    {'id': 'R44', 'name': 'Lumisquid', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Water', 'families': ['Squid'], 'fusion_results': {'base': 'R50'}, 'fusion_sources': {'base': 'R38'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R45', 'name': 'Crocodile', 'fusion_quantity': 2, 'rarity': 'Rare', 'category': 'Combat', 'families': ['Croco', 'Reptile'], 'fusion_results': {'base': 'R57'}, 'fusion_sources': {'base': 'R42'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R46', 'name': 'Bullfrog', 'fusion_quantity': 2, 'rarity': 'Rare', 'category': 'Water', 'families': ['Amphibian', 'Frog'], 'fusion_results': {'base': 'R50'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Frog Shard + Rare+ Forest Shard'}]}},
    {'id': 'R49', 'name': 'Dreadwing', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Forest', 'families': ['Phantom'], 'fusion_results': {'base': 'R52'}, 'fusion_sources': {'base': ['R10', 'R13', 'R16', 'R22', 'R25', 'R34', 'R43']}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Rare+ Shard + Phanpyre Shard'}, {'recipe_string': 'Rare+ Shard + Phanflare Shard'}]}},
    {'id': 'R50', 'name': 'Joydive', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Water', 'families': [], 'fusion_results': {'base': 'R53'}, 'fusion_sources': {'base': ['R44', 'R46']}, 'acquisition': {'type': 'direct'}},
    {'id': 'R51', 'name': 'Stalagmight', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Combat', 'families': ['Cave Dweller'], 'fusion_results': {'base': 'R57'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Quartzfang Shard + Cave Dweller Shard'}]}},
    {'id': 'R52', 'name': 'Fungloom', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Forest', 'families': ['Cave Dweller'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': 'R49'}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Cave Dweller Shard + Epic+ Forest Shard'}]}},
    {'id': 'R53', 'name': 'Eel', 'fusion_quantity': 2, 'rarity': 'Rare', 'category': 'Water', 'families': ['Amphibian', 'Eel'], 'fusion_results': {'base': 'R56'}, 'fusion_sources': {'base': 'R50'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R54', 'name': 'King Cobra', 'fusion_quantity': 2, 'rarity': 'Rare', 'category': 'Combat', 'families': ['Reptile', 'Serpent'], 'fusion_results': {'base': 'R57'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Python Shard + Uncommon+ Combat Shard'}]}},
    {'id': 'R56', 'name': 'Lava Flame', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Water', 'families': [], 'fusion_results': {'base': 'R59'}, 'fusion_sources': {'base': 'R53'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R57', 'name': 'Draconic', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Combat', 'families': ['Dragon'], 'fusion_results': {'base': 'R60'}, 'fusion_sources': {'base': ['R45', 'R51', 'R54']}, 'acquisition': {'type': 'direct'}},
    {'id': 'R58', 'name': 'Falcon', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Forest', 'families': ['Bird'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion', 'details': [{'recipe_string': 'Bird Shard + Rare+ Shard'}]}},
    {'id': 'R59', 'name': 'Inferno Koi', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Water', 'families': ['Treasure Fish'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': 'R56'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R60', 'name': 'Wither', 'fusion_quantity': 5, 'rarity': 'Rare', 'category': 'Combat', 'families': ['Dragon'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': 'R57'}, 'acquisition': {'type': 'direct'}},
    {'id': 'R61', 'name': 'Gecko', 'fusion_quantity': 2, 'rarity': 'Rare', 'category': 'Forest', 'families': ['Reptile', 'Scaled'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'direct'}},
    {'id': 'E1', 'name': 'Terra', 'fusion_quantity': 2, 'rarity': 'Epic', 'category': 'Forest', 'families': ['Elemental'], 'fusion_results': {'base': 'E34'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E2', 'name': 'Cryo', 'fusion_quantity': 2, 'rarity': 'Epic', 'category': 'Water', 'families': ['Elemental'], 'fusion_results': {'base': 'E17'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E3', 'name': 'Aero', 'fusion_quantity': 2, 'rarity': 'Epic', 'category': 'Combat', 'families': ['Elemental'], 'fusion_results': {'base': 'E12'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E4', 'name': 'Pandarai', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Forest', 'families': ['Panda'], 'fusion_results': {'base': 'E34'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E5', 'name': 'Leviathan', 'fusion_quantity': 2, 'rarity': 'Epic', 'category': 'Water', 'families': ['Lizard', 'Reptile'], 'fusion_results': {'base': 'E17'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E6', 'name': 'Alligator', 'fusion_quantity': 2, 'rarity': 'Epic', 'category': 'Combat', 'families': ['Croco', 'Reptile'], 'fusion_results': {'base': 'E12'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E7', 'name': 'Fenlord', 'fusion_quantity': 2, 'rarity': 'Epic', 'category': 'Water', 'families': ['Amphibian', 'Frog'], 'fusion_results': {'base': 'E17'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E9', 'name': 'Basilisk', 'fusion_quantity': 2, 'rarity': 'Epic', 'category': 'Combat', 'families': ['Reptile', 'Serpent'], 'fusion_results': {'base': 'E12'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E10', 'name': 'Iguana', 'fusion_quantity': 2, 'rarity': 'Epic', 'category': 'Forest', 'families': ['Reptile', 'Scaled'], 'fusion_results': {'base': 'E34'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E11', 'name': 'Moray Eel', 'fusion_quantity': 2, 'rarity': 'Epic', 'category': 'Water', 'families': ['Amphibian', 'Eel'], 'fusion_results': {'base': 'E17'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E12', 'name': 'Thorn', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'E15'}, 'fusion_sources': {'base': ['E3', 'E6', 'E9']}, 'acquisition': {'type': 'direct'}},
    {'id': 'E13', 'name': 'Lunar Moth', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Forest', 'families': ['Bug'], 'fusion_results': {'base': 'E34'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E14', 'name': 'Fire Eel', 'fusion_quantity': 2, 'rarity': 'Epic', 'category': 'Water', 'families': ['Amphibian', 'Eel'], 'fusion_results': {'base': 'E17'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E15', 'name': 'Bal', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Combat', 'families': ['Cave Dweller'], 'fusion_results': {'base': 'E18'}, 'fusion_sources': {'base': 'E12'}, 'acquisition': {'type': 'direct'}},
    {'id': 'E16', 'name': 'Hideonsack', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Forest', 'families': ['Shulker'], 'fusion_results': {'base': 'E34'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E17', 'name': 'Water Hydra', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Water', 'families': [], 'fusion_results': {'base': 'E20'}, 'fusion_sources': {'base': ['E2', 'E5', 'E7', 'E11', 'E14']}, 'acquisition': {'type': 'direct'}},
    {'id': 'E18', 'name': 'Flare', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'E21'}, 'fusion_sources': {'base': 'E15'}, 'acquisition': {'type': 'direct'}},
    {'id': 'E20', 'name': 'Sea Emperor', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Water', 'families': [], 'fusion_results': {'base': 'E26'}, 'fusion_sources': {'base': 'E17'}, 'acquisition': {'type': 'direct'}},
    {'id': 'E21', 'name': 'Prince', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'E24'}, 'fusion_sources': {'base': 'E18'}, 'acquisition': {'type': 'direct'}},
    {'id': 'E22', 'name': 'Komodo Dragon', 'fusion_quantity': 2, 'rarity': 'Epic', 'category': 'Forest', 'families': ['Reptile', 'Scaled'], 'fusion_results': {'base': 'E34'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E24', 'name': 'Mimic', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'E27'}, 'fusion_sources': {'base': 'E21'}, 'acquisition': {'type': 'direct'}},
    {'id': 'E26', 'name': 'Shellwise', 'fusion_quantity': 2, 'rarity': 'Epic', 'category': 'Water', 'families': ['Reptile', 'Turtle'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': 'E20'}, 'acquisition': {'type': 'direct'}},
    {'id': 'E27', 'name': 'Barbarian Duke X', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'E29'}, 'fusion_sources': {'base': 'E24'}, 'acquisition': {'type': 'direct'}},
    {'id': 'E28', 'name': 'Toucan', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Forest', 'families': ['Bird'], 'fusion_results': {'base': 'E34'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E29', 'name': 'Hellwisp', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Combat', 'families': [], 'fusion_results': {'base': 'E33'}, 'fusion_sources': {'base': 'E27'}, 'acquisition': {'type': 'direct'}},
    {'id': 'E30', 'name': 'Caiman', 'fusion_quantity': 2, 'rarity': 'Epic', 'category': 'Combat', 'families': ['Croco', 'Reptile'], 'fusion_results': {'base': 'E33'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E31', 'name': 'Firefly', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Forest', 'families': ['Bug'], 'fusion_results': {'base': 'E34'}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E32', 'name': 'Sea Serpent', 'fusion_quantity': 2, 'rarity': 'Epic', 'category': 'Water', 'families': ['Amphibian', 'Eel', 'Serpent'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E33', 'name': 'Ghost', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Combat', 'families': ['Cave Dweller'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': ['E29', 'E30']}, 'acquisition': {'type': 'direct'}},
    {'id': 'E34', 'name': 'XYZ', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Forest', 'families': [], 'fusion_results': {'base': None}, 'fusion_sources': {'base': ['E1', 'E4', 'E10', 'E13', 'E16', 'E22', 'E28', 'E31']}, 'acquisition': {'type': 'direct'}},
    {'id': 'E35', 'name': 'Leatherback', 'fusion_quantity': 2, 'rarity': 'Epic', 'category': 'Water', 'families': ['Reptile', 'Turtle'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E36', 'name': 'Cavernshade', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Combat', 'families': ['Cave Dweller'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
    {'id': 'E37', 'name': 'Dragonfly', 'fusion_quantity': 5, 'rarity': 'Epic', 'category': 'Forest', 'families': ['Bug'], 'fusion_results': {'base': None}, 'fusion_sources': {'base': None}, 'acquisition': {'type': 'fusion'}},
]

# ── Lookups ───────────────────────────────────────────────────────────────
shard_by_id = {s['id']: s for s in shards_data}
shard_by_name = {s['name'].lower(): s for s in shards_data}

# ── Hunt method metadata ──────────────────────────────────────────────────
# Every direct-acquisition shard's hunting method, parsed from wiki data
# files (data/wiki/Attributes_SLASH_List_SLASH_{Common,Uncommon,Rare,Epic}.wiki).
#
# Fields:
#   summary  — one-line description of how to acquire this shard
#   tier     — farming ease tier (S/A/B/C) or None if rate unknown
#   evidence — why this tier was assigned (sources, reasoning)
#
# Tiers (recalibrated — old S=20/hr ceiling was wrong):
#   S = ~30/hr — multi-method Galatea, trivial capture, or player-verified fast
#   A = ~15/hr — solid Galatea methods, reliable spawns
#   B = ~6/hr  — zone-locked, seasonal, single-method, or non-Galatea traps
#   C = ~2/hr  — salt-only, boss/dungeon drops, seasonal-restricted, rare
#
# Rate calibration: Glacite Walker (Huntaxe + Salt, Dwarven Mines) is
# player-verified as "way more than 20/hr" — fast spawns, only bottleneck
# is Black Hole cooldown. This pushes S-tier to ~30/hr.
#
# Unrated shards (tier=None) have known methods but unknown spawn rates.
# They are EXCLUDED from coins/hr rankings but their method info is shown.
HUNT_INFO = {
    # ══════════════════════════════════════════════════════════════════════
    # COMMON (22 direct shards)
    # ══════════════════════════════════════════════════════════════════════

    # ── Galatea active hunting (Lasso/Net — you find and capture the mob) ──
    'Birries': {
        'summary': 'Traps (Galatea land) · Net · Lasso',
        'tier': 'A', 'evidence': 'active Lasso/Net capture on Galatea land',
    },
    'Coralot': {
        'summary': 'Traps (Murkwater underwater) · Net · Lasso',
        'tier': 'A', 'evidence': '15 contest pts, active Lasso capture on Galatea',
    },

    # ── Trap + Fishing (passive traps ~1/day, fishing ~4-5/hr) ──
    'Verdant': {
        'summary': 'Traps (Murkwater underwater) · Fishing (Tomb Floodway) · Net',
        'tier': 'B', 'evidence': 'trap+fishing — traps ~1/day, fishing ~4-5/hr (player est.)',
    },
    'Azure': {
        'summary': 'Traps (Murkwater underwater) · Fishing (Tomb Floodway)',
        'tier': 'B', 'evidence': 'trap+fishing — traps ~1/day, fishing ~4-5/hr (player est.)',
    },
    'Cod': {
        'summary': 'Traps (Murkwater underwater) · Fishing (Tomb Floodway) · Net',
        'tier': 'B', 'evidence': 'trap+fishing — traps ~1/day, fishing ~4-5/hr (player est.)',
    },

    # ── Galatea Lasso/Traps + Tree Gifts ──
    'Phanpyre': {
        'summary': 'Lasso · Traps (Galatea land) · Fig/Mangrove Tree Gifts',
        'tier': 'A', 'evidence': '11.8% tree spawn rate + lasso + traps',
    },
    'Phanflare': {
        'summary': 'Lasso · Traps (Galatea land) · Fig/Mangrove Tree Gifts',
        'tier': 'A', 'evidence': '7.1% tree spawn rate + lasso + traps',
    },

    # ── Galatea hunt (Lasso/Black Holes) ──
    'Hideonleaf': {
        'summary': 'Hunt Hideonleafs on Galatea (Lasso)',
        'tier': 'A', 'evidence': 'Galatea Forest/Shulker, wiki says "Hunting in Galatea"',
    },

    # ── Galatea Black Holes/Salt + Traps ──
    'Tadgang': {
        'summary': 'Black Holes/Salt · Traps (Murkwater underwater)',
        'tier': 'A', 'evidence': 'Galatea Water/Frog, BH + trap support',
    },
    'Chill': {
        'summary': 'Black Holes/Salt (Chillshot/Chillblade) · Traps (Wyrmgrove Tomb)',
        'tier': 'B', 'evidence': 'Galatea zone-specific (Wyrmgrove Tomb), BH + traps',
    },

    # ── Galatea Traps + Grass ──
    'Mudworm': {
        'summary': 'Traps (Galatea land) · Found in Grass on Galatea',
        'tier': 'B', 'evidence': '45 contest pts, hard to find despite being common',
    },

    # ── Non-Galatea Huntaxe + Salt ──
    'Night Squid': {
        'summary': 'Black Holes/Salt on Night Squid',
        'tier': None, 'evidence': 'BH/Salt, location not specified in wiki',
    },
    'Lapis Zombie': {
        'summary': 'Black Holes/Salt on Lapis Zombies (Deep Caverns)',
        'tier': None, 'evidence': 'BH/Salt, non-Galatea — spawn rate unknown',
    },
    'Voracious Spider': {
        'summary': "Black Holes/Salt on Voracious Spider (Spider's Den)",
        'tier': None, 'evidence': 'BH/Salt, non-Galatea — spawn rate unknown',
    },
    'Zealot': {
        'summary': 'Black Holes/Salt on Zealots (The End)',
        'tier': None, 'evidence': 'BH/Salt, non-Galatea — spawn rate unknown',
    },
    'Golden Ghoul': {
        'summary': 'Black Holes/Salt on Golden Ghoul (Hub)',
        'tier': None, 'evidence': 'BH/Salt, rare Hub spawn — rate unknown',
    },
    'Bezal': {
        'summary': 'Black Holes/Salt on Bezal (Crimson Isle) · also Kuudra',
        'tier': None, 'evidence': 'BH/Salt, non-Galatea — spawn rate unknown',
    },
    'Yog': {
        'summary': 'Black Holes/Salt on Yog (Crystal Hollows)',
        'tier': None, 'evidence': 'BH/Salt, non-Galatea — spawn rate unknown',
    },
    'Miner Zombie': {
        'summary': 'Black Holes/Salt on Miner Zombie (Dwarven Mines)',
        'tier': None, 'evidence': 'BH/Salt, non-Galatea — spawn rate unknown',
    },

    # ── Salt-only ──
    'Tank Zombie': {
        'summary': 'Salt only — kill Crypt Tank Zombies (Hub Crypts)',
        'tier': 'C', 'evidence': 'salt-only, worst active method, Hub Crypts',
    },

    # ── Shop ──
    'Crow': {
        'summary': "Agatha's Shop (15 coupons)",
        'tier': None, 'evidence': 'shop-bought, economics depend on coupon value',
    },

    # ── Wiki-missing (no wiki entry found) ──
    'Sea Archer': {
        'summary': 'Method unknown (not in wiki data)',
        'tier': None, 'evidence': 'no wiki entry found for this shard',
    },

    # ══════════════════════════════════════════════════════════════════════
    # UNCOMMON (18 direct shards)
    # ══════════════════════════════════════════════════════════════════════

    # ── Galatea multi-method ──
    'Pest': {
        'summary': 'Black Holes/Lasso/Salt on Garden pests (Cricket, Fly, etc.)',
        'tier': 'A', 'evidence': 'Galatea Forest/Bug, 3 capture methods',
    },
    'Salmon': {
        'summary': 'Traps (Murkwater underwater) · Fishing (Tomb Floodway) · Net',
        'tier': 'B', 'evidence': 'trap+fishing — traps ~1/day, fishing ~4-5/hr (player est.)',
    },

    # ── Galatea Black Holes/Salt + Traps ──
    'Ent': {
        'summary': 'Black Holes/Salt · Traps (Murkwater underwater)',
        'tier': 'B', 'evidence': 'Galatea BH + traps, density unverified',
    },

    # ── Galatea seasonal ──
    'Bambuleaf': {
        'summary': 'Traps (Tranquility Sanctum, Spring/Summer) · Pandas on Galatea',
        'tier': 'B', 'evidence': 'seasonal restriction (Spring/Summer only)',
    },
    'Mochibear': {
        'summary': 'Traps (Tranquility Sanctum, Autumn/Winter) · Pandas on Galatea',
        'tier': 'C', 'evidence': 'seasonal restriction (Autumn/Winter only)',
    },

    # ── Non-Galatea Huntaxe + Salt ──
    'Rain Slime': {
        'summary': "Black Holes/Salt on Rain/Toxic Rain Slime (Spider's Den)",
        'tier': None, 'evidence': 'BH/Salt, non-Galatea — spawn rate unknown',
    },
    'Seer': {
        'summary': 'Black Holes/Salt on Seer (The End)',
        'tier': None, 'evidence': 'BH/Salt, non-Galatea — spawn rate unknown',
    },
    'Obsidian Defender': {
        'summary': 'Black Holes/Salt on Obsidian Defender (Obsidian Sanctuary)',
        'tier': None, 'evidence': 'BH/Salt, non-Galatea — spawn rate unknown',
    },
    'Sycophant': {
        'summary': 'Black Holes/Salt on Revenant Sycophant (Hub)',
        'tier': None, 'evidence': 'BH/Salt, non-Galatea — spawn rate unknown',
    },
    'Flaming Spider': {
        'summary': "Black Holes/Salt on Flaming Spider (Spider's Den)",
        'tier': None, 'evidence': 'BH/Salt, non-Galatea — spawn rate unknown',
    },
    'Bruiser': {
        'summary': 'Black Holes/Salt on Zealot Bruiser (The End)',
        'tier': None, 'evidence': 'BH/Salt, non-Galatea — spawn rate unknown',
    },

    # ── Non-Galatea Huntaxe + Salt + Traps ──
    'Soul of the Alpha': {
        'summary': 'Black Holes/Salt · Traps (Howling Cave)',
        'tier': None, 'evidence': 'BH/Salt + trap, non-Galatea — rate unknown',
    },
    'Magma Slug': {
        'summary': 'Black Holes/Salt · Kuudra · Traps (Crimson Isle, under lava)',
        'tier': None, 'evidence': 'BH/Salt + Kuudra alt + trap, non-Galatea',
    },
    'Stridersurfer': {
        'summary': 'Black Holes/Salt (Strider Surfer) · Traps (Stride-Ember Fissure)',
        'tier': 'C', 'evidence': 'dedicated non-Galatea zone, BH + traps',
    },

    # ── Salt-only ──
    'Zombie Soldier': {
        'summary': 'Salt only — kill Zombie Knight/Soldier/Commander/Lord (Catacombs)',
        'tier': 'C', 'evidence': 'salt-only, dungeon mobs',
    },

    # ── Shop ──
    'Heron': {
        'summary': "Agatha's Shop (15 coupons)",
        'tier': None, 'evidence': 'shop-bought, economics depend on coupon value',
    },

    # ── Collection rewards ──
    'Sparrow': {
        'summary': 'Fig Log VII collection reward',
        'tier': None, 'evidence': 'collection unlock, not farmable per se',
    },
    'Seagull': {
        'summary': 'Mangrove Log VI collection reward',
        'tier': None, 'evidence': 'collection unlock, not farmable per se',
    },

    # ══════════════════════════════════════════════════════════════════════
    # RARE (26 direct shards)
    # ══════════════════════════════════════════════════════════════════════

    # ── Galatea Traps/Fish ──
    'Piranha': {
        'summary': 'Traps (Murkwater underwater) · Fishing (Moonglade Marsh)',
        'tier': 'B', 'evidence': 'trap+fishing — traps ~1/day, fishing ~4-5/hr (player est.)',
    },
    'Lumisquid': {
        'summary': 'Traps (Squid Cave, underwater) · Net',
        'tier': 'B', 'evidence': 'trap+net, zone-locked (Squid Cave) — traps ~1/day',
    },
    'Joydive': {
        'summary': 'Traps (Murkwater Depths, underwater) · Net',
        'tier': 'B', 'evidence': 'trap+net — traps ~1/day',
    },

    # ── Galatea Traps + Grass ──
    'Invisibug': {
        'summary': 'Traps (Galatea land) · Found in Grass on Galatea',
        'tier': 'B', 'evidence': 'same method as Mudworm — trap + grass',
    },

    # ── Galatea Black Holes/Salt + Traps ──
    'Drowned': {
        'summary': 'Black Holes/Salt (Seacurse/Hydrospear/Tidetot) · Traps (Drowned Reliquary)',
        'tier': 'B', 'evidence': 'Galatea zone-specific (Drowned Reliquary), BH + traps',
    },

    # ── Non-Galatea Traps/Fishing ──
    'Abyssal Lanternfish': {
        'summary': 'Traps (Dwarven Mines, underwater) · Fishing (Dwarven Mines)',
        'tier': 'B', 'evidence': 'non-Galatea trap + fishing, Dwarven Mines',
    },
    'Silentdepth': {
        'summary': 'Traps (Crystal Hollows, underwater) · Fishing (Crystal Hollows)',
        'tier': 'B', 'evidence': 'non-Galatea trap + fishing, Crystal Hollows',
    },
    'Snowfin': {
        'summary': "Traps (Jerry's Workshop, underwater)",
        'tier': 'C', 'evidence': "trap-only, Jerry's Workshop — possibly seasonal",
    },
    'Inferno Koi': {
        'summary': 'Traps (Crimson Isle, under lava) · Fishing (Crimson Isle)',
        'tier': 'B', 'evidence': 'non-Galatea trap + fishing, Crimson Isle',
    },

    # ── Non-Galatea Huntaxe + Salt (player-verified) ──
    'Glacite Walker': {
        'summary': 'Black Holes/Salt on Glacite Walker (Dwarven Mines)',
        'tier': 'S', 'evidence': 'PLAYER VERIFIED: "way more than 20/hr" — fast spawns',
    },

    # ── Non-Galatea Huntaxe + Salt (rate unknown) ──
    'Star Sentry': {
        'summary': 'Black Holes/Salt on Star Sentry (Dwarven Mines)',
        'tier': None, 'evidence': 'BH/Salt, non-Galatea — spawn rate unknown',
    },
    'Carrot King': {
        'summary': 'Black Holes/Salt on Carrot King',
        'tier': None, 'evidence': 'BH/Salt — spawn rate unknown',
    },

    # ── Non-Galatea Huntaxe + Salt + Kuudra alt ──
    'Thyst': {
        'summary': 'Black Holes/Salt · Traps (Crystal Hollows)',
        'tier': None, 'evidence': 'BH/Salt + trap, non-Galatea — rate unknown',
    },
    'Kada Knight': {
        'summary': 'Black Holes/Salt · also Kuudra',
        'tier': None, 'evidence': 'BH/Salt + Kuudra alt — rate unknown',
    },
    'Wither Specter': {
        'summary': 'Black Holes/Salt on Wither Spectre · also Kuudra',
        'tier': None, 'evidence': 'BH/Salt + Kuudra alt — rate unknown',
    },
    'Matcho': {
        'summary': 'Black Holes/Salt · also Kuudra',
        'tier': None, 'evidence': 'BH/Salt + Kuudra alt — rate unknown',
    },
    'Lava Flame': {
        'summary': 'Black Holes/Salt · Kuudra · Traps (Crimson Isle, under lava)',
        'tier': None, 'evidence': 'BH/Salt + Kuudra + trap, non-Galatea — rate unknown',
    },

    # ── Salt-only / Boss ──
    'Arachne': {
        'summary': "Salt only — kill Arachne boss (Spider's Den)",
        'tier': 'C', 'evidence': 'salt-only, boss mob',
    },

    # ── Boss / Dungeon drops ──
    'Revenant': {
        'summary': 'Dropped by Revenant Horror (slayer boss)',
        'tier': 'C', 'evidence': 'boss drop, rate depends on slayer tier',
    },
    'Draconic': {
        'summary': 'Dropped by Dragons in The End',
        'tier': 'C', 'evidence': 'boss drop, rare',
    },
    'Wither': {
        'summary': 'Catacombs Floor VII / Master Mode Floor VII',
        'tier': 'C', 'evidence': 'dungeon drop, F7/MM7',
    },

    # ── Beacon ──
    'Beaconmite': {
        'summary': 'Tuning the Moonglade Beacon (NOT a mob)',
        'tier': None, 'evidence': 'beacon mechanic, not farmable in traditional sense',
    },

    # ── Shop ──
    'Bitbug': {
        'summary': 'Purchased from Bits Shop',
        'tier': None, 'evidence': 'shop-bought (Bits), economics depend on bit value',
    },
    'Crocodile': {
        'summary': "Purchased from Kiara's Shop",
        'tier': None, 'evidence': 'shop-bought, cost unknown',
    },
    'Gecko': {
        'summary': "Purchased from Kiara's Shop",
        'tier': None, 'evidence': 'shop-bought, cost unknown',
    },
    'Eel': {
        'summary': "Kiara's Shop · Fishing (Moonglade Marsh)",
        'tier': None, 'evidence': 'shop + fishing dual source, economics unclear',
    },

    # ══════════════════════════════════════════════════════════════════════
    # EPIC (12 direct shards)
    # ══════════════════════════════════════════════════════════════════════

    # ── Galatea multi-method ──
    'XYZ': {
        'summary': 'Lasso/Salt (Atom) · Kuudra · Traps (Mystic Marsh) · Atominizer',
        'tier': 'C', 'evidence': 'Epic, many methods but all are endgame',
    },
    'Shellwise': {
        'summary': 'Traps (Murkwater Depths, underwater) · Net',
        'tier': 'C', 'evidence': '45 contest pts, Epic rarity',
    },

    # ── Non-Galatea Black Holes/Salt ──
    'Thorn': {
        'summary': 'Black Holes/Salt on Thorn (Epic Combat)',
        'tier': 'C', 'evidence': 'Epic mob, rate unknown',
    },
    'Water Hydra': {
        'summary': 'Black Holes/Salt on Water Hydra',
        'tier': 'C', 'evidence': 'Epic mob, rate unknown',
    },
    'Sea Emperor': {
        'summary': 'Black Holes/Salt on Loch Emperor',
        'tier': 'C', 'evidence': 'Epic mob, rate unknown (wiki: Loch Emperor)',
    },
    'Ghost': {
        'summary': 'Black Holes/Salt on Ghosts (Crystal Hollows)',
        'tier': 'C', 'evidence': 'Epic Cave Dweller, rate unknown',
    },

    # ── Non-Galatea Salt + Kuudra alt ──
    'Flare': {
        'summary': 'Black Holes/Salt · also Kuudra',
        'tier': 'C', 'evidence': 'Epic Infernal mob + Kuudra alt',
    },
    'Barbarian Duke X': {
        'summary': 'Black Holes/Salt · also Kuudra',
        'tier': 'C', 'evidence': 'Epic mob + Kuudra alt',
    },
    'Hellwisp': {
        'summary': 'Black Holes/Salt · also Kuudra',
        'tier': 'C', 'evidence': 'Epic mob + Kuudra alt',
    },

    # ── Salt-only / Boss ──
    'Bal': {
        'summary': 'Salt only — kill Bal boss (Crystal Hollows)',
        'tier': 'C', 'evidence': 'salt-only, Crystal Hollows boss',
    },
    'Prince': {
        'summary': 'Salt only — kill Princes (Catacombs)',
        'tier': 'C', 'evidence': 'salt-only, dungeon mob',
    },
    'Mimic': {
        'summary': 'Salt only — kill Mimic (Catacombs)',
        'tier': 'C', 'evidence': 'salt-only, dungeon mob',
    },
}

# ── Tier labels and rate estimates ────────────────────────────────────────
EASE_LABEL = {
    'S': '🟢 Very Easy',
    'A': '🔵 Easy',
    'B': '🟡 Moderate',
    'C': '🔴 Hard/Rare',
}

# Estimated shards/hr per tier (recalibrated from player data).
# Glacite Walker (BH+Salt, Dwarven Mines) = "way more than 20/hr",
# so multi-method Galatea mobs should be at least comparable.
# These are RELATIVE estimates for ranking — actual rates vary with
# gear, hunting level, and specific mob density.
EASE_RATE = {
    'S': 30,   # ~30/hr — player-verified fast (Glacite Walker) or trivial Galatea
    'A': 15,   # ~15/hr — solid methods, reliable spawns
    'B': 6,    # ~6/hr  — zone-locked, single method, dedicated effort
    'C': 2,    # ~2/hr  — rare spawns, boss drops, salt-only, endgame
}

# ── Backward compatibility helpers ───────────────────────────────────────
# FARM_EASE dict preserved for _build_farm_results lookup pattern
FARM_EASE = {name: info['tier'] for name, info in HUNT_INFO.items() if info['tier']}


BAZAAR_ID_OVERRIDES = {
    'Abyssal Lanternfish': 'SHARD_ABYSSAL_LANTERN',
    'Stridersurfer': 'SHARD_STRIDER_SURFER',
}


def shard_bazaar_id(name: str) -> str:
    """Convert shard name to its Bazaar product ID."""
    if name in BAZAAR_ID_OVERRIDES:
        return BAZAAR_ID_OVERRIDES[name]
    return 'SHARD_' + name.upper().replace(' ', '_').replace("'", '')


# ── Rarity helpers ────────────────────────────────────────────────────────
RARITY_ORDER = ['Common', 'Uncommon', 'Rare', 'Epic']
RARITY_SYMBOL = {'Common': '◇', 'Uncommon': '◆', 'Rare': '★', 'Epic': '✦'}


def rarity_tag(rarity: str) -> str:
    sym = RARITY_SYMBOL.get(rarity, '?')
    return f"{sym} {rarity}"


# ── Market data helpers ───────────────────────────────────────────────────
MIN_VOLUME = 500  # Below this = thin market


def get_shard_price(shard, cache: PriceCache) -> dict:
    """Get price data for a shard. Returns dict with sell, buy, buy_volume, sell_volume, healthy."""
    bz_id = shard_bazaar_id(shard['name'])
    p = cache.get_price(bz_id)
    if p['source'] != 'bazaar':
        return {'sell': 0, 'buy': 0, 'buy_volume': 0, 'sell_volume': 0, 'healthy': False, 'found': False}

    sell = p['sell'] or 0
    buy = p['buy'] or 0
    buy_vol = p['buy_volume'] or 0
    sell_vol = p['sell_volume'] or 0

    # A market is healthy if there are actual buyers for the shard
    # (buy_volume = people wanting to buy = you can sell into their orders)
    healthy = sell > 0 and buy_vol >= MIN_VOLUME

    return {
        'sell': sell,       # instant-sell price (what you get)
        'buy': buy,         # instant-buy price (what you pay)
        'buy_volume': buy_vol,
        'sell_volume': sell_vol,
        'healthy': healthy,
        'found': True,
    }


def market_warning(price_data: dict) -> str:
    """Return a market warning string, or empty if healthy."""
    if not price_data['found']:
        return "❌ NOT ON BAZAAR"
    if price_data['sell'] <= 0:
        return "❌ NO SELL PRICE"
    if price_data['buy_volume'] == 0:
        return "❌ ZERO BUY ORDERS"
    if price_data['buy_volume'] < MIN_VOLUME:
        return f"⚠️  THIN ({_fmt(price_data['buy_volume'])} buy vol)"
    # Flag extreme buy/sell spreads (>5:1 ratio means pricing is unreliable)
    if price_data['sell'] > 0 and price_data['buy'] > 0:
        spread_ratio = price_data['buy'] / price_data['sell']
        if spread_ratio > 5:
            return f"⚠️  WIDE SPREAD (sell {_fmt(price_data['sell'])} / buy {_fmt(price_data['buy'])})"
    return ""


# ── Opportunity cost (shop shards with tradeable currency) ────────────────
def get_opportunity_cost(shard, cache: PriceCache) -> dict | None:
    """Check if a shard has a shop cost with tradeable currency.

    Returns {currency_name, amount, unit_sell, total_sell, shard_sell, net}
    where net = shard_sell - total_sell (negative = selling currency is better).
    Returns None if the shard has no shop_cost.
    """
    shop = shard.get('shop_cost')
    if not shop:
        return None

    currency_id = shop['currency']
    amount = shop['amount']
    currency_name = shop['currency_name']

    if amount is None:
        # We know it's shop-bought but don't know the price yet
        return {'currency_name': currency_name, 'amount': None,
                'unit_sell': None, 'total_sell': None, 'shard_sell': None, 'net': None, 'unknown': True}

    p = cache.get_price(currency_id)
    if p['source'] != 'bazaar' or not p['sell']:
        return None

    unit_sell = p['sell']
    total_sell = amount * unit_sell
    shard_sell = get_shard_price(shard, cache)['sell']

    return {
        'currency_name': currency_name,
        'amount': amount,
        'unit_sell': unit_sell,
        'total_sell': total_sell,
        'shard_sell': shard_sell,
        'net': shard_sell - total_sell,
        'unknown': False,
    }


def opportunity_warning(shard, cache: PriceCache) -> str:
    """Return a warning string if the shard's shop cost exceeds its sell value."""
    oc = get_opportunity_cost(shard, cache)
    if not oc:
        return ""
    if oc['unknown']:
        return f"🏪 Shop-bought ({oc['currency_name']}, unknown qty)"
    if oc['net'] < 0:
        return f"🏪 TRAP: {oc['amount']}× {oc['currency_name']} = {_fmt(oc['total_sell'])} > shard sell {_fmt(oc['shard_sell'])} ({_fmt(oc['net'])})"
    return f"🏪 Shop: {oc['amount']}× {oc['currency_name']} = {_fmt(oc['total_sell'])} (net +{_fmt(oc['net'])})"


# ── Cheapest fillers ──────────────────────────────────────────────────────
def find_cheapest_fillers(cache: PriceCache) -> dict:
    """Find the cheapest per-unit filler for each rarity (instant-buy).

    Returns {rarity: {name, id, price_each}} or {rarity: None}.
    """
    fillers = {}
    for rarity in RARITY_ORDER:
        best = None
        for s in shards_data:
            if s['rarity'] != rarity:
                continue
            bz_id = shard_bazaar_id(s['name'])
            p = cache.get_price(bz_id)
            if p['source'] != 'bazaar' or not p['buy'] or p['buy'] <= 0:
                continue
            price = p['buy']
            if best is None or price < best['price_each']:
                best = {'name': s['name'], 'id': s['id'], 'price_each': price}
        fillers[rarity] = best
    return fillers


# ── Chain tracing ─────────────────────────────────────────────────────────
def trace_chain(start_shard, cache: PriceCache, fillers: dict) -> list[dict]:
    """Trace the full base-chain forward from a shard.

    Returns a list of steps, each with:
        shard, sell_price, filler_cost, cumulative_filler, net_vs_selling_start
    The first entry is the starting shard itself (no fusion cost).

    Assumes you HAVE the starting shard (free). The only costs are fillers.
    """
    chain = []
    current = start_shard
    visited = set()  # cycle protection

    while current and current['id'] not in visited:
        visited.add(current['id'])
        price_data = get_shard_price(current, cache)

        step = {
            'shard': current,
            'price_data': price_data,
            'sell_price': price_data['sell'],
            'warning': market_warning(price_data),
            'filler_cost_this_step': 0,  # 0 for the starting shard
            'filler_name': None,
            'filler_qty': 0,
            'cumulative_filler': 0,
        }

        if chain:
            # This step required a fusion from the previous shard
            prev = chain[-1]
            prev_shard = prev['shard']
            rarity = prev_shard['rarity']
            qty = prev_shard['fusion_quantity']
            filler = fillers.get(rarity)

            if filler:
                filler_cost = qty * filler['price_each']
                step['filler_cost_this_step'] = filler_cost
                step['filler_name'] = filler['name']
                step['filler_qty'] = qty
            else:
                # No filler available for this rarity — can't fuse
                step['filler_cost_this_step'] = float('inf')

            step['cumulative_filler'] = prev['cumulative_filler'] + step['filler_cost_this_step']

        chain.append(step)

        # Follow the base chain forward
        next_id = current.get('fusion_results', {}).get('base')
        current = shard_by_id.get(next_id) if next_id else None

    return chain


def find_shard(query: str):
    """Find a shard by name (fuzzy) or ID."""
    q = query.strip()

    # Exact ID match
    if q.upper() in shard_by_id:
        return shard_by_id[q.upper()]

    # Exact name match (case-insensitive)
    if q.lower() in shard_by_name:
        return shard_by_name[q.lower()]

    # Substring match
    matches = [s for s in shards_data if q.lower() in s['name'].lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print(f"Ambiguous — matched {len(matches)} shards:")
        for m in matches:
            print(f"  {m['id']:5s}  {m['name']} ({m['rarity']})")
        return None

    print(f"No shard found matching '{query}'")
    return None


# ── Commands ──────────────────────────────────────────────────────────────

def cmd_chain(args: list[str], cache: PriceCache, fillers: dict):
    """Trace a shard's fusion chain and show sell-vs-fuse decisions."""
    if not args:
        print("Usage: shards.py chain <shard_name_or_id>")
        print("Example: shards.py chain 'Glacite Walker'")
        return

    query = ' '.join(args)
    shard = find_shard(query)
    if not shard:
        return

    chain = trace_chain(shard, cache, fillers)

    print(f"\n{'='*70}")
    print(f" FUSION CHAIN: {shard['name']} ({shard['id']}) — {rarity_tag(shard['rarity'])} {shard['category']}")
    print(f"{'='*70}")
    print(f" Assumes you HAVE the starting shard. Only filler costs shown.")

    # Show hunt method if this is a direct-acquisition shard
    hunt = HUNT_INFO.get(shard['name'])
    if hunt:
        ease = hunt['tier']
        ease_str = EASE_LABEL.get(ease, '⚪ Unrated') if ease else '⚪ Rate unknown'
        print(f" How to get: {hunt['summary']}")
        print(f" Farm ease:  {ease_str}")
    print()

    start_sell = chain[0]['sell_price']
    best_profit = 0
    best_step_idx = 0

    for i, step in enumerate(chain):
        s = step['shard']
        sell = step['sell_price']
        cum_filler = step['cumulative_filler']
        warn = step['warning']

        # Net value = what you'd get selling here minus what you spent on fillers
        net = sell - cum_filler
        profit_vs_start = net - start_sell  # vs just selling the starting shard

        if net > best_profit and (not warn or warn.startswith('⚠')):
            best_profit = net
            best_step_idx = i

        # Header
        if i == 0:
            marker = "  YOU ARE HERE"
            fuse_line = ""
        else:
            marker = ""
            fq = step['filler_qty']
            fn = step['filler_name'] or '???'
            fc = step['filler_cost_this_step']
            fuse_line = f"  ↑ Fuse: {fq}× {fn} filler = {_fmt(fc)}"

        print(f"  {'─'*64}")
        if fuse_line:
            print(fuse_line)
            print(f"  {'─'*64}")

        line = f"  [{i}] {s['name']} ({s['id']}) — {rarity_tag(s['rarity'])}"
        if marker:
            line += marker
        print(line)

        # Price info
        sell_str = _fmt(sell) if sell > 0 else "???"
        print(f"      Instant-sell: {sell_str}", end="")
        if warn:
            print(f"  {warn}", end="")
        print()

        if i > 0:
            print(f"      Total filler spent: {_fmt(cum_filler)}")
            print(f"      Net if sold here:   {_fmt(net)}", end="")
            if profit_vs_start > 0:
                print(f"  (+{_fmt(profit_vs_start)} vs selling [{0}])")
            elif profit_vs_start < 0:
                print(f"  ({_fmt(profit_vs_start)} vs selling [{0}])")
            else:
                print(f"  (same as selling [{0}])")

    # Recommendation
    print(f"\n  {'─'*64}")
    if len(chain) == 1:
        print(f"  ⛔ End of chain — no further fusions available.")
    elif best_step_idx == 0:
        print(f"  💡 RECOMMENDATION: Sell {chain[0]['shard']['name']} as-is.")
        print(f"     Fusing costs more in fillers than the output gains in value.")
    else:
        best = chain[best_step_idx]
        net = best['sell_price'] - best['cumulative_filler']
        gain = net - start_sell
        print(f"  💡 RECOMMENDATION: Fuse to [{best_step_idx}] {best['shard']['name']}")
        print(f"     Sell: {_fmt(best['sell_price'])}  −  Fillers: {_fmt(best['cumulative_filler'])}  =  Net: {_fmt(net)}")
        print(f"     That's +{_fmt(gain)} vs selling {chain[0]['shard']['name']} directly.")

    # Opportunity cost warning for shop-bought shards
    oc_warn = opportunity_warning(shard, cache)
    if oc_warn:
        print(f"\n  {oc_warn}")
    print()


def _build_farm_results(cache: PriceCache, fillers: dict) -> list[dict]:
    """Build farm results for all direct-acquisition shards."""
    results = []

    for shard in shards_data:
        if shard['acquisition']['type'] != 'direct':
            continue

        chain = trace_chain(shard, cache, fillers)
        start_sell = chain[0]['sell_price']

        # Find the best step in the chain (highest net = sell − cumulative filler)
        best_net = start_sell  # baseline: sell as-is (0 filler cost)
        best_step = chain[0]
        best_idx = 0

        for i, step in enumerate(chain):
            if step['warning'] and step['warning'].startswith('❌'):
                continue  # skip dead markets
            net = step['sell_price'] - step['cumulative_filler']
            if net > best_net:
                best_net = net
                best_step = step
                best_idx = i

        ease = FARM_EASE.get(shard['name'])
        rate = EASE_RATE.get(ease, 0) if ease else 0
        coins_hr = best_net * rate if rate else None

        results.append({
            'start': shard,
            'start_sell': start_sell,
            'best_step': best_step,
            'best_idx': best_idx,
            'best_net': best_net,
            'chain_len': len(chain),
            'chain': chain,
            'ease': ease,
            'rate': rate,
            'coins_hr': coins_hr,
        })

    return results


def cmd_farm(cache: PriceCache, fillers: dict):
    """Rank farmable shards by estimated coins/hr, factoring in ease of farming."""
    results = _build_farm_results(cache, fillers)

    # ── Coins/hr ranking (the actual useful view) ─────────────────────────
    rated = [r for r in results if r['coins_hr'] is not None]
    rated.sort(key=lambda r: r['coins_hr'], reverse=True)

    print(f"\n{'='*70}")
    print(f" BEST SHARDS TO FARM — ranked by estimated coins/hr")
    print(f" Ease tiers: 🟢 S ~30/hr  🔵 A ~15/hr  🟡 B ~6/hr  🔴 C ~2/hr")
    print(f" Rates are rough estimates — actual rates vary with gear & hunting level")
    print(f"{'='*70}")

    print(f"\n  {'#':>3s}  {'Shard':22s}  {'Ease':15s}  {'Net/shard':>10s}  {'Est. coins/hr':>14s}  {'Best path'}")
    print(f"  {'─'*3}  {'─'*22}  {'─'*15}  {'─'*10}  {'─'*14}  {'─'*30}")

    for i, r in enumerate(rated[:30], 1):
        s = r['start']
        ease_str = EASE_LABEL.get(r['ease'], '?')
        net_str = _fmt(r['best_net'])
        hr_str = _fmt(r['coins_hr'])

        if r['best_idx'] == 0:
            path = "sell as-is"
        else:
            best_name = r['best_step']['shard']['name']
            path = f"→ {best_name} ({r['best_idx']} fusions)"

        warn = market_warning(get_shard_price(s, cache))
        oc_warn = opportunity_warning(s, cache)
        flags = ""
        if warn:
            flags += f"  {warn}"
        if oc_warn:
            flags += f"  {oc_warn}"

        print(f"  {i:3d}  {s['name']:22s}  {ease_str:15s}  {net_str:>10s}  {hr_str:>14s}/hr  {path}{flags}")

    # ── By-rarity detail view ─────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f" FULL LIST BY RARITY")
    print(f"{'='*70}")

    results.sort(key=lambda r: r['best_net'], reverse=True)

    for rarity in RARITY_ORDER:
        tier = [r for r in results if r['start']['rarity'] == rarity]
        if not tier:
            continue

        filler = fillers.get(rarity)
        filler_info = f"{filler['name']} @ {_fmt(filler['price_each'])}/ea" if filler else "none available"

        print(f"\n  ── {rarity_tag(rarity)} (filler: {filler_info}) ──")
        print()

        for r in tier:
            s = r['start']
            warn = market_warning(get_shard_price(s, cache))
            best = r['best_step']['shard']
            ease = FARM_EASE.get(s['name'])
            ease_icon = {'S': '🟢', 'A': '🔵', 'B': '🟡', 'C': '🔴'}.get(ease, '⚪')
            hunt = HUNT_INFO.get(s['name'])

            sell_now = _fmt(r['start_sell']) if r['start_sell'] > 0 else "???"

            if r['best_idx'] == 0:
                print(f"    {ease_icon} {s['name']:22s}  sell: {sell_now:>8s}  ← best as-is  (chain: {r['chain_len']} deep)", end="")
            else:
                filler_cost = r['best_step']['cumulative_filler']
                print(f"    {ease_icon} {s['name']:22s}  sell: {sell_now:>8s}  → fuse to {best['name']} = net {_fmt(r['best_net']):>8s}  (−{_fmt(filler_cost)} fillers, {r['best_idx']} fusions)", end="")

            if warn:
                print(f"  {warn}", end="")

            oc_warn = opportunity_warning(s, cache)
            if oc_warn:
                print(f"\n      {'':22s}         {oc_warn}", end="")

            # Show hunt method
            if hunt:
                print(f"\n      {'':22s}         📍 {hunt['summary']}", end="")
            print()

    print()


def cmd_fillers(cache: PriceCache, fillers: dict):
    """Show cheapest fillers per rarity and runner-ups."""
    print(f"\n{'='*70}")
    print(f" CHEAPEST FILLERS BY RARITY (instant-buy price per unit)")
    print(f"{'='*70}")

    for rarity in RARITY_ORDER:
        print(f"\n  ── {rarity_tag(rarity)} ──")

        # Get all shards of this rarity sorted by buy price
        priced = []
        for s in shards_data:
            if s['rarity'] != rarity:
                continue
            bz_id = shard_bazaar_id(s['name'])
            p = cache.get_price(bz_id)
            if p['source'] != 'bazaar' or not p['buy'] or p['buy'] <= 0:
                continue
            priced.append({
                'name': s['name'],
                'id': s['id'],
                'buy': p['buy'],
                'buy_volume': p['buy_volume'] or 0,
                'sell_volume': p['sell_volume'] or 0,
            })

        priced.sort(key=lambda x: x['buy'])

        # Show top 5
        for i, f in enumerate(priced[:5]):
            marker = " ← CHEAPEST" if i == 0 else ""
            vol_note = ""
            if f['sell_volume'] < MIN_VOLUME:
                vol_note = f"  (⚠️  low sell vol: {_fmt(f['sell_volume'])})"
            print(f"    {f['name']:24s}  {_fmt(f['buy']):>8s}/ea{marker}{vol_note}")

    # Show the cost to fuse for qty=2 vs qty=5 shards
    print(f"\n  ── Filler cost per fusion (qty × price) ──")
    for rarity in RARITY_ORDER:
        f = fillers.get(rarity)
        if f:
            cost_2 = 2 * f['price_each']
            cost_5 = 5 * f['price_each']
            print(f"    {rarity:10s}  qty=2: {_fmt(cost_2):>8s}   qty=5: {_fmt(cost_5):>8s}   (using {f['name']})")
    print()


def cmd_health(cache: PriceCache):
    """Flag shards with dead or thin markets."""
    print(f"\n{'='*70}")
    print(f" MARKET HEALTH CHECK")
    print(f" Flags: ❌ = can't sell / no buyers  ⚠️  = thin market (<{MIN_VOLUME} buy vol)")
    print(f"{'='*70}")

    dead = []
    thin = []
    healthy = 0

    for s in shards_data:
        pd = get_shard_price(s, cache)
        warn = market_warning(pd)
        if warn.startswith('❌'):
            dead.append((s, pd, warn))
        elif warn.startswith('⚠'):
            thin.append((s, pd, warn))
        else:
            healthy += 1

    if dead:
        print(f"\n  ── DEAD MARKETS ({len(dead)}) — DO NOT FUSE INTO THESE ──")
        for s, pd, warn in sorted(dead, key=lambda x: x[0]['rarity']):
            print(f"    {rarity_tag(s['rarity']):14s}  {s['name']:24s}  {warn}")

    if thin:
        print(f"\n  ── THIN MARKETS ({len(thin)}) — sell carefully, check volume ──")
        for s, pd, warn in sorted(thin, key=lambda x: -x[1]['buy_volume']):
            sell_str = _fmt(pd['sell']) if pd['sell'] > 0 else "???"
            print(f"    {rarity_tag(s['rarity']):14s}  {s['name']:24s}  sell: {sell_str:>8s}  {warn}")

    print(f"\n  ── SUMMARY ──")
    print(f"    Healthy: {healthy}   Thin: {len(thin)}   Dead: {len(dead)}   Total: {len(shards_data)}")
    print()


def cmd_summary(cache: PriceCache, fillers: dict):
    """Quick overview — top farmable shards, fillers, and warnings."""
    # Fillers summary
    print(f"\n{'='*70}")
    print(f" SHARD FUSION ADVISOR — Quick Summary")
    print(f"{'='*70}")

    print(f"\n  Cheapest fillers:")
    for rarity in RARITY_ORDER:
        f = fillers.get(rarity)
        if f:
            print(f"    {rarity:10s}  {f['name']:20s}  {_fmt(f['price_each'])}/ea")

    # Top 15 by estimated coins/hr
    results = _build_farm_results(cache, fillers)
    rated = [r for r in results if r['coins_hr'] is not None]
    rated.sort(key=lambda r: r['coins_hr'], reverse=True)

    print(f"\n  Top 15 farmable shards (estimated coins/hr — S:30/hr A:15/hr B:6/hr C:2/hr):")
    print(f"  {'#':>3s}  {'Shard':22s}  {'Ease':5s}  {'Net/shard':>10s}  {'~coins/hr':>12s}  {'Best path'}")
    print(f"  {'─'*3}  {'─'*22}  {'─'*5}  {'─'*10}  {'─'*12}  {'─'*25}")

    for i, r in enumerate(rated[:15], 1):
        s = r['start']
        ease_icon = {'S': '🟢', 'A': '🔵', 'B': '🟡', 'C': '🔴'}.get(r['ease'], '⚪')

        if r['best_idx'] == 0:
            path = "sell as-is"
        else:
            best_name = r['best_step']['shard']['name']
            path = f"→ {best_name} ({r['best_idx']})"

        flags = ""
        oc_warn = opportunity_warning(s, cache)
        if oc_warn:
            flags = f"  {oc_warn}"
        warn = market_warning(get_shard_price(s, cache))
        if warn:
            flags += f"  {warn}"

        print(f"  {i:3d}  {s['name']:22s}  {ease_icon:5s}  {_fmt(r['best_net']):>10s}  {_fmt(r['coins_hr']):>12s}/hr  {path}{flags}")

    # Dead markets warning
    dead_count = sum(1 for s in shards_data if market_warning(get_shard_price(s, cache)).startswith('❌'))
    if dead_count:
        print(f"\n  ⚠️  {dead_count} shards have dead markets — run 'shards.py health' for details")

    print(f"\n  Commands:")
    print(f"    shards.py chain <name>  — Trace a shard's fusion chain with sell-vs-fuse advice")
    print(f"    shards.py farm          — Full farmable shard rankings by rarity")
    print(f"    shards.py fillers       — Cheapest fillers with runner-ups")
    print(f"    shards.py health        — Dead/thin market check")
    print()


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print("Fetching live Bazaar prices...")
    cache = PriceCache()
    cache._fetch_bazaar()

    # Check coverage
    found = sum(1 for s in shards_data if get_shard_price(s, cache)['found'])
    print(f"Found {found}/{len(shards_data)} shards on Bazaar")

    fillers = find_cheapest_fillers(cache)

    # Parse command
    args = sys.argv[1:]
    cmd = args[0].lower() if args else ''

    if cmd == 'chain':
        cmd_chain(args[1:], cache, fillers)
    elif cmd == 'farm':
        cmd_farm(cache, fillers)
    elif cmd == 'fillers':
        cmd_fillers(cache, fillers)
    elif cmd == 'health':
        cmd_health(cache)
    elif cmd in ('', 'summary', 'help'):
        cmd_summary(cache, fillers)
    else:
        # Maybe they passed a shard name directly — treat as chain
        shard = find_shard(' '.join(args))
        if shard:
            cmd_chain(args, cache, fillers)

    cache.flush()


if __name__ == '__main__':
    main()
