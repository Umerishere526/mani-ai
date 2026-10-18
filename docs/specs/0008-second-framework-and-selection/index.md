# 0008. Thought Reframe as the second active framework, and selection between them

**Date**: 2026-10-17
**Status**: Built; live run owed

## Summary

The client sent the Thought Reframe cadence document (2026-10-17): five steps, per-style wording, each
step named once as it opens, the somatic check-in mandatory at the end, and the rule that ABCDE takes
priority only when both frameworks fit equally ([message](../../client/messages/2026-10-17-thought-reframe-cadence.md),
R19). muhammad asked for it activated beside ABCDE without changing the chat's functional properties
(the gates, the stage contract, the body cadence), for the pinpointed core issue and feeling to drive
which framework is offered, for dead content values to be cleaned, and for a repeatable recipe for the
remaining four paused frameworks.

The machinery built for this was already mostly multi-framework (`Registry`, the Framework Index, the
stage contract of spec 0007). Two code spots assumed exactly one active framework, and one real schema
gap surfaced while building: `thread_technique_state` is a singleton row per thread, so "finish one
framework, then a different one may be offered sooner than its own cooldown" needed history that row
cannot hold.

## Decisions

1. **Selection is a hybrid: the model picks, code guards the tie and the fallback.** The Framework
   Index already renders every active framework's `central_indication`, its pairwise `distinctions`
   and `contraindications`. The model reports `heading_toward` from the pinpointed core issue and
   feeling, same gate as spec 0006/0007 (no offer before problem → core issue → control → confirmed
   reading). `repairs.offer_framework` resolves a reported id that is active and not excluded, else the
   first offerable id in the registry's order (lowest `display_order` — the client's "ABCDE wins a tie"
   rule, generalised past exactly two sets), else none. One active framework collapses to exactly
   today's behaviour.
2. **The selection reason is stored, not logged.** `Reply.heading_reason` (CHECK_OPEN only): one
   sentence, from their words, for why this set fits. Stored as
   `thread_technique_state.offered_because` (≤200 chars, migration 027) — never read by anything that
   decides what happens next, surfaced only in `AI_DEBUG_MODE` (`Turn.offered_because`, the chat-tester
   caption, `scenario_check.py`). Joinable later with `body_response`/`conversation_helped` for
   reviewing selection quality at scale.
3. **After a completed framework, a different one may be offered sooner than its own cooldown; a
   decline still paces the next check globally.** `thread_technique_state` is one row per thread
   (its primary key is `thread_id` alone) and only ever remembers the single most recent run —
   insufficient for "exclude the one just finished, but not a different active framework". Migration
   027 adds `thread_technique_runs`, appended once per finished run (accepted or declined).
   `context.excluded_frameworks(ctx)` reads it: a **completed (accepted)** run excludes only its own
   framework id for `COOLDOWN_AFTER_COMPLETE` (45) messages; a **decline** is not given this
   per-framework treatment and instead continues to block `may_check` globally for
   `COOLDOWN_AFTER_DECLINE` (6) messages, exactly as before two frameworks existed — a "no" or "Keep
   chatting" is never read as "offer me the other one instead". `may_check` and
   `repairs.offer_framework`/`repairs.apply` both take an `offerable: frozenset[str]` computed once per
   turn by the orchestrator (`frozenset(registry.ids) - context.excluded_frameworks(ctx)`); left out
   (tests, or a turn before one is needed), both fall back to the pre-0008 singleton-only behaviour.
4. **Thought Reframe stays lighter than ABCDE, per the client's own rule ("MANI does not turn Thought
   Reframe into ABCDE").** One reflection, at the end (`reframe`) only — "what changes when you see it
   this way?" — not after every step.
5. **The paused `thought_reframe.md` is rewritten to the stage contract (spec 0007), not kept in its
   old shape.** Its five stages (`thought`, `significance`, `facts`, `alternative`, `reframe`) map 1:1
   onto the five client steps; the paused file's separate `closing` stage is dropped, since the
   client's own somatic cadence (R18) is now the mandatory ending. The new PDF's wording (step names,
   intro lines, per-style questions) wins; the paused file's boundaries, `if_unclear` branches,
   contraindications and worked example enrich it where the PDF is silent.
6. **Dead content keys are deleted everywhere, now; a stale DB column is batched into the same
   migration.** `to_find_out`, `appropriate_when`, `not_when`, `redirects` are read by nothing in
   `mani/` (confirmed by a repo-wide grep) and are removed from every framework file, active and
   paused. `threads.vague_streak` (dead since the message-count offer gate it paced was replaced by
   spec 0006's confirmed check, 2026-10-13) is dropped in the same migration that adds the run-history
   table, rather than a second schema push.
7. **`composer.framework_index` drops a distinction pair naming a framework that is not active**,
   rather than rendering it with a guessed label. A paused framework's id looks exactly like any other
   distinction key (both are `snake_case`), so there is no syntactic way to tell them apart except by
   what is actually active; the only non-framework key every framework file uses is
   `continued_conversation`, which still renders. ABCDE's file compares itself only with
   `continued_conversation`, so this never showed; the paused files compare themselves with each other,
   so the next activation would have leaked a pair against a set the model can never offer.

## What this is not

- Not a change to the stage contract, the offer/check gate, the somatic cadence, or any style file.
  Every existing ABCDE behaviour (its tests, its live-run numbers from spec 0007) is unaffected; the
  full Thought Reframe walk integration test passed on the first run with zero changes to `walk.py`,
  which is the proof the stage contract actually generalises.
- Not a framework-selection algorithm beyond "the model judges from the Framework Index, code resolves
  the tie and the exclusion". No keyword rules, no classifier call: the client's own instruction is
  "pinpoint the problem, then its core issue, before deciding", which is exactly the existing check
  gate's job.
- Not an admin review surface. `offered_because` is stored and readable by the thread's owner (RLS) and
  via `AI_DEBUG_MODE`; building a dedicated admin endpoint for it is out of scope here (PORT-STATUS
  already lists "Admin conversation browser" as not built, scoped narrowly when it is).

## Acceptance criteria

- **AC-1**: `content/frameworks/thought_reframe.md` passes `missing_for_activation` with `[]`; its
  offer templates share ABCDE's slot shape (`going_through` inline on every style, a `lead_line` whole
  line on supportive/reflective) so `repairs.slots_for`'s "shape from the first active framework" still
  works with either framework first. `tests/unit/test_thought_reframe_content.py`.
- **AC-2**: Every reply that opens a Thought Reframe stage carries that stage's `intro`
  ("Step N is …"), word for word once, never on a reply that stays; the same `walk.reply_text` as
  ABCDE, no framework-specific branch. `test_a_reframe_walk_stays_lighter_than_abcde_with_one_reflection_at_the_end`.
- **AC-3**: Only `reframe` has a `reflect`; the other four steps move from the reading straight to the
  next step's letter line on their yes. Same test as AC-2.
- **AC-4**: `repairs.offer_framework(heading_toward, registry, offerable)`: a reported id in
  `offerable` wins; otherwise the first id of `registry.ids` that is in `offerable`; otherwise `None`.
  `test_with_no_pick_the_first_offerable_set_wins_the_tie`,
  `test_with_everything_excluded_the_offer_is_still_dropped`.
- **AC-5**: `thread_technique_runs` (migration 027): one row per finished run, RLS scoped to the
  owner, insert-only for `mani_service` (never update or delete), FK-indexed, read into
  `TurnContext.recent_runs`. `tests/sql/test_grants.sql`, `scripts/test_db.sh --local`.
- **AC-6**: `context.excluded_frameworks(ctx)` excludes a framework only while its most recent
  **accepted** run (the singleton row or a `thread_technique_runs` row) is within
  `COOLDOWN_AFTER_COMPLETE` messages of ending; a **declined** singleton row is never added to the
  exclusion set by this function. `context.may_check(ctx, offerable=...)` additionally blocks every
  check for `COOLDOWN_AFTER_DECLINE` messages after a decline, regardless of `offerable`.
  `test_a_finished_framework_can_be_followed_by_a_different_one_sooner_than_its_own_cooldown`,
  `test_a_decline_blocks_every_check_for_its_own_cooldown_not_just_the_declined_set`.
- **AC-7**: `thread_technique_state.offered_because` (migration 027, ≤200 chars) is written on every
  fresh offer row from `reply.heading_reason`, truncated; read back into `Turn.offered_because` and
  `TurnOut.offered_because` only under `AI_DEBUG_MODE`; never part of any query that decides behaviour.
- **AC-8**: `threads.vague_streak` is dropped (migration 027); every reference in
  `tests/sql/test_grants.sql` is removed, not just the column.
- **AC-9**: `to_find_out`, `appropriate_when`, `not_when`, `redirects` exist in no framework file,
  active or paused, after this change. `composer.framework_index` renders a distinction pair only when
  both sides are in the registry or the non-framework key `continued_conversation`.
  `test_a_distinction_naming_a_set_that_is_not_active_is_dropped_not_guessed_at`.
- **AC-10**: `scripts/scenarios.json`'s `pinpoint_and_check` group gains `cheat_sheet_thought_reframe`
  (`expect.offers: thought_reframe`) and pins `expect.offers: abcde` on `cheat_sheet_abcde` and
  `cheat_sheet_problem_solving` (the latter stays ABCDE while Structured Problem-Solving is paused).
  `scenario_check.py` flags an offer that does not match `expect.offers` and prints the stored reason.

## The recipe for the next framework

No code changes per framework, once this spec's machinery exists:

1. File the client's cadence document under `docs/client/messages/`, with a "what we drew from it"
   section and a new requirement row.
2. Rewrite the paused file's stages to the stage contract (`parts`, `intro`, `reflect`, `when_stuck`,
   `confirm`, `stop_pushing`) and its `offering` block to the shared offer slot shape. Keep the paused
   file's boundaries, `if_unclear` branches and contraindications where the new material is silent.
3. Write `distinctions` against every framework that is already active (not every paused one — the
   index drops anything not active, AC-9).
4. Move the file from `content/frameworks/paused/` to `content/frameworks/`; `display_order` decides
   its tie-break position. `missing_for_activation` fails loudly in the seed step, not in a live chat,
   if a key is missing.
5. Write the framework's own content test (mirroring `test_thought_reframe_content.py`), one full-walk
   integration scenario, and cheat-sheet selection scenarios in `scenarios.json` against every
   already-active framework.
6. Live run in three styles before calling it done (R5/the cadence quality bar is unchanged by which
   framework is running).

## Follow-up

- [ ] Live run of `cheat_sheet_thought_reframe`, `cheat_sheet_abcde`, `cheat_sheet_problem_solving` in
  three styles (needs muhammad's yes — real model calls).
- [ ] Tell the client: the offer's step list is gone (R11 conflict, recorded 2026-10-17); the letter
  line change history (R12); that Structured Problem-Solving is the better fit for her own "coworker in
  a bad mood" test chat by her own cheat sheet, and ask whether it should come off pause next.
- [ ] Migration 027 is applied locally only. Hosted was last compared on 2026-10-07; compare it again
  before pushing (PORT-STATUS, Open engineering).
- [ ] If an admin review surface for `offered_because` is wanted, scope it as its own small addition —
  not built here.
