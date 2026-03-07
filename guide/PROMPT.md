You are reviewing the SkyBlock guide at ~/projects/hypixel-skyblock/guide/ as a critical, opinionated
reviewer — not a bug finder. ISSUES.md already captures the known UX bugs. Your job is to find
problems that a bug-oriented review would miss.

Read ISSUES.md first so you don't duplicate anything already listed there.

Then read the guide's HTML, CSS, and JS thoroughly. Critique it across these dimensions:

**Content & Information Architecture:**
- Are pages the right granularity? Should any be split or merged?
- Is anything important missing that a new SkyBlock player would need?
- Does the page ordering in the sidebar match how a player would actually progress?
- Are there pages that are too thin to justify existing as separate pages?
- Do the callout boxes (tips, warnings, corrections) add value or are any of them noise?

**Writing Quality:**
- Is the tone consistent across pages? (Some may have been written at different times)
- Are there places where the guide tells you WHAT but not WHY?
- Does any section read like a wiki dump rather than a guide?
- Are there walls of text that should be restructured?

**Design Decisions:**
- Is the single-page-app architecture the right choice for this content?
- Are there CSS patterns that are fragile or over-engineered?
- Is the JS doing things that CSS alone could handle?
- How big is the total payload? Is it reasonable for what this is?

**Credibility & Trust:**
- Would a reader trust this guide? What signals trust or undermines it?
- Are sources cited where claims are made?
- How does this compare to what else exists for SkyBlock guides?

Be blunt. Don't pad criticism with compliments. If something is fine, skip it and focus on
what isn't. Deliver your findings as a ranked list with the most impactful issues first.
