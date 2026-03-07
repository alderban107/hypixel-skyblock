# Weapons & Armor Progression Research

**Purpose:** Reference data for guide rewrite. Stats extracted from wiki sources listed below.
**Date compiled:** 2026-03-04
**Sources:** `data/wiki/*.wiki`, `data/wiki-official/*.wiki`

---

## KEY CORRECTIONS (Apply Everywhere)

- **AOTD is a trap pick.** It is an NPC/drop item with no upgrade path. The correct melee path is:
  Super Cleaver → Hyper Cleaver → Giant Cleaver → Bouquet of Lies (paired with FoT/Giant Cleaver)
- **One For All enchant = do not recommend.** Wiki notes: "OFA does not buff the damage of Bouquet of Lies." It is an NPC item trap.
- **Dragon Armor outside dungeons = 0 dungeon scaling.** Non-dungeonized dragon armor gets NO dungeon stat bonuses. Stars on dungeon items give +10% per star INSIDE dungeons only.
- **Livid Dagger requires F5 COMPLETION** (not a cata level number).
- **Shadow Assassin Armor requires F5 COMPLETION** (not a cata level number).
- **Wither Cloak Sword requires F7 COMPLETION** (wiki: "The Catacombs - Floor VII").
- **Hyperion / Necron's Blade require F7 COMPLETION** (crafting requires F7 cleared).

---

## PART 1: WEAPONS PROGRESSION

### 1.1 Melee — Early Game

#### Undead Sword
- **Source:** `data/wiki/Undead Sword.wiki`
- **ID:** `UNDEAD_SWORD`
- **Rarity:** Common
- **Stats:** Damage +30
- **Special:** Deals +100% damage to Undead mobs
- **Cost:** 100 coins from Weaponsmith NPC
- **Requirement:** None
- **Notes:** Good early weapon vs. undead mobs (Deep Caverns). Can be upgraded to Revenant Falchion (requires Zombie Slayer 3). Cheap 5-star candidate for early progression. As of Aug 2025, can be dungeonized.
- **Upgrade path:** → Revenant Falchion (Zombie Slayer 3)

#### Aspect of the End (AOTE)
- **Source:** `data/wiki/Aspect of the End.wiki`
- **ID:** `ASPECT_OF_THE_END`
- **Rarity:** Rare
- **Stats:** Damage +100, Strength +100
- **Ability:** Instant Transmission (RIGHT CLICK) — Teleport 8 blocks ahead, gain +50 Speed for 3s. No cooldown, costs 50 Mana.
- **Collection:** Ender Pearl VIII
- **Craft cost:** 32 Enchanted Eye of Ender + 1 Enchanted Diamond
- **Requirements to use:** None (crafting requires Ender Pearl VIII)
- **Dungeon requirement (if dungeonized):** Listed as upgradeable via Etherwarp Conduit (Enderman Slayer 7)
- **Notes:**
  - Synergizes with Strong Dragon Armor full set bonus (Strong Blood): +75 Damage, +2 teleport range, +3s speed duration, +5 Strength on cast
  - Can be upgraded to Aspect of the Void at Enderman Slayer 6 (+20 Damage, -5 Mana cost)
  - Can be combined with Etherwarp Conduit (Enderman Slayer 7) for long-range teleport on sneak+right-click
  - The "Strong Blood" interaction makes AOTE genuinely powerful when paired correctly
- **Role:** Mobility weapon + early damage before dungeon access

#### Aspect of the Dragons (AOTD) — DO NOT RECOMMEND
- **Source:** `data/wiki/Aspect of the Dragons.wiki`
- **ID:** `ASPECT_OF_THE_DRAGON`
- **Rarity:** Legendary
- **Stats:** Damage +225 (275 with max Ender Dragon pet), Strength +100 (130 with max pet)
- **Ability:** Dragon Rage (RIGHT CLICK) — Deals 12,000 Ability Damage in a 60° cone, 7.5 blocks long. 100 Mana, no cooldown.
- **Source:** Ender Dragon drop (3% per eye placed)
- **Requirement:** Combat 18; Catacombs 12 (if dungeonized)
- **Cost tier:** ~few million coins (AH)
- **GUIDE NOTE:** This is an NPC/drop item with no upgrade path. While the stats appear competitive, the Hyper Cleaver surpasses it at the same price range. AOTD was historically top-tier but has been obsolete since dungeon weapons launched. The wiki's own Tips section now says "it is much more recommended to use a Super Cleaver." Do not recommend in progression guides.

---

### 1.2 Melee — Mid Game (Dungeon Path)

#### Super Cleaver
- **Source:** `data/wiki/Super Cleaver.wiki`
- **ID:** `SUPER_CLEAVER`
- **Rarity:** Rare (Dungeon Sword)
- **Stats:** Damage +105, Strength +20, Crit Damage +20%
- **Ability:** Cleave — Mobs within 3 blocks take a portion of damage dealt to target
- **Cost:** 80,000 coins + 1 Cleaver from Ophelia (NPC purchase)
- **Requirement:** None (NPC item, no floor requirement)
- **Notes:** The wiki explicitly recommends Super Cleaver over AOTD: "it is much more recommended to use a Super Cleaver and upgrade it as you progress through the Catacombs." No dungeon floor requirement to purchase.
- **Upgrade path:** → Hyper Cleaver (800k + 1 Super Cleaver from Ophelia)

#### Hyper Cleaver
- **Source:** `data/wiki/Hyper Cleaver.wiki`
- **ID:** `HYPER_CLEAVER`
- **Rarity:** Epic (Dungeon Sword)
- **Stats:** Damage +175, Strength +100, Crit Damage +100%
- **Ability:** Cleave — Mobs within 4 blocks take a portion of damage dealt to target
- **Requirement:** Floor III cleared to use
- **Cost:** 800,000 coins + 1 Super Cleaver from Ophelia
- **Notes:** "Comfortably outclasses other weapons such as AOTD or Livid Dagger, and is highly recommended as a primary weapon." Gold Essence for stars.
- **Upgrade path:** → Giant Cleaver (5m + 1 Hyper Cleaver from Ophelia)

#### Giant Cleaver
- **Source:** `data/wiki/Giant Cleaver.wiki`
- **ID:** `GIANT_CLEAVER`
- **Rarity:** Legendary (Dungeon Sword) — upgraded from Epic in Aug 2025
- **Stats:** Damage +235, Strength +120, Crit Damage +120%
- **Ability:** Cleave — Mobs within 5 blocks take a portion of damage dealt to target
- **Requirement:** Floor VI cleared to use
- **Cost:** 5,000,000 coins + 1 Hyper Cleaver from Ophelia
- **Notes:** "Among the best weapons you can use upon obtaining it, comfortably outclassing Livid Dagger, Shadow Fury, or Giant's Sword." Pairs well with Flower of Truth or Bouquet of Lies. Gold Essence for stars.

---

### 1.3 Melee — Late Game (F5 Dungeon Items)

#### Livid Dagger
- **Source:** `data/wiki/Livid Dagger.wiki`
- **ID:** `LIVID_DAGGER`
- **Rarity:** Legendary (Dungeon Sword)
- **Stats:** Damage +210, Strength +60, Crit Chance +100%, Crit Damage +50%, Attack Speed +50%
- **Passive:** Critical Hits deal +100% more damage if you are behind your target
- **Ability:** Throw (RIGHT CLICK) — Throw dagger forward, 150 Mana, 5s cooldown
- **Requirement:** Floor V COMPLETION (not a cata level)
- **Obtaining:**
  - Livid Collection III reward (150 Livid kills) — one-time claim
  - Dungeon Reward Chest (Obsidian/Bedrock, F5): 0.31% / 1.16% chance, costs 7M to open
- **Cost tier:** ~15–25M AH
- **Notes:** The +100% backstab damage is powerful but requires positioning. The Fast reforge allows it to reach +100% Attack Speed. Wither Essence for stars. Less versatile than Cleaver line due to positioning requirement.

#### Shadow Fury
- **Source:** `data/wiki/Shadow Fury.wiki`
- **ID:** `SHADOW_FURY`
- **Rarity:** Legendary (Dungeon Sword)
- **Stats:** Damage +300 (+310 with Livid Frags), Strength +130 (+160 with frags), Crit Damage +30% (+60%), Speed +30 (+40)
- **Ability:** Shadow Fury (RIGHT CLICK) — Teleports to up to 5 enemies within 12 blocks, rooting each. 15s cooldown, no mana cost.
- **Requirement:** Floor V COMPLETION
- **Obtaining:** Bedrock Chest, F5 (0.29% chance, costs 15M to open)
- **Cost tier:** ~20–40M AH
- **Upgrade:** +8 Livid Fragments → adds +10 dmg, +30 str, +30 cd, +10 spd, +1 Combat gem slot
- **Notes:** Wither Essence for stars. Ability is exceptional for tagging multiple mobs and triggering backstab. Pairs well with Livid Dagger playstyle.

#### Flower of Truth (FoT)
- **Source:** `data/wiki/Flower of Truth.wiki`
- **ID:** `FLOWER_OF_TRUTH`
- **Rarity:** Legendary (Dungeon Sword)
- **Stats:** Damage +160, Strength +300
- **Ability:** Heat-Seeking Rose (RIGHT CLICK) — Shoots a rose that ricochets to up to 3 enemies (max 20 blocks range). Damage multiplies per bounce. 1s cooldown, costs 10% max HP.
- **Requirement:** Floor VI COMPLETION (crafting requires F6 cleared)
- **Craft:** 9 Ancient Rose (Bazaar)
- **Cost tier:** Craft-based, ~1–5M depending on Ancient Rose price
- **Notes:** Precursor to Bouquet of Lies. Ability does NOT scale with Int or Ability Damage — uses melee damage formula (Strength + Crit Damage). OFA and Cleave don't affect it.
- **Upgrade path:** → Bouquet of Lies (12 Fel Rose + 1 FoT)

#### Bouquet of Lies (BoL)
- **Source:** `data/wiki/Bouquet of Lies.wiki`
- **ID:** `BOUQUET_OF_LIES`
- **Rarity:** Legendary (Dungeon Sword)
- **Stats:** Damage +220, Strength +300, Crit Damage +50%
- **Ability:** Petal Barrage (RIGHT CLICK) — Fires 3 roses that ricochet between up to 5 foes (max 15 total hits). For every 10% HP missing, roses deal +2% more damage. 1s cooldown, costs 10% max HP.
- **Requirement:** Floor VI COMPLETION
- **Craft:** 12 Fel Rose + 1 Flower of Truth
- **Cost tier:** Craft-based, ~5–15M
- **Notes:** High Strength makes it excellent with Baby Yeti Pet. Fabled reforge recommended for balanced Str/CD. Pairs with Giant Cleaver for swap DPS (left-click melee + right-click ability). OFA does NOT buff Bouquet of Lies ability.

---

### 1.4 Melee — Endgame (F6/F7 Items)

#### Giant's Sword
- **Source:** `data/wiki/Giant's Sword.wiki`
- **ID:** `giants_sword`
- **Rarity:** Legendary (Dungeon Longsword)
- **Stats:** Damage +500, Swing Range +1
- **Ability:** Giant's Slam (RIGHT CLICK) — Slams sword into ground, 100,000 damage to nearby mobs in 8-block radius, 5 blocks ahead. 30s cooldown, 100 Mana. Scales with Int and Ability Damage.
- **Requirement:** Floor VI COMPLETION
- **Obtaining:** Bedrock Chest, F6 (0.1875% chance, costs 25M to open)
- **Cost tier:** ~50–100M AH (rare drop, not worth buying per wiki tips)
- **Notes:** Second-highest base Damage in the game. Wither Essence for stars. Wiki explicitly notes: "not worth buying from the AH, only worth it if you drop one." Used in sword-swapping setups.

#### Wither Cloak Sword
- **Source:** `data/wiki/Wither Cloak Sword.wiki`
- **ID:** `WITHER_CLOAK`
- **Rarity:** Epic (Dungeon Sword)
- **Stats:** Damage +190, Strength +135, Defense +250
- **Ability:** Creeper Veil (RIGHT CLICK) — Toggle: grants 10s damage immunity (absorbs hits for 20% max Mana each). Cannot attack while active. 10s cooldown.
- **Requirement:** Floor VII COMPLETION
- **Obtaining:** Dungeon Reward Chest, F7 (Emerald 0.54%, Obsidian 1.88%, Bedrock 5.27%; costs 4.5M to open)
- **Notes:** Defensive utility weapon. Used for Trial of Fire and tanking mechanics. Wither Essence for stars.

#### Necron's Blade (and variants)
- **Source:** `data/wiki/Necron's Blade.wiki`, `data/wiki/Hyperion.wiki`
- **ID:** `NECRON_BLADE`
- **Rarity:** Legendary (Dungeon Sword)
- **Base Stats:** Damage +260, Strength +110, Intelligence +50, Ferocity +30
- **Special:** Deals +50% damage to Wither mobs. Right-click to use class ability.
- **Requirement:** Floor VII COMPLETION
- **Craft:** 24 Wither Catalyst + 1 Necron's Handle
- **Refinement:** Upgraded to one of four variants using Precursor Relics (drops from F7 Blood Room Giants):
  | Variant | Precursor Relic | Bonus Stats |
  |---------|----------------|-------------|
  | **Hyperion** | 8 L.A.S.R.'s Eye | +350 Intelligence |
  | **Astraea** | 8 Jolly Pink Rock | +250 Defense, +20 True Defense |
  | **Scylla** | 8 Bigfoot's Bola | +12% Crit Chance, +35% Crit Damage |
  | **Valkyrie** | 8 Diamante's Handle | +60 Ferocity |
- **All variants also gain:** +1 Damage and class-specific stat (+1 or +2) per Catacombs level
- **Variants can be converted between each other** (consuming the appropriate relic)
- **Essence:** Wither (150/300/500/900/1500 per star)

#### Hyperion (detail)
- **Source:** `data/wiki/Hyperion.wiki`
- **ID:** `HYPERION`
- **Full Stats:** Damage +260 (max 310), Strength +150, Intelligence +350 (max 450), Ferocity +30
- **Scaling:** +1 Damage and +2 Intelligence per Catacombs level
- **Special:** +50% damage to Wither mobs
- **Notes:** The primary Mage endgame weapon. Heroic and Suspicious reforges pair well; Fabled for Left-Click Mage. Donating to Museum gives credit for all Necron's Blade variants. Cannot be salvaged/sold.

---

### 1.5 Ranged Weapons

#### Runaan's Bow
- **Source:** `data/wiki/Runaan's Bow.wiki`
- **ID:** `RUNAANS_BOW`
- **Rarity:** Legendary (Bow)
- **Stats:** Damage +160, Strength +50
- **Ability:** Triple Shot — Shoots 3 arrows at a time; 2 extra arrows deal 40% of main arrow damage, homing within 10 blocks
- **Collection:** Bone IX
- **Craft:** 192 Enchanted Bone + 192 Enchanted String
- **Dungeon requirement (if dungeonized):** Catacombs 8
- **Notes:** Good early game bow. Spider Essence for stars. Side arrows don't benefit from Power or Piercing enchants.

#### Spirit Bow
- **Source:** `data/wiki/Spirit Bow.wiki`
- **ID:** `BOSS_SPIRIT_BOW`
- **Rarity:** Epic (Dungeon Bow)
- **Special:** Only weapon that can damage Thorn (F4 boss). Single shot. Cannot leave The Catacombs.
- **Requirement:** None (floor requirement = none; obtained from Spirit Bear in F4)
- **Notes:** Not a progression weapon — purely a boss-mechanic item. Obtained automatically during F4 run.

#### Juju Shortbow
- **Source:** `data/wiki/Juju Shortbow.wiki`
- **ID:** `juju_shortbow`
- **Rarity:** Epic (Bow)
- **Stats:** Damage +310, Strength +40, Crit Chance +10%, Crit Damage +110%
- **Special:** Shortbow (instant fire). Hits 3 mobs on impact (3-block AOE). Can damage Endermen. Shot cooldown: 0.5s
- **Collection:** Enderman Slayer 5
- **Craft:** 32 Null Ovoid + 32 Enchanted Eye of Ender + 32 Enchanted Quartz Block + 192 Enchanted String
- **Dungeon requirement (if dungeonized):** Catacombs 15 (150 Dragon Essence to convert)
- **Notes:** Dragon Essence for stars. Fire rate scales with Attack Speed stat (2.22–5 shots/sec). Pre-Terminator endgame archer weapon.

#### Terminator
- **Source:** `data/wiki/Terminator.wiki`
- **ID:** `TERMINATOR`
- **Rarity:** Legendary (Bow)
- **Stats:** Damage +310, Strength +50, Crit Damage +250%, Attack Speed +40%
- **Special:** Shortbow (instant fire). Shoots 3 arrows per shot. Can damage Endermen. Divides Crit Chance by 4. 0.3s shot cooldown.
- **Ability:** Salvation (LEFT CLICK, after 3 hits) — Beam that penetrates up to 5 enemies, always crits. 1 Soulflow, 0.25s cooldown.
- **Collection:** Enderman Slayer 7
- **Craft (Bazaar materials):** 192 Enchanted Quartz Block + 6144 Enchanted Obsidian + 24576 Null Sphere + 27 Null Atom + 4096 Enchanted Flint + 16384 Tarantula Web + 256 Enchanted Lapis Block + 640 Absolute Ender Pearl + 640 Griffin Feather + 1728 Enchanted Mithril + 1024 Soul String + **1 Judgement Core** (not from Bazaar)
- **Requirement:** Enderman Slayer 7 to use
- **Notes:** The endgame ranged weapon. CC/4 mechanic means Crit Chance must be built carefully. Fire rate 2.22–5 shots/sec depending on Attack Speed.

---

### 1.6 Mage Weapons

#### Bonzo's Staff
- **Source:** `data/wiki/Bonzo's Staff.wiki`
- **ID:** `bonzo_staff`
- **Rarity:** Rare (Dungeon Sword)
- **Requirement:** Floor I COMPLETION
- **Obtaining:** Bonzo Collection IV (150 Bonzo kills, one-time) or Dungeon Reward Chest F1 (Emerald 0.71%, Obsidian 1%)
- **Ability:** Showtime — Fires slow balloons at 4/s that explode for 1,000 base damage in 2-block radius. Launches user upward on self-explosion.
- **Notes:** Early mage weapon. Not viable as primary weapon past first few floors, but retained for F7 mobility use (launch mechanic).

#### Spirit Sceptre
- **Source:** `data/wiki/Spirit Sceptre.wiki`
- **ID:** `BAT_WAND`
- **Rarity:** Legendary (Dungeon Sword)
- **Stats:** Damage +180, Intelligence +300
- **Ability:** Guided Bat (RIGHT CLICK) — Shoots guided spirit bat; explodes for 2,000 Ability Damage in 6-block radius on contact. 200 Mana. Scales with Int (0.2 factor) and Ability Damage.
- **Requirement:** Floor IV COMPLETION
- **Craft:** 3 Spirit Wing + 6 Enchanted Lapis Lazuli Block
- **Upgrade:** +8 Thorn Fragment → Starred Spirit Sceptre (+10 Damage, +30 Int)
- **Notes:** Primary mage weapon for F4+ range. Bat can be buffed by Bat Person Talisman upgrades. Wither Essence for stars.

#### Hyperion (Mage endgame — see section 1.4 above)
- Primary mage endgame weapon. Used by Mage class with Necron's Blade scroll abilities.

---

## PART 2: ARMOR PROGRESSION

### Star Scaling Reference (from `data/wiki/Star Upgrades.wiki`)
- **Dungeon items:** +10% of all stats per star INSIDE dungeons (up to 5 stars = +50%). Stats in dark gray parentheses on tooltip show the in-dungeon values.
- **Master Stars (1–5):** +5% per Master Star inside Master Mode only.
- **Crimson Isle items:** +2% per star (different system, uses Crimson Essence). Up to 2–15 stars depending on item.
- **IMPORTANT:** Non-dungeonized dragon armor and other non-dungeon items do NOT receive the +10% dungeon scaling bonus.

### Dragon Armor Dungeonization Requirements (from individual armor wikis)
| Set | Dungeonize Cost | Cata Req to Use (Dungeonized) |
|-----|----------------|-------------------------------|
| Young Dragon Armor | Dragon Essence | Catacombs 10 |
| Unstable Dragon Armor | Dragon Essence | Catacombs 10 |
| Strong Dragon Armor | Dragon Essence | Catacombs 12 |
| Superior Dragon Armor | Dragon Essence | Catacombs 14 |

---

### 2.1 Combat Armor — Progression Chain

#### Lapis Armor
- **Source:** `data/wiki/Lapis Armor.wiki`
- **Rarity:** Uncommon
- **Stats (full set):** Defense +120, HP +60 (set bonus), Mining Speed +80, Mining Fortune +8
- **Set Bonus:** Health — +60 max HP
- **Additional:** +200% Bonus Experience when mining ores
- **Requirement:** Mining 5
- **Obtaining:** 1% drop from Lapis Zombies in Lapis Quarry
- **Notes:** Popular early armor for grinding mining XP. Better than Diamond armor for new players. Drop rate improved by Looting/Luck enchants.

#### Hardened Diamond Armor
- **Source:** `data/wiki/Hardened Diamond Armor.wiki`
- **Rarity:** Rare
- **Stats (full set):** Defense +330
- **Collection:** Diamond VII
- **Craft:** 24 Enchanted Diamond total (5/8/7/4 per piece)
- **Notes:** Pre-dragon armor progression step. Upgrades to Mineral Armor.

#### Ender Armor
- **Source:** `data/wiki/Ender Armor.wiki`
- **Rarity:** Epic (8-piece set including Equipment)
- **Stats (armor only):** HP +135 (270 in The End), Defense +200 (400 in The End)
- **Per-piece:** Helmet +35 def/+20 hp, Chest +60 def/+30 hp, Legs +50 def/+25 hp, Boots +25 def/+15 hp
- **Additional (Equipment pieces):** +10 def/+15 hp each (Necklace, Cloak, Belt, Gauntlet)
- **Special:** All stats x2 in The End, including enchantments and reforges
- **Requirement:** Combat 12
- **Obtaining:** 1% drop from Endermen in The End; Equipment pieces 0.5% drop
- **Notes:** Soulbound co-op (not tradeable except to co-op members). Excellent for Enderman farming due to 2x multiplier.

#### Unstable Dragon Armor
- **Source:** `data/wiki/Unstable Dragon Armor.wiki`
- **Rarity:** Legendary
- **Stats (full set):** HP +350, Defense +500, Crit Chance +20%, Crit Damage +60%, Intelligence +25
- **Per-piece:** Helmet +110 def/+70 hp/+5% cc/+15% cd/+25 int; Chest +160 def/+120 hp/+5% cc/+15% cd; Legs +140 def/+100 hp/+5% cc/+15% cd; Boots +90 def/+60 hp/+5% cc/+15% cd
- **Set Bonus:** Unstable Blood — Occasionally strikes nearby mobs with lightning (8-block radius, 3,000 damage every 15s)
- **Requirement:** Combat 16 to use; Catacombs 10 if dungeonized
- **Craft:** 240 Unstable Dragon Fragments
- **Notes:** Best pre-dungeon critical stats armor. Dragon Essence to dungeonize, then requires Cata 10.

#### Strong Dragon Armor
- **Source:** `data/wiki/Strong Dragon Armor.wiki`
- **Rarity:** Legendary
- **Stats (full set):** HP +350, Defense +500, Strength +100
- **Per-piece:** Helmet +110 def/+70 hp/+25 str; Chest +160 def/+120 hp/+25 str; Legs +140 def/+100 hp/+25 str; Boots +90 def/+60 hp/+25 str
- **Set Bonus:** Strong Blood — Improves AOTE and Aspect of the Void: +75 Damage, +2 teleport blocks, +3s speed duration, +5 Strength on cast
- **Requirement:** Combat 16; Catacombs 12 if dungeonized
- **Craft:** 240 Strong Dragon Fragments
- **Notes:** Primarily used as AOTE synergy set. Less universal than Unstable; good for specific AOTE builds.

#### Young Dragon Armor
- **Source:** `data/wiki/Young Dragon Armor.wiki`
- **Rarity:** Legendary
- **Stats (full set):** HP +350, Defense +500, Speed +80
- **Per-piece:** Helmet +110 def/+70 hp/+20 spd; Chest +160 def/+120 hp/+20 spd; Legs +140 def/+100 hp/+20 spd; Boots +90 def/+60 hp/+20 spd
- **Set Bonus:** Young Blood — +70 Walk Speed above 50% HP, +100 Walk Speed cap
- **Requirement:** Combat 16; Catacombs 10 if dungeonized
- **Craft:** 240 Young Dragon Fragments
- **Notes:** Mobility/speed set. Full set grants +150 speed while above 50% HP plus +100 to the speed cap. Useful for Berserk class in Dungeons due to high speed cap.

#### Superior Dragon Armor
- **Source:** `data/wiki/Superior Dragon Armor.wiki`
- **Rarity:** Legendary
- **Stats (full set):** HP +450, Defense +600, Strength +40, Crit Chance +8%, Crit Damage +40%, Speed +12, Intelligence +100
- **Per-piece:** Helmet +130 def/+90 hp/+10 str/+2% cc/+10% cd/+3 spd/+25 int; Chest +190 def/+150 hp/+10 str/+2% cc/+10% cd/+3 spd/+25 int; Legs +170 def/+130 hp/+10 str/+2% cc/+10% cd/+3 spd/+25 int; Boots +110 def/+80 hp/+10 str/+2% cc/+10% cd/+3 spd/+25 int
- **Set Bonus:** Superior Blood — All Combat stats and Magic Find +5%; AOTD ability deals 50% more Ability Damage
- **Requirement:** Combat 20; Catacombs 14 if dungeonized
- **Craft:** 240 Superior Dragon Fragments
- **Notes:** Most expensive and powerful Dragon Armor set. The 5% all-combat-stats multiplier compounds with other bonuses. AOTD interaction is largely irrelevant for serious players (see AOTD note above).

#### Adaptive Armor
- **Source:** `data/wiki/Adaptive Armor.wiki`
- **Rarity:** Epic (Dungeon Armor)
- **Stats (full set):** HP +515 (555 starred), Defense +245 (285 starred), Strength +60, Intelligence +60
- **Per-piece:** Helmet +50 def/+110 hp/+15 str/+15 int; Chest +85 def/+170 hp/+15 str/+15 int; Legs +65 def/+145 hp/+15 str/+15 int; Boots +45 def/+90 hp/+15 str/+15 int
- **Set Bonus:** Efficient Training — Every 5 Catacombs levels, armor gains +2% stats
- **Class Bonuses (per piece):**
  - Berserk: +20 Strength
  - Healer: +5 Mending, +40 HP
  - Mage: +50 Intelligence
  - Tank: +30 Defense, -5% damage taken per piece if hit by same mob within 10s
  - Archer: +5% Crit Chance, +15% Crit Damage
- **Requirement:** Floor III COMPLETION
- **Obtaining:** Dungeon Reward Chests F3+ (Diamond 1.28%, Emerald 1.46%, Obsidian 1.21%)
- **Notes:** Versatile early dungeon armor. Set bonus scales with Cata level. Stars use Wither Essence. Fragged version has 1 Combat gemstone slot.

#### Shadow Assassin Armor
- **Source:** `data/wiki/Shadow Assassin Armor.wiki`
- **Rarity:** Epic (Legendary with Livid Fragments)
- **Stats (full set):** HP +735 (775 starred), Defense +330, Strength +100 (120 starred), Crit Damage +100%, Speed +28% (32% starred)
- **Per-piece:** Helmet +70 def/+160 hp/+25 str/+25% cd/+7% spd; Chest +110 def/+240 hp/+25 str/+25% cd/+7% spd; Legs +95 def/+210 hp/+25 str/+25% cd/+7% spd; Boots +55 def/+125 hp/+25 str/+25% cd/+7% spd
- **Set Bonus:** Shadow Assassin — Collect shadows of killed enemies, +1 Strength per kill for the rest of the dungeon
- **Requirement:** Floor V COMPLETION
- **Obtaining:** Dungeon Reward Chests F5; SA Chestplate also from Livid Collection VI (750 Livid kills)
- **Starred version:** Rarity upgrades to Legendary
- **Notes:** Strong Berserk/general dungeon armor. The stacking Strength is significant for long runs. Scam-prone: beware fake listings with Obsidian Chestplates. Wither Essence for stars.

#### Necron's Armor
- **Source:** `data/wiki/Necron's Armor.wiki`
- **Rarity:** Legendary (Dungeon Armor)
- **Stats (full set):** HP +815, Defense +450, Strength +160, Crit Damage +120%, Intelligence +60
- **Per-piece:** Helmet +100 def/+180 hp/+40 str/+30% cd/+30 int; Chest +140 def/+260 hp/+40 str/+30% cd/+10 int; Legs +125 def/+230 hp/+40 str/+30% cd/+10 int; Boots +85 def/+145 hp/+40 str/+30% cd/+10 int
- **Set Bonus:** Witherborn — Spawns a wither minion every 30s (max 1). Withers travel to and explode on nearby enemies.
- **Effect:** Reduces damage from Wither mobs by 10% per piece (40% max)
- **Requirement:** Floor VII COMPLETION
- **Craft (each piece):** 8 Diamante's Handle + any Wither Armor variant (Goldor's/Storm's/Maxor's/Wither pieces)
- **Notes:** Top-tier endgame combat armor. Wither Essence for stars (50/100/200/350/500 helm; 100/200/350/600/1000 chest; 75/150/250/400/700 legs; 50/100/200/350/500 boots).

---

### 2.2 Mining Armor

#### Lapis Armor (dual-purpose — see section 2.1)
- Also functions as early mining armor due to +200% ore XP bonus

#### Hardened Diamond Armor (see section 2.1)
- Stepping stone before Mineral Armor

#### Mineral Armor
- **Source:** `data/wiki/Mineral Armor.wiki`
- **Rarity:** Epic
- **Stats (full set):** Defense +390, Speed +50
- **Per-piece:** Helmet +70 def/+10 spd; Chest +125 def/+15 spd; Legs +125 def/+15 spd; Boots +70 def/+10 spd
- **Special:** Increases the number of blocks the player can mine with a Pickaxe (blocks with Breaking Power 3 or less)
- **Craft:** 24 Refined Mineral + 24 Enchanted Diamond (upgrades from Hardened Diamond)
- **Notes:** Refined Minerals drop from Ores during Mining Fiesta event (Cole's Mining Fiesta perk). Upgrades to Glossy Mineral Armor.

#### Sorrow Armor
- **Source:** `data/wiki/Sorrow Armor.wiki`
- **Rarity:** Legendary
- **Stats (full set):** Mining Speed +200, Mining Fortune +80, True Defense +240, Magic Find +20
- **Per-piece:** Helmet +50 ms/+20 mf/+5 mspd/+50 td; Chest +50 ms/+20 mf/+5 mspd/+80 td; Legs +50 ms/+20 mf/+5 mspd/+70 td; Boots +50 ms/+20 mf/+5 mspd/+40 td
- **Special:** 2+ pieces = permanent Invisibility effect, -40% damage from Ghosts
- **Ability:** Mist Aura — Hides wearer in mist
- **Requirement:** Heart of the Mountain Tier V
- **Craft:** 72 Sorrow (dropped by Ghosts in The Mist)
- **Notes:** No HP or Defense — pure mining stats + True Defense. Most True Defense of any armor set. Popular for Blaze Slayer beginners due to True Defense (with Opal gems). Gives most Magic Find of non-kuudra sets. Universal gemstone slots.

#### Armor of Divan
- **Source:** `data/wiki/Armor of Divan.wiki`
- **Rarity:** Legendary
- **Stats (full set):** Mining Speed +320, Mining Fortune +120, HP +510, Defense +540, plus gem slots for more
- **Per-piece:** Helmet +80 ms/+30 mf/+100 hp/+130 def; Chest +80 ms/+30 mf/+200 hp/+130 def; Legs +80 ms/+30 mf/+130 hp/+170 def; Boots +80 ms/+30 mf/+80 hp/+110 def
- **Gemstone slots (per piece, via Gemstone Chambers):** 2 Jade, 2 Amber, 1 Topaz (expandable up to 5 Gemstone Chambers per piece)
- **Requirement:** Heart of the Mountain 6
- **Obtaining:** Forged in The Forge (24 hours per piece). Requires Divan Fragments + assorted Fine Gemstones + Sludge Juice.
- **Notes:** End-tier mining armor. Gemstone Chambers allow Perfect Jade/Amber/Topaz for massive Mining Fortune/Speed bonuses. Each piece takes 23 hours to forge.

---

### 2.3 Farming Armor

#### Farmer Boots
- **Source:** `data/wiki/Farmer Boots.wiki`
- **ID:** `farmer_boots`
- **Rarity:** Uncommon (single piece)
- **Stats:** HP +40; Defense: 20 + 2 per Farming level; Speed: 10 + 4 per Farming level
- **Collection:** Pumpkin IX
- **Requirement:** Farming 18 to use
- **Craft:** 256 Enchanted Pumpkin (40,960 raw Pumpkin)
- **At Farming 60:** Defense ~140, Speed ~250
- **Notes:** Upgrades to Rancher's Boots.

#### Rancher's Boots
- **Source:** `data/wiki/Rancher's Boots.wiki`
- **ID:** `ranchers_boots`
- **Rarity:** Epic (single piece)
- **Stats:** HP +100; Defense: 70 + 2 per Farming level; Speed: 50 + 4 per Farming level; Farming Fortune +1 per level on The Garden
- **Collection:** Pumpkin XI
- **Requirement:** Farming 21 to use
- **Craft:** 16 Polished Pumpkin + 1 Farmer Boots (requires Pumpkin XI)
- **Gemstone slots:** 2 Peridot slots
- **Abilities:**
  - Farmer's Speed (LEFT CLICK): Set a maximum Speed cap (20–1000)
  - Farmer's Grace: Immunity to trampling crops
- **At Farming 60:** Defense ~190, Speed ~290, Farming Fortune +60 (on Garden)
- **Notes:** Industry standard farming boots. Speed cap feature is critical for crop farming. Non-salable. Does not raise player's absolute speed cap by itself — needs other items for super-speed builds.

---

### 2.4 Fishing Armor

#### Angler Armor
- **Source:** `data/wiki/Angler Armor.wiki`
- **Rarity:** Common (8-piece set with Equipment)
- **Stats (armor only):** Defense +105; Sea Creature Chance +4% (1% per piece)
- **Per-piece:** Helmet +20 def/+1% scc; Chest +40 def/+1% scc; Legs +30 def/+1% scc; Boots +15 def/+1% scc
- **Tiered Bonuses:**
  - Depth Champion (0/8 pieces): -3% to -10% damage from Sea Creatures
  - Deepness Within (0/4 armor pieces): +6–10 HP per Fishing level
- **Cost:** 100 coins per piece from Fish Merchant NPC
- **Notes:** Dirt cheap. 8-piece includes Equipment (Necklace, Cloak, Belt, Bracelet). As of Mar 2025, tiered bonuses replaced old full-set bonuses.

#### Shark Scale Armor
- **Source:** `data/wiki/Shark Scale Armor.wiki`
- **Rarity:** Legendary
- **Stats (full set):** HP +545, Defense +545, Sea Creature Chance +10% (2.5% per piece)
- **Per-piece:** Helmet +120 hp/+120 def/+2.5% scc; Chest +175 hp/+175 def/+2.5% scc; Legs +150 hp/+150 def/+2.5% scc; Boots +100 hp/+100 def/+2.5% scc
- **Set Bonus:** Absorb — Doubles Defense while in water
- **Tiered Bonus:** Festival Fisher — +0/15/20/25% Shark catch chance during Fishing Festival (0/1/2/4 pieces)
- **Requirement:** Fishing 24
- **Craft:** 2 Enchanted Shark Fin + existing Sponge Armor piece (per piece)
- **Notes:** Can be boosted up to +20% stats with Megalodon Pet. Fourth-highest SCC in game; highest of water-fishing sets.

---

### 2.5 Dungeon-Specific Armor Summary

| Armor Set | Rarity | Floor Req | Key Stat Focus |
|-----------|--------|-----------|----------------|
| Adaptive Armor | Epic | F3 cleared | Versatile, scales with Cata level, class bonuses |
| Shadow Assassin Armor | Epic (→Leg starred) | F5 cleared | Strength/CD stacking, +1 Str per kill |
| Necron's Armor | Legendary | F7 cleared | Best stats overall, Wither resist, Witherborn |

#### Notes on Dungeonized Dragon Armor vs Native Dungeon Armor
- Dragon armor (Unstable, Strong, Young, Superior) can be dungeonized via Dragon Essence
- After dungeonization, they gain +10% stats per star INSIDE dungeons
- **Without dungeonization, dragon armor gets ZERO dungeon stat scaling**
- Native dungeon armor (Adaptive, SA, Necron) is already dungeon-native — no conversion needed
- For F5+, Shadow Assassin generally beats dungeonized dragon armor
- For endgame, Necron's Armor is the clear winner

---

## PART 3: QUICK REFERENCE TABLES

### Weapon Progression (Melee)

| Stage | Weapon | Damage | Requirement | Cost Tier | Notes |
|-------|--------|--------|-------------|-----------|-------|
| Early | Undead Sword | +30 | None | 100c | +100% vs undead |
| Early | AOTE | +100 | Ender Pearl VIII | ~500K craft | Mobility + damage |
| Mid | Super Cleaver | +105 | None | 80K NPC | Buy from Ophelia |
| Mid | Hyper Cleaver | +175 | F3 cleared | 800K NPC | Beats AOTD |
| Mid-Late | Giant Cleaver | +235 | F6 cleared | 5M NPC | Best until F7 |
| Late | Livid Dagger | +210 | F5 cleared | 7M+ (chest) | Backstab +100% dmg |
| Late | Shadow Fury | +300 | F5 cleared | 15M+ (chest) | Teleport/tag 5 mobs |
| Late | Flower of Truth | +160 | F6 cleared | ~2M craft | Precursor to BoL |
| Late | Bouquet of Lies | +220 | F6 cleared | ~10M craft | Pair with Giant Cleaver |
| Endgame | Giant's Sword | +500 | F6 cleared | 50–100M | AH-only, rarely drops |
| Endgame | Necron's Blade | +260 | F7 cleared | Craft (F7 mats) | Refine to Hyperion/etc |
| Endgame | Wither Cloak Sword | +190 | F7 cleared | 4.5M (chest) | Defensive/utility |

### Weapon Progression (Ranged)

| Stage | Weapon | Damage | Requirement | Notes |
|-------|--------|--------|-------------|-------|
| Early-Mid | Runaan's Bow | +160 | Bone IX | Triple shot, 40% side arrows |
| Mechanic | Spirit Bow | N/A | F4 run | Only Thorn damage, F4 only |
| Late | Juju Shortbow | +310 | Enderman Slayer 5 | Instant fire, 3-mob AOE |
| Endgame | Terminator | +310 | Enderman Slayer 7 | Best bow, CC/4 downside |

### Armor Progression (Combat)

| Stage | Armor | Defense | Requirement | Notes |
|-------|-------|---------|-------------|-------|
| Early | Lapis Armor | +120 | Mining 5 | +200% ore XP, drop from Lapis Zombies |
| Mid | Hardened Diamond | +330 | Diamond VII | Craft step |
| Mid | Ender Armor | +200 (+400 in End) | Combat 12 | x2 in End Island |
| Mid | Unstable Dragon | +500 | Combat 16 | +20% CC/+60% CD |
| Mid | Strong Dragon | +500 | Combat 16 | AOTE synergy set |
| Mid | Young Dragon | +500 | Combat 16 | Speed/mobility set |
| End | Superior Dragon | +600 | Combat 20 | +5% all combat stats |
| Dungeon | Adaptive Armor | +245 | F3 cleared | Class bonuses, scales with Cata |
| Dungeon | Shadow Assassin | +330 | F5 cleared | +1 Str/kill stacking |
| Endgame | Necron's Armor | +450 | F7 cleared | Best overall dungeon armor |

### Dragon Armor Dungeonization Cata Requirements

| Set | Cata Level Required (Dungeonized) | Worth Dungeonizing? |
|-----|----------------------------------|---------------------|
| Unstable Dragon | Cata 10 | Yes, until F5 |
| Young Dragon | Cata 10 | Yes for speed builds |
| Strong Dragon | Cata 12 | Only for AOTE build |
| Superior Dragon | Cata 14 | Debatable at high cost |

---

## PART 4: ITEMS THAT ARE TRAPS (Do Not Recommend)

### AOTD (Aspect of the Dragons)
- **Why it's a trap:** Drop item with no upgrade path; 3% chance per eye = expensive to obtain; Hyper Cleaver costs the same or less and is objectively better. The wiki's own Tips section says to use Super Cleaver instead.
- **Correct path:** Super Cleaver → Hyper Cleaver → Giant Cleaver

### One For All Enchant
- **Why it's a trap:** Per wiki (Bouquet of Lies): "One For All does not buff the damage of Bouquet of Lies." Giant's Sword trivia: "Before OFA was nerfed, the Giant's Sword could achieve +1643 damage... the base damage can no longer exceed +580." The enchant is no longer effective on the best weapons.

### Giant's Sword (buying from AH)
- **Why it's a trap:** Wiki explicitly states: "not worth buying from the AH, only worth it if you drop one." The drop chance is 0.1875% from Bedrock F6 chest, and AH prices reflect that rarity (50–100M+). Buy a Giant Cleaver instead.

---

## SOURCES CITED

All data extracted from:
- `~/projects/hypixel-skyblock/data/wiki/Undead Sword.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Aspect of the End.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Aspect of the Dragons.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Super Cleaver.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Hyper Cleaver.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Giant Cleaver.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Livid Dagger.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Shadow Fury.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Flower of Truth.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Bouquet of Lies.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Giant's Sword.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Wither Cloak Sword.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Necron's Blade.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Hyperion.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Runaan's Bow.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Spirit Bow.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Juju Shortbow.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Terminator.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Bonzo's Staff.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Spirit Sceptre.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Star Upgrades.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Dungeon Items.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Lapis Armor.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Hardened Diamond Armor.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Ender Armor.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Dragon Armor.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Unstable Dragon Armor.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Strong Dragon Armor.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Young Dragon Armor.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Superior Dragon Armor.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Adaptive Armor.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Shadow Assassin Armor.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Necron's Armor.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Mineral Armor.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Sorrow Armor.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Armor of Divan.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Angler Armor.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Shark Scale Armor.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Farmer Boots.wiki`
- `~/projects/hypixel-skyblock/data/wiki/Rancher's Boots.wiki`
- `~/projects/hypixel-skyblock/data/wiki-official/Giant Cleaver.wiki` (supplementary history data)
