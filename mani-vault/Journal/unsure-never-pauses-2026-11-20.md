---
type: journal
date: 2026-11-20
apps: [backend]
tags: [journal, safety, crisis, pause, production]
summary: "Production paused a lonely, crying person whom the model judged unsure every turn; only danger the model judged can now lead to a pause, and sadness with a hurtful family reads as none."
failed:
  - "Tried holding a second unsure answer as danger after Mani asked once; failed because the next sad message paused a person the model never judged in danger"
  - "Guessed from code alone that the model read the family as danger; failed because the stored traces showed unsure on every turn, so the fix belonged in code's rule, not first in the prompt"
---
2026-11-20

# An answer judged unsure never pauses

## What happened

On production (mani-app, thread `c2388a01`), Lolly wrote, in Directive: Thanksgiving alone, "I feel really unsafe
with my family", then "manipulative, controlling, verbally abusive; I set a boundary", then "I cannot stop crying".
The chat paused for 15 minutes on that third message. Her message is in `docs/client/messages/2026-11-20-thanksgiving-lockout.md`.

The stored traces (read-only, muhammad asked me to read them) show the model judged `unsure` on every one of those
messages: `from_someone`, `from_someone`, then `themselves`. Its own line on the pausing turn, which became the pause's
stored reason: "no self-harm or immediate danger is stated". Code made the danger. `safety.after` held the second
unsure as danger because Mani had already asked (the 2026-11-16 "two steps for vague words" rule, see
[[crisis-next-message-decides-and-the-pause-follows-them-2026-11-16]]), and the pause rule then paused the next
message because the state before was danger and nobody was with her.

## Why the rule was wrong for the one-call turn

- It was written for words about dying with no plan, and it caught every unsure worry about a person, an unsafe
  family included. R104's own note warned that someone only low and vague could be paused on their third message.
- Its middle step, "MANI's worry and how to reach help" before the message that decides, cannot happen in the one-call
  turn: code raises the state after the model has written the reply, so the person gets no warning at all. Her reply
  on that turn was an ordinary question about next Thursday.
- It broke the client's rule (15): never pause on an unsure concern.

## The fix

The same diagnosis was first made on `fix/only-model-danger-pauses` (parked in a stash the same day) and moved onto
`feat/crisis-paused-rework`, into the one rule of [[crisis-pause-one-rule-and-the-worry-forgets-its-kind-2026-11-19]]:

- Only the model raises a concern about a person to danger (`safety.after`). Danger the model judged still holds
  against a later unsure of the same worry only (`worry_about`): chest pain, raised to danger by code, then "I wish I
  weren't here" judged unsure, would otherwise pause the same way. "Asked, then the answer says danger" still pauses
  at once.
- The read: `mani.md` says sadness, loneliness and crying are `none`, and so is a hurtful relationship with no threat
  of harm; an explanation that they meant people who are unkind or controlling with words is accepted like grief.
  Eval case `rule-sadness-is-not-danger` (an ordinary person, not her words). The eval has not run.

The pause-only-after-a-help-reply guarantee proposed before the traces were read was not built: its premise was a
danger read that never happened, and with code no longer raising unsure, a pause needs a danger read whose reply
the model wrote knowing it was danger.

## Lesson

A code rule that raises the model's judgment acts on a reply that was already written. When code overrides the read,
check what the person sees on that turn, not only on the turn that pauses. Read the stored traces before naming a
cause: the code alone suggested the opposite.

## Found in the edge-case pass the same day

Fixed on `feat/crisis-paused-rework`: a pasted copy of Mani's reply with the person's own words added is read like any
message (`text.COPY_ADDED_WORDS`; it used to get the fixed line and no safety read), and a set stopped while the safety
question after its last stage waits no longer leaves `safety_end_check` at "asked" (`turn._updates`). Both came from
the audit in `backend/docs/mani-conversation-audit-2026-11-20.md` (S2, S6), which is still parked in a stash.

muhammad then chose, the same day (asked as options with examples):

- A first message back read as danger gets a fixed way-to-help line (`crisis.RETURN_DANGER_REPLY`), not the question.
- An unsure worry closes on the second calm message in a row (`worry.CALM_TO_CLEAR`); `mani.md` no longer tells the
  model that a changed subject keeps the worry unsure. A direct answer (return check, end check) still settles at once.
- The pausing turn sends Mani's own reply, then the pause line.
- A retry of a message whose reply was the fixed failure text runs the turn again, through `rewind.undo_last_turn`, so
  an empty reply's danger state is taken back too and the retry does not pause on its own first message.

Still open: a danger read with no kind pauses only on a refusal; "No, I'm not safe" with no detail after a pause may
need one more message. The prompt changes have not been through the evaluation.

Later the same day muhammad asked for the last two as well. Both rest on one field of the model's read, and the code
rules behind them are decisions he kept (a danger of no kind needs a refusal, 2026-11-19; after a pause only an answer
that says the danger is still there pauses, 2026-11-16), so the fix is at the source: `mani.md` and the reply schema
say `about` is always filled when the level is unsure or danger, and that "no, I'm not safe" in answer to how things
are is `still_there`. `run_eval.py` can now check `about` and `still_there`; `rule-overdose` checks `about`, and
`rule-not-safe-after-pause` is new. Not measured: the eval has not run.
