# 0003. Short base prompt of general rules

**Date**: 2026-10-07
**Status**: Superseded (2026-10-07)
**Why**: muhammad dropped this spec's acceptance criteria and had the base prompt rewritten shorter, without the home map, the `ctx` key list or the word guard test. The decision now lives in `backend/PORT-STATUS.md`, "Decisions in force". Read the rest as history only.

## Summary

This spec cuts `mani_base.md` and `response_format.md` together to 2,800 words or fewer, starting from the YAML version merged in `bc1df3d` (3,436 words of body today). The limit is one number in a guard test (a test that fails if the files grow back). The test also fails when the files sit 50 or more words under the limit, so the limit follows the files down, and a rise needs an `/architect` update. Each rule gets exactly one home, so nothing is said twice across the two prompt files and the reply schema's field descriptions. The client's fixed lines become rules about what the reply must do, with the client's line kept as at most one example. The exceptions are the lines the code detects by their exact words; those stay word for word until feature 9 moves them out of Python. You confirm it with the guard test and one real ABCDE journey per style, run only after you say yes.

## Context

Scope feature 3 (`docs/scope/scope.md`, Slice 1) asks for a short base prompt: who Mani is, how it replies, the three styles, how a conversation moves. Done when the two files fit a size budget, hold no line the model must say word for word, and repeat no rule, and the ABCDE replay still reads well in all three styles. The scope says "line budget"; this spec counts words instead, because the YAML lines run to paragraph length and a line count would hide their size. The goal of the whole scope is fewer tokens and lower latency (a turn measured 12.6 s on average at effort high, 2026-10-07).

Commit `bc1df3d` on `origin/main` already rewrote both files as keyed YAML. Counting the body only (what `scripts.seed.parse_prompt` returns), `mani_base` is 2,044 words and `response_format` is 1,392, about 4,850 tokens together, down from about 10,600. That version still falls short of the scope's bar in three ways:

- **Must say lines.** `consent_lines`, the seven `any_stage` replies, the two clarification lines and `after_framework_question` ("word for word"), and the ending's "fixed wording ... exactly as the stage gives it".
- **Word lists.** `rules` lists "a lot", "so much", "tough", "carrying", "the weight of"; `styles.all` lists "I hear you", "That makes sense", "I'm here for you".
- **Repeats.**
  - "One question" appears in `rules`, `questions`, `reply` and the `reasoning` steps.
  - `their_last` is explained in `reply_shapes`, in `ctx` and again as its own section.
  - The correction rule is in both `their_last.correction` and `any_stage`.
  - The offer gate is in `offers`, `ctx.cooldown_passed` and a reasoning step.
  - The `state.accepted` rule is in the schema, `ctx.offer_waiting` and `ctx.this_thread`.
  - "Never skip a stage" is in the `state.step` description and in `in_a_framework`.
  - The `prompts` description repeats the button rules.
  - The `reasoning` description points to a heading, "The reasoning field", that no longer exists.
  - `offers` carries a garbled sentence: "or one that Never offer one when rules out".

Measured by section, the large parts are `ctx` (657 words), `in_a_framework` plus `any_stage` (451), `offers` (352), `reasoning` (314), `reply` plus `buttons` plus `library` (231) and `their_last` (184). Writing the files with every repeat, list, `any_stage` and `consent_lines` removed gave 3,220 words, only 6% under today's 3,436. Most of the size is behaviour that has an owner: the `ctx` glossary for about 28 keys, the stuck cases in `in_a_framework`, and the offer subcases. A terse pass that kept every behaviour reached 2,797. 2,000 would need about 800 words of that behaviour dropped, and only real runs could show which of it is safe to lose.

Forces that shaped the choice:

- The client's style document (`backend/docs/specs/conversational-styles.md`) gives the three consent lines. The client's documents beat our own conversation rules, and muhammad allowed rewording the client's text for comprehension (2026-10-05).
- **Some client lines are state the code reads.**
  - `context.clarification_used` (`context.py:119`) decides whether the one check question has been used by matching `CLARIFICATION_QUESTIONS` in Mani's past replies.
  - `context._after_framework_question` (`context.py:95`) picks the next of the three after framework questions by matching `AFTER_FRAMEWORK_QUESTIONS`.
  - `repairs._without_clarification` strips only the exact clarification lines.
  - The eval validator `after_framework_questions_asked` matches the exact questions, and `journey_abcde` expects it.
  - If any of these lines were reworded, the check question would be offered forever and the same after framework question would be served every turn.
- The body check in and the practice are already sent word for word by code (`repairs.with_the_check_in`, `repairs.practice_for`). The offer's permission question also comes from code (`repairs.PERMISSION_QUESTIONS`). The prompt does not need to demand any of them.
- Every framework stage carries its own `if_unclear` lines, sent each turn as `stage_if_unclear`, which already covers most of what `any_stage` says.
- Safety is out of reach: the crisis field, `safety: concern`, `recent_crisis` and the injection rules keep their meaning (feature 10 owns crisis).
- Some tests read the prompt text: `test_negative_set.py` asserts three exact sentences and loads `reply_shapes` with `yaml.safe_load` to compare against `schema.SHAPES`.
- Real model runs spend the client's credit, so they need muhammad's yes and a `get-credits` check first.
- Your journal (`measure-before-tuning-prompts.md`) found that putting `reasoning` first in the schema was the strongest lever against repeated openers. Adding more prose rules did not help style.

## Requirements

**User stories**:
- As muhammad, I want the base prompt short and stated once, so every turn sends fewer tokens and a change to a rule is made in one place.
- As a person talking to Mani, I want replies that still feel like the same Mani in my chosen style, from the first message to the end of the questions.

**Acceptance criteria**:
- **AC-1**: The bodies of `mani_base.md` and `response_format.md` (the text `scripts.seed.parse_prompt(path)["content"]` returns) total 2,800 words or fewer, counted by splitting on whitespace. The limit is the constant `WORD_BUDGET` in the guard test, and the test holds the total in a band, `WORD_BUDGET - 50 < total <= WORD_BUDGET`. Its failure message prints the total and the limit to use, which is `ceil(total / 50) * 50`. A change that leaves the total 50 or more under the limit lowers `WORD_BUDGET` in the same change. A raise needs an `/architect` update of this spec.
- **AC-2**: Both bodies load with `yaml.safe_load` as mappings, with no duplicate key at any level and no YAML list anywhere. Every section is a mapping of named rules, using the key names in the home map below. `mani_base`'s `reply_shapes` keys still equal `schema.SHAPES`.
- **AC-3**: The model is never told to say a line exactly, with one named exception. None of "word for word", "exactly as", "verbatim", "fixed wording" appears, except inside `ctx.clarification_available` and `ctx.after_framework_question`, whose lines the code detects by their exact words. There is no `consent_lines` or `any_stage` key at the top level of `mani_base`. Any other client line is introduced as an example (`e.g.` or "for example"), with at most one example per situation. That last part is checked by reading, not by the guard test.
- **AC-4**: Neither body lists words to avoid. None of "a lot", "so much", "tough", "carrying", "the weight of", "I hear you", "That makes sense", "I'm here for you" appears, matched as whole words and ignoring case. The rules `rules.never_bigger` and `styles.all` ("never signal a style with stock phrases") remain.
- **AC-5**: Every rule has exactly one home, as set by the rule home map below. No rule in one file restates a rule in the other, and no `Reply`, `TechniqueState` or `SmartPrompt` field description in `schema.py` states a behaviour rule a prompt also states.
- **AC-6**: `response_format.ctx` holds exactly the entries in the `ctx` key list below: `about`, one per single key, one per group, and nothing for a key the code does not send. This is checked by reading at verify, against `context.py`.
- **AC-7**: `response_format.reasoning.steps` is a mapping of exactly 5 named steps. `Reply.reasoning` is still the first field in the schema, and its description names the `reasoning` section correctly.
- **AC-8**: Safety keeps its meaning. The `Reply.crisis` description is unchanged. `ctx.safety` carries every behaviour it has today, plus "the questions resume from the same stage once they are okay to go on" (moved from `any_stage`). `ctx.recent_crisis` and `staying_yourself` keep every behaviour they carry today.
- **AC-9**: The whole `pytest` run passes with clean output, and the integration count shows the tests ran rather than skipped. The two `test_negative_set.py` tests that asserted exact prompt sentences are deleted, not weakened.
- **AC-10**: After reseeding, `python scripts/eval_replies.py --scenario journey_abcde --verbose` runs once in each style (3 conversations, 16 turns each). It passes when each conversation:
  - reaches the offer, runs the ABCDE stages in order, gives the body check in, and reaches Chat More;
  - has no `after framework` finding and no `repeated opener` finding in the eval's output;
  - is judged by muhammad to read well.

  This run happens only after muhammad's yes and a `get-credits` check. Until then this criterion is reported as owed, not met.

## Options considered

### Option 1: Trim main's YAML in place, with a rule home map

Keep `bc1df3d`'s structure. Give every rule one named home. Turn the fixed lines into intent with the client's line as an example, except the lines code detects. Guard the size with a test.

**Pros**:
- Most of the cut is already done and merged. The YAML test still works.
- Named keys make "stated once" something you can check, not only a goal.

**Cons**:
- Rules added after real bad replies get shorter, and the word lists go.
- The consent lines and stage replies are no longer guaranteed word for word.

### Option 2: Write a fresh prompt from the scope's four headings

Start from an empty file with only identity, replies, styles and flow, and add rules back only when a replay shows one is missing.

**Pros**:
- The shortest result, with no inherited wording.

**Cons**:
- It throws away work merged today. Every rule has to earn its way back through real runs, and you pay for those on the client's credit.

### Option 3: Keep every client line word for word, and trim everything else

Same as Option 1, but `consent_lines` and `any_stage` stay required as well.

**Pros**:
- Follows the client's style document to the letter.

**Cons**:
- Fails the scope's "no word for word line" bar for lines nothing in the code needs exact, and `any_stage` repeats what each stage's `if_unclear` already sends.

## Decision

**Chosen option**: Option 1: Trim main's YAML in place, with a rule home map

You rewrite `mani_base.md` and `response_format.md` from `bc1df3d` to the home map below. You remove behaviour rules from the `schema.py` reply field descriptions where a prompt already holds them. You add a guard test for the budget, the structure and the bans, and you delete the two tests that asserted exact prompt sentences.

**Implementation skills**: none apply (prompt content and Pydantic description text; no web, mobile or database change).

## Rationale

The scope wants fewer tokens with no loss in quality, and the only affordable proof of quality is a few real runs. Option 1 moves the least, so the fewest rules are at risk. 2,800 words is a 19% cut that keeps every behaviour that has an owner. A first draft showed that 2,000 cannot do both. Option 2 would need many runs to rebuild nuance that already exists. Option 3 keeps text nothing depends on.

Lines the code detects stay exact, because rewording them silently breaks state tracking (`clarification_used`, `_after_framework_question`). Feature 9 moves them out of Python together with the code that matches them. Sentences that demand what the code already enforces (the check in, the practice, the permission question) are dropped rather than reworded. Turning the word lists into rules follows the journal: what helped style was schema order, not lists. Named keys exist because repeats are where `bc1df3d` still spends words, and nothing stops them coming back without a named owner.

The limit is a band, not only a ceiling, because a ceiling alone lets the files drift back up and wastes every deletion. With a band the test, not a promise each later spec has to remember, keeps the limit honest: it goes red when the files are 50 or more words under it, and it prints the number to use. The price is that a feature which adds rules has no slack and plans a raise. It is a guard, not a promise of 2,000: the `ctx` entries those features can remove or rewrite (`offer_lines`, `stage_lines`, `next_stage_lines`, `stage_note`, `rewrite`, `recent_openers`, `recent_styles`) are about 130 words today.

## Feature design

**Rule home principles** (the home map follows them):
1. A behaviour that always applies lives in `mani_base`.
2. A behaviour triggered by a `[ctx]` key lives on that key's entry in `response_format.ctx`, and nowhere else.
3. How to fill a reply field lives in that field's `schema.py` description. What to say lives in the prompts.
4. Reply form (length, layout, language) and buttons live in `response_format.reply` and `response_format.buttons`.
5. A reasoning step points at a rule by its section and key. It never restates the rule.

**Exceptions**:
- The physical pain rule appears both in `mani_base.offers.pain_first` and in the `Reply.crisis` description. It stays in both until feature 10, because the crisis description is not touched (AC-8).
- `Reply.state` keeps its "REQUIRED ... you MUST populate" emphasis. The orchestrator reads `state` to track the stage, and the scripted model tests would not catch a model that stopped filling it.

**Rule home map** (key names are fixed; the word column is the size as built, not counting each section's own key, so it sums to 2,780 against the 2,797 total; AC-1 is the bar):

| Section | Named rules (each once) | Words |
|---|---|---|
| `mani_base.identity` | `who`, `judgment`, `neutral` | 91 |
| `mani_base.goal` | `outcome`, `hold_on` (the path lives in `flow`) | 35 |
| `mani_base.rules` | `their_words`, `never_bigger`, `never_label`, `nothing_unsaid`, `no_unasked_advice`, `no_silver_linings`, `name_once` | 132 |
| `mani_base.moves` | `acknowledgment`, `acceptance`, `mirroring`, `permission`, `presence` | 79 |
| `mani_base.reply_shapes` | the six shapes, keys unchanged | 86 |
| `mani_base.styles` | `all` (same Mani, style fixed by `[ctx]`, no stock phrases); `direct`, `supportive`, `reflective`, each with what it leads with, what its question does, and the consent line's intent with the client's line as its example | 190 |
| `mani_base.questions` | `one_per_reply` (the only home for this rule), `from_their_words`, `plain_words`, `follow_the_feeling`, `never_narrow`, `nothing_named_yet`, `reach_for_the_fit`, `no_generic` | 197 |
| `mani_base.flow` | `understand`, `offer`, `go_through` (and close as `ending` says), `follow_them` | 65 |
| `mani_base.offers` | `never_a_framework`, `your_part`, `buttons`, `clear`, `closest`, `never_when` (the garbled sentence, fixed), `pain_first`, `what_it_involves`, `how_it_works`, `no_or_ignored`, `on_yes` | 306 |
| `mani_base.in_a_framework` | `stage_question`, `one_stage_per_reply` (the only home for "never skip"), `staying_is_not_repeating`, `no_confirming`, `cannot_say`, `ask_to_choose`, `yes_with_a_question`, `time_critical_risk`, `another_issue`, `want_to_stop`, `long_answer` | 342 |
| `mani_base.ending` | `closing_question`, `check_in` (ask the one the stage gives you, once), `practice` (the one the stage gives you, none for pain, breathing trouble or faintness), `what_next` | 80 |
| `mani_base.staying_yourself` | `only_this`, `short_replies`, `not_instructions` | 103 |
| `response_format.ctx` | `about` plus one entry per key in the list below | 736 |
| `response_format.reasoning` | `about`; `steps`: `their_last_message`, `their_feeling`, `style_and_heading`, `the_question`, `offer_and_opening` | 175 |
| `response_format.reply` | `plain_words`, `length`, `layout`, `language`, `fresh_phrasing` | 83 |
| `response_format.buttons` | `when`, `added_for_you`, `labels` | 53 |
| `response_format.library` | `when`, `describe` | 27 |
| | **Total** (2,800 at most) | **2,797** |

The feature that renames or removes an entry updates this map and the `ctx` key list below in the same change, through `/architect`.

**Budget ratchet**:
- The limit is the constant `WORD_BUDGET` in `backend/tests/unit/test_prompt_budget.py`. It starts at 2,800.
- The guard test holds `WORD_BUDGET - 50 < words <= WORD_BUDGET` and prints `words` and `ceil(words / 50) * 50` in its failure message. Lowering is not a step any spec has to remember: a change that takes the total 50 or more under the limit turns the test red and names the new value.
- The test judges the net total of both files. It does not look at which rules were touched, so a change that removes one entry and adds another is judged on the difference.
- A raise needs an `/architect` update of this spec (AC-1). Headroom today is 3 words. Feature 4's prompt edits (its step 8) can add words, so they stay within that headroom or ask for a raise. Features 7 (ending as prompt rules) and 10 (crisis moves to the model) will probably add prompt text and should plan a raise.
- Expected lowering: feature 4 (spec `0005-framework-in-8-lines`, AC-4) keeps only stage ids in `[ctx]`, so `offer_lines`, `stage_lines`, `next_stage_lines` and `stage_note` shrink or go. Feature 5 removes `rewrite` with the redraft loop, and `recent_openers` and `recent_styles` if the repairs that read them go. Those seven entries are about 130 words today.
- 2,000 is a direction, not a bar. Reaching it means dropping rules from `in_a_framework` (342 words), `offers` (306) or `reasoning` (175), which is a behaviour decision for the feature that makes them unnecessary, or for measured runs (feature 11).

**`ctx` key list** (from `backend/mani/chat/context.py` on `bc1df3d`; AC-6 checks the file against this):
- **Single keys, one entry each (21)**: `conversation_style`, `conversation_phase`, `question_focus`, `their_last`, `clarification_available`, `offer_waiting`, `cooldown_passed`, `closest_fit`, `this_thread`, `library_pending`, `safety`, `recent_crisis`, `recent_styles`, `recent_openers`, `framework_shortlist`, `framework_starting`, `active_framework`, `framework_stages`, `stage_note`, `after_framework_question`, `rewrite`.
- **Folded into another entry (3)**: `since_last` into `cooldown_passed`; `history` and `current_phase` into `this_thread`.
- **Groups, one entry each (3)**: `offer_lines` (`offer`, `offer_purpose`, `offer_listen_for`, `offer_ready_when`, `offer_boundaries`, `offer_if_unclear`, `offer_ask`), `stage_lines` (`stage` and its `stage_*` fields), `next_stage_lines` (`next_stage` and its `next_stage_*` fields). These are built with f strings in `_stage_lines`, so a grep for literal keys misses them.
- **Nested**: `their_last` is a mapping with `when`, `vague`, `correction` (the only home for the correction rule, including "they say they already told you") and `heard`. It counts as one entry.
- **Triggered behaviour that moves onto its key**:
  - `clarification_available` gets the check once rule and the two client lines, word for word.
  - `cooldown_passed` gets the offer gate.
  - `recent_openers` gets "open differently".
  - `offer_waiting` points to `state.accepted`, without restating it.
  - `safety` gets the stage resume clause.
  - `after_framework_question` is asked word for word, after reflecting what they said.
- `rewrite` is sent by `context.py:190` for a redraft; feature 5 removes its entry with its code.

**Fixed lines, what becomes of each**:

| Was | Becomes | Example kept |
|---|---|---|
| `consent_lines` | `styles.<style>`: open the yes reply with a short line in this style saying you will take it one step at a time | the client's line for that style |
| clarification lines | `ctx.clarification_available`, word for word (code detects them) | not an example, required |
| `after_framework_question` | `ctx.after_framework_question`, word for word (code detects them) | not an example, required |
| `any_stage` "don't know" | removed; each stage's `stage_if_unclear` carries it, and `in_a_framework.cannot_say` covers practical problems | none |
| `any_stage` "another issue", "want to stop" | `in_a_framework.another_issue`, `in_a_framework.want_to_stop` | the client's line |
| `any_stage` "they correct you", "already told you" | `ctx.their_last.correction` | none |
| `any_stage` "a long answer" | `in_a_framework.long_answer` | none |
| `any_stage` "safety is concern" | `ctx.safety`, with the resume clause | none |
| ending "fixed wording", "exactly as" | `ending.check_in` and `ending.practice` without the exactness; code sends both word for word | none |

**Schema description changes** (`backend/mani/llm/schema.py`, text only, no field, type or order change):

| Field | Keeps | Loses (its home) |
|---|---|---|
| `Reply.reasoning` | fill first, not shown, follow the `reasoning` section in your instructions | the stale heading name |
| `Reply.style` | the shape this reply uses, from the list | "may repeat; the opening words may not" (`ctx.recent_openers`) |
| `Reply.heading_toward` | the Framework Index id or null, not shown | "decides which missing thing your question reaches for" (`questions.reach_for_the_fit`) |
| `Reply.offer_fit` | `clear` or `closest` when offering, else null | the meaning of each (`offers.clear`, `offers.closest`) |
| `Reply.prompts` | field mechanics, `technique` only on the offer's Try it, `library` only on a library button, two or three at most | when buttons appear, user voice labels (`response_format.buttons`) |
| `Reply.state` | unchanged, including its REQUIRED emphasis | nothing |
| `TechniqueState.step` | the stage id from `framework_stages` | "must follow order, cannot skip" (`in_a_framework.one_stage_per_reply`) |
| `TechniqueState.accepted` | the full fill rule (true, false, null), its only home | nothing; `ctx.offer_waiting` and `ctx.this_thread` drop their copies |
| `Reply.crisis`, `Reply.title`, `Reply.text`, `Extraction` and memory models | unchanged | |

**Dependencies on other layers** (the rewrite must keep these names, which the prompts point at):
- "Framework Index" and its "Finding the fit" line are generated by `composer.py:117`, not written in these files. `questions.reach_for_the_fit`, `offers.clear` and `reasoning.steps.style_and_heading` refer to them. Feature 4 may rename them, and then these references move with it.
- `stage_ready_when`, `next_stage_ask` and the other stage fields are named inside `stage_note` by `context.py`.

**Value sourcing**:

| Action | Value | Source |
|---|---|---|
| Guard test | the word count | `parse_prompt(path)["content"]` from `scripts/seed.py`, split on whitespace |
| Guard test | duplicate keys | a `yaml.SafeLoader` subclass whose mapping constructor raises on a repeated key |
| Guard test | the allowed shapes | `mani.llm.schema.SHAPES` |
| Guard test | must say markers, removed keys, banned phrases | the strings in AC-3 and AC-4, held in the test, matched as whole words ignoring case |
| Guard test | where markers are allowed | the two key paths named in AC-3 |
| Ratchet | the new limit | `ceil(words / 50) * 50`, printed by the guard test's failure message |
| Verify | the `ctx` keys sent | the `ctx` key list above, compared by reading `context.py` |
| Replay | the conversation | `journey_abcde` in `backend/scripts/eval_conversations.yaml` |
| Replay | the three styles | `eval_replies.py` already runs each scenario in every style |
| Replay | the pass signal | the `after framework` and `repeated opener` findings from `tests/evals/validators.py`, printed by the run, plus muhammad's reading |

**Key invariants**:
- `reply_shapes` keys equal `SHAPES`, and `Reply` field order is unchanged (`reasoning`, `style`, `heading_toward`, `offer_fit` before `text`).
- The two clarification lines in the prompt match `CLARIFICATION_QUESTIONS` exactly. The after framework questions are not in the prompt: `ctx.after_framework_question` tells the model to ask the one the code supplies from `AFTER_FRAMEWORK_QUESTIONS`, word for word.
- No change to frontmatter (`id`, `model_id`, `model_parameters`). Thinking level belongs to features 2 and 11.
- No change to `context.py`, `repairs.py`, `redraft.py` or the framework files. Those belong to features 4, 5, 7, 8 and 9.
- An example containing `: ` or starting with a quote is quoted in YAML, so `safe_load` reads it as text.
- No rule is named `yes`, `no`, `on` or `off`, which YAML reads as booleans.

**Security model**: no change to who can read or write anything. The content is health related: `staying_yourself` (prompt injection and never reveal) and the safety lines keep their meaning (AC-8).

**Configuration required**: none. Run `python scripts/seed.py` after the edit; the app picks it up when its prompt cache expires or the server restarts.

**Critical test scenarios**:
- The guard test fails on today's `bc1df3d` files (3,436 words, lists, `consent_lines` present) and passes after the rewrite, verifies **AC-1**, **AC-2**, **AC-3**, **AC-4**.
- The guard test fails when the total is over `WORD_BUDGET` and when it is 50 or more under, and its message names the limit to use, verifies **AC-1**.
- `test_every_style_value_the_schema_allows_is_taught` still passes, verifies **AC-2**.
- `journey_abcde` in Direct, Supportive and Reflective reaches its ending with no `after framework` and no `repeated opener` finding, verifies **AC-10**.

## Build plan

Tracer Bullet: the thread is the two files and the guard, then the one ABCDE journey through the real model. Nothing else in the turn changes.

0. Before you start, pull `origin/main` so the work starts from `bc1df3d` (this branch is 4 commits behind and still holds the older prose files).
1. Add `backend/tests/unit/test_prompt_budget.py`. It checks:
   - the YAML structure, with no lists and no duplicate keys;
   - the word total in the band `WORD_BUDGET - 50 < total <= WORD_BUDGET`, 2,800 to start, with a failure message that prints the total and the limit to use;
   - must say markers only in the two allowed keys;
   - the removed keys and the banned phrases.

   Confirm it fails on today's files. Satisfies **AC-1**, **AC-2**, **AC-3**, **AC-4**.
2. Rewrite `response_format.md` to its home map rows:
   - `ctx` per the key list, with triggered behaviour on its key and the safety resume clause added;
   - `reasoning.steps` as 5 named steps;
   - `reply`, `buttons` and `library` as mappings.

   Satisfies **AC-3**, **AC-5**, **AC-6**, **AC-7**, **AC-8**.
3. Rewrite `mani_base.md` to its home map rows:
   - named rules throughout;
   - consent lines as examples inside each style;
   - `any_stage` removed per the fixed lines table;
   - no word lists;
   - nothing a `ctx` entry already holds;
   - the garbled `never_when` sentence fixed.

   Satisfies **AC-1**, **AC-2**, **AC-3**, **AC-4**, **AC-5**, **AC-8**.
4. Edit the `schema.py` descriptions per the schema table. Satisfies **AC-5**, **AC-7**, **AC-8**.
5. Delete `test_presence_may_be_said_in_any_style_while_openers_still_vary` and `test_staying_on_a_stage_is_not_told_to_repeat_the_same_wording` from `test_negative_set.py`. Then run the whole `pytest` against the local database and check the integration count. Satisfies **AC-9**.
6. Run `python scripts/seed.py`. In `backend/PORT-STATUS.md`:
   - add one line under "Decisions in force": "The base prompt is 2,800 words or fewer across `mani_base` and `response_format`, a limit the guard test keeps within 50 words of the files, so it follows them down and a rise needs `/architect`, each rule has one named home, and the client's fixed lines are examples, except the clarification and after framework lines the code matches exactly";
   - update the status line that gives the 4,850 token figure.

   Satisfies **AC-1**, **AC-5**.
7. Ask muhammad for the replay, with its size (3 conversations, 16 turns each) and the `get-credits` balance. On yes, run `--scenario journey_abcde --verbose` once, and give him the transcripts and the findings to judge. Satisfies **AC-10**.
8. If the guard test was built as a ceiling only, change its word total check to the band in step 1, and make its failure message print the total and `ceil(total / 50) * 50`. Satisfies **AC-1**.

## Consequences

**Positive**:
- Every turn sends about 19% fewer base words (3,436 to 2,797), and the cached prefix gets shorter. The guard keeps that from growing back.
- A rule changes in one named place, and the guard test stops the files growing back without anyone noticing.
- Features 4, 5, 8 and 9 inherit clean homes: framework rules in `in_a_framework`, key triggered rules on their `ctx` entries, fill rules in the schema, and the code matched lines named in one spot.

**Negative / tradeoffs**:
- The consent lines and stage replies are no longer guaranteed word for word. A reply may phrase them differently from the client's document.
- Rules added after real bad replies are now shorter or gone, and the word lists are gone. Until feature 5 removes `repairs.py`, the code still checks feeling words, so the reply side is not yet free of them.
- Two prompt text tests are deleted. Nothing now notices if the "presence in any style" or "staying is not repeating" rule is dropped, except review and the replay.
- One run per style is a smoke check, not a measurement. Your journal says one run is noise. The before and after numbers wait for feature 1, measured by reseeding `bc1df3d`.
- The scope's "no word for word line" bar is met only partly: five lines stay exact until feature 9.
- 2,000 is out of reach for now. The removals features 4 and 5 own are about 130 words, so the size stays well above 2,000 unless a behaviour decision drops more.
- Any change that takes 50 or more words out turns the guard red until `WORD_BUDGET` is updated, and a feature that adds rules has no slack, so it plans a raise through `/architect`.

**Neutral**:
- `repairs.py`'s `_OFFER_WORDS` matches "one step at a time"; the consent line comes after an offer, not in it, so rewording does not change what it detects. Feature 5 removes it.
- Rollback is a revert of one commit plus `python scripts/seed.py`. There is no data migration.

## Follow-up

- [ ] Measure `bc1df3d` against this version with feature 1's `--baseline` once it exists (three runs before, three after), and record the numbers in `backend/PORT-STATUS.md`, "Latest measurements".
- [x] Feature 4 (`0005-framework-in-8-lines`): its step 8 edits prompt lines and can add words. Note there that the net change stays within the 3 words of headroom or asks `/architect` for a raise. Done: AC-15 and build step 8 of that spec.
- [ ] Features 7 and 10: plan a raise of `WORD_BUDGET` through `/architect` if they add prompt text.
- [ ] `backend/PORT-STATUS.md`, "Decisions in force": the line says the limit is lowered as features 4 and 5 remove entries. Reword it to the band rule (`/develop`).
- [ ] Feature 11: decide from measured runs whether more behaviour can go, which is the only route toward 2,000.
- [ ] Feature 9: when the clarification and after framework lines move out of Python, drop the word for word exception in `ctx`, along with the code that matches them.
- [ ] Scope open question: confirm the client is fine with their consent and stage lines becoming examples. Your standing permission covers rewording, but this changes required lines into examples.
- [ ] Feature 10: remove the pain rule's duplicate from the `Reply.crisis` description when crisis moves to the model.
