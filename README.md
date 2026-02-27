# Hypixel SkyBlock Toolkit

A collection of tools and resources for playing [Hypixel SkyBlock](https://wiki.hypixel.net/).

[Hypixel SkyBlock](https://hypixel.net/) is an MMORPG-style game mode on Minecraft's largest multiplayer server. Players progress through skills, gear, dungeons, bosses, and a player-driven economy with two distinct markets: the **Bazaar** (bulk commodity exchange with instant buy/sell orders) and **Auctions** (player-to-player item sales, typically using "Buy It Now" fixed prices). Equipment in SkyBlock has hidden properties — reforges, enchantments, star upgrades, hot potato books — stored as compressed [NBT](https://minecraft.wiki/w/NBT_format) data in the API, which the tools here decode and display.

This repo includes a beginner guide, a CLI profile analyzer with live market pricing, a craft flip scanner, an event investment tracker, a local wiki mirror, and an Obsidian vault generator that cross-links game data for graph-view exploration.

## What's Here

### `guide/` — Beginner Guide

A single-page HTML guide covering SkyBlock from first spawn through mid-game. Open `index.html` in a browser — no build step needed.

**Important**: As of late 2025, Hypixel requires **Minecraft 1.21.9+**. Older guides teaching 1.8.9 Forge + NEU are obsolete. This guide covers modern **Fabric 1.21.10** with the current mod ecosystem (Skyblocker, SkyHanni, Firmament).

Content is organized into tabbed pages with auto-generated navigation:

- **Getting Started** — Mod installation, texture packs, first-day checklist, staying safe
- **Core Systems** — Skills (12 types), stats, profiles, collections, bestiary, museum
- **Early Progression** — Accessories/magic power, equipment slots, fairy souls, minions, garden
- **Content Areas** — Enchanting, sacks, chocolate factory, slayers (each type individually), dungeons (floor-by-floor), mining/HotM, Rift, Diana, Crimson Isle, events
- **Economy & Meta** — Money-making strategies (NPC flipping, Bazaar, crafting), mayors, pets
- **Skill Guides** — Detailed leveling guides for all 12 skills
- **Reference** — Gear progression tables, tips, external links

Interactive features: localStorage-backed checkboxes with per-section progress tracking, collapsible scrollspy navigation, mobile hamburger menu, and a dark enchanting-purple theme.

### `tools/` — Python Scripts

Six standalone scripts. No dependencies beyond the standard library. Run from the `tools/` directory (scripts import from each other via relative imports).

---

**`profile.py`** — Fetches a player's SkyBlock profile from the [Hypixel API v2](https://api.hypixel.net/) and prints a comprehensive breakdown. Decodes base64-gzip NBT inventory blobs to extract item details (reforges, enchantments with levels, star count, hot potato book count, rarity) for every equipped item, accessory, wardrobe slot, ender chest item, and backpack.

Output is organized into 23 sections — 8 core shown by default, 15 extended available on request:

| Core (default) | Extended (`--full` or `-s`) |
|---|---|
| general, skills, slayers, dungeons | collections, minions, garden, museum |
| hotm, effects, pets, inventories | rift, sacks, jacob, crystals |
| | bestiary, stats, foraging, chocolate |
| | community, misc, crafts |

Also includes:
- **Market prices** for all equipped gear and weapons, with total accessory bag value (top 5 most expensive shown)
- **Upgrade suggestions** based on current gear tier — filters out items the player already owns and shows live prices for each recommendation
- **Raw JSON export** to `data/last_profile.json` with full profile data, garden, museum, and cached market prices for further analysis

```bash
python3 profile.py                          # core sections
python3 profile.py --full                   # all 22 sections
python3 profile.py -s dungeons,collections  # specific sections
```

---

**`pricing.py`** — Real-time item pricing with two sources and automatic fallback:

1. **Bazaar API** (Hypixel) — bulk commodity prices with buy/sell spread and volume data. Fetched in a single API call for all items. Cached for 5 minutes.
2. **Coflnet API** — lowest BIN (Buy It Now) auction prices for gear and rare items. Fetched per-item with rate limiting (1 request per 0.6s to stay under 100/min). Cached for 10 minutes.

Items are looked up on the Bazaar first; if not found there, falls back to Coflnet auction data. Failed lookups (404s) are also cached to avoid repeated requests. Cache is stored in `data/price_cache.json`.

```bash
python3 pricing.py SHADOW_ASSASSIN_CHESTPLATE ENCHANTED_DIAMOND
```

Also used as a library — `profile.py` imports `PriceCache` directly for inline market valuations.

---

**`crafts.py`** — Scans for profitable **craft flips**: items where bazaar-bought ingredients can be crafted into items that sell on the Auction House for more than the material cost. Parses all crafting recipes from the NEU-REPO item database, prices ingredients using the Bazaar API (`quick_status.buyPrice`), and fetches auction house prices from [Moulberry's](https://moulberry.codes/) bulk APIs (3-day averaged lowest BIN, current lowest BIN, and actual sales volume) in three fast requests.

Filters to items where all ingredients are available on the Bazaar and the output is sold on the AH (not the Bazaar). Uses current lowest BIN for profit calculation (what you'd undercut to sell), real sales data for volume filtering, and shows 3-day averaged lowest BIN for reference. Calculates profit after the 1% AH tax. Minimum thresholds: 10K profit and 1 sale/day.

Each item's unlock requirement (collection tier, slayer level, HotM level) is parsed from the NEU-REPO data and resolved against the Hypixel collections API for actual tier thresholds.

```bash
python3 crafts.py              # full scan — all profitable crafts (~5 sec)
python3 crafts.py --profile    # filter by player's unlocked recipes (reads last_profile.json)
python3 crafts.py --cached     # use cached prices only (no API calls)
python3 crafts.py --fresh      # ignore cache, fetch all prices fresh
```

Price data is cached in `data/craft_cache.json` (5-minute TTL, 1-hour eviction). The `--profile` mode cross-references the player's collections and slayer XP to show which crafts are unlocked and which are closest to unlocking.

Also used as a library — `profile.py` imports craft scanning functions for the `crafts` section.

---

**`investments.py`** — Event-driven investment tracker that identifies buy/sell opportunities based on SkyBlock's recurring event cycle. Each event creates predictable price swings through one of three mechanisms:

- **Flood during** — The event produces items as drops/rewards, flooding supply and crashing prices. Buy during the event when prices bottom out, sell between events when supply dries up. *(e.g. Bat Person armor from Spooky Festival bosses, Snow Suit from Jerry's gifts)*
- **Demand during** — The event creates demand for consumable items, spiking prices while it's active. Buy between events when nobody needs the items, sell during the event when demand peaks. *(e.g. Green/Purple Candy — players buy it to earn Spooky Festival rewards)*
- **Demand before** — Players buy materials in anticipation of an upcoming event, driving prices up before it starts. Buy well after the event when demand fades, sell in the lead-up. *(e.g. enchanted meat/fish before the Traveling Zoo for pet leveling)*

All historical price data is fetched on-demand from [Coflnet](https://sky.coflnet.com/) — no background jobs, cron, or local data accumulation needed. For bazaar items, Coflnet's resolution scales with the requested time range (5-minute data for short windows, 2-hour for 7 days, daily for 30 days). The script automatically fetches high-resolution windows around short events (like the 1-hour Spooky Festival) so that price spikes are captured, while using the broad 30-day range for overall trends. AH items use the monthly price aggregation endpoint (daily min/max/avg/volume). Current prices come from the Hypixel Bazaar API and Moulberry's lowest BIN data.

Includes a SkyBlock calendar system that converts real-world time to in-game dates (epoch: June 11, 2019; 1 SB year = 124 real hours) to determine event timing and cycle position. For each tracked item, the script compares current price against historical event-period and off-event averages, then generates BUY/SELL/HOLD/WATCH recommendations with expected profit percentages.

Tracks 46 items across 6 events:

| Event | Schedule | Items | Pattern |
|---|---|---|---|
| Spooky Festival | Autumn 29-31 | Candy (bazaar) | Demand during — buy off-event, sell during |
| | | Bat Person armor, Spooky armor, Spooky Shard (AH) | Flood during — buy during event, sell off-event |
| Jerry's Workshop | Late Winter 1-31 | Gifts, Snow Suit, Nutcracker armor, Yeti Sword | Flood during |
| Hoppity's Hunt | Early Spring 1-31 | Chocolate items | Flood during |
| Traveling Zoo | Early Summer/Winter 1-3 | Enchanted meat/fish (pet materials) | Demand before — buy off-event, sell pre-event |
| Fishing Festival | Mayor-dependent (Marina) | Shark fins, shark teeth | Flood during |
| Mining Fiesta | Mayor-dependent (Cole) | Refined Mineral, Glossy Gemstone | Flood during |

```bash
python3 investments.py                      # recommendations (fetches 30-day history, ~30 sec)
python3 investments.py --calendar           # SkyBlock calendar + upcoming event countdowns
python3 investments.py --event spooky       # detail view for one event with item prices
python3 investments.py --history GREEN_CANDY # price history table for one item
```

---

**`wiki_dump.py`** — Mirrors the [Hypixel SkyBlock Wiki](https://wiki.hypixel.net/) to local `.wiki` files via the MediaWiki API (GET-only — POST is blocked by Cloudflare). Saves each page as an individual wikitext file.

Three modes:

```bash
python3 wiki_dump.py              # full dump (~4,800 content pages + ~42 data templates)
python3 wiki_dump.py --update     # incremental (only pages changed since last dump)
python3 wiki_dump.py --templates  # only Template:Data/* pages
```

Incremental updates check the wiki's `recentchanges` API for pages modified since the last sync timestamp (stored in `data/wiki/.dump_meta.json`). Requires a previous full dump. Requests are rate-limited to 1/second to respect the wiki's servers.

Page titles with special characters are sanitized for the filesystem (slashes become `_SLASH_`, etc.). Content pages come from namespace 0 (excluding redirects), templates from namespace 10 with prefix `Data/`.

---

**`converter.py`** — Converts two data sources into an interconnected [Obsidian](https://obsidian.md/) vault:

- [**NEU-REPO**](https://github.com/NotEnoughUpdates/NotEnoughUpdates-REPO) — a community-maintained database of every SkyBlock item as individual JSON files, plus constant files for essence costs, reforges, enchantments, pets, and leveling XP tables. One markdown file is generated per item (~10,000+).
- **Local wiki dump** — the wikitext pages from `wiki_dump.py`. Each page is converted from MediaWiki markup to markdown (~4,800 files). Handles bold/italic, headings, internal/external links, HTML tags, MediaWiki table syntax (`{| |}` to markdown tables), Minecraft color codes, and categories (extracted to YAML frontmatter tags).

Cross-linking uses a three-tier ID resolution system (NEU display names < wiki secondary params < wiki `|item=` params) to convert internal IDs like `SHADOW_ASSASSIN_CHESTPLATE` into `[[Shadow Assassin Chestplate]]` wikilinks that Obsidian can follow.

The converter handles 15+ page-level templates (Item Page, Armor Page, NPC Page, Mob Page, etc.), 20+ inline templates (recipes as 3x3 grids, forge recipes with durations, coin formatting, stat formatting, rarity badges, zone/NPC links), and MediaWiki table conversion with pipe escaping inside wikilinks. Template recursion is capped at 200 iterations.

Output includes a pre-configured `.obsidian/app.json` (wikilinks enabled, frontmatter visible).

```bash
python3 converter.py               # full conversion (~12,000 files)
python3 converter.py --wiki-only   # only wiki pages
python3 converter.py --items-only  # only NEU items
python3 converter.py --page "Coal" # single page (debugging)
```

### `data/` — Reference Data (git-ignored)

Large and/or generated files that don't belong in version control. Everything here can be regenerated with the tools above:

| Path | Size | Source | Contains |
|---|---|---|---|
| `wiki/` | ~27 MB | `wiki_dump.py` | 4,800+ `.wiki` files + `.dump_meta.json` |
| `neu-repo/` | ~82 MB | [git clone](https://github.com/NotEnoughUpdates/NotEnoughUpdates-REPO) | Item JSONs, constants, recipes |
| `vault/` | ~53 MB | `converter.py` | ~12,000 interlinked `.md` files for Obsidian |
| `collections_resource.json` | ~180 KB | [Hypixel API](https://api.hypixel.net/v2/resources/skyblock/collections) | Collection tier thresholds (no key needed) |
| `last_profile.json` | ~400 KB | `profile.py` | Latest API fetch (profile, garden, museum, prices) |
| `price_cache.json` | ~300 KB | `pricing.py` | Bazaar + auction price cache with TTL timestamps |
| `craft_cache.json` | ~240 KB | `crafts.py` | Moulberry bulk price data + collection data cache |
| `display_names.json` | ~244 KB | `pricing.py` | Item ID → display name mapping from NEU-REPO |

## Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/alderban107/hypixel-skyblock.git
   cd hypixel-skyblock
   ```

2. Create a `.env` file in the project root with your [Hypixel API key](https://developer.hypixel.net/):
   ```
   HYPIXEL_API_KEY=your-key-here
   MINECRAFT_USERNAME=your-ign
   ```

3. Populate the data directory:
   ```bash
   mkdir -p data

   # Download wiki (~5 min, rate-limited)
   cd tools && python3 wiki_dump.py && cd ..

   # Clone NEU item database
   git clone https://github.com/NotEnoughUpdates/NotEnoughUpdates-REPO data/neu-repo

   # Generate Obsidian vault (requires both wiki + neu-repo)
   cd tools && python3 converter.py && cd ..
   ```

4. Run tools from the `tools/` directory:
   ```bash
   cd tools
   python3 profile.py
   python3 pricing.py ASPECT_OF_THE_END
   ```

No pip packages required — everything uses the Python standard library.

## Claude Code Skill

This repo includes a [Claude Code skill](https://docs.anthropic.com/en/docs/claude-code/skills) that turns `/skyblock` into an AI-powered profile analyzer. When invoked, Claude fetches your live profile data, cross-references the local wiki, checks current market prices, and gives prioritized gameplay recommendations.

### Installing the Skill

1. Complete the setup steps above (API key, wiki dump)

2. Copy the skill file to your Claude Code skills directory:
   ```bash
   mkdir -p ~/.claude/skills/skyblock
   cp SKILL.md ~/.claude/skills/skyblock/SKILL.md
   ```

3. Open Claude Code from the project root and type `/skyblock`

### Prerequisites

- **Hypixel API key** — Apply at [developer.hypixel.net](https://developer.hypixel.net/). Approval is not instant; dev keys may take a few days.
- **Local wiki dump** — The skill relies on grepping the wiki to verify game mechanics before making claims. Without it, recommendations may be less accurate. Run `cd tools && python3 wiki_dump.py` (~5 min, rate-limited to 1 req/sec).
- **Claude Code working directory** — The skill uses relative paths, so Claude Code must be opened from the project root.

### Customization

The `SKILL.md` file's "Important Context" section controls how Claude approaches recommendations. You can edit your local copy to match your playstyle — for example, adding notes about your budget preferences, which content you enjoy, or specific goals you're working toward.

## License

This is a personal project. The wiki content belongs to [Hypixel](https://hypixel.net/) and the NEU-REPO data belongs to the [NotEnoughUpdates](https://github.com/NotEnoughUpdates) contributors.
