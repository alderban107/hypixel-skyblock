# Toolkit Hardening Plan

Comprehensive fix plan from a full live test of all 20 tools (2026-03-18).
Issues identified from two perspectives: a player using the tools directly,
and an agent consuming tool output to generate gameplay recommendations.

## Batch 1 — Data Integrity

These produce wrong recommendations if left unfixed.

### 1. `forge.py` — Duration unit conversion

**Problem:** Coflnet `/api/flip/forge` returns `duration` in seconds. The tool
assigns it directly to `duration_hours` without conversion. Every displayed
duration is 3,600× too long, and every profit/hour is 3,600× too low.

Will-o'-wisp shows as 1,800 days when it actually takes 12 hours. Mithril
Necklace shows as 150 days when it takes 1 hour. An agent reading this output
would dismiss forge entirely or actively steer a player away from what may be
one of the best money-making methods available to them.

**Fix:**
- Line 145: `duration_hours = entry.get("duration", 0)` →
  `duration_hours = entry.get("duration", 0) / 3600`
- Add comment: `# Coflnet returns duration in seconds; convert to hours`
- Add sanity guard after conversion: if any duration exceeds 720 hours (30
  days), print a warning to stderr — catches future API unit changes

**Validation:** After fix, Will-o'-wisp ≈ 12h, Mithril Necklace ≈ 1h, Divan's
Powder Coating ≈ 36h. Profit/hour should be in the millions, not hundreds.

---

### 2. `kat.py --scan` — Liquidity warnings and partitioning

**Problem:** The scan ranks purely by profit, placing illiquid pets at the top.
Witch COMMON→LEGENDARY shows as #1 at 157M profit, but requires ~405M capital,
shows "?" for sales (no volume data), and may take weeks to sell. A user or
agent taking the top result gets a recommendation to sink 400M into a trap.

**Fix:**
- After sorting results, partition into two groups:
  - **Liquid**: `sales_day is not None and >= 0.5`
  - **Illiquid**: `sales_day is None or < 0.5`
- Print liquid results first under the existing header
- Print illiquid results in a separate section:
  `⚠ LOW LIQUIDITY (may take days/weeks to sell)`
- Add footer note:
  `Sales "?" = no recent AH data. High profit + low liquidity = high risk.`
- In `--profit` single-pet view: if target rarity has `sales_day` of None or
  < 0.5, add warning line:
  `⚠ This rarity has very low AH volume — selling may take a long time`

---

## Batch 2 — Honesty and Safety

These prevent misinterpretation of output. Low risk, small changes.

### 3. `validate.py --kat` — Honest about what it does

**Problem:** Header says "KAT VALIDATION — Matched: 320, Divergent: 0" but no
actual comparison happens. `divergent` is hardcoded to 0. The body text says
"reference data — no direct comparison" but the statistics imply validation
occurred, giving false confidence.

**Fix:**
- Change section header from `KAT VALIDATION` to `KAT REFERENCE DATA (Coflnet)`
- Remove `Matched` and `Divergent` counts from Kat output
- Replace with: `Coflnet items: 320 | Note: reference only — no cross-validation
  (Coflnet provides per-step data, our tool calculates full chains)`
- In `--json` output: set `"type": "kat_reference"`, remove `"divergent"` key
- Add code comment in `validate_kat()` explaining why comparison isn't possible

---

### 4. `minions.py` — Practical warning for no-SC3000 mode

**Problem:** Without Super Compactor, raw drops fill the 15-slot minion storage
within minutes at high tiers. The profit numbers (e.g. Cow 441K/minion/day) are
mathematically correct but practically unreachable without constant manual
collection. Nothing in the output indicates this.

**Fix:**
- In `show_ranked_table()`, when `use_sc3000 is False`, add footer:
  ```
  ⚠ Without Super Compactor, minion storage fills quickly with raw drops.
    Profits assume all items are collected and sold — actual yield depends
    on collection frequency. High-action minions are most affected.
  ```
- In `show_detail()`, when `use_sc3000 is False`, calculate and show storage
  fill time: `Storage: 15 slots × 64 = 960 items. At {drops}/action and
  {actions}/day, fills in ~{time}.` Gives concrete sense of collection cadence.

---

### 5. `crafts.py` — Clarify sell price vs profit calculation

**Problem:** The "Sell" column shows raw LBIN. The "Profit" column applies a 5%
undercut + 1% AH tax. A user doing `Sell - Cost` in their head gets a number
that doesn't match "Profit", with no explanation in the table output. The
`--item` detail view shows the formula but the summary table doesn't.

**Fix:**
- Add one-line footer below craft flip tables:
  `Profit = Sell × 0.99 × (1 − undercut%) − Cost. Sell shows LBIN before fees.`
- For `--forge` variant:
  `Profit = Sell × 0.99 − Cost. Time includes Quick Forge if applicable.`

---

## Batch 3 — UX and Agent Ergonomics

### 6. `shards.py` — Add `-h`/`--help` support

**Problem:** `-h` and `--help` are treated as shard name lookups and fail with
"No shard found matching '--help'". Every other tool supports standard help.

**Fix:**
- In command parsing (line ~1248), before the command dispatch chain:
  ```python
  if cmd in ('-h', '--help', 'help'):
      print_usage()
      return
  ```
- Add `print_usage()` function:
  ```
  Usage: python3 shards.py [command] [args]

  Commands:
    (none) / summary    Top farmable shards + cheapest fillers
    chain <shard>       Fusion chain and recommendation for a shard
    farm                Rank all shards by estimated farming coins/hr
    fillers             Cheapest filler shards by rarity
    health              Market health check — thin/dead market flags
    <shard name>        Shortcut for 'chain <shard>'

  Examples:
    python3 shards.py
    python3 shards.py chain mimic
    python3 shards.py coralot
  ```
- On "No shard found", append:
  `Run 'python3 shards.py --help' for usage.`

---

### 7. `sbxp.py --category` — Validate category input

**Problem:** Invalid category silently produces no filtered recommendations.
Every other tool with category filtering warns about invalid input.

**Fix:**
- In `print_recommendations()`, before applying filter, collect known
  categories: `known_cats = sorted(set(r["category"] for r in all_recs))`
- After filtering, if result is empty but pre-filter list wasn't:
  ```python
  if not filtered and all_recs:
      print(f"  No recommendations match category '{category_filter}'.")
      print(f"  Available: {', '.join(known_cats)}")
  ```

---

### 8. `profile.py` — Add `--only` flag for section isolation

**Problem:** `--section hotm` *adds* HotM to the 9 core sections. There's no
way to get just HotM data without the 60+ lines of general/skills/slayers/
dungeons preamble. When an agent needs one data point, it pays for 9 sections
of context it doesn't need.

**Fix:**
- Add flag: `--only` / `-o` with help text:
  `Show ONLY these sections (comma-separated), skip core defaults`
- In section logic, add before the existing `if args.full:` block:
  ```python
  if args.only:
      active_sections = set()
      for s in args.only.split(","):
          s = s.strip().lower()
          if s in ALL_SECTIONS:
              active_sections.add(s)
          else:
              print(f"Warning: unknown section '{s}'. "
                    f"Available: {', '.join(ALL_SECTIONS)}")
  elif args.full:
      ...
  ```
- Usage: `python3 profile.py --only hotm` shows just HotM.
  `python3 profile.py --only hotm,pets` shows just those two.

---

### 9. `forge.py --item` — Fix output ordering on error

**Problem:** When `--item FAKE` fails, the "9 recipes" text appears on the same
line as the error because the fetch uses `end=""` continuation and the error
prints to stderr while the count goes to stdout, causing interleaved output.

**Fix:** Change the fetch progress line (311-312) from two prints with
`end=""` continuation to a single print:
```python
forge_data = fetch_forge_data()
print(f"  Fetching forge data from Coflnet... {len(forge_data)} recipes")
```
Or: move the fetch to before the print, emit the count as a complete line.

---

### 10. `profile.py` — Add `--json` output

**Problem:** Profile output is 784 lines / ~39KB of human-formatted text with
Unicode box characters. Every other data-producing tool has `--json`. When an
agent needs to extract specific values, it's parsing decorative output.

**Fix:**
- Add `--json` flag to argparse
- Add a `data = {}` collector dict at the top of the display phase
- In each section, populate `data["section_name"] = {...}` with structured data
  before the existing print logic
- When `--json`, skip all prints and `json.dump(data)` at the end
- **Scope to high-value sections first:** general (purse, bank, MP, SB level),
  skills, slayers, dungeons, hotm, pets, collections. Decorative sections
  (inventories, market prices, crafts) can be added in a follow-up.

This is the largest single change (~2,800 lines of display logic to instrument).
Suggest implementing incrementally — get the core sections working first, add
more as needed.

---

## Implementation Order

| Batch | Items | Risk | Effort |
|-------|-------|------|--------|
| 1 — Data integrity | #1 forge duration, #2 kat liquidity | Low | Small |
| 2 — Honesty/safety | #3 validate kat, #4 minions warning, #5 crafts footer | Low | Small |
| 3 — UX/ergonomics | #6-#9 help/validation/flags/ordering | Low | Small-Medium |
| 3 — Agent support | #10 profile --json | Low | Large |

Batch 1 should be done and verified first — these actively produce wrong
recommendations. Batch 2 is all one-liner to small-block changes. Batch 3
items 6-9 are independent and can be done in any order. Item 10 is the only
labor-intensive change and can be deferred or scoped down.
