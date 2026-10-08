# 0005. Each framework as eight model facing lines

**Date**: 2026-10-07
**Status**: In Progress

## Summary

Each of the six frameworks shrinks from about 300 to 390 lines to eight lines the model reads: when it starts, how it sounds, when to skip it, its stages in one line, when it ends, how to offer it, and two things it must never do. All six sets of eight lines sit in the cached part of the system prompt (the part of the prompt that is reused between turns and billed at a tenth of the price), and the per stage blocks in `[ctx]` (the small block of turn facts sent with every message) go away. The model writes every stage question itself, in the chosen style. Code keeps only what code needs: stage ids, the router's phrase lists, and the grief veto. All six convert in one change, with no second format kept alive.

## Context

> ⚠️ Premise note: this spec converts all six frameworks at once, which merges scope features 4 and 6. The scope's Tracer Bullet plan said ABCDE goes through the lean path alone first and is measured before the others follow. muhammad chose all six to avoid a temporary second code path for two formats, which his rules treat as backward compatibility. The cost is that a quality drop cannot be pinned on one framework from the real runs alone. The build plan keeps the Tracer Bullet spirit inside the change: ABCDE is converted and passes every check before the other five are written.

Mani runs six talking frameworks (ABCDE, Thought Reframe, Structured Problem Solving, ACT Choice Point, Behavioral Activation, DBT STOP). Each lives in `backend/content/frameworks/<id>.md` as YAML frontmatter (structured fields at the top of a markdown file) plus a markdown body, and `scripts/seed.py` loads it into `admin.frameworks`. A file carries the client's whole specification for that framework. That includes a central indication, what to find out, contraindications, distinctions from neighbours, an earliest offer message, router phrases, and, for every stage, a purpose, listening cues, a readiness test, boundaries, unclear answer branches with scripted replies, and three scripted asks, one per style. The body holds a worked example and a table of responses to avoid.

What the model actually reads today comes from two places. `mani/prompts/composer.py::framework_index` builds the cached Framework Index from five activation fields across all six frameworks. `mani/chat/context.py::_stage_lines` renders the current stage's six blocks and the next stage's six blocks into `[ctx]` on every framework turn, which is uncached and paid at full price. The markdown body is seeded into `admin.frameworks.body` and read by nothing. `earliest_offer_message` is not model text. It is a Python gate (`context.earliest_offer_ok`), applied in the redraft loop and in `cooldown_passed`.

The lean prompt scope (`docs/scope/scope.md`) sets the goal: fewer tokens and lower latency, and prompts that improve as models get faster rather than scripts the model must follow word for word. The journal's measurement lesson (`mani-vault/Journal/measure-before-tuning-prompts.md`) applies: one run is noise, and a prompt change is judged on several runs before and after. The before numbers for this change do not exist yet. `eval_replies.py --baseline` is built, but no `before-lean-prompts` file has been saved.

Three constraints bound the change. The client's documents win over our own conversation rules, and muhammad gave standing permission to reword the client's lines without sign off (2026-10-05). The crisis screen and the grief veto (`never_offer_when_said` on Behavioral Activation, read by `router.vetoes`) are out of reach for this scope and change only through their own rows. Every real model run spends the client's OpenRouter credit and needs muhammad's yes first.

## Requirements

**User stories**:
- As muhammad, I want each framework to be eight lines the model reads, so a turn costs fewer tokens and the model writes questions that fit the person rather than reciting scripts.
- As someone talking to Mani, I want a framework's questions to follow what I already said, in the style I chose, without being asked to repeat myself.
- As a maintainer, I want the seed to refuse a framework that grows past its budget, so the files cannot drift back to 300 lines.

**Acceptance criteria**:
- **AC-1**: Each of the six files in `backend/content/frameworks/` has a body of exactly eight non-empty lines, labelled in this order: `Starts when:`, `Sounds like:`, `Skip when:`, `Stages:`, `Ends when:`, `Offer:`, `Never:`, `Never:`. Its frontmatter holds only `id`, `name`, `summary`, `display_order`, `phases`, and `activation` with `strong_signals`, `signals`, `redirects` and, on Behavioral Activation only, `never_offer_when_said`. No `stages`, `central_indication`, `to_find_out`, `appropriate_when`, `not_when`, `contraindications`, `distinctions` or `earliest_offer_message` remain.
- **AC-2**: `python scripts/seed.py` exits non zero, names the file and the reason, and writes nothing (the seed runs in one transaction) when a framework body is not exactly eight lines (a blank line or a heading counts as a line and is refused), has a label missing or out of order, has a line over 220 characters, has a `Stages:` line over 320 characters, or has stage ids in its `Stages:` line that differ from its `phases` after `offering`, in order. Stages are split on ` > `, and a stage's id is its text before ` (`. The words inside the parentheses are free text and may contain commas.
- **AC-3**: The Framework Index in the cached system prompt carries, for each active framework in `display_order`, its name, its id, and its eight lines verbatim, and none of today's four generated sections (the "Use it when" table, "Telling them apart", "Never offer one when", "Finding the fit"). The rule that the description is added for the model and that the model never names the framework stays.
- **AC-4**: While a framework runs, `[ctx]` carries `active_framework`, `framework_stages`, `stage: <id>`, `next_stage: <id>` and one `stage_note`. It carries no `stage_purpose`, `stage_listen_for`, `stage_ready_when`, `stage_boundaries`, `stage_if_unclear` or `stage_ask` line for a framework's own stages. The two somatic stages still render their blocks unchanged, both as the current stage and as `next_stage` (on the `closing` turn the next stage is `somatic_checkin`, and its block is sent). While an offer is open and unanswered (phase `offering`), `[ctx]` shows `stage: offering` and no other stage line.
- **AC-5**: On the turn the person says yes, `stage:` names the first working stage (the id after `offering`) and `next_stage:` the one after it. The `stage_note` tells the model to judge whether what they already said answers that first stage, by its words in the `Stages:` line. If it does, the reply says it back in their words and asks the next stage's question. If it does not, the reply asks the first stage's question built from what they said. This is the model's judgment; the unit test checks that the note and both ids are present, and the `start_keeps_context` and `exam_start_keeps_context` scenarios show the behaviour in the real runs.
- **AC-13**: On a somatic stage, the `stage_note` keeps today's rule that the body check in and practice are fixed wording, given as the stage gives it. On a framework's own stage, the note says to ask that stage's question in the model's own words and the chosen style, built from what the person said, as the `Stages:` line describes it.
- **AC-6**: The earliest offer gate is gone: `context.earliest_offer_ok`, the orchestrator's `_earliest_ok` (used for the redraft at `orchestrator.py:481-490` and for the `cooldown_passed` argument passed to `repairs.apply` at `orchestrator.py:601`), and the `earliest_wait` redraft reason are removed, and no `Offer:` line names a message count. When the model is confident one framework fits, it may offer it from the person's second message, under the existing general cooldown (`CLEAR_OFFER_AFTER`), which feature 5 owns.
- **AC-12**: No prompt text sent to the model refers to anything this change removes. `mani_base.md`, `response_format.md`, `redraft.py` and the index intro mention no "Finding the fit", "Never offer one when", `offer_ask`, `offer_purpose`, `stage_ready_when`, `stage_ask`, `next_stage_ask` or per stage "model question" for a framework's own stages, and point at the eight lines instead. `offer_fit: clear` means the model has learned what the framework's `Starts when:` line names.
- **AC-7**: Stage tracking is unchanged: the model reports `state.step`, `Registry.validate_transition` still enforces order, reaching the final stage still leads into the body check in, and every phase id stays the same, so a thread already inside a framework when the content is reseeded carries on.
- **AC-8**: The router behaves as before for the same phrase lists: `tests/unit/test_router.py` passes untouched, and the grief veto still rules Behavioral Activation out.
- **AC-9**: No framework's eight lines name a person from a worked example (she, her, manager, partner and the rest of the existing `_EXAMPLE_PEOPLE` list) or carry an author note (" - use ", " only if ", " only when "). No line except `Sounds like:` carries a word from `repairs.FEELING_WORDS` (`Sounds like:` quotes how a person talks, which can include a feeling). All of this is checked over every file by `tests/evals/`.
- **AC-10**: Real runs, after muhammad's yes. (a) Cost: `--baseline --label before-lean-prompts` before any change and `--label after-lean-frameworks` after, each the default three runs of the baseline set; their median totals per turn are written in `PORT-STATUS.md`. (b) Quality: `journey_abcde` in all three styles, and one journey per other framework with `--style supportive`, each reach the offer, pass every stage in order, and end at the body check in. (c) ABCDE's median findings over the three after runs of the baseline set are no more than the before median. The other five have no before journey to compare, so (b) is their bar.
- **AC-14**: Every framework's contraindication and offering boundary is either carried by its `Skip when:` line (a situation that means "not this one", such as a medical or energy limit for Behavioral Activation) or by a `Never:` line (a harm rule, such as never using DBT STOP in place of the safety protocol), or is listed as cut. muhammad reads that list at the review stop in build step 10 before anything is seeded.
- **AC-11**: The whole `pytest` suite passes with the integration tests running against the local database (not skipped), and output is clean.

## Options considered

### Option 1: Fix in place, trim each stage block

Keep the frontmatter structure and the per stage `[ctx]` rendering, but cut every stage to a one line purpose, a one line readiness test and one ask per style.

**Pros**:
- No code change beyond content; the turn and its tests keep working as they are.
- The client's per style wording survives in a shorter form.

**Cons**:
- Each framework still runs to roughly 60 to 100 lines, and the stage blocks still ride in the uncached `[ctx]` every framework turn.
- The model still receives scripted asks, which the scope sets out to remove.

### Option 2: Eight lines per framework in the cached index, frontmatter keeps only code data

The body of each file becomes the eight model facing lines, seeded into the unused `body` column. The index renders all six bodies. `[ctx]` names only the stage ids. Router lists, phases and the grief veto stay as data that only code reads.

**Pros**:
- The whole model facing framework text is about 50 lines, all in the cached prefix.
- No migration: `body` already exists and nothing reads it.
- One source per fact: a model facing line lives in the body, and code data lives in the frontmatter.

**Cons**:
- The client's scripted replies for unclear answers (for example the abuse reply in ABCDE's first stage) go, so the two `Never:` lines and the model carry that weight.
- Six frameworks change at once, so a regression is harder to pin on one.

### Option 3: Starts and skip lines in the index, the running framework's lines in `[ctx]`

The cached index carries two lines per framework, and the running framework's full eight lines ride in `[ctx]`.

**Pros**:
- A smaller cached prefix.

**Cons**:
- The uncached part grows on every framework turn, which is the expensive direction.
- The eight lines split across two places, so the model reads a framework's rules in two halves.

## Decision

**Chosen option**: Option 2: Eight lines per framework in the cached index, frontmatter keeps only code data.

Every framework becomes eight labelled lines in its file body, rendered verbatim into the cached Framework Index. Stage ids stay as the only per stage data, and code keeps reading the router lists, phases and the grief veto from the frontmatter.

**Implementation skills**: none. This is backend Python and authored content. The `supabase-postgres` skill does not apply, because there is no schema change.

## Rationale

The scope's goal is fewer tokens per turn. The biggest variable cost a framework adds today is the two stage blocks in `[ctx]`, which are uncached and sent on every framework turn. Option 2 removes them entirely and moves what remains into the prefix that is already cached, at 0.01 dollars per million tokens instead of 0.10. Option 1 shrinks the blocks but keeps them in the expensive place. Option 3 moves the wrong half into the uncached block.

The recommended calls, settled here:
- **The `body` column holds the eight lines** (runner up: a new column). It already exists, nothing reads it, and the file then reads exactly like what the model sees. A new column would cost a migration while local and hosted schemas already differ.
- **`activation_conditions` gets the `Starts when:` line** (runner up: an empty string). The column is read by nothing, and its comment asks for it to stay readable to a person looking at the table.
- **The offer candidate in `[ctx]` becomes one `offer: <framework id>` line** (runner up: keep `_stage_lines("offer", …)`). Without an offering block, that call would print only `offer: offering`, which names nothing. The model reads the `Offer:` line from the index.
- **`redirects` stay in the frontmatter** (runner up: delete them). They are read only by `tests/unit/test_router.py`, which proves each neighbour's sentence routes to the right framework. That is router data, which muhammad chose to keep.
- **The negative set check follows the client specs** (runner up: drop it). `test_every_framework_still_carries_its_negative_set` asserts each content file has the "Responses MANI must avoid" table. The table leaves the content, so the test reads `backend/docs/specs/framework-*.md`, which still holds it (§25) and is where the eval examples were transcribed from.
- **The eval runner gains `--style`** (runner up: run the five other journeys in all three styles). muhammad chose one style for the five. Today `--scenario` always plays all three, so without a flag the run would cost three times what was agreed. `--style` is refused with `--baseline`, which already fixes its own set and style.
- **`Starts when:` names what to learn before offering** (runner up: a ninth line). Today `to_find_out` is how `heading_toward` and `offer_fit: clear` work. Folding it into the first line keeps eight lines and gives "clear" a meaning: the model has learned what that line names.
- **The prompts that point at removed things are edited in this change, line by line** (runner up: wait for feature 3's rewrite of the base prompt). Shipping this without those edits would tell the model to read sections that no longer exist. The edits are minimal. Feature 3 has already rewritten both prompts as short YAML rules, so they are edited where they stand.
- **Contraindications are sorted, not dropped silently** (runner up: let `Never:` lines run to 320 characters). Behavioral Activation alone has six. A "not this one" situation belongs in `Skip when:`, a harm rule in `Never:`, and anything cut is listed for muhammad at the review stop.
- **The early offer gate goes with no replacement**. muhammad's call: when the model is confident one framework fits, an early offer is fine. That matches "Offers follow Mani's confidence" in `PORT-STATUS.md`. It also removes a contradiction where the cached `Offer:` line would say wait while `[ctx]` said offer now.
- **Hosted is reseeded in the same deploy as the code** (runner up: a runtime guard that refuses an old body). New code on old content would render 300 line bodies into the prompt. A deploy rule costs nothing, and hosted deploys are manual and need muhammad's yes anyway.
- **Three new journeys** for Structured Problem Solving, ACT Choice Point and DBT STOP. Today only ABCDE, Behavioral Activation and Thought Reframe have one, and AC-10 needs an offer to end path for each framework.

Converting all six in one change departs from the scope's Tracer Bullet order. muhammad accepted that tradeoff (see the premise note). The build plan still drives ABCDE through every check before the other five are written, so the format, the seed check and the turn are proven on one framework first.

## Feature design

**Data model sketch** (no schema change):

| Store | Field | After this change |
|---|---|---|
| `admin.frameworks` | `body` text | the eight lines, verbatim from the file body |
| `admin.frameworks` | `activation_conditions` text | the `Starts when:` line's text |
| `admin.frameworks` | `phases` text[] | unchanged ids, still `offering` first and the two somatic stages appended by the seed |
| `admin.frameworks` | `activation` jsonb | only `strong_signals`, `signals`, `redirects`, and `never_offer_when_said` on Behavioral Activation |
| `admin.frameworks` | `stages` jsonb | only the two somatic stages merged by the seed; no framework's own stages |
| `public.thread_technique_state` | `phase` | unchanged; ids are the same, so in flight rows stay valid |

The file shape, for ABCDE (the wording is the draft /develop refines; the labels, order and ids are the contract):

```markdown
---
id: abcde
name: ABCDE
summary: "<unchanged client description, added to the offer by the backend>"
display_order: 1
phases: [offering, activate, belief, consequence, examine, balanced, closing]
activation:
  strong_signals: [...unchanged...]
  signals: [...unchanged...]
  redirects: [...unchanged...]
---
Starts when: you have learned the event that set it off, what it came to mean about them, and how believing that shapes what they feel or do.
Sounds like: "so I must be", "this proves I", "everyone must think I am", one setback read as a verdict on who they are.
Skip when: one quick thought to reframe (thought_reframe), a decision or plan (structured_problem_solving), a thought evidence cannot settle (act_choice_point), or they only want to be heard.
Stages: activate (what happened) > belief (what it came to mean) > consequence (how believing it affected them) > examine (what supports it, then what challenges it) > balanced (a fairer belief in their words) > closing (how it sits now)
Ends when: they hold a belief that fits all the evidence and sounds like them; they need not feel better, forgive, act or agree.
Offer: mirror what the event came to mean to them, in their words, then ask if they want to look at it together.
Never: invent evidence, name a feeling or effect they did not name, or decide the belief is false.
Never: question whether abuse, threats, coercion, discrimination or danger was real or as serious as it felt.
```

**State transitions**: unchanged. `offering` (offered) → accepted → each id in `phases` in order → `closing` → `somatic_checkin` → `somatic_practice` → retired (phase null). A decline sets the outcome to declined.

**Interface surface** (no HTTP change; the internal seams that change):

| Seam | Change | Inputs | Outputs | Failure |
|---|---|---|---|---|
| `scripts/seed.py::parse_framework` | reads the body as eight labelled lines and checks them | file path | dict with `body`, `activation_conditions` = `Starts when` text, `phases`, `activation`, `stages` = `{}` | `ValueError` naming the file and the broken rule; the seed transaction rolls back |
| `mani/prompts/composer.py::framework_index` | renders a heading and the body per framework | `Registry` | index text | none (seed guarantees the shape) |
| `mani/chat/context.py::build` | stage ids only for framework stages, one `offer: <id>` line, rewritten `stage_note` | `TurnContext`, shortlist | `[ctx]` text | none |
| `mani/chat/context.py::earliest_offer_ok` | removed | | | |
| `mani/chat/redraft.py::reasons` | `earliest_wait` parameter and branch removed | | | |
| `scripts/eval_replies.py` | `--style supportive\|reflective\|direct` limits a scenario to one style | CLI flag | runs | unknown value, or `--style` with `--baseline`, refused by argparse |
| `content/prompts/mani_base.md`, `response_format.md`, `redraft.py:118` | lines naming removed sections or `[ctx]` lines point at the eight lines | | prompt text | |

**Value sourcing**:

| Action | Value produced / displayed | Source |
|---|---|---|
| Seed | eight lines in `body` | the framework file body |
| Seed | `activation_conditions` | the `Starts when:` line of the body |
| Seed | stage ids checked against the `Stages:` line | frontmatter `phases` after `offering`, in order |
| Index | the order frameworks appear in | `admin.frameworks.display_order` |
| `[ctx]` | `stage`, `next_stage` | `thread_technique_state.phase` and the next id in `admin.frameworks.phases` |
| `[ctx]` | `offer: <id>` | the router shortlist's candidate, under today's confidence, closest fit and cooldown rules |
| Model reply | the stage question's wording | written by the model from the `Stages:` line's words, the conversation style in `[ctx]`, and what the person said |
| Model reply | `heading_toward`, `offer_fit: clear` | judged by the model against the `Starts when:` line of each framework in the index |
| Model reply | when to offer | the model's confidence, under the existing `cooldown_passed` (`CLEAR_OFFER_AFTER`) |
| Real runs | which style a journey plays | the new `--style` flag (not with `--baseline`) |
| Real runs | before and after numbers | `--baseline --label before-lean-prompts` and `--label after-lean-frameworks` |

**Key invariants**:
- A framework body is exactly eight labelled lines in the fixed order. Every line is at most 220 characters, and the `Stages:` line at most 320.
- The `Stages:` line names every id in `phases` after `offering`, in order, each followed by a few words in parentheses.
- No model facing framework text is written in Python. The `stage_note` strings are the exception, and they move out under scope feature 8.
- Phase ids never change in this feature, so a thread already in a framework stays valid.
- The grief veto and the crisis screen are untouched.
- No prompt text names a section, a `[ctx]` line or a field this change removes.
- Code and content ship together: no environment runs the new code on old framework rows, or the old code on new ones.

**Security model**: no change. Framework content lives in the `admin` schema, which the Data API does not expose. The seed connects with `DATABASE_URL` as it does today. Nothing in this change reads or writes user rows. The real runs use the eval's own throwaway users, which it removes afterwards.

**Configuration required**: none.

**Critical test scenarios** (unit tests build real framework file text and real `Framework` rows; no mocks of our own code):
- Seed check: a valid eight line file parses. A nine line file, a missing `Ends when:`, swapped labels, a 221 character line, a 321 character `Stages:` line, and a `Stages:` line that skips an id are each refused with the reason named. Verifies **AC-2**.
- Every shipped framework file passes the seed check, and its frontmatter has no key outside the allowed set. Verifies **AC-1**.
- Index: two `Framework` rows render their names, ids and bodies verbatim in display order, with none of the four old section headings. Verifies **AC-3**.
- `[ctx]` while running on a lean framework stage shows the stage id and next id and no `stage_ask` line. On `closing` the `somatic_checkin` block is sent as `next_stage`. On `somatic_checkin` the current block and the somatic note are sent. With an offer open, only `stage: offering` appears. Verifies **AC-4**, **AC-7**, **AC-13**.
- `[ctx]` on the yes turn names the first working stage as `stage`, the second as `next_stage`, and carries the yes turn note. Verifies **AC-5**.
- A confident offer on the second message is no longer redrafted or dropped for being early (the gate is gone). Verifies **AC-6**.
- No prompt file or prompt string in `mani/` contains any of the removed names listed in AC-12. Verifies **AC-12**.
- The eight lines of every file pass the example people and author note patterns, and every line but `Sounds like:` passes the feeling word check. Verifies **AC-9**.
- The existing router and grief veto tests pass unchanged. Verifies **AC-8**.

## Build plan

Ordered Tracer Bullet style: ABCDE goes through the whole path and every check before the other five are written.

1. Ask muhammad's yes, then take the before numbers: `python scripts/eval_replies.py --baseline --label before-lean-prompts` on today's content (about 0.10 to 0.20 dollars per spec 0002). Satisfies **AC-10**.
2. Add `--style` to `scripts/eval_replies.py`, refused together with `--baseline`. Satisfies **AC-10**.
3. Write the format check in `scripts/seed.py::parse_framework`: exactly eight lines with the labels in order, the length caps, the `Stages:` parse rule from AC-2 checked against `phases`, the allowed frontmatter keys (top level and inside `activation`), `activation_conditions` from `Starts when:`, and the file's own `stages` empty, checked before the somatic merge. The seed's printed per framework stage count is reworded to the phase count. Add the seed check unit tests. Note that `tests/unit/test_router.py` and `scripts/eval_replies.py` also call `parse_framework`, so a bad file now fails them too. Satisfies **AC-1**, **AC-2**.
4. Rewrite `content/frameworks/abcde.md` to the eight line shape, drafted from `backend/docs/specs/framework-abcde.md`. `Starts when:` names what to learn, `Offer:` names no message count, and its contraindication and offering boundaries are sorted per AC-14. Satisfies **AC-1**, **AC-6**, **AC-9**, **AC-14**.
5. Rewrite `composer.framework_index` to render name, id and body per framework, with a new intro ("each set of questions is eight lines: when it starts and what to learn first, how it sounds, when to skip it for another, its stages, when it ends, how to offer it, and what never to do; `[ctx]` names the stage you are on"), keeping the "never name it" rule. Rewrite the index tests in `tests/unit/test_composer.py` (around lines 66 to 270, including the `earliest_offer_message` fixture), and replace `test_every_shipped_framework_says_what_it_needs_to_find_out` with the shipped format test. Satisfies **AC-3**.
6. In `context.build`: a framework's own stages render ids only, through `_stage_lines`, which already returns just the id when a stage has no block. Somatic stages keep their blocks as `stage` and as `next_stage`. On the yes turn, `stage` is the first working stage. With an offer open, only `stage: offering` is sent. Replace the offer candidate lines with `offer: <id>`, and remove the `offer_waiting` `stage_ask` filter. Write three `stage_note` strings: the yes turn note (AC-5), the framework stage note and the somatic note (AC-13). Update `tests/unit/test_chat_context.py` (the old line assertions around lines 227 to 422 and 633) and `tests/integration/test_turn.py` (`offer_ask` at about lines 314 and 1030, and `stage_ask` at about 916 and 1363, which become checks that no framework stage block is sent). Satisfies **AC-4**, **AC-5**, **AC-7**, **AC-13**.
7. Remove the earliest offer gate: `context.earliest_offer_ok`, `_earliest_ok` in `orchestrator.py` with its use in the redraft at about lines 481 to 490 and in the `cooldown_passed` argument to `repairs.apply` at about line 601, and the `earliest_wait` parameter and branch in `redraft.py`. Remove their tests (`test_chat_context.py` around lines 652 to 663, `test_redraft.py` line 90). Satisfies **AC-6**.
8. Edit the prompt text that points at removed things, one line at a time. Both prompt files are short YAML rules now. In `content/prompts/mani_base.md`, the `questions`, `offers` and `reasoning` lines that say "Finding the fit" (it becomes the `Starts when:` line), the `offers` line that says "Never offer one when" (it becomes `Skip when:` and `Never:`), and the `in_a_framework` line that says "model question" (it becomes the `Stages:` line). In `content/prompts/response_format.md`, the `ctx` entries `stage_lines`, `facts` (it names `offer_lines`) and `framework_starting` that describe the per stage blocks and the offer block, and the "Finding the fit" line in `reasoning`. Also the redraft note at `mani/chat/redraft.py:118`. The somatic rules under `ending` stay. Satisfies **AC-12**.
9. Rewrite `tests/evals/test_negative_set.py`: the negative set check reads `backend/docs/specs/framework-*.md`, and the `_asks` tests become one check over every framework body with `_EXAMPLE_PEOPLE`, `_AUTHOR_NOTE`, and `repairs.FEELING_WORDS` on every line but `Sounds like:`. Add a unit test that no prompt file and no prompt string in `mani/` names a removed section or line. Satisfies **AC-9**, **AC-12**.
10. Run the whole `pytest` with the local database up and check the integration count is not skipped. Satisfies **AC-11**, **AC-8**.
11. Draft the other five files (Thought Reframe, Structured Problem Solving, ACT Choice Point, Behavioral Activation keeping `never_offer_when_said`, DBT STOP) from their client specs, sorting each contraindication and offering boundary per AC-14. **Stop for muhammad's read of all six files, with the list of cut items, before seeding.** Satisfies **AC-1**, **AC-6**, **AC-9**, **AC-14**.
12. Add journeys `journey_structured_problem_solving`, `journey_act_choice_point` and `journey_dbt_stop` to `scripts/eval_conversations.yaml`, modelled on `journey_abcde` (scripted lines that reach the offer, accept, answer each stage, and answer the body check in). Satisfies **AC-10**.
13. Reseed locally with `python scripts/seed.py` and rerun the whole `pytest`. Satisfies **AC-11**.
14. Ask muhammad's yes, then run the real conversations: `journey_abcde` in all three styles, the five other journeys with `--style supportive`, and `--baseline --label after-lean-frameworks`. Compare with `before-lean-prompts` per AC-10. Satisfies **AC-10**, **AC-5**.
15. Update `backend/PORT-STATUS.md` in the same change: the Frameworks paragraph (eight lines each, the index carries them, no stage blocks, no earliest offer gate), the median totals before and after, and one line under "Decisions in force" ("Each framework is eight model facing lines in the cached index; stage ids, router lists and the grief veto are code data"). Edit the existing "Offers follow Mani's confidence" line in place to say a confident offer has no per framework earliest message. Update the "How the code uses these" list in `backend/docs/specs/README.md`. Satisfies **AC-10**.

## Consequences

**Positive**:
- The uncached `[ctx]` loses two stage blocks, roughly 12 lines, on every framework turn, and the cached index shrinks from five generated sections to about 50 lines.
- A framework is readable in one screen, and changing one needs a content edit and a reseed only.
- The seed check stops the files from growing back.

**Negative / tradeoffs**:
- The client's scripted replies for unclear answers, their per style asks and their worked examples leave what the model reads. Behaviour in the hard cases (an assumed motive, a falsely positive belief, a described abuse) now rests on the `Never:` lines and the model's own judgment. The real runs check the common path, not every edge case.
- Six frameworks change in one step, so a regression in the runs is harder to pin on one framework.
- With the earliest offer gate gone, ABCDE, Thought Reframe and ACT Choice Point can be offered from the person's second message when the model is confident. muhammad accepts that. A wrong early offer is now caught only by the person declining it.
- A thread already inside a framework at reseed loses that stage's purpose and boundaries on its next turn. It does not break (the ids are unchanged), but the next reply may read differently.
- The real runs cost credit, roughly 8 conversations plus two baselines.

**Neutral**:
- No migration. A reseed changes the content, and the app picks it up when its prompt cache expires or the server restarts.
- The client specs in `backend/docs/specs/` stay as provenance and become the only home of the long form content.
- `stage_note` stays Python text until scope feature 8.

## Migration plan

**Strategy**: no schema migration; a content reseed, local first.
**Phases**:
1. Local: reseed after step 12, then run the real runs in step 13.
2. Hosted: no deploy in this feature. Hosted carries a different schema and real people's data, so it needs its own yes from muhammad. When it happens, the code and `python scripts/seed.py` against hosted go out in the same deploy, seed straight after the code. New code on old rows would render the old 300 line bodies into the prompt, and old code on new rows would send no stage guidance at all.

**Rollback**: revert the commit and run `python scripts/seed.py`. Phase ids are unchanged, so threads in flight survive both directions.
**Risks**: a reseed while a thread is inside a framework is safe, since the ids are the same. A prompt cache that has not yet expired (`mani/prompts/cache.py`) serves the old index until it does, so restart the server after reseeding.

## Follow-up

- [x] Scope features 4 and 6 are merged into this spec. Scope row 6 is marked dropped, merged into feature 4.
- [ ] `.claude/BACKEND.md` lists the activation fields (`central_indication`, `to_find_out`, `earliest_offer_message`, `never_offer_when_said`, `contraindications`, `appropriate_when`, `not_when`) as framework content. It goes stale with this change and belongs to `/sync`.
- [ ] `admin.frameworks.activation_conditions` and `stages` hold little after this change and the somatic move in feature 7. Dropping them needs a migration, best decided with feature 7.
- [ ] Feature 5 (one model call) should check whether any redraft reason still assumes the stage blocks exist.
