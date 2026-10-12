# Scope: Mani lean prompts

Mani is a mental health companion. This scope covers how Mani talks to the model: a short base prompt of general rules, each framework in about 8 lines saying when it starts, when to skip it and when it ends, nothing hardcoded in prompts or in Python, no checks that redraft or rewrite the reply, and a thinking level set on every call. The goal is fewer tokens and lower latency now, and prompts that get better as models get faster.

**Build approach:** Tracer Bullet (take ABCDE through the whole lean path first, measure it, then repeat for the other frameworks).
**Workflow:** Beta (check verify, then test). The replies are health content, so a real conversation through the backend is the proof, not unit tests alone. Every real model run needs muhammad's yes first, because it spends the client's credit.

_These are recommendations to keep your build orderly, not requirements. Skip anything that does not fit._

## At a glance

| #   | Feature                                  | Phase    | Status      |
| --- | ---------------------------------------- | -------- | ----------- |
| A   | Chat turn pipeline                       | Existing | existing    |
| B   | Six frameworks and the body check in     | Existing | existing    |
| 12  | No offer before a real conversation (R1) | Now      | in-progress |
| 13  | Faster turns (R2)                        | Now      | in-progress |
| 14  | Styles from the client's document (R8, R9) | Now    | in-progress |
| 15  | General judgment over case patches       | Now      | in-progress |
| 16  | Structured reply fields in place of text parsing | Next | planned |

## Already built

### A. Chat turn pipeline · existing

One turn: safety screen, router shortlist, system prompt (base, framework index, response format), `[ctx]` block, model call, repairs. code in backend/mani/chat/, backend/mani/prompts/, backend/mani/llm/

### B. Six frameworks and the body check in · existing

ABCDE, Thought Reframe, Structured Problem Solving, ACT Choice Point, Behavioral Activation and DBT STOP, each 300 to 390 lines, plus the body check in merged into every framework at seed time. code in backend/content/, backend/scripts/seed.py

## Now: client blockers

### 12. No offer before a real conversation (R1) · in-progress

Mani listens before it offers a framework. Code owns one offer window, the same in every style: it opens at the person's third message and the best fit is due at their fifth. The prompts follow the window and never decide timing themselves.
**Done when:** no offer comes before their third message in any style, the best fit is offered by their fifth, a model offer before the window is stripped, and live runs in all three styles show it.

- [x] Build it: `/develop no offer before a real conversation`
  - [x] `offer_window` in context.py replaces cooldown_passed, closest_fit and offer_fit, with its tests
  - [x] Prompt cuts in mani_base.md and response_format.md, reseeded
  - [x] scenario_check flags an early offer; resentful_coworker scenario added
- [x] Verify it: `/check verify no offer before a real conversation`
- [ ] Test it: `/test no offer before a real conversation`
      Decision in [PORT-STATUS.md](../../backend/PORT-STATUS.md#decisions-in-force) (first offer window), requirement [R1](../client/requirements.md#requirements). No spec, by muhammad's choice (2026-10-12).

### 13. Faster turns (R2) · in-progress

One chat call per turn at a low thinking level, with no redraft. Code shapes the reply instead of asking again: no offer field before the offer window opens, and the stage label is set from the model's own ledger.
**Done when:** every turn makes one chat call, the chat call and exercise pick run at `low`, redraft is gone and its lost checks only log, scenario_check prints each turn's time, calls and tokens, and a measured run (after muhammad's yes) shows a median of 4 s or less and a slowest of 10 s or less in all three styles.

- [x] Build it: `/develop faster turns`
  - [x] Honest cost rows and per turn timing in scenario_check (feature 1's first milestone, slim)
  - [x] Effort `low` for the chat call and the exercise pick
  - [x] Reply schema per offer window, step from the ledger, redraft loop removed, lost checks logged
  - [x] PORT-STATUS decisions, journal, requirements row, and feature 12's Done when reads "stripped"
- [ ] Verify it: `/check verify faster turns`
- [ ] Test it: `/test faster turns`
      Decision in [PORT-STATUS.md](../../backend/PORT-STATUS.md#decisions-in-force) (one chat call at effort `low`), requirement [R2](../client/requirements.md#requirements). No spec, by muhammad's choice (2026-10-12). code in backend/mani/chat/reply_checks.py, backend/mani/chat/orchestrator.py, backend/mani/llm/. A live run for the 4 s and 10 s target is owed (muhammad's yes).

### 14. Styles from the client's document (R8, R9)

Each style gets its own prompt file written from the client's behavior lists, and only the chosen one reaches the model. Rules shared by every style that contradict the client's document are cut, and the stored value becomes `directive`.
**Done when:** the system prompt carries exactly one style file, chosen from the thread; no style rules remain in `mani_base.md`, `context.py` or `response_format.md`; `direct` is renamed `directive` everywhere (DB, code, content, tests, tester); the contradicting base rules are cut, and a measured run (after muhammad's yes) in all three styles shows Directive leading, Supportive accompanying, Reflective mirroring then asking.

- [x] Build it: `/develop styles from the client's document`
  - [x] Rename `direct` to `directive` (migration 019, code, content, tests)
  - [x] Three style prompt files, one composed per thread; framework index prints only the chosen style
  - [x] Cut the contradicting rules in mani_base, `[ctx]` and response_format; scenario_check measures behavior, not shared words
  - [x] Client document recorded, requirements conflict rows, PORT-STATUS decisions edited in place
- [ ] Verify it: `/check verify styles from the client's document`
- [ ] Test it: `/test styles from the client's document`
      Requirements [R8, R9](../client/requirements.md#requirements). No spec, by muhammad's choice (2026-10-12). Design in the approved plan of 2026-10-12: one style file in the system prompt after `response_format`, framework index for the chosen style only, the client's bullets plus two examples per style. code in backend/content/prompts/style_*.md, backend/mani/prompts/composer.py, backend/mani/chat/context.py, backend/supabase/migrations/019_conversation_style_directive.sql. A live run of the four client scenarios is owed (muhammad's yes).

### 15. General judgment over case patches · in-progress

Mani reads the person with the model's own judgment, from one general rule per idea. There are no per case prompt lines, and the eval checks behavior rather than collecting one scenario per bug.
**Done when:** each fit rule lives in one place, using the slot test; the copies, word lists, case examples and paused framework rules are gone from the prompts; `[ctx]` no longer sends `open`; at `due` Mani checks understanding and never forces an offer; the dead imminent action and veto paths are deleted; scenarios are grouped by behavior with machine checked expectations (earliest and latest offer, must not offer); and a live run (after muhammad's yes) shows no offer from an event or behavior alone.

- [x] Build it: `/develop general judgment over case patches`
  - [x] Eval first: behavior groups with expectations, fix the line 3 blind spot, drop "closest" from the leak check (baseline run skipped by muhammad; "must not offer" not added, no conversation needs it yet)
  - [x] Fit rule in one home (`abcde.md` `central_indication`, slot test wording), copies cut from `mani_base.md` and `response_format.md`
  - [x] Prompt cuts: word lists, slot examples, paused framework rules, step 1 duplicates, "nearest", "Finding the fit" no longer "from their first message", schema case examples
  - [x] Window: `open` line removed, `due` becomes check understanding; dead paths deleted; Decisions in force edited in place
- [ ] Verify it: `/check verify general judgment over case patches`
- [ ] Test it: `/test general judgment over case patches`
      Requirements [R1, R3, R8](../client/requirements.md#requirements). No spec: the decisions were made in the /scope panel of 2026-10-12 (two features; `due` checks understanding and never forces; the slot test wording; dead paths deleted now). code in backend/content/prompts/, backend/content/frameworks/abcde.md, backend/mani/chat/context.py, backend/mani/chat/orchestrator.py, backend/scripts/scenario_check.py, backend/scripts/scenarios.json. The live run is owed (muhammad's yes).

## Next

### 16. Structured reply fields in place of text parsing · needs a decision

The model reports what code currently guesses from text: its own offer line, where they feel it, whether they declined, and whether this reply ends the framework. Code then places the client's fixed text, and the regexes go.
**Done when:** no regex or phrase list reads meaning from the person's or the model's words outside the safety screen, and every gate stays keyed on database state, never on these fields.

- [ ] Design it (spec): `/architect structured reply fields`

## Legend

**The decision box.** Every feature carries one sub task ending in `(spec)`. Skills find it by that suffix.

- **Next step** is the first unticked box.
- **needs a decision** means run `/architect` first. The tag drops once the spec is captured.
- **Status** goes `planned`, `in-progress`, `done`, plus `existing` (built before this workflow) and `dropped`.
- **Workflow tier tag** beside a heading (`· GA`) raises that one feature above the project default.
