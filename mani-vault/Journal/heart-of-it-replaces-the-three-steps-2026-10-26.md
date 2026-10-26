---
type: journal
date: 2026-10-26
tags: [journal, prompts, understanding, check, design, lessons]
---

# The heart of it replaces the three steps (2026-10-26)

Lolly sent two conversations with plain ChatGPT (a boss who won't lead, a 43-year friendship) and said "I wish mani
sounded this way"; Mani "went down an unnecessary rabbit hole, missing the problem + core issue". Third complaint of
this kind after the 2026-10-22 and 2026-10-25 fixes, so the patch limit tripped and the architecture reviewer was
asked. It reached the same verdict on its own: the design, not the wording.

## Root cause

Before a framework Mani filled slots. Code walked the problem, core issue and feeling underneath one per turn
(`understanding.STEPS`, `advance`, `found`, `[ctx] understanding_next`), checked as soon as they were full (message 3
to 4), made every reply end on a second question (`options`), and the prompt banned offering a reading ("never
explain people to themselves", "never leads them to a conclusion"). ChatGPT instead holds one growing reading of the
central conflict, says it as a guess, and tests it with one question ("Was it the disagreement itself, or how she
treated you?"), until it knows what they want and what is stopping them.

## Measured before building

- Bare-prompt diagnostic (Lolly's one paragraph as the whole system prompt, 6 turns, $0.03): `gpt-6-luna` made the
  same moves as `gpt-6.1-sol` in the friendship chat, so the model was not the gap. In the boss chat both bare models
  read "directive" as advice and wrote bullet lists: our understand-first and no-advice rules are what keep Mani off
  that, so they stay.
- Baseline replay (`chatgpt_reference`, Directive): "what does that mean to you?" three turns running in the boss
  chat, the friendship chat checked at message 6 before what she wants was known, every reply ending "Is it A, B, or
  something else?".

## Change (muhammad's decisions)

- `heart` (`exploring`, `conflict_named`, `ready`), one closed value per chatting reply. Never let it grow back into a
  multi-part record: that is how Mani ended up filling a form instead of listening.
- Check only from their 5th message and only on a reply that says `ready`; a `ready` with no check makes the next
  turn `check: due` (code names the turn, the 2026-10-16 lesson). The check says the conflict, what they want and
  what is stopping them; its summary is the stored `case`.
- `understanding_update` keeps only `feeling`. `options` is gone before a framework. `heading_toward` only on the
  answer to a check.
- `mani_base.md` cut from 9,479 to 9,180 characters: the reading as a guess, questions that test it, an observation
  now and then, never announcing a question (not quoted, since quoted bans get spoken).
- Lolly's chats are Directive's examples only, edited for the announced questions, ChatGPT's two slips and the
  figures the prompt bans. In `mani_base.md` every style would copy them ([[three-styles-read-the-same-2026-10-22]]).

## After (one Directive run, $0.03)

- Turns 1 to 4 read like her chats: forked questions, a reading that grows ("It seems the disagreement hurt because
  you felt dismissed…", "That imbalance sounds like the deeper hurt"), no options line, no preamble, no flags.
- The boss chat judged `ready` at their 6th message, the friendship chat at their 9th; ChatGPT went to about the
  12th. Both went from `exploring` straight to `ready`, never `conflict_named`. One run is noise, but watch it.
- A check part written to run on into the next went out as "leave,. but": `repairs._sentence` now keeps a trailing
  comma.

## Lessons

- Run the bare model first. It separates "the model can't" from "our structure won't" for a few cents.
- The case no longer grows during a framework (2026-10-22 made it add-only after the boss chat's D and E missed later
  details). The transcript is in view; whether D and E use it is unmeasured.
- Short scripted conversations (3 to 5 lines) can no longer reach a check, so `answering_the_offer` and
  `client_documents` stop before the offer. They need longer lines.

See [[failure-classes-from-later-branches-2026-10-21]], [[core-issue-was-situation-2026-10-25]],
[[mirror-picked-one-clause-2026-10-22]].
