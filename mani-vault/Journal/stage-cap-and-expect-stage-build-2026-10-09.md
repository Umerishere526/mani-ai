---
type: journal
date: 2026-10-09
tags: [journal, frameworks, stages, ledger, evals]
---

# Spec 0010 tasks 3 to 5: the cap at 3, and expect_stage

## What landed

- `stage_turn_cap: 3` in `content/prompts/tuning.md`, with the comment that the stage is asked once more than the cap. Reseeded. The cap integration test now sends `stage_turn_cap` turns and checks the stage is still held one turn before, rather than sending a fixed four.
- `expect_stage` in `scripts/eval_replies.py`: a turn may be `{say: <line>, expect_stage: <phase>}`. Eleven `stages_*` scenarios in `eval_conversations.yaml`: the ABCDE example by tap and by typed yes, a vague meaning, out of order, one side of D, a stall, and one per other framework with its first two stages told before the offer.

## Gotchas

- An `@accept` line sends nothing once the offer was taken, so it has no `Exchange`. `expect_stage` on such a line is checked against the phase after the last line that was sent, which lets one expectation sit on the last `@accept` of a group whichever one took the offer.
- `tests/evals/test_style_findings.py` calls `_score` with a scenario dict that has no `turns`. Anything new in `_score` reads the scenario with `.get`, as `markers` and `heard` already do.
- The offer may name a different framework than the scenario was written for (ABCDE is offered over Thought Reframe whenever both fit), so a stage finding names the stored framework too.

## First real run (muhammad's yes, the six ABCDE ones, Supportive)

Passed: told before the offer (tap and typed yes both land on `dispute`), out of order, stall. Failed:

- One side of D stored `consequences`: the model did not count "I stayed in all weekend and felt awful about it" as C, probably because the person never tied it to the thought, and asked C three more times. Either the line should tie it, or this is the judgement the spec's tradeoffs warn about.
- Vague meaning never got an offer: ABCDE's Starts when needs the meaning first, so a vague meaning cannot reach the accepting turn. AC-13's second bullet conflicts with the content. Settled by `/architect` the same day: the case runs inside a running ABCDE, started on `activating_event`. The general rule: whatever a framework's Starts when needs is always known on the accepting turn, so a partial stage before the offer can only be a later one.
- Any message typed while an offer is open declines it, so `@accept` fallbacks after an early offer go through decline and ask again. The scenarios still read, but the path is not the one written.
- Every offer turn logged "dropped a stage report: not a stage of the framework". Worth a look at which id the model sends there.

Rerun after the third amendment: both pass. Vague meaning, started on `activating_event`, held `belief`. One side of D, once the C line said "Because of that thought", landed on `dispute` and asked only the missing side. So the first failure was the script, not the model: an effect the person never tied to the thought reads as not clear.

Without `--style` every scenario plays in all three styles, three times the cost.

Related: [[stage-last-try-never-shipped-2026-10-09]], [[stage-skip-and-short-questions-scope-2026-10-09]], [[stage-ledger-design-2026-10-08]]
