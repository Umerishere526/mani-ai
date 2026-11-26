---
type: journal
date: 2026-11-19
apps: [backend]
tags: [journal, safety, crisis, pause, design, redesign]
summary: "The pause's state lived in four places with different lifetimes; one rule over one standing replaced the flags, and a worry's kind is forgotten when it settles."
failed:
  - "Tried patching each gap in the pause on its own; failed because a settled body worry's kind blocking a later pause is the same fault as the question's kind (two record keys, one rebuilt each turn, one never), the fifth fix in the area"
  - "Tried honouring checked_at in the conversation a pause began in, on its own; failed because that conversation stays at danger, so its next message would pause with no word from Mani"
---
> Superseded 2026-11-25 — see [[return-check-only-in-the-paused-conversation-2026-11-25]] (the settling by `checked_at` across conversations, and changes 2 and 3 for new conversations)
2026-11-19

# One rule for a conversation's safety, and a worry forgets its kind when it settles

Work on `feat/crisis-paused-rework`. muhammad asked for the gaps in the crisis pause, then approved redesign A of the
`architecture-reviewer` and ruled on gap 2: their word that they are all right, in any conversation, ends the question
everywhere, the paused conversation included. What came before: [[crisis-next-message-decides-and-the-pause-follows-them-2026-11-16]].
The decision is in "Decisions in force" in `backend/PORT-STATUS.md`.

## What was wrong

- A worry's kind sat in two record keys with different lifetimes: `asked_about` was rebuilt every turn, `danger_about`
  never was and was read as the kind of the current worry. After a settled body worry, a later danger the model gave
  no kind inherited `body` and could not pause with a refusal.
- `pauses_now` took eight inputs, two of them flags (`is_return_check`, `after_return_check`) standing in for the
  phases of the question owed after a pause, which had no states of their own. The first-message-back rule flipped
  three times in four days.
- The conversation a pause began in was never reached by their answer elsewhere: its `threads.safety` stayed danger,
  and a test pinned that it asked again. Honouring `checked_at` alone would have let its next message pause with no
  word from Mani.

## What it is now

`worry.step(Standing, Safety)` is the one rule. `Standing` is the state, the worry's kind (`worry_about`, only while it
is open) and the phase (ordinary, asking, answering). `worry.standing` settles a held worry whose conversation's last
message came before the latest pause's `checked_at`; that is one-shot by construction, since the next message is later.
`pause.return_check` is the one rule for who is owed the question; `own_pause`, `ReturnCheck.kind` and its query are
gone. Every sequence in `test_worry.py` was first run through the rules as they stood, and only the rows commented in
the file differ.

## Changes from before

1. A settled worry's kind is forgotten. A later danger with no stated kind needs a refusal to pause, like any other:
   before, after a worry about themselves it paused without one. muhammad kept this on 2026-11-19.

For muhammad to keep or overrule:

2. A conversation asks with the latest pause's reason, wherever the pause began: before, the paused one used its own
   older pause's reason when a later pause was elsewhere.
3. The answer to the question a new conversation opens with is a held turn: no rate limit, no fixed copied-back line.

## Left alone, on purpose

The start at unsure on the turn that owes the question stays (a refusal there keeps it unsure); it is a row of the
table, not a leftover. R102 (the 25 s wait) is still open. R101 was done the same day, muhammad approving it: the first turn back after a pause is
code's fixed question (`crisis.RETURN_CHECK_REPLY`), because the one-call turn left "never agree to carry on first" to
one line of the facts. The model's read of that message still counts; its text is dropped. The two `pauses`
queries (the turn context and `pauses.owed`) stay two: they run with different column grants.
