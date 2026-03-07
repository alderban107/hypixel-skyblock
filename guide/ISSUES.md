# SkyBlock Guide — UX Issues

## Critical

### 1. Scroll Reveal Animation Creates Massive Empty Gaps
The `.reveal` class is applied to **278 elements** across all pages. Each starts with `opacity: 0; transform: translateY(16px)` and only becomes visible when the IntersectionObserver fires. But when navigating to a page, content below the fold remains invisible while still occupying vertical space — creating huge blank gaps between section headings (clearly visible on the Dungeons page where "Floor Progression", "What Changes Inside Dungeons", "Dungeon Gear Rules", and "Scoring & Secrets" are separated by ~300px of nothing).

**Fix:** Either remove `.reveal` from content within pages (keep it for landing cards only), or immediately reveal all elements on the active page when `showPage()` is called:
```js
target.querySelectorAll('.reveal:not(.visible)').forEach(el => el.classList.add('visible'));
```

### 2. Callout Emoji Leaking Into Page
Every `.callout` uses a `::before` pseudo-element for its emoji icon. Since all pages exist in the DOM simultaneously (just `display: none`), the emojis from hidden pages leak into the accessibility tree and show up as visible text at the bottom of the content area. The snapshot shows long strings of emoji text like `⚠️ 💡 ❌ 💡 🔥 ⚠️...` appearing between sections.

**Fix:** The callout `::before` content is rendering as text nodes in the `.main` container because the hidden `.page` elements still generate pseudo-element content. Set `.page { visibility: hidden; }` in addition to `display: none`, or restructure so callout icons use actual elements rather than `::before`.

### 3. Mobile: Text and Tables Clip Off-Screen
At 375px width, body text runs off the right edge with no wrapping (visible in the Slayers page — "Slayers are repeatable boss fights that unlock p..." clips mid-word). Tables overflow horizontally with no scroll container, cutting off the rightmost columns ("Key Unlocks" and "Token" columns are unreadable).

**Fix for tables:** Wrap tables in a horizontally-scrollable container:
```css
.table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
```
**Fix for text clipping:** The `body { overflow-x: hidden }` is hiding the overflow instead of preventing it. Check for elements with fixed widths or padding that push content beyond the viewport.

## Moderate

### 4. Search Only Matches Page Titles
The search index only indexes page titles and group names — not the actual content within pages. Searching for "Bonzo" or "Spirit Bow" or "Livid Dagger" returns nothing. For a guide this comprehensive, content-level search would be a huge improvement.

### 5. Tab Bar Is Declared But Non-Functional
`selectTab()` has a comment `// Future: show/hide tab content sections` — tabs render and can be clicked, but they don't actually filter or change content. The Skills page shows tabs via `data-tabs` attribute but nothing happens when you switch between them. Either implement tab functionality or remove the tab bar to avoid confusion.

### 6. Sidebar Doesn't Scroll to Active Item on Load
When you navigate directly via hash (e.g., `#crimson-isle`), the sidebar highlights the correct item but doesn't scroll it into view on initial load. Items near the bottom of the long nav (Crimson Isle, The Rift, Events Calendar, Pets, etc.) require manual scrolling to find.

### 7. No Back-to-Top Button
Long content pages (Slayers, Dungeons) require extensive scrolling. There's no floating back-to-top button or any way to quickly return to the top short of scrolling manually.

### 8. `overflow-x: hidden` on Body Masks Layout Bugs
`style.css:83` — This hides horizontal overflow globally instead of fixing the source. On mobile, this means content that exceeds the viewport just gets clipped silently rather than being scrollable or properly responsive.

## Minor

### 9. Sidebar Footer Truncation
"v2 — Nether Slate" in the sidebar footer uses `white-space: nowrap; overflow: hidden` but has no `text-overflow: ellipsis`, so it could silently clip on narrower sidebar states.

### 10. Landing Cards Navigate to First Item in Group, Not Overview
Clicking "Getting Started" on the landing page goes to `setup-mods` (the first nav item in that group), not to any overview page for that category. This works but might confuse users expecting a section overview.

### 11. No Way to Return to Landing Page
After navigating away, clicking the "SkyBlock Guide" logo/header does nothing. There's no way to get back to the landing page without clearing the hash manually.

### 12. Arrow Key Navigation Uses Left/Right
`ArrowLeft`/`ArrowRight` navigate between pages sequentially, which is unintuitive — most users would expect these for horizontal actions (like tab switching), not vertical page navigation. Could conflict with text selection or horizontal scrolling.

### 13. No Focus Styles on Nav Items
Nav items use `cursor: pointer` and hover styles, but have no visible `:focus` indicator for keyboard users. The `div` elements with `data-page` aren't focusable by default (no `tabindex`), making the sidebar keyboard-inaccessible.

### 14. Sidebar Search Trigger Missing Keyboard Activation
The search trigger has `role="button" tabindex="0"` which is good, but doesn't respond to `Enter`/`Space` keypress — only click events are bound. Keyboard users can tab to it but can't activate it.

### 15. Useful Resources Page Has No Hyperlinks
Every external resource (Hypixel Wiki, SkyCrypt, Bazaar Tracker, Coflnet, Modrinth, etc.) is listed as bold text with a description, but none are actual clickable links. The entire purpose of a resources page is to send users to those tools — without hyperlinks, users have to manually search for each one. The mod entries (Skyblocker, SkyHanni, Firmament) also lack links despite having well-known GitHub/Modrinth pages.

### 16. Sidebar "Skill Guides" Category Redundancy
The sidebar has a "SKILL GUIDES" category header containing a single item also called "Skill Guides." This reads as unfinished — either the individual skills should be broken out as sidebar entries (matching the tab bar on the page), or the category header should directly link to the page without the redundant child item.

## Content & Information Architecture

### 17. Skill Guides Page Is a Dead End Pretending to Be Ambitious
13 tabs declared, none functional, and the content behind them is just bullet-point summaries that repeat what's already on other pages. The Farming section says "Sugar Cane, Nether Wart, Pumpkin/Melon farming in Garden" — the Garden page already covers this. Mining says "Commissions in Dwarven Mines" — the Mining & HotM page already covers this. Every skill section is 4-5 bullets that could be replaced by a cross-link.

The page promises "Detailed leveling guides for all 12 skills" and delivers none. Either write actual skill guides with XP rates, method comparisons, and breakpoints — or delete it and add a "Leveling Priority" section to the existing Skills page. As-is, it damages credibility because the reader sees the promise, clicks a tab, nothing happens, reads the content, and finds a wiki summary.

### 18. Diana Event Is a 1-Line Redirect Page
The entire page is: "Diana's Mythological Ritual is covered in the Events Calendar page alongside all other events." This is a sidebar item with its own nav entry that exists solely to point elsewhere. Either merge it into Events Calendar (remove the nav item) or put real content on it. Having it as a page signals it was planned but never written.

### 19. Page Granularity Is Uneven — Several Pages Are Too Thin
Some pages are substantial (Dungeons: ~90 lines, multiple tables and callouts). Others are skeletal:
- **Chocolate Factory**: ~50 lines of HTML
- **Sacks & Inventory**: ~46 lines of HTML
- **Profile Types**: ~84 lines of HTML

If a page is <60 lines of HTML, it should either be expanded or merged into a related page. Sacks & Inventory could live under Core Mechanics. Profile Types could live under Core Mechanics. Chocolate Factory could be a section within Events Calendar or a general "Island Features" page.

### 20. Events Calendar Page Doubles as a Money-Making Guide
The "Event Investment" section at the bottom teaches a money-making strategy — buy during events, sell between. Genuinely useful but buried in a calendar page. A reader looking for money methods won't think to check the events calendar. Either cross-link it from Money Making or move the strategy content there and keep the calendar as pure reference.

### 21. Repeated Information Across Pages With No Single Source of Truth
The Cleaver upgrade path appears on: Early Game, Gear Progression, and (implicitly) Dungeons. The dungeonization rules appear on both Dungeons and Gear Progression. The correction about AOTD appears on Early Game and Gear Progression. If any of these gets updated, the others go stale. The guide needs to pick one canonical location per topic and cross-link from others, not duplicate.

### 22. Sidebar Ordering Doesn't Match Progression
Galatea & The Park, The End, and Crimson Isle are ordered roughly by geography, not by when a player would encounter them. A new player following the sidebar top-to-bottom hits Enchanting & Potions before Early Game, because Content Areas is listed before Progression. The sidebar groups mitigate this, but within groups the ordering should reflect "do this first" → "do this later."

Specifically: Early Game should come *before* Core Systems in the sidebar, or at minimum be in the same group. A new player should see "First Day → Early Game → Core Mechanics" not "Setup → Core Mechanics → Early Game."

## Writing & Credibility

### 23. The Guide Tells WHAT but Rarely WHY
The Bestiary page says "focus on mobs you are already killing" but doesn't say *why Bestiary matters for your build*. How much HP do you realistically get from milestones by mid-game? Is it worth optimizing for, or just a background process? The Collections page lists mechanics but never says which collections are *urgent* to unlock vs. which are traps. The Equipment Slots page likely lists slots without saying which ones have the best stat-to-cost ratio.

The correction callouts do a much better job at this — "AOTD is outdated because X, the correct path is Y" — but the positive recommendations rarely explain *why this over alternatives*. A new player can't evaluate advice they can't reason about.

### 24. Useful Resources Page Has No Opinions
Beyond the missing hyperlinks (Issue #15), the deeper problem is editorial: the page has zero opinion about what to use when. "Bazaar Tracker — real-time Bazaar prices and flip opportunities" tells a reader nothing about whether they should use Bazaar Tracker or Coflnet or `crafts.py`. A resources page should rank, compare, and recommend — not just catalog.

### 25. Correction Callouts Are the Best Differentiator — But Not Leveraged
The correction boxes ("AOTD is outdated", "Bazaar doesn't count for collections", "F4 should be skipped") are the guide's differentiator over the wiki. But they're scattered with no way to see all corrections at a glance, and a new reader doesn't know the guide *has* this feature until they stumble on one.

Consider: a dedicated "Common Misconceptions" page or section that collects all corrections in one place, with links to the relevant page for context. This would be the single most trust-building page in the guide and a strong hook for sharing.

### 26. No "Verified Date" Metadata on Pages
The `verified-date` CSS class exists but isn't used on any page. The meta tag promises "Verified mechanics, corrected misconceptions" — but the reader has no way to know *when* anything was last verified. SkyBlock changes constantly. A "Last verified: Feb 2026" tag on each page would massively boost trust and signal that this isn't abandoned wiki content.

### 27. Skill Guides Page Breaks the Tone
Most pages read like a knowledgeable friend explaining things. The Skill Guides page reads like auto-generated wiki stubs. Compare: "SkyBlock is enormous and intentionally overwhelming — this checklist cuts through the noise" (First Day) vs. "Leveled by chopping trees. Cap is 54, not 50" (Skill Guides). The latter is a fact dump with no personality.

## Design & Architecture

### 28. 229KB Single HTML File Is a Scalability Concern
All 37 pages, 278 reveal animations, and 112 callouts live in one file. At 229KB HTML + 24KB CSS + 13KB JS + 200KB images = ~466KB total. Reasonable *now*, but every new page makes it worse. The architecture works for a 10-page guide; at 37 pages it's straining. A reader loads ALL content even though they'll read maybe 3-5 pages per session.

For a static guide this is defensible — no build tooling, instant deployment, works offline. But if any page ever gets significantly longer (like actual skill guides), the single-file approach will become a real performance issue on mobile.

### 29. SVG Icons Are Inlined Everywhere
Every nav item, every landing card, every section header has a full inline SVG. These are Lucide icons — they could be a single `<defs>` block at the top with `<use>` references, or an icon font/external SVG sprite. ~130+ inline SVGs × ~200 bytes average = ~26KB of just icons. Readable and maintainable, but adds weight that scales linearly with page count.

## Priority Order

**UX Bugs (from original review):**
1. Reveal animation gaps — most visible, affects every content page
2. Mobile text/table clipping — guide is unreadable on mobile for data-heavy pages
3. Useful Resources missing hyperlinks — defeats the purpose of the page
4. Callout emoji leaking — accessibility and visual noise issue
5. Tab bar implementation — either finish it or remove it
6. Content search — would significantly improve navigation for a 30+ page guide
7. Sidebar Skill Guides redundancy — minor but looks unfinished

**Content & Architecture (from editorial review):**
1. Skill Guides page — most damaging to credibility, promises and doesn't deliver
2. Correction callouts collection page — highest-value addition for trust
3. WHAT-not-WHY across pages — most pervasive writing issue
4. Repeated information / no canonical source — maintenance debt
5. Diana Event redirect page — easy fix, remove or populate
6. Thin pages needing merge or expansion — structural cleanup
7. Verified date metadata — easy win for trust
8. Sidebar ordering — moderate impact on new-player experience
9. Events Calendar money strategy buried — cross-link fix
10. Useful Resources needs opinions — editorial improvement
11. Skill Guides tone break — rewrite when the page is rebuilt
12. SVG deduplication — optimization, not urgent
13. Single-file scalability — monitor, not urgent
