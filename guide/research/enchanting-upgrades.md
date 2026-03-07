# Enchanting, Reforges, Potions & Item Upgrades — Research Notes

> Sources: `data/neu-repo/constants/enchants.json`, `reforges.json`, `reforgestones.json`,
> `essencecosts.json`, and local wiki dump (`data/wiki/`). Last verified 2026-03-04.

---

## 1. Enchanting System

### How the Enchanting Table Works

The Enchantment Table lets players choose specific enchantments at specific levels, each with a
fixed XP cost. Unlike vanilla Minecraft, you can see and select enchants individually.

- Placing an item opens a list of all valid enchantments for that item type.
- Each enchantment and level has a stated XP cost — click to apply.
- Conflicting enchants (e.g. Syphon + Life Steal) auto-remove the old one when the new is applied.
- Enchants can also be removed via the table (same XP cost to remove; also grants Enchanting XP).
- Books **cannot** be enchanted directly via the table — books come from other sources only.
- Combining Enchanted Books costs **no XP** in an Anvil.
- Enchanting gives Enchanting Skill XP. Cap: 500,000 XP/day from table/anvil. No cap bypass except
  the Experimentation Table.

### Bookshelf Power

- **20 Bookshelf Power** is required for full enchant access.
- Regular Bookshelf: +1 power each (15+ needed for max = 15 shelves).
- **Enchanted Bookshelf**: +15 power each. **Only 2 are needed** for full access (2 × 15 = 30 > 20).
- Enchanted Bookshelves are NOT sold on the Bazaar. Craft them (Sugar Cane 6 collection required).
- Recipe: 6 Enchanted Oak Log + 6 Enchanted Paper.

### Enchanting XP Daily Limit & Workaround

- Manual enchanting (table + anvil): **500,000 XP/day hard cap**.
- **Experimentation Table** bypasses this cap — use it daily for efficient leveling.

### Enchanting Skill Level Gates

Key levels that unlock important enchantments or features:

| Level | What Unlocks |
|-------|-------------|
| 2 | Infinite Quiver, Harvesting, Sunder |
| 5 | Life Steal, Growth |
| 7 | Replenish (see note), Sugar Rush |
| 10 | Experimentation Table, First Strike, Pesterminator, Rejuvenate |
| 12 | Dedication, Impaling |
| 14 | Lethality, Execute, Thunderlord, Frail |
| 15 | Syphon, Caster, Flowstate, True Protection, Vampirism |
| 16 | Dragon Hunter, Bank |
| 20 | Thunderbolt, Mana Steal, Ultimate Wise |
| 22 | Mana Vampire, Hardened/Strong/Ferocious Mana, Counter-Strike, Lapidary |
| 25 | Corruption, Charm, The One, Prosecute |
| 28 | Habanero Tactics, Titan Killer, Duplex |
| 30 | Ice Cold, Flash, Last Stand |
| 33 | Overload |
| 38 | One For All (highest table unlock; NOT recommended — see corrections) |

> **Replenish note:** Cannot be obtained from the Enchanting Table (patched). Get it from Cocoa
> Beans Collection 8, the Bazaar, or a Librarian visitor.

---

## 2. Enchantment Types and Sources

### Level VI / "Top-Level" Enchants (Not from Table)

Many enchantments have a max level obtainable from the table (often V), but a higher "cap" level
(often VI or VII) exists and **cannot** be made by combining two V books. Sources:

- **Experimentation Table** (most common source of L5 exclusives)
- **Dark Auction** (rare)
- **Tomioka** NPC

**Critical correction:** Level 5 of enchantments like Looting V, Syphon V, Life Steal IV, etc.
are Experimentation Table exclusives. You **cannot** combine two Looting IV books to get Looting V.
These must come from Experiment rewards.

| Enchant | Table Max | True Max | Source for Max |
|---------|-----------|----------|----------------|
| Sharpness | V | VII | Experimentation Table |
| Smite | V | VII | Experimentation Table |
| Bane of Arthropods | V | VII | Experimentation Table |
| Looting | III | V | Experimentation Table |
| Life Steal | III | IV | Experimentation Table |
| Syphon | III | V | Experimentation Table |
| Giant Killer | V | VII | Experimentation Table |
| Critical | V | VII | Experimentation Table |
| First Strike | IV | V | Experimentation Table |
| Triple Strike | IV | V | Experimentation Table |
| Ender Slayer | V | VII | Experimentation Table |
| Thunderlord | V | VII | Experimentation Table |
| Growth | V | VII | Experimentation Table |
| Protection | V | VII | Experimentation Table |
| Feather Falling | V | X | Experimentation Table |
| Infinite Quiver | V | X | Experimentation Table |
| Mana Vampire / Hardened Mana / etc. | max via table | X | Experimentation Table |

### Enchantment Conflict Pools

Items can only have one enchantment from each conflict pool:

| Pool | Enchants |
|------|----------|
| Touch | Silk Touch, Smelting Touch, Fortune |
| Ultimate | All Ultimate_ enchants (only 1 per item) |
| Protection | Protection, Blast Protection, Fire Protection, Projectile Protection |
| Regen | Rejuvenate, Respite |
| Lightning | Thunderlord, Thunderbolt |
| Sustain | Syphon, Life Steal, Mana Steal |
| Execute | Execute, Prosecute |
| Walking | Depth Strider, Frost Walker |
| Strike | First Strike, Triple Strike |
| Killer | Giant Killer, Titan Killer |

---

## 3. Ultimate Enchantments

Only **one** Ultimate enchantment per item. Applied via Anvil from a book.

> **Important:** Ultimate enchants require the listed Enchanting skill level to equip/use, **even
> if applied to the item via Anvil from a pre-made book**. Check level requirements before
> purchasing.

### Sword Ultimates

| Enchant | Max | Notes |
|---------|-----|-------|
| Ultimate One For All | I | NPC-sold item per Rogue's Guide. **Not recommended** — conflicts with almost all other sword enchants. |
| Ultimate Soul Eater | V | Stacks Strength when enemies die nearby |
| Ultimate Chimera | V | Improves effect of all other enchants |
| Ultimate Combo | V | Stacks up to 10 combo points for bonus damage |
| Ultimate Swarm | V | +5% dmg per nearby enemy, stacks |
| Ultimate Wise | V | Mana restore on ability use |
| Ultimate Inferno | V | Fire damage over time |
| Ultimate Fatal Tempo | V | Attack speed ramp-up |

### Armor Ultimates

| Enchant | Max | Notes |
|---------|-----|-------|
| Ultimate Bank | V | Increases coin gain |
| Ultimate Last Stand | V | Bonus defense at low HP |
| Ultimate Legion | V | +stats per nearby player |
| Ultimate No Pain No Gain | V | Converts damage taken to mana |
| Ultimate Wisdom | V | XP boost |
| Ultimate Habanero Tactics | V | Requires Enchanting 28 |
| Ultimate Bobbin' Time | V | Fishing-related, unlocks at Enchanting 24 |
| Ultimate Refrigerate | V | Cold/ice themed stats |

### Bow Ultimates

| Enchant | Notes |
|---------|-------|
| Ultimate Soul Eater | Applies to bows too |
| Ultimate Rend | Bow-specific |
| Ultimate Reiterate | Double-shot |
| Ultimate Duplex | Duplicate arrows |

---

## 4. Experimentation Table

**Unlock:** Enchanting level 10. Craft with 8 Oak Log + 1 Experience Bottle (recipe requires
Enchanting 10 to unlock).

- Placed on Private Island; max 1 table.
- Contains daily mini-games (memory, etc.) that reward:
  - Enchanting XP (bypasses daily cap from manual enchanting)
  - Level 3–7 Enchanted Books (including exclusive max-level books)
  - Experience Bottles
- Resets daily at **12:00 AM GMT / 7:00 PM EST**.
- Has its own daily limit (exact cap unknown, but separate from table cap).
- **Priority tip:** Use the Experimentation Table every day as your first Enchanting action. It is
  the most efficient source of high-level enchant books and XP.
- Piscary was removed from the Experimentation Table as of patch 0.19.3.

---

## 5. Reforges

Reforges are stat bonuses applied to items. Most are random-rolled from the Reforge Anvil or
Blacksmith NPC. Some require specific Reforge Stones.

### How to Reforge

- **Regular reforging:** Use any Blacksmith (Hub, Catacombs Entrance, Dungeon Hub) or a Reforge
  Anvil (crafted at Obsidian 10, or bought from Smithmonger for 2M coins).
- **Stone reforging:** Place the Reforge Stone + item in the Reforge Anvil. Requires the stone and
  a coin fee. Some stones require Mining skill levels.
- Reforges are overwritten each time — you cannot stack them.

### Standard Sword Reforges (SWORD/ROD type, Legendary rarity)

| Reforge | Str | CD | CC | Atk Spd | Notes |
|---------|-----|----|----|---------|-------|
| Spicy | +10 | +80 | +1 | +10 | Highest CD |
| Sharp | — | +75 | +20 | — | CD + CC |
| Legendary | +25 | +28 | +15 | +10 | Balanced |
| Epic | +40 | +35 | — | +10 | Str + CD |
| Odd | -50 Int | +30 | +25 | — | No Str |
| Fair | +10 | +10 | +10 | +10 | All-round |
| Heroic | +40 | — | — | +5 | +100 Int |
| Fast | — | — | — | +50 | Atk speed only |
| Gentle | +15 | — | — | +25 | Str + Spd |

> **Best for DPS:** Spicy (max CD), Sharp (CC + CD), Legendary (balanced).

### Standard Armor Reforges (ARMOR type, Legendary rarity)

| Reforge | HP | DEF | STR | Int | CD | CC | SPD | Notes |
|---------|----|----|-----|-----|----|----|-----|-------|
| Titanic | +35 | +35 | — | — | — | — | — | Tank |
| Heavy | — | +80 | — | — | -5 | — | -1 | Pure defense |
| Wise | +15 | — | — | +125 | — | — | +2 | Mage |
| Smart | +15 | +15 | — | +100 | — | — | — | Int |
| Mythic | +10 | +10 | +10 | +50 | — | +5 | +2 | Mage hybrid |
| Pure | +8 | +8 | +8 | +8 | +8 | +10 | +1 | Balanced |
| Clean | +20 | +20 | — | — | — | +10 | — | Crit |
| Fierce | — | — | +10 | — | +18 | +6 | — | DPS |
| Light | +20 | +5 | — | — | +5 | +3 | +5 | Mobile |

### Standard Bow Reforges (BOW type, Legendary rarity)

Key options: **Deadly** (+50 CD, +22 CC), **Unreal** (CC + CD), **Rapid** (Atk Speed focus).

### Reforge Stones (Special Reforges)

Reforge Stones unlock reforges not available via random rolling. Applied at a Reforge Anvil or
Malik/Blacksmith with Advanced Reforging.

**Sword Reforge Stones:**

| Stone | Reforge | Source | Cost to Apply | Mining Req |
|-------|---------|--------|--------------|------------|
| Dragon Claw | Fabled | Ender Dragon drops | 60k / 2M | XXII |
| Suspicious Vial | Suspicious | Catacombs F3 Boss Chest | 60k / 2M | XXIII |
| Midas Jewel | Gilded | King Midas drop | 5M / 10M | XXV |
| Wither Blood | Withered | Catacombs F7 / Necron I unlock | 10k / 60k | XXX |
| Warped Stone | Warped | Catacombs F5 chest | 5M | XXVI |
| Dirt Bottle | Dirty | Smithmonger (100k) | 1k / 75k | X |
| Entropy Suppressor | Coldfused | Crafted | varies | — |

**Armor Reforge Stones (selection):**

| Stone | Reforge | Source |
|-------|---------|--------|
| Necromancer's Brooch | Necrotic | Dungeon Loot Chests |
| Dragon Scale | Spiked | Ender Dragon drops |
| Rare Diamond | Reinforced | Diamond Ore/Blocks in Deep Caverns |
| Molten Cube | Cubic | Magma Cube Boss |
| Premium Flesh | Undead | Zombie drops in Dungeons (1/500–1/1000) |
| Candy Corn | Candied | Spooky Festival chests |

---

## 6. Potions & Brewing

### Brewing Basics

1. Start with an **Awkward Potion** (Nether Wart + Water Bottle in Brewing Stand).
2. Add the primary ingredient to create the base potion.
3. Optional modifiers can be added to change tier or duration.

**Brewing Stand** costs 30 coins from the Alchemist NPC, or is craftable (3 Cobblestone + 1 Blaze Rod).

### Duration Modifiers

| Ingredient | Effect |
|-----------|--------|
| Redstone | +8:00 duration |
| Enchanted Redstone | +16:00 duration |
| Enchanted Redstone Block | +16:00 duration |
| Enchanted Redstone Lamp | +16:00 + 3 levels |
| Glowstone Dust | +1 level |
| Enchanted Glowstone Dust | +2 levels |
| Enchanted Glowstone | +3 levels |
| Gunpowder | Duration ÷ 2, makes Splash |
| Enchanted Gunpowder | Makes Splash (no duration penalty) |
| Potion Affinity Talisman | +10% duration |
| Potion Affinity Ring | +25% duration |
| Potion Affinity Artifact | +50% duration |
| Parrot Pet | +40% duration |
| Alchemy skill | +% duration (1% per level via Brewer perk) |

### Key Potions

**Critical Potion** (Max: IV)
- Source: Flint + Awkward Potion. Requires Gravel 7 collection.
- Effect: +10% Crit Chance / +10% Crit Damage (I) → +25% CC / +40% CD (IV)
- Level up via Glowstone modifiers.

**Strength Potion** (Max: VIII)
- Source: Blaze Powder (I→II), Enchanted Blaze Powder (→IV), Enchanted Blaze Rod (→VII+).
- Effect: +5 Strength (I) → +75 Strength (VIII)
- KnockOff™ Cola brew modifier adds +5% Strength bonus.

**Speed Potion** (Max: VIII)
- Source: Sugar (I), Enchanted Sugar (III), Enchanted Sugar Cane (V+).
- Effect: +5 Speed (I) → +40 Speed (VIII)
- Coffee brews (Cheap/Decent/Black) add bonus Speed.

**Haste Potion** (Max: IV)
- Effect: +50 Mining Speed (I) → +200 Mining Speed (IV)
- Coal + Awkward Potion.

**Dungeon Potion** — specialized for Catacombs.

**Alchemy XP Boost, Combat XP Boost, etc.** — profession XP boosters.

### God Potion

- **Cost:** 1,500 Bits from Elizabeth (Community Center Bits Shop).
- **Duration:** 12 hours base + 0.24 hours per Alchemy level = up to **24 hours** at Alchemy 50.
- Does NOT count down while offline, in a dungeon, or on a Private Island.
- Stacks (extending timer) up to 192 hours (8 days) max.
- Using any regular potion while God Potion is active **does not extend or enhance** any overlapping
  effect.
- Can be upgraded with **Mixins** (unlocked at Slayer Level 8 per slayer type):
  - Zombie Brain, Spider Egg, Wolf Fur, End Portal Fumes, Gabagoey, Deepterror, Glowing Mush.

**God Potion effects include:**
Critical IV, Regeneration IX, Strength VIII, Agility IV, Night Vision I, Absorption VIII,
Burning IV, Stun IV, Dodge IV, Experience IV, Mana VIII, Speed VIII, Water Breathing VI,
all 7 Skill XP Boost III potions (Alchemy/Combat/Enchanting/Farming/Fishing/Foraging/Mining),
Rabbit VI, Resistance VIII, Archery IV, Jump Boost IV, Magic Find IV, Pet Luck IV, Spirit IV,
Spelunker V, Adrenaline VIII, Fire Resistance I, Haste IV, True Resistance IV, Jerry Candy
(+100 HP, +20 Str, +2 Ferocity, +100 Int, +3 MF).

> **Tip for new players:** Get the God Potion early. Claim the free Booster Cookie, earn 1,500
> Bits, and buy it from Elizabeth. It replaces nearly every buff potion for 12–24 hours.

### Alchemy Leveling

- Best early method: Enchanted Sugar (Strength/Speed potion line) — good XP:cost ratio.
- Best speed method: Enchanted Sugar Cane (Speed potion, fast brew cycle) — ~4× more expensive
  per XP but can hit Alchemy 50 much faster with autobrewers.
- Brewer perk: +1% potion duration per Alchemy level (up to +50% at level 50).
- God Potion benefits doubly from Brewer (100% bonus instead of 50%).

---

## 7. Item Upgrades

### Star Upgrades (Essence System)

Stars are applied to **Dungeon Items** using Essence at Malik (Catacombs Entrance or Dungeon Hub).

**Stat boost per star:**
- Inside dungeons: **+10% per star** (5 stars = +50% all stats)
- Outside dungeons: **+2% per star** (5 stars = +10% all stats)

**Caps:**
- Standard Dungeon Items: maximum **5 stars**.
- Crimson Essence items (Kuudra gear): maximum **15 stars**.

**Essence types and sources:**

| Essence | Primary Source |
|---------|---------------|
| Wither | Dungeon Reward Chests, Dungeon Secrets, Hub Races |
| Undead | Dungeon Reward Chests, Crypt Undeads |
| Dragon | Ender Dragon kills, Lost Adventurers |
| Spider | Arachne, Lonely/Cellar Spiders |
| Gold | Golden Goblins, King Midas, Crystal Hollows chests |
| Diamond | Angry Archaeologist, Diamond Goblins, Crystal Hollows |
| Crimson | Kuudra runs |
| Ice | Winter Sea Creatures, Frozen Adventurers |
| Forest | Tree Gifts, Fig/Mangrove trees, Agatha rewards |

> **Buying Essence from Bazaar** requires Catacombs 20 (except Forest Essence, no requirement).

**Sample essence costs (Wither items, to 5 stars):**

| Item | Star 1 | 2 | 3 | 4 | 5 | Total |
|------|--------|---|---|---|---|-------|
| Soul Whip | 200 | 300 | 400 | 550 | 750 | + 300 initial = 2500 |
| Adaptive Helmet | 10 | 25 | 50 | 100 | 150 | 335 |
| Adaptive Chestplate | 20 | 50 | 100 | 200 | 300 | 670 |

### Hot Potato Books

- **Effect per book:** Armor: +4 HP, +2 Defense. Weapons/Axes: +2 Damage, +2 Strength.
- **Max:** 10 Hot Potato Books per item.
- **Maxed armor (10 HPBs):** +40 HP, +20 Defense.
- **Maxed weapon (10 HPBs):** +20 Damage, +20 Strength.
- Sources: Potato Collection VIII (craft), Dungeon Reward Chests, Shiny Pig (0.59% drop).
- Craft recipe (Potato 8 unlock): 1 Enchanted Baked Potato + 3 Paper.
- Free to apply (no XP cost at anvil).
- Blaze Pet (Legendary) passive doubles Hot Potato Book stat bonuses.

### Fuming Potato Books

- **Effect per book:** Same as HPB (+4 HP / +2 Def, or +2 Dmg / +2 Str per book).
- **Max:** 5 Fuming Potato Books, but **only after all 10 HPBs are applied first**.
- **Combined max (10 HPB + 5 FPB):** Armor: +60 HP, +30 Def. Weapons: +30 Dmg, +30 Str.
- Sources: Dungeon Reward Chests only (no craft recipe).
- Blaze Pet (Legendary) passive doubles Fuming Potato Book stat bonuses.
- **Note:** As of 2026-01-27, FPBs now require 10 HPBs applied before they can be used.

### Gemstone Slots

Items can have Gemstone Slots that accept specific Gemstone types.

**Slot types and their gemstones:**

| Slot | Valid Gem | Stat |
|------|----------|------|
| Ruby | Ruby | Health |
| Amethyst | Amethyst | Defense |
| Jade | Jade | Mining Fortune |
| Sapphire | Sapphire | Intelligence |
| Amber | Amber | Mining Speed |
| Topaz | Topaz | Pristine |
| Jasper | Jasper | Strength |
| Opal | Opal | True Defense |
| Onyx | Onyx | Crit Damage |
| Aquamarine | Aquamarine | Fishing Speed |
| Citrine | Citrine | Foraging Fortune |
| Peridot | Peridot | Farming Fortune |

**Special slot types:**
- **Combat slot:** Ruby, Amethyst, Sapphire, Jasper, Onyx, or Opal.
- **Defensive slot:** Ruby, Amethyst, or Opal.
- **Mining slot:** Jade, Amber, or Topaz.
- **Universal slot:** Any gemstone.

Gemstone tiers (Rough → Flawed → Fine → Flawless → Perfect) provide increasing stat bonuses.

Some items have locked slots that must be unlocked via Gemstone Chambers (e.g. Armor of Divan).
Gemstone Chambers require Heart of the Mountain 5 to forge (4-hour forge time).

---

## 8. Key Corrections to Apply in the Guide

These are verified corrections that contradict common misconceptions:

1. **Level 5 enchants are Experimentation Table exclusives.** You cannot combine two L4 books to
   get Looting V, Syphon V, etc. They must be obtained from Experimentation Table rewards.

2. **Ultimate enchants check Enchanting level even if applied via Anvil.** You still need the
   unlock level to use the item. Don't buy expensive ultimate books without verifying your level.

3. **Bookshelf Power required is 20, not 15.** Regular bookshelves give +1 each; Enchanted Bookshelves
   give +15. Only **2 Enchanted Bookshelves** are needed. Neither is sold on Bazaar.

4. **One For All is an NPC item** (Rogue's Guide source). It conflicts with nearly every other
   sword enchantment. Do not recommend it to general players.

5. **Replenish cannot be obtained from the Enchanting Table** (patched out). Get it from:
   - Cocoa Beans Collection 8
   - Bazaar
   - Librarian visitor

6. **Stars give +10% per star inside dungeons, +2% outside.** Not +5% or flat across the board.

7. **Polarvoid Book no longer adds Breaking Power** (as of patch 0.20.6). It now only gives
   Mining Speed and Fortune. Remove any guide text about Breaking Power from Polarvoid.

8. **Fuming Potato Books now require 10 HPBs applied first** (changed 2026-01-27). Older guide
   text may say FPBs can be applied freely.

---

## 9. Enchantment XP Costs (Selected)

From `enchants.json` `enchants_xp_cost` — cost per level in XP levels:

| Enchant | L1 | L2 | L3 | L4 | L5 | L6 | Max Table Level |
|---------|----|----|----|----|----|----|-----------------|
| Sharpness | 10 | 15 | 20 | 25 | 30 | — | V |
| Critical | 10 | 20 | 30 | 40 | 50 | 75 | V |
| Giant Killer | 10 | 20 | 30 | 40 | 50 | 100 | V |
| Growth | 10 | 20 | 30 | 40 | 50 | 95 | V |
| Protection | 10 | 15 | 20 | 25 | 30 | 100 | V |
| Looting | 15 | 30 | 45 | 100 | 200 | — | III (table) |
| Life Steal | 20 | 25 | 30 | 50 | 200 | — | III (table) |
| Syphon | 20 | 25 | 30 | 45 | 200 | — | III (table) |
| Dragon Hunter | 50 | 100 | 150 | 200 | 250 | — | V |
| Overload | 50 | 100 | 150 | 200 | 250 | — | V |
| First Strike | 20 | 30 | 40 | 75 | 200 | — | IV (table) |
| Ender Slayer | 10 | 20 | 25 | 30 | 40 | 75 | V |
| Thunderlord | 20 | 25 | 30 | 40 | 50 | 200 | V |
| Infinite Quiver | 10 | 15 | 20 | 25 | 30 | 60 | V |
| Feather Falling | 10 | 15 | 20 | 25 | 30 | 60 | V |
| Efficiency | 10 | 15 | 20 | 25 | 30 | — | V |
| Fortune | 15 | 30 | 45 | — | — | — | III |
| Mana Vampire | 30 | 45 | 60 | 75 | 90 | 180 | X (high tier) |
| Pristine | 25 | 50 | 100 | 150 | 200 | — | V |
| Replenish | 50 | — | — | — | — | — | I (from table — now patched) |
| Ultimate Wise | 50 | 100 | 150 | 200 | 250 | — | V |
| Tabasco | 500 | 500 | 500 | — | — | — | III (special) |

---

## 10. Enchantment Slots by Item Type (Summary)

### Sword Enchantments (Core)
Bane of Arthropods, Cleave, Critical, Cubism, Dragon Hunter, Ender Slayer, Execute, Experience,
Fire Aspect, First Strike, Giant Killer, Impaling, Knockback, Lethality, Life Steal, Looting,
Luck, Mana Steal, Prosecute, Scavenger, Sharpness, Smite, Syphon, Titan Killer, Thunderlord,
Thunderbolt, Triple Strike, Vampirism, Venomous, Vicious, Smoldering, Champion, Divine Gift,
Tabasco.

### Bow Enchantments (Core)
Aiming, Chance, Cubism, Dragon Hunter, Flame, Impaling, Infinite Quiver, Piercing, Overload,
Power, Punch, Snipe, Toxophilite, Vicious, Divine Gift, Tabasco, Smoldering.

### Armor Enchantments (Core)
All pieces: Protection, Blast/Fire/Projectile Protection, Growth, Rejuvenate, Respite, Thorns,
Hardened/Strong/Ferocious/Mana Vampire (mana set), Pesterminator, Ice Cold.
Helmet only: Big Brain, Respiration, Aqua Affinity, Hecatomb, Transylvanian, Small Brain.
Chestplate only: Counter-Strike, True Protection, Reflection.
Leggings only: Smarty Pants, Tidal.
Boots only: Sugar Rush, Feather Falling, Depth Strider, Frost Walker.

### Tool Enchantments
Pickaxe/Drill: Compact, Efficiency, Experience, Fortune, Silk Touch, Pristine, Smelting Touch,
Paleontologist, Lapidary, Ultimate Flowstate.
Hoe: Replenish, Harvesting, Turbo-[crop] enchants, Cultivating, Delicate, Dedication.
Axe: Efficiency, Replenish, Silk Touch, Turbo-Coco/Melon/Pumpkin, Delicate, Sunder, Dedication,
Absorb, Ultimate First Impression, Ultimate Missile.

### Fishing Rod Enchantments (Core)
Angler, Blessing, Caster, Expertise, Frail, Looting, Luck of the Sea, Lure, Magnet,
Spiked Hook, Impaling, Charm, Corruption, Piscary, Quick Bite.
(Note: Piscary was removed from Experimentation Table as of 0.19.3.)

---

*Research file compiled 2026-03-04. Data from NEU repo constants and local wiki dump.*
