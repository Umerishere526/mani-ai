---
type: journal
date: 2026-10-09
tags: [journal, prompts, ending, ledger, debug]
---

# Body check started with no offer (thread 18757742)

muhammad saw Mani open with "If you're willing, press your feet into the floor": the offer and the first step came in one reply. He thought the flow had changed. It had not. The `ending` wording had been the same since `dd0e577` (2026-10-08).

## What the rows showed

- `admin.llm_calls.stage` per turn and `thread_technique_state.stage_ledger` tell the whole story with no model call. Read them first.
- E reached `stage_turn_cap`, so the code moved the stage to `closing`. The reply on that turn was written while `[ctx]` still said E, so it was the E draft ("Does that feel believable?"). The answer to that draft arrived on `closing`. This is the cost spec 0010 accepted ("counts as the next stage's first turn"), but for the last ledger stage the next stage is the ending.
- Thread f8449c64 had the same cap and the same draft, but there the "yes" arrived while the stage was still E. Mani asked how it sits, then made a proper offer. So the cap changes which turn the ending starts on, and the wording "offer a short body check" let the model merge the offer into step one.
- `dispute` leaving `reported_stages` was not a bug. Once it was `passed`, the model stopped reporting it, and the stored ledger kept it.

## Fix

muhammad chose a reword, not new code: "offer a short body check" became "ask if they would like a short body check". One real run of `abcde_closing_asks_before_body_check` (Directive) asked how they feel first and gave no step. The scenario lines were then fixed to answer the feeling question, so a rerun would reach the offer. That rerun has not been done.

Lesson: when a scripted model cannot reproduce something the model chose, the evidence is the call rows plus a sibling thread that went right. Compare the two before you blame the code.

Related: [[stage-last-try-never-shipped-2026-10-09]], [[body-ending-design-2026-10-08]], [[stage-cap-and-expect-stage-build-2026-10-09]]
