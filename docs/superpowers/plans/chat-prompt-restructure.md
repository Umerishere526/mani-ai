# Plan: chat prompt restructure

Make the chat prompt files linear and single-owner, so that each rule lives in one place,
the file a rule lives in matches what the code does with it, and the model has room to write
rather than a wall of overlapping constraints.

**Spec:** `backend/docs/specs/conversational-styles.md` and `backend/docs/specs/six-frameworks-overview.md`
are the client's authority. `backend/PORT-STATUS.md` holds the decisions in force.

## Context

Four MD files reach a chat turn. Two are prompt layers (`mani_base`, `response_format`),
one is merged into every framework by `seed.py` (`somatic.md`), six are frameworks read one
stage at a time through `[ctx]`.

Measured section sizes before this plan:

| mani_base | chars | response_format | chars |
|---|---|---|---|
| identity | 545 | ctx | 4258 |
| goal | 207 | their_last | 964 |
| rules | 883 | reasoning | 1979 |
| moves | 518 | reply | 1110 |
| reply_shapes | 582 | buttons | 288 |
| styles | 2100 | library | 155 |
| questions | 922 | | |
| flow | 580 | | |
| offers | 1981 | | |
| consent_lines | 201 | | |
| in_a_framework | 1646 | | |
| any_stage | 773 | | |
| ending | 753 | | |
| staying_yourself | 619 | | |

## Global constraints

- **Do not merge the two prompt files.** `prompts/cache.py:24` requires both by name, and
  `composer.compose()` puts the generated Framework Index between them on purpose: identity,
  then what may be offered, then how to answer. Restructure within the files.
- **Do not delete `somatic.md`.** `seed.py` merges it into all six frameworks; the ending breaks
  without it.
- **Strings matched by code must not be reworded.** `consent_lines`, the `any_stage` lines, the
  somatic practice texts, `reply_shapes` (must equal `schema.SHAPES`), the Chat More / Go to
  Library labels, and every `[ctx]` key name.
- **No colons inside a YAML bullet.** One turned a bullet into a dict silently during this work.
  Every task verifies with `yaml.safe_load` that no bullet is a non-string.
- Each task: edit, parse-check, `pytest`, seed, confirm the database row matches the file.
- **Verification is by reading, not by eval.** The eval harness was deleted on muhammad's
  instruction. Each task states what to read to judge it.

## The single-owner rule

Every rule lands in exactly one place, decided by what varies:

| Kind of rule | Owner |
|---|---|
| True on every turn — who Mani is, how it talks, what a question must do | `mani_base` |
| Describes *this* turn's state — `[ctx]` keys, the reasoning order | `response_format` |
| Enforced by code regardless of what the prompt says | code; the prompt copy is removed unless it demonstrably prevents a redraft |
| One framework's own content | that framework file |

---

## Task 1: add `voice:` to mani_base, remove its duplicates from response_format

**Produces:** a `voice:` block in `mani_base`, after `styles`.
**Consumes:** the language lines currently in `response_format.reply`.

The language rules live in `response_format.reply` today, where the model reads them as output
formatting rather than as how Mani speaks. They belong beside `styles`. This task also adds the
three things muhammad asked for that exist nowhere: grammar, register, and what makes a question
answerable.

Steps:

1. Add `voice:` to `mani_base.md` after `styles`, carrying:
   - the language lines moved from `response_format.reply` (everyday words, one idea per
     sentence, no more words than the idea needs, read it back for stumbles, no dashes,
     phone layout)
   - grammar: full sentences, correct and unfussy; never sacrifice sense for brevity
   - register: match how they write. Someone writing in fragments and slang gets a reply that
     sounds like a person, not a form. Someone writing formally gets the same care without the
     looseness. Never perform their register back at them.
   - what makes a question answerable: it can be answered in a sentence, from what they already
     know, without making them summarise their life.
   - mirror length: a reflection is shorter than what it reflects, and earns the question that
     follows it. If it only delays the question, cut it.
2. Remove the moved lines from `response_format.reply`, leaving the turn-shape rules
   (one question at most and its exception, the framework-stage rule).
3. Parse-check both files; assert no bullet is a non-string.
4. `pytest` → expect 496 passed, 4 skipped.
5. Seed; confirm `admin.prompts` lengths match the files.
6. Commit.

**Expected:** `mani_base` grows ~800 chars, `response_format.reply` shrinks to 3-4 rules.

**To judge it:** open a chat in the tester, write one message in slang and one formally, and
read whether the two replies differ in register without either sounding performed.

---

## Task 2: collapse the stage-question rule to one owner

**Consumes:** Task 1's `voice:` block (the mirror rule interacts with it).

"Put the stage question in their words, never send it bare" reaches the model three times:
`mani_base.in_a_framework` bullet 1, and `context.py`'s `stage_note`, emitted every turn.
(The `response_format.reasoning` copy was already removed during this work.)

Steps:

1. Read `context.py`'s two `stage_note` strings (the `framework_starting` one and the ordinary
   one). They are nearest the message and cost nothing extra.
2. Trim `mani_base.in_a_framework` bullet 1 to what `stage_note` does **not** say: the rule
   about never bringing in a person, detail or feeling they did not give.
3. Parse-check, `pytest`, seed, commit.

**Expected:** `in_a_framework` loses ~150 chars; no rule is lost, one copy is.

**To judge it:** run a framework to its second stage and read whether the question is still
built from their words.

---

## Task 3: remove the prompt copies of rules code enforces absolutely

Three rules are enforced unconditionally in `repairs.py`, so the prompt copy buys nothing except
tokens — unless it prevents a redraft, which only the feeling rule does.

| Rule | Code | Action |
|---|---|---|
| name at most once | `repairs._without_their_name` | remove from `mani_base.rules` |
| clarification once | `repairs._without_clarification` | remove from `response_format.ctx.clarification_available` |
| no technique inside a running framework | `repairs.apply` | remove from `response_format.reply` |
| **never name a feeling they have not** | `repairs.introduced_feelings` + a redraft | **KEEP** — a redraft costs a whole model call |

Steps:

1. Remove the three rows marked remove. Keep the feeling rule.
2. Parse-check, `pytest`, seed, commit.

**Expected:** ~400 chars saved across the two files.

**Risk:** the model may now say someone's name twice; `repairs` strips the second either way,
so the person never sees it. If a reply reads oddly after stripping, this task is reverted.

**To judge it:** set a nickname on a profile, chat for six turns, read whether any reply reads
as if a word was removed.

---

## Task 4: make the four code overrides visible to the model

Code overrides the model at four points and the prompt says so at only one. A model that does not
know its text will be replaced writes the replaced part anyway, which is wasted output and, in the
offer case, wasted thinking.

| Override | Code | Does the prompt say so? |
|---|---|---|
| offer = model's part + framework summary + permission question | `repairs._compose_offer` | partly — fixed during this work |
| the somatic ending is sent verbatim | `orchestrator._body_route_step` | **no** |
| Chat More / Go to Library are attached by code | `orchestrator._handoff` | yes, in `ending` |
| phase order is corrected silently | `registry.clamp` | no, and it should not — it would invite drift |

Steps:

1. Add one line to `mani_base.ending`: once the body check-in is answered, the practice is sent
   as written for the place they named; write the reflection before it and nothing else.
2. Parse-check, `pytest`, seed, commit.

**Expected:** one line added. The model stops writing practice text that is discarded.

**To judge it:** complete a framework, read the last three replies.

---

## Task 5: documentation and decisions

Steps:

1. `backend/PORT-STATUS.md`: remove the eval harness from "What the service does"; remove or mark
   the "Latest measurements" section, which describes a harness that no longer exists; add a line
   under "Decisions in force" for the single-owner rule.
2. `backend/docs/specs/README.md` and `backend/docs/ai-layer-audit.md` reference `tests/evals/`;
   note that it was removed.
3. Journal note under `mani-vault/Journal/` recording the single-owner rule and the YAML colon
   trap.
4. Commit.

---

## Not in this plan — decisions for muhammad

These change behaviour or are the client's, so they are listed rather than executed.

1. **The Structured Problem Solving summary contains "overwhelming"**
   (`content/frameworks/structured_problem_solving.md:4`). `repairs._compose_offer` appends it
   verbatim, so every SPS offer names a feeling the person did not use — against the system's
   central rule. It is the client's wording.

2. **The content filter crashes a turn.** Azure returns a refusal, the retry hits the same
   provider, and the person's message is lost with "Mani had trouble responding". Options: ask
   Azure to relax the filter, retry on the fallback provider (reopens the data-protection
   question in PORT-STATUS), or accept and document.

3. **A schema field for style commitment.** The journal (2026-09-23) says prose rules did not
   differentiate the styles and schema field order did. If Task 1 and the styles rewrite do not
   show a difference, the next lever is a field declared before `text` that commits to a lead or
   a length.

4. **Fewer code overrides** — letting the model's own words survive to the person at the somatic
   ending or in the offer. Architectural, with safety implications.

## Review focus

- No reworded string that code matches by text.
- No YAML bullet turned into a dict by a colon.
- Nothing that weakens the safety screen, the crisis path, or the framework phase machine.
- The two prompt files still parse and still carry every `[ctx]` key `context.py` emits.
