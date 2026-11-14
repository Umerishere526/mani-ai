---
type: journal
date: 2026-11-13
apps: [backend]
tags: [journal, safety, crisis, pause, lessons]
---

# The crisis pause fires on a refusal, not on a missing "help in place" (2026-11-13)

2026-11-13. History, not rules. The rule in force is the safety entry of Decisions in force in `backend/PORT-STATUS.md`.

## What the live replays showed

The first live replays of the pause (Task 10, two runs of each chat, scripted lines through `runner.send`) paused where
the design said it never would:
- The chest-and-wife chat paused in both runs, 2 and 3 times, while the wife was making the call. The model re-judged
  `help_in_place` every turn and flipped it to false on short or off-topic lines ("i cant think of that right now",
  "either or both"); one false read paused the chat. "yea i have my wife in front of me and i told her to make the call"
  was read false in both runs, although the field's own description says "someone is with them".
- Body-symptom chats paused on the first doubt ("dont you think it could be stress"): 5 pauses in 6 chances.
- The pause text offered the suicide line for a bee sting and said "your safety" for a friend's overdose.

## Why one `help_in_place` judgment was the wrong sole gate

The rule was "danger before, danger after, and not `help_in_place`". That makes every turn in danger a pause unless
the model, on that very turn, positively affirms help. A gate that fires on the absence of a judgment fires on every
lapse of it, and the model's judgment lapses on short lines. muhammad's rule needs a positive signal instead: they
refuse help, say again they will do it, or push the question away. `declined` already meant the last of these and was
already held by code (a refusal never lowers a concern), so it was broadened to the other two rather than adding a
field. `help_in_place` stays as a second guard. A doubt, a question, a step under way, and pushback about a symptom in
the body are never declined. The description alone was not enough for the body: Lolly's 2026-11-11 replay had the model
read "you already said this a few times" as declined with no `about` and no danger value. A blanket "never pause a
body danger" guard was tried first and replaced the same day (the controller's ruling): someone who refuses the
ambulance for chest pain happening now needs the pause too. So a body danger pauses only when the turn's own read is
`declined` with danger now and `symptom_now` yes, an outright refusal of the help; whose danger it is comes from the
conversation (`understanding.danger_about`) when the read names none.

## The owed check is bounded

A pause owes the return check only while it ended within `RECENT_CRISIS_DAYS` (30), the window `recent_crisis` already
uses; without a bound, every old unchecked pause would make every conversation ask, however long ago.

## Two more from the owner's chat

- A conversation created before the pause asked nothing when opened after it, so going back to an older conversation
  bypassed the check. Now every conversation asks about the person's latest pause until a settled answer marks it
  checked. Loading only the conversation's own pause first (the Task 8 fix in
  [[crisis-pause-audit-findings-2026-11-13]]) also hid a later pause from a conversation that had answered its own, so
  the turn now loads both: the person's latest, and its own.
- The danger reply asked its question, gave the direction, then asked the same question again: `_with_forward` dropped
  the text's copy only when the text ended on it. It now drops that sentence wherever it stands.

Related: [[crisis-pause-audit-findings-2026-11-13]], [[safety-is-the-models-judgment-2026-11-10]].
