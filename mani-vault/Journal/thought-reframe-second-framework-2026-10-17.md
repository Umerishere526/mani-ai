---
type: journal
date: 2026-10-17
tags: [journal, frameworks, selection, thought-reframe, schema, lessons]
---

# Thought Reframe as the second framework (2026-10-17)

Lolly's Thought Reframe document (R19) and muhammad's ask: activate it beside ABCDE without touching what
works, let the pinpointed core issue pick between them, and leave a recipe so the other four are content only.
Spec 0008 holds the decisions and the recipe; this note is what was learned.

## What went right

- The stage contract of [[stage-contract-parts-2026-10-17]] generalised: the full Reframe walk test passed on
  its first run with no change to `walk.py`. Writing the contract as data instead of per-letter code paid off
  on its first reuse.
- Selection needed almost no code. The model already reported `heading_toward` from the Framework Index;
  the only change was the fallback (first offerable set in `display_order`, which is Lolly's "ABCDE wins a
  tie") and a stored one-line reason.

## What surprised us

- `thread_technique_state` is one row per thread (primary key `thread_id`). It can only remember the most
  recent run, so "finish ABCDE, then Reframe may come sooner than ABCDE's own 45-message cooldown" had nothing
  to read. Asked muhammad; added `thread_technique_runs` (migration 027) rather than overloading the row.
- First cut excluded declined frameworks per framework too. An existing integration test failed: a decline
  then let a check open for the *other* set almost at once, which reads a "no" as "offer me something else".
  Fix: only a completed run is per framework; a decline still paces every check. The test was right and
  caught a behaviour change muhammad had not asked for.
- `repairs.slots_for` takes the offer's slot shape from the first active framework. Every framework's offer
  templates must share that shape (an inline `<going_through>` slot, a whole-line lead slot on Supportive and
  Reflective). The seed gate caught Reframe's first draft missing it; the content test now pins it.
- The Framework Index would render a distinction pair naming a paused framework, with a label guessed from
  the id (a test pinned that). It never showed because ABCDE's file only compares itself with
  `continued_conversation`, but the paused files compare themselves with each other, so the next activation
  would have leaked it. The index now renders a pair only when both sides are active.

## Lessons

- Before building "per framework" behaviour, check what the schema can remember per framework. A singleton
  row is fine for "what is live now", not for history.
- Decline and completion are different signals and deserve different cooldown scopes.
- The prompt budget test (`CHARACTERS_BEFORE_STRUCTURED_FIELDS`) trips when the index grows; trim wording,
  never behaviour.

## Noticed, not fixed

- `ruff check .` in `backend/` reports 19 findings in files this work did not touch (import order in
  `main.py`, `memory.py`, `summarize.py`, `routers/admin.py` and two tests; unused `noqa` in three scripts;
  nested `with` in `db/pool.py`; a blind `except Exception` in `llm/client.py`). 18 are auto-fixable.
