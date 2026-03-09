---
name: skyblock
description: Fetch a Hypixel SkyBlock profile and provide live gameplay recommendations
allowed-tools: Bash(cd tools && python3 profile.py*), Bash(cd tools && python3 pricing.py*), Bash(cd tools && python3 crafts.py*), Bash(cd tools && python3 investments.py*), Bash(cd tools && python3 kat.py*), Bash(cd tools && python3 museum.py*), Bash(cd tools && python3 networth.py*)
---

# SkyBlock Profile Analyzer

When this skill is invoked:

1. **Run the profile script** to fetch live data from the Hypixel API:
   ```
   cd tools && python3 profile.py --full
   ```

2. **Read the raw JSON** for deeper analysis if needed:
   - `data/last_profile.json` contains full profile + garden + museum data

3. **Check live prices** for specific items when evaluating upgrades:
   ```
   cd tools && python3 pricing.py ITEM_ID ITEM_ID_2
   ```

4. **Check craft flips** for money-making opportunities:
   ```
   cd tools && python3 crafts.py --profile
   ```

5. **Check event investments** for buy/sell opportunities based on event cycles:
   ```
   cd tools && python3 investments.py
   ```

6. **Check Kat pet upgrade profits** for pet flipping opportunities:
   ```
   cd tools && python3 kat.py --scan
   cd tools && python3 kat.py RABBIT --from common --to mythic --shopping
   ```

7. **Check networth** for total profile value and modifier breakdown:
   ```
   cd tools && python3 networth.py
   cd tools && python3 networth.py --category pets
   cd tools && python3 networth.py --top 20
   ```

8. **Check museum donations** for cheapest missing items:
   ```
   cd tools && python3 museum.py
   cd tools && python3 museum.py --xp
   ```

9. **Grep the local wiki** to verify game mechanics before making claims:
   ```
   grep -ri "search term" data/wiki/
   ```
   The wiki is a local dump of the fandom wiki (hypixel-skyblock.fandom.com, ~6,200 pages of wikitext), actively maintained by community volunteers. Always check it before stating specifics about drop rates, recipe requirements, collection unlock thresholds, slayer mechanics, or dungeon requirements. Training data may be outdated — the wiki is kept current with `tools/wiki_dump.py --update`.

   **If `data/wiki/` is empty or doesn't exist**, tell the user to run the wiki dump first (`cd tools && python3 wiki_dump.py`) before you can verify game mechanics. Do not guess at specifics without wiki verification.

10. **Reference the beginner guide** at `guide/index.html` for progression advice. The guide contains curated gear paths, money-making strategies, mod recommendations, and section-by-section walkthrough content that has been hands-on verified. It covers topics not always on the wiki (e.g., optimal mod setups, budget-conscious upgrade paths, early-game money methods). Prefer its recommendations over generic wiki info when they overlap — but don't modify the guide unless asked.

11. **Analyze the profile and provide recommendations.** You ARE the recommendation engine — the script just fetches data for you to interpret.

## Analysis Checklist

Cover ALL of these areas, not just one or two. The user invokes this skill when they want a broad view of their profile and fresh ideas — not a deep dive into whatever was discussed earlier in the session.

- **Progression stage**: Where is the user in the game? Early/mid/late? What content are they ready for?
- **Skill gaps**: Any skills lagging behind? Quick wins to raise skill average?
- **Gear assessment**: Is current equipment appropriate for the user's level and next goals? The INVENTORIES section shows all equipped armor, equipment slots, inventory items, accessories, ender chest contents, and backpacks — use this to see exactly what they have before recommending anything. Use `pricing.py` to check current market values when evaluating upgrade options.
- **Minion optimization**: Are minions set up well? Missing easy crafts for slot unlocks?
- **Collections**: Any collections close to a meaningful tier unlock? Grep the wiki for collection tier thresholds rather than guessing.
- **Slayer/Dungeon readiness**: Ready to start or progress in slayers/dungeons? What gear/stats are needed? Check the wiki for floor requirements and slayer level unlock thresholds.
- **Pets**: Is the active pet optimal? Any pets worth getting for current activities?
- **Magical Power**: Is accessory bag power appropriate? Check the accessory bag AND ender chest for talismans that should be moved into the bag.
- **Money-making**: Run `crafts.py --profile` for craft flips, `investments.py` for event investments, and `kat.py --scan` for pet flip opportunities. Highlight the best current opportunities.
- **Museum**: Run `museum.py` to check cheapest missing donations. SkyBlock XP from museum milestones adds up.
- **Garden**: Progression status, worth investing time?

## Response Format

- Start with a quick status summary (stage, standout stats, immediate concerns)
- Give **3-5 prioritized actions** across different areas of the game, with clear reasoning
- Recommendations should be independent of what was discussed earlier in the session — the user typically invokes this skill when they want to switch objectives, so suggest variety
- When recommending upgrades, include live prices from `pricing.py` so the user can evaluate affordability
- Flag anything urgent (expiring items, easy wins being missed, gear that's holding them back)
- Suggest a longer-term direction based on where they're heading

## Important Context

- Fairy souls only give SkyBlock XP now, NOT stats. They must be exchanged in chunks of 5 — don't recommend spending them unless the user has 5+ unspent.
- **Do NOT recommend money farming or flag low purse/bank balance.** The Banking API often doesn't return data, so the purse value shown may be misleading — many players keep most coins in the bank. Treat money as a non-issue unless the user specifically asks about it.
- The local wiki dump is sourced from the fandom wiki (hypixel-skyblock.fandom.com) — always prefer grepping the local dump over web lookups
- If the API key has expired, check the dev key expiry or personal key approval status in `.env`
- **Check the INVENTORIES section carefully before recommending items.** Don't recommend talismans/gear the user already owns — they may be in the ender chest, backpack, or accessory bag.
- Don't push expensive consumables (like HPBs) on transitional gear that will be replaced soon
- **Always verify claims against the local wiki or beginner guide before stating them as fact.** If you're unsure about a mechanic, grep the wiki first.
