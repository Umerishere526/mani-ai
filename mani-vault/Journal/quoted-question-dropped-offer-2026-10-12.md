---
type: journal
date: 2026-10-12
tags: [journal, offers, repairs, design, lessons]
---

# A quoted question cost a valid offer (2026-10-12)

muhammad's Directive test (resentful coworker, thread 46ffc5e4): Mani answered "why me" with
"“Why me?” sounds like the question coming up for you. There's a framework called ABCDE…". It
showed no Try it, Tell me more or Keep chatting buttons, the framework state stayed inactive, and
the "yes" after it began ABCDE in Mani's words only.

## Root cause

`repairs.apply` decided that an offer shared the reply with a second question using
`"?" in part`. The `?` inside the quoted "Why me?" counted, so the code dropped the buttons. It
then tried to strip the offer's words with `_OFFER_SENTENCE`, which only knows "set of
questions" wording and missed "a framework called ABCDE". So no `offered` row was written, and the
next turn had no pending offer to accept.

It was not the offer window. `PAUSE_FIRST_OFFER_WINDOW=true` in `backend/.env` kept the window
open on every turn, and "why me" was the person's third message anyway.

Reproduced without the model: the two repair functions turn the reply plus "Would you like to
try it?" into the stored message character for character.

## What changed

The offer wins. A question put to them beside an offer is cut, and the offer is always composed
with the client's permission question and buttons. A question is a sentence that ends in `?`, so
one quoted mid-sentence is not one (`repairs._asks_them`). This was the fourth change to the same
check. "Offer wins" had already been tried in 2f617d4, and it was lost only to the whole-repo
restore in f064d5a, not because it failed.

## Lessons

- A single character is not a question. When code reads the model's text, it should read whole
  sentences.
- When a heuristic fires, the turn's decision (the offer) should survive and the side text should
  go, not the other way round.
- Seen, not changed: when the model's text does not name the set, `_compose_offer` adds "It's
  called ABCDE." straight after a reflection, which reads abruptly. This existed already for
  offers made only by buttons.

See [[offer-window-owned-by-code-2026-10-12]].
