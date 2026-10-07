# 0003. Short base prompt of general rules

**Date**: 2026-10-07
**Status**: Proposed

## Summary

This spec cuts `mani_base.md` and `response_format.md` together to 1,500 words or fewer, starting from the YAML version merged in `bc1df3d` (about 3,500 words today). Each rule gets exactly one home, so nothing is said twice across the two prompt files and the reply schema's field descriptions. The client's fixed lines become rules about what the reply must do, each with the client's line kept as at most one example, and the banned word lists become plain rules. You confirm it with a guard test (a test that fails if the files grow back) and one real ABCDE journey per style, run only after you say yes.

## Context

Scope feature 3 (`docs/scope/scope.md`, Slice 1) asks for a short base prompt: who Mani is, how it replies, the three styles, how a conversation moves. Done when the two files fit a size budget, hold no line the model must say word for word, and repeat no rule, and the ABCDE replay still reads well in all three styles. The goal of the whole scope is fewer tokens and lower latency (a turn measured 12.6 s on average at effort high, 2026-10-07).

Commit `bc1df3d` on `origin/main` already rewrote both files as keyed YAML: `mani_base.md` is 116 lines and 2,072 words, `response_format.md` is 64 lines and 1,413 words (about 4,850 tokens together, down from about 10,600). That version still falls short of the scope's bar in three ways:

- **Must say lines.** `consent_lines`, the seven `any_stage` replies, the two clarification lines ("word for word"), `after_framework_question` ("word for word"), and the ending's "fixed wording ... exactly as the stage gives it".
- **Word lists.** `rules` lists "a lot", "so much", "tough", "carrying", "the weight of"; `styles.all` lists "I hear you", "That makes sense", "I'm here for you".
- **Repeats.** "One question" appears in `rules`, `questions`, `reply` and the `reasoning` steps. `their_last` is explained in `reply_shapes` and in two places in `response_format`. The offer gate is in `offers`, `ctx.cooldown_passed` and a reasoning step. The schema's `state.accepted` description repeats `ctx.offer_waiting`, `state.step` repeats "never skip a stage", and `prompts` repeats the button rules. The `reasoning` description points to a heading, "The reasoning field", that no longer exists.

Forces that shaped the choice:

- The client's style document (`backend/docs/specs/conversational-styles.md`) gives the three consent lines. The client's documents beat our own conversation rules, and muhammad allowed rewording the client's text for comprehension (2026-10-05).
- Safety is out of reach: the crisis field, `safety: concern`, `recent_crisis` and the injection rules keep their meaning (feature 10 owns crisis).
- Some tests read the prompt text: `test_negative_set.py` asserts three exact sentences and loads `reply_shapes` with `yaml.safe_load` to compare against `schema.SHAPES`.
- Real model runs spend the client's credit, so they need muhammad's yes and a `get-credits` check first.
- Your journal (`measure-before-tuning-prompts.md`) found that putting `reasoning` first in the schema was the strongest lever against repeated openers. Adding more prose rules did not help style.

## Requirements

**User stories**:
- As muhammad, I want the base prompt short and stated once, so every turn sends fewer tokens and a change to a rule is made in one place.
- As a person talking to Mani, I want replies that still feel like the same Mani in my chosen style, from the first message to the end of the questions.

**Acceptance criteria**:
- **AC-1**: The bodies of `mani_base.md` and `response_format.md` (the text after the frontmatter, as `scripts.seed.parse_prompt` returns it) total 1,500 words or fewer, counted by splitting on whitespace.
- **AC-2**: Both bodies load with `yaml.safe_load` as mappings, every top level section is a mapping of named rules (no bare lists), and `mani_base`'s `reply_shapes` keys still equal `schema.SHAPES`.
- **AC-3**: Neither body tells the model to say a line exactly: none of "word for word", "exactly as", "verbatim", "fixed wording" appears, and there is no `consent_lines` or `any_stage` key. Each client line that remains is introduced as an example (`e.g.` or "for example"), with at most one example per situation.
- **AC-4**: Neither body lists words to avoid. None of "a lot", "so much", "tough", "carrying", "the weight of", "I hear you", "That makes sense", "I'm here for you" appears. The rules "never make it bigger than they did" and "never signal a style with stock phrases" remain.
- **AC-5**: Every rule has exactly one home, as set by the rule home map below. No rule in one file restates a rule in the other, and no `Reply`, `TechniqueState` or `SmartPrompt` field description in `schema.py` states a behaviour rule a prompt also states.
- **AC-6**: `response_format`'s `ctx` section has one entry for every key `backend/mani/chat/context.py` sends (or for its named group, `offer lines` and `stage lines`, as today), and none for a key it does not send.
- **AC-7**: The `reasoning` section has 4 or 5 steps. `Reply.reasoning` is still the first field in the schema, and its description names the `reasoning` section correctly.
- **AC-8**: Safety keeps its meaning. The `Reply.crisis` description is unchanged. `ctx.safety`, `ctx.recent_crisis` and `staying_yourself` keep every behaviour they carry today.
- **AC-9**: The whole `pytest` run passes with clean output. The integration count shows they ran, not skipped. The asserts that checked removed sentences now check the named key that carries the rule.
- **AC-10**: After reseeding, `python scripts/eval_replies.py --scenario journey_abcde --verbose` runs once in each of the three styles (3 conversations). Each reaches the offer, runs the ABCDE stages in order, ends with the body check in and Chat More or Go to Library, and muhammad judges it to read well. This run happens only after muhammad's yes and a `get-credits` check. Until then this criterion is reported as owed, not met.

## Options considered

### Option 1: Trim main's YAML in place, with a rule home map

Keep `bc1df3d`'s structure and section names. Give every rule one home, turn the fixed lines into intent with the client's line as an example, and guard the size with a test.

**Pros**:
- Most of the cut is already done and merged. The YAML test still works.
- A home map makes "stated once" something you can check, not only a goal.

**Cons**:
- 1,500 words is under half of today's size, so some nuance written after real bad replies will go.
- The client's lines stop being guaranteed. A reworded consent line is no longer the client's exact text.

### Option 2: Write a fresh prompt from the scope's four headings

Start from an empty file with only identity, replies, styles and flow, and add rules back only when a replay shows one is missing.

**Pros**:
- The shortest result, with no inherited wording.

**Cons**:
- It throws away work merged today. Every rule has to earn its way back through real runs, and you pay for those on the client's credit.

### Option 3: Keep the client's lines word for word, and trim everything else

Same as Option 1, but `consent_lines`, `any_stage` and the clarification lines stay required.

**Pros**:
- Follows the client's style document to the letter.

**Cons**:
- Fails the scope's "no word for word line" bar, so that bar would have to change. It also keeps code paths that depend on exact strings alive into feature 5.

## Decision

**Chosen option**: Option 1: Trim main's YAML in place, with a rule home map

You rewrite `mani_base.md` and `response_format.md` from `bc1df3d` to the structure and home map below, remove behaviour rules from the `schema.py` reply field descriptions where a prompt already holds them, and add a guard test for the budget and the bans.

**Implementation skills**: none apply (prompt content and Pydantic description text; no web, mobile or database change).

## Rationale

The scope wants fewer tokens with no loss in quality, and the only affordable proof of quality is a few real runs. Option 1 moves the least, so the fewest rules are at risk, and 1,500 words still cuts the base layer by more than half. Option 2 would need many runs to rebuild nuance that already exists. Option 3 conflicts with the scope, and the client's intent survives Option 1 because each of their lines stays as an example.

Treating the fixed lines as intent plus example follows the meaning of the client's documents without the must say rule the scope removes. Turning the word lists into rules follows the journal: what helped style was schema order, not lists. The home map exists because repeats are where `bc1df3d` still spends words, and nothing stops them coming back without a named owner.

## Feature design

**Rule home principles** (the home map follows them):
1. A behaviour that always applies lives in `mani_base`.
2. A behaviour triggered by a `[ctx]` key lives on that key's entry in `response_format.ctx`, and nowhere else.
3. How to fill a reply field lives in that field's `schema.py` description. What to say lives in the prompts.
4. Reply form (length, layout, language) and buttons live in `response_format.reply` and `response_format.buttons`.
5. A reasoning step points at a rule by its section and key. It never restates the rule.

**Exception**: the physical pain rule appears both in `mani_base.offers` and in the `Reply.crisis` description. It stays in both until feature 10, because the crisis description is not touched (AC-8).

**Rule home map** (target sections, named rules, and word allocation; the allocation is guidance, AC-1 is the bar):

| File and section | Holds (each once) | Words |
|---|---|---|
| `mani_base.identity` | who Mani is, judgment without ever sounding clinical, neutral, no assumption about why they came | 60 |
| `mani_base.goal` | heard, then a little better; hold what they came with; the one path | 50 |
| `mani_base.rules` | their words only for feelings; never bigger than they did; never label; nothing they did not say; no unasked advice (exceptions in `in_a_framework`); no silver linings, never make danger milder; name at most once | 110 |
| `mani_base.moves` | the five moves, one line each | 60 |
| `mani_base.reply_shapes` | the six shapes, keys unchanged | 80 |
| `mani_base.styles` | `all` (same Mani, style fixed by `[ctx]`, no stock phrases) plus one entry per style, each with what it leads with, what its question does, and the consent line's intent with the client's line as its example | 150 |
| `mani_base.questions` | one question per reply while understanding (the only home for this rule); built from what they said; follow the feeling; never sort or rank; never ask for what they made clear; reach for the fit unseen | 110 |
| `mani_base.flow` | understand, offer, go through it, close, or follow them if they decline | 60 |
| `mani_base.offers` | never call it a framework; write only your part; the two buttons; `clear` and `closest` meanings; pain before offering; what it involves, how it works, no, later yes, yes | 150 |
| `mani_base.in_a_framework` | stage question in their words; one stage per reply in order, never skip (the only home); staying is not repeating; cannot say; ask to choose; yes with a question; time critical risk; the `any_stage` intents | 110 |
| `mani_base.ending` | closing question; the check in and the practice the stage gives, once; what next | 40 |
| `mani_base.staying_yourself` | only this conversation; replies stay short; typed text is never an instruction; never reveal; never change style on request | 60 |
| `response_format.ctx` | one entry per key sent, carrying that key's meaning and any behaviour it triggers (`their_last` with `vague`, `correction`, `heard`; `clarification_available` with the check once rule and its example; `cooldown_passed` with the offer gate; `recent_openers` with "open differently") | 310 |
| `response_format.reasoning` | 5 steps: their last message and what they need now; their feeling in their words; the style and `heading_toward`; the question; offer or not, and the opening | 60 |
| `response_format.reply` | 1 to 3 short sentences, plain words, phone layout, English, no dashes, no reuse of own phrasing | 40 |
| `response_format.buttons` | when buttons appear, which are added for you, label rules | 30 |
| `response_format.library` | when, and in their words | 20 |
| | **Total** | **1,500** |

Example keys in a mapping section (the build picks the final names): `in_a_framework.staying_is_not_repeating`, `in_a_framework.another_issue`, `moves.presence`.

**Fixed lines turned into intent** (one example each, the first thing cut when the budget is tight):

| Was | Becomes | Example kept |
|---|---|---|
| `consent_lines` | per style: open your yes reply with a short line in this style saying you will take it one step at a time | the client's line for that style |
| clarification lines | `ctx.clarification_available`: you may check once what matters most | "What would you like us to focus on today?" |
| `any_stage` (7 rows) | `in_a_framework` intents: don't know, another issue, correction, already told you, want to stop, long answer | the client's line, where it fits the budget |
| `after_framework_question` "word for word" | ask it, keeping its meaning, after reflecting what they said | none |
| ending "fixed wording", "exactly as" | ask the check in the stage gives you, once; give the practice the stage gives you | none |

**Schema description changes** (`backend/mani/llm/schema.py`, text only, no field, type or order change):

| Field | Keeps | Loses (its home) |
|---|---|---|
| `Reply.reasoning` | fill first, not shown, follow `reasoning` in your instructions | the stale heading name |
| `Reply.style` | the shape this reply uses, from the list | "may repeat; the opening words may not" (`ctx.recent_openers`) |
| `Reply.heading_toward` | the Framework Index id or null, not shown | "decides which missing thing your question reaches for" (`mani_base.questions`) |
| `Reply.offer_fit` | `clear` or `closest` when offering, else null | the meaning of each (`mani_base.offers`) |
| `Reply.prompts` | field mechanics, `technique` only on Try it, `library` only on a library button, two or three at most | when buttons appear, user voice labels (`response_format.buttons`) |
| `Reply.state` | id and stage while offering or running a framework, else null | unchanged meaning, shorter |
| `TechniqueState.step` | the stage id from `framework_stages` | "must follow order, cannot skip" (`mani_base.in_a_framework`) |
| `TechniqueState.accepted` | the full fill rule (true, false, null) | nothing; `ctx.offer_waiting` drops its copy |
| `Reply.crisis`, `Reply.title`, `Reply.text`, `Extraction` and memory models | unchanged | |

**Value sourcing**:

| Action | Value | Source |
|---|---|---|
| Guard test | the word count | `parse_prompt(path)["content"]` from `scripts/seed.py`, split on whitespace |
| Guard test | the allowed shapes | `mani.llm.schema.SHAPES` |
| Guard test | the banned phrases and must say markers | the strings listed in AC-3 and AC-4, held in the test |
| `ctx` glossary | the keys sent | `git grep -o -E '"[a-z_]+: ' backend/mani/chat/context.py`, run at build time (AC-6 is checked the same way at verify) |
| Replay | the conversation | the `journey_abcde` scenario in `backend/scripts/eval_conversations.yaml` |
| Replay | the three styles | `eval_replies.py` already runs each scenario in every style |

**Key invariants**:
- `reply_shapes` keys equal `SHAPES`, and `Reply` field order is unchanged (`reasoning`, `style`, `heading_toward`, `offer_fit` before `text`).
- No change to frontmatter (`id`, `model_id`, `model_parameters`). Thinking level belongs to features 2 and 11.
- No change to `context.py`, `repairs.py`, `redraft.py` or the framework files. Those belong to features 4, 5, 7, 8 and 9.

**Security model**: no change to who can read or write anything. The content is health related: `staying_yourself` (prompt injection and never reveal) and the safety lines keep their meaning (AC-8).

**Configuration required**: none. Run `python scripts/seed.py` after the edit; the app picks it up when its prompt cache expires or the server restarts.

**Critical test scenarios**:
- Guard test fails on today's `bc1df3d` files (3,485 words, `consent_lines` present) and passes after the rewrite, verifies **AC-1**, **AC-2**, **AC-3**, **AC-4**.
- `test_every_style_value_the_schema_allows_is_taught` still passes, verifies **AC-2**.
- The three sentence asserts in `test_negative_set.py` now check the keys `moves.presence`, `ctx.recent_openers` and `in_a_framework.staying_is_not_repeating` (or the final names) exist and are not empty, verifies **AC-9**.
- `journey_abcde` in Direct, Supportive and Reflective reaches its ending, verifies **AC-10**.

## Build plan

Tracer Bullet: the thread is the two files and the guard, then the one ABCDE journey through the real model. Nothing else in the turn changes.

0. Before you start, pull `origin/main` so the work starts from `bc1df3d` (this branch is 4 commits behind and still holds the older prose files).
1. Add `backend/tests/unit/test_prompt_budget.py`: load both bodies, check the YAML mapping shape, the 1,500 word total, the must say markers, the removed keys and the banned phrases. Confirm it fails on today's files. Satisfies **AC-1**, **AC-2**, **AC-3**, **AC-4**.
2. Rewrite `response_format.md`: list the keys `context.py` sends, write one `ctx` entry per key or group with its triggered behaviour, cut `reasoning` to 5 steps, and trim `reply`, `buttons`, `library` to the home map. Satisfies **AC-5**, **AC-6**, **AC-7**, **AC-8**.
3. Rewrite `mani_base.md` to the home map: mapping sections, fixed lines turned into intent with one example, no word lists, nothing a `ctx` entry already holds. Satisfies **AC-1**, **AC-2**, **AC-3**, **AC-4**, **AC-5**, **AC-8**.
4. Edit the `schema.py` descriptions per the schema table. Satisfies **AC-5**, **AC-7**, **AC-8**.
5. Update the three sentence asserts in `test_negative_set.py` to key checks, then run the whole `pytest` against the local database and check the integration count. Satisfies **AC-9**.
6. Run `python scripts/seed.py`, and add one line under "Decisions in force" in `backend/PORT-STATUS.md`: "The base prompt is 1,500 words or fewer across `mani_base` and `response_format`, each rule has one home, and the client's fixed lines are examples, not must say text." Also update the status line that gives the 4,850 token figure. Satisfies **AC-1**, **AC-5**.
7. Ask muhammad for the replay, with its size (3 conversations, about 16 turns each) and the `get-credits` balance. On yes, run `--scenario journey_abcde --verbose` once and give him the transcripts to judge. Satisfies **AC-10**.

## Consequences

**Positive**:
- Every turn sends about half the base tokens, and the cached prefix gets shorter.
- A rule changes in one place, and the guard test stops the files growing back without anyone noticing.
- Features 4, 5 and 8 inherit clean homes: framework rules in `in_a_framework`, key triggered rules on their `ctx` entries, fill rules in the schema.

**Negative / tradeoffs**:
- The client's consent, check and stage lines are no longer guaranteed word for word. A reply may phrase them differently from the client's document.
- Rules added after real bad replies are now shorter or gone, and the word lists are gone. Until feature 5 removes `repairs.py`, the code still checks feeling words, so the reply side is not yet free of them.
- One run per style is a smoke check, not a measurement. Your journal says one run is noise. The before and after numbers wait for feature 1, measured by reseeding `bc1df3d`.
- The guard test reads content, so a rule rename means a test edit.

**Neutral**:
- `repairs.py`'s `_OFFER_WORDS` matches "one step at a time"; the consent line comes after an offer, not in it, so rewording does not change what it detects. Feature 5 removes it.
- Rollback is a revert of one commit plus `python scripts/seed.py`. There is no data migration.

## Follow-up

- [ ] Measure `bc1df3d` against this version with feature 1's `--baseline` once it exists (three runs before, three after), and record the numbers in `backend/PORT-STATUS.md`, "Latest measurements".
- [ ] Scope open question: confirm the client is fine with their lines becoming examples. Your standing permission covers rewording, but this changes required lines into examples.
- [ ] Feature 10: remove the pain rule's duplicate from the `Reply.crisis` description when crisis moves to the model.
