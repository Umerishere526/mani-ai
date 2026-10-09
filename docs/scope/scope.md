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
| 12 | Stages skip what the chat already told | Slice 4 | in-progress |
| 13 | Frameworks offered when the chat fits | Slice 4 | in-progress |
| 14 | Mani speaks and asks as the client wrote | Slice 5 | in-progress |
| 15 | The offer in the client's words | Slice 5 | in-progress |
| 16 | Audit unused code and files | Slice 5 | in-progress |
| 17 | Offer and Tell me more per framework and style | Slice 5 | in-progress |
| 20 | ABCDE from the client's ABCDE doc | Slice 5 | in-progress |
| 22 | Mani understands the issue, then offers naturally | Slice 5 | in-progress |
| 21 | The ending follows the issue | Slice 5 | planned |
| 10 | Crisis decided by the model | Slice 6 | planned |
| 18 | Crisis events can be resolved | Slice 6 | planned |
| 11 | Thinking level and prompt tuning from measurements | Slice 7 | planned |
| 19 | Memory folding runs on a schedule | Slice 7 | planned |

## Already built

### A. Chat turn pipeline · existing
One turn: safety screen, grief veto, system prompt (base, framework index, response format), `[ctx]` block, one model call, integrity guards. code in backend/mani/chat/, backend/mani/prompts/, backend/mani/llm/

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
**Done when:** each is about 8 lines, a real conversation reaches each one's offer and end, and the model picks the right one for the client's example lines.
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
Spec: [0007](../specs/0007-model-text-out-of-python/index.md) · code in backend/mani/chat/context.py, backend/mani/prompts/, backend/mani/llm/schema.py, backend/mani/chat/vetoes.py, backend/content/, backend/supabase/migrations/019_reply_shape_not_pinned.sql
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
Text sent straight to the person (greeting, style question and buttons, openers, clarification lines, after framework questions) moves into a seeded `replies` row, and the conversation numbers (offer timing, cooldowns, windows, history, style and memory windows) into a seeded `tuning` row, both checked on every write. A second commit deletes the phrase lists behind `their_last` and lets the model track the clarification and after framework lines. The body ending's labels stay for feature 7, and the crisis reply for feature 10.
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

## Slice 4: Frameworks follow the chat

### 12. Stages skip what the chat already told · in-progress
A framework's stages are what Mani needs to learn, not steps to walk in order. In the same one call, the model reports each stage of the running framework as known, partial or missing (status only, none of their words); the code stores that ledger and sets the stage to the first one not known. An intake stage (the event, the belief, the problem) skips when the chat already answered it; a work stage (examine, balanced, choose, first action) counts as known only in the person's own words in this conversation. The ending opens once all are known. Today the one stage clamp in `techniques.py` and the "never skip a stage" rule send Mani back to stages already answered, though each Starts when line requires those answers before the offer.
**Done when:** on acceptance the reply skips every stage the chat already answered (the ABCDE example starts at the right stage), a partial stage gets only its missing part, no stage already answered is asked again, no framework holds the thread past the cap from any stage, and the evals show no question for a stage already known.
Spec: [0010](../specs/0010-stages-skip-what-chat-told/index.md) · code in backend/mani/chat/, backend/mani/llm/schema.py, backend/mani/models/rows.py, backend/mani/db/threads.py, backend/content/, backend/scripts/, backend/supabase/migrations/
- [x] Design it (spec): `/architect stages skip what the chat already told` (decided 2026-10-08: the stage ledger approach and the work stage rule)
- [ ] Build it: `/develop stages skip what the chat already told`
  - [x] Tracer: migration 021, the ledger in the guard, the running turn branch on every accepting path, `[ctx]` `stage_ledger`, the ` | ` in all six Stages lines, prompt drafts reviewed by muhammad, reseed (AC-1, AC-2, AC-3, AC-5, AC-9, AC-10, AC-11). Built 2026-10-08, full `pytest` green (755 passed); wording accepted by muhammad, reseed skipped by muhammad's call, so the database held the old prompts and Stages lines until the reseed for spec 0011 on 2026-10-08
  - [ ] Counting and backstops: `stage_turn_cap` 4 in `tuning`, `passed`, `stage_last_try`, hold and count, concern turns, frozen from `closing`, ending cap from `closing` (AC-4, AC-6, AC-7, AC-8, AC-12, AC-14)
  - [ ] Evals: `expect_stage` and scenarios, real runs only with muhammad's yes (AC-13, AC-14)
  - [ ] Close out: PORT-STATUS, schema reference, journal, full `pytest` (AC-15)
- [ ] Verify it: `/check verify stages skip what the chat already told`
- [ ] Test it: `/test stages skip what the chat already told`

### 13. Frameworks offered when the chat fits · in-progress
Mani offers a set from what the person means, not from an exact phrase. Today "I've been avoiding my friends because I've been overwhelmed, and I feel guilty about ignoring them" gets an empty shortlist, so Mani can offer nothing. The model judges fit from the Framework Index it already reads; the phrase router, its distinction rules, the shortlist line and the urgent DBT STOP case go, and only the grief veto and the cooldown stay in code.
**Done when:** a plain sentence with no phrase from any list, such as the avoiding friends line, can be offered a fitting set at the person's second message; the grief veto still keeps Behavioral Activation from someone who has lost a person; and the router's phrase lists, scoring and distinction rules no longer exist. Whether the model picks well on plain phrasing is measured under feature 11, not here.
Spec: [0011](../specs/0011-offers-follow-the-chat/index.md) · code in backend/mani/chat/, backend/scripts/seed.py, backend/mani/prompts/tuning.py, backend/content/
- [x] Design it (spec): `/architect frameworks offered when the chat fits` (decided 2026-10-08: the model judges, the router is cut to the veto, urgency dropped, scripted tests only)
- [x] Build it: `/develop frameworks offered when the chat fits` (built on spec 0010's staged tracer, by muhammad's call)
  - [x] Tracer: no shortlist and no urgent case, `framework_shortlist` out of `[ctx]`, the offer log, prompt drafts reviewed by muhammad, scripted tests (AC-1, AC-5, AC-7, AC-8). Built 2026-10-08; wording accepted by muhammad as the spec drafted it
  - [x] Remove the scoring: `router.py` to `vetoes.py`, the veto checked once per load in `Registry`, framework files, seed and `tuning` row, the tests that reach them (AC-2, AC-3, AC-4, AC-6). Built 2026-10-08, reseeded locally, full `pytest` green (666 passed, 4 skipped)
  - [x] Close out: PORT-STATUS, schema reference, docs, journal, reseed after muhammad's yes on the wording, full `pytest` (AC-9). Journal: offers-follow-the-chat-build-2026-10-08
- [ ] Verify it: `/check verify frameworks offered when the chat fits`
- [ ] Test it: `/test frameworks offered when the chat fits`

## Slice 5: Client cadence

### 14. Mani speaks and asks as the client wrote · in-progress
Each reply does what the client's Directive, Supportive or Reflective behavior list says (docs/client-share-docs/directive, reflective, supportive .docx), asks the way the client's examples ask, and offers once Mani can identify the issue: about 2 to 4 exchanges, a range, not a count. Reached by replacing and cutting prompt rules, never by adding them, because rule bloat makes the model drift. Today the `Starts when` gates, the "reaches, unseen" question rule and the "If two fit" rule kept the manager and CEO conversation asking for 8 turns, and "Start with what they feel" made Direct restate instead of lead.
**Done when:** `mani_base.md` plus `response_format.md` are under 150 lines and 3616 words together, and three real conversations, one run each after muhammad's yes (`client_anxiety` Directive, `client_overthinking` Reflective, `client_stress` Supportive), each reach an offer with no "I hear you", "That makes sense" or "I'm here for you". Recorded as measured; a failing run is reported, not rerun. When the offer comes is feature 22's, since the client dropped the 2 to 4 window (2026-10-08). Broader offer measurement stays under feature 11.
Spec: [0012](../specs/0012-mani-speaks-as-client-wrote/index.md) · code in backend/content/, backend/mani/chat/context.py, backend/mani/prompts/replies.py, chat-tester/app.py
- [x] Design it (spec): `/architect mani speaks and asks as the client wrote` (decided 2026-10-08: cut and replace rules with the client's phrases, hybrid style lines, `question_focus` and `clarification_lines` cut, Directive label only, offer wording left to feature 15, real runs capped at 3)
- [x] Build it: `/develop mani speaks and asks as the client wrote`
  - [x] Tracer: `question_focus` and `clarification_lines` out of code, `[ctx]` and the `replies` row, the Directive label, the prompt and Starts when drafts, `pytest tests/unit` green (AC-1 to AC-8)
  - [x] Review and reseed: muhammad reviews the wording, reseed, full `pytest` with integration not skipped, `wc -lw` (AC-9, AC-12)
  - [x] Close out: `conversational-styles.md` from the October 8 doc, the eval yaml comment, PORT-STATUS, journal (AC-10, AC-12)
  - [x] Real runs: three conversations with muhammad's yes and `get-credits` first (AC-11)
- [ ] Verify it: `/check verify mani speaks and asks as the client wrote`
- [ ] Test it: `/test mani speaks and asks as the client wrote`

### 15. The offer in the client's words · in-progress
The offer is a fixed frame in seeded content: "We'll go through a few focused questions.", `Framework: <name>`, that framework's description word for word from docs/client-share-docs/intro to six frameworks _ three follow up questions .docx, and "Would it help to work through it together?", with three buttons: Yes, let's try it · Tell me more · I want to keep talking. Tell me more gets a short explanation in the chosen style, then Yes, let's try it · I want to keep talking. Showing the name is muhammad's call over the client doc (2026-10-08). Design it with feature 14, since both rewrite the `offers:` rules.
**Done when:** every offer shows the frame, the name and that framework's client description exactly, with the three buttons; Tell me more answers and leaves the two buttons; and changing any of this text needs only a reseed.
Spec: [0013](../specs/0013-offer-in-client-words/index.md) · code in backend/content/, backend/mani/chat/offer.py, backend/mani/chat/orchestrator.py, backend/mani/prompts/replies.py, backend/scripts/, chat-tester/app.py
- [x] Design it (spec): `/architect the offer in the client's words` (decided 2026-10-08: the code writes the offer from seeded rows and the model only decides when and which; one lead for all six, kept by muhammad over the repeat it makes; the client's names and descriptions; Tell me more shows the name and description with no model call until feature 17; the chat tester hides its field while an offer is open; the `Offer:` lines cut to seven; no real runs)
- [x] Build it: `/develop the offer in the client's words`
  - [x] Tracer: the `offer` block and its checks, `offer.py`, the orchestrator step, one scripted offer test (AC-1, AC-4)
  - [x] Tell me more and the other paths: the tap with no model call, typed text past an offer by the one rule, relabelled tests and docstrings (AC-5, AC-6, AC-7, AC-10)
  - [x] Content and reseed: names, descriptions, seven lines, the prompt drafts reviewed by muhammad, reseed, full `pytest` (AC-2, AC-3, AC-8, AC-11)
  - [x] Chat tester and close out: the hidden composer, eval checks skip code written replies, PORT-STATUS, BACKEND.md, journal (AC-9, AC-12, AC-13)
- [ ] Verify it: `/check verify the offer in the client's words`
- [ ] Test it: `/test the offer in the client's words`

### 16. Audit unused code and files · in-progress
A list of what nothing reads or runs, each item with evidence: code, framework fields such as `appropriate_when` and `not_when`, columns, scripts, tests and docs. Guardrails and crisis handling are marked keep. muhammad marks each item keep or delete before anything is deleted.
**Done when:** the list sits in the spec's `rationale.md`, every item carries evidence and muhammad's mark, and the deletes are a build plan.
Spec: [0014](../specs/0014-audit-unused-code-files/index.md) · code in backend/mani/, backend/scripts/, backend/supabase/migrations/, backend/tests/, backend/content/prompts/, chat-tester/, .claude/, backend/docs/
- [x] Design it (spec): `/architect audit unused code and files` (decided 2026-10-08: backend, chat tester and docs, not web or mobile; about twenty Python names, two packages, four columns, six grants and a dead policy go; audit columns, guardrails and timestamps stay; the pool settings go and pool.py's 2 and 10 stay; one vulture cross check, no standing check; 0012 and 0013 committed before the build)
- [x] Build it: `/develop audit unused code and files`
  - [x] Tracer: the Python deletions, the pool settings, the docstring fixes, the tests and chat tester, no schema change (AC-1, AC-2, AC-3, AC-10)
  - [x] Packages and content: `langchain-core` for `langchain`, `email-validator` out, the prompt frontmatter, reseed (AC-4, AC-9)
  - [x] Migrations 022 to 025: the four column drops, the grant revokes, `test_grants.sql` and `test_rls.sql` (AC-5, AC-6, AC-7, AC-8)
  - [x] Docs, strays and close out: the stale statements, `ai-layer-audit.md`, the old `.eval` outputs, `.obsidian/workspace.json`, PORT-STATUS, journal (AC-11 to AC-15)
- [ ] Verify it: `/check verify audit unused code and files`
- [ ] Test it: `/test audit unused code and files`

### 17. Offer and Tell me more per framework and style · in-progress
from spec 0013. A tap on Tell me more explains how the questions will help, in the client's wording. Until then it shows the framework's name and description again (spec 0013). The client's wording has arrived for ABCDE (docs/client-share-docs/ABCDE Framework.docx, transcribed in backend/docs/specs/framework-abcde.md §0.4 and §0.6): a different offer line for each style ("There's a framework called ABCDE that helps you …"), and a Tell Me More that lists all five steps in that style. muhammad wants both built (2026-10-08). The open points are where text for each framework and style lives, how `offer.py` picks it, and what the other five show until their documents arrive.
**Done when:** an ABCDE offer and its Tell Me More show the client's text for the chosen style, generalised where it quoted one person, the two buttons stay after Tell Me More, Try It after Tell Me More neither restarts nor repeats the five steps, and changing the wording needs only a reseed.
Spec: [0015](../specs/0015-offer-per-framework-style/index.md) · code in backend/content/prompts/replies.md, backend/mani/prompts/replies.py, backend/mani/chat/offer.py, backend/mani/chat/orchestrator.py, backend/scripts/
- [x] Design it (spec): `/architect offer and tell me more per framework and style` (decided 2026-10-08: literal per style text in `replies.offer.by_framework`, ABCDE generalised where it quoted one user, the other five on the shared offer, all three styles or none, no prompt change, one Reflective real run after muhammad's yes)
- [x] Build it: `/develop offer and tell me more per framework and style`
  - [x] Tracer: `by_framework` and its checks, the ABCDE block, the style through the offer step, the per style offer tests (AC-1, AC-3, AC-4, AC-6)
  - [x] Tell Me More in the style, then Try It, and the no style default (AC-3, AC-4, AC-5)
  - [x] The seed id check, the `@more` token, the `abcde_told_more` scenario, reseed after muhammad's yes, full `pytest` (AC-2, AC-7, AC-8). Built 2026-10-08, reseeded, 684 passed, 4 skipped
  - [x] Close out: PORT-STATUS, journal, and the one real run after muhammad's yes (AC-7, AC-9). Real run passed, 0 findings. Journal: offer-per-style-build-2026-10-08
- [ ] Verify it: `/check verify offer and tell me more per framework and style`
- [ ] Test it: `/test offer and tell me more per framework and style`

### 20. ABCDE from the client's ABCDE doc · in-progress
The client's ABCDE Framework doc (October 2026) in the seven ABCDE lines: each letter named as Mani goes (A is for Activating Event, D is for Dispute, E is for Effective New Belief), including stages the chat already answered; ABCDE offered over Thought Reframe whenever both fit; the end reached once they tell what they know from what they assumed, with no new belief manufactured. Also the client's buttons, Try It · Tell Me More · Keep Chatting, for all six. The stage ids are the client's step names, `activating_event` to `effective_new_belief`, and the Stages line cap went to 420 to hold them (muhammad, 2026-10-08).
**Done when:** the ABCDE lines carry the letter names, Dispute, Effective New Belief, the priority and the end; Thought Reframe defers to ABCDE; the buttons read Try It · Tell Me More · Keep Chatting; the doc is transcribed in backend/docs/specs/framework-abcde.md; reseeded; full `pytest` green.
code in backend/content/frameworks/abcde.md, backend/content/frameworks/thought_reframe.md, backend/content/prompts/replies.md, backend/scripts/seed.py, backend/docs/specs/framework-abcde.md
- [x] Build it: `/develop abcde from the client doc` (built 2026-10-08, reseeded, full `pytest` 670 passed, 4 skipped)
- [ ] Verify it: `/check verify abcde from the client doc` (only a real run shows the letters named, with muhammad's yes)
- [ ] Test it: `/test abcde from the client doc`

### 22. Mani understands the issue, then offers naturally · in-progress
The client's feedback on all three styles (docs/client-share-docs/mani-response-feedback-2026-10-08.md): Mani restates what the person just said instead of answering it, asks a narrow question before it knows what the issue is, and moves into a framework with a recap. The client's principle: understand the problem, introduce the framework naturally, use what they already shared, and never make them explain it twice. No fixed number of exchanges before the offer. Reached by cutting and replacing prompt rules, never by adding them. The transcripts predate features 15 and 17, so the recap before the offer is gone, but the seeded offer now arrives with no bridge from the conversation.
**Done when:** in the client's job decision conversation, three real runs per style after muhammad's yes, each check holding in at least 2 of a style's 3 runs, no reply opens by restating what they just said, the first question asks what the decision is, both sides are explored before any offer, the offer reads as a natural next step that lets them choose, and the first stage question asks nothing they already told; and `mani_base.md` plus `response_format.md` end with no more lines than they started with.
Spec: [0016](../specs/0016-understand-issue-then-offer-naturally/index.md) · code in backend/content/prompts/mani_base.md, backend/content/prompts/response_format.md, backend/mani/chat/orchestrator.py, backend/scripts/eval_conversations.yaml
- [x] Design it (spec): `/architect mani understands the issue then offers naturally` (decided 2026-10-08: seven prompt lines replaced one for one, mirroring only to check understanding, ask what the issue is first, offer once the issue, what makes it hard and for a choice what pulls each way are known, the model's own line before every seeded offer, no say back on a yes, floor of 2 kept, no code check on the bridge, one `client_job_decision` run per style after muhammad's yes; round 2 after those runs failed: E6 made concrete, E8 to E11 swap `rules` line 18, `warmth lead`, and the Supportive and Reflective style lines so care is about what they face and never their feeling handed back, three runs per style passing on 2 of 3, shapes and reasoning printed, the say back after Try It measured only)
- [ ] Build it: `/develop mani understands the issue then offers naturally`
  - [x] The bridge: the model's line before the seeded offer on every kept offer, E6, and the offer tests (AC-4, AC-7)
  - [x] The prompt cuts E1 to E5 and E7, line and word counts, reseed, full `pytest` (AC-1, AC-2, AC-3, AC-5, AC-6, AC-7)
  - [x] The `client_job_decision` scenario and the three real runs after muhammad's yes (AC-8): run 2026-10-08, all three fail on restating, see PORT-STATUS measurements
  - [x] PORT-STATUS, spec 0012 AC-11 check and the journal note (AC-9)
  - [x] Round 2: E6 rewritten, E8 to E11, reseed, full `pytest`, nine graded runs plus three measured after muhammad's yes, PORT-STATUS and journal (AC-1, AC-4, AC-6, AC-8, AC-9): run 2026-10-08, AC-8 fails on restating (Direct and Supportive 0 of 3) and the bridge (0 of 9, each makes its own offer), see PORT-STATUS measurements
- [ ] Verify it: `/check verify mani understands the issue then offers naturally`
- [ ] Test it: `/test mani understands the issue then offers naturally`

### 21. The ending follows the issue · waiting on the client
from the client's ABCDE doc: completing a framework must not trigger a body check by itself. This replaces feature 7's "every framework ends by offering the body check" (spec 0009), for all six. muhammad's thinking (2026-10-08, may change): no three after framework questions, since the stages usually answer them already (feature 12). If the issue is not resolved when the framework finishes, keep chatting and offer another framework that fits. Once the issue is resolved, offer the body check; if they want it, do it, otherwise stop with Chat More and Go to Library. Held until the client answers; today's flow is audited in `mani-vault/Journal/ending-waits-on-client-2026-10-08.md`.
**Done when:** set once the client answers.
- [ ] Ask the client: should Mani offer a body check after a framework, and when; if the issue is not resolved, another framework, how soon, and may the same one return; the three after framework questions, yes or no; when Chat More and Go to Library appear; all six frameworks or ABCDE only
- [ ] Design it (spec): `/architect the ending follows the issue`

## Slice 6: Crisis

### 10. Crisis decided by the model · needs a decision · GA
Remove the keyword crisis and concern screen. The model's own `crisis` field becomes the only detector. The thread lock and the crisis reply still follow when it fires. This is the riskiest change in the scope, so it comes last and carries the highest rigour.
**Done when:** safety.py's phrase lists are gone, every crisis eval scenario (direct, indirect, misspelt, mixed with other topics) locks the thread and sends the crisis reply, and no ordinary conversation triggers it.
- [ ] Design it (spec): `/architect crisis decided by the model`

### 18. Crisis events can be resolved · needs a decision · GA
from spec 0014. `admin.crisis_events.resolution` and `resolved_at` are never written, so the admin list filtered to unresolved returns every crisis event ever recorded. Decide who resolves an event, how, and what the filter shows.
**Done when:** a crisis event can be marked resolved with a reason, the unresolved filter shows only open events, and the change is covered by the RLS and grant tests.
- [ ] Design it (spec): `/architect crisis events can be resolved`

## Slice 7: Keep improving

### 11. Thinking level and prompt tuning from measurements · needs a decision
Use the baseline from feature 1 to choose the thinking level per call and to compare each prompt change, three runs before and three after, so the prompts keep improving as models get faster.
**Done when:** each call's level is backed by numbers recorded in PORT-STATUS.md, and the tuning loop is a documented command anyone can run again.
- [ ] Design it (spec): `/architect thinking level and prompt tuning`

### 19. Memory folding runs on a schedule · needs a decision
from spec 0014. `scripts/fold_idle_threads.py` folds idle threads into a person's memory, but nothing schedules it, and `/internal/cron/fold-summaries` runs thread summaries, not memory folding. Once deployed, memory may never fold. Decide what runs it and how often.
**Done when:** memory folding runs on a schedule in a deployed environment, and the docs name what runs it.
- [ ] Design it (spec): `/architect memory folding runs on a schedule`

## Deferred
- Delete mobile's `stylePrompt` once mobile renders the greeting from the API (from spec 0008).
- Map API error categories to dictionary text in both frontends, instead of `ServiceError.user_message` (from spec 0008).
- Move `CHAT_MORE_LABEL` and `GO_TO_LIBRARY_LABEL` into the `replies` row once spec 0008 builds it (from spec 0009).
- Tell the client the ending now offers the body check and lets Mani choose the steps (from spec 0009).
- Tell the client the offer now shows the framework name, against the intro doc's "do not give them the name" (muhammad's call, 2026-10-08, feature 15).
- Hide the text field in web and mobile while an offer is open, the way the chat tester does, once they are wired to the API (from spec 0013).
- Tell the client every offer opens with the same lead, and Tell me more shows the name and description until they send its wording (from spec 0013).
- Tell the client the two check lines ("Do I have this right?", "What would you like us to focus on today?") are gone and Mani checks its understanding in its own words (from spec 0012).
- Show `ending_from` and `stage_ledger` in the chat tester's framework state panel (from spec 0014).
- Build spec 0010's `expect_stage`, `stage_turn_cap` and `stage_last_try`, and give it a `verify.md` (from spec 0014).
- Reconcile this scope's stale lines: the 8 line wording, feature 3's status, "the other five drafted" (from spec 0014, for `/scope`).

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
