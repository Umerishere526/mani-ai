---
type: journal
date: 2026-10-07
tags: [journal, prompts, frameworks, decisions]
---

# Prompt restructure: what muhammad decided (2026-10-07)

The goal: shorter prompts so the model has room to write, a Mani that holds the chosen style
(Direct, Supportive, Reflective), therapeutic but a warm companion, neutral, never labelling and
never advising unasked, and questions that move the conversation. "Just enough that the chat makes
sense in asking questions" - not a rebuild.

Measured before starting: about 15,000 tokens of static prompt on every reply call (`mani_base`
8,100, the generated Framework Index 3,000, `response_format` 2,500, the Reply schema 1,500).

## Decided

- **Format:** `mani_base.md` and `response_format.md` are written as YAML keys and arrays, not
  prose, and sent to the model as written. No new parser: `seed.py` stores the body as text.
- **Persona:** the model brings "the judgment of a therapist with forty years of listening to
  people", and never says so, never calls it therapy, never sounds clinical. The client spec
  forbids the word to the person.
- **Advice:** questions only, with three exceptions kept and scoped - options when they say they
  cannot decide, one small step when they ask Mani to pick, and the protective step on a
  time-critical risk.
- **Framework rules:** each framework file carries its own 7-8 `agent_rules` (trigger, skip,
  start, move, stay, end, stop), sent only for the framework on offer or running. The base
  prompt holds only what is common to all of them.
- **Choosing a framework:** the model chooses among the six by meaning, in the same reply call.
  The keyword router stays a hint and the code gates stay. This is the opposite of the reverted
  embedding router, where code decided and the model was not asked.
- **Dialogue inside a framework:** no schema change. `[ctx]` carries progress and the issue in
  their words. Counting turns per stage and keeping facts from the offer turn were the reverted
  migrations 012 and 017, and are not coming back without a new decision.
- **Synonyms:** everyday phrasings added to the router's signals, from the client spec's own
  example lines, each checked so no framework takes another's examples.

## How the work is held to account

- Every line in a rewritten prompt traces to the client spec, an ADR or journal decision, or a
  line already in the prompt. A rule with no source does not go in.
- Strings the code matches by text (somatic `when` lines, practice texts, the client's fixed
  questions, offer and permission patterns) are not reworded.
- Measured three runs before and three after with `scripts/eval_replies.py`; a shorter prompt that
  makes a number worse gets the rule back. See [[measure-before-tuning-prompts]].
- Prod is reseeded only on muhammad's approval.

## Phase 0, done

The voice translation in `mani/stt.py` sent no provider order, no `data_collection: deny` and no
reasoning effort, and was served by OpenAI. It now uses `chain.request_body` like every other call
and is served by Azure. A test fails if a prompt on a reasoning model leaves out `reasoning_effort`.

## Phase 2 draft: where each section of `mani_base.md` comes from

Sources: **P** = the prompt before this change (`mani_base.md` at `2b426f6`), **S-styles** =
`backend/docs/specs/conversational-styles.md`, **S-six** = `backend/docs/specs/six-frameworks-overview.md`,
**D** = muhammad's decisions above, **J** = a journal note or ADR.

| Section | Source |
|---|---|
| `identity` | P "Who you are" (warm companion, calm, unhurried, kind, never scripted, never clinical, the five forbidden words, "never assume which"); D persona; muhammad's "neutral, non judgement" |
| `goal` | P "Your goal"; J [[what-every-conversation-is-for]] (the one path) |
| `rules` 1-2 | P "Naming a feeling" and "What never happens"; S-six "never introduces a feeling word". The size list keeps only the phrases code does **not** enforce: `repairs.FEELING_WORDS` already redrafts heavy, overwhelming, exhausting, stressful |
| `rules` 3 | S-styles "Universal rule: do not label" |
| `rules` 4-6 | S-six "Rules common to every framework" |
| `rules` 7 | D advice |
| `rules` 8-9 | P "What never happens" |
| `moves` | P "How you respond", shortened; the presence line keeps muhammad's 2026-09-24 wording, pinned by a test |
| `reply_shapes` | P "Shapes a reply can take"; must equal `schema.SHAPES`, pinned by a test |
| `styles.all` | S-styles "Style continuity" and "Do not create repetitive language patterns" (its three stock phrases) |
| `styles.*` | S-styles "Direct leads. Supportive accompanies. Reflective mirrors and explores." and "Within the framework, by style"; P "The three styles" |
| `questions` | P "The question you ask"; J [[framework-files-what-the-model-actually-reads]] (steering toward Finding the fit, measured); "plain everyday words" is muhammad's ask |
| `flow` | S-styles "Complete conversation cadence" and "Framework entry" (two to four, a range not a count); P "How a conversation moves" |
| `offers` | P "Offering the questions" and step 3; ADR-007 (clear and closest); `repairs._compose_offer` (description and permission question added by code) |
| `consent_lines` | S-styles "The key difference" table, verbatim |
| `in_a_framework` | P "Going through the questions"; S-six "The cadence, at every stage"; ADR-011 (pick one as a draft); D advice exceptions |
| `any_stage` | S-six "Universal any stage handling", the client's lines verbatim; P table |
| `ending` | P "Ending gently"; S-six "Completion, somatic, and the hand-off" |
| `staying_yourself` | P "Staying yourself" |

**Removed, with no replacement:** the three example conversations, the "thought questions"
illustration, the quoted generic check-in, and the instruction for Reflective to name a sensed
feeling as a question. That instruction contradicted P's own "not as a guess, not as a question",
S-styles ("does not introduce ... emotions ... the user has not expressed"), and the redraft that
code makes when a feeling is named, so Reflective was being sent back to undo its own instruction.

**Moved to Phase 3** (`response_format.md`): how to read `their_last`, `clarification_available`,
`offer_waiting` and the other `[ctx]` signals.

## Phase 3: `response_format.md`

| Section | Source |
|---|---|
| `ctx` | P `response_format.md` "What each line tells you", one entry per key that `context.py` emits, checked against the code |
| `their_last` | P `mani_base.md` "When their reply says little, or says you missed something", without its example question |
| `reasoning` | P "Before you write: the reasoning field", nine steps folded into eight |
| `reply` | P "Rules for every reply"; muhammad's "human like language, no complex words" as the first line |
| `buttons`, `library` | P "Buttons" and "The Library", without the example Library description |

## The output budget (found by the baseline, 2026-10-07)

At effort high, a chat turn thought for 1,955 of its 2,048 output tokens and the reply was cut off: 4 of the first 61
calls failed, and the eval crashed on the first. On a reasoning model the output budget covers the thinking and the
reply together, and every caller sized it for the reply alone (the exercise pick had 200). `chain.sampling` now adds
`REASONING_ALLOWANCE_TOKENS` (8,192) on top for reasoning models. Average successful turn at high: 12.6 s, longest
41 s. Effort is the latency lever, not the prompt size.
