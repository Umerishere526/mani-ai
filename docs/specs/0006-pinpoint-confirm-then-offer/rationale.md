# 0006. Rationale

## Context

Three client inputs arrived on 2026-10-13: a sample conversation for voice and tone, a flow agreed in a meeting (understand the problem, find what is in their control, check the understanding, then offer), and a Framework Selection Cheat Sheet (pinpoint the problem, then its core issue, never select from the opening feeling). Lolly's message the same day said neither chat version showed that Mani "truly understands the person's emotional concern".

The offer gate was a count of the person's messages (`context.offer_window`: not before the 3rd, due at the 5th). It had three fixes in a row (scope features 12, 15, 19): an offer at the first message, offers at the third from an event alone, offers about the wrong thing. Each fix tuned the count or the fit rule around it. None recorded whether the person agreed that Mani understood them, which is what the count stood in for.

Constraints:
- one model call per turn at effort `low` (R2);
- no phrase lists judging what people say;
- offers are client templates;
- only ABCDE is active, and the other five must come back without a code change (muhammad, 2026-10-13);
- the check's wording must not be fixed text (muhammad, 2026-10-13).

## Options considered

### Option 1: Keep the count window, tell the model to check first

Leave `offer_window` and add a prompt rule: check your understanding before offering.

**Pros**: no migration, smallest diff.
**Cons**: nothing in code knows a check happened, so the offer cannot be gated on it. The only ways to tell are reading the text with a phrase match, which the Decisions in force forbid, or trusting the model, which offered early 18 times out of 18 when told the window was open. It is the fourth tune of the same proxy.

### Option 2: A confirmed check stored on the thread, marked by a typed field (chosen)

The reply's `check` field marks the check, code stores its state on `threads`, and the next turn's shape (`CHECK_OPEN`) reads the answer. The offer exists only after a yes.

**Pros**: the gate is a database fact, like an open offer is today. It reuses the Moment and shape pattern. One call per turn. The words stay the model's own.
**Cons**: a migration and a new moment. One more exchange before an offer.

### Option 3: The check as a client template rendered by code

Like the offer: a fixed frame with slots.

**Pros**: exact wording, code knows it was sent.
**Cons**: muhammad rejected fixed wording (2026-10-13): "wording can change, let the LLM decide". The typed field in Option 2 gives code the same certainty without fixing the words.

### Option 4: Store the check state inside `threads.understanding` or `thread_technique_state`

**Pros**: no new columns.
**Cons**: `understanding` is reported by the model and merged, and gate state must not pass through that. `thread_technique_state` is one upserted row per thread, keyed to a framework, so a later offer overwrites the check. A flag on the message is lost when history scrolls out of the 20 message window.

## Rationale

The offer timing failures share one cause: code gated on a proxy and never on what the person said about Mani's understanding. The client has now named that signal, so storing it is the fix at the level of the design. Option 2 is the only option that keeps every constraint at once. The gate is code owned and database keyed, nothing reads text, the turn stays one call, and the wording stays the model's.

The first draft stored a state machine (`open`, `confirmed`, `declined`). A cross check on another model (2026-10-13) found that it could strand a thread. A confirmed check whose offer was dropped waited forever, because a waiting offer never rendered after a declined row, and the old "they just finished it" rule refused ABCDE for good once it was done. Storing only when the last check was made, and reading "open" as "the last reply was the check", removes every state that could stick. A check is used on the next turn, whatever happens on it. The floor at the 2nd message keeps R1: the earliest offer is the 3rd message, the same as today.

Framework choice stays the model's (`heading_toward`), restricted to active ids. The sole active set fallback is generic, so with six active it never fires. No framework id enters code. The seed contract check makes "add a framework" fail loudly at seed time, instead of in a live chat.

The architecture reviewer (2026-10-13) reached the same design independently: a column on `threads`, `CHECK_OPEN` mirroring `offer_answer`, the count deleted, the clarification phrase match deleted.
