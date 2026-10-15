---
type: journal
date: 2026-10-14
tags: [journal, abcde, frameworks, decisions, reversal]
---

# ABCDE names each stage and confirms what it already knows (2026-10-14)

muhammad reversed two 2026-10-09 decisions: "the chat never names a stage" and "a stage their words already
answer is skipped, with no check and no mention". What he asked for, from the client's own ABCDE document
(`~/Downloads/ABCDE Framework.docx`): the offer lists the five stages, and after Try it every stage message starts
with its label ("A is for Activating Event."), so the person knows they are following a framework. A stage Mani
already understands is stated as a possibility and checked, in a general line that varies, one stage per turn.

## Why the 2026-10-09 removal was not a reason against this

[[stages-are-skipped-not-confirmed-2026-10-09]] removed the labels after a manual chat in which two taps on a
"Not sure" button skipped C and D and E arrived three replies after Try it. The cause was the button, which no one
asked for and which is gone, not the naming. Stage advancement (`validate_transition`, `clamp`, `may_skip`, the
two-ask limit) is unchanged, so the failure mode cannot return through this change.

## What it is, and where

- `abcde.md`: `label` per stage, `stages.offering.stage_list`, `confirm` patterns for A, B and C per style, and
  `stages.offering.check`, about four equivalent closing lines per style. The model keeps the words and fills the
  angle brackets, as it does for offers.
- `repairs.with_stage_label` puts the consent line and then the stage's label ahead of its question the first time
  the stage is asked (tapped or typed yes alike), and not on a re-ask or when the model already wrote it.
- `repairs._compose_offer` adds the stage list after the permission question, except on the Tell me more re-offer.
- `context._WALK_THE_STAGES`, `mani_base.md` `in_a_framework` and `response_format.md` were rewritten from "skip
  without a word" to "confirm, then go on". `known` now means they confirmed it.
- `greeting.CONSENT_LINES` holds the three consent lines the prompt also carries; a test keeps them equal.

## Seen live, and not yet fixed

Direct, one run: the offer listed the stages; Try it gave the consent line then "A is for Activating Event. From
what you've shared, … seems to be what started these concerns. Did I get that right?"; B and C followed with their
labels and different check lines. In an earlier run C was asked as if unknown although the person had said it was
wearing them down: the model does not always use the read for a stage. That is the model's judgement and is not
checked in code.

The provider was slow all day: p50 8.4 s, p95 70 s against 6.4 and 10 s the day before, with the same token counts,
so it was not the prompts. Live testing needed `LLM_TIMEOUT_SECONDS` raised for the test process.

Open: muhammad will supply per-step details for Tell me more; they go in `stages.offering.explain`.
