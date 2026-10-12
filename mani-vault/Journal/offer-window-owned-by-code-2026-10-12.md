---
type: journal
date: 2026-10-12
tags: [journal, offers, cadence, design, lessons]
---
> Superseded 2026-10-12 — see [[one-call-turns-at-low-effort-2026-10-12]] (an early offer is redrafted once, then stripped: the reply shape now has no way to make one)

# The offer window is owned by code (2026-10-12)

Lolly's Direct test (resentment toward a coworker) got ABCDE in reply to her first message, and
she stopped testing (R1 in `docs/client/requirements.md`).

## Root cause

Not a bad line: the Decision in force of 2026-10-10 said a framework is offered as soon as it
fits, from the first message (see [[direct-questions-have-no-target-2026-10-09]]). Every layer
carried it out:

- `context.cooldown_passed` returned yes whenever nothing had been offered, so `[ctx]` told the
  model "an offer may be made in this reply" on turn 1.
- `[ctx]` meanings and `mani_base.md` said "as soon as one fits, offer it", Direct "reaches the
  offer soonest", and ABCDE "fits as soon as they have described a situation". A situation plus
  a feeling word made almost any first message a fit.
- The only count based gate (the closest fit window) was keyed on `offer_fit`, a label the model
  set itself. The redraft note even told it "if you are confident, set offer_fit to clear".

The decision misread the client's spec: "a range, not a required count" is about not padding
questions; the cadence still puts about two to four exchanges before the offer, and all three of
the client's examples offer on the person's third message.

## What changed

One window, `context.offer_window` (not_yet, open, due), counted in the person's messages, the
same in every style: opens at their third, due at their fifth. `offer_fit` is gone. The prompts
follow the window and hold no timing of their own.

## Measured (2026-10-12)

`scenario_check.py`, `resentful_coworker` (Lolly's message word for word, then four of muhammad's
test lines) and `workplace_boundaries`, 3 runs in each style: 18 of 18 offered ABCDE at the
person's third message, none earlier, about 0.05 dollars. Every offer came at the earliest point
the window allows, never later, so the model reads `open` as "offer now". Watch whether the
client finds message 3 too soon in Supportive and Reflective.

The checker's "same question" flag fired 36 times on these runs: with offers now at the same
message in every style, it compared the client's fixed permission question across styles. It now
compares only Mani's own questions.

Seen but not part of R1: Supportive sometimes answered with no question at all ("I'm glad you
told me.", "I'm sorry that happened, especially after you stayed late to help."), and two
Supportive replies handed the person's words back. Both belong to R3 and R5.

## Lessons

- A gate keyed on a label the model sets for itself is no gate, especially when the rewrite note
  says which label passes.
- When code and prompt both speak about timing, they drift; let code own the number and the
  prompt only read it.
- The architecture reviewer caught the `offer_fit` bypass that a line level reading missed.

## Open

- `_their_messages` assumes three opening messages (greeting, style tap, opener). A thread whose
  style is set through `PATCH /v1/threads/{id}` has one, so the count runs low and the offer
  comes one message later than intended. Count the person's messages directly before the
  frontends go live.
