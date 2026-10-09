---
type: journal
date: 2026-10-08
tags: [journal, offers, client, build, replies]
---

# Building spec 0013: the offer in the client's words

Spec: `docs/specs/0013-offer-in-client-words/`. Scope feature 15. Design: [[offer-in-client-words-design-2026-10-08]].

Built on top of spec 0012's staged, uncommitted work (muhammad's choice), so the working tree diff holds both specs until he commits.

## Counts (AC-11)

- Before: 667 passed, 4 skipped, 139 integration tests ran. After the reseed: 675 passed, 4 skipped, 142 integration tests ran. The four skips are the JWKS tests, as before.
- The +8 reconciles as +8 `replies` refusal cases, +2 summary refusal cases, +3 turn tests (`thought_reframe` offer, Tell me more, an offer a concern drops), +1 eval scoring test, and −6 from `test_a_framework_line_carries_nothing_from_a_worked_example`, which runs once per framework line and lost the six `Offer:` lines. I nearly reported it as "added 14, got 8, fine". Diffing `pytest --collect-only` per file against `git archive $(git write-tree)` found it.
- The six names and descriptions were checked against the intro .docx (`word/document.xml`), not only against the spec's table: all six appear word for word, with "This Framework" capitalised there.

## Things worth knowing

- **The Tell me more reply carries a technique button too** (its Yes, let's try it). So in `eval_replies.py`, `Exchange.offered` already marks both replies the code writes, and AC-13 needed no new field.
- **`offer` is a local name in `orchestrator.send`** (`offer = pending_offer(history)`), so the module is imported as `offer as offers`.
- **Taps in tests now go through the seeded labels.** After an offer turn the stored options are the code's, so a test that taps the label its scripted model wrote ("Try it") no longer matches. `test_tapping_the_offer_records_acceptance` now scripts "Let's do it" on purpose, to prove the label the model writes is never shown.
- **An offer turn records no style**, and `test_the_turn_is_stored_and_the_thread_state_follows_it` was the only turn level test that a style is recorded at all. It became two turns, an ordinary reply whose style is kept and an empty text offer whose style is not, so that coverage is not lost.
- The reseed left muhammad's `fastapi dev` alone: its reloader had already restarted the worker on the code change, and the cache takes new rows within 300 s. Old code would have refused the new `replies` row (`extra="forbid"`), so the order is code first, then seed, locally too.

## Noticed, not fixed

- `.claude/BACKEND.md`'s `chat/` line names `router.py` and `ending.py`, and neither file exists in `mani/chat/`.
- `PORT-STATUS.md` "Status, 2026-10-01" still says 641 passed.
- AC-12 asks that "scope feature 15's row links this spec" in `PORT-STATUS.md`, which has no feature rows. The scope's feature 15 already links spec 0013.
- The spec says showing the framework name is "already on the client list". It was not, so it went into the new lead line there.

Related: [[client-cadence-build-2026-10-08]], [[prompt-word-budget-and-yaml-yes-key-2026-10-07]], [[seeded-content-turns-dormant-paths-live-in-tests]]
