---
name: skyblock
description: Fetch a Hypixel SkyBlock profile and provide live gameplay recommendations. Use this skill whenever the user asks about their SkyBlock progression, gear upgrades, money-making, dungeon readiness, skill levels, minions, collections, slayers, mining, rift progress, or wants a profile checkup — even if they don't say "profile" explicitly. Also use when they ask what to do next in SkyBlock or wants fresh recommendations.
compatibility: Requires Python 3, Hypixel API key in ~/projects/hypixel-skyblock/.env, local wiki dump in data/wiki/, NEU repo in data/neu-repo/
---

# SkyBlock Profile Analyzer

## Tools & Data Sources

**Profile data:**
```
cd ~/projects/hypixel-skyblock/tools && python3 profile.py --full
```
Raw JSON at `~/projects/hypixel-skyblock/data/last_profile.json` if you need to dig deeper.

**Live prices:**
```
cd ~/projects/hypixel-skyblock/tools && python3 pricing.py ITEM_ID ITEM_ID_2
```
Use Hypixel internal IDs, not display names. Some are non-obvious: Necron = `POWER_WITHER_*`, Goldor = `TANK_WITHER_*`, Storm = `WISE_WITHER_*`, Maxor = `SPEED_WITHER_*`. If pricing returns nothing for an item you know exists, the ID is wrong — check `data/neu-repo/items/` or search Coflnet: `curl -s 'https://sky.coflnet.com/api/item/search/QUERY'`. If price data is genuinely missing, say so rather than silently omitting.

**Local wiki** at `~/projects/hypixel-skyblock/data/wiki/` (~6,200 pages of wikitext from hypixel-skyblock.fandom.com). Grep this for game mechanics — drop rates, collection thresholds, recipe requirements, slayer mechanics, dungeon requirements. Training data is unreliable for SkyBlock; the wiki is kept current with `wiki_dump.py --update`.

**Beginner guide** at `~/projects/hypixel-skyblock/guide/index.html`. Curated gear paths, money-making strategies, progression advice. Cross-reference gear recommendations against this before suggesting upgrades. Activity-specific sections at `#sg-{skill}` (e.g., `#sg-mining`).

**NEU repo** at `data/neu-repo/`:
- `items/ITEM_ID.json` — recipes, lore, skill requirements. Only ~26% of items have recipes; drops won't have one.
- `constants/essencecosts.json` — star upgrade costs for 528 items
- `constants/reforges.json` — 50 reforges with stat breakdowns by rarity
- `constants/reforgestones.json` — 79 stones with item type mappings. **Skill requirements are in Roman numerals** in the lore — convert before comparing against the player's levels.
- `constants/enchants.json`, `constants/pets.json`, `constants/leveling.json`

**SBXP analysis:**
```
cd ~/projects/hypixel-skyblock/tools && python3 sbxp.py
```
Full SkyBlock XP breakdown — 25 formula-based calculators (skills, fairy souls, MP, pets, collections, minions, dungeons, slayers, bestiary, mining, garden, museum) + 692 individual tasks (harp songs, essence shop, trophy fish, event perks, abiphone contacts, dojo, timecharms, objectives, etc.). Smart recommendations cross-reference essence stockpiles vs shop costs, find close collection milestones, and surface garden quick wins. Use `--brief` for just recommendations, `--category X` to filter, `--json` for scripting. Task database at `data/sbxp_tasks.json`.

**Craft flips:** The profile output includes a `CRAFT FLIPS` section showing profitable crafts the player has unlocked and ones they're close to unlocking. For a fresh check, run `crafts.py --profile`.

**Accessory upgrades:**
```
cd ~/projects/hypixel-skyblock/tools && python3 accessories.py
```
Finds all missing accessories ranked by coins/MP efficiency. Shows upgrade paths (e.g. Ring → Artifact) and flags what you already own. Use when evaluating MP upgrades or wondering what accessory to buy next.

**Dungeon profit:**
```
cd ~/projects/hypixel-skyblock/tools && python3 dungeons.py
cd ~/projects/hypixel-skyblock/tools && python3 dungeons.py --floor f6
cd ~/projects/hypixel-skyblock/tools && python3 dungeons.py --score s+d3
```
Per-floor profit breakdown with chest recommendations (which to open, which to skip), kismet feather analysis, and RNG meter targets ranked by coins/XP. Summary view ranks all floors by hourly rate. Use when deciding which floor to grind or whether to open chests.

**Slayer profit:**
```
cd ~/projects/hypixel-skyblock/tools && python3 slayers.py
```
Per-slayer, per-tier profit analysis showing profit/boss, profit/hr, and coins/XP. Identifies the best tier for each slayer type. Use when deciding which slayer to do or which tier is most efficient.

**Minion profit:**
```
cd ~/projects/hypixel-skyblock/tools && python3 minions.py
cd ~/projects/hypixel-skyblock/tools && python3 minions.py --slots 9 --tier 7
```
Ranks all minion types by daily profit. Defaults to T11 with optimal setup (SC3000, Diamond Spreading, E-Lava). Use `--slots` and `--tier` to match the player's actual setup. Use when optimizing minion layout.

**Museum donations:**
```
cd ~/projects/hypixel-skyblock/tools && python3 museum.py
```
Lists all missing museum donations sorted by cost, showing the cheapest items to donate next. Use when the player wants to increase museum progress efficiently.

**Shard fusions:**
```
cd ~/projects/hypixel-skyblock/tools && python3 shards.py
cd ~/projects/hypixel-skyblock/tools && python3 shards.py chain <name>
cd ~/projects/hypixel-skyblock/tools && python3 shards.py farm
```
Shard fusion advisor — ranks farmable shards by chain value, shows cheapest fillers per rarity, identifies dead markets to avoid. Use when the player is doing shard content or asking about fusion profitability.

**Dragon fight EV:**
```
cd ~/projects/hypixel-skyblock/tools && python3 dragons.py
cd ~/projects/hypixel-skyblock/tools && python3 dragons.py --type superior --eyes 4
```
Expected value per fight by dragon type, using DragonLoot.json drop tables + live pricing. Shows net profit after eye cost.

**Farming profit:**
```
cd ~/projects/hypixel-skyblock/tools && python3 farming.py --profile
cd ~/projects/hypixel-skyblock/tools && python3 farming.py --fortune 500
cd ~/projects/hypixel-skyblock/tools && python3 farming.py --crop wheat
```
Per-crop profit/hr with fortune scaling. Compares NPC vs Bazaar (raw and enchanted) sell methods. `--profile` auto-detects farming fortune.

**Forge flips:**
```
cd ~/projects/hypixel-skyblock/tools && python3 forge.py --profile
cd ~/projects/hypixel-skyblock/tools && python3 forge.py --hotm 5 --quick-forge 20
cd ~/projects/hypixel-skyblock/tools && python3 forge.py --item TITANIUM_DRILL_1
```
Forge recipe profitability from Coflnet data, sorted by profit/hour. Filters by HotM level, applies Quick Forge time reduction. `--profile` auto-detects HotM level.

**Net worth:**
```
cd ~/projects/hypixel-skyblock/tools && python3 networth.py
cd ~/projects/hypixel-skyblock/tools && python3 networth.py --verbose
cd ~/projects/hypixel-skyblock/tools && python3 networth.py --category pets
```
Full networth breakdown by category (purse, bank, inventory, armor, accessories, wardrobe, pets, museum, sacks, storage, essence). Values soulbound items via recursive craft cost. Shows top N most valuable items with component breakdown (base, stars, HPB, enchants, reforge, etherwarp). `--verbose` lists every priced item, `--category` filters to one category, `--no-cosmetic` excludes dyes/skins/runes.

**Cross-validation:**
```
cd ~/projects/hypixel-skyblock/tools && python3 validate.py
cd ~/projects/hypixel-skyblock/tools && python3 validate.py --forge --threshold 30
```
Cross-validates our pricing against Coflnet for crafts, Kat upgrades, fusions, and forge recipes. Use when pricing seems off or to sanity-check recommendations.

## How to Analyze

Run the profile, read the output, and think about what's actually useful to tell the player right now. You're the recommendation engine — the script just fetches data.

Look at the whole profile. Skills, gear, dungeons, slayers, collections, minions, pets, mining, foraging, Rift, garden, chocolate factory, museum, bestiary, active effects, sacks, contests — whatever's relevant. Don't tunnel-vision on one area. This skill is invoked when the player wants a broad view and fresh ideas, not a rehash of what was already discussed in the session.

For money-making analysis, use the full toolkit: `crafts.py --profile` for craft flips, `forge.py --profile` for forge flips, `farming.py --profile` for crop profit, `dragons.py` for dragon fight EV, `kat.py --scan` for pet flips, `dungeons.py` for dungeon chest profit, `slayers.py` for slayer tier efficiency, `shards.py` for fusion profitability. Compare across methods to recommend the best options for the player's current stage. Use `validate.py` if any pricing looks suspicious.

For upgrade questions, use `accessories.py` for MP-efficient accessory upgrades, `minions.py` for minion optimization, and `museum.py` for cheap donations.

Give **actionable recommendations** — things the player can do right now or work toward. Prioritize by impact. If they're broke, money-making comes first (you can't buy upgrades with an empty purse). Free daily wins are always worth mentioning. Don't pad with filler recommendations; if there are 3 good things to say, say 3.

Include prices when recommending purchases so the player can evaluate affordability. The Banking API doesn't work for all profiles, so the purse is the only visible number — it's a floor, not the whole picture.

## Things That Have Gone Wrong Before

These are corrections from past sessions. They're here because I got them wrong at least once:

**Don't recommend things the player can't do.** Check coins, skill levels, quest prerequisites, collection tiers, and unlock gates before suggesting anything. Reforge stones have skill requirements hidden in Roman numerals in the NEU repo. If something is gated, either note what it takes to clear the gate or suggest something else.

**Don't recommend things the player already has.** The INVENTORIES section shows armor, equipment, inventory, accessories, ender chest, and backpacks. Read it before suggesting gear or talismans.

**Don't judge items by rarity alone.** "Epic > Uncommon" is not analysis. Grep the wiki for both items and compare actual stats. Lower-rarity items can be better for specific content.

**Don't call accessory duplicates "extras" without checking.** Many accessories are tiered (Talisman → Ring → Artifact) and multiple copies of lower tiers are crafting materials for upgrades. Check the wiki or NEU repo for upgrade paths before suggesting the player sell or trash copies.

**Don't trust training data for SkyBlock mechanics.** Always verify against the wiki or NEU repo before making claims about drop rates, recipes, collection thresholds, or how game systems work.

**Don't describe garden farming as passive/AFK.** It's active gameplay — the player has to manually farm crops.

**Fairy souls give SkyBlock XP and Backpack Slots**, not stats. Exchanged at Tia in chunks of 5.

**Skill caps vary.** Farming goes to 60 (via Gold Medals/Anita), Taming to 60 (Pet Collector/George), Foraging to 54 (Agatha + collection). The profile script shows the actual max. Don't confuse NEU repo base caps (50) with the real ceiling.

**Chronomatron bonus clicks** are automatically consumed during the next Superpairs round. They're not a separate claimable thing. Don't tell the player to "claim" them. **Players typically do Chronomatron (add-on) before Superpairs** — if the profile says "add-on not done", it may just mean they haven't done their experiments yet today. Don't recommend doing add-ons as if they're being skipped.

**MP is low priority.** Don't default to recommending accessory bag expansion or talisman shopping as a top action. Only flag MP if it's severely behind the player's progression stage.

**Don't push expensive consumables on transitional gear.** Respect the player's budget — they will replace gear as they progress.

**Commit to recommendations.** Players want clear reasoning, not hedging. Present options when there are genuine tradeoffs, but don't waffle when you have a clear best pick.

**Quiver arrows all show as generic `ARROW` in the API.** The item ID doesn't distinguish between arrow types (flint, spectral, etc.). Don't assume the player is using plain arrows or recommend arrow upgrades based on quiver data alone.

## Subagent Rules

Subagents don't see this skill file. When delegating SkyBlock research, tell them to verify claims by grepping `~/projects/hypixel-skyblock/data/wiki/`. Never present subagent output directly — verify key claims yourself first. Label web-sourced information and note whether you verified it against the wiki.

If the API key has expired, tell the player to check `~/projects/hypixel-skyblock/.env`.
