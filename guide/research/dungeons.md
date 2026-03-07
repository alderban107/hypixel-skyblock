# Dungeons (The Catacombs) — Research Notes

Sourced from: `data/wiki-official/Catacombs.wiki`, floor pages, class pages, and gear pages.
Applied corrections from known errata. See "Key Corrections" section.

---

## 1. General System

### Access

- Talk to **Mort** in the **Dungeon Hub** or at the **Catacombs Entrance**, or call him via Abiphone.
- Default: party of 2–5 required.
- **Solo unlock**: Complete F3, get **Saul's Recommendation** from Adventurer Saul, give it to Mort.

### What Changes Inside Dungeons

- No warping to Private Island.
- No Auction House, Bazaar, or Anvil (even with Cookie).
- No horses/mounts.
- Shops charge from **bank**, not purse.
- `Drop` key = Ultimate class ability. `Drop Stack` key = Normal class ability.
- Hitting mobs regenerates **5 + 1% of max Mana** per hit (sword or bow).
- No God Potions. Only 1 potion per run (exceptions: Stamina, Healing, Mana potions).
- Speed above 100 is reduced by 33.3%.
- Vampirism healing nerfed 10x inside dungeons.
- 70-minute run time limit.

### Dungeon Stats vs. Outside Stats

**Dungeon Items** scale heavily inside the Catacombs. Outside, regular stars give +2% per star. Inside:
- Each regular star (✪): **+10% stat bonus** inside dungeons.
- Max 5 stars = +50% bonus inside.
- Master Stars: additional +5% each inside Master Mode (up to +75% total from stars in MM).
- Stars have **no effect outside** dungeons beyond the +2% per star.
- **Catacombs Level** also scales item stats inside — formula adds up to +475% bonus at high Cata levels.
- Non-dungeonized armor = **ZERO scaling** inside dungeons (important: Dragon Armor must be dungeonized).

**Gear Score** is purely informational — no gameplay effect.

### Dungeon Item Cata Level Requirements

Item requirements are set based on the floor the item drops from (not an arbitrary number). Examples:
- Cata 1: Rotten Armor, Skeleton Grunt Armor
- Cata 8: Sniper Helmet, Runaan's Bow, Leaping Sword
- Cata 10: Young/Old/Unstable/Holy Dragon Armor
- Cata 12: Strong/Wise/Protector Dragon Armor, Skeleton Master Armor
- Cata 14: Superior Dragon Armor, Zombie Knight Armor
- Cata 15: Skeletor Armor, Super Heavy Armor, Juju Shortbow
- Cata 27: Terminator

**Floor completion requirements** (item must be equippable after clearing that floor):
- F1: Bonzo's Mask, Bonzo's Staff
- F3: Adaptive Armor, Shadow Goggles, Hyper Cleaver
- F4: Spirit Boots, Spirit Bow, Spirit Sword, Bone Boomerang
- **F5: Shadow Assassin Armor**, Last Breath, Livid Dagger, Shadow Fury
- F6: Necromancer Lord Armor, Giant's Sword, Flower of Truth
- **F7: All Wither Armor variants (Necron's, Storm's, Goldor's, Maxor's), Wither Cloak Sword, Hyperion, Scylla, Astraea, Valkyrie, Necron's Blade**
- M7: Dark Claymore

### Dragon Armor Dungeonization Requirements

Must be dungeonized to scale inside:
- Young Dragon Armor: Cata 10 to equip
- Strong Dragon Armor: Cata 12 to equip
- Unstable Dragon Armor: Cata 12 to equip
- Superior Dragon Armor: Cata 14 to equip

---

## 2. Classes

Players choose one class per run. If you are the **only player of your class** in a run, all class abilities are **doubled in strength**.

Class XP is earned by playing the class. Teammates also gain some XP passively when one player is on a given class.

### Healer

**Role**: Support, healing, revives
**Primary stat**: Health/Intelligence

**Passives:**
- *Renew*: Healing abilities heal for 50% additional HP.
- *Healing Aura*: Passively heals all teammates within 8 blocks for 0.5% HP/sec.
- *Revive*: Spawns a fairy that follows and revives dead teammates. 100s cooldown after reviving.
- *Orbies*: 15% chance for killed enemies to drop healing orbs (30% max HP heal + stat buff).
- *Soul Tether*: Click a teammate to tether; heals them 0.5% HP/sec + 1% HP per 5 melee hits.
- *Overheal*: Healing a full-health player converts excess into absorption shield (up to 20% HP).

**Abilities:**
- *Healing Circle* (normal): Healing orb creates an AoE heal zone (2% HP/sec). 2s cooldown.
- *Wish* (ultimate): Heals entire party to full + 20% absorption shield. 120s cooldown.

**Ghost Abilities:**
- *Healing Potion*: Heals teammates within 10 blocks for 10% max HP + 100 HP flat.
- *Revive*: Auto-revive self after 50 seconds.

**Gear notes**: Prioritize HP and sustain. Strong Blood set (4-piece Zombie Soldier or similar) is common early. Healer benefits from high HP pools for Overheal effectiveness.

---

### Mage

**Role**: AoE damage, ability/magic damage
**Primary stat**: Intelligence

**Passives:**
- *Mage Staff*: All melee attacks become ranged, dealing 30% + 5 of melee damage (scaled by Intelligence) up to 10 blocks. This is the "mage beam" — extremely high single-target damage at high Int.
- *Efficient Spells*: All abilities have 25% shorter cooldown.

**Abilities:**
- *Guided Sheep* (normal): Sheep projectile that destroys weak walls/crypts. Damage scales with Mage level. 30s cooldown.
- *Thunderstorm* (ultimate): 10-block radius lightning for 15s. Scales with Mage level.

**Ghost Abilities:**
- *Instant Wall*: 5×3 wall at cursor for 10s.
- *Fireball*: Fireball dealing level-scaled damage.

**Playstyles:**
- **Left-Click Mage**: Uses Mage Staff beam for high single-target damage. Optimize Str + Crit Damage + Int. Best weapons: Dark Claymore, Midas' Sword with Chimera. Best armor: Ancient Storm's Armor.
- **Right-Click Mage**: Uses weapon abilities for AoE. Prioritize ehp or mana pool. Good weapons: Hyperion, Astraea (more ehp), Midas' Staff, Ice Spray Wand.

**Gear notes**: Storm's Armor (high Int), Wise Dragon Armor, or Necromancer Lord Armor. Hyperion or Astraea are late-game weapons.

---

### Berserk

**Role**: Melee single-target DPS, self-sustain
**Primary stat**: Strength, Crit Damage

**Passives:**
- *Bloodlust*: After killing a mob, next hit deals +20% damage and heals 1% of damage dealt. Expires after 5 seconds. Also grants +30 Speed and +30% Melee Damage passively.
- *Lust for Blood*: Each hit on an enemy increases damage to that enemy by 5%, up to 100% (1100% cap at level 50).

**Abilities:**
- *Throwing Axe* (normal): Deals damage equal to your highest melee hit in the last minute. 10s cooldown.
- *Ragnarok* (ultimate): Summons 3 zombie minions. 60s cooldown.

**Ghost Abilities:**
- *Buff Potion*: +30 Strength to nearby teammates in 10 blocks.
- *Ghost Axe*: Throws an axe dealing level-scaled damage.

**Gear notes**: Necron's Armor or Maxor's Armor. Shadow Assassin is a common mid-game set. Weapons: Shadow Fury, Hyperion (for teleport cleave), Scylla, Valkyrie.

---

### Archer

**Role**: Ranged DPS, AoE + single target
**Primary stat**: Strength, Crit Damage

**Passives:**
- *Doubleshoot*: 50% chance to shoot a second arrow (101% chance at level 50).
- *Bone Plating*: Reduces next incoming hit by a scaling amount (250s cooldown).
- *Bouncy Arrows*: Chance for arrows to bounce to additional targets (100% at level 50). 15s cooldown.

**Abilities:**
- *Explosive Shot* (normal): Shoots 3 exploding arrows dealing highest bow hit in a 4-block radius. 40s cooldown (20s at level 50).
- *Rapid Fire* (ultimate): 5 arrows/sec for 4 seconds (8 seconds at level 50) at 75% of highest bow hit.

**Ghost Abilities:**
- *Healing Bow*: Heals a teammate for 20% max HP + 50 Str for 10s. Note: causes knockback.
- *Stun Bow*: Stuns non-boss mobs temporarily. 5s cooldown.

**Gear notes**: Relies on high Crit Damage and Strength. Fragile — low ehp. Best bow: Terminator (Cata 27), Juju Shortbow (Cata 15), Runaan's Bow. Shadow Assassin or Necron's armor are used.

---

### Tank

**Role**: Damage absorption, mob control, team protection
**Primary stat**: Health, Defense

**Base bonuses**: +100 HP, +50 Defense just from being Tank class.

**Passives:**
- *Protective Barrier*: Permanent +25% Defense. Below 50% HP, gain 10% HP absorption shield (90s cooldown). When sole tank, +50% defense and triggers at 100% HP (always active, 45s cooldown).
- *Taunt*: Increases mob aggro toward you when above 25% HP.
- *Diversion*: Diverts 80% of damage taken by teammates within 30 blocks to you.
- *Defensive Stance*: Immunity to mob knockback.

**Abilities:**
- *Seismic Wave* (normal): Line attack dealing 20,000 + 10% per 50 Defense. 15s cooldown.
- *Castle of Stone* (ultimate): 70% damage reduction for 20s + aggros nearby mobs. 150s cooldown.

**Ghost Abilities:**
- *Stun Potion*: Stuns all mobs in 10 blocks.
- *Absorption Potion*: +200 absorption to teammates in 10 blocks.

**Gear notes**: Super Heavy Armor, Goldor's Armor. Tank is most effective in a full party where Diversion protects allies.

---

## 3. Floor-by-Floor Guide

### Entering Dungeons

**Entry requirement for the Catacombs (any floor)**: Combat Level 15 (not 24 — that was an old requirement that's been corrected).

### Floor Summary Table

| Floor | Cata Req | Boss | Size | Secret % for S+ | Speed Limit |
|-------|----------|------|------|-----------------|-------------|
| Entrance | Combat XV | The Watcher | Tiny (4×4) | — | — |
| F1 | Cata I | Bonzo | Tiny (4×5) | 30% | 10 min |
| F2 | Cata III | Scarf | Small (5×5) | 40% | 10 min |
| F3 | Cata V | The Professor | Small (5×5) | 50% | 10 min |
| F4 | Cata IX | Thorn | Small (6×5) | 60% | 12 min |
| F5 | **Cata XIV** | Livid | Medium (6×5) | 70% | 10 min |
| F6 | Cata XIX | Sadan | Medium (6×6) | 85% | 12 min |
| F7 | Cata XXIV | Wither Lords | Large (6×6) | 100% | 14 min |

Master Mode requires completing the normal floor first, then reaching the listed Cata level.

---

### Entrance

- **Requirement**: Combat Level 15
- **Boss**: The Watcher (stalker creature collecting adventurers)
- **Size**: Tiny (4×4)
- **No reward chests** — entrance only; no essence loot.
- **Auto-revive**: Available.
- Teaches basic mechanics. Do a few runs to unlock F1.

---

### Floor I — Bonzo

- **Requirement**: Cata Level 1
- **Boss**: Bonzo — New Necromancer; "Originally worked as a Circus clown."
- **Size**: Tiny (4×5)
- **Auto-revive**: Yes, after 50 seconds (last floor with auto-revive after F2).
- **Puzzles**: Creeper Beams, Teleport Maze, Three Weirdos, Water Board, Tic Tac Toe.

**Boss Mechanics**: Bonzo fights with summoned undead. Relatively simple entry-level fight.

**Notable Drops**:
- **Bonzo's Mask** (helmet) — F1 floor completion required to equip. Death prevention mechanic: when you take fatal damage, the mask triggers and prevents death (one-time per run). **Use as a swap item, not full-time** — wearing it breaks your 4-piece armor set bonus.
- Bonzo's Staff — early mage weapon
- Rotten Armor, Skeleton Grunt Armor, Skeleton Soldier Armor

**Recommended gear**: Any starting equipment. Zombie Soldier Armor is a solid budget starter. Bonzo's Mask from the Bonzo II collection (50 kills) is free.

**Grind note**: F1 is fast and straightforward. Grind here briefly, then move to F2/F3.

---

### Floor II — Scarf

- **Requirement**: Cata Level 3
- **Boss**: Scarf — Apprentice Necromancer; "First of his class."
- **Size**: Small (5×5)
- **Auto-revive**: Yes, after 95 seconds. **Last floor with auto-revive.**
- **Puzzles**: Creeper Beams, Teleport Maze, Three Weirdos, Water Board, Tic Tac Toe, Higher or Lower.

**Boss Mechanics**: Scarf spawns Undead Archer, Mage, Warrior, and Priest. Each has distinct behavior. Kill the adds to weaken Scarf.

**Notable Drops**: Stone Blade, Red Scarf, Scarf Studies, Skeleton Master Boots.

**Recommended gear**: Working toward Zombie Soldier Armor or Adaptive Armor. Cata 3 required.

---

### Floor III — The Professor

- **Requirement**: Cata Level 5
- **Boss**: The Professor — "Failed the Masters exam three times. Works from 8 to 5."
- **Size**: Small (5×5)
- **Auto-revive**: None from F3 onward.
- **Trap Rooms**: First floor with Trap Rooms.
- **Puzzles**: Creeper Beams, Teleport Maze, Three Weirdos, Water Board, Tic Tac Toe, Higher or Lower, Boulder, Ice Path.
- New mobs: Skeletors, Zombie Knights, Zombie Soldiers, Shadow Assassin miniboss, King Midas miniboss.

**Boss Mechanics**: The Professor fights with Guardian minions (Chaos, Healthy, Reinforced, Laser). Must manage adds while damaging The Professor.

**Notable Drops**: Adaptive Armor, Shadow Goggles, Mender Fedora, Hyper Cleaver, Super Undead Bow. Also: Skeletor Armor, Zombie Knight Armor, Zombie Soldier Armor from mob drops.

**Saul's Recommendation**: Defeating The Professor unlocks Adventurer Saul's item for solo queue access.

**Progression note — F3 is a major grind floor.** Grind F3 until **Cata 14–15** before attempting F5. F4 exists but is considered a weak floor for XP efficiency.

---

### Floor IV — Thorn

**SKIP THIS FLOOR FOR PROGRESSION.** F4 gives poor XP relative to F3 and F5. Grind F3 until Cata 14–15, then jump to F5.

- **Requirement**: Cata Level 9
- **Boss**: Thorn — Shaman Necromancer; "Calls himself a vegetarian, go figure."
- **Size**: Small (6×5)
- **No auto-revive.**
- **Dungeon Chest Keys** first appear as drops from F4+.
- New mobs: Frozen Adventurers, Spirit Bears, Spirit Animals.

**Boss Mechanics**: Thorn has a Spirit Bow mechanic — you must shoot a Spirit Bow at Thorn while he's airborne. The Spirit Bow drops during the fight. A Fairy Room also appears during the fight, reviving dead players.

**Notable Drops**:
- **Spirit Boots** (F4 completion required) — grants temporary flight and invincibility (Spirit Glide ability). Strong boots even compared to F7 Wither Armor boots. Upgrade with Thorn Fragments for +10 Str, +10 Speed.
- Spirit Bow, Spirit Sword, Bone Boomerang, Bat Wand, Bone Reaver

**Note on Spirit Boots**: Very useful even at high progression for the Spirit Glide ability. Often kept as a swap item.

---

### Floor V — Livid

- **Requirement**: **Cata Level 14** (not 16 — confirmed from wiki).
- **Boss**: Livid — Master Necromancer; "Strongly believes he will become the Lord one day."
- **Size**: Medium (6×5)
- **No auto-revive.**
- **Bedrock Chest** first becomes available from F5+ (requires S+ score, costs 2M coins).

**Boss Mechanics**: Livid spawns multiple clones of himself. You must identify and kill the **real Livid** (distinguished by a specific color/name indicator). Hitting fakes does nothing meaningful. The real Livid cycles positions — coordinate with your party.

**Notable Drops**:
- **Shadow Assassin Armor** (F5 completion required, Epic rarity) — full set: 100 Str, 100 Crit Dmg, 735 HP, 330 Def, 28% Speed. Full set bonus: +1 Strength per mob kill in the run. Each piece buffs the player on teleport (invisibility, speed, healing, mana). Upgrade with Livid Fragments → +5 Str, +10 HP, +1 Spd per piece, upgrades to Legendary.
- Last Breath (bow), Livid Dagger, Shadow Fury (sword), Shadow Assassin Cloak

**Gear progression**: Shadow Assassin Armor is the primary mid-game dungeon set. It's a major step up from F3 gear. Aim to 5-star it with Wither Essence.

---

### Floor VI — Sadan

- **Requirement**: Cata Level 19
- **Boss**: Sadan — Necromancer Lord; "Says he once beat a Wither in a duel. Likes to brag."
- **Size**: Medium (6×6)
- **No auto-revive.**
- **New puzzle**: Quiz (F6+).
- **New mobs**: Zombie Commander, Skeletor Prime, Sleeping Golem, Woke Golem, Terracotta. Also spawns Giants: L.A.S.R., The Diamond Giant (Diamante), Jolly Pink Giant, Bigfoot.
- **Mimic**: First appearance. Killing Mimic gives +2 Bonus score.

**Boss Mechanics**: Sadan summons Giants (L.A.S.R., Diamante, Bigfoot, Jolly Pink Giant). Players must defeat all four giants before Sadan can be damaged. Giants have high HP and deal large damage. Each giant has distinct movement and attack patterns. After giants are killed, Sadan himself is fought.

**Important**: These giants spawn in F6 as part of the boss fight. Giants also appear as Watcher Undeads in F7. **Giants do NOT spawn as regular floor mobs in F7** — they are strictly boss-room or Watcher-spawned entities.

**Notable Drops**:
- Necromancer Lord Armor, Giant's Sword, Flower of Truth, Precursor Eye, Necromancer Sword, Giant Cleaver, Death Bow, Wither Goggles, Giant's Eye Sword
- Mimic Fragment (from Mimic)

---

### Floor VII — The Wither Lords

- **Requirement**: Cata Level 24
- **Bosses**: Maxor → Storm → Goldor → Necron (sequential phases), plus Wither King in M7.
- **Size**: Large (6×6)
- **No auto-revive.**
- **All puzzles** available including Ice Fill (F7 exclusive in normal mode).
- New mobs: Wither Guard, Wither Miner, Skeleton Lord, Zombie Lord, Zombie Commander.

**Boss Mechanics — 4 phases:**

1. **Maxor** — Deals high melee damage. Wither Armor + high HP required. Calls for burst damage.
2. **Storm** — Storm is agile and uses lightning/ranged attacks. Requires mobility and high DPS.
3. **Goldor** — Extremely high defense. Requires True Damage or specific mechanics to bypass defense. Triggers defense-lowering mechanic.
4. **Necron** — Final boss, uses multiple attack phases including a giant instakill mechanic. Spawns Giant Watcher Undeads (L.A.S.R., Diamante, Bigfoot, Jolly Pink Giant) during Watcher phase inside F7.

**M7 only**: Wither King appears as a 5th phase after Necron. M7 requires Cata 36.

**Notable Drops**:
- **All Wither Armor variants** (F7 completion required): Wither Armor (base), Maxor's Armor, Storm's Armor, Goldor's Armor, Necron's Armor
- **Necron's Handle** → used to craft Necron's Blade and Wither Armor upgrades
- **Wither Cloak Sword** (F7 completion required)
- **Hyperion** (F7 completion required) — top-tier Mage weapon
- **Scylla** (F7 completion required)
- **Astraea** (F7 completion required) — Mage/tank hybrid
- **Valkyrie** (F7 completion required)
- Skeleton Lord Armor, Zombie Lord Armor, Mimic Fragment

---

## 4. Dungeon Gear Reference

### Dungeon Item Stars

| Stars | Inside Bonus | Outside Bonus |
|-------|-------------|--------------|
| 1 ✪ | +10% | +2% |
| 2 ✪✪ | +20% | +4% |
| 3 ✪✪✪ | +30% | +6% |
| 4 ✪✪✪✪ | +40% | +8% |
| 5 ✪✪✪✪✪ | +50% | +10% |
| +1 Master Star (MM) | +5% additional | None |

Star upgrades use **Wither Essence** (for most dungeon items) at the Essence Shops.

---

### Key Gear Items

#### Bonzo's Mask
- **Source**: F1 reward chests / Bonzo II collection (free at 50 kills)
- **Equip req**: F1 completion
- **Ability**: Triggers once per run to prevent death (instakill prevention)
- **Use**: Swap it onto your head when near death — then swap back. Do NOT wear it full-time, as it breaks your 4-piece armor set bonus (e.g., Strong Blood set). Bonzo's Mask and Spirit Mask have **separate cooldowns** — you can chain both.
- **Upgrade**: 8 Bonzo Fragments → ⚚ version (+25 HP, +50 Int)

#### Spirit Boots
- **Source**: F4 reward chests / Thorn V collection (400 kills)
- **Equip req**: F4 completion
- **Stats**: Strong standalone boots; often compete with Wither Armor boots
- **Ability**: *Spirit Glide* — flight + invincibility for ~5 seconds
- **Use**: Either full-time boots or a swap item for traversal/escape
- **Upgrade**: 8 Thorn Fragments → +10 Str, +10 Spd

#### Shadow Assassin Armor
- **Source**: F5 reward chests
- **Equip req**: F5 completion
- **Rarity**: Epic (Legendary with Livid Fragments)
- **Stats**: 100 Str, 100 Crit Dmg, 735 HP, 330 Def, 28% Speed
- **Set bonus**: +1 Strength per kill in the dungeon run
- **Teleport buffs**: Per-piece bonuses trigger on teleport (invisible 10s, +10 Str 10s, 1% HP heal, +10 Mana)
- **Upgrade**: 8 Livid Fragments per piece → +5 Str, +10 HP, +1 Spd each

#### Necromancer Lord Armor (F6)
- **Source**: F6 reward chests
- **Equip req**: F6 completion
- Decent Mage support set with good ehp

#### Wither Armor Variants (F7)

All Wither Armor requires **F7 completion** to equip. Base stats are similar across variants; each is specialized:

| Armor | Specialization | Key Stats |
|-------|---------------|-----------|
| Maxor's Armor | Speed / HP | High HP, Speed |
| Storm's Armor | Intelligence / Mage | High Int, balanced Str/CD |
| Goldor's Armor | Defense / Tank | Highest Defense |
| Necron's Armor | Strength / Damage | 160 Str, 120 CD, Witherborn set bonus |

**Necron's Armor stats**: 815 HP, 450 Def, 120 CD, 160 Str, 60 Int. Set bonus *Witherborn*: spawns a wither minion every 30s that attacks nearby enemies. Crafted by surrounding any Wither Armor piece with 8 Diamante's Handles (from Necron chest drops).

**Common substitutions**: Many players swap Necron's Chestplate for cheaper alternatives (Zombie Knight Chestplate, Shadow Assassin Chestplate, Necromancer Lord Chestplate). Necron's Helmet is often replaced with Golden Necron Head, Tarantula Helmet, or Primordial Helmet.

#### Key Weapons

| Weapon | Floor | Notes |
|--------|-------|-------|
| Bonzo's Staff | F1 | Early Mage weapon |
| Spirit Bow | F4 | Required for Thorn boss fight; also a decent early bow |
| Shadow Fury | F5 | Teleport weapon; chains teleports rapidly; good Berserk/Archer |
| Livid Dagger | F5 | Fast melee, good for Berserk |
| Giant's Sword | F6 | Heavy-hitting melee |
| Necron's Blade | F7 | Top-tier F7 sword; scrolls expand its abilities |
| Hyperion | F7 | Top Mage weapon (Int/ability damage builds) |
| Astraea | F7 | Mage with more ehp than Hyperion |
| Scylla | F7 | Berserk sword |
| Valkyrie | F7 | Berserk/Tank hybrid |
| Wither Cloak Sword | F7 | Requires F7 completion |

---

## 5. Scoring and Secrets

### Score Categories

| Category | Range | Notes |
|----------|-------|-------|
| Skill | 20–100 | Starts at 20; -2 per death, -14 per failed puzzle |
| Exploration | 0–100 | 60 pts for rooms cleared + 40 pts for secrets |
| Speed | 0–100 | 100 if under time limit; decays after |
| Bonus | 0–17 | Crypts (+5 max), Mimics (+2, F6/F7 only), Paul EZPZ perk (+10) |

**Total max possible: 317** (with Paul perk and Mimics killed)

### Score Rankings

| Rank | Score Required |
|------|---------------|
| S+   | 300+ |
| S    | 270+ |
| A    | 230+ |
| B    | 160+ |
| C    | 100+ |
| D    | Under 100 |

### Chest Unlock Requirements

| Chest | Score Req | Cost (F3–F7) |
|-------|-----------|-------------|
| Wood | None | Free |
| Gold | None | 100,000 |
| Diamond | None | 250,000 |
| Emerald | A (230+) | 500,000 |
| Obsidian | S (270+) | 1,000,000 |
| Bedrock | S+ (300+) | 2,000,000 (F5+ only) |

Bedrock chest is only available on **F5 and higher**. This is where the best gear drops.

### Secret Requirements by Floor

To max out the Exploration score secrets component (40 points), you need to find at least:

| Floor | Secrets Required (% of total) |
|-------|-------------------------------|
| F1 | 30% |
| F2 | 40% |
| F3 | 50% |
| F4 | 60% |
| F5 | 70% |
| F6 | 85% |
| F7 | 100% |
| Master Mode | 100% |

For F7 and Master Mode, **all secrets must be found** for full exploration score.

### Speed Limits (for 100 Speed Score)

| Floor | Time Limit |
|-------|-----------|
| F1, F2, F3, F5 | 10 minutes |
| F4, F6 | 12 minutes |
| F7 | 14 minutes |
| M1–M5 | 8 minutes |
| M6 | 10 minutes |
| M7 | 14 minutes |

### S+ Requirements (Practical)

To reliably hit S+ (300+):
- **Zero failed puzzles** (each costs 14 Skill points)
- **Max 2 deaths** in F1–F5, max 3 in F6–F7 (with Paul: up to 7–8 deaths total)
- **Complete all rooms** for full room score
- **Find required % of secrets** (see table above)
- **Finish under the time limit**

### Bonus Points

- Kill Crypt Undeads in blown-up Crypts: +1 per kill, up to +5 max (always worth it)
- Kill Mimic on F6 or F7: +2 (Mimic can appear disguised as a chest)
- Paul mayor EZPZ perk active: +10 bonus score (massive for S+)

---

## 6. Blessings

Blessings are temporary stat boosts shared by all party members. They stack and scale with floor level.

| Blessing | Stats | Per Level |
|----------|-------|-----------|
| Blessing of Life | HP, Heal Rate | +3% per level |
| Blessing of Power | Strength, Crit Damage | +2% per level, +4 flat |
| Blessing of Stone | Defense, Damage | Def +2%/+4 flat, Dmg +6 flat |
| Blessing of Wisdom | Intelligence, Speed | +2% per level, +4 flat |
| Blessing of Time | HP, Def, Str, Int | +2% per level, +4 flat (from Quiz puzzle only) |

- **Mobs/puzzles**: Always grant Level V blessings.
- **Secrets**: Grant Level I or II blessings only.
- Stacks: Getting the same blessing multiple times adds to existing tier.
- Blessings from secrets are lower power — but free.

---

## 7. Rooms and Generation

| Room Type | Description |
|-----------|-------------|
| Regular | Standard combat rooms (1×1 to 4×1, L-shaped, 2×2) |
| Start | Starting room with Mort; class selection happens here |
| Fairy | Healing pool + fairies (drop Revive Stones); no key required |
| Puzzle | Various puzzles; one per floor |
| Miniboss | Angry Archaeologist, Lost/Frozen Adventurer, Shadow Assassin, King Midas |
| Trap | F3+; disables abilities; navigate traps to complete |
| Blood | Final room before boss; The Watcher spawns mob waves; kill all to open boss portal |

**Wither Key**: Drop from killing all starred mobs in a room. Opens locked doors.
**Blood Key**: Opens the Blood Room entrance.

### Dungeon Map Indicators

- White checkmark: room completed (all starred mobs killed)
- Green checkmark: room fully completed including all secrets
- Red X: failed puzzle room

---

## 8. Death System

When a player dies they become a **Ghost** with special ghost abilities. Ghosts can:
- Use Ghost Abilities (class-specific)
- Damage Fairies in Fairy Rooms to revive themselves
- Assist teammates

**Revive methods:**
1. Entering the boss portal (Blood Room → boss) auto-revives all ghosts
2. Revive Stone (carried before death or used by alive player)
3. Killing a Fairy in a Fairy Room (ghosts can do this)
4. Healer's revive ability
5. Killing a Wandering Soul (Watcher-spawned ghost lookalike)
6. Auto-revive in Entrance, F1, F2 (after set timer — not available F3+)

---

## Key Corrections Applied

The following corrections override any conflicting information that may appear in older guides:

| Topic | Wrong | Correct |
|-------|-------|---------|
| Dungeon entry (Combat level) | Combat 24 | Combat 15 |
| F5 entry requirement | Cata 16 | Cata 14 |
| F4 grind recommendation | Grind F4 | **Skip F4**; grind F3 to Cata 14–15, then go to F5 |
| Star bonus inside dungeons | Unclear | **+10% per star** inside; +2% per star outside |
| Stars outside dungeons | +10% | **+2% per star** outside |
| Gear Score | Gameplay effect | **Purely informational, no gameplay effect** |
| Bonzo's Mask usage | Wear full-time | **Swap item only** — breaks 4-piece set bonus if worn full-time |
| SA Armor equip requirement | Various | **F5 completion** |
| Wither Cloak/F7 weapons equip req | Various | **F7 completion** |
| Dragon Armor dungeonization req | N/A | Young=Cata 10, Strong/Unstable=Cata 12, Superior=Cata 14 |
| Non-dungeonized armor | Scales partially | **ZERO scaling** inside dungeons |
| Giants (L.A.S.R., Diamante, etc.) | Spawn on F7 | **F6 boss room** (normal) + Watcher Undeads in F7 — not as regular F7 floor mobs |
| Cata level req on items | Arbitrary | **Determined by drop floor** |
