# Hypixel SkyBlock Project

Tools and resources for Hypixel SkyBlock gameplay.

## Structure

```
guide/          Static HTML beginner guide (index.html, script.js, style.css)
tools/          Python scripts (run from this dir or project root)
  items.py      Hypixel API resource data (items, skills, collections, requirements)
  profile.py    Fetch & display SkyBlock profile data
  pricing.py    Live Bazaar + Moulberry BIN + SkyHelper variant pricing (attribute rolls, skins, pet levels)
  flips.py      Unified flip scanner (craft, forge, kat, NPC, bits) with recursive cost optimization
  flip_engine.py  Flip engine — CostEngine, recipe parsing, scanner functions
  networth.py   Networth calculator (all storage locations, modifier pricing, soulbound)
  dungeons.py   Dungeon profit calculator (per-score-tier drops, RNG meter, Kismet analysis)
  dragons.py    Dragon profit calculator (EV per fight by dragon type, DragonLoot.json + live pricing)
  accessories.py Missing accessories finder (MP efficiency, upgrade chains, inactive detection)
  slayers.py    Slayer profit calculator (6 types incl. Bloodfiend, RNG meter via rngscore, MF/Aatrox)
  farming.py    Farming profit calculator (per-crop profit/hr, fortune scaling, NPC vs Bazaar)
  validate.py   Cross-validation vs Coflnet (crafts, Kat, fusions, forge — flags divergences)
  kat.py        Kat upgrade calculator (materials, coins, time, shopping lists)
  sbxp.py       SkyBlock XP analyzer — 23 formula sources, 692 tasks, smart recs (essence/collections/garden)
  minions.py    Minion profit calculator (live Bazaar pricing, 50+ minion types)
  investments.py Event investment tracker (buy low during events, sell high between)
  wiki_dump.py  Dump fandom wiki to local .wiki files + parse to text
data/           Reference data and generated output
  wiki/         Local wiki dump (~6,200 pages, raw wikitext from fandom wiki)
  wiki/parsed/  Parsed text with templates expanded (grep this for data lookups)
  neu-repo/     NotEnoughUpdates item/recipe data (git clone)
  external/     Third-party data files (SkyHanni, skyblock-plus-data — DungeonLoot, DragonLoot, SlayerItems, etc.)
  last_profile.json   Latest profile API fetch
  dungeon_loot.json   Cached wiki dungeon loot tables (24hr TTL, --wiki fallback only)
  sbxp_tasks.json    SBXP task database (23 formula sources + 692 individual tasks across 17 categories)
  slayer_drops.json  Slayer drop data (6 types incl. Bloodfiend, Luckalyzer RNG + SkyHanni drops)
  price_cache.json    Cached market prices
  external/BitPrices.json       Bits shop item costs (skyblock-plus-data)
  external/power_stats.json     Maxwell power base stats (skyblock-plus-data POWER_TO_BASE_STATS)
  external/farming_weight.json  EliteFarmers farming weight constants
  craft_cache.json    Cached craft flip data (Moulberry)
.env            API credentials (HYPIXEL_API_KEY)
```

## Running Tools

All scripts are in `tools/`. Run from that directory:

```bash
cd tools
python3 profile.py                          # core sections
python3 profile.py --full                   # all sections
python3 profile.py -s dungeons,collections  # specific sections
python3 profile.py -s weight                # Senither + Lily + Farming weight
python3 pricing.py SHADOW_ASSASSIN_CHESTPLATE ENCHANTED_DIAMOND
python3 pricing.py "RABBIT;4"              # pet by ID
python3 pricing.py "rabbit legendary"       # pet by name + rarity
python3 pricing.py rabbit                   # all pet rarities
python3 flips.py                            # all flip types (craft, forge, kat, NPC, bits)
python3 flips.py craft                      # craft flips only
python3 flips.py forge                      # forge flips only (sorted by profit/hour)
python3 flips.py sell-order                 # bazaar sell-order flips (patient flipping)
python3 flips.py kat                        # Kat pet upgrade flips
python3 flips.py npc                        # NPC buy → market sell
python3 flips.py bits                       # bit shop value ranking (coins/bit)
python3 flips.py --profile                  # filter by player's unlocked recipes
python3 flips.py --no-recursive             # disable recursive craft cost optimization
python3 flips.py --all-liquidity            # include illiquid flips (<0.5 sales/day)
python3 flips.py --cached                   # use cached prices only (no API calls)
python3 flips.py --fresh                    # ignore cache, fetch all prices fresh
python3 flips.py --undercut 8               # set undercut % below LBIN (default: 5%)
python3 flips.py --item PERSONAL_COMPACTOR_4000         # recipe breakdown with recursive costs
python3 flips.py --item REFINED_MITHRIL                 # forge recipe breakdown with profit/hr
python3 flips.py --item PERSONAL_COMPACTOR_4000 --check # + requirement check vs profile
python3 networth.py                    # full networth breakdown
python3 networth.py --category pets    # just pets breakdown
python3 networth.py --top 20          # top 20 most valuable items
python3 networth.py --no-cosmetic     # exclude cosmetic items
python3 networth.py --json            # machine-readable output
python3 networth.py --verbose         # list every item with price
python3 dungeons.py                           # all floors summary (S+D5 score tier)
python3 dungeons.py --floor f7                # detailed F7 breakdown
python3 dungeons.py --floor m5                # Master Mode 5
python3 dungeons.py --score s+a3              # specific score tier (SA1-SD5, S+A1-S+D5)
python3 dungeons.py --score sd5               # S grade (instead of S+)
python3 dungeons.py --no-splus                # shortcut for --score SD5
python3 dungeons.py --runs-per-hour 6         # override runs/hr estimate
python3 dungeons.py --json                    # machine-readable output
python3 dungeons.py --wiki                    # use wiki data instead of DungeonLoot.json
python3 dungeons.py --wiki --refresh          # force re-scrape wiki data
python3 accessories.py                    # full missing accessories report
python3 accessories.py --budget 10m       # only show within 10M total budget
python3 accessories.py --sort cost        # sort by absolute cost instead of coins/MP
python3 accessories.py --upgrades-only    # only show upgrade opportunities
python3 accessories.py --inactive         # focus on inactive/duplicate cleanup
python3 accessories.py --available-only   # hide locked/unobtainable
python3 accessories.py --json             # machine-readable output
python3 slayers.py                         # all 6 slayer types summary + tier comparisons
python3 slayers.py --type zombie           # detailed Revenant breakdown (best tier)
python3 slayers.py --type zombie --tier 5  # detailed T5 Revenant
python3 slayers.py --type wolf --tier 4    # T4 Sven
python3 slayers.py --type vampire          # Riftstalker Bloodfiend (Rift-exclusive)
python3 slayers.py --magic-find 200        # factor in Magic Find
python3 slayers.py --aatrox                # apply Aatrox mayor bonuses
python3 slayers.py --kills-per-hour 12     # override kill speed estimate
python3 slayers.py --json                  # machine-readable output
python3 minions.py                          # ranked profit table, default setup (25× T11)
python3 minions.py --item snow --roi        # detailed breakdown + setup cost + ROI
python3 minions.py --tier 12 --top 10       # top 10 T12 minions
python3 minions.py --fuel plasma            # change fuel type
python3 minions.py --no-sc3000 --npc        # raw NPC pricing, no compactor
python3 minions.py --sort roi --top 15      # sort by ROI, show top 15
python3 minions.py --list                   # list all available minion types
python3 minions.py --slots                  # cheapest crafts for next minion slot unlock
python3 items.py TARANTULA_TALISMAN        # show requirements from API + NEU
python3 kat.py RABBIT                       # all Kat upgrade paths + costs
python3 kat.py RABBIT --from uncommon --to legendary           # specific range
python3 kat.py RABBIT --from common --to legendary --profit    # include profit analysis
python3 kat.py RABBIT --profit              # single pet with profit analysis
python3 kat.py SKELETON --shopping          # consolidated shopping list (craft + Kat materials)
python3 kat.py RABBIT --from common --to mythic --shopping     # shopping list with range
python3 sbxp.py                           # full SBXP analysis + recommendations
python3 sbxp.py --brief                   # recommendations only
python3 sbxp.py --category mining         # filter by category (mining, dungeons, etc.)
python3 sbxp.py --json                    # raw JSON output for scripting
python3 investments.py                      # event investment recommendations (Coflnet history)
python3 investments.py --calendar           # SkyBlock calendar + upcoming events
python3 investments.py --event spooky       # detail view for one event
python3 investments.py --history GREEN_CANDY # price history for one item
python3 dragons.py                          # all dragon types summary (EV per fight)
python3 dragons.py --type superior          # detailed Superior Dragon breakdown
python3 dragons.py --eyes 4                 # assume 4 eyes placed (affects cost)
python3 dragons.py --json                   # machine-readable output
python3 farming.py                          # all crops profit/hr (default 100 fortune)
python3 farming.py --fortune 500            # set farming fortune
python3 farming.py --crop wheat             # detailed wheat breakdown
python3 farming.py --profile                # auto-detect fortune from profile
python3 farming.py --npc                    # show NPC sell prices in summary
python3 farming.py --bps 25                 # override blocks/second
python3 validate.py                         # run all validations vs Coflnet
python3 validate.py --crafts                # craft profits only
python3 validate.py --kat                   # Kat upgrade profits only
python3 validate.py --fusions               # shard fusion profits only
python3 validate.py --forge                 # forge recipe profits only
python3 validate.py --threshold 30          # flag divergences >30% (default: 20%)
python3 wiki_dump.py --update               # incremental wiki update
python3 wiki_dump.py --parse                # generate parsed text (expands templates, ~80 min)
python3 wiki_dump.py --update --parse       # update + re-parse changed pages
```

## Important Rules

- **Grep `data/wiki/parsed/` first** for data lookups (costs, stats, recipes) — templates are expanded there. Fall back to `data/wiki/` for structural/wikitext queries. If a parsed file doesn't exist for a page, check the raw wikitext. The local wiki dump is sourced from the fandom wiki (hypixel-skyblock.fandom.com), which is actively maintained by community volunteers.
- **ALWAYS grep the local wiki** before making game mechanics claims or recommendations. Don't rely on training data for SkyBlock specifics — it may be outdated.
- **For collection tier data, use the Hypixel API** (`https://api.hypixel.net/v2/resources/skyblock/collections`, no key needed) — NOT the wiki. The wiki's Collections page is stale (e.g. still shows pre-PETv2 recipe unlock tiers). The API is authoritative. Cached locally at `data/collections_resource.json`.
- **Bazaar purchases don't count** toward collections — materials must be gathered manually.
- **Don't push expensive upgrades** without context on the player's budget.
- **Always verify claims** against the local wiki or beginner guide before stating them as fact. If unsure about a mechanic, grep the wiki first.
