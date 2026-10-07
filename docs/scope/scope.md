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
| 2 | Thinking level required on every call | Foundation | planned |
| 3 | Short base prompt of general rules | Slice 1 | planned |
| 4 | Framework in 8 lines, ABCDE first | Slice 1 | planned |
| 5 | One model call, no redraft or repairs | Slice 1 | planned |
| 6 | The other five frameworks in 8 lines | Slice 2 | planned |
| 7 | Body check in in the lean format | Slice 2 | planned |
| 8 | Model facing text out of Python | Slice 3 | planned |
| 9 | Reply text and numbers out of Python | Slice 3 | planned |
| 10 | Crisis decided by the model | Slice 4 | planned |
| 11 | Thinking level and prompt tuning from measurements | Slice 5 | planned |

## Already built

### A. Chat turn pipeline · existing
One turn: safety screen, router shortlist, system prompt (base, framework index, response format), `[ctx]` block, model call, redraft, repairs. code in backend/mani/chat/, backend/mani/prompts/, backend/mani/llm/

### B. Six frameworks and the body check in · existing
ABCDE, Thought Reframe, Structured Problem Solving, ACT Choice Point, Behavioral Activation and DBT STOP, each 300 to 390 lines, plus the body check in merged into every framework at seed time. code in backend/content/, backend/scripts/seed.py

## Foundations

### 1. Turn cost and latency baseline · in-progress
A repeatable way to see what one turn costs before and after each change: input, cached, output and reasoning tokens, latency, and model calls per turn, for a fixed set of conversations. Without it, "faster" and "cheaper" are guesses, and one eval run is noise (three before, three after).
**Done when:** one command runs the chosen scenarios and prints those numbers per turn, reasoning tokens are recorded, the numbers survive the eval's own cleanup, and today's numbers are written down as the baseline.
- [x] Design it (spec): `/architect turn cost and latency baseline`
- [ ] Build it: `/develop turn cost and latency baseline`
  - [ ] Honest cost rows: reasoning tokens column (migration 018), both usage readers, latency per attempt (AC-3, AC-13)
  - [ ] One measured run writes a baseline file, with the local, column and abort guards and cleanup that always runs (AC-1, AC-2, AC-4, AC-5, AC-8, AC-9, AC-10, AC-12)
  - [ ] Repeated runs with scenario totals and medians, and the offline compare (AC-1, AC-5, AC-6, AC-7, AC-14)
  - [ ] Docs, the PORT-STATUS decision line, and the first `before-lean-prompts` baseline after muhammad's yes (AC-11)
- [ ] Verify it: `/check verify turn cost and latency baseline`
- [ ] Test it: `/test turn cost and latency baseline`
Spec [0002](../specs/0002-turn-cost-latency-baseline.md)

### 2. Thinking level required on every call · needs a decision
Every model call names its own thinking level: chat, summary, memory fold, title and the exercise pick. A missing level is an error at seed time, never a silent fallback.
**Done when:** seeding fails for a prompt row with no level or an unknown one, no model call goes out without an explicit level, and the config fallback is gone.
- [ ] Design it (spec): `/architect thinking level required`

## Slice 1: ABCDE through the lean path

### 3. Short base prompt of general rules · needs a decision
Rewrite `mani_base` as a short set of general rules: who Mani is, how it replies, the three styles, how a conversation moves. No scripted lines, no example conversations, no banned word lists, and each rule stated once across the base prompt, the response format and the schema descriptions.
**Done when:** the base prompt and the response format together fit a line budget set in the spec, contain no line the model must say word for word, repeat no rule, and the ABCDE replay conversation still reads well in all three styles.
- [ ] Design it (spec): `/architect short base prompt`

### 4. Framework in 8 lines, ABCDE first · needs a decision
Define the 8 line framework format (when it starts, the words that trigger it, when to skip it, the stages in one line, when it ends, what never happens) using Hussnain's rule, and convert ABCDE to it. The model writes each stage question itself in the chosen style. The unused body, lists and per stage blocks go.
**Done when:** abcde.md is about 8 lines of model facing content, the seed and the turn send only that, and a real ABCDE conversation runs from offer to end in each style.
- [ ] Design it (spec): `/architect framework in 8 lines`

### 5. One model call, no redraft or repairs · needs a decision
Remove the redraft loop and the reply repairs: feeling word checks, repeated question checks, offer timing, closest fit pushes, button trimming and rewritten permission questions. The model's reply goes out as it wrote it, apart from schema validation. Crisis handling stays until feature 10.
**Done when:** every turn makes exactly one chat call, redraft.py and the repairs are gone or reduced to schema shape, the tests that asserted those checks are removed or rewritten, and the ABCDE replay still completes.
- [ ] Design it (spec): `/architect one model call no repairs`

## Slice 2: Every framework lean

### 6. The other five frameworks in 8 lines
Convert Thought Reframe, Structured Problem Solving, ACT Choice Point, Behavioral Activation and DBT STOP to the format from feature 4, including how each is told apart from its neighbours.
**Done when:** each is about 8 lines, a real conversation reaches each one's offer and end, and the router picks the right one for the client's example lines.
- [ ] Build it: `/develop other five frameworks in 8 lines`

### 7. Body check in in the lean format · needs a decision
The ending (completion question, body check in, exercise, Chat More or Go to Library) as short rules the model follows, not verbatim text enforced in code, and no code that matches words inside the content.
**Done when:** every framework ends with the body check in, the four places get a fitting exercise, no code reads `when` text, and the client's flow holds in all three styles.
- [ ] Design it (spec): `/architect body check in lean format`

## Slice 3: Nothing hardcoded

### 8. Model facing text out of Python · needs a decision
The instruction text Python adds to the prompt (index headings, `stage_note`, memory and summary wrappers, schema field descriptions, the exercise picker prompt, phrase lists naming framework ids) moves into seeded content, so changing it never needs a code change.
**Done when:** no sentence the model reads is written in backend/mani/, and changing any of them needs only a reseed.
- [ ] Design it (spec): `/architect model facing text out of python`

### 9. Reply text and numbers out of Python · needs a decision
Text sent straight to the person (greeting, style question, openers, after framework questions, button labels, crisis reply) and the timing numbers (cooldowns, offer windows, router weights, summary threshold) move into seeded content or config.
**Done when:** no user facing sentence or behaviour number is a Python constant, and each can change with a reseed or config change.
- [ ] Design it (spec): `/architect reply text and numbers out of python`

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

## Open questions
- Hussnain's 7 to 8 line rule: get the exact format before `/architect framework in 8 lines`.
- The client's wording for each style, stage and body exercise goes away under the 8 line format. muhammad has allowed rewording to fix comprehension. Confirm the client is fine with the model writing these itself.

## Legend

**The decision box.** Every feature carries one sub task ending in `(spec)`. Skills find it by that suffix.
- **Next step** is the first unticked box.
- **needs a decision** means run `/architect` first. The tag drops once the spec is captured.
- **Status** goes `planned`, `in-progress`, `done`, plus `existing` (built before this workflow) and `dropped`.
- **Workflow tier tag** beside a heading (`· GA`) raises that one feature above the project default.
