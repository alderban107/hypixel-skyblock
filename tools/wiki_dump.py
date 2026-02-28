#!/usr/bin/env python3
"""
Dump the Hypixel SkyBlock Wiki (wiki.hypixel.net) to local files.

Uses the MediaWiki API with GET-only requests (POST is blocked by Cloudflare).
Fetches wikitext in batches of 50 pages and saves each as an individual .wiki file.

Usage:
    python3 wiki_dump.py              # Full dump (content pages + data templates)
    python3 wiki_dump.py --update     # Incremental update (only changed pages)
    python3 wiki_dump.py --templates  # Only dump Template:Data/* pages
    python3 wiki_dump.py --parse      # Generate parsed text (expands templates)
    python3 wiki_dump.py --update --parse  # Update + re-parse changed pages
"""

import argparse
import html as html_module
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

WIKI_API = "https://wiki.hypixel.net/api.php"
USER_AGENT = "SkyBlockProfileAnalyzer/1.0 (personal wiki cache; contact: none)"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "wiki")
PARSED_DIR = os.path.join(OUTPUT_DIR, "parsed")
META_FILE = os.path.join(OUTPUT_DIR, ".dump_meta.json")
DELAY = 1.0  # seconds between requests


# ---------------------------------------------------------------------------
#  HTML → plain text converter
# ---------------------------------------------------------------------------

class HTMLToText(HTMLParser):
    """Convert parsed wiki HTML to clean searchable text.

    Preserves table structure as pipe-separated rows so data lookups
    (costs, stats, recipes) are greppable.
    """

    SKIP_TAGS = {"script", "style"}
    BLOCK_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
                  "blockquote", "section", "article", "header", "footer"}

    def __init__(self):
        super().__init__()
        self.pieces = []       # output buffer
        self.skip_depth = 0    # depth inside skip tags
        self.in_cell = False
        self.cell_buf = []     # text within current <td>/<th>
        self.row_cells = []    # finished cells for current <tr>

    # -- tag handlers --

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return

        if tag == "br":
            self._emit(" ")
        elif tag == "table":
            self._emit("\n")
        elif tag == "tr":
            self.row_cells = []
        elif tag in ("td", "th"):
            self.in_cell = True
            self.cell_buf = []
        elif tag == "li":
            self._emit("\n  - ")
        elif tag in self.BLOCK_TAGS:
            self._emit("\n")
        elif tag == "img":
            pass  # skip images entirely

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return

        if tag in ("td", "th"):
            self.in_cell = False
            self.row_cells.append("".join(self.cell_buf).strip())
            self.cell_buf = []
        elif tag == "tr":
            if self.row_cells:
                self._emit(" | ".join(self.row_cells) + "\n")
            self.row_cells = []
        elif tag == "table":
            self._emit("\n")
        elif tag in self.BLOCK_TAGS:
            self._emit("\n")

    def handle_data(self, data):
        if self.skip_depth:
            return
        self._emit(data)

    def handle_entityref(self, name):
        if self.skip_depth:
            return
        self._emit(html_module.unescape(f"&{name};"))

    def handle_charref(self, name):
        if self.skip_depth:
            return
        self._emit(html_module.unescape(f"&#{name};"))

    # -- helpers --

    def _emit(self, text):
        if self.in_cell:
            self.cell_buf.append(text)
        else:
            self.pieces.append(text)

    def get_text(self):
        raw = "".join(self.pieces)
        # Collapse runs of blank lines
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        # Strip trailing whitespace per line
        lines = [line.rstrip() for line in raw.split("\n")]
        return "\n".join(lines).strip() + "\n"


def html_to_text(html_content):
    """Convert HTML string to searchable plain text."""
    converter = HTMLToText()
    converter.feed(html_content)
    return converter.get_text()


def filename_to_title(filename):
    """Reverse sanitize_filename: .wiki filename → wiki page title."""
    title = filename
    if title.endswith(".wiki"):
        title = title[:-5]
    title = title.replace("_SLASH_", "/")
    return title


def parse_single_page(title):
    """Fetch server-parsed HTML for a page and convert to plain text."""
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "disabletoc": 1,
        "disableeditsection": 1,
    }
    try:
        data = api_get(params)
        page_html = data.get("parse", {}).get("text", {}).get("*", "")
        if not page_html:
            return None
        return html_to_text(page_html)
    except Exception as e:
        return None


def api_get(params):
    """Make a GET request to the MediaWiki API."""
    params["format"] = "json"
    url = f"{WIKI_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def sanitize_filename(title):
    """Convert a wiki page title to a safe filename."""
    # Replace characters that are problematic in filenames
    name = title.replace("/", "_SLASH_")
    name = re.sub(r'[<>:"|?*\\]', "_", name)
    return name + ".wiki"


def fetch_all_pages(namespace=0, filter_redirects="nonredirects", prefix=None):
    """Fetch all pages with their wikitext content from a namespace."""
    pages = {}
    params = {
        "action": "query",
        "generator": "allpages",
        "gapnamespace": namespace,
        "gaplimit": 50,
        "gapfilterredir": filter_redirects,
        "prop": "revisions",
        "rvprop": "content|timestamp",
        "rvslots": "main",
    }
    if prefix:
        params["gapprefix"] = prefix

    batch = 0
    while True:
        batch += 1
        data = api_get(params)

        query_pages = data.get("query", {}).get("pages", {})
        for page_id, page_data in query_pages.items():
            if int(page_id) < 0:
                continue  # missing page
            title = page_data.get("title", "")
            revisions = page_data.get("revisions", [])
            if not revisions:
                continue
            rev = revisions[0]
            content = rev.get("slots", {}).get("main", {}).get("*", "")
            timestamp = rev.get("timestamp", "")
            if content:
                pages[title] = {"content": content, "timestamp": timestamp}

        count = len(pages)
        sys.stdout.write(f"\r  Fetched {count} pages (batch {batch})...")
        sys.stdout.flush()

        # Check for continuation
        cont = data.get("continue")
        if not cont:
            break
        params.update(cont)
        time.sleep(DELAY)

    print()
    return pages


def save_pages(pages, subdir=None):
    """Save pages to disk as individual .wiki files."""
    target_dir = os.path.join(OUTPUT_DIR, subdir) if subdir else OUTPUT_DIR
    os.makedirs(target_dir, exist_ok=True)

    saved = 0
    for title, page_data in pages.items():
        filename = sanitize_filename(title)
        # Strip namespace prefix for template files
        if subdir and ":" in title:
            filename = sanitize_filename(title.split(":", 1)[1])

        filepath = os.path.join(target_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(page_data["content"])
        saved += 1

    return saved


def fetch_recent_changes(since_timestamp):
    """Fetch pages changed since a given timestamp."""
    changed_titles = set()
    params = {
        "action": "query",
        "list": "recentchanges",
        "rcnamespace": "0|10",  # content + templates
        "rctype": "edit|new",
        "rclimit": 500,
        "rcprop": "title|timestamp",
        "rcend": since_timestamp,  # rcend = oldest timestamp (yes, it's backwards)
        "rcdir": "older",
    }

    data = api_get(params)
    changes = data.get("query", {}).get("recentchanges", [])
    for change in changes:
        changed_titles.add(change["title"])

    return changed_titles


def fetch_specific_pages(titles):
    """Fetch specific pages by title."""
    pages = {}
    title_list = list(titles)

    for i in range(0, len(title_list), 50):
        batch = title_list[i : i + 50]
        params = {
            "action": "query",
            "titles": "|".join(batch),
            "prop": "revisions",
            "rvprop": "content|timestamp",
            "rvslots": "main",
        }
        data = api_get(params)

        query_pages = data.get("query", {}).get("pages", {})
        for page_id, page_data in query_pages.items():
            if int(page_id) < 0:
                continue
            title = page_data.get("title", "")
            revisions = page_data.get("revisions", [])
            if not revisions:
                continue
            rev = revisions[0]
            content = rev.get("slots", {}).get("main", {}).get("*", "")
            timestamp = rev.get("timestamp", "")
            if content:
                pages[title] = {"content": content, "timestamp": timestamp}

        sys.stdout.write(f"\r  Fetched {len(pages)}/{len(title_list)} pages...")
        sys.stdout.flush()
        if i + 50 < len(title_list):
            time.sleep(DELAY)

    print()
    return pages


def load_meta():
    """Load dump metadata (last sync timestamp, page count)."""
    if os.path.exists(META_FILE):
        with open(META_FILE) as f:
            return json.load(f)
    return {}


def save_meta(meta):
    """Save dump metadata."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)


def do_full_dump():
    """Perform a full wiki dump."""
    print("=== Hypixel SkyBlock Wiki Full Dump ===\n")

    # Content pages (namespace 0)
    print("Fetching content pages (namespace 0)...")
    content_pages = fetch_all_pages(namespace=0)
    print(f"  Total: {len(content_pages)} content pages")

    # Data templates (namespace 10, prefix "Data/")
    print("\nFetching Data templates (namespace 10, prefix Data/)...")
    data_templates = fetch_all_pages(namespace=10, prefix="Data/")
    print(f"  Total: {len(data_templates)} data templates")

    # Save everything
    print("\nSaving files...")
    saved_content = save_pages(content_pages)
    saved_templates = save_pages(data_templates, subdir="templates")
    print(f"  Saved {saved_content} content pages to {OUTPUT_DIR}/")
    print(f"  Saved {saved_templates} data templates to {OUTPUT_DIR}/templates/")

    # Save metadata
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_meta({
        "last_sync": now,
        "content_pages": saved_content,
        "data_templates": saved_templates,
    })

    total_size = sum(
        os.path.getsize(os.path.join(dirpath, f))
        for dirpath, _, filenames in os.walk(OUTPUT_DIR)
        for f in filenames
        if f.endswith(".wiki")
    )
    print(f"\n  Total size: {total_size / 1024 / 1024:.1f} MB")
    print(f"  Metadata saved to {META_FILE}")
    print("\nDone!")


def do_update():
    """Perform an incremental update (only changed pages)."""
    meta = load_meta()
    if not meta.get("last_sync"):
        print("No previous dump found. Run a full dump first.")
        sys.exit(1)

    since = meta["last_sync"]
    print(f"=== Incremental Update (since {since}) ===\n")

    print("Checking for recent changes...")
    changed = fetch_recent_changes(since)
    if not changed:
        print("  No changes found. Wiki is up to date!")
        return

    print(f"  Found {len(changed)} changed pages")

    # Separate content pages from templates
    content_titles = {t for t in changed if not t.startswith("Template:")}
    template_titles = {t for t in changed if t.startswith("Template:")}

    if content_titles:
        print(f"\nFetching {len(content_titles)} updated content pages...")
        pages = fetch_specific_pages(content_titles)
        saved = save_pages(pages)
        print(f"  Updated {saved} content pages")

    if template_titles:
        print(f"\nFetching {len(template_titles)} updated templates...")
        pages = fetch_specific_pages(template_titles)
        saved = save_pages(pages, subdir="templates")
        print(f"  Updated {saved} templates")

    # Update metadata
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    meta["last_sync"] = now
    save_meta(meta)
    print(f"\nDone! Metadata updated.")


def do_templates_only():
    """Dump only Template:Data/* pages."""
    print("=== Data Templates Dump ===\n")

    print("Fetching Data templates (namespace 10, prefix Data/)...")
    data_templates = fetch_all_pages(namespace=10, prefix="Data/")
    print(f"  Total: {len(data_templates)} data templates")

    print("\nSaving files...")
    saved = save_pages(data_templates, subdir="templates")
    print(f"  Saved {saved} data templates to {OUTPUT_DIR}/templates/")
    print("\nDone!")


def do_parse(force=False, only_titles=None):
    """Generate parsed plain-text files with all templates expanded.

    Uses action=parse (one page at a time) to get server-rendered HTML,
    then converts to clean searchable text.

    Args:
        force:       Re-parse even if .txt is up-to-date.
        only_titles: If set, only parse these page titles.
    """
    os.makedirs(PARSED_DIR, exist_ok=True)

    # Build list of pages to parse
    if only_titles:
        to_parse = [(t, sanitize_filename(t)) for t in only_titles
                     if not t.startswith("Template:")]
    else:
        to_parse = []
        for f in sorted(os.listdir(OUTPUT_DIR)):
            if not f.endswith(".wiki"):
                continue
            wiki_path = os.path.join(OUTPUT_DIR, f)
            txt_name = f[:-5] + ".txt"
            txt_path = os.path.join(PARSED_DIR, txt_name)

            if not force and os.path.exists(txt_path) and \
               os.path.getmtime(txt_path) >= os.path.getmtime(wiki_path):
                continue  # already up-to-date
            to_parse.append((filename_to_title(f), f))

    if not to_parse:
        print("  All pages already parsed. Use --force to re-parse.")
        return

    total = len(to_parse)
    print(f"  Parsing {total} pages (this takes ~{total} seconds)...\n")

    parsed = 0
    failed = 0
    start = time.time()

    for i, (title, wiki_fname) in enumerate(to_parse):
        text = parse_single_page(title)
        if text:
            txt_name = wiki_fname[:-5] + ".txt" if wiki_fname.endswith(".wiki") \
                else sanitize_filename(title)[:-5] + ".txt"
            txt_path = os.path.join(PARSED_DIR, txt_name)
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)
            parsed += 1
        else:
            failed += 1

        elapsed = time.time() - start
        rate = (i + 1) / elapsed if elapsed > 0 else 0
        remaining = (total - i - 1) / rate if rate > 0 else 0
        mins, secs = divmod(int(remaining), 60)
        sys.stdout.write(
            f"\r  [{parsed}/{total}] {parsed} parsed, {failed} failed"
            f"  ({mins}m {secs}s remaining)   "
        )
        sys.stdout.flush()

        if i < total - 1:
            time.sleep(DELAY)

    elapsed = time.time() - start
    mins, secs = divmod(int(elapsed), 60)
    print(f"\n\n  Done: {parsed} parsed, {failed} failed in {mins}m {secs}s")
    print(f"  Saved to {PARSED_DIR}/")

    # Update metadata
    meta = load_meta()
    meta["last_parse"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    meta["parsed_pages"] = parsed
    save_meta(meta)


def main():
    parser = argparse.ArgumentParser(description="Dump the Hypixel SkyBlock Wiki locally.")
    parser.add_argument("--update", action="store_true", help="Incremental update only")
    parser.add_argument("--templates", action="store_true", help="Only dump Data templates")
    parser.add_argument("--parse", action="store_true",
                        help="Generate parsed text files (expands all templates)")
    parser.add_argument("--force", action="store_true",
                        help="Force re-parse even if files are up-to-date")
    args = parser.parse_args()

    if args.update:
        do_update()
        if args.parse:
            # Re-parse pages that were just updated
            meta = load_meta()
            # Parse any pages needing it (the update touched .wiki files,
            # so timestamp comparison will catch them)
            print("\nParsing updated pages...")
            do_parse(force=args.force)
    elif args.templates:
        do_templates_only()
    elif args.parse:
        print("=== Parse Wiki Pages ===\n")
        do_parse(force=args.force)
    else:
        do_full_dump()
        if args.parse:
            print("\nParsing all pages...")
            do_parse(force=True)


if __name__ == "__main__":
    main()
