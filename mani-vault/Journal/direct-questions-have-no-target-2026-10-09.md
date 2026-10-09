---
type: journal
date: 2026-10-09
tags: [journal, prompts, questions, direct, lessons]
---

# Direct questions have no target (2026-10-09)

muhammad's Direct chat (manager criticised them in front of the office, insulted them, threatened
to fire them; their real worry, said at message 5, was colleagues laughing at them). Mani asked
for what they had already told it ("What did your manager say?", "Had he threatened to fire you
before?" right after "this time it was way too much") and chased the event ("What happened after
he said it?"). Nearly every reply opened by restating them.

## Evidence

Replayed each turn live with the real history forced (turns before k return the recorded
replies, turn k calls the model with `AI_DEBUG_MODE=true` so `reasoning` comes back), three runs
each. The model's own reasoning cites the `[ctx]` steer: "Direct style calls for one concrete
question; whether this has happened before would clarify the situation." The `question_focus`
meaning for Direct is a fixed list (what happened, whether it has happened before, what they have
tried), sent every turn, beside their message, with nothing about what is already known. It
outranks every "never ask for what they already made clear" line in `mani_base`.

"Most replies are one plain line and a pointed question" is read as "Direct style calls for a
brief reflection and a pointed question": that is the restating on every reply.

## What did not work (12 questions per variant)

| Variant | Redundant or event-chasing | Generic ("what's on your mind") |
|---|---|---|
| Original checklist | 9 | 0 |
| "about what is bothering them, never the event" | 1 | 8 |
| "what is happening for them, never more detail, never general" | 6 | 3 |
| Same, plus "list what they told you in reasoning, then the one unknown" | 4 | 3 |

The list did get written (the mechanism works), but the chosen unknown was still generic or
the event. Rewording swings between two failures: a checklist the model executes, or no target
and it falls back on a check-in. **The questions before an offer have no defined target**, since
they may not aim at a set (decision of 2026-10-08), and "their concern is clear" is defined
nowhere. All edits were reverted; raised with muhammad as a design question. The planned
ABCDE-only reduction would give the target for free (what happened, what they made of it), so it
bears on when to do this.

## Decided and tried, same day

muhammad chose to define the target: what happened, what about it hurts or worries them now,
whether they want to feel better or act. It lives in the `understanding` meaning in `[ctx]`, and
Direct's checklist and "one plain line and a pointed question" are gone. Replays (12 questions):
re-asking or event-chasing 9 to 0, restating 8 to 2. `scenario_check.py`, all scenarios, before and
after: Direct replies opening on their words 5/22 to 1/23, but "two styles ask the same question"
6 to 16, because the targets are shared by all three styles. The third target became its own
template ("Would you rather talk through X or work out Y?"), asked twice in one conversation even
with "only once" in the line, and the model holds the offer until it is answered.

## Fixed: scenario_check hang

`scripts/scenario_check.py` gathers every scenario-and-style conversation at once: 4 scenarios x 3
styles = 12 concurrent turns against `MAX_POOL_SIZE = 10`. Each turn holds a pool connection while
`client.complete` records its cost row on another, so it should deadlock with no error. Not run
against `scenario_check.py` itself; seen with the same pattern in a replay script (12 at once, no
`llm_calls` row for ten minutes; 4 at a time ran fine). Now bounded by `AT_ONCE = 4`; all 15
conversations ran.

See [[measure-before-tuning-prompts]], [[prompt-restructure-2026-10-07]].
