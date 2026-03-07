# Slayer Research Notes

Sources: `data/wiki/Slayer.wiki`, `data/wiki/Zombie Slayer.wiki`, `data/wiki/Spider Slayer.wiki`,
`data/wiki/Wolf Slayer.wiki`, `data/wiki/Enderman Slayer.wiki`, `data/wiki/Blaze Slayer.wiki`,
`data/wiki/Revenant Horror.wiki`, `data/wiki/Tarantula Broodfather.wiki`,
`data/wiki/Sven Packmaster.wiki`, `data/wiki/Voidgloom Seraph.wiki`,
`data/wiki/Inferno Demonlord.wiki`

Last updated: 2026-03-04

---

## System Overview

Slayer Quests are started by talking to **Maddox the Slayer** under the Tavern at Hub (-75, 66, -56),
via **Maddox Batphone** (unlocked at Wolf Slayer 3), or an **Abiphone** contact.

Only 1 Slayer Quest can be active at a time per dimension. A quest costs coins to start, requires
earning a set amount of Combat XP from killing the corresponding mob type, then killing the boss
that spawns. Boss must be defeated within the time limit (usually 3–4 minutes) or it despawns and
the quest fails.

**Universal boss mechanics:**
- If the boss hasn't hit a player for a while, it rapidly regenerates HP. Stops when it hits again.
- If the player or boss stands in the same block too long, the boss does a True Damage slam-dunk.
- Knockback enchantment has no effect on slayer bosses.
- All bosses are immune to Aspect of the Dragons and Ice Spray Wand abilities.

**Auto-Slayer**: Automatically restarts the same slayer type after a successful kill. Unlocked at
LVL 6 in Zombie, Spider, and Wolf Slayer. This is **per-type**, not global — you enable/disable it
per slayer.

**RNG Meter**: Unlocked for each boss type by killing its T3 boss. XP from T3–T5 fills the meter.
Select an item to boost its drop chance; when full, that item is guaranteed next kill.

**Bits per kill**: T1 = 2, T2 = 5, T3 = 8, T4 = 12, T5 = 15.

**Global Combat Wisdom Buff**: Killing a new boss on T1/T2/T3 gives +1 Combat Wisdom. T4/T5 gives +2.
Maximum: +34 Combat Wisdom total.

**Token drop**: Always guaranteed after each kill:
- Zombie: Revenant Flesh
- Spider: Tarantula Web
- Wolf: Wolf Tooth
- Enderman: Null Sphere
- Blaze: Derelict Ashe

---

## XP to Level Up (all slayers)

| Level | Zombie | Spider | Wolf / Endo / Blaze |
|-------|--------|--------|---------------------|
| 1     | 5      | 10     | 10                  |
| 2     | 15     | 25     | 30                  |
| 3     | 200    | 200    | 250                 |
| 4     | 1,000  | 1,000  | 1,500               |
| 5     | 5,000  | 5,000  | 5,000               |
| 6     | 20,000 | 20,000 | 20,000              |
| 7     | 100,000| 100,000| 100,000             |
| 8     | 400,000| 400,000| 400,000             |
| 9     | 1,000,000|1,000,000|1,000,000          |

**LVL 6 bonus** (Zombie, Spider, Wolf): +3 token drops from minibosses.
**LVL 7 bonus** (Zombie, Spider, Wolf): 4% cheaper slayer quests.
**LVL 8**: Each slayer unlocks a unique perk + Bartender Mixin.
**LVL 9**: Additional perk (Enderman Slayer also has one).

---

## Unlock Chain

Zombie → Spider (kill T2 Revenant) → Wolf (kill T2 Tarantula) → Enderman (kill T4 Sven) →
Blaze (kill T3 Voidgloom Seraph)

---

## 1. Revenant Horror (Zombie Slayer)

**Unlock requirement**: Default (available from the start). Higher Combat level for higher tiers.
**Location**: Hub Graveyard, Hub Crypts, Deep Caverns, or anywhere with Zombie spawns.
**Token drop**: Revenant Flesh (always guaranteed).
**Main crafting resources**: Revenant Flesh, Revenant Viscera.

### Tier Table

| Tier | HP      | DPS    | Slayer XP | Cost    | Combat XP Required | Combat Level Req |
|------|---------|--------|-----------|---------|-------------------|-----------------|
| T1   | 500     | 15/s   | 5 XP      | 2,000   | 150               | —               |
| T2   | 20,000  | 25/s   | 25 XP     | 7,500   | 1,440             | Combat V (5)    |
| T3   | 400,000 | 120/s  | 100 XP    | 20,000  | 2,400             | Combat X (10)   |
| T4   | 1,500,000| 400/s | 500 XP    | 50,000  | 4,800             | Combat XV (15)  |
| T5   | 10,000,000| 2,400/s| 1,500 XP | 100,000 | 6,000            | Combat XXV (25), Zombie Slayer 7 |

Time limit: 3 minutes.

### Mechanics

**T1**: Life Drain — drains HP every few seconds.

**T2**: +Pestilence — AOE damage every second, shreds armor by 25%.

**T3**: +Enrage — at 40 seconds, enters "Mad" state; at 45 seconds, enters "Enraged" (faster, much
higher damage) for 12 seconds.

**T4**: Abilities unchanged from T3 but harder values.

**T5 (Atoned Horror)**: Completely different look and behavior. Immune to:
- All ability damage
- Arrows (and arrow-based items like Voodoo Doll)
- Wither Skeleton Pet's Death's Touch
- Bonemerang

The Atoned Horror has natural regen (1/1000 max HP per second = 10,000 HP/s normally).

Every second, a circle appears under the target's feet. After a short delay, the boss throws TNT
to the center of that circle. TNT deals % of the player's HP based on proximity to center. Boss
heals 500,000 HP when TNT hits a player. At 1/3 HP, TNT frequency doubles permanently.

After 30 seconds, the boss stops and creates a bedrock circle. After a 5-second countdown, it
releases a massive lightning barrage (7 block radius), killing anything. Bypasses End Stone Sword
and Mithril Coat. Then resumes normal behavior.

**Tip**: Standing at (-138, 42, -141) in Hub Crypts blocks the TNT attack. Useful for T5.

### Minibosses (spawn during T3+ quests)

| Miniboss         | HP          | Damage  | XP   | Min Tier | Drop          |
|------------------|-------------|---------|------|----------|---------------|
| Revenant Sycophant | 24,000    | 320     | 360  | T3       | 1 Revenant Flesh |
| Revenant Champion | 90,000     | 800     | 600  | T4       | 2 Revenant Flesh |
| Deformed Revenant | 480,000    | 1,600   | 1,200| T4       | 5 Revenant Flesh |
| Atoned Champion  | 600,000     | 800     | 900  | T5       | 2 Revenant Flesh |
| Atoned Revenant  | 2,400,000   | 1,600   | 1,600| T5       | 5 Revenant Flesh |

### Loot Table

| Drop              | T1    | T2    | T3    | T4    | T5    | Odds     | LVL Req |
|-------------------|-------|-------|-------|-------|-------|----------|---------|
| Revenant Flesh    | 1-3   | 9-18  | 30-50 | 50-64 | 63-64 | Guaranteed | 1    |
| Foul Flesh        | —     | 1     | 1-2   | 2-3   | 3-4   | ~16%     | 1       |
| Pestilence Rune I | —     | 1     | 1     | 1     | 1     | 0.67–6.33% | 2    |
| Undead Catalyst   | —     | 1     | 1     | 1     | 1     | 0.6–2.02% | 3    |
| Revenant Shard    | —     | —     | 1     | 1     | 1     | ~0.8–1.36% | — |
| Severed Hand      | —     | —     | 1     | 1     | 1     | 0.4–0.81% | 4 |
| Beheaded Horror   | —     | —     | 1     | 1     | 1     | 0.08–0.16% | 5 |
| Revenant Catalyst | —     | 1     | 1     | 1     | 1     | ~1%      | 6       |
| Snake Rune I      | —     | —     | —     | 1     | 1     | ~0.14–0.16% | 6  |
| Revenant Viscera  | —     | —     | —     | —     | 1-2   | 13.77%   | 7       |
| Scythe Blade      | —     | —     | —     | 1     | 1     | 0.06–0.1% | 7      |
| Shard of the Shredded | — | —   | —     | —     | 1     | 0.06%    | 7       |
| Warden Heart      | —     | —     | —     | —     | 1     | 0.01%    | 7       |
| Matcha Dye        | yes   | yes   | yes   | yes   | yes   | ~0.000007–0.0002% | — |

### Level Rewards (stat bonuses are permanent)

| LVL | XP Req    | Rank         | Stat Bonus         | Items Unlocked                                               |
|-----|-----------|--------------|--------------------|--------------------------------------------------------------|
| 1   | 5         | Noob         | +2 HP              | Wand of Healing                                              |
| 2   | 15        | Novice       | +2 HP              | Zombie Ring, Revenant Viscera                                |
| 3   | 200       | Skilled      | +2 HP              | Revenant Falchion, Wand of Mending, Crystallized Heart       |
| 4   | 1,000     | Destroyer    | +3 HP              | Revenant Leggings, Revenant Boots, Travel Scroll to Hub Crypts |
| 5   | 5,000     | Bulldozer    | +3 HP              | Revenant Minion, Devour Ring, Revenant Chestplate, Voodoo Doll, Small Slayer Sack |
| 6   | 20,000    | Savage       | +4 HP              | Wand of Restoration, Revived Heart, Reaper Falchion          |
| 7   | 100,000   | Deathripper  | +4 HP              | Zombie Artifact, Reaper Mask, Reaper Scythe, Wand of Atonement, full Reaper Armor |
| 8   | 400,000   | Necromancer  | +5 HP, +50 HR      | Reaper Orb, Axe of the Shredded, Warden Helmet; Bartender: Zombie Brain Mixin |
| 9   | 1,000,000 | Grim Reaper  | +6 HP              | —                                                            |

### Recommended Gear by Tier

- **T1–T2**: Basic combat gear. Any sword works. Spider Hat (if available) or Growth armor.
- **T3**: Dragon Armor reforged to Fierce recommended. Start using Life Steal/Syphon on weapons.
  Power Orbs strongly recommended. Lure into lava in Deep Caverns to slow movement.
- **T4**: Shadow Assassin Armor (Ancient reforge) + max enchanted Reaper Falchion. Guardian Pet (Epic/Legendary)
  with Wise Dragon or Storm's Armor works well. High HP alternative.
- **T5**: High HP + True Defense build. Safe spot at (-138, 42, -141) in Hub Crypts avoids TNT.
  Atoned Horror immune to ability damage and arrows — use melee only.

---

## 2. Tarantula Broodfather (Spider Slayer)

**Unlock requirement**: Kill T2 Revenant Horror.
**Location**: Spider's Den. Flaming Spider in Burning Desert also grants XP.
**Token drop**: Tarantula Web (always guaranteed).
**Main crafting resources**: Tarantula Web, Tarantula Silk.

> **NOTE**: Spider Slayer was REWORKED in July 2025. T5 was added, DPS values were buffed,
> Combat XP requirements to spawn T2/T3/T4 were increased. Old guides are outdated.
> T3 is now significantly harder than pre-rework.

### Tier Table

| Tier | HP                              | DPS      | Slayer XP | Cost    | Combat XP Required |
|------|---------------------------------|----------|-----------|---------|--------------------|
| T1   | 1,000 (was 750 before July 2025)| 35/s     | 5 XP      | 2,000   | 250                |
| T2   | 30,000                          | 55/s     | 25 XP     | 7,500   | 650 (was 600)      |
| T3   | 900,000                         | 260/s    | 100 XP    | 20,000  | 1,500 (was 1,000)  |
| T4   | 2,400,000                       | 530/s    | 500 XP    | 50,000  | 3,000 (was 2,000)  |
| T5   | 10M initial + 20M Conjoined = 30M total | 3,500/s (7,000 conjoined) | 1,500 XP | 100,000 | 6,000, Combat XXV, Spider Slayer 7 |

Time limit: 3 minutes.

### Mechanics

All tiers include all abilities from tiers below.

**T1**: Backstab — leaps behind the player and deals +50% damage.

**T2**: +Noxious Paralysis — reduces Vitality by 25% while alive; stacks -0.5% Speed cap debuff
every fifth hit.

**T3**: +Web of Lies — at 66% (600k) and 33% (300k) HP, leaps and spews web that disables
teleportation. 2 Egg Sacs appear above the boss (3 HP each); must be destroyed to remove web.
If eggs hatch, minions spawn. **Backstab deals +100% damage.**

**T4**: +Bat Barrage — at 66% (1.6M) HP, becomes immune to magic damage and releases bats.
Each bat deals 1% max HP/s as damage. **3 Egg Sacs at 6 HP each for Web of Lies.
Backstab deals +125%.**

**T5 (Primordial Broodfather)**: Immune to ability damage. Natural regeneration.
- Backstab: +150% damage.
- Noxious Paralysis: -99% Vitality, -2% Speed cap every fifth hit.
- Web of Lies: at 66% (6.7M) and 33% (3.3M). 4 Egg Sacs at 9 HP each.
- Bat Barrage: Primordial Bats deal 2% max HP/s.
- **Till Death Do Us Part**: At death, summons Primordial Broodmother and fuses into Conjoined Brood.
  Conjoined has double HP (20M), double DPS, but only passive abilities (Backstab + Noxious Paralysis).

**Note on T4**: Boss is immune to magic damage once Bat Barrage triggers. Bats are immune to magic
but Giant's Sword ability counts as melee and can clear them.

**Tip**: A Spider Shortbow or better is recommended for dealing with Egg Sacs at T3+. Back into
a corner to reduce the effectiveness of leap attacks.

### Minibosses (spawn during T3+ quests)

| Miniboss          | HP          | Damage | XP    | Min Tier | Drop           |
|-------------------|-------------|--------|-------|----------|----------------|
| Tarantula Vermin  | 54,000      | 260    | 150   | T3       | 1 Tarantula Web |
| Tarantula Beast   | 144,000     | 1,000  | 300   | T4       | 2 Tarantula Web |
| Mutant Tarantula  | 576,000     | 2,000  | 500   | T4       | 5 Tarantula Web |
| Primordial Jockey | 1,000,000   | ?      | 1,350 | T5       | 4 Tarantula Web |
| Primordial Viscount| 4,000,000  | 2,500  | 2,600 | T5       | 8 Tarantula Web |

### Loot Table

| Drop                    | T1  | T2   | T3    | T4    | T5 | Odds       | LVL Req |
|-------------------------|-----|------|-------|-------|----|------------|---------|
| Tarantula Web           | 1-3 | 9-18 | 28-48 | 52-64 | 64 | Guaranteed | 1       |
| Toxic Arrow Poison      | —   | 4-8  | 6-8   | 16-32 | 32-48 | ~15%  | 1       |
| Bite Rune I             | —   | 1    | 1     | 1     | 1  | 0.7–6.48%  | 1       |
| Spider Catalyst         | —   | —    | 1     | 1     | 1  | 0.18–2.06% | 2       |
| Tarantula Silk          | —   | —    | —     | —     | 1  | 20%        | 2       |
| Darkness Within Rune I  | —   | —    | —     | 1     | 1  | ~0.39–0.77%| 1       |
| Enchanted Book (BoA VI) | —   | —    | 1     | 1     | 1  | 0.21–0.42% | 4       |
| Tarantula Catalyst      | —   | —    | 1     | 1     | 1  | 0.25–0.43% | 4       |
| Fly Swatter             | —   | —    | 1     | 1     | 1  | 0.08–0.21% | 5       |
| Tarantula Talisman      | —   | —    | 1     | 1     | 1  | 0.08–0.21% | **6**   |
| Vial of Venom           | —   | —    | —     | 1     | 1  | 0.08–0.14% | 6       |
| Digested Mosquito       | —   | —    | —     | 1     | 1  | ~0.06%     | 7       |
| Shriveled Wasp          | —   | —    | —     | —     | 1  | 0.1%       | 7       |
| Ensnared Snail          | —   | —    | —     | —     | 1  | 0.06%      | 7       |
| Primordial Eye          | —   | —    | —     | —     | 1  | 0.02%      | 7       |
| Brick Red Dye           | yes | yes  | yes   | yes   | yes| ~0.0000001–0.000004% | — |

> **Correction**: Tarantula Talisman requires Spider Slayer 6 to drop (not lower as some old guides
> state). NEU repo incorrectly tags Tarantula Helmet/Chestplate as Spider Slayer 5 — in-game, ALL
> 4 Tarantula Armor pieces and Tarantula Fang unlock at Spider Slayer 4.

### Level Rewards

| LVL | XP Req    | Rank                   | Stat Bonus              | Items Unlocked                                                    |
|-----|-----------|------------------------|-------------------------|-------------------------------------------------------------------|
| 1   | 10        | Noob                   | +1 Crit Damage          | Spider Ring                                                       |
| 2   | 25        | Novice                 | +1 Crit Damage          | Recluse Fang, Medium Slayer Sack, Tarantula Silk                  |
| 3   | 200       | Skilled                | +1 Crit Damage          | Scorpion Bow                                                      |
| 4   | 1,000     | Destroyer              | +1 Crit Damage          | **Full Tarantula Armor set**, Tarantula Fang                      |
| 5   | 5,000     | Bulldozer              | +2 Crit Damage          | Tarantula Minion                                                  |
| 6   | 20,000    | Savage                 | +2 Crit Damage          | Scorpion Foil, Flycatcher, Spider Artifact                        |
| 7   | 100,000   | Pest Control Genius    | +2 Crit Damage; Survivor Cube | Mosquito Shortbow, full Primordial Armor, Mosquito Pet, Tarantula Ring |
| 8   | 400,000   | Tarantula Exterminator | +3 Crit Damage, +10 Aw | Bartender: Spider Egg Mixin; The Primordial, Sting                |
| 9   | 1,000,000 | Spider Annihilator     | +3 Crit Damage          | Bartender: Tarantula Minion XII Upgrade Stone                     |

### Recommended Gear by Tier

- **T1–T2**: Basic gear. Any sword. Spider Ring from LVL 1 helps.
- **T3**: Radiant Power Orb + Spider Hat, or Dragon Armor (Fierce). Life Steal/Vampirism essential.
  Use Tarantula Armor if you have kill count built up. Voodoo Doll effective here.
- **T4**: Tarantula Armor (10,000+ kills for defense bonus), or Superior/Shadow Assassin Armor for
  more damage. Clear bats with Giant's Sword. Bring a shortbow for Egg Sacs.
- **T5**: High EHP build required. Aware of Arachne's Keeper adds (Venom Shot + Noxious Paralysis
  stacks fast). Shortbow mandatory for Egg Sacs.

---

## 3. Sven Packmaster (Wolf Slayer)

**Unlock requirement**: Kill T2 Tarantula Broodfather.
**Location**: Hub Ruins, Howling Cave.
**Token drop**: Wolf Tooth (always guaranteed).
**Main crafting resources**: Wolf Tooth, Golden Tooth.

**Important**: Sven Packmaster is immune to ALL ability damage and ranged damage (bows, Voodoo Doll,
Flower of Truth abilities). Melee only.

### Tier Table

| Tier | HP        | DPS (melee) | True DPS | Slayer XP | Cost    | Combat XP Required |
|------|-----------|-------------|----------|-----------|---------|-------------------|
| T1   | 2,000     | 60/s        | —        | 5 XP      | 2,000   | 250               |
| T2   | 40,000    | 80/s        | 10/s     | 25 XP     | 7,500   | 650               |
| T3   | 750,000   | 180/s       | 50/s     | 100 XP    | 20,000  | 1,500             |
| T4   | 2,000,000 | 440/s       | 200/s    | 500 XP    | 50,000  | 3,000             |

Time limit: 4 minutes.

### Mechanics

**T1**: Agile — small and fast, harder to hit.

**T2**: +True Damage — deals True Damage that ignores defense.

**T3 & T4**: +Call the Pups! — at 50% HP, the boss slows to a crawl and stops regenerating HP.
It becomes invulnerable and spawns 1 Sven Pup per second for 5 seconds. Each Pup has 10% of the
boss's max HP. After all pups die, the boss returns to normal behavior.

**Tip**: The pup phase is a good time to heal. Fighting in water drowns the pups and helps control
the fight. Pond near the Ruins is recommended. Mastiff Armor synergizes with Wolf Pet for high HP.
Since T3/T4 deal True Damage, high HP is more valuable than Defense.

### Minibosses (spawn during T3+ quests)

| Miniboss      | HP        | Damage | XP  | Min Tier | Drop        |
|---------------|-----------|--------|-----|----------|-------------|
| Pack Enforcer | 45,000    | 360    | 100 | T3       | 1 Wolf Tooth |
| Sven Follower | 125,000   | 1,200  | 250 | T4       | 2 Wolf Tooth |
| Sven Alpha    | 480,000   | 2,200  | 500 | T4       | 5 Wolf Tooth |

### Loot Table

| Drop                     | T1  | T2   | T3    | T4    | Odds       | LVL Req |
|--------------------------|-----|------|-------|-------|------------|---------|
| Wolf Tooth               | 1-3 | 9-18 | 30-50 | 50-64 | Guaranteed | 1       |
| Hamster Wheel            | —   | 1    | 2-4   | 4-5   | ~16.5%     | 1       |
| Spirit Rune I            | —   | 1    | 1     | 1     | 0.68–6.37% | 2       |
| Enchanted Book (Crit VI) | —   | —    | 1     | 1     | 0.41–0.81% | 4       |
| Furball                  | —   | —    | 1     | 1     | 0.82–1.62% | 4       |
| Red Claw Egg             | —   | —    | 1     | 1     | 0.04–0.12% | 5       |
| Couture Rune I           | —   | —    | —     | 1     | 0.24%      | 6       |
| Grizzly Salmon           | —   | —    | —     | 1     | 0.06%      | 7       |
| Overflux Capacitor       | —   | —    | —     | 1     | 0.04%      | 7       |
| Celeste Dye              | yes | yes  | yes   | yes   | ~0.000007–0.0001% | — |

### Level Rewards

| LVL | XP Req    | Rank         | Stat Bonus                 | Items Unlocked                                                   |
|-----|-----------|--------------|----------------------------|------------------------------------------------------------------|
| 1   | 10        | Noob         | +1 Speed                   | Red Claw Talisman                                                |
| 2   | 30        | Novice       | +2 HP                      | Radiant Power Orb, Golden Tooth                                  |
| 3   | 250       | Skilled      | +1 Speed                   | **Maddox Batphone**, Shaman Sword                                |
| 4   | 1,500     | Destroyer    | +2 HP                      | Full Mastiff Armor set                                           |
| 5   | 5,000     | Bulldozer    | +1 Crit Damage             | Red Claw Ring, Edible Mace, Weird Tuba, Red Claw Artifact, Weirder Tuba |
| 6   | 20,000    | Savage       | +3 HP                      | Mana Flux Power Orb, Pooch Sword, full Pack Armor set            |
| 7   | 100,000   | King Hunter  | +2 Crit Damage             | Hunter Talisman, Overflux Power Orb, Large Slayer Sack           |
| 8   | 400,000   | Pack Leader  | +1 Speed; **Perk: Lose 5% less coins on death** | Hunter Ring, Plasmaflux Power Orb; Bartender: Wolf Fur Mixin |
| 9   | 1,000,000 | Alpha Wolf   | +5 HP                      | —                                                                |

### Recommended Gear by Tier

- **T1–T2**: Basic gear. Melee only — no bows, no abilities.
- **T3**: Mastiff Armor + Wolf Pet (Alpha Dog cuts damage by up to 30%). Radiant Power Orb + Zombie
  Sword for healing. Fight in water to drown pups. Wolf Pet's Pack Leader ability stacks with Mastiff's
  Absolute Unit for massive HP pool.
- **T4**: Same as T3 but upgraded. Superior Dragon Armor for high HP alternative. True Protection
  enchant helps. Sorrow Armor viable for True Defense. Growth enchant recommended.

---

## 4. Voidgloom Seraph (Enderman Slayer)

**Unlock requirement**: Kill T4 Sven Packmaster.
**Location**: The End (Endermen, Zealots, Zealot Bruisers, Voidling Fanatics/Extremists).
**Token drop**: Null Sphere (always guaranteed).
**Main crafting resources**: Null Sphere, Null Ovoid.

**Important**: Voidgloom Seraph is significantly harder than previous bosses. Only Juju Shortbow
and Terminator arrows can damage it (other bows apply 1 hit to Hitshield only, no actual damage).
Immune to arrows for HP damage — but any bow removes 1 hit from the Hitshield.
Immune to water damage. Aspect of the Dragons and Ice Spray Wand don't work.
When Hitshield is NOT active, Ferocity is divided by 4.

### Tier Table

| Tier | HP      | DPS     | Slayer XP | Cost   | Combat XP Required |
|------|---------|---------|-----------|--------|-------------------|
| T1   | 300,000 | 1,200/s | 5 XP      | 2,000  | 2,750             |
| T2   | 12M     | 5,000/s | 25 XP     | 7,500  | 6,600             |
| T3   | 50M     | 12,000/s| 100 XP    | 20,000 | 11,000            |
| T4   | 210M    | 21,000/s| 500 XP    | 50,000 | 22,000            |

Time limit: 4 minutes.

### Mechanics

All tiers include all abilities from tiers below.

**T1**:
- **Dissonance**: Teleports behind/beside the player (more frequent if player doesn't move). Deals
  half of DPS as AOE to all fighters within 6.5 blocks. (AOE is inactive in T1.)
- **Malevolent Hitshield**: Shield with 15 hits. Appears at spawn and at 2/3 and 1/3 HP. Boss does
  NOT gain DPS while shield is up. While shield is DOWN, incoming Ferocity is divided by 4. Any arrow
  removes 1 hit from the shield. Upon shield breaking, boss resumes attacking.

**T2**: +Yang Glyphs — appears at 50% HP (6M). Boss holds a beacon and throws it after 2 seconds.
Walk on/adjacent to it to destroy it. If not destroyed in 5 seconds, all fighters take 1000 × Max HP
as True Damage. Glyphs can't be thrown while Hitshield is up. Hitshield has 30 hits, gains +3,000 DPS
every 3s while up (removed when broken). Hitshield appears at spawn and 2/3 (8M) and 1/3 (4M) HP.

**T3**: +Nukekubi Fixations — heads spawn around the player at 1/3 HP (16.7M). Look at them directly
for 0.5 seconds to destroy. Each head increases Dissonance damage by 800/s, doubling for each
additional head. 5 heads = 64,000 DPS. Hitshield has 60 hits. Yang Glyphs start at 2/3 HP (33.3M)
and are thrown more often.

**T4**: +Broken Heart Radiation — at 5/6 (175M), 1/2 (105M), and 1/6 (35M) HP. Boss becomes
invulnerable for 8 seconds. Casts 12 rotating beams (4 groups of 3, 90° apart, 20 blocks long).
Beams rotate clockwise for 8 seconds. Touching a beam: 25% max HP as True Damage + -12% Vitality
for 90s (stacks). Leaving beam range during BHR: 10% max HP as True Damage twice per second.
Yang Glyphs and Nukekubi Fixations can still trigger during BHR. Nukekubi deals 2,000 base DPS per
head (doubled per head alive). Hitshield has 100 hits.

### Minibosses (spawn during T3+ quests)

| Miniboss           | HP         | Damage  | XP    | Min Tier | Drop          |
|--------------------|------------|---------|-------|----------|---------------|
| Voidling Devotee   | 8,400,000  | 5,000   | 800   | T3       | 1 Null Sphere |
| Voidling Radical   | 17,500,000 | 7,400   | 2,000 | T4       | 2 Null Sphere |
| Voidcrazed Maniac  | 52,000,000 | 25,000  | 5,000 | T4       | 5 Null Sphere |

### Loot Table

| Drop                          | T1  | T2    | T3    | T4      | Odds         | LVL Req |
|-------------------------------|-----|-------|-------|---------|--------------|---------|
| Null Sphere                   | 2-3 | 14-24 | 60-80 | 105-155 | Guaranteed   | 0       |
| Twilight Arrow Poison         | —   | 16    | 24-32 | 60-64   | ~13–15%      | 0       |
| Endersnake Rune I             | —   | —     | 1     | 1       | 2.42–5.34%   | 0       |
| Summoning Eye                 | —   | 1     | 1     | 1       | 0.56–0.67%   | 1       |
| Awakened Summoning Eye        | —   | 1     | 1     | 1       | ~0.12–0.20%  | 1       |
| Enchanted Book (Mana Steal I) | —   | —     | 1     | 1       | 2.23–4.47%   | 2       |
| Transmission Tuner            | —   | —     | 1     | 1       | 2.11–2.23%   | 3       |
| Null Atom                     | —   | —     | 1     | 1       | 3.73–5.94%   | 4       |
| Hazmat Enderman               | —   | —     | 1     | 1       | 1.04–1.55%   | 4       |
| Pocket Espresso Machine       | —   | —     | —     | 1       | 0.39%        | 4       |
| Enchanted Book (Smarty Pants I)| —  | —     | —     | 1       | 1.76%        | 5       |
| End Rune I                    | —   | —     | —     | 1       | 0.70%        | 5       |
| Handy Blood Chalice           | —   | —     | —     | 1       | 0.18%        | 5       |
| Sinful Dice                   | —   | —     | —     | 1       | 0.46%        | 6       |
| Exceedingly Rare Ender Artifact Upgrade | — | — | —  | 1       | 0.03%        | 6       |
| Etherwarp Merger              | —   | —     | —     | 1       | 0.42%        | 7       |
| Void Conqueror Enderman Skin  | —   | —     | —     | 1       | 0.18%        | 7       |
| Judgement Core                | —   | —     | —     | 1       | 0.06%        | 7       |
| Enchant Rune I                | —   | —     | —     | 1       | 0.05%        | 7       |
| Enchanted Book (Ender Slayer VII) | — | —  | —     | 1       | 0.01%        | 7       |
| Byzantium Dye                 | yes | yes   | yes   | yes     | ~0.000007–0.0001% | — |

### Level Rewards

| LVL | XP Req    | Rank                | Stat Bonus            | Items Unlocked                                                      |
|-----|-----------|---------------------|-----------------------|---------------------------------------------------------------------|
| 1   | 10        | Noob                | +1 HP                 | Voidwalker Katana                                                   |
| 2   | 30        | Novice              | +2 Intelligence       | Null Ovoid, Soulflow Pile, Lesser Soulflow Engine                   |
| 3   | 250       | Skilled             | +2 HP                 | Soul Esoward, Voidedge Katana                                       |
| 4   | 1,500     | Destroyer           | +2 Intelligence       | Full Final Destination Armor, Voidling Minion I, Travel Scroll to Void Sepulture |
| 5   | 5,000     | Bulldozer           | +3 HP                 | Soulflow Battery, Soulflow Engine, Vorpal Katana, Gloomlock Grimoire, **Juju Shortbow** |
| 6   | 20,000    | Savage              | +5 Intelligence       | Gyrokinetic Wand, Aspect of the Void, Atomsplit Katana, Sinseeker Scythe |
| 7   | 100,000   | Voidwracker         | +4 HP                 | Soulflow Supercell, **Etherwarp Conduit**, Ender Relic, **Terminator** |
| 8   | 400,000   | Tall Purple Hater   | +4 Int; **Perk: +15% RNGesus enchants in Superpairs** | Bartender: End Portal Fumes |
| 9   | 1,000,000 | Definition of End   | +5 HP, +5 Tracking    | **Perk: Increases spawn chances of Elusive sea creatures** (all Mythic except Plhlegblast) |

### Recommended Gear by Tier

- **T1**: High-damage melee + a bow for quickly breaking Hitshields. Any bow removes 1 hit per arrow.
  Juju Shortbow not needed yet (it's locked until Enderman Slayer 5 anyway).
- **T2**: Strong melee + bow for Hitshields. Stand on Yang Glyphs to destroy them. High HP/True Defense
  recommended. Learn to watch for glyph throws.
- **T3**: Requires Juju Shortbow or Terminator for Hitshield-down phases. Very high DPS needed.
  Multiple players recommended for nukekubi management. High True Defense for Dissonance.
- **T4**: Top-tier gear required. Terminator preferred. True Defense mandatory to survive Broken Heart
  Radiation. Mithril Coat or Wither Cloak Sword ability can block Yang Glyph instakill.
  Vitality stacking from BHR is a major threat — kill it fast.

---

## 5. Inferno Demonlord (Blaze Slayer)

**Unlock requirement**: Kill T3 Voidgloom Seraph.
**Location**: Crimson Isle — Stronghold (Blaze, Mutated Blaze, Bezal), Smoldering Tomb (Smoldering
Blaze, Millennia-Aged Blaze), Ruins of Ashfang (Ashfang).
**Token drop**: Derelict Ashe (always guaranteed).
**Main crafting resources**: Derelict Ashe, Molten Powder.

**Important**: Blaze Slayer uses entirely different mechanics. The boss does True Damage that scales
with the player's own HP — not with the boss's DPS. Higher HP pools are punished more.
T2+ has Hellion Shield requiring attuned Blaze Slayer Daggers to deal damage.

> **Bal (Blaze boss) note**: Bal is hit-based for shield mechanics, NOT damage-based. Any bow with
> fast hit rate works as well as expensive bows for clearing Fire Pillars. A shortbow is equivalent.
> Expensive bows offer no advantage for the pillar mechanic specifically.

### Tier Table

| Tier | HP    | True Damage (% of player max HP) | Slayer XP | Cost    | Combat XP Required |
|------|-------|----------------------------------|-----------|---------|-------------------|
| T1   | 2.5M  | 100 + 5%/8%/12% at 100/66/33%   | 5 XP      | 10,000  | 6,000             |
| T2   | 10M   | 100 + 5%/10%/15% at 100/66/33%  | 25 XP     | 25,000  | 14,400            |
| T3   | 45M   | 100 + 5%/10%/15% at 100/66/33%  | 100 XP    | 60,000  | 18,000            |
| T4   | 150M  | 100 + 15%/25%/35% at 100/66/33% | 500 XP    | 150,000 | 36,000            |

Note: Blaze Slayer start costs are higher (T1: 10k, T2: 25k, T3: 60k, T4: 150k).

### Mechanics

**Immolate** (all tiers): The Inferno Demonlord deals True Damage to anyone within aggro range.
Damage is 100 + a % of the player's max HP per second. The % increases as the boss's HP decreases
(phase thresholds). At T4, the percentages are dramatically higher.

**Demonsplit** (all tiers): At 50% HP (T1: 1.25M, T2: 5M), boss splits into two demons:
- **Quazii** (Wither Skeleton appearance): Attacked first. Typhoeus is immune while Quazii is alive.
- **Typhoeus** (Pigman appearance): Immune while Quazii is alive. Has AOE with Scorched Anger.
  When Quazii dies, Typhoeus becomes attackable. When both are killed, Demonlord reforms.
- T3: Demonsplit occurs at 2/3 and 1/3 HP.
- T4: Same as T3 (2/3 at 100M, 1/3 at 50M).

**Hellion Shield** (T2+): Boss and demons have 99% damage reduction. Only hits from attuned
Blaze Slayer Daggers, their enchantment damage, and suffocation damage bypass the shield.
Shield attunement cycles: Ashen → Spirit → Auric → Crystal → (repeat), every 8 correct hits.
Daggers: Twilight, Firedust, Kindlebane, Mawdredge, Pyrochaos, Deathripper.
Demons alternate between 2 attunements:
- Quazii: Spirit ↔ Crystal
- Typhoeus: Ashen ↔ Auric
Ferocity is excluded — Ferocity upgrades don't help.

**Fire Pillars** (T2+ at 50% HP; T3/T4 at 2/3 HP): Every 20 seconds, boss forms a fireball above
head for 3.5 seconds then throws it. A 4-block high orange pillar spawns. Must be destroyed within
7 seconds by clicking it 8 times while having any **Wisp Pet** active. No invincibility frames.
If not destroyed: 1000 × Max HP as True Damage to all fighters. Mithril Coat or Wither Cloak Sword
ability can block this.

**DDR Apocalypse** (T3/T4 at 1/3 HP): Spawns up to 5 fire pits near the player regularly.
Orange terracotta cross-shapes → fire after 1.5 seconds. Standing in fire: 200% max HP as True
Damage per second (instant kill with ≤100 True Defense).

**Quazii ROFLcopter** (T3/T4): Spinning beam around Quazii. Touching it: 70% max HP as True Damage
+ Quazii heals 20% of its HP (1M at T3, 2M at T4).

**Typhoeus Trail of Fire** (T4): Leaves fire trail. Touching fire: 60% max HP as True Damage.

**Demon HP by Tier**:
| Tier | Quazii HP | Typhoeus HP | Each Demon DPS |
|------|-----------|-------------|----------------|
| T1   | 500,000   | 500,000     | 2,500          |
| T2   | 1,750,000 | 1,750,000   | 8,000          |
| T3   | 5,000,000 | 5,000,000   | 15,000         |
| T4   | 10,000,000| 10,000,000  | 30,000         |

### Minibosses (spawn during T3+ quests)

| Miniboss          | HP         | XP    | Min Tier | Drop           |
|-------------------|------------|-------|----------|----------------|
| Flare Demon       | 9,000,000  | 1,200 | T3       | 1 Derelict Ashe |
| Kindleheart Demon | 17,500,000 | 2,400 | T4       | 2 Derelict Ashe |
| Burningsoul Demon | 50,000,000 | 8,000 | T4       | 5 Derelict Ashe |

(Miniboss HP was reduced in Dec 2024: 12M→9M, 25M→17.5M, 75M→50M)

### Loot Table

| Drop                     | T1  | T2   | T3    | T4     | Odds       | LVL Req |
|--------------------------|-----|------|-------|--------|------------|---------|
| Derelict Ashe            | 6-8 |12-22 | 60-80 |110-155 | Guaranteed | 0       |
| Enchanted Blaze Powder   | 1   | 2-3  | 4-8   | 16-40  | ~11–21%    | 0       |
| Bundle of Magma Arrows   | —   | 1    | 1     | 1      | ~7.62–8.47%| 1       |
| Wisp's Ice-Flavored Water| —   | 1    | 2     | 5      | ~2.54–2.82%| 1       |
| Lavatears Rune I         | —   | —    | 1     | 1      | ~1.01–1.07%| 1       |
| Mana Disintegrator       | —   | 1    | 1     | 1      | ~3.56–3.95%| 2       |
| Scorched Books           | —   | 1    | 1     | 1      | ~2.03–2.26%| 2       |
| Kelvin Inverter          | —   | 1    | 1     | 1      | ~2.54–2.82%| 3       |
| Blaze Rod Distillate     | —   | 2    | 6-10  | 16-24  | ~4.57–5.08%| 3       |
| Glowstone Distillate     | —   | 2    | 6-10  | 16-24  | ~4.57–5.08%| 3       |
| Magma Cream Distillate   | —   | 2    | 6-10  | 16-24  | ~4.57–5.08%| 3       |
| Nether Wart Distillate   | —   | 2    | 6-10  | 16-24  | ~4.57–5.08%| 3       |
| Gabagool Distillate      | —   | 2    | 6-10  | 16-24  | ~2.54–2.82%| 3       |
| Scorched Power Crystal   | —   | —    | 1     | 1      | ~3.05–3.24%| 4       |
| Archfiend Dice           | —   | —    | 1     | 1      | ~1.02–1.08%| 4       |
| Enchanted Book (Fire Aspect III) | — | — | —  | 1      | 1.27%      | 5       |
| Flawed Opal Gemstone     | —   | —    | —     | 240-400| 2.79%      | 5       |
| Fiery Burst Rune I       | —   | —    | —     | 1      | 0.20%      | 5       |
| Enchanted Book (Duplex I)| —   | —    | —     | 1      | 1.79%      | 6       |
| High Class Archfiend Dice| —   | —    | —     | 1      | 0.25%      | 7       |
| Wilson's Engineering Plans| —  | —    | —     | 1      | 0.09%      | 7       |
| Subzero Inverter         | —   | —    | —     | 1      | 0.09%      | 7       |
| Flame Dye                | yes | yes  | yes   | yes    | ~0.000007–0.0001% | — |

### Level Rewards

| LVL | XP Req    | Rank          | Stat Bonus                     | Items Unlocked                                                |
|-----|-----------|---------------|--------------------------------|---------------------------------------------------------------|
| 1   | 10        | Noob          | +3 HP                          | Droplet Wisp Pet                                              |
| 2   | 30        | Novice        | +1 Strength                    | Molten Powder, Firedust Dagger, Twilight Dagger               |
| 3   | 250       | Skilled       | +4 HP                          | Wisp Upgrade Stone (Rare), Burststopper Talisman, Warning Flare, Inferno Minion I |
| 4   | 1,500     | Destroyer     | +1 True Defense                | Kindlebane Dagger, Mawdredge Dagger, Demonslayer Gauntlet, Teleporter Pill, Travel Scroll to Smoldering Tomb |
| 5   | 5,000     | Bulldozer     | +5 HP                          | Wisp Upgrade Stone (Epic), Destruction Cloak, Tactical Insertion |
| 6   | 20,000    | Savage        | +2 Strength                    | Pyrochaos Dagger, Deathripper Dagger, Blazetekk Ham Radio, Alert Flare |
| 7   | 100,000   | Hellsplitter  | +6 HP                          | Burststopper Artifact, Wisp Upgrade Stone (Legendary), Annihilation Cloak, SOS Flare |
| 8   | 400,000   | Demon Eater   | +2 True Defense; **Perk: +20% Pet XP when feeding Wisps with Gabagool** | Bartender: Gabagoey Mixin |
| 9   | 1,000,000 | Gabagool King | +7 HP; **Perk: 10 Bits discount on Inferno Fuel Blocks** | — |

Note: Blaze Slayer is the only slayer that doesn't unlock an exclusive armor set, but it's also
the only slayer that unlocks equipment (Demonslayer Gauntlet).

### Recommended Gear by Tier

- **T1**: Low HP build helps (less Immolate damage since % scales with max HP). A Wisp Pet is mandatory
  for Fire Pillars from T2+. Attuned dagger not needed at T1 (no Hellion Shield yet).
- **T2**: Require attuned daggers. Firedust and Twilight unlocked at LVL 2. Watch the shield attunement
  color and switch targeting accordingly. Wisp Pet required for Fire Pillars.
- **T3**: Need faster dagger rotation. Kindlebane/Mawdredge (LVL 4) or Pyrochaos/Deathripper (LVL 6)
  strongly recommended. DDR Apocalypse fire is instant death — dodge the orange tiles. ROFLcopter beam
  is dangerous. High DPS to prevent pillars from stacking.
- **T4**: Top Blaze daggers required. True Defense matters for survival. Extreme mechanical skill needed.
  Trail of Fire from Typhoeus adds constant hazard. Build True Defense, not raw HP (avoids more Immolate).

---

## Key Corrections Summary

1. **Spider Slayer rework July 2025**: T5 added, T1 HP increased (750→1000), T2/T3 DPS buffed,
   Combat XP requirements raised. T3 is now significantly harder. Old guides wrong.
2. **Tarantula Talisman**: Requires Spider Slayer 6 to unlock as a drop (not a lower level).
3. **Tarantula Armor/Fang**: All 4 armor pieces + Tarantula Fang unlock at Spider Slayer 4 (NEU repo
   incorrectly shows 5 for helmet/chestplate).
4. **Auto-Slayer**: Per-type, not global. Enabling it for Zombie Slayer doesn't affect Spider, etc.
5. **Blaze Demonlord hit-based shield**: Fire Pillars are destroyed by hits, not damage. Any shortbow
   clicking 8 times works identically to expensive bows for this mechanic.
6. **Sven Packmaster**: Fully immune to ability damage AND ranged damage (bows). Melee only.
7. **Voidgloom Seraph**: Regular bows can only remove 1 hit per arrow from the Hitshield — they
   cannot damage the boss's actual HP. Juju Shortbow and Terminator are the only bows that deal HP
   damage (once shield is down, Ferocity is divided by 4 until shield returns).
