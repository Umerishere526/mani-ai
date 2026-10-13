# 0003. Structured reply fields: rationale

The decision record behind [index.md](index.md).

## Context

Scope feature 16. Requirements R1, R3 and R9 in `docs/client/requirements.md`. The Decision in force "No phrase lists judge the conversation" (2026-10-09) already names this as the remaining gap.

Code reads meaning from words in eight places outside `safety.py`:

| Where | Reads | Decides |
|---|---|---|
| `repairs.named_place` (`_PLACE_WORDS`) | the person's message | which body practice to send |
| `repairs.declines_or_acts` | the person's message | skip the body practice |
| `repairs.comes_back` | the person's message | send the client's "it returns" text |
| `"?" in content` (orchestrator, two places) | the person's message | they asked about the open offer |
| `_ASKS_WHAT_NEXT` (orchestrator) | Mani's reply | show the handoff buttons, the body route "described early" path |
| `_OFFER_WORDS`, `_without_permission_question` | Mani's reply | find and replace the model's permission question |
| `_OFFER_SENTENCE` | Mani's reply | strip offer words when the offer button was dropped |
| `practice_in`, `_says_name` | Mani's reply | whether a practice or the framework's name is already there |

Each one misreads paraphrases. The Decision in force records that literal matching "cannot read a paraphrase, so its judgments were silently wrong whenever people worded things differently". The client's offer and Keep chatting lines in `backend/content/frameworks/abcde.md` (`offering.offer`, `offering.keep_chatting`) are already templates with `<...>` slots, and the body route's branches in `backend/content/prompts/somatic.md` are fixed client text. Yet the model writes the offer in free text, and code then digs the client's parts out of it again.

Constraints:
- **One chat call per turn, at effort `low`** (Decision in force, R2). Nothing here may add a call or a redraft.
- **Health data.** Slot values are the person's words, so they never reach a log.
- **Gates stay in code and the database** (scope Done when): the offer window, cooldowns, which framework is running, and which stage.
- **Prompt changes cut, they never add** (muhammad, 2026-10-08).
- The client's deadline for R9 is 2026-10-14. This feature is scoped `Next`, not a blocker.

## Options considered

### Option 1: One schema per moment, picked from database state

Code works out the moment from the database and sends the schema class for it. This extends the existing `ReplyWithoutOffer` pattern.

**Pros**: A field exists only where it means something, so the model cannot fill it out of turn, and the gates are structural. Each turn pays only for the field descriptions it needs.
**Cons**: A schema factory with several variants and one more pure function to keep in step with the stage machine. Changing the schema between turns can cost prompt cache hits on the schema part.

### Option 2: Flat optional fields on one `Reply`, always sent

Add `offer`, `offer_answer` and `body` to `Reply` as nullable fields, and have code ignore them outside their moment.

**Pros**: One class, and the smallest diff.
**Cons**: Every turn pays for every description. The model can fill a field that does not apply, so code needs a guard in each place. "Ignored" stays a convention, not a structure.

### Option 3: One tagged union field chosen by the model

A single `moment` field whose type depends on a tag the model picks.

**Pros**: Compact.
**Cons**: The model decides which moment it is in, which moves a gate from the database to the model, against the scope's Done when.

For the offer itself, a single free line plus code adding the name was weighed against filling the client's slots. The free line keeps the model's own wording, but it drifts from the client's template and keeps `_says_name`. For the body route, separate `place` and `response` fields were weighed against one enum. The pair is more flexible, but it creates combinations (declined plus chest) that the client's flow never defines.

## Rationale

The scope's Done when has two halves, and Option 1 meets both by construction. The regexes go because the model reports each judgment directly. The gates stay in the database because a field cannot exist outside the moment the database selects. Option 2 meets the first half only by discipline. Option 3 breaks the second half.

Filling slots beats a free line because the client's wording becomes exact by rendering, not by stripping, which removes a whole class of repair code (`_OFFER_WORDS`, `_OFFER_SENTENCE`, `_says_name`, the permission question swap). It also matches the house rule that code owns the client's fixed wording and the model owns meaning (journal, 2026-10-12, general judgment over case patches).

The offer has no framework id of its own. `heading_toward` already names the set the model is reading toward, and the prompt says it decides which set is offered. A second id could disagree with it, so the offer uses `heading_toward`.

`moved_on` is separate from `no` because sending the client's Keep chatting question to someone who has just raised something new would talk past them. Yet both are a decline for the cooldown, as muhammad decided on 2026-09-24.

Settled calls (pick, why, runner up):
- **Closed sets as `Literal`, with a `mode="before"` validator that maps an off-list value to `None` and logs it.** The model sees the allowed set in the JSON schema, and a bad value never raises (a `ValidationError` costs a second call and can lose the message, as `schema.py` records). This follows `Button._decline_written_as_a_word`. `StageKnown.status` is a `Literal` without such a validator, which is exactly the exposure this avoids. Runner up: `strict=True` in `chain.build`. That decodes the enums reliably, but it changes every call in the app and forces every field to be required, so it is a separate decision.
- **Branch ids in content.** Each `if_unclear` branch in `somatic.md` gets an `id:` key equal to its `body` value (`chest`, `pain`, …), and code looks branches up by id. Today `practice_for` and the pain and returns lookups match English inside `when`, which is our own text but still fragile. Runner up: keep matching `when` substrings.
- **Template rendering.** In a client template, a `<...>` that is the whole first line is replaced by `lead_line`. An inline `<...>` is replaced by `going_through` (offer) or `their_words` (Keep chatting), and every inline slot in one template takes the same value ("the same short noun phrase"). A slot value has surrounding quotes and trailing punctuation stripped, and keeps its case. One renderer in `repairs.py`, next to `_compose_offer`. It parses our own content, never anyone's words. Runner up: store the templates with named slots (`{going_through}`), which is cleaner, but means editing the client's text in content.
- **Slot descriptions come from the client's placeholders.** The schema description of `going_through`, `lead_line` and `their_words` is the text inside that `<...>` in the thread's style's template. That is the client's own description of the slot, so each style's different meaning (directive "feel like <…>", supportive "feel so <…>", reflective "When you say <…>") reaches the model without a hand written copy. Runner up: one fixed description per field, which cannot carry three meanings.
- **Moment selection** is one pure function, `context.moment(...)`, over values the orchestrator already computes. Runner up: inline branches in `send`, which is already 400 lines.
- **The schema is built by one factory**, `schema.reply_for(...)`, using `pydantic.create_model` over the core fields plus the moment's fields. Runner up: one hand written class per variant, which comes to about eight classes.
- **A body value outside its phase is accepted as a known leak.** One `body` enum is sent in every body phase, and a value invalid for the stored phase is ignored and logged. Runner up: a per phase enum, which is stricter but multiplies the variants for little gain, since the invalid combinations are few and harmless when ignored.
