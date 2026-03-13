# External Data Files

Data sourced from open-source SkyBlock projects. Attribution below.

## Files

| File | Source | License | Description |
|------|--------|---------|-------------|
| `AttributeGoodRolls.json` | [SkyHanni-REPO](https://github.com/hannibal002/SkyHanni-REPO) | LGPL-3.0 | Good Kuudra attribute combos per item type |
| `StackingEnchants.json` | [SkyHanni-REPO](https://github.com/hannibal002/SkyHanni-REPO) | LGPL-3.0 | Stacking enchant level thresholds |
| `PriceOverrides.json` | [skyblock-plus-data](https://github.com/kr45732/skyblock-plus-data) | — | NPC prices for vanilla items + manual overrides |
| `enchant_rules.json` | SkyHanni-REPO + skyblock-plus-data | Mixed | Consolidated enchantment pricing rules |
| `prestige_costs.json` | skyblock-plus-data | — | Kuudra prestige material costs (with Heavy Pearls) |
| `DungeonLoot.json` | [skyblock-plus-data](https://github.com/kr45732/skyblock-plus-data) | — | Per-score-tier dungeon drop chances (52K lines, SA1-SD5, S+A1-S+D5) |
| `DragonLoot.json` | [skyblock-plus-data](https://github.com/kr45732/skyblock-plus-data) | — | Dragon fight loot tables (all dragon types, quality + chances) |
| `SlayerProfitTrackerItems.json` | [SkyHanni-REPO](https://github.com/hannibal002/SkyHanni-REPO) | LGPL-3.0 | Slayer drop item lists (6 types, used for cross-reference) |
| `BitPrices.json` | [skyblock-plus-data](https://github.com/kr45732/skyblock-plus-data) | — | Bits shop item costs (49 items) |
| `power_stats.json` | [skyblock-plus-data](https://github.com/kr45732/skyblock-plus-data) | — | Maxwell power base stats per 100 MP (30 powers) |
| `farming_weight.json` | [EliteFarmers/FarmingWeight](https://github.com/EliteFarmers/FarmingWeight) | MIT | Farming weight crop divisors + bonus constants |

## Updating

Files from auto-updated repos can be refreshed by re-downloading from GitHub:
- `DungeonLoot.json`: `kr45732/skyblock-plus-data/DungeonLoot.json`
- `DragonLoot.json`: `kr45732/skyblock-plus-data/DragonLoot.json`
- `SlayerProfitTrackerItems.json`: `hannibal002/SkyHanni-REPO/constants/SlayerProfitTrackerItems.json`
- `PriceOverrides.json`: `kr45732/skyblock-plus-data/PriceOverrides.json`
- `BitPrices.json`: `kr45732/skyblock-plus-data/BitPrices.json`
- `power_stats.json`: Extract `POWER_TO_BASE_STATS` from `kr45732/skyblock-plus-data/Constants.json`

Consolidated files (enchant_rules.json, prestige_costs.json, farming_weight.json) need manual re-generation.
