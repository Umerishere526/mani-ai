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
| 16  | Structured reply fields in place of text parsing | Next | in-progress |
| 17  | The offer shows the five steps (R11)     | Now      | in-progress |
| 18  | The ABCDE walk names each letter and remembers (R6, R12) | Now | in-progress |
| 19  | Questions follow what the person said (R4, R6) | Now | in-progress |

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

### 17. The offer shows the five steps (R11) · in-progress

The ABCDE offer makes clear what A, B, C, D and E stand for before they decide. It is the style's client template with their feeling in the slot ("your anxiety"), then the permission question, then the client's short list of the five steps, reworded to "you". Tell me more keeps the longer per style explanation.
**Done when:** every ABCDE offer, in all three styles, is the style's template with their feeling in the slot, then the permission question, then the five steps; Tell me more still sends the longer explanation and then shows only Try it and Keep chatting.

- [x] Build it: `/develop the offer shows the five steps`
  - [x] `offering.steps` and the feeling slot in `abcde.md`, `repairs.offer_template` shared by the offer and scenario_check, tests, Decision in force edited in place
- [ ] Verify it: `/check verify the offer shows the five steps`
- [ ] Test it: `/test the offer shows the five steps`
      Requirement [R11](../client/requirements.md#requirements). No spec: muhammad decided the shape on 2026-10-13 (list in the offer, Tell me more kept for the longer text). Spec 0003's offer section goes stale. code in backend/content/frameworks/abcde.md (`offering.steps`, the offer slots, `central_indication`), backend/mani/chat/repairs.py (`offer_template`, `_offer_text`), backend/scripts/scenario_check.py. A live run is owed (muhammad's yes).

### 18. The ABCDE walk names each letter and remembers (R6, R12) · in-progress

Once they say yes, Mani walks one stage per reply, and each stage opens with its letter and name, as the client's ABCDE document shows. A stage they already answered is said back in their words and confirmed once, and only a missing one is asked. What they said per stage is stored by code, so it is never asked twice and survives the history window.
**Done when:** every stage opens with its letter and name; one stage per reply; a stage already answered, before or during the framework, is said back with their words and confirmed once, never asked; what they said per stage is stored and still used after it leaves the 20 message window; every turn is still one model call.

- [x] Design it (spec): `/architect abcde walk and memory`
      Requirements [R6, R12](../client/requirements.md#requirements). Spec [0004](../specs/0004-abcde-walk-and-memory/index.md). Reverses the Decisions in force "The chat never names a stage" and "a stage their words already answer is skipped" (muhammad agreed 2026-10-13). Confirming a known stage departs from the document's Situation 1 (see Conflicts in requirements.md).
- [x] Build it: `/develop the abcde walk and memory`
  - [x] Thin walk: migration 020, the stage reply fields, `intro` and client lines in `abcde.md`, the code owned one stage step, missing stages sent as the client's ask (AC-1, AC-2, AC-6, AC-10, AC-11)
  - [x] Memory: the merge, seeding on the start turn, stored words and the branch line in `[ctx]` (AC-3, AC-9, AC-12)
  - [x] Confirm and correct: known, possible and partial render, confirm phrases, fallbacks, corrections and the plain no (AC-4, AC-5, AC-7, AC-8)
  - [x] Cleanup and docs: remove the ledger and skip walk, `ledger_view` on the store, rewrite the broken tests, scenario_check, Decisions in force in place (AC-13)
      code in backend/mani/chat/walk.py, backend/mani/chat/context.py, backend/mani/chat/orchestrator.py, backend/mani/llm/schema.py, backend/mani/db/threads.py, backend/content/frameworks/abcde.md, backend/supabase/migrations/020_thread_stages_known.sql and 021_framework_confirm_phrases.sql. Built 2026-10-13, tested with a scripted model; a live seeded run is owed (muhammad's yes).
  - [x] First live run fixes (2026-10-13): a yes to a check moves on (it stayed on A and sent B's sentence with no letter line); the letter line shares one paragraph with the stage's line; their words in A's slot start lowercase (AC-1, AC-2, AC-4)
      Found live on thread ca968cbd: phase still activate, A known with tries 1. Cause: the field descriptions called the start turn "the turn they say yes", so a yes to a check came back with stage_answer null; reworded to "the turn they accept the offer" (/debug, 3 of 3 replays then moved on). The letter line now shares a paragraph, and their words in A's slot start lowercase (/develop).
- [ ] Verify it: `/check verify the abcde walk and memory`
- [ ] Test it: `/test the abcde walk and memory`

### 19. Questions follow what the person said (R4, R6) · in-progress

Every question, in the chat and inside a framework, builds on the thread so far: question 2 on answer 1, question 3 on answers 1 and 2, keeping what they came with (their feeling and their issue) in view. Code keeps a running understanding of the conversation, updated every turn and sent back on the next, and one positive question rule replaces the framework checklist ("Finding the fit") and the bans on using their feeling. muhammad chose this over OpenAI's conversation API (OpenRouter rejects stored state, and it would not change what the model is told to ask) and over a prompt rewrite alone, on 2026-10-13. Found live the same day: a Directive chat opened "i am frustrated", and after two questions Mani followed ABCDE's checklist instead and offered with their judgment about the client in place of their feeling.
**Done when:** the running understanding is stored per thread, updated each turn, sent back the next turn and still used after the 20 message window; in a live run of the frustrated chat and the client scenarios, in all three styles, each question follows from their previous answers, the feeling they named comes back in a question or the offer, the offer slot holds their feeling word, and nothing is restated as a statement (R3); every turn is still one model call on OpenRouter; and the Decision in force "Questions before an offer ask for what is still missing" is edited in place.

- [x] Design it (spec): `/architect questions follow what the person said`
      Requirements [R4, R6](../client/requirements.md#requirements). Spec [0005](../specs/0005-questions-follow-what-they-said/index.md). The understanding holds their feeling and issue only (muhammad dropped the answers list, 2026-10-13); nothing is stored from a concern turn; it replaces `thread_summaries.current_issue` and spec 0004's yes turn `feeling`.
- [x] Build it: `/develop questions follow what the person said`
  - [x] The record end to end: migration 022 (column, `mani_service` grant, drop `current_issue`), the merge, `understanding_update` in every reply shape, the write, the `[ctx]` line (AC-1, AC-2, AC-4, AC-10, AC-11)
  - [x] Its readers: A's missing slot from the stored feeling, the exercise pick from the issue, `current_issue` and the yes turn `feeling` removed with their tests (AC-7, AC-8)
  - [x] The prompt: the one question rule in `rules`, the four cuts with "Finding the fit" and `to_find_out`, the three offer slot placeholders, reseed (AC-3, AC-6, AC-9)
  - [x] Debug view, the frustrated chat scenario, Decisions in force and docs (AC-12, AC-13)
      code in backend/mani/chat/understanding.py, backend/mani/chat/orchestrator.py, backend/mani/chat/context.py, backend/mani/llm/schema.py, backend/mani/db/threads.py, backend/mani/summarize.py, backend/mani/prompts/composer.py, backend/content/prompts/mani_base.md, backend/content/prompts/response_format.md, backend/content/frameworks/abcde.md, backend/supabase/migrations/022_thread_understanding.sql. The live run (AC-3, AC-5, AC-6) needs muhammad's yes.
- [ ] Verify it: `/check verify questions follow what the person said`
- [ ] Test it: `/test questions follow what the person said`

## Next

### 16. Structured reply fields in place of text parsing · in-progress

The model reports what code currently guesses from text: its own offer line, where they feel it, whether they declined, and whether this reply ends the framework. Code then places the client's fixed text, and the regexes go.
**Done when:** no regex or phrase list reads meaning from the person's or the model's words outside the safety screen, and every gate stays keyed on database state, never on these fields.

- [x] Design it (spec): `/architect structured reply fields`
- [ ] Build it: `/develop structured reply fields`
  - [x] Offer thread: moment selection, schema factory, offer and Keep chatting from the client's templates, offer_answer, safety guard, prompt cuts (AC-1 to AC-4, AC-8 to AC-10, AC-12)
  - [x] Body thread: branch ids in somatic.md, the body enum, handoff from the branch (AC-5, AC-6)
  - [x] Cleanup: delete the regexes, `prompts` and `ReplyWithoutOffer`; Decisions in force edited in place (AC-7)
  - [ ] Live run in all three styles after muhammad's yes (AC-11)
- [ ] Verify it: `/check verify structured reply fields`
- [ ] Test it: `/test structured reply fields`
      Spec [0003](../specs/0003-structured-reply-fields/index.md). code in backend/mani/llm/schema.py, backend/mani/chat/context.py, backend/mani/chat/repairs.py, backend/mani/chat/reply_checks.py, backend/mani/chat/orchestrator.py, backend/mani/prompts/cache.py, backend/mani/prompts/composer.py, backend/scripts/scenario_check.py, backend/scripts/scenarios.json, backend/content/prompts/somatic.md, backend/content/prompts/mani_base.md, backend/content/prompts/response_format.md

## Legend

**The decision box.** Every feature carries one sub task ending in `(spec)`. Skills find it by that suffix.

- **Next step** is the first unticked box.
- **needs a decision** means run `/architect` first. The tag drops once the spec is captured.
- **Status** goes `planned`, `in-progress`, `done`, plus `existing` (built before this workflow) and `dropped`.
- **Workflow tier tag** beside a heading (`· GA`) raises that one feature above the project default.
