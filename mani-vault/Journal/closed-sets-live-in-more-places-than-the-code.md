---
type: journal
date: 2026-10-07
tags: [journal, prompts, router, gotcha]
---

# Closed sets live in more places than the code, and fallbacks hide what a gate costs

Found while designing spec 0007 (model facing text out of Python).

- **The six reply shapes were in three places**: `SHAPES` in `schema.py`, `reply_shapes` in
  `mani_base.md`, and a CHECK constraint in migration 003 (`response_styles_shape_known`). The first
  draft moved the list into content and missed the database. A shape added in the portal would have
  passed the guard and then failed the insert, losing the turn. An independent cross check caught it.
  Before moving a closed set, grep `supabase/migrations/` for its values too.
- **The closest fit was the only guaranteed path to an offer.** Removing it while making the router's
  shortlist the offer gate means the phrase lists' reach caps every offer. The router also scored only
  the last four messages (`RECENCY_WEIGHTS`), which is harmless as a ranking hint and wrong as a gate:
  an early sign drops out. When a hint becomes a gate, recheck everything that shaped the hint.
- **muhammad's preference on routing** (2026-10-07): every framework gets an equal chance and Mani
  decides from the person's situation; router and model must both see the fit; no nearest fit
  offers; when a person asks for a kind of help, Mani explores and steers rather than offering on the
  spot.

Related: [[prompt-text-names-index-sections]], [[client-lines-the-code-matches-exactly]].
