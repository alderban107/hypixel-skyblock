#!/usr/bin/env python3
"""
Dump the Hypixel SkyBlock Wiki (wiki.hypixel.net) to local files.

Uses the MediaWiki API with GET-only requests (POST is blocked by Cloudflare).
Fetches wikitext in batches of 50 pages and saves each as an individual .wiki file.

Usage:
    python3 wiki_dump.py              # Full dump (content pages + data templates)
    python3 wiki_dump.py --update     # Incremental update (only changed pages)
    python3 wiki_dump.py --templates  # Only dump Template:Data/* pages
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

WIKI_API = "https://wiki.hypixel.net/api.php"
USER_AGENT = "SkyBlockProfileAnalyzer/1.0 (personal wiki cache; contact: none)"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "wiki")
META_FILE = os.path.join(OUTPUT_DIR, ".dump_meta.json")
DELAY = 1.0  # seconds between requests


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


def main():
    parser = argparse.ArgumentParser(description="Dump the Hypixel SkyBlock Wiki locally.")
    parser.add_argument("--update", action="store_true", help="Incremental update only")
    parser.add_argument("--templates", action="store_true", help="Only dump Data templates")
    args = parser.parse_args()

    if args.update:
        do_update()
    elif args.templates:
        do_templates_only()
    else:
        do_full_dump()


if __name__ == "__main__":
    main()
