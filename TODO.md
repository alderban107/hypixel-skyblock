# SkyBlock Toolkit — TODO

## 1. ~~Networth Calculator (`networth.py`)~~ ✅ COMPLETE

Calculate total profile value by pricing every item across all storage locations.

### Data Sources

Pull items from every inventory slot in the profile API:
- **Inventory** — `inv_contents.data`
- **Ender Chest** — `ender_chest_contents.data`
- **Accessory Bag** — `bag_contents.talisman_bag.data`
- **Wardrobe** — `wardrobe_contents.data`
- **Equipment** — `equippment_contents.data` (yes, Hypixel misspells it)
- **Personal Vault** — `personal_vault_contents.data`
- **Storage** (Backpacks) — `backpack_contents.{0..17}.data`
- **Museum** — Hypixel API endpoint `v2/skyblock/museum?profile={id}` — items donated here still have value
- **Pets** — `pets_data.pets[]` (price by `type` + `tier`, use `pricing.py` pet ID format)
- **Purse** — `coin_purse` (liquid coins on hand)
- **Bank** — `profile.banking.balance` (shared across coop)
- **Sacks** — `sacks_counts` (price each material × quantity via Bazaar)
- **Essence** — `currencies.essence.{type}.current` (may or may not be tradeable — track but flag)

All inventory blobs are base64-encoded gzipped NBT. `profile.py` already has `decode_nbt_inventory_slots()` which returns item dicts with `id`, `reforge`, `stars`, `hpb`, `enchants`, and `lore`.

### Pricing Strategy

Use `pricing.py`'s `PriceCache` for all lookups. **Default pricing: weighted average** across all tools.

For Bazaar items, weighted average formula:
```
weighted_price = (buy_price × buy_volume + sell_price × sell_volume) / (buy_volume + sell_volume)
```
This gives a more realistic valuation than pure instant-sell (too conservative) or buy-order (too optimistic). `pricing.py` already has buy/sell prices and volumes — add a `weighted()` method to `PriceCache`.

Price resolution order:
1. **Bazaar items** — weighted average (default)
2. **AH items** — use `lowest_bin` from Moulberry, fall back to `avg_lbin_3d`
3. **Soulbound items** — no AH/Bazaar price exists. Instead, calculate **crafting cost** by:
   - Looking up the recipe in NEU repo (`data/neu-repo/items/`)
   - Recursively pricing each ingredient via Bazaar/AH
   - Using `crafts.py`'s `calculate_craft_cost()` as a starting point, but extended to handle:
     - Recipes with non-Bazaar ingredients (AH-priced components)
     - Multi-step recipes (ingredient is itself crafted from other things)
     - Essence costs (Wither/Dragon/etc. essence × Bazaar price)
   - Flag these items as `[Soulbound - Craft Cost]` in output so it's clear the value is what it *cost to make*, not what it could sell for
4. **Unpriceable items** — some items have no recipe and no market price (event exclusives, unobtainable items). Track these separately as "unpriced" rather than silently dropping them

### Dual Networth (from SkyHelper-Networth)

SkyHelper-Networth reports **two** networth figures, which is a genuinely useful distinction:
- **Total Networth** — everything, including soulbound items valued at craft cost
- **Unsoulbound Networth** — only tradeable items, reflecting liquidation value

We should do the same. Soulbound detection: check the item lore for `* Soulbound *` or `* Co-op Soulbound *`, or check `extraAttributes.donated_museum`. Our NBT parser already extracts lore lines.

### Modifier Pricing (from SkyHelper-Networth's handler system)

SkyHelper-Networth uses an impressive handler architecture — 30+ individual handlers that each price a specific modifier. Their key insight is **application worth multipliers**: a modifier doesn't add its full market price to an item, because applying it is common and removing it isn't possible. For example:
- Essence stars: 0.75× the essence market price
- Hot Potato Books: 1.0× (always worth full price)
- Fuming Potato Books: 0.6×
- Recombobulators: 0.8×
- Enchantments: 0.85×
- Reforges: 1.0× (the reforge stone itself)
- Gemstones: 1.0×
- Master Stars: 1.0×
- Necron Blade Scrolls: 1.0×
- Art of War/Peace: 0.6× / 0.8×
- Pet Candy: 0.65×
- Dyes: 0.9×

This is much smarter than just adding raw material costs. We should adopt this approach.

**Full modifier pricing from v1** — include all modifier handlers from the start. SkyHelper-Networth's handler architecture is a good reference. Each modifier is priced independently and summed:

- **Stars** (essence cost × 0.75, from `upgrade_costs` in Hypixel items API)
- **HPB/Fuming** (count from `hot_potato_count` NBT field — first 10 are HPB at 1.0×, remainder are Fuming at 0.6×)
- **Reforges** (reforge stone price × 1.0×, from a mapping of modifier name → stone item ID)
- **Enchantments** (price each enchant book on AH × 0.85)
- **Recombobulators** (from `rarity_upgrades` NBT field, 0.8×)
- **Gemstones** (from gemstone slot NBT data, 1.0×)
- **Master Stars** (1.0×)
- **Necron Blade Scrolls** (Implosion, Shadow Warp, Wither Shield — 1.0×)
- **Art of War/Peace** (0.6× / 0.8×)
- **Drill/Rod parts** (1.0×)
- **Dyes** (0.9×)
- **Pet Candy** (0.65×)
- **Pet Items** (held item, 1.0×)
- **Wood Singularity** (0.5×)
- **Farming for Dummies** (0.5×)
- **Etherwarp Conduit** (1.0×)
- **Transmission Tuners** (0.7×)
- **Mana Disintegrator** (0.8×)

Our NBT parser (`decode_nbt_inventory_slots`) already extracts: `id`, `reforge` (modifier), `stars` (upgrade_level), `hpb` (hot_potato_count), `enchants`, and `lore`. Extend it to also extract: `rarity_upgrades`, gemstone data, scroll data, drill/rod parts, pet held item, and other modifier fields.

Store application worth multipliers as a dict constant — easy to tune if values feel off.

### Non-Cosmetic Networth (from SkyHelper-Networth)

SkyHelper also separates cosmetic items (dyes, skins, runes, pet skins) from functional items. This is useful because cosmetic value is speculative — a rare dye might be "worth" 50M but doesn't affect gameplay. Consider adding a `--no-cosmetic` flag.

### Output Format

```
═══════════════════════════════════════════
  NETWORTH SUMMARY — PlayerName
═══════════════════════════════════════════

  Category                     Value
  ─────────────────────────────────────
  Purse                        1.2M
  Bank                         5.0M
  Inventory                    12.3M
  Ender Chest                  8.7M
  Accessory Bag                45.2M
  Wardrobe                     120.5M
  Equipment                    15.0M
  Pets                         35.8M
  Museum                       18.3M
  Sacks                        3.1M
  Storage                      2.4M
  Personal Vault               0
  ─────────────────────────────────────
  TOTAL NETWORTH               249.2M
  UNSOULBOUND NETWORTH         144.0M

  Top 10 Most Valuable Items:
    1. POWER_WITHER_CHESTPLATE  [5★] [Soulbound]    85.0M
       Base: 42M | Stars: 28M | HPB: 2.1M | Enchants: 12.9M
    2. GOLDEN_DRAGON;4                               42.0M
    3. LIVID_DAGGER             [5★]                  9.2M
    ...

  Soulbound Items (valued at craft cost):     105.2M
  Unpriced Items (no market/recipe data):     3 items
    - HEGEMONY_ARTIFACT
    - ...
```

### CLI Interface

```bash
python3 networth.py                    # full networth breakdown
python3 networth.py --category pets    # just pets breakdown
python3 networth.py --top 20          # top 20 most valuable items
python3 networth.py --no-cosmetic     # exclude cosmetic items
python3 networth.py --json            # machine-readable output
python3 networth.py --verbose         # list every item with price, not just summary
```

### Implementation Notes

- Reuse `profile.py`'s `decode_nbt_inventory_slots()` for all inventory parsing
- Reuse `pricing.py`'s `PriceCache` for all market lookups
- Extend `crafts.py`'s recipe/cost logic for soulbound craft cost calculation
- Pet pricing: construct pet ID as `{TYPE};{RARITY_NUM}` and pass to `PriceCache`
- Bank balance is at the profile level (shared in coop), not the member level
- Default to weighted average pricing for Bazaar items, LBIN for AH items
- Cache-friendly: bulk-fetch prices once, then iterate items
- Museum data requires a separate API call (`v2/skyblock/museum`)
- Application worth multipliers stored as a dict constant — easy to tune
- Soulbound detection from lore lines (already parsed by NBT reader)
- SkyHelper-Networth handles many edge cases for item ID resolution (skinned items, shiny variants, editioned items, fragged/starred prefix items) — reference their `getItemId()` logic when handling special item variants

---

## 2. ~~Dungeon Profit Calculator (`dungeons.py`)~~ ✅ COMPLETE

Calculate expected profit per run for each dungeon floor based on drop tables and current market prices.

### Core Concept

For a given floor, answer: "What's my expected coins per run, and which chests should I open?"

### Data Extraction

**Scrape the fandom wiki live** (hypixel-skyblock.fandom.com). The fandom wiki is more reliably structured and actively maintained by community volunteers. FluxCapacitor2's dungeon-loot-calculator scrapes the official wiki (wiki.hypixel.net) but the fandom wiki is more stable for parsing.

Scrape dungeon reward chest pages for each floor to extract:
- Item name, chest type, cost per item, and drop chances
- Drop chances vary by **Treasure Talisman tier** (None/Talisman/Ring/Artifact) and **Boss Luck level** (0/1/3/5/10)
- Separate rates for **base** vs **S+ score** runs

Cache scraped data locally as `data/dungeon_loot.json` with a TTL (e.g., 24 hours) so we're not hitting the wiki every run. Re-scrape on demand with `--refresh`.

FluxCapacitor2's item name → item ID mapping (`constants/items.ts`) is a useful reference — it maps display names like "Necron's Handle" to API IDs like `NECRON_HANDLE`, including tricky ones like enchanted books (`"Soul Eater I": "ENCHANTED_BOOK-ULTIMATE_SOUL_EATER-1"`).

### Calculations

For each floor + chest combination:
```
EV = Σ (item_price × drop_chance / 100)
Chest Profit = EV - chest_opening_cost
```

For each floor (total):
1. **Per-chest EV**: calculate for each chest tier (Wood, Gold, Diamond, Emerald, Obsidian, Bedrock)
2. **Chest profit** = EV - opening cost → OPEN if positive, SKIP if negative
3. **Optimal run EV** = sum of all profitable chests' net profit
4. **Hourly rate** = optimal run EV × runs/hour (configurable, default by floor)

### Drop Rate Modifiers

The wiki provides drop rates for multiple modifier combinations. We should support:
- **Treasure Talisman tier**: None, Talisman, Ring, Artifact — affects drop chances for most items
- **Boss Luck level**: 0, 1, 3, 5, 10 — from Boss Luck enchant on equipment
- **S+ vs base score** — significantly different drop rates on higher floors
- Default to player's actual Treasure Talisman tier (check accessory bag) and S+ rates

### Kismet Analysis (from FluxCapacitor2)

Their approach is simple and effective:
```
Reroll EV = Chest EV - Kismet Feather price
```
If the EV of the chest exceeds the Kismet price, rerolling is profitable. Show this per-chest.

### Essence Drops

Essence is guaranteed per run and scales with Cata level. These are often a significant portion of floor profit. Price essence via Bazaar (`ESSENCE_WITHER`, etc.). Need to find the scaling formula or table — the wiki should have this.

### RNG Drop Handling

High-value rare drops (Necron's Handle at 0.04%, Shadow Assassin CP, etc.) dominate EV calculations despite being extremely unlikely per run. Show:
- **EV with RNG drops** — mathematical expected value including everything
- **EV without RNG drops** — what you'll actually see most runs (more practical)
- **Separate RNG section** — list each rare drop with its individual EV contribution

### Output Format

```
═══════════════════════════════════════════
  DUNGEON PROFIT — Floor 7
  Score: S+ | Treasure Talisman: Artifact | Boss Luck: 10
═══════════════════════════════════════════

  Chest Breakdown:
    Chest          Cost      EV        Profit    Verdict
    ─────────────────────────────────────────────────────
    Wood           free      12.3K     +12.3K    OPEN
    Gold           20K       45.2K     +25.2K    OPEN
    Diamond        50K       38.1K     -11.9K    SKIP
    Emerald        100K      215.4K    +115.4K   OPEN
    Obsidian       200K      180.2K    -19.8K    SKIP
    Bedrock        500K      1.2M      +700K     OPEN ★

  Guaranteed Drops:
    Wither Essence ×32              89.6K

  ─────────────────────────────────────────────────────
  Optimal Run EV (profitable chests + essence):  1.03M
  Optimal Run EV (excluding RNG drops):          420K
  Runs/hr estimate:                              4-5
  Hourly rate:                                   1.7M - 2.1M (excl. RNG)

  High-Value RNG Drops:
    Necron's Handle     0.04%    LBIN: 680M     EV: 272K/run
    Auto Recombobulator 2%       LBIN: 12M      EV: 240K/run

  Kismet Analysis (Kismet Feather: 350K):
    Bedrock: Chest EV 1.2M → Reroll EV 850K  → WORTH IT
    Emerald: Chest EV 215K → Reroll EV -135K  → NOT WORTH IT
```

### CLI Interface

```bash
python3 dungeons.py                           # all unlocked floors summary (compact)
python3 dungeons.py --floor f7                # detailed F7 breakdown
python3 dungeons.py --floor m5                # Master Mode 5
python3 dungeons.py --talisman ring           # override Treasure Talisman tier
python3 dungeons.py --luck 5                  # override Boss Luck level
python3 dungeons.py --no-splus                # show base score rates instead of S+
python3 dungeons.py --runs-per-hour 6         # override runs/hr estimate
python3 dungeons.py --json                    # machine-readable output
```

### Implementation Notes

- Drop table source: scrape fandom wiki live (hypixel-skyblock.fandom.com), cache as `data/dungeon_loot.json` with 24hr TTL, `--refresh` to force re-scrape
- Item name → ID mapping: build from FluxCapacitor2's reference + our own `items.py` display names
- Price data: `pricing.py` bulk fetch (Moulberry LBIN + Bazaar weighted average)
- Kismet Feather price from Bazaar (`KISMET_FEATHER`)
- Essence quantity scaling: grep wiki for the formula/table
- Some drops are soulbound on pickup — only price tradeable drops
- Bedrock chest only available F5+ (FluxCapacitor2 handles this)
- Master Mode floors (M1-M7) have different loot tables — wiki has these as separate tabs
- Auto-detect player's Treasure Talisman tier from profile data if available

---

## 3. Missing Accessories Finder (`accessories.py`)

Identify which accessories a player is missing, prioritized by magical power and cost-effectiveness.

### Core Concept

Compare the player's accessory bag contents against the full list of obtainable accessories. Show what's missing, what it would cost, and how much magical power each one adds — so you can find cheap MP upgrades you've overlooked.

### Data Sources

**Player's accessories — check ALL locations (from SkyCrypt):**
SkyCrypt's `getAccessories()` scans far more than just the accessory bag:
- **Accessory bag**: `bag_contents.talisman_bag.data` (primary location)
- **Armor slots**: some accessories are worn as armor (e.g., Power Artifact in helmet slot)
- **Inventory**: accessories that haven't been put in the bag yet
- **Ender Chest + Storage**: accessories stashed away but still owned

Our `profile.py` already decodes all these locations. We need to scan all of them, not just the bag.

**Full accessory list:**
- **Hypixel items API** (`resources/skyblock/items`, no key needed) — authoritative source. Filter by `category: "ACCESSORY"`. Gives us ID, name, tier/rarity, and material data
- This is what SkyCrypt uses (via MongoDB cache of the same data)
- `items.py`'s `get_item_category()` can identify accessories

**Accessory upgrade chains (from SkyCrypt):**
SkyCrypt maintains a hardcoded `accessoryUpgrades` array — ~50 upgrade chains mapping e.g.:
```
["WOLF_TALISMAN", "WOLF_RING"]
["CANDY_TALISMAN", "CANDY_RING", "CANDY_ARTIFACT", "CANDY_RELIC"]
["BEASTMASTER_CREST_COMMON", ..., "BEASTMASTER_CREST_LEGENDARY"]
```

This is essential. Only the highest tier in a chain provides MP — lower tiers are wasted bag slots. We need this data. Options:
1. **Use the Hypixel items API `upgrade_costs` field** if it provides chain grouping (needs verification)
2. **Port SkyCrypt's `accessoryUpgrades` array** — it's well-maintained and MIT licensed
3. **Build from NEU repo** — may have family data in item files

Recommend option 2 as the starting point (known-good, comprehensive), stored as a JSON file in `data/accessory_upgrades.json`, with verification against the items API.

**Accessory aliases (from SkyCrypt):**
Some accessories have alternate IDs that represent the same item (e.g., `PIGGY_BANK` / `BROKEN_PIGGY_BANK` / `CRACKED_PIGGY_BANK`, various `WEDDING_RING` and `CAMPFIRE_TALISMAN` variants). SkyCrypt's `ACCESSORY_ALIASES` mapping handles these — without it, you'd incorrectly flag aliased items as missing.

**Ignored accessories (from SkyCrypt):**
Some accessories exist in the API but are unobtainable or shouldn't be counted:
```
LUCK_TALISMAN, TALISMAN_OF_SPACE, RING_OF_SPACE, ARTIFACT_OF_SPACE,
COMPASS_TALISMAN, GRIZZLY_PAW, ETERNAL_CRYSTAL, OLD_BOOT, BINGO_HEIRLOOM, etc.
```
SkyCrypt maintains an `ignoredAccessories` list for these. We should port this too.

**Special accessories (from SkyCrypt):**
Some accessories have unusual pricing or rarity behavior:
- `BOOK_OF_PROGRESSION` / `PANDORAS_BOX` — rarity varies (uncommon through mythic), affects MP
- `PULSE_RING` — has variable rarity, upgrade cost is Thunder in a Bottle × tier-dependent count
- `POWER_ARTIFACT` — custom pricing (requires Perfect gemstones to craft)
- `TRAPPER_CREST` — custom pricing

**Magical Power per rarity:**
- Common: 3, Uncommon: 5, Rare: 8, Epic: 12, Legendary: 16, Mythic: 22
- Special: 3, Very Special: 5
- Hegemony Artifact doubles its own MP (check separately)
- Abicase adds MP based on active Abiphone contacts (floor(contacts / 2))
- Rift Prism adds 11 MP if consumed

### Duplicate / Inactive Detection (from SkyCrypt)

SkyCrypt marks accessories as inactive when:
1. A higher-tier upgrade exists in the player's collection (e.g., have Ring → Talisman is inactive)
2. Exact duplicates exist (only one counts for MP)
3. An alias of the accessory is already present

This is important for showing the player their *effective* MP vs total accessories owned. We should show:
- Active count (contributing MP)
- Inactive count (wasted bag slots — could be sold/upgraded)
- Duplicates that should be removed

### Recombobulated Tracking (from SkyCrypt)

Recombobulating an accessory raises its rarity by one tier, gaining extra MP. SkyCrypt tracks:
- How many accessories are recombobulated vs. total that allow recombing
- This tells the player how much more MP they could gain from recombs alone

We should include this: "X/Y accessories recombobulated. Recombing all would add +Z MP."

### Calculations

For each missing accessory:
1. **MP gain** — rarity MP value, or MP difference if upgrading within a family
2. **Cost** — LBIN from AH, or craft cost for craftable ones, or flag as quest/event if no market data
3. **Coins per MP** — cost ÷ MP gain. Lower = better value. This is the primary sort key
4. **Obtainability** — buyable on AH, craftable, quest reward, event exclusive, unobtainable

For upgrade opportunities (player has lower tier):
- Show incremental cost: price of next tier minus value of current tier (since current can be sold/used as ingredient)
- Show incremental MP gain

### Output Format

```
═══════════════════════════════════════════
  MISSING ACCESSORIES — PlayerName
  Active: 65/78 owned (350 MP)
  Inactive: 13 (duplicates or lower-tier)
  Recombobulated: 12/65 (could gain +38 MP from recombs)
═══════════════════════════════════════════

  Best Upgrades by Coins/MP:
    #   Accessory                    Rarity    MP    Cost       Coins/MP   Source
    ──────────────────────────────────────────────────────────────────────────────
    1.  Night Crystal               Uncommon  +5    12.5K      2.5K       AH
    2.  Day Crystal                 Uncommon  +5    14.2K      2.8K       AH
    3.  Wither Relic                Legendary +4    1.2M       300K       AH (upgrade)
        └─ You have: Wither Artifact [Epic]
    4.  Scarf's Grimoire            Legendary +16   3.8M       237.5K     AH
    5.  Red Scarf                   Legendary +16   4.1M       256.3K     AH
    ...

  Inactive Accessories (wasted bag slots):
    Accessory                      Reason
    ─────────────────────────────────────────────────
    Wolf Talisman                  Have Wolf Ring (higher tier)
    Speed Talisman (×2)            Duplicate

  Locked Behind Progression:
    Accessory                      Requirement              MP    Cost
    ────────────────────────────────────────────────────────────────────
    Tarantula Talisman             Spider Slayer 3           +5    180K
    Wolf Ring                      Wolf Slayer 6 (✗)         +8    1.2M

  Unobtainable / Event-Only:
    - Dante Talisman (Mayor Dante exclusive)
    - ...

  Summary:
    Missing accessories:           42
    Available now:                 28
    Total MP if all obtained:      +186 MP (→ 536 MP)
    Cheapest 50 MP:                ~4.2M (13 accessories)
    Full recomb potential:         +38 MP (53 remaining × ~1.5M each)
```

### CLI Interface

```bash
python3 accessories.py                    # full missing accessories report
python3 accessories.py --budget 10m       # only show accessories within 10M total budget
python3 accessories.py --sort cost        # sort by absolute cost instead of coins/MP
python3 accessories.py --upgrades-only    # only show upgrade opportunities (have lower tier)
python3 accessories.py --inactive         # focus on inactive/duplicate cleanup
python3 accessories.py --available-only   # hide locked/unobtainable
python3 accessories.py --json             # machine-readable output
```

### Implementation Notes

- Authoritative accessory list from Hypixel items API (`resources/skyblock/items`, no key needed)
- Port SkyCrypt's `accessoryUpgrades` array to `data/accessory_upgrades.json` — 50+ upgrade chains
- Port SkyCrypt's `ACCESSORY_ALIASES` and `ignoredAccessories` lists
- Scan ALL inventory locations for accessories, not just the bag
- Handle special accessories (Book of Progression variable rarity, Pulse Ring upgrade costs, etc.)
- Inactive detection: mark lower-tier upgrades and duplicates
- Recombobulation tracking: count recombed vs total, calculate potential MP gain
- Use `items.py`'s `check_requirements()` for progression gating
- Price using `pricing.py` bulk lookups for efficiency
- MP formula for Hegemony Artifact and Abicase/Rift Prism are special cases — handle explicitly

---

## 4. Slayer Profit Calculator (`slayers.py`)

Calculate expected profit per boss for each slayer type and tier, with live pricing and RNG meter optimization.

### Core Concept

For a given slayer type and tier, answer: "How much profit do I make per boss, which RNG meter target is optimal, and what's my hourly rate?"

No automated tool currently does this with live prices. The community relies on manual forum posts (TheFireDragon52's profit breakdowns) or spreadsheets with manually entered prices. We can build the definitive version.

### Drop Table Data

**Source: Luckalyzer's `slayer.json`** (Mabi19, MIT licensed) — clean fractional drop probabilities and RNG meter boss counts for all 5 slayer types. Example:
```json
{
  "WARDEN_HEART": {
    "probability": { "num": 2, "den": 14527 },
    "rngMeterBosses": 2421
  }
}
```

This covers RNG drops only. We also need **common drops** (guaranteed/high-chance loot like Revenant Flesh, Tarantula Silk, Wolf Tooth, etc.) which aren't in Luckalyzer's data since it's a luck calculator, not a profit calculator.

**Common drop data** — source from our local wiki dump (`data/wiki/parsed/`). Each slayer boss has:
- Guaranteed material drops (e.g., 63-64 Revenant Flesh per T5 Revenant)
- Weight-based common drops (Revenant Viscera, Foul Flesh, etc. — dropped based on weighted RNG)
- Per-tier differences (higher tiers have access to rarer drops)

Store everything in `data/slayer_drops.json` with structure:
```json
{
  "zombie": {
    "name": "Revenant Horror",
    "tiers": {
      "1": { "cost": 100, "xp": 5, "combat_xp": 150, "level": 15 },
      "2": { "cost": 2000, "xp": 25, "combat_xp": 250, "level": 50 },
      "3": { "cost": 10000, "xp": 100, "combat_xp": 1000, "level": 200 },
      "4": { "cost": 50000, "xp": 500, "combat_xp": 2500, "level": 600 },
      "5": { "cost": 100000, "xp": 1500, "combat_xp": 5000, "level": 1580 }
    },
    "guaranteed_drops": {
      "REVENANT_FLESH": { "min": 63, "max": 64, "min_tier": 5 }
    },
    "weighted_drops": { ... },
    "rng_drops": { ... }
  }
}
```

### Pricing Strategy (from TheFireDragon52's methodology)

Use a **weighted average** for Bazaar items rather than just instant sell:
```
weighted_price = (buy_price × buy_volume + sell_price × sell_volume) / (buy_volume + sell_volume)
```
This gives a more realistic valuation than pure instant-sell (too conservative) or buy-order (too optimistic). `pricing.py` already has both buy and sell prices plus volumes — just need to expose the weighted calculation.

For AH items (rare drops like Warden Heart, Scythe Blade), use LBIN or average sale price from Moulberry/Coflnet.

Some drops are NPC-only sells (Foul Flesh at 25K each) — hardcode these.

### RNG Meter Optimization (from TheFireDragon52)

The RNG meter fills with slayer XP per boss kill. When full, you can claim a guaranteed drop. The key insight from the forum analysis:

1. For each RNG-eligible drop, calculate **coins per meter XP**:
   ```
   coins_per_xp = item_market_price / meter_xp_to_fill
   ```
2. The optimal target is whichever drop gives the highest coins/XP ratio
3. Convert each boss's XP contribution to coin value:
   ```
   meter_value_per_boss = boss_xp × best_coins_per_xp
   ```

For Revenant T5, the meter contributes ~49.5K per boss — the single largest profit source. This is a non-obvious insight that makes the tool genuinely useful.

**Strategy nuance** (from spreadsheet discussion): the optimal play is to leave the meter OFF (no target selected) until it's full enough to claim, then select and claim. This avoids the meter's increased-drop-chance mechanic consuming your meter progress early. The spreadsheet author notes this is complex to model perfectly — for v1, we can assume the simpler "always targeting best item" approach and note the optimization.

### Magic Find Integration

SkyBlock slayer drops use a **weight-based system**, which means Magic Find doesn't simply multiply drop rates. It increases the weight of rare items, which:
- **Increases** rare drop chance (good)
- **Decreases** common drop chance (the total weight pool grows, so common items' share shrinks)

The formula (from community research):
```
effective_weight = base_weight × (1 + magic_find / 100)  [for items affected by MF]
```
Only items with <5% base drop rate are affected by Magic Find. Common drops (>5%) keep their original weight but their effective chance decreases as the total pool weight increases.

Include Magic Find as an optional `--magic-find` flag. Without the flag, calculate without MF (matching TheFireDragon52's baseline approach).

### Scavenger & Champion Coins

Additional coin sources per boss (from TheFireDragon52):
- **Scavenger 5**: `mob_level × 0.18` coins per kill (boss + minibosses)
- **Champion X**: 5 coins per boss if not one-shot (2nd hit trigger)
- These are small but add up — include with a note about assumed enchants

Boss level is per-tier (e.g., Revenant T5 is level 1580 = 2,844 coins from Scav 5).

### Aatrox Mayor Detection

If Aatrox is the current mayor, slayer costs are reduced and XP is boosted:
- 25% reduced quest costs (50% with all perks)
- 25% bonus slayer XP
- Check via Hypixel API election endpoint or SkyBlock calendar

Include as auto-detected bonus or `--aatrox` flag.

### Per-Tier Comparison

Show a comparison table across all tiers for a given slayer:
```
  Tier   Cost     XP    Profit/Boss   Coins/XP    Est. Kills/hr   Profit/hr
  ─────────────────────────────────────────────────────────────────────────
  T1     100      5     +450          90           120             54K
  T2     2,000    25    +1,200        48           80              96K
  T3     10,000   100   +8,500        85           40              340K
  T4     50,000   500   +24,500       49           15              367.5K
  T5     100,000  1500  +24,500       16.3         8               196K
```

This answers the question "which tier should I grind?" — it depends on whether you're optimizing coins/XP (for leveling cheaply) or profit/hour (for money-making).

### Output Format

```
═══════════════════════════════════════════
  SLAYER PROFIT — Revenant Horror (T5)
  Summoning Cost: 100,000 coins
═══════════════════════════════════════════

  Guaranteed Drops:
    Revenant Flesh ×63.5 avg          8.5K

  Common Drops (weight-based):
    Revenant Viscera (1 in 7.3)       14.9K/boss
    Foul Flesh (1 in 7.3)            12.1K/boss  [NPC sell]
    Catalysts, misc                   232/boss

  RNG Drops:
    Drop                  Chance      Price     EV/Boss
    ────────────────────────────────────────────────────
    Warden Heart          1/7264      119.9M    16.5K
    Scythe Blade          1/968       9.5M      9.8K
    Shard of Shredded     1/1815      11.1M     6.1K
    Smite VII             1/2075      7.5M      3.6K

  RNG Meter (1,500 XP/boss):
    Best target: Warden Heart (33.0 coins/XP)
    Meter value per boss:             49.5K ★

  Other Income:
    Scavenger 5 (lvl 1580):           2,844
    Champion X:                       5

  ─────────────────────────────────────────────────────
  Total Value/Boss:                   124.5K
  Profit/Boss (after cost):          +24.5K
  Est. kills/hr:                     8
  Profit/hr:                         ~196K

  Tier Comparison:
    Tier   Cost     Profit/Boss   Coins/XP    Profit/hr
    ─────────────────────────────────────────────────────
    T1     100      +450          90.0        54.0K
    T3     10K      +8.5K        85.0        340.0K
    T4     50K      +24.5K      49.0        367.5K  ← Best $/hr
    T5     100K     +24.5K      16.3        196.0K
```

### CLI Interface

```bash
python3 slayers.py                         # all slayer types, best tier summary
python3 slayers.py --type zombie           # detailed Revenant breakdown (all tiers)
python3 slayers.py --type zombie --tier 5  # detailed T5 Revenant
python3 slayers.py --type wolf --tier 4    # T4 Sven
python3 slayers.py --magic-find 200        # factor in Magic Find
python3 slayers.py --aatrox                # apply Aatrox mayor bonuses
python3 slayers.py --kills-per-hour 12     # override kill speed estimate
python3 slayers.py --json                  # machine-readable output
```

### Implementation Notes

- Port Luckalyzer's `slayer.json` for RNG drop probabilities and meter data (MIT licensed)
- Common/guaranteed drops need manual curation from wiki — store in `data/slayer_drops.json`
- Weighted Bazaar pricing: extend `pricing.py` or calculate in-tool from existing buy/sell/volume data
- NPC sell prices for certain items (Foul Flesh, etc.) — hardcode or grep wiki
- RNG meter XP per boss = slayer XP for that tier (same value)
- Scavenger coins depend on boss level per tier — store in tier data
- Aatrox detection: Hypixel API has election/mayor data, or use `--aatrox` flag
- Kill speed estimates are highly gear-dependent — provide sensible defaults but make overridable
- All 5 slayer types: Zombie (Revenant), Spider (Tarantula), Wolf (Sven), Enderman (Voidgloom), Blaze (Inferno). Vampire (Riftstalker) is the 6th but is Rift-exclusive with different mechanics — add later if relevant
- Common/guaranteed drop data needed for all 5 types — curate from wiki up front
- Magic Find weight calculation included via `--magic-find` flag
