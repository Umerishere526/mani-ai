---
type: journal
date: 2026-10-25
tags: [journal, prompts, understanding, feelings, pacing, lessons]
---

> Superseded 2026-10-26 (the three steps, their pacing by `found`, and the add-only problem, core issue and feeling) - see [[heart-of-it-replaces-the-three-steps-2026-10-26]].

# The core issue was defined as more situation (2026-10-25)

muhammad's research named two failures: Mani hears "I'm sad I can't provide for my family, I'm a failure" as *sad*
and asks about the situation, and a second feeling ("I'm frustrated") replaces the first. Lolly's 2026-10-18 sister
loans review says the same ("MANI chooses the transactional detail and bypasses the emotional disclosure"; R24).

## What was already built, and not the cause

The data was never lost: `feeling`, `stack`, `issue`, `core_issue` and `underlying_feeling` only grow and reach `[ctx]`
every turn. The research's other proposals were weighed and left out. An emotion classifier would be a second model;
CBT distortion labels go against R28 and our no-clinical rule; a "frustration is a shield" rule would explain people
to themselves. LangGraph would duplicate the orchestrator.

## Causes

- Our own words, not the client's, defined the core issue as consequences: "what happens because of the problem", "a
  feeling, such as not being enough, is not yet the core issue: ask what makes them feel it". That sends "I'm a
  failure" straight back to the situation. The problem step's "who, what, how often" did the same.
- Reasoning step 1 read only the last message, so the newest feeling became the whole subject of the reply.
- `understanding.merge` dropped a core issue or feeling said before the problem was stored (the AC-17 order gate), and
  `_gathered` dropped the oldest entry first, which is the feeling they came with.

## Change

The swaps were cut-for-cut: `mani_base.md` stayed at 9477 characters and `response_format.md` went from 2307 to 2286.
- The core issue is what the problem means to them (belief about themselves, a value, two things wanted at once).
- The problem is taken whole.
- Reasoning reads the message against what `[ctx]` holds.
- `stack` ties each feeling to what it is about.
- The repair line says what Mani missed instead of asking.

In code:
- Every step is stored when said (`_in_order` is gone).
- `_gathered` keeps the first entry.
- `found` paces the steps.

## The lesson: one gate did two jobs

The first build stored out of order with no pacing. In one Directive run the sister chat stored a guessed core issue
from her vague first line and the feeling from her second, then checked and offered ABCDE at message 2 with her family
value unexplored. That is Lolly's failure 8, only faster. The AC-17 gate on storage had also been the pacing. They are
now separate: storage takes everything, and `understanding.advance` counts one step a turn as found, in order. It
cannot stall, because a stored step counts on the next turn whatever that turn is about. Before removing a gate, list
every job it does.

## Measured

The two runs (`holds_the_feelings`, Directive, 1 run each, $0.01 in total) both came before the pacing went in:
- Before the change, the provide chat asked about income, bills and savings for four turns and never stored a core
  issue. Its third reply dropped both "sad" and "failure".
- After the change, message 1 stored "not providing means you are a failure" and asked what providing means to them.

The second feeling went untested: the check came before "I'm frustrated" was sent. muhammad tests the paced build by hand.

## Still open

- Three tests fail on muhammad's uncommitted `abcde.md` rewording (they assert the old sentences); left for him.
- The offer still says "question whether they're true" against a value (R28).

See [[mirror-picked-one-clause-2026-10-22]], [[failure-classes-from-later-branches-2026-10-21]], [[measure-before-tuning-prompts]].
