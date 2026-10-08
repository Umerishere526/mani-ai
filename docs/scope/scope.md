# Scope: Mani lean prompts

Mani is a mental health companion. This scope covers how Mani talks to the model: a short base prompt of general rules, each framework in about 8 lines saying when it starts, when to skip it and when it ends, nothing hardcoded in prompts or in Python, no checks that redraft or rewrite the reply, and a thinking level set on every call. The goal is fewer tokens and lower latency now, and prompts that get better as models get faster.

**Build approach:** Tracer Bullet (take ABCDE through the whole lean path first, measure it, then repeat for the other frameworks).
**Workflow:** Beta (check verify, then test). The replies are health content, so a real conversation through the backend is the proof, not unit tests alone. Every real model run needs muhammad's yes first, because it spends the client's credit.

_These are recommendations to keep your build orderly, not requirements. Skip anything that does not fit._

## At a glance

| # | Feature | Phase | Status |
|---|---------|-------|--------|
| A | Chat turn pipeline | Existing | existing |
| B | Six frameworks and the body check in | Existing | existing |
| 1 | Turn cost and latency baseline | Foundation | in-progress |
| 2 | Thinking level required on every call | Foundation | in-progress |
| 3 | Short base prompt of general rules | Slice 1 | in-progress |
| 4 | Framework in 8 lines, all six | Slice 1 | in-progress |
| 5 | One model call, no redraft or repairs | Slice 1 | in-progress |
| 6 | The other five frameworks in 8 lines | Slice 2 | dropped |
| 7 | Body check in in the lean format | Slice 2 | in-progress |
| 8 | Model facing text out of Python | Slice 3 | in-progress |
| 9 | Reply text and numbers out of Python | Slice 3 | in-progress |
| 10 | Crisis decided by the model | Slice 4 | planned |
| 11 | Thinking level and prompt tuning from measurements | Slice 5 | planned |

## Already built

### A. Chat turn pipeline · existing
One turn: safety screen, router shortlist, system prompt (base, framework index, response format), `[ctx]` block, one model call, integrity guards. code in backend/mani/chat/, backend/mani/prompts/, backend/mani/llm/

### B. Six frameworks and the body check in · existing
ABCDE, Thought Reframe, Structured Problem Solving, ACT Choice Point, Behavioral Activation and DBT STOP, each 300 to 390 lines, plus the body check in merged into every framework at seed time. code in backend/content/, backend/scripts/seed.py

## Foundations

### 1. Turn cost and latency baseline · in-progress
A repeatable way to see what one turn costs before and after each change: input, cached, output and reasoning tokens, latency, and model calls per turn, for a fixed set of conversations. Without it, "faster" and "cheaper" are guesses, and one eval run is noise (three before, three after).
**Done when:** one command runs the chosen scenarios and prints those numbers per turn, reasoning tokens are recorded, the numbers survive the eval's own cleanup, and today's numbers are written down as the baseline.
- [x] Design it (spec): `/architect turn cost and latency baseline`
- [x] Build it: `/develop turn cost and latency baseline`
  - [x] Honest cost rows: reasoning tokens column (migration 018), both usage readers, latency per attempt (AC-3, AC-13)
  - [x] One measured run writes a baseline file, with the local, column and abort guards and cleanup that always runs (AC-1, AC-2, AC-4, AC-5, AC-8, AC-9, AC-10, AC-12)
  - [x] Repeated runs with scenario totals and medians, and the offline compare (AC-1, AC-5, AC-6, AC-7, AC-14)
  - [x] Docs, the PORT-STATUS decision line, and the first `before-lean-prompts` baseline after muhammad's yes (AC-11)
- [ ] Verify it: `/check verify turn cost and latency baseline`
- [ ] Test it: `/test turn cost and latency baseline`
Spec [0002](../specs/0002-turn-cost-latency-baseline/index.md) · code in backend/scripts/eval_replies.py, backend/scripts/baseline.py, backend/mani/llm/, backend/mani/db/llm_calls.py, backend/supabase/migrations/018_llm_call_reasoning_tokens.sql

### 2. Thinking level required on every call · in-progress
Every model call names its own thinking level in its own prompt row: chat turn, summary, memory fold, exercise pick and voice translation (the title rides on the chat turn). A missing level is refused at seed, at an admin edit and at call time, never a silent fallback. Spec: [0004](../specs/0004-thinking-level-required/index.md) code in backend/mani/prompts/calls.py, backend/content/prompts/
**Done when:** seeding fails for a prompt row with no level or an unknown one, no model call goes out without an explicit level, and the config fallback is gone.
- [x] Design it (spec): `/architect thinking level required`
- [x] Build it: `/develop thinking level required`
  - [x] The shared check and the voice translation row end to end (AC-1, AC-3, AC-5, AC-6, AC-7, AC-8)
  - [x] Exercise pick row, then chat turn, summary and memory fold on `effort_for` (AC-1, AC-5, AC-6, AC-7)
  - [x] Config fallback removed and admin writes refused (AC-2, AC-4)
  - [x] Tests, a reseeded local run, and PORT-STATUS.md (AC-1 to AC-8)
- [ ] Verify it: `/check verify thinking level required`
- [ ] Test it: `/test thinking level required`

## Slice 1: ABCDE through the lean path

### 3. Short base prompt of general rules · in-progress
Rewrite `mani_base` as a short set of general rules: who Mani is, how it replies, the three styles, how a conversation moves. No scripted lines, no example conversations, no banned word lists, and each rule stated once across the base prompt, the response format and the schema descriptions.
**Done when:** the base prompt and the response format together fit a line budget set in the spec, contain no line the model must say word for word, repeat no rule, and the ABCDE replay conversation still reads well in all three styles.
**Spec:** [0003](../specs/0003-short-base-prompt.md)
**Code:** backend/content/prompts/, backend/mani/llm/schema.py, backend/tests/unit/test_prompt_budget.py
- [x] Design it (spec): `/architect short base prompt`
- [ ] Build it: `/develop short base prompt`
  - [x] Guard test reduced to the one check the code needs: the clarification lines (word budget, shape and bans dropped by muhammad, 2026-10-07)
  - [x] Both prompt files rewritten to the rule home map, `ctx` key list and fixed lines table (AC-3, AC-5, AC-6, AC-7, AC-8)
  - [x] Schema descriptions without repeats, prompt text tests deleted, whole `pytest` clean, reseeded, PORT-STATUS updated (AC-5, AC-9)
  - [x] Word band dropped by muhammad, 2026-10-07; the base prompt was rewritten shorter instead (2,403 words)
  - [ ] ABCDE journey once per style, after muhammad's yes (AC-10)
- [ ] Verify it: `/check verify short base prompt`
- [ ] Test it: `/test short base prompt`

### 4. Framework in 8 lines, all six · in-progress
Define the 8 line framework format (starts when, sounds like, skip when, stages, ends when, offer, never, never) and convert all six frameworks to it in one change (feature 6 is merged in). The model writes each stage question itself in the chosen style. The unused body, lists and per stage blocks go, and so does the earliest offer gate.
**Done when:** each framework file is exactly 8 lines of model facing content, the seed refuses anything else, the index and the turn send only that, and the real runs in spec 0005 AC-10 pass.
Spec: [0005](../specs/0005-framework-in-8-lines.md)
Code: backend/content/frameworks/, backend/scripts/seed.py, backend/mani/prompts/composer.py, backend/mani/chat/context.py
- [x] Design it (spec): `/architect framework in 8 lines`
- [ ] Build it: `/develop framework in 8 lines`
  - [x] Before baseline, `--style`, and the seed format check (AC-1, AC-2, AC-10)
  - [x] ABCDE lean through index, `[ctx]`, gate removal, prompt edits and evals (AC-3 to AC-9, AC-12, AC-13, AC-14)
  - [ ] The other five drafted, muhammad's review stop, reseed, full `pytest` (AC-1, AC-11, AC-14)
  - [ ] Three new journeys, real runs after muhammad's yes, PORT-STATUS and specs README (AC-10)
- [ ] Verify it: `/check verify framework in 8 lines`
- [ ] Test it: `/test framework in 8 lines`

### 5. One model call, no redraft or repairs · in-progress
Remove the redraft loop and the reply repairs: feeling word checks, repeated question checks, offer timing, closest fit pushes, button trimming and rewritten permission questions. The model's reply goes out as it wrote it, apart from schema validation. Crisis handling stays until feature 10.
**Done when:** every turn makes exactly one chat call, redraft.py and the repairs are gone or reduced to schema shape, and the tests that asserted those checks are removed or rewritten.
- [x] Design it (spec): `/architect one model call no repairs`
- [ ] Build it: `/develop one model call no repairs`
  - [x] One call end to end: no redraft, no schema retry on chat, the grief veto as `ruled_out` in [ctx] (AC-1, AC-2, AC-7)
  - [x] Offer in the model's words: description in the index, offer rules rewritten, offer composition removed (AC-3, AC-8, AC-9)
  - [x] Integrity guards only: guards.py and ending.py, state guards for decline and retiring turns, word lists to the evals (AC-3, AC-4, AC-5, AC-6, AC-10)
  - [ ] Tests, docs and stale references, full suite with the database up (AC-11, AC-12) (one failure left, waiting on the spec 0005 reseed)
- [ ] Verify it: `/check verify one model call no repairs`
- [ ] Test it: `/test one model call no repairs`
Spec [0006](../specs/0006-one-model-call-no-repairs/index.md) · code in backend/mani/chat/, backend/mani/llm/client.py, backend/mani/prompts/composer.py, backend/content/prompts/

## Slice 2: Every framework lean

### 6. The other five frameworks in 8 lines · dropped
Merged into feature 4 (spec 0005): all six convert in one change. Originally: convert Thought Reframe, Structured Problem Solving, ACT Choice Point, Behavioral Activation and DBT STOP to the format from feature 4, including how each is told apart from its neighbours.
**Done when:** each is about 8 lines, a real conversation reaches each one's offer and end, and the router picks the right one for the client's example lines.
- [ ] Build it: `/develop other five frameworks in 8 lines`

### 7. Body check in in the lean format · in-progress
The ending (completion question, body check in, exercise, Chat More or Go to Library) as short rules the model follows, not verbatim text enforced in code, and no code that matches words inside the content.
**Done when:** every framework ends by asking how they feel and offering the body check, guided one step per turn; the model's `ending` field alone retires the framework (Chat More / Go to Library and the card on `choice`, nothing on `keep_talking`), with a 12 turn cap as backstop; and no code edits the reply or reads words to drive the ending.
Spec [0009](../specs/0009-body-check-in-lean-format/index.md) · code in backend/content/prompts/mani_base.md, backend/content/prompts/response_format.md, backend/mani/chat/orchestrator.py, backend/mani/chat/guards.py, backend/mani/chat/context.py, backend/mani/chat/techniques.py, backend/mani/llm/schema.py, backend/mani/models/rows.py, backend/mani/db/threads.py, backend/scripts/seed.py, backend/supabase/migrations/020_technique_ending_from.sql, backend/tests/integration/test_turn.py, backend/tests/evals/validators.py
- [x] Design it (spec): `/architect body check in lean format`
- [ ] Build it: `/develop body check in lean format` (before spec 0008)
  - [x] Tracer, `choice` end to end: seed and `[ctx]` without stage blocks, the `ending` field and guard, the old body route and `ending.py` deleted (AC-2 to AC-6, AC-8, AC-11)
  - [x] `keep_talking`, the safety concern pause and the crisis retire (AC-5, AC-7, AC-12)
  - [x] Migration 020, `ending_from` and the 12 turn cap (AC-9, AC-10)
  - [x] Evals, `REMOVED` and docs: `missing_handoff`, `panic_somatic_once`, PORT-STATUS, the specs README and the schema reference (AC-13)
  - [ ] muhammad reviews the `ending` wording in `mani_base.md`, then reseed and the full `pytest` with the database up (AC-1, AC-13)
- [ ] Verify it: `/check verify body check in lean format`
- [ ] Test it: `/test body check in lean format`

## Slice 3: Nothing hardcoded

### 8. Model facing text out of Python · in-progress
The instruction text Python adds to the prompt (index headings, `stage_note`, memory and summary wrappers, schema field descriptions, the exercise picker prompt, phrase lists naming framework ids) moves into seeded content, so changing it never needs a code change. Also removes the closest fit offer: Mani offers only a set on the router's shortlist that it judges fits.
**Done when:** no sentence the model reads is written in backend/mani/, and changing any of them needs only a reseed.
Spec: [0007](../specs/0007-model-text-out-of-python/index.md) · code in backend/mani/chat/context.py, backend/mani/prompts/, backend/mani/llm/schema.py, backend/mani/chat/router.py, backend/content/, backend/supabase/migrations/019_reply_shape_not_pinned.sql
- [x] Design it (spec): `/architect model facing text out of python`
- [x] Build it: `/develop model facing text out of python` (needs spec 0004 AC-6 built first)
  - [x] `[ctx]` and the layers as keys and headings, the stage rules and layer meanings in `response_format.md`, both contract tests (AC-1, AC-2, AC-5, AC-12)
  - [x] Summary, memory fold, exercise pick and tapped button messages, and the schemas with no descriptions (AC-3, AC-4)
  - [x] Reply shapes from `mani_base.md`, migration 019 dropping the shape check (AC-6)
  - [x] Distinction rules in the framework files, no closest fit, the shortlist as the offer gate, the offer log, in its own PR (AC-7, AC-8, AC-9, AC-10, AC-11)
  - [x] Tokenizer count, reseed, full `pytest` with the database up, PORT-STATUS and schema reference (AC-13)
- [ ] Verify it: `/check verify model facing text out of python`
- [ ] Test it: `/test model facing text out of python`

### 9. Reply text and numbers out of Python · in-progress
Text sent straight to the person (greeting, style question and buttons, openers, clarification lines, after framework questions) moves into a seeded `replies` row, and the conversation numbers (offer timing, cooldowns, router weights, history, style and memory windows) into a seeded `tuning` row, both checked on every write. A second commit deletes the phrase lists behind `their_last` and lets the model track the clarification and after framework lines. The body ending's labels stay for feature 7, and the crisis reply for feature 10.
**Done when:** no line Mani sends without the model and no conversation number is a Python constant, each can change with a reseed, and a broken edit is refused when written.
Spec: [0008](../specs/0008-reply-text-numbers-out-python/index.md) · code in backend/content/prompts/, backend/mani/prompts/, backend/mani/chat/, backend/mani/memory.py, backend/mani/db/config_tables.py
- [x] Design it (spec): `/architect reply text and numbers out of python`
- [x] Build it: `/develop reply text and numbers out of python`
  - [x] Commit 1: `replies` row, the shared check, required rows refused at seed and admin writes, greeting, buttons and openers from content (AC-1, AC-3, AC-4, AC-5, AC-7, AC-8)
  - [x] Commit 1: `tuning` row and every number moved, including the cron backstop and the idle fold, with PORT-STATUS (AC-2, AC-3, AC-6, AC-7, AC-8, AC-15)
  - [x] Commit 2: phrase lists and `their_last` gone, `clarification_lines` and `after_framework_questions` tracked by the model, `EXPLAIN_LABELS` gone, `max_entries` in the fold message (AC-9 to AC-13)
  - [x] Commit 2: `REMOVED` and `REMOVED_NAMES`, full `pytest` with the database up, PORT-STATUS lines edited (AC-14, AC-15)
- [ ] Verify it: `/check verify reply text and numbers out of python`
- [ ] Test it: `/test reply text and numbers out of python`

## Slice 4: Crisis

### 10. Crisis decided by the model · needs a decision · GA
Remove the keyword crisis and concern screen. The model's own `crisis` field becomes the only detector. The thread lock and the crisis reply still follow when it fires. This is the riskiest change in the scope, so it comes last and carries the highest rigour.
**Done when:** safety.py's phrase lists are gone, every crisis eval scenario (direct, indirect, misspelt, mixed with other topics) locks the thread and sends the crisis reply, and no ordinary conversation triggers it.
- [ ] Design it (spec): `/architect crisis decided by the model`

## Slice 5: Keep improving

### 11. Thinking level and prompt tuning from measurements · needs a decision
Use the baseline from feature 1 to choose the thinking level per call and to compare each prompt change, three runs before and three after, so the prompts keep improving as models get faster.
**Done when:** each call's level is backed by numbers recorded in PORT-STATUS.md, and the tuning loop is a documented command anyone can run again.
- [ ] Design it (spec): `/architect thinking level and prompt tuning`

## Deferred
- Drop the unused `threads.vague_streak` column in its own migration (from spec 0008).
- Delete mobile's `stylePrompt` once mobile renders the greeting from the API (from spec 0008).
- Map API error categories to dictionary text in both frontends, instead of `ServiceError.user_message` (from spec 0008).
- Move `CHAT_MORE_LABEL` and `GO_TO_LIBRARY_LABEL` into the `replies` row once spec 0008 builds it (from spec 0009).
- Drop the unused `admin.frameworks.stages` column in its own migration (from spec 0009).
- Tell the client the ending now offers the body check and lets Mani choose the steps (from spec 0009).

## Open questions
- Should call rows also require `model_id`, so `DEFAULT_CHAT_MODEL` and `DEFAULT_SUMMARY_MODEL` go away? Left out of spec 0004 by choice (from spec 0004).
- Hussnain's 7 to 8 line rule: get the exact format before `/architect framework in 8 lines`.
- The client's wording for each style, stage and body exercise goes away under the 8 line format. muhammad has allowed rewording to fix comprehension. Confirm the client is fine with the model writing these itself.

## Legend

**The decision box.** Every feature carries one sub task ending in `(spec)`. Skills find it by that suffix.
- **Next step** is the first unticked box.
- **needs a decision** means run `/architect` first. The tag drops once the spec is captured.
- **Status** goes `planned`, `in-progress`, `done`, plus `existing` (built before this workflow) and `dropped`.
- **Workflow tier tag** beside a heading (`· GA`) raises that one feature above the project default.
