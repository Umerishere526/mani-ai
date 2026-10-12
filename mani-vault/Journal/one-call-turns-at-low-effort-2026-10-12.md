---
type: journal
date: 2026-10-12
tags: [journal, latency, redraft, effort, design, lessons]
---

# A turn is one call at low effort (2026-10-12)

The client's urgency letter lists "excessive latency" (R2 in `docs/client/requirements.md`).
Target set by muhammad: a median turn of 4 s, the slowest 10 s.

## Root cause

Not a slow line. The design made every missed rule cost a full model call. A turn asked a
reasoning model at effort `high` for a reply, judged the reply in code (`redraft.py`), and when it
failed a check asked again, up to twice more. The reply already carries its own written
`reasoning` field before `text`, so the hidden thinking at `high` was a second pass over work the
schema already forces. Measured on 2026-10-07: median 12.6 s, slowest 41 s, about 7% of replies
redrafted. [[prompt-restructure-2026-10-07]] had already named it: "Effort is the latency
lever, not the prompt size."

## What changed

- `mani_base` and the exercise pick that follows a framework run at `low`. The pick used to fall
  back to the config default (`high`), which a change to the chat row alone would have missed
  (architecture reviewer).
- The redraft loop is gone. Each reason it had became one of three things:
  - **shaped away.** While no offer may be made, the reply shape has no `technique` on a button
    (`schema.ReplyWithoutOffer`), so the model cannot offer early and the reply keeps the
    question it was asked to end on. A button strip alone would have deleted the offer sentence
    and left the reply with no question.
  - **set in code.** `state.step` is written after the text, so where it disagrees with the
    reply's own `stages_known` the step is the wrong label; `reply_checks.with_ledger_step`
    sets it.
  - **counted.** A repeated question, no question, an offer due and not made: logged, and in
    `Turn.checks`, printed by `scenario_check`. These guarded R3, R5 and R8, so losing them is a
    real risk that is not measured yet.
- `repairs.py` stays: it costs no call.

## Not measured

No live run has been made (it spends the client's credit; muhammad's yes is owed). The first
run to read: `scenario_check.py` three times, for the median and slowest turn, the calls per
turn, the thinking tokens, and how often each check is missed. If the misses are common, the
fix is to cut and clarify prompt rules ([[prompt-changes-cut-not-add]] in memory), not to bring
the loop back.

## Streaming

Not reopened. The reply is structured JSON with `text` last, and code rewrites `text` after the
model finishes (the offer, the check-in, the body route), so streamed words would be taken back.
The decision "no streaming" rested on "while turns stay short", which no longer holds; revisit it
after the next measured run.

## Found, not fixed

- `AI_DEBUG_MODE` adds a prompt layer asking for longer reasoning, and the chat-tester sidebar
  needs it on, so the client's own testing pays for longer turns than a real user.
- The voice translation runs even when the text is already English, at the config default effort.
- The summary task holds a pool connection for its whole model call.

Related: [[offer-window-owned-by-code-2026-10-12]], [[stages-are-skipped-not-confirmed-2026-10-09]],
[[measure-before-tuning-prompts]].
