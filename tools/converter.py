#!/usr/bin/env python3
"""Convert NEU-repo items and wiki pages into an Obsidian vault.

Usage:
    python3 converter.py                  # Full conversion
    python3 converter.py --wiki-only      # Only wiki pages
    python3 converter.py --items-only     # Only NEU items
    python3 converter.py --page "Coal"    # Single wiki page (debugging)
"""

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
WIKI_DIR = DATA_DIR / "wiki"
TEMPLATE_DIR = WIKI_DIR / "templates"
NEU_DIR = DATA_DIR / "neu-repo"
ITEMS_DIR = NEU_DIR / "items"
VAULT_DIR = DATA_DIR / "vault"

# Section name mapping for page templates
PAGE_SECTIONS = {
    "summary": "Summary",
    "obtaining": "Obtaining",
    "upgrading": "Upgrading",
    "usage": "Usage",
    "collection": "Collection",
    "lore": "Lore",
    "trivia": "Trivia",
    "history": "History",
    "stats": "Stats",
    "drops": "Drops",
    "dialogue": "Dialogue",
    "tips": "Tips",
    "strategies": "Strategies",
    "abilities": "Abilities",
    "rewards": "Rewards",
    "gallery": "Gallery",
    "notes": "Notes",
    "levelingrewards": "Leveling Rewards",
    "xpgain": "XP Gain",
    "tips_and_tricks": "Tips & Tricks",
    "npcs": "NPCs",
    "mobs": "Mobs",
    "items": "Items",
    "description": "Description",
    "location": "Location",
    "quests": "Quests",
    "features": "Features",
    "requirements": "Requirements",
    "damage": "Damage",
    "variants": "Variants",
    "levels": "Levels",
    "ingredients": "Ingredients",
    "effects": "Effects",
    "tiers": "Tiers",
    "crafting": "Crafting",
    "enchantments": "Enchantments",
    "reforges": "Reforges",
    "set_bonus": "Set Bonus",
    "dungeon_stats": "Dungeon Stats",
}

# ── Color code stripping ──────────────────────────────────────────────

COLOR_CODE_RE = re.compile(r"§[0-9a-fk-or]", re.IGNORECASE)


def strip_color(text):
    """Strip Minecraft § color codes."""
    return COLOR_CODE_RE.sub("", text)


# ── ID-to-name mapping ───────────────────────────────────────────────

def build_id_maps():
    """Pre-scan wiki files to build ID-to-display-name maps.

    Scans for patterns like |item = COAL, |zone = ID, |npc = ID, etc.
    Priority: |item= wins over other params, NEU displaynames fill gaps.
    """
    id_map = {}  # INTERNAL_ID -> Display Name

    # First pass: NEU items (lowest priority, will be overwritten)
    for jf in ITEMS_DIR.glob("*.json"):
        item_id = jf.stem
        try:
            data = json.loads(jf.read_text(errors="replace"))
            name = strip_color(data.get("displayname", ""))
            if name:
                id_map[item_id] = name
        except (json.JSONDecodeError, OSError):
            pass

    # Second pass: non-item wiki params (medium priority)
    secondary_re = re.compile(r"^\|(?:armor|mob|npc|zone|pet|minion|enchantment|potion|weapon|tool)\s*=\s*(\S+)", re.MULTILINE)
    title_re = re.compile(r"^\|(?:title)\s*=\s*(.+?)$", re.MULTILINE)

    wiki_files = list(WIKI_DIR.glob("*.wiki"))
    for wf in wiki_files:
        page_name = wf.stem
        try:
            text = wf.read_text(errors="replace")
        except OSError:
            continue

        for m in secondary_re.finditer(text):
            raw_id = m.group(1).strip()
            if raw_id:
                id_map[raw_id] = page_name

        for m in title_re.finditer(text):
            raw_title = m.group(1).strip()
            if raw_title:
                clean = raw_title.replace("'''", "").strip()
                if clean:
                    normalized = clean.upper().replace(" ", "_")
                    id_map[normalized] = clean

    # Third pass: |item = params (highest priority — overwrites everything)
    item_re = re.compile(r"^\|item\s*=\s*(\S+)", re.MULTILINE)
    for wf in wiki_files:
        page_name = wf.stem
        try:
            text = wf.read_text(errors="replace")
        except OSError:
            continue
        for m in item_re.finditer(text):
            raw_id = m.group(1).strip()
            if raw_id:
                id_map[raw_id] = page_name

    return id_map


def id_to_name(item_id, id_map):
    """Convert an internal ID to a display name."""
    if item_id in id_map:
        return id_map[item_id]
    # Fallback: SOME_ID -> Some Id
    return item_id.replace("_", " ").title()


def id_to_wiki_link(item_id, id_map):
    """Convert an internal ID to a [[wikilink]]."""
    name = id_to_name(item_id, id_map)
    return f"[[{name}]]"


# ── NEU Item Conversion ──────────────────────────────────────────────

def extract_rarity_type(lore):
    """Extract rarity and item type from the last lore line."""
    if not lore:
        return None, None

    last = strip_color(lore[-1]).strip()
    # Pattern: "EPIC DUNGEON CHESTPLATE" or "UNCOMMON ORE"
    rarities = ["ADMIN", "VERY SPECIAL", "SPECIAL", "SUPREME", "MYTHIC", "DIVINE",
                "LEGENDARY", "EPIC", "RARE", "UNCOMMON", "COMMON"]
    for r in rarities:
        if last.startswith(r):
            remainder = last[len(r):].strip()
            return r.title(), remainder.title() if remainder else None
    return None, None


def format_recipe_table(recipe, id_map):
    """Format a crafting recipe as a markdown table."""
    rows = []
    rows.append("| | 1 | 2 | 3 |")
    rows.append("|---|---|---|---|")
    for row_label in ["A", "B", "C"]:
        cells = []
        for col in ["1", "2", "3"]:
            key = f"{row_label}{col}"
            val = recipe.get(key, "")
            if val:
                parts = val.split(":")
                item_id = parts[0]
                count = parts[1] if len(parts) > 1 else "1"
                link = id_to_wiki_link(item_id, id_map)
                cell = f"{link} x{count}" if count != "1" else link
            else:
                cell = ""
            cells.append(cell)
        rows.append(f"| {row_label} | {cells[0]} | {cells[1]} | {cells[2]} |")
    return "\n".join(rows)


def format_forge_recipe(recipe, id_map):
    """Format a forge recipe as a list."""
    lines = ["**Forge Recipe:**"]
    inputs = recipe.get("inputs", [])
    for inp in inputs:
        parts = inp.split(":")
        item_id = parts[0]
        count = parts[1] if len(parts) > 1 else "1"
        link = id_to_wiki_link(item_id, id_map)
        lines.append(f"- {link} x{count}")

    duration = recipe.get("duration", 0)
    if duration:
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        if hours > 0:
            lines.append(f"- Duration: {hours}h {minutes}m" if minutes else f"- Duration: {hours}h")
        else:
            lines.append(f"- Duration: {minutes}m")

    return "\n".join(lines)


def convert_neu_item(item_data, id_map):
    """Convert a single NEU item JSON to markdown."""
    item_id = item_data.get("internalname", "UNKNOWN")
    display_name = strip_color(item_data.get("displayname", item_id))
    lore = item_data.get("lore", [])
    rarity, item_type = extract_rarity_type(lore)

    # Frontmatter
    fm_parts = [f"id: {item_id}"]
    if rarity:
        fm_parts.append(f"rarity: {rarity}")
    if item_type:
        fm_parts.append(f"type: {item_type}")

    # Wiki link
    info = item_data.get("info", [])
    wiki_url = None
    for url in info:
        if "wiki.hypixel.net" in url:
            wiki_url = url
            break

    if wiki_url:
        # Extract page name from URL
        page_name = wiki_url.rsplit("/", 1)[-1].replace("_", " ")
        fm_parts.append(f"wiki: \"[[{page_name}]]\"")

    frontmatter = "---\n" + "\n".join(fm_parts) + "\n---"

    # Body
    lines = [frontmatter, "", f"# {display_name}", ""]

    # Lore (excluding last rarity line)
    lore_lines = lore[:-1] if lore else []
    if lore_lines:
        for ll in lore_lines:
            clean = strip_color(ll).strip()
            if clean:
                lines.append(f"> {clean}")
            else:
                lines.append(">")
        lines.append("")

    # Recipes
    recipes = item_data.get("recipes", [])
    for i, recipe in enumerate(recipes):
        rtype = recipe.get("type", "crafting")
        if rtype == "crafting":
            if len(recipes) > 1:
                lines.append(f"## Recipe {i + 1}")
            else:
                lines.append("## Recipe")
            lines.append("")
            lines.append(format_recipe_table(recipe, id_map))
            count = recipe.get("count", 1)
            if count > 1:
                lines.append(f"\nOutput: x{count}")
            lines.append("")
        elif rtype == "forge":
            lines.append(format_forge_recipe(recipe, id_map))
            lines.append("")

    # Cross-link to wiki page
    if wiki_url:
        page_name = wiki_url.rsplit("/", 1)[-1].replace("_", " ")
        lines.append(f"See also: [[{page_name}]]")
        lines.append("")

    return "\n".join(lines)


def convert_all_items(id_map):
    """Convert all NEU items to markdown files."""
    out_dir = VAULT_DIR / "items"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(ITEMS_DIR.glob("*.json"))
    total = len(json_files)
    converted = 0
    errors = 0

    for i, jf in enumerate(json_files):
        if (i + 1) % 500 == 0:
            print(f"  Items: {i + 1}/{total}...")

        try:
            data = json.loads(jf.read_text(errors="replace"))
            md = convert_neu_item(data, id_map)
            out_path = out_dir / f"{jf.stem}.md"
            out_path.write_text(md)
            converted += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  Error converting {jf.name}: {e}", file=sys.stderr)

    print(f"  Items complete: {converted} converted, {errors} errors")
    return converted


# ── Wiki Page Conversion ─────────────────────────────────────────────

# ── Template parsing ──────────────────────────────────────────────────

def find_matching_braces(text, start):
    """Find the matching closing '}}' for an opening '{{' at position start.

    Handles nested templates by counting brace depth.
    Returns the index of the character AFTER the closing '}}'.
    """
    depth = 0
    i = start
    while i < len(text):
        if text[i:i+2] == "{{":
            depth += 1
            i += 2
        elif text[i:i+2] == "}}":
            depth -= 1
            if depth == 0:
                return i + 2
            i += 2
        else:
            i += 1
    return len(text)  # unclosed


def parse_template(text):
    """Parse a template string (without outer {{ }}) into name and params.

    Returns (template_name, positional_params, named_params).
    Handles nested templates and links by tracking {{ }}, [[ ]] depth.
    """
    # Split on pipes, but respect nested {{ }} and [[ ]]
    parts = []
    depth_brace = 0
    depth_link = 0
    current = []
    i = 0
    while i < len(text):
        if text[i:i+2] == "{{":
            depth_brace += 1
            current.append("{{")
            i += 2
            continue
        elif text[i:i+2] == "}}":
            depth_brace -= 1
            current.append("}}")
            i += 2
            continue
        elif text[i:i+2] == "[[":
            depth_link += 1
            current.append("[[")
            i += 2
            continue
        elif text[i:i+2] == "]]":
            depth_link -= 1
            current.append("]]")
            i += 2
            continue
        elif text[i] == "|" and depth_brace == 0 and depth_link == 0:
            parts.append("".join(current))
            current = []
            i += 1
            continue
        current.append(text[i])
        i += 1
    parts.append("".join(current))

    name = parts[0].strip() if parts else ""
    positional = []
    named = {}

    for p in parts[1:]:
        if "=" in p:
            key, val = p.split("=", 1)
            key = key.strip().lower()
            named[key] = val.strip()
        else:
            positional.append(p.strip())

    return name, positional, named


# ── Stat templates ────────────────────────────────────────────────────

STAT_TEMPLATES = {
    "health", "defense", "strength", "speed", "crit chance", "crit damage",
    "intelligence", "mining speed", "mining fortune", "farming fortune",
    "foraging fortune", "sea creature chance", "magic find", "pet luck",
    "attack speed", "ferocity", "ability damage", "true defense",
    "combat", "mining", "farming", "fishing", "foraging", "enchanting",
    "alchemy", "taming", "carpentry", "social", "crit", "mending",
    "vitality", "swing range", "breaking power", "pristine",
    "bonus pest chance", "cold resistance", "rift time", "mana regen",
    "walk speed", "bonus attack speed", "weapon ability damage",
    "skyblock xp",
}

RARITY_TEMPLATES = {
    "common", "uncommon", "rare", "epic", "legendary", "mythic",
    "divine", "special", "very special", "supreme", "admin",
}


def convert_template(name, positional, named, id_map, neu_recipes):
    """Convert a single template invocation to markdown."""
    name_lower = name.lower().strip()

    # Item/ID → [[Name]]
    if "/" in name and not name_lower.startswith("dungeon table"):
        prefix, item_id = name.split("/", 1)
        prefix_lower = prefix.lower().strip()

        if prefix_lower in ("item", "zone", "npc", "mob", "pet", "minion",
                            "enchantment", "potion", "armor", "reforge", "power"):
            display = id_to_name(item_id.strip(), id_map)
            # For minions with tier info
            if positional:
                extra = ", ".join(positional)
                return f"[[{display}]] ({extra})"
            return f"[[{display}]]"

        if prefix_lower == "recipe":
            recipe_id = item_id.strip()
            return _render_recipe_from_neu(recipe_id, id_map, neu_recipes)

        # Fallback for unknown prefix/id templates
        display = id_to_name(item_id.strip(), id_map)
        return f"[[{display}]]"

    # Color template: {{color|green|text}} or {{Color|green|text}}
    if name_lower == "color":
        if len(positional) >= 2:
            return positional[1]
        if len(positional) == 1:
            return positional[0]
        return ""

    # Coins template: {{Coins|5000000}} → 5,000,000 coins
    if name_lower == "coins":
        if positional:
            try:
                amount = int(positional[0].replace(",", ""))
                return f"{amount:,} coins"
            except ValueError:
                return f"{positional[0]} coins"
        return "coins"

    # Stat templates: {{Health|+10}} → +10 Health
    if name_lower in STAT_TEMPLATES:
        stat_name = name.strip()
        if positional:
            return f"{positional[0]} {stat_name}"
        return stat_name

    # Rarity templates: {{Epic}} → **Epic**
    if name_lower in RARITY_TEMPLATES:
        return f"**{name.strip()}**"

    # SkyBlock Version
    if name_lower == "skyblock version":
        patch = named.get("patch", "")
        changes = []
        for k, v in sorted(named.items()):
            if k.startswith("change"):
                changes.append(v.strip())
        if changes:
            return "- Patch " + patch + ": " + "; ".join(changes)
        if patch:
            return "- Patch " + patch
        return ""

    # Image template — just strip it (images don't work in Obsidian without files)
    if name_lower == "image":
        return ""

    # ListSpacing — just return content
    if name_lower == "listspacing":
        return named.get("list", "")

    # Tab template — simplify to sections
    if name_lower == "tab":
        parts = []
        for i in range(1, 20):
            tab_name = named.get(f"t{i}name", "")
            tab_content = named.get(f"t{i}content", "")
            if tab_name:
                parts.append(f"\n**{tab_name}**\n{tab_content}")
        return "\n".join(parts)

    # MA (Main Article) template
    if name_lower == "ma":
        links = ", ".join(positional) if positional else ""
        return f"*Main article: {links}*"

    # Page layout templates — should be handled by extract_page_template,
    # but if we encounter one inline, render its sections
    page_templates = {"item page", "npc page", "mob page", "zone page",
                      "armor page", "enchantment page", "skills page",
                      "minion page", "potion page", "weapon page",
                      "tool page", "accessory page", "pet page",
                      "fishing rod page", "bow page"}
    if name_lower in page_templates:
        return _convert_page_template(name, named, id_map)

    # Dungeon Table — too complex, render as note
    if name_lower.startswith("dungeon table"):
        return "*[Dungeon drop rate table — see wiki]*"

    # Collections template — render as simplified list
    if name_lower == "collections":
        return _convert_collections_template(named)

    # Skills templates
    if name_lower.startswith("skills "):
        return ""  # These are complex formatting templates, skip

    # Slideshow — just note it
    if name_lower == "slideshow":
        return "*[Animated slideshow — see wiki]*"

    # Farming/Mining/etc Collection template
    if name_lower.endswith(" collection"):
        return ""  # Sidebar navbox, not needed

    # CollapsibleTree
    if name_lower == "collapsibletree":
        return ""  # Navbox

    # Navbox-like templates
    if name_lower.endswith("navbox") or name_lower.startswith("mobnavbox"):
        return ""

    # History templates
    if name_lower.startswith("history/"):
        return ""

    # Unknown template — render as plain text
    result_parts = [name]
    if positional:
        result_parts.extend(positional)
    return " ".join(result_parts)


def _render_recipe_from_neu(recipe_id, id_map, neu_recipes):
    """Try to render a recipe from the NEU data."""
    recipes = neu_recipes.get(recipe_id, [])
    if not recipes:
        display = id_to_name(recipe_id, id_map)
        return f"*Recipe: [[{display}]]*"

    recipe = recipes[0]
    rtype = recipe.get("type", "crafting")
    if rtype == "crafting":
        return "\n" + format_recipe_table(recipe, id_map) + "\n"
    elif rtype == "forge":
        return "\n" + format_forge_recipe(recipe, id_map) + "\n"
    else:
        display = id_to_name(recipe_id, id_map)
        return f"*Recipe: [[{display}]]*"


def _convert_page_template(name, named, id_map):
    """Convert a page layout template to markdown sections."""
    parts = []

    for key, section_title in PAGE_SECTIONS.items():
        content = named.get(key, "").strip()
        if content:
            parts.append(f"\n## {section_title}\n")
            parts.append(content)
            parts.append("")

    # Handle any remaining named params not in the mapping
    handled = set(PAGE_SECTIONS.keys()) | {"notification", "item", "armor",
        "armor2", "armor2name", "armorname", "title", "image", "category",
        "mob", "npc", "zone", "pet", "minion", "enchantment", "potion",
        "weapon", "tool", "disable_multi_essence", "disable_essence",
        "icon", "desc", "type", "tier", "table"}
    for key, val in named.items():
        if key not in handled and val.strip():
            section_title = key.replace("_", " ").title()
            parts.append(f"\n## {section_title}\n")
            parts.append(val.strip())
            parts.append("")

    return "\n".join(parts)


def _convert_collections_template(named):
    """Convert a Collections template to a simple tier list."""
    lines = []
    for i in range(1, 20):
        req = named.get(f"t{i}required", "")
        reward = named.get(f"t{i}reward", "")
        if req:
            lines.append(f"| {i} | {req} | {reward} |")
    if lines:
        return "| Tier | Required | Reward |\n|---|---|---|\n" + "\n".join(lines)
    return ""


# ── Markup conversion ─────────────────────────────────────────────────

def convert_mediawiki_markup(text, id_map, neu_recipes):
    """Convert MediaWiki markup to Obsidian-compatible markdown."""

    # First: process templates (must happen before other conversions
    # because templates can contain wiki markup)
    text = process_templates(text, id_map, neu_recipes)

    # Bold: '''text''' → **text**
    text = re.sub(r"'''(.+?)'''", r"**\1**", text)

    # Italic: ''text'' → *text*
    text = re.sub(r"''(.+?)''", r"*\1*", text)

    # Headings: == H2 == → ## H2
    for level in range(6, 1, -1):
        eq = "=" * level
        hashes = "#" * level
        text = re.sub(rf"^{eq}\s*(.+?)\s*{eq}\s*$", rf"{hashes} \1", text, flags=re.MULTILINE)

    # Internal links: [[Page|Display]] → [[Page|Display]] (already Obsidian format)
    # But [[Category:Name]] → extract to tags
    # Handle category extraction separately (in convert_wiki_page)

    # External links: [url text] → [text](url)
    text = re.sub(r"\[https?://\S+\s+([^\]]+)\]", r"\1", text)
    # Bare external links
    text = re.sub(r"\[(https?://\S+)\]", r"\1", text)

    # HTML tags
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?(?:div|span|center|small|big|sup|sub|u|s|del|ins)[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # Math: <math>...</math> → $...$
    text = re.sub(r"<math>(.*?)</math>", r"$\1$", text, flags=re.DOTALL)

    # Code: <code>...</code> → `...`
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text, flags=re.DOTALL)
    text = re.sub(r"<nowiki>(.*?)</nowiki>", r"`\1`", text, flags=re.DOTALL)

    # noinclude / includeonly
    text = re.sub(r"</?noinclude>", "", text)
    text = re.sub(r"</?includeonly>", "", text)

    # File/Image links — strip
    text = re.sub(r"\[\[File:[^\]]*\]\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[\[Image:[^\]]*\]\]", "", text, flags=re.IGNORECASE)

    # Tables
    text = convert_tables(text)

    # Strip remaining color codes
    text = strip_color(text)

    # Clean up multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def process_templates(text, id_map, neu_recipes):
    """Process all {{ }} templates in the text, innermost first."""
    max_iterations = 200  # safety limit for complex pages
    for _ in range(max_iterations):
        # Find the innermost template (one that contains no {{ inside it)
        match = re.search(r"\{\{([^{}]*)\}\}", text)
        if not match:
            break

        inner = match.group(1)

        # Handle {{!}} escape (MediaWiki pipe-in-template workaround)
        if inner == "!":
            text = text[:match.start()] + "|" + text[match.end():]
            continue

        name, positional, named = parse_template(inner)
        replacement = convert_template(name, positional, named, id_map, neu_recipes)

        text = text[:match.start()] + replacement + text[match.end():]

    return text


# ── Table conversion ──────────────────────────────────────────────────

def convert_tables(text):
    """Convert MediaWiki tables to markdown tables."""
    result = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Table start
        if line.strip().startswith("{|"):
            table_lines = [line]
            depth = 1
            i += 1
            while i < len(lines) and depth > 0:
                l = lines[i]
                if l.strip().startswith("{|"):
                    depth += 1
                elif l.strip().startswith("|}"):
                    depth -= 1
                table_lines.append(l)
                i += 1

            md_table = _wikitable_to_md(table_lines)
            result.append(md_table)
            continue

        result.append(line)
        i += 1

    return "\n".join(result)


def _wikitable_to_md(table_lines):
    """Convert a single MediaWiki table to markdown."""
    rows = []
    current_row = []
    is_header_row = False

    for line in table_lines:
        stripped = line.strip()

        # Skip table open/close and style attributes
        if stripped.startswith("{|") or stripped.startswith("|}"):
            continue
        if stripped.startswith("|+"):
            # Caption
            caption = stripped[2:].strip()
            if caption:
                rows.insert(0, [f"**{_strip_style(caption)}**"])
            continue

        # Row separator
        if stripped == "|-" or stripped.startswith("|-"):
            if current_row:
                rows.append(current_row)
                current_row = []
            is_header_row = False
            continue

        # Header cell
        if stripped.startswith("!"):
            is_header_row = True
            cells = _split_cells(stripped[1:], "!")
            current_row.extend(_strip_style(c) for c in cells)
            continue

        # Data cell
        if stripped.startswith("|"):
            cells = _split_cells(stripped[1:], "|")
            current_row.extend(_strip_style(c) for c in cells)
            continue

    if current_row:
        rows.append(current_row)

    if not rows:
        return ""

    # Normalize column count
    max_cols = max(len(r) for r in rows) if rows else 0
    if max_cols == 0:
        return ""

    for r in rows:
        while len(r) < max_cols:
            r.append("")

    # Build markdown table
    md_lines = []
    header = rows[0] if rows else []
    md_lines.append("| " + " | ".join(_escape_pipe_in_links(c.strip()) for c in header) + " |")
    md_lines.append("|" + "|".join("---" for _ in range(max_cols)) + "|")
    for row in rows[1:]:
        md_lines.append("| " + " | ".join(_escape_pipe_in_links(c.strip()) for c in row) + " |")

    return "\n".join(md_lines)


def _escape_pipe_in_links(cell):
    """Escape | inside [[wikilinks]] so they don't break markdown tables."""
    # Replace [[Page|Display]] with [[Page\\|Display]] for markdown table compat
    return re.sub(r"\[\[([^\]]*?)\|([^\]]*?)\]\]", r"[[\1\|\2]]", cell)


def _split_cells(text, sep):
    """Split a wiki table row into cells, handling || or !! separators."""
    return [c.strip() for c in text.split(sep * 2)]


def _strip_style(cell):
    """Strip style attributes from a table cell.

    MediaWiki cells can have: style="..." | actual content
    """
    cell = cell.strip()
    # If cell contains a pipe with style before it, but NOT inside [[ ]]
    if "|" in cell:
        # Find the first | that's not inside [[ ]]
        depth = 0
        for idx, ch in enumerate(cell):
            if cell[idx:idx+2] == "[[":
                depth += 1
            elif cell[idx:idx+2] == "]]":
                depth -= 1
            elif ch == "|" and depth == 0:
                before = cell[:idx].strip()
                after = cell[idx+1:].strip()
                if re.match(r'^(?:style|class|rowspan|colspan|width|align|valign)\s*=', before):
                    return after
                break
    # Strip rowspan/colspan attributes
    cell = re.sub(r'(?:rowspan|colspan)\s*=\s*"?\d+"?\s*', "", cell)
    cell = re.sub(r'style\s*=\s*"[^"]*"\s*', "", cell)
    cell = re.sub(r'class\s*=\s*"[^"]*"\s*', "", cell)
    return cell.strip()


# ── Wiki page conversion ─────────────────────────────────────────────

def extract_categories(text):
    """Extract [[Category:Name]] tags from text and return (cleaned_text, categories)."""
    categories = []
    def repl(m):
        categories.append(m.group(1))
        return ""
    cleaned = re.sub(r"\[\[Category:([^\]]+)\]\]", repl, text)
    return cleaned, categories


PAGE_TEMPLATE_NAMES = {
    "item page", "npc page", "mob page", "zone page", "armor page",
    "enchantment page", "skills page", "minion page", "potion page",
    "weapon page", "tool page", "accessory page", "pet page",
    "fishing rod page", "bow page",
}


def extract_page_template(text):
    """Extract and parse a page-level template (Item Page, NPC Page, etc.).

    These templates wrap the entire page and use |param = value syntax.
    Uses balanced brace counting to handle nested {{templates}} and {|tables|}.

    Returns (before, template_name, sections_dict, after) or None if no page template.
    """
    # Check if text starts with a page template
    match = re.match(r"\s*\{\{(\w[\w ]*)", text)
    if not match:
        return None

    tpl_name = match.group(1).strip()
    if tpl_name.lower() not in PAGE_TEMPLATE_NAMES:
        return None

    # Find the matching }} using balanced brace counting
    # Start after the opening {{
    start = match.start()
    depth = 0
    i = start
    end = len(text)

    while i < len(text):
        if text[i:i+2] == "{{":
            depth += 1
            i += 2
        elif text[i:i+2] == "}}":
            depth -= 1
            if depth == 0:
                end = i + 2
                break
            i += 2
        else:
            i += 1

    template_body = text[start+2:end-2]  # content between outer {{ }}
    before = text[:start].strip()
    after = text[end:].strip()

    # Parse the template body into sections
    # Split on top-level | that start a new parameter
    # We need to handle nested {{ }} and {| |} inside values
    sections = {}
    current_key = None
    current_value = []

    # Remove template name from the start
    body = template_body[len(tpl_name):]

    # Split on top-level pipes
    parts = _split_template_params(body)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Check if this is a named param: key = value
        eq_match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_ ]*?)\s*=\s*", part)
        if eq_match:
            if current_key is not None:
                sections[current_key] = "\n".join(current_value).strip()
            current_key = eq_match.group(1).strip().lower()
            current_value = [part[eq_match.end():]]
        else:
            # Continuation of current value or positional param
            if current_key is not None:
                current_value.append(part)

    if current_key is not None:
        sections[current_key] = "\n".join(current_value).strip()

    return before, tpl_name, sections, after


def _split_template_params(body):
    """Split template body on top-level pipes, respecting nested {{ }}, {| |}, and [[ ]]."""
    parts = []
    current = []
    depth_braces = 0   # {{ }} depth
    depth_table = 0    # {| |} depth
    depth_link = 0     # [[ ]] depth
    i = 0

    while i < len(body):
        ch = body[i]

        if body[i:i+2] == "{{":
            depth_braces += 1
            current.append("{{")
            i += 2
            continue
        elif body[i:i+2] == "}}":
            depth_braces -= 1
            current.append("}}")
            i += 2
            continue
        elif body[i:i+2] == "[[":
            depth_link += 1
            current.append("[[")
            i += 2
            continue
        elif body[i:i+2] == "]]":
            depth_link -= 1
            current.append("]]")
            i += 2
            continue
        elif body[i:i+2] == "{|":
            depth_table += 1
            current.append("{|")
            i += 2
            continue
        elif body[i:i+2] == "|}":
            depth_table -= 1
            current.append("|}")
            i += 2
            continue

        if ch == "|" and depth_braces == 0 and depth_table == 0 and depth_link == 0:
            parts.append("".join(current))
            current = []
            i += 1
            continue

        current.append(ch)
        i += 1

    parts.append("".join(current))
    return parts


def convert_wiki_page(page_name, text, id_map, neu_recipes):
    """Convert a single wiki page to Obsidian markdown."""
    # Extract categories first
    text, categories = extract_categories(text)

    # Check for page-level template
    page_tpl = extract_page_template(text)

    if page_tpl:
        before, tpl_name, sections, after = page_tpl

        # Build the page from sections
        md_parts = [f"# {page_name}", ""]

        for key, section_title in PAGE_SECTIONS.items():
            content = sections.get(key, "").strip()
            if content:
                # Process templates and markup within each section
                content = convert_mediawiki_markup(content, id_map, neu_recipes)
                content = content.strip()
                if content:
                    md_parts.append(f"## {section_title}")
                    md_parts.append("")
                    md_parts.append(content)
                    md_parts.append("")

        # Handle remaining sections not in the standard mapping
        handled = set(PAGE_SECTIONS.keys()) | {
            "notification", "item", "armor", "armor2", "armor2name",
            "armorname", "title", "image", "category", "mob", "npc",
            "zone", "pet", "minion", "enchantment", "potion", "weapon",
            "tool", "disable_multi_essence", "disable_essence", "icon",
            "desc", "type", "tier", "table",
        }
        for key, val in sections.items():
            if key not in handled and val.strip():
                section_title = key.replace("_", " ").title()
                content = convert_mediawiki_markup(val.strip(), id_map, neu_recipes)
                if content.strip():
                    md_parts.append(f"## {section_title}")
                    md_parts.append("")
                    md_parts.append(content.strip())
                    md_parts.append("")

        # Process any text after the page template
        if after:
            after_md = convert_mediawiki_markup(after, id_map, neu_recipes).strip()
            if after_md:
                md_parts.append(after_md)
                md_parts.append("")

        md = "\n".join(md_parts)
    else:
        # No page template — convert the whole text
        md = convert_mediawiki_markup(text, id_map, neu_recipes)
        if not md.strip().startswith("# "):
            md = f"# {page_name}\n\n{md}"

    # Build frontmatter
    fm_parts = []
    if categories:
        tags = [c.replace(" ", "-").lower() for c in categories]
        fm_parts.append("tags:")
        for t in tags:
            fm_parts.append(f"  - {t}")

    if fm_parts:
        frontmatter = "---\n" + "\n".join(fm_parts) + "\n---\n\n"
    else:
        frontmatter = ""

    return frontmatter + md


def convert_all_wiki(id_map, neu_recipes, single_page=None):
    """Convert all wiki pages to markdown files."""
    out_dir = VAULT_DIR / "wiki"
    out_dir.mkdir(parents=True, exist_ok=True)

    if single_page:
        # Find the matching file
        candidates = list(WIKI_DIR.glob(f"{single_page}.wiki"))
        if not candidates:
            # Try case-insensitive
            for wf in WIKI_DIR.glob("*.wiki"):
                if wf.stem.lower() == single_page.lower():
                    candidates = [wf]
                    break
        if not candidates:
            print(f"  Page not found: {single_page}")
            return 0
        wiki_files = candidates
    else:
        wiki_files = sorted(WIKI_DIR.glob("*.wiki"))

    total = len(wiki_files)
    converted = 0
    errors = 0

    for i, wf in enumerate(wiki_files):
        if not single_page and (i + 1) % 500 == 0:
            print(f"  Wiki: {i + 1}/{total}...")

        page_name = wf.stem
        try:
            text = wf.read_text(errors="replace")
            md = convert_wiki_page(page_name, text, id_map, neu_recipes)
            out_path = out_dir / f"{page_name}.md"
            out_path.write_text(md)
            converted += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  Error converting {wf.name}: {e}", file=sys.stderr)

    # Also convert template/data pages
    if not single_page:
        data_dir = VAULT_DIR / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        template_files = sorted(TEMPLATE_DIR.glob("*.wiki")) if TEMPLATE_DIR.exists() else []
        for tf in template_files:
            page_name = tf.stem.replace("Data_SLASH_", "Data/")
            try:
                text = tf.read_text(errors="replace")
                md = convert_wiki_page(page_name, text, id_map, neu_recipes)
                safe_name = tf.stem.replace("_SLASH_", " - ")
                out_path = data_dir / f"{safe_name}.md"
                out_path.write_text(md)
                converted += 1
            except Exception as e:
                errors += 1

    print(f"  Wiki complete: {converted} converted, {errors} errors")
    return converted


# ── NEU recipe index ──────────────────────────────────────────────────

def build_recipe_index():
    """Build a map of item_id -> recipes from NEU data."""
    recipes = {}
    for jf in ITEMS_DIR.glob("*.json"):
        try:
            data = json.loads(jf.read_text(errors="replace"))
            item_recipes = data.get("recipes", [])
            if item_recipes:
                recipes[jf.stem] = item_recipes
        except (json.JSONDecodeError, OSError):
            pass
    return recipes


# ── Vault setup ───────────────────────────────────────────────────────

def setup_vault():
    """Create minimal Obsidian vault configuration."""
    obsidian_dir = VAULT_DIR / ".obsidian"
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    app_config = {
        "useMarkdownLinks": False,  # Use [[wikilinks]]
        "showFrontmatter": True,
        "livePreview": True,
    }
    (obsidian_dir / "app.json").write_text(json.dumps(app_config, indent=2))


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Convert SkyBlock data to Obsidian vault")
    parser.add_argument("--wiki-only", action="store_true", help="Only convert wiki pages")
    parser.add_argument("--items-only", action="store_true", help="Only convert NEU items")
    parser.add_argument("--page", type=str, help="Convert single wiki page (for debugging)")
    args = parser.parse_args()

    print("Building indices...")

    # Build ID map
    id_map = build_id_maps()
    print(f"  ID map: {len(id_map)} entries")

    # Build recipe index
    neu_recipes = build_recipe_index()
    print(f"  Recipes: {len(neu_recipes)} items with recipes")

    # Setup vault
    setup_vault()

    if args.page:
        print(f"\nConverting single page: {args.page}")
        convert_all_wiki(id_map, neu_recipes, single_page=args.page)
        return

    total = 0

    if not args.wiki_only:
        print("\nConverting NEU items...")
        total += convert_all_items(id_map)

    if not args.items_only:
        print("\nConverting wiki pages...")
        total += convert_all_wiki(id_map, neu_recipes)

    print(f"\nDone! {total} files written to {VAULT_DIR}/")


if __name__ == "__main__":
    main()
