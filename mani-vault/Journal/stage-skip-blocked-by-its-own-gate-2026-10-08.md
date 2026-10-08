---
type: journal
date: 2026-10-08
tags: [journal, frameworks, stages, router, gotcha]
---

# Frameworks re-ask what the offer gate already required

Found while scoping features 12 and 13 (`docs/scope/scope.md`).

## The contradiction

Every framework's `Starts when` line says Mani must already know the early stages before it may offer (ABCDE: the event, what it came to mean, how believing it shapes them, which is A, B and C). Then the stage machine walks from the first stage again. The better Mani understands before the offer, the more repetitive the framework feels.

## Three places hold the walk in order

- `Registry.clamp` in `backend/mani/chat/techniques.py` records at most one stage forward per turn. A reply jumping from A to D is stored as B, and the next `[ctx]` says `stage: belief`, so Mani asks B again. This is the "repeats an answered stage" muhammad saw live.
- `mani_base.md` `in_a_framework` says "never skip a stage".
- `response_format.md` `framework_starting` allows exactly one skip, on the accepting turn.

Changing only one of them changes nothing: the other two pull the pointer back.

## The ending cap has a gap

`ending_turn_cap` counts from `ending_from`, which is set only once the stored stage is `somatic_checkin` or `somatic_practice`. A framework stuck on `closing` or earlier has no backstop, and while it runs the router is off, so nothing else can be offered. Not seen live yet.

## The router misses plain phrasing

"I've been avoiding my friends because I've been overwhelmed, and I feel guilty about ignoring them" gets an empty shortlist from `router.shortlist`. With no closest fit (spec 0007), that means no offer at all. Check a sentence like this against the router (no model, no database: load the frontmatter of `content/frameworks/*.md` and call `router.shortlist`) before assuming triggering works.

## muhammad's calls

- The stage ledger: the model reports known, partial or missing per stage in the same one call, and the code picks the next stage from it.
- A work stage (examine, balanced, choose, first action) counts as known only in the person's own words.
- Triggering is its own feature, because it reverses spec 0007's no closest fit.

Related: [[body-ending-build-2026-10-08]], [[model-text-out-of-python-build-2026-10-07]]
