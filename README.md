# Hypixel SkyBlock Toolkit

A collection of tools and resources for playing [Hypixel SkyBlock](https://wiki.hypixel.net/), built for personal use.

Includes a comprehensive beginner guide, a CLI profile analyzer with live market pricing, a local wiki mirror, and an Obsidian vault generator that cross-links game data for exploration.

## What's Here

### `guide/` — Beginner Guide

A single-page HTML guide covering SkyBlock from first spawn through mid-game. 34+ sections on everything from fairy souls to dungeon progression, money-making strategies, mod recommendations, and gear paths.

Features a dark theme, collapsible navigation with scrollspy, localStorage-backed checkboxes with a progress bar, and mobile support. Open `index.html` in a browser — no build step needed.

### `tools/` — Python Scripts

Four standalone scripts. No frameworks, no dependencies beyond the standard library. All use the Hypixel API v2 and/or local data.

**`profile.py`** — Fetches a SkyBlock profile from the Hypixel API and prints a detailed breakdown: skills, slayers, dungeons, mining, pets, gear (with full NBT decoding for reforges, enchants, stars, and hot potato books), active effects, and market values for equipped items. Supports 22 sections total — 8 core sections shown by default, 14 extended sections available with `--full` or `-s`.

```
python3 profile.py              # core sections
python3 profile.py --full       # everything
python3 profile.py -s dungeons,slayers,collections
```

**`pricing.py`** — Real-time item pricing from the Bazaar API and [Coflnet](https://sky.coflnet.com/) lowest BIN auctions. File-cached with configurable TTLs. Also works as a standalone CLI:

```
python3 pricing.py SHADOW_ASSASSIN_CHESTPLATE ENCHANTED_DIAMOND
```

**`wiki_dump.py`** — Mirrors the [Hypixel SkyBlock Wiki](https://wiki.hypixel.net/) to local `.wiki` files via the MediaWiki API. Supports incremental updates. Useful for grepping game mechanics offline.

```
python3 wiki_dump.py            # full dump (~4,800 pages)
python3 wiki_dump.py --update   # incremental
```

**`converter.py`** — Converts the [NEU-REPO](https://github.com/NotEnoughUpdates/NotEnoughUpdates-REPO) item database and the local wiki dump into an [Obsidian](https://obsidian.md/) vault with `[[wikilinks]]` between items, recipes, NPCs, and wiki pages. Produces ~12,000 interlinked markdown files for graph-view exploration of game data.

```
python3 converter.py            # full conversion
python3 converter.py --page "Coal"  # single page (debugging)
```

### `data/` — Reference Data (git-ignored)

Large and/or generated files that don't belong in version control. Everything here can be regenerated:

| Directory/File | Size | Source |
|---|---|---|
| `wiki/` | ~27 MB | `wiki_dump.py` |
| `neu-repo/` | ~82 MB | `git clone` from [NEU-REPO](https://github.com/NotEnoughUpdates/NotEnoughUpdates-REPO) |
| `vault/` | ~53 MB | `converter.py` (requires wiki + neu-repo) |
| `last_profile.json` | ~400 KB | `profile.py` (latest API response) |
| `price_cache.json` | ~300 KB | `pricing.py` (auto-managed cache) |

## Setup

1. Clone the repo and set up a Python venv:
   ```bash
   git clone https://github.com/alderban107/hypixel-skyblock.git
   cd hypixel-skyblock
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Create a `.env` file in the project root with your [Hypixel API key](https://developer.hypixel.net/):
   ```
   HYPIXEL_API_KEY=your-key-here
   MINECRAFT_USERNAME=your-ign
   ```

3. Populate the data directory:
   ```bash
   mkdir -p data
   cd tools
   python3 wiki_dump.py                    # download wiki
   cd ../data
   git clone https://github.com/NotEnoughUpdates/NotEnoughUpdates-REPO neu-repo
   cd ../tools
   python3 converter.py                    # generate obsidian vault
   ```

4. Run tools from the `tools/` directory:
   ```bash
   cd tools
   python3 profile.py
   ```

## License

This is a personal project. The wiki content and NEU-REPO data belong to their respective owners.
