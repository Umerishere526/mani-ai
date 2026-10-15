---
type: journal
date: 2026-10-13
tags: [journal, memory, architecture, abcde, lessons]
---
> Superseded 2026-10-14 (each stage judged "since the confirmed check", reported in stage_updates) — see [[reach-judged-in-its-own-field-2026-10-14]]

# The transcript is the memory within a thread (2026-10-13)

muhammad's Supportive run (thread 7d102554): after B, Mani asked C, D and E with the client's fixed questions
though the person had said them, and they answered "I've already mentioned…" three times. This was the fourth
round of the same class of failure.

## What the earlier fixes missed

- The model saw only the last 20 messages. `messages.py` said "Matches the previous system's window": the
  number was inherited, never chosen, and a thread reaches E at about message 23 to 30.
- So everything needed later was guessed into a store ahead of time: the seed of every stage at the yes, and
  the understanding record. Guessed early, a store is stale or thin. Each fix (seed better, clear what went
  stale) patched the guess and opened the next bug. That was the design, not the prompt.
- My clearing rule fired on "yes, and more" and could wipe good stages.

## What changed

- **The architecture reviewer weighed seven designs:** the status quo, a longer window in a framework, the
  whole thread, case notes, a rolling summary, retrieval, and every message updating every stage. It
  recommended the whole thread within a budget. Fable 5.1 reviewed the plan twice and found:
  - the memory fold reads raw messages, not summaries;
  - the summary uncached the history on every refresh;
  - the typed yes paths would lose A's guidance;
  - the correction rule (AC-8);
  - a missing D gap line needs a typed field, not text matching.
- **Memory:** the whole thread up to 40,000 characters, dropped in blocks of 20 past it. The summary is sent
  only once messages have left.
- **Walk:** each stage is judged when it is reached, from the whole thread since the confirmed check, by its
  own `ready_when` and `reach` rule. Nothing is stored ahead; stale entries from before are ignored.
- **E:** a plan is not the new belief, and `acting` waits for E's one try.

## Lessons

- When a fix needs a store to "remember" something past a window, first ask whether the window should exist.
- Grep a constant's comment before trusting it. "Matches the previous system" is not a reason.
- Have the plan reviewed by a different model before building; both reviews here caught real breakage.

See [[client-sample-voice-and-confirmed-check-2026-10-13]], [[abcde-walk-owned-by-code-2026-10-13]].
