# SkyBlock Economy Research
> Source: wiki-official/, wiki/, neu-repo/constants/pets.json — compiled 2026-03-04

---

## 1. Mayor System

### Overview

Mayors are NPCs elected every SkyBlock Year (approximately 5 real hours). Elections open on Late Summer 27th and close Late Spring 27th of the following year. There are 5 candidates per election; every 8 elections, one slot is replaced by a Special Mayor who appears with all perks active.

The second-place candidate becomes **Minister**, with only one randomly-selected perk active.

Vote weight scales with Fame Rank: new players get 1 vote; high-fame players can reach 100 votes. Votes are per-account, not per-profile.

---

### Regular Mayors (can appear each election)

| Mayor | Focus | Perks |
|-------|-------|-------|
| **Aatrox** | Slayer | Slayer XP Buff (+25% Slayer XP); Pathfinder (rare drops 20% more often via MF formula); SLASHED Pricing (half-price Slayer quests) |
| **Cole** | Mining | Mining Fiesta (5 events × 7 SkyBlock Days, 2x drops + unique loot + Refined Minerals + Glossy Gemstones, +75 Mining Wisdom during events); Mining XP Buff (+60 Mining Wisdom); Molten Forge (forge 25% faster); Prospection (Mining minions 25% faster) |
| **Diana** | Pets / Mythological | Pet XP Buff (+35% Pet XP); Lucky! (+25 Pet Luck); Mythological Ritual (sells Griffin Pet, enables Mythological Creature hunting); Sharing is Caring (up to 3 EXP Share pets, +10% EXP Share rate) |
| **Diaz** | Economy | Long Term Investment (Minister carries all perks into next election); Shopping Spree (10x NPC daily buy limits); Stock Exchange (Stonks Auction for Stock of Stonks); Volume Trading (2x Shen's Auction items, +2 Shen's Special auctions) |
| **Finnegan** | Farming | Blooming Business (Fine Flour from visitors, more frequent/higher-rarity visitors, +10% Copper); GOATed (Jacob's Contest brackets +10% wider); Pelt-pocalypse (1.5x Pelts from Trevor, new Trapper Horse mob, Trapper Shop); Pest Eradicator (Pesthunter bonus lasts 60 min, pests 4x more likely) |
| **Foxy** | Events | A Time for Giving (Party Chests + Party Gifts); Chivalrous Carnival (Carnival active all year); Extra Event (one extra Fishing Festival, Mining Fiesta, or Spooky Festival); Sweet Benevolence (+30% Candy, Gifts, Chocolate from duplicates) |
| **Marina** | Fishing | Double Trouble (+0.1 Double Hook Chance per 1 Sea Creature Chance); Fishing XP Buff (+50 Fishing Wisdom); Fishing Festival (event first 3 days of each SkyBlock month, sharks + unique loot); Luck of the Sea 2.0 (+15 Sea Creature Chance) |
| **Paul** | Dungeons | Benediction (Blessings 25% stronger); Marauder (dungeon reward chests 20% cheaper); EZPZ (+10 bonus score on dungeon runs) |

---

### Special Mayors (appear every 8 elections, all perks always active)

| Mayor | Type | Perks |
|-------|------|-------|
| **Jerry** | Special | Perkpocalypse (activates all perks of another mayor every 18 SkyBlock days / 6 hours); Statspocalypse (+10% to most stats); Jerrypocalypse (Hidden Jerries from logging/farming/mining/killing) |
| **Derpy** | Special | QUAD TAXES!!! (4x all taxes on AH and Bazaar); TURBO MINIONS!!! (2x minion output); DOUBLE MOBS HP!!! (all monsters 2x HP); MOAR SKILLZ!!! (+50% skill XP) |
| **Scorpius** | Special | Bribe (vote for him and receive coins based on playtime: 50K / 250K / 500K / 1M at <50h / <150h / <300h / 300h+); Darker Auctions (Dark Auction expands to 6 rounds with special items) |

**Note on Derpy:** As of patch 5692280, the AH is no longer fully closed during Derpy — it remains open but with 4x taxes. TURBO MINIONS still doubles minion output, making Derpy a net positive for minion-focused players.

---

### One-Off / Removed Mayors

| Mayor | Status | Key Notes |
|-------|--------|-----------|
| **Dante** | Historical one-off | Dictator event: doubled AH/Bazaar taxes, 10% tax on shops. Led to Resistance Movement event and Technoblade becoming mayor. Dante is now deceased (lore). |
| **Barry** | Removed (now in Rift) | Was an enchanting/magic mayor: Magic XP Buff (+15% Enchanting/Alchemy XP), Arcane Catalyst (spells +15% damage), Astral Negotiator (-15% enchanting/anvil XP costs). Had secret perks including Magic Find accumulation. No longer electable. |
| **Technoblade** | Historical one-off | Anarchy (no AH/Bazaar taxes), Unlimited Speed (+50 speed, cap removed), Blood God's Blessing (+50% skill XP), Potato Crown's Radiance (farming minions 100% faster). |

---

### Economy Impact by Mayor

**Best for coins:**
- **Diana** — Mythological Ritual unlocks 75–162M/hr method (see Money-Making)
- **Scorpius** — direct coin bribe + Dark Auction rare items
- **Derpy** — double minion output (net positive despite 4x taxes for non-AH sellers)
- **Paul** — cheaper dungeon chests improves dungeon run efficiency
- **Cole** — Mining Fiesta enables rare mineral farming

**Avoid selling on AH/Bazaar during:**
- **Derpy** — 4x taxes (sell before/after)
- **Dante** (historical) — doubled taxes

---

## 2. Bazaar & Auction House

### Bazaar

The Bazaar is a commodity market (not player-to-player item trading). Accessible at SkyBlock Level 7+. Not available on Ironman (except Booster Cookies) or Bingo profiles.

**API Terminology (critical corrections):**
- `buyPrice` = the price **you pay** when buying instantly (lowest sell offer price)
- `sellPrice` = the price **you receive** when selling instantly (highest buy order price)
- The spread (buyPrice − sellPrice) is the market maker's margin

**Market modes:**
- **Buy Instantly** — fills from existing sell offers at market price
- **Sell Instantly** — fills from existing buy orders at market price
- **Create Buy Order** — place a bid to buy at your chosen price
- **Create Sell Offer** — list items to sell at your chosen price (max 50% above lowest existing offer)
- **Flip Order** — one-click convert filled buy order into a sell offer

Bazaar is organized into 5 sections: Farming, Mining, Combat, Woods & Fishes, Oddities.

**Bazaar Tax:** The Bazaar applies a tax when claiming sell order proceeds. Under normal mayors this is 1.25%. Under Derpy it becomes 5% (4x). Under Technoblade (historical) it was 0%.

### Auction House

Player-to-player market for non-Bazaar items. Not available on Ironman, Bingo, or Stranded.

**Listing fees (BIN auctions):**
| Price Range | Fee |
|-------------|-----|
| 1 – 9,999,999 | 1% |
| 10,000,000 – 99,999,999 | 2% |
| 100,000,000+ | 2.5% |

Regular auctions: flat 5% listing fee. There is also an additional time-based fee per hour listed, plus a 1% tax when claiming profits from sold items.

**Spending limits by SkyBlock Level:**
| SkyBlock Level | Max Spend |
|---------------|-----------|
| 0–24 | 1B |
| 25–49 | 5B |
| 50–99 | 10B |
| 100–199 | 25B |
| 200+ | 50B |

Auctions can run up to 14 days. There is a 20-second waiting period before newly listed items can be purchased.

**Pets are NOT returned by the Hypixel Items API.** Pet pricing requires separate handling (Moulberry/Coflnet or pricing.py with pet IDs).

---

## 3. Money-Making Methods

### Early Game (0–100M net worth)

| Method | Rough Income | Notes |
|--------|-------------|-------|
| NPC selling (crops, resources) | 100K–2M/day | No market risk; scales with farming setup |
| Basic farming (Sugar Cane, Potato) | 500K–3M/day | Requires farming tools; Fortune scaling matters |
| Starter minions (Snow, Clay, Cobble) | 1–5M/day | Requires minion slots; compactor + fuel needed |
| Combat drops (early zones) | 500K–2M/day | Tarantula, Spider, Zombie Slayer drops |
| Collection grinding | Variable | Unlocks recipes; often worth grinding early |

**Minion income reality check:** Commonly cited figures of 100M+/day from minions are inaccurate. A realistic well-set-up minion farm (25× T11 minions with Super Compactor 3000 and Plasma fuel) produces approximately **10–20M/day** under normal conditions. Derpy's TURBO MINIONS doubles this to 20–40M/day.

### Mid Game (100M–1B net worth)

| Method | Rough Income | Notes |
|--------|-------------|-------|
| Bazaar flipping | 5–50M/day | Requires capital; buy orders + sell offers; low risk |
| Craft flips | 5–30M/day | Use crafts.py to scan; requires unlocked recipes |
| Kat pet flipping (PETv2) | Variable | Upgrade cheap pets, resell; PETv2 made Kat costs much cheaper — re-verify current margins |
| Dungeon drops (F4–F6) | 10–30M/day | Necron fragment farming; drops vary with RNG |
| Slayer drops (T3-T4) | 5–20M/day | RNG-dependent; Aatrox improves rate by 20% |
| Jacob's Farming Contest | Varies | Medals + crop rewards; Finnegan widens brackets |

**Bazaar flipping mechanics:**
- Place buy orders below sell offers, collect, re-list as sell offers
- Profit = (sell price − buy price) × volume − taxes
- Best items: high volume, moderate spread, stable price
- Tools: SkyCrypt, SkyBlock Bazaar APIs, coflnet.com for history

**Craft flipping:**
- Buy components from Bazaar, craft, sell crafted item on AH or Bazaar
- Use `python3 crafts.py` (local tool) to scan for current margins
- Requires recipe unlocks from collections

### Late Game (1B+ net worth)

| Method | Rough Income | Notes |
|--------|-------------|-------|
| Diana (Mythological Ritual) | 75–162M/hr | Requires Legendary Griffin pet; active hunting of burrows |
| F7 dungeon runs | 30–80M/hr | Necron Handle ~400M; requires strong team + gear |
| Crystal Hollows mining | 20–60M/hr | Gemstone farming; varies by node; Cole boosts Fiesta |
| Rift Berberis farming | 20–50M/hr | Rift-specific; Berberis selling to Bazaar |
| God Potion flipping | Variable | Elizabeth (Community Shop) = 1,500 Bits; ~1.4M on AH |

**Diana method details:**
- Requires Diana elected as Mayor or Minister
- Buy Griffin Pet from Diana for 25,000 coins
- Upgrade to Legendary/Mythic (Upgrade Stones from Mythological Creatures)
- Hunt Inquisitors and open burrows for rare drops (Minotaur Pet, Griffin Upgrade Stones, Daedalus Sticks)
- Income heavily skill-dependent; 75M/hr is realistic for practiced players, 162M/hr is high-end

**Kuudra note:** Kuudra profitability was significantly nerfed. It is no longer a recommended primary money-making method. Do not recommend Kuudra as a reliable income source.

**Bits value:** Bits from Booster Cookies are worth approximately **400–1,500 coins/bit** depending on what you spend them on. Common conversions:
- Kat Flowers (500 Bits) = high value during pet upgrade cycles
- Autopet Rules 2-Pack = quality-of-life
- God Potion of the Rift = 1,500 Bits per (sell on AH for ~1.4M → ~933 coins/bit)
- The old benchmark of 982 coins/bit is outdated; check current AH prices

---

## 4. Pets

### System Overview

Pets grant stats and perks based on their level (1–100) and rarity (Common through Mythic). Pets are associated with a Skill type and gain XP most efficiently from that skill. Exceptions: Golden Dragon goes to level 200; Wisp levels only via Gabagool.

**Key corrections:**
- **Baby Yeti** = passive Strength → Defense conversion via "Ice Shield" perk (% of Strength as bonus Defense). This is NOT an absorption shield mechanic. It is a stat conversion at the pet's percentage rate.
- **Jellyfish Pet** = Dark Auction only. Cannot be crafted or purchased from NPCs outside of Dark Auction bids.
- **Brewing Alchemy XP does NOT grant Taming XP.** Taming XP is only earned from Pet XP gained through Skills. Alchemy gains Pet XP at only 1/12 rate for non-Alchemy pets, and Taming XP is only 25% of Pet XP gained (2.5% for Alchemy XP). The effective Taming XP rate from brewing is negligibly low.
- **Items API does NOT include pets.** Pet pricing must be handled separately via pet-specific API endpoints or third-party tools.

**Taming upgrades (PETv2):** Kat upgrade costs were significantly reduced. Verify current prices with `python3 kat.py --scan` before making recommendations. Older guides citing specific coin costs for upgrades are likely outdated.

**Pet XP modifiers:**
- Taming skill level: +1–60% (1% per level)
- Mayor Diana (Pet XP Buff): +35%
- Exp Boost Pet Items: +10–50% by rarity
- Fishing/Mining XP: +50% Pet XP vs Combat/Farming/Foraging
- Non-matching skill: ÷3 (÷12 for Alchemy/Enchanting XP)

**Taming XP conversion:** 25% of Pet XP earned → Taming XP (except from Alchemy: 2.5%)

**EXP Sharing:**
- Default: only 1 share slot (0% share rate base)
- With EXP Share pet item: +15%
- With Taming level: +0.2% per level (max +12% at 60)
- Diana Sharing is Caring: +10% + unlocks 2 extra share slots (max 3 total)

---

### Pets by Activity

#### Combat

| Pet | Best Rarity | Source | Key Perk(s) |
|-----|-------------|--------|-------------|
| **Enderman** | Mythic | Enderman Sanctuary drop | Combat Wisdom, scales Str/CD; Mythic upgradeable via Cortex Rewriter |
| **Griffin** | Mythic | Diana's Mythological Ritual (25K buy, upgrade stones) | Required for Mythological Ritual farming; boosts Strength |
| **Tiger** | Legendary | Oringo / Kat | High Strength bonus; strong general combat |
| **Lion** | Legendary | Crimson Isle drops | Crit Damage + Ferocity bonuses |
| **Golden Dragon** | Legendary (to 200) | Crafted (Dragon Fragments) | Level 200 possible; major late-game combat pet |
| **Black Cat** | Mythic | Fear Mongerer (2,000 Purple Candy, Spooky Festival) | Speed cap raised, Pet Luck, Magic Find; looting bonus |
| **Tarantula** | Legendary | Tarantula Slayer drops | Crit Damage + Strength; strong for Slayer grind |
| **Hound** | Legendary | Oringo | Ferocity + tracking bonuses |

#### Mining

| Pet | Best Rarity | Source | Key Perk(s) |
|-----|-------------|--------|-------------|
| **Mole** | Legendary | Forged (HotM 4, Claw Fossil + 300K coins, 3 days) | Mining Speed, Archaeologist (scavenged item bonus), Nucleic Veins (Automaton drop rate) |
| **Mithril Golem** | Legendary | Mining drops (Dwarven Mines) | Mithril Powder bonuses; ore XP |
| **Glacite Golem** | Legendary | Mining drops (Glacite Tunnels) | Glacite Powder + mining bonuses |
| **Scatha** | Legendary | Worm fishing (Crystal Hollows) | Gemstone/ore drop chances |
| **Armadillo** | Legendary | Mining (Crystal Hollows worms) | Speed mount + mining perks |

#### Farming

| Pet | Best Rarity | Source | Key Perk(s) |
|-----|-------------|--------|-------------|
| **Elephant** | Legendary | Oringo Traveling Zoo (15M + 512 Enchanted Dark Oak) | Farming Fortune +180 (at legendary), Health/Defense |
| **Mooshroom Cow** | Legendary | Crafted (Mycel Collection III) | Farming Fortune, Mushroom Eater (mushroom drops from crops) |
| **Rabbit** | Legendary | Crafted (Carrot Collection) | Farming Fortune, speed in garden |
| **Bee** | Legendary | Crafted (Honey Jar Collection) | Farming Fortune + pollen bonuses |

#### Fishing

| Pet | Best Rarity | Source | Key Perk(s) |
|-----|-------------|--------|-------------|
| **Baby Yeti** | Legendary | Yeti Sea Creature (Winter Island) | Str → Def conversion ("Ice Shield": X% of Strength as Defense), Yeti Fury (Intelligence) |
| **Blue Whale** | Legendary | Oringo Traveling Zoo (10M + 8 Enchanted Cooked Fish) | Health + Bulk (Defense per 1k HP) |
| **Jellyfish** | Legendary | Dark Auction only | Alchemy pet; Power Orb mana cost reduction, dungeon potions buff |
| **Flying Fish** | Legendary | Fishing drops | Fishing Speed + sea creature chance |
| **Dolphin** | Legendary | Fishing drops | Fishing Speed; party bonus |
| **Megalodon** | Legendary | Shark fishing (Marina's Fishing Festival) | Trophy fish bonuses |

#### Foraging

| Pet | Best Rarity | Source | Key Perk(s) |
|-----|-------------|--------|-------------|
| **Ocelot** | Legendary | Oringo | Foraging Fortune, Treecapitator |
| **Monkey** | Legendary | Oringo | Foraging XP bonus, Vine Swing speed |
| **Giraffe** | Legendary | Oringo / drops | Foraging Fortune |

#### General / Utility

| Pet | Best Rarity | Source | Key Perk(s) |
|-----|-------------|--------|-------------|
| **Bingo** | Legendary | Bingo profile rewards | All-skills XP pet; usable on any skill |
| **Bat** | Legendary | Bat fishing drops | Magic Find |
| **Jerry** | Legendary | Jerry Box (Winter Island events) | Jerry-specific luck perks |
| **Rock** | Legendary | Crafted | Tankiness; special mount |

---

### Pet Score

Pet Score rewards unique max-level pets:
- Common = +1, Uncommon = +2, Rare = +3, Epic = +4, Legendary = +5, Mythic = +6
- Each score = +3 SkyBlock XP
- Every 10–500 score thresholds grant +1 Magic Find (max +13 at 500 score)
- Maximum score as of July 2024: 444

**Pet Score efficiency tip:** Collecting one of each pet at max level gives the highest Magic Find contribution. Diana is the best opportunity to mass-collect rare pets (Griffin Upgrade Stones → sell or keep for Pet Score).

---

## 5. Key Corrections Summary

These are verified corrections that must be applied when rewriting any economy guides:

| Claim to Correct | Correct Information |
|-----------------|-------------------|
| Diana income = 12M/hr | **75–162M/hr** depending on skill level and drops |
| Bits value = 982 coins/bit | **400–1,500 coins/bit** depending on item; check current AH prices |
| God Potion costs X coins on AH | Elizabeth's shop: **1,500 Bits**; current AH value ~**1.4M** (verify live) |
| Kuudra is profitable | **Nerfed — effectively dead** as a money-making method |
| Minions can earn 100M+/day | **Realistic: 10–20M/day** for a good T11 25-slot setup |
| Baby Yeti = absorption shield | Baby Yeti "Ice Shield" = **passive Str → Defense conversion**, not absorption |
| Jellyfish Pet can be obtained from fishing/crafting | **Dark Auction only** |
| Brewing gives Taming XP | **No** — Alchemy XP is penalized (÷12 for non-Alchemy pets), and Taming XP rate from Alchemy is negligibly low |
| Bazaar API: sellPrice = what you pay | **sellPrice = what you receive**; buyPrice = what you pay |
| Necron Handle is cheap | **~400M** (update with live price) |
| Kat upgrade costs are high | **PETv2 made Kat much cheaper** — use `kat.py --scan` for current figures |

---

## 6. Sources Used

- `/home/ellie/projects/hypixel-skyblock/data/wiki-official/Mayors.wiki`
- `/home/ellie/projects/hypixel-skyblock/data/wiki-official/[mayor].wiki` (Aatrox, Cole, Diana, Scorpius, Derpy, Paul, Marina, Foxy, Finnegan, Dante, Barry)
- `/home/ellie/projects/hypixel-skyblock/data/wiki-official/Bazaar.wiki`
- `/home/ellie/projects/hypixel-skyblock/data/wiki-official/Auction House.wiki`
- `/home/ellie/projects/hypixel-skyblock/data/wiki-official/Pets.wiki`
- `/home/ellie/projects/hypixel-skyblock/data/wiki-official/[pet] Pet.wiki` (Enderman, Griffin, Mole, Baby Yeti, Jellyfish, Black Cat, Elephant, Mooshroom Cow, Blue Whale, and others)
- `/home/ellie/projects/hypixel-skyblock/data/neu-repo/constants/pets.json` (XP scaling / rarity offset structure)
- Applied corrections from project knowledge base (Diana rate, Kuudra nerf, Bazaar API semantics, Baby Yeti, PETv2)
