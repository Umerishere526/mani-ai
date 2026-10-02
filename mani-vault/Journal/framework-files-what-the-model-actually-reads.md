---
type: journal
date: 2026-10-01
tags: [journal, frameworks, router, lessons]
---

# Framework files: what the model actually reads

Lessons from reviewing ABCDE, Thought Reframe and ACT Choice Point against the client's
specification, 2026-10-01. Follows [[framework-endings-and-ignored-offers]] and
[[measure-before-tuning-prompts]]. Stack facts stay in `.claude/BACKEND.md`.

## Only some of a framework file reaches the model

- Read by code: `central_indication` (framework index), `distinctions` ("Telling them apart"),
  `contraindications` ("Never offer one when"), `strong_signals` and `signals` (the router), and
  each stage's `purpose`, `listen_for`, `ready_when`, `boundaries`, `if_unclear` and `ask`.
- Read by nothing: `appropriate_when`, `not_when`, and the markdown body below the frontmatter.
  A safety rule written only there enforces nothing, which is how the abuse and danger guard
  went missing from ABCDE and Thought Reframe. Put it in `contraindications`.
- `redirects` was read by nothing until `test_router.py` made it the check that each "may fit
  another framework" example routes to the framework it names.

## The specification's tone lines are not always a stage's own question

In the ACT section 15 the line labelled "Stage N" is the reply after an answer in stage N, and
it asks stage N+1's question. Copying it into stage N's `ask` made every stage ask the next
one's question, so "what is showing up" and "what is one action" were never asked. A stage's
`ask` is that stage's own primary question (section 12). Check which a line is before copying.

## Both specifications claim the same patterns

An unanswered message, an exclusion and a mistake are patterns of both ABCDE and Thought
Reframe. Widening ABCDE's event words stole Thought Reframe's own worked example. The only
real separator is whether the person asks to understand why it affected them, so that is the
ABCDE rule now. Run the other framework's examples through the router before widening a rule.

## A discriminator rule that adds a candidate must be opt in

Letting any fired rule put its framework on the shortlist made "I cannot begin to tell you how
good the trip was" suggest Behavioral Activation. `Rule.standalone` is off by default; only
rules whose phrase is specific on its own (ACT's "cannot control", the "want to understand
why" cue) set it. A standalone candidate scores the floor, below the confidence bar.

## Run the whole suite, not only tests/unit

`tests/evals/test_negative_set.py` rejects any stage `ask` that names someone, carries an
author note, or hands over a feeling word. The specifications' tone lines are scenario text
("your manager", "embarrassed", "her silence"), so copying them verbatim into ABCDE and Thought
Reframe broke 14 of those asks, and only `pytest tests` showed it. Where a tone line has a
scenario free question half, keep that half; otherwise use the stage's primary question.

## The database holds the last seed

Integration tests read frameworks from `admin.frameworks`, not from the markdown. After editing
a framework file or `somatic.md`, run `python scripts/seed.py` before trusting them. The running
local Supabase is on 54321/54322, which disagrees with `config.toml` and BACKEND.md (54341/54342).

## Steering the questions toward a framework (2026-10-01)

The base prompt told Mani, twice, that a question "is not how you steer", and `reasoning` said
to offer only when the router sent a `framework_shortlist`. The router is keyword scoring, so
grief, a loop of thoughts or anything phrased unusually got an empty shortlist and no offer.
Now every question follows the feeling and also reaches for the next item on the best fit
framework's `to_find_out` list (shown in the Framework Index under "Finding the fit"), the model
commits to a lean in `heading_toward` before it writes the text, and with nothing fitting well
it offers the closest with Keep chatting beside it. The client's cadence in code is unchanged
(first offer after 2 of their messages in Direct, 4 in the others).

Measured with `scripts/eval_replies.py`, three runs of three scenarios, every style, valid runs
only. Offers made / style-runs, and the message the Direct one arrived at:

| Scenario | Before | After |
|---|---|---|
| grief_dog_steering | 1 of 9 (Direct at 5) | 6 of 9 (Direct at 2, 2, 3) |
| deadlines_steering | 3 of 6 (Direct at 3) | 9 of 9 (Direct at 3) |
| withdrawal_behavioral_activation | 6 of 6 (Direct at 4) | 7 of 9 (Direct at 2, 2, 3) |

Findings per run were level (8.6 before, 8.4 after); "stalled" fell, "added scale" and
"labelling" rose a little. Reflective is the style that still offers least.

Things to remember:
- A new output field must be read by something. `heading_toward` is logged as an id only
  (`thread X heading toward Y`) and read by evals; `clinical_note` was removed for being unread.
- The model sometimes writes a word ("decline", "Keep chatting") in a boolean field. That failed
  the whole turn (2 of 9 baseline runs, 5 of 9 after the steering change, since offers are where
  it happens). `SmartPrompt.decline` now reads a word as true.
- Run the baseline before editing anything that is imported by the eval: a schema change made
  while the baseline ran would have leaked into it. Prompts live in the database, so they only
  change at the next seed.
- Behavioral Activation was offered in 1 of 9 grief style-runs although its "Never offer one
  when" line names early grief. Prose did not hold it.

## Feeling words: a check that only logs enforces nothing (2026-10-01)

"That sounds incredibly stressful" reached a person who never said stressed. The code check for
feeling words they had not used only wrote a log note, and the word list was a fixed 60 with
"stressed" but not "stressful". Now: a draft that names an unsaid feeling is redrafted once
with the words listed in `[ctx]`; a second miss has the offending sentence dropped when a
question survives (`repairs.without_feeling_sentences`). Their own word and its plain forms
(lonely, loneliness) are theirs; a different feeling is not. Measured on the same rule: 6.4% of
replies named an unsaid feeling before (28 of 440), 0 of 130 after, with a redraft on 4.6%.
The base prompt no longer lets Mani offer an unnamed feeling as a question. A turn is now one
model call, or two when a draft needs redrafting (ADR-002's one call per turn bends here).

Things to remember:
- A reply check that only records a note is not a guard. Say so in the comment, or make it act.
- "Exact word only" was too strict: "the loneliness" after "lonely" is theirs. Compare stems.
- Raising the word list changes other tests' data (a button labelled "Still tense" is now dropped).

## Offers: the context block said yes while the code said no (2026-10-01)

For a first offer `[ctx]` hardcoded `cooldown_passed: yes`, and `repairs.apply` then dropped the
offer when the style's count had not passed. The model was told it could, and was overruled: 58% of
Supportive and 33% of Reflective first offers, leaving replies with no question. Fix the truth in
the block before adding a rule to the prompt. Offers now follow Mani's own confidence
(`Reply.offer_fit`, a clear offer from the second message in any style), the closest fit is owed
by the fourth ("Try the closest fit" beside Keep chatting), and a repeat offer after the person typed
past one is redrafted. ADR-007. Measured: 36 of 36 conversations offered; grief went from 1 of 9 to
all of them. Also: my first default treated an empty `offer_fit` as closest and relabelled normal
offers, which broke taps on the old label, so empty means clear.

## Still open

- `test_account_lifecycle` fails: the signup response has no `id` (the auth container, not the
  framework work). Not checked on a clean checkout.
- `appropriate_when` and `not_when` are read by nothing; each framework file says so.
- A tie between two frameworks sorts alphabetically, so ABCDE lists before Thought Reframe.
- "cannot stop thinking" puts ACT on the shortlist for thoughts evidence could examine; it is
  never confident alone (pinned by a test). Watch it in real conversations.
- `safety.PROTOCOLS` and `CLARIFICATION` are empty: the approved safety wording does not exist.
