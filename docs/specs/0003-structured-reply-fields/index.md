# 0003. Structured reply fields in place of text parsing

**Date**: 2026-10-12
**Status**: In Progress

## Summary

Today the backend guesses from words. It guesses where in the body someone feels something, whether they said no, whether they asked about an offer, and whether Mani's reply ends a framework. This spec has the model report those things in typed fields of its JSON reply. Code then sends the client's own fixed text: the offer, Keep chatting, the body practices and the handoff. The reply shape sent each turn depends on what the database says is happening, so a field can only exist when it means something, and every gate stays keyed on the database. The regexes and phrase lists that read meaning go away. Only the safety screen keeps one.

## Requirements

**User stories**:
- As the client, I want every offer, Keep chatting line and body practice to read exactly as I wrote it, in the person's style, so that Mani sounds like my design.
- As muhammad, I want the model's judgments to arrive as typed values, so that no regex silently misreads a paraphrase and each judgment can be counted in the logs.

**Acceptance criteria**:
- **AC-1**: The reply schema for a turn is chosen only from database state and the deterministic safety screen: the live technique row's outcome and phase, `context.offer_window`, the buttons stored under Mani's last message, whether a framework retires this turn, and `safety.screen`'s result (moment table below). A field that is not in that moment's schema cannot affect the turn.
- **AC-2**: When the `chatting` moment carries `offer`, the reply fills it, and `heading_toward` names a framework, the whole reply text is the client's `offering.offer[style]` template for that framework, rendered word for word with `going_through` (and `lead_line` where the style's template has a whole line slot), then `Would you like to try it?`. The model's `text` is not sent on that turn. The buttons are Try it (with the framework id), Tell me more and Keep chatting.
- **AC-3**: An offer is dropped when any of these hold: `heading_toward` is null or not in the registry; `going_through` is empty; `lead_line` is empty when the style's template needs one; the framework has no `offering.offer[style]` template; the framework is the one they already finished; or the window does not allow it. Then the model's `text` is sent alone with no buttons, no `offered` row is written, the miss is logged as `offer unusable: <reason>`, and no second call is made.
- **AC-4**: The answer to an offer drives the row:
  - **Taps first.** A tap on a stored button (Try it, Tell me more, Keep chatting) decides by itself, and `offer_answer` is ignored on that turn.
  - `yes` starts the framework (`ACCEPTED`). The same reply asks the first stage, and its step is corrected from its ledger as on any stage turn.
  - `no`, or the Keep chatting tap, records `DECLINED`. The reply is the client's `offering.keep_chatting[style]`, rendered with `their_words`. If `their_words` is empty, the model's `text` is sent and the miss is logged.
  - `moved_on`, null or an off-list value records `DECLINED` (the same cooldown), and the model's own `text` is sent.
  - `asked`, or the Tell me more tap, keeps the row `OFFERED` (row handling as today). The reply is the client's `offering.explain[style]` for the framework on the `OFFERED` row, then the permission question, then the buttons Try it and Keep chatting.
  - On a live `DECLINED` row, `yes` (they asked for it back) starts it at any time. Any other value changes nothing.
- **AC-5**: In the `body` moment, each `body` value sends its `somatic.md` branch word for word (in the thread's style where the client wrote one per style):
  - **Taps first.** A tap on a stored place button decides the place by itself.
  - `chest`, `head`, `stomach` and `elsewhere` send the practice as the whole text, with no buttons.
  - `no_place` sends Mani's first sentence, then `somatic_practice.ask[style]`, with the buttons Chest, Head, Stomach and Somewhere else.
  - `agreed` (supportive only) sends Mani's first sentence, then the client's "What do you notice in your body?".
  - `declined` at `somatic_checkin` sends the client's decline line as the whole text. `declined` after the place question sends the model's `text`, since the client wrote no line for it.
  - `acting` sends the client's skip line as the whole text.
  - `pain` sends the client's safety line as the whole text, and no practice.
  - `returned` sends the client's returning text as the whole text.
  - A value that is not valid for the stored phase (transition table below) is ignored and logged.
- **AC-6**: The handoff buttons (Chat More, Go to Library) appear exactly when `body` is `declined` or `acting`, or on the turn a framework retires and Mani's last message did not already carry them. They are never decided by reading reply text, and the old exemption for a typed "Chat More" goes, since `_offered_handoff` already covers it.
- **AC-7**: No regex or phrase list outside `backend/mani/chat/safety.py` reads meaning from the person's or the model's words. The checks that stay are the ones in *Kept on purpose* below, and each matches a fixed string code owns, punctuation, or a stored button label. Removed: `_PLACE_WORDS`, `named_place`, `_DECLINES_OR_ACTS`, `declines_or_acts`, `_COMES_BACK`, `comes_back`, `_OFFER_WORDS`, `_without_permission_question`, `_OFFER_SENTENCE`, `practice_in`, `_says_name`, `_ASKS_WHAT_NEXT`, and both `"?" in content` checks.
- **AC-8**: A turn still makes exactly one chat call (`test_a_turn_costs_exactly_one_provider_call` stays green).
- **AC-9**: For ABCDE in the supportive style on an `offer_open` turn, the composed system prompt plus `[ctx]` plus the `offer_open` schema (the JSON schema text sent as `response_format`) is shorter in characters than today's system prompt plus `[ctx]` plus `Reply`.
- **AC-10**: The turn log carries the moment name and every enum value (`offer_answer`, `body`, the offered framework id), and never `going_through`, `lead_line` or `their_words`.
- **AC-11**: After muhammad's yes, one `scenario_check` run in all three styles covers an offer, a no, a moved on, a yes through the stages, and the body route. Every offer and Keep chatting line matches the client's template with only the slots changed. `scenario_check` flags any offer wording in `text` (eval tooling, not runtime), and the run reports how often that happened.
- **AC-12**: On a safety concern, from `safety.screen` before the call or from the model's `crisis` field after it, no client template is rendered and no row changes from a reply field. `offer`, `offer_answer` and `body` are ignored, only `text` is sent, and the framework stays paused exactly as today.

## Decision

**Chosen option**: Option 1: One schema per moment, picked from database state, with the model filling the client's template slots and reporting the body route as one enum naming the client's branch.

The model reports judgments in typed fields, and code renders all of the client's fixed text. The schema sent each turn is chosen from database state.

## Feature design

**Data model sketch**: No database change. The technique row (`outcome`, `phase`) and `messages.prompt_options` stay exactly as they are. `prompt_options` keeps its stored shape, and the HTTP `Turn` shape is unchanged.

**Moments** (computed in order, the first that matches wins):

| Moment | When (database state and the safety screen) | Schema fields beyond the core |
|---|---|---|
| `concern` | `safety.screen` reports a concern this turn (a crisis never reaches the model) | none |
| `body` | the framework retires this turn; or the accepted row's phase is the framework's `closing`; or it is `somatic_checkin`; or it is `somatic_practice` and Mani's last message carried the place buttons | `body`; plus `state` and `stages_known` while the phase is `closing` |
| `in_stages` | the accepted row's phase is any other stage, or a Try it tap starts it this turn | `state`, `stages_known` |
| `offer_open` | an `OFFERED` row (buttons showing or not) | `offer_answer`, `their_words`, `state`, `stages_known` |
| `chatting` | anything else | `offer` only when `offer_window != "not_yet"`; `offer_answer`, `state` and `stages_known` whenever the live row is `DECLINED` |

Core fields in every moment: `reasoning`, `style`, `heading_toward`, `text`, `title`, `crisis`. The `prompts` field is removed from every schema, and `ReplyWithoutOffer` is deleted. `text` stays required in every moment, because it is what is sent whenever a field turns out unusable.

**Fields**:
- `offer: {going_through: str, lead_line: str | None}`. The framework is `heading_toward`. The slot descriptions are the client's placeholder text for the style (Rationale). `lead_line` exists only when the style's template has a whole line slot (supportive, reflective).
- `offer_answer: Literal["yes", "no", "asked", "moved_on"] | None`
- `their_words: str | None`: the slot of the style's Keep chatting line, described by its placeholder. Filled on `no` or a Keep chatting tap. On a tap the message reads only "User tapped the button", so the model fills it from the conversation.
- `body: Literal["chest", "head", "stomach", "elsewhere", "no_place", "agreed", "declined", "acting", "pain", "returned"] | None`
- `state` loses `accepted`. It keeps `technique` and `step`, and is sent only in the moments listed above.

**State transitions** (body route, the stored phase after the reply):

| `body` | Valid when the stored phase is | Text sent | Buttons | Stored phase after |
|---|---|---|---|---|
| `chest`, `head`, `stomach`, `elsewhere` | `closing`, `somatic_checkin`, `somatic_practice` (awaiting place) | the practice for the place (whole text) | none | `somatic_practice` (retires next turn) |
| `no_place` | `somatic_checkin`, `somatic_practice` (awaiting place) | first sentence + `somatic_practice.ask[style]` | Chest, Head, Stomach, Somewhere else | `somatic_practice` |
| `agreed` | `somatic_checkin`, supportive style only | first sentence + "What do you notice in your body?" | none | `somatic_checkin` |
| `declined` | `somatic_checkin` | the client's decline line (whole text) | handoff | `somatic_practice` |
| `declined` | `somatic_practice` (awaiting place) | the model's text | handoff | `somatic_practice` |
| `acting` | `closing`, `somatic_checkin` | the client's skip line (whole text) | handoff | `somatic_practice` |
| `pain` | `closing`, `somatic_checkin`, `somatic_practice` (awaiting place) | the client's safety line (whole text) | none | `somatic_practice` |
| `returned` | retiring turn only | the client's returning text (whole text) | handoff unless already shown | retired |
| null | any | the model's text. When `state.step` moves from `closing` to `somatic_checkin`, the client's check-in question replaces its closing question, as `with_the_check_in` does today | handoff on a retiring turn unless already shown, else none | at `closing`, from `state.step`; otherwise unchanged |

On a retiring turn, only `returned` and null are valid. A tap on a stored place button counts as that place value.

**API surface**: No HTTP change. The internal surface is:

| Function | Inputs | Output |
|---|---|---|
| `context.moment(technique, outcome, offer, retiring_framework_id, awaiting_place, framework, concern)` | values `send` already holds, plus `assessment.blocks_framework` | a `Moment` enum |
| `schema.reply_for(moment, *, may_offer, declined_row, on_closing, templates)` | the moment, whether the window allows an offer, whether the live row is declined, whether the phase is `closing`, and the style's templates (for slot descriptions) | the Pydantic class to send, built with `create_model` |
| `repairs.render_template(template, *, lead_line, slot)` | a client template string | rendered text, or `None` when a slot it needs is empty |
| `repairs.apply(...)` | gains `moment`, loses the button filter inputs | `Repaired`, with prompts set by code and an `offer_dropped` reason when an offer was unusable |

**Value sourcing**:

| Action | Value | Source |
|---|---|---|
| choose the schema | moment | `context.moment` from the technique row, `pending_offer` (stored `prompt_options`), `retiring_framework_id`, `_awaiting_place`, `safety.screen` |
| choose the schema | whether an offer field exists | `offer_window != "not_yet"` (the window includes the cooldowns) |
| choose the schema | slot descriptions | the `<...>` text in the style's `offer` and `keep_chatting` templates |
| render the offer | framework | `reply.heading_toward`, checked against the registry |
| render the offer | template | `framework.stages["offering"]["offer"][style]` (`admin.frameworks`) |
| render the offer | `going_through`, `lead_line` | the model's `offer` field |
| render the offer | style | `context.resolve_style(ctx)` |
| render the offer | permission question | `repairs.PERMISSION_QUESTION` |
| render the offer | buttons | `repairs._offer_buttons` (labels from `greeting.py`) |
| answer an offer | outcome | `offer_answer`, or the tap (`find_tapped_prompt` on the stored buttons) |
| Keep chatting | template and slot | `offering.keep_chatting[style]`, and `their_words` |
| asked about it | framework | the `OFFERED` row's `framework_id` |
| asked about it | text | `offering.explain[style]` + `PERMISSION_QUESTION` |
| body branch | text and buttons | the `somatic.md` branch whose `id` equals `body`, via `reply_for(branch, style)`, and the branch's `prompts` |
| `no_place` | question | `somatic_practice.ask[style]` |
| place tap | place | the tapped stored label mapped to its `body` value |
| check-in question | text | `somatic_checkin.ask[style]` |
| handoff | buttons | `orchestrator._handoff()` |
| first sentence | text | `repairs.first_sentence(text)` |

**Key invariants**:
- A gate never reads a reply field. The window, the cooldown, the running framework and the stage machine read only the database, and a field outside its moment does not exist.
- A tap on a stored button outranks any reply field about the same choice.
- A safety concern or the model's `crisis` field suppresses every template and every row change from a reply field (AC-12). That guard runs before any rendering.
- An offer is never left open by default: any answer other than `yes` or `asked` to an `OFFERED` row declines it.
- Every word of client text reaches the person from content, never from the model's copy of it.
- An unusable field degrades to the model's own `text` and a log line. It never causes a second call or an error.
- The person's words in slot fields are never logged.

**Kept on purpose** (not meaning, so AC-7 allows them): `safety.screen`, `strip_script_leakage`, `without_internal_words`, the `[ctx]` guard (`context.disarm`), `context.clarification_used` and `repairs._without_clarification` (exact client strings), the after framework question lookup in `context.py` (exact client strings), `_without_their_name` (their stored nickname), `_asks_them` and `_without_sentences` (a sentence ending in `?`), `first_sentence` and `with_the_check_in` (punctuation), `reply_checks.repeats` and the "asks no question" check (log only), and `find_tapped_prompt` and `chosen_style` (matching stored button labels).

**Security model**: Unchanged. A framework id from the model (`heading_toward`) is untrusted until it matches the registry. Slot values are inserted into fixed templates as plain text and never interpreted. Logs follow `send_default_pii=False` practice.

**Configuration required**: None. A reseed is required after the `somatic.md` id edit (`python scripts/seed.py`).

**Critical test scenarios** (scripted model, `tests/unit` and `tests/integration/test_turn.py`):
- `context.moment` returns each moment for its state, including a concern (concern), a Try it tap (in_stages), an offered row with no buttons showing (offer_open), the closing phase (body), `somatic_practice` without place buttons (not body), and retirement (body). Verifies **AC-1**.
- A `chatting` turn before the window gets a schema with no `offer` field. A `chatting` turn on a declined row gets `offer_answer`, `state` and `stages_known`. Verifies **AC-1**.
- A supportive offer is the client's two lines word for word with the slots filled, then the permission question and the three buttons, with none of the model's `text`. A directive schema has no `lead_line`. Quotes and trailing punctuation in a slot are stripped. Verifies **AC-2**.
- An empty `going_through`, a null or unknown `heading_toward`, the framework they finished, or a framework with no template is dropped. The model's text is sent, no offered row is written and the miss is logged. Verifies **AC-3**.
- Each answer:
  - yes starts the framework and its step is corrected from its ledger.
  - no sends the Keep chatting line, and an empty `their_words` sends the text and logs.
  - moved_on, null and an off-list value each decline and keep the model's text.
  - asked sends explain with two buttons and keeps the row offered.
  - A Keep chatting tap with `offer_answer: yes` still declines.
  - A yes on a declined row starts it.

  Verifies **AC-4**.
- Each `body` value at a valid phase sends its branch. `agreed` in the directive style and `chest` on a retiring turn are ignored and logged. A tap on "Head" gives the head practice whatever `body` says. Verifies **AC-5**.
- The handoff appears for declined, acting and retirement, and not when the reply text says "keep chatting or go to the library" on its own. Verifies **AC-6**.
- One provider call per turn across the scenarios above. Verifies **AC-8**.
- A test composes the supportive ABCDE system prompt and serializes the `offer_open` schema, then asserts the total is below a recorded figure from before the change. Verifies **AC-9**.
- A log capture on an offer turn contains the moment and framework id and none of the slot text. Verifies **AC-10**.
- `scenario_check.offer_words_in_text` flags offer wording in `text`, as a pure unit test. Verifies **AC-11**.
- On a screen concern the schema has no offer or body fields. With a model `crisis` on an `offer_open` turn answering `yes`, or on a body turn answering `chest`, only the text is sent and the row is unchanged. Verifies **AC-12**.

## Build plan

Tracer Bullet: the offer thread goes end to end first, then the body thread, then the cleanup. The suite is green after each slice.

**Slice 1: offer thread**
1. Before any change, record the AC-9 figure (supportive ABCDE system prompt plus `Reply` schema characters) in the test, satisfies **AC-9**.
2. `context.moment` and the `Moment` enum (including `concern`), with unit tests, satisfies **AC-1**, **AC-12**.
3. `schema.reply_for` factory: the `Offer` model, `offer_answer`, `their_words`, slot descriptions from the style's placeholders, the `Literal` plus lenient validator, and `state` without `accepted`. `ReplyWithoutOffer` stays only until slice 3, satisfies **AC-1**, **AC-4**.
4. `repairs.render_template` and offer composition from slots and `heading_toward` (the rendered offer is the whole text, replacing the free text path in `_compose_offer`), with the AC-3 drop rules and an `offer_dropped` reason, satisfies **AC-2**, **AC-3**.
5. Orchestrator wiring:
   * choose the schema by moment;
   * taps first, then `offer_answer` drives the outcome (replacing the `state.accepted` branches and both `"?" in content` checks, with any other answer declining);
   * move `with_ledger_step` after the answer is resolved, so a typed yes is corrected too;
   * render Keep chatting and explain;
   * run the concern and `crisis` guard before any rendering;
   * log the moment and enums.

   Satisfies **AC-1**, **AC-4**, **AC-8**, **AC-10**, **AC-12**.
6. Rewire `reply_checks.offered` and `misses` to the rendered offer in `Repaired`, not `Reply.prompts`, and log `offer unusable: <reason>` from `offer_dropped`, satisfies **AC-3**.
7. Prompt cuts: the offer writing guidance and the button line in `response_format.md` and `mani_base.md`, and the `state.accepted` lines in `context._MEANING`. The Framework Index stops printing the offer and Keep chatting templates, since the slot descriptions carry them. Then reseed, satisfies **AC-9**.
8. `scenario_check.offer_words_in_text` and its flag in the run output, satisfies **AC-11**.

**Slice 2: body thread**
9. Add `id:` to each `if_unclear` branch in `somatic.md`, reseed, switch `practice_for`, `returning_reply` and the pain lookup to ids, and have `cache.load` refuse content without the ids, satisfies **AC-5**.
10. `context._stage_lines` shows each body branch as its `id` and `when` only, not the client's full practice text, which code now sends itself, satisfies **AC-5**, **AC-9**.
11. The `body` moment and `_body_route_step` rewritten on the `body` value (taps first) per the transition table, with the check-in question still placed by code, satisfies **AC-5**, **AC-12**.
12. Handoff from the branch or from retirement, replacing `_ASKS_WHAT_NEXT` at its three call sites, satisfies **AC-6**.

**Slice 3: cleanup**
13. Delete the `prompts` field, the button filter loop in `repairs.apply`, `ReplyWithoutOffer`, `_PLACE_WORDS`, `named_place`, `declines_or_acts`, `comes_back`, `_OFFER_WORDS`, `_without_permission_question`, `_OFFER_SENTENCE`, `practice_in`, `_says_name`, `_ASKS_WHAT_NEXT`, and the tests that covered only them, satisfies **AC-7**.
14. Edit in place in `backend/PORT-STATUS.md`: "No phrase lists judge the conversation", "A turn is one chat call" (the `ReplyWithoutOffer` mention), "An open offer is read from the database", and "An offer is one short line that names its framework" (now the client's template). Add a journal note, and update the requirements row for R1, R3 and R9, satisfies **AC-7**.
15. After muhammad's yes: one `scenario_check` run in all three styles, satisfies **AC-11**.

## Consequences

**Positive**:
- Offers, Keep chatting and the body route read exactly as the client wrote them, in each style.
- About 150 lines of regex and repair code go, and the model's judgments become countable in the logs.
- The model can no longer offer before the window or name a body place outside the body route. The schema has no field for it.

**Negative / tradeoffs**:
- An offer the model writes into `text` is no longer stripped at runtime. It is only measured by `scenario_check`.
- Offers lose the model's own phrasing outside the slots. If the client's template reads stiffly in a case, only the client's text can fix it.
- The schema factory and the moment function must change whenever the stage machine changes.
- On an offer, a no, and the whole text body branches, the model's acknowledgement of what they just said is not sent. The client's line is the whole reply, as the practices already are today. If the client wants a reflection before these lines, that is a content change.
- On an `offer_open` turn the model writes `text` that is thrown away whenever the answer is `no` or `asked`. That costs a few output tokens.
- The schema differs between turns, so the schema part of the prompt caches less well. Prompt prefix caching of the system prompt is unaffected.
- A turn where the model leaves a needed slot empty loses its offer for that turn.

**Neutral**:
- `somatic.md` gains ids, and the paused frameworks must give their `offer` and `keep_chatting` templates the same slot shape before they return.
- Tests built on `state.accepted` and model buttons are rewritten, not just deleted.

## Migration plan

**Strategy**: no data migration. A single deploy per slice, with the content reseed in the same deploy.
**Phases**: slices 1 to 3 above, each shippable alone.
**Rollback**: revert the slice's commit and reseed the previous content.
**Risks**: the deploy and the reseed drift apart. Code expecting branch ids against unseeded content would miss every branch, so slice 2 checks for the ids at load (`cache.load`) and refuses to start without them.

## Follow-up

- [ ] The live run in AC-11 is owed and needs muhammad's yes (it spends the client's credit).
- [ ] `.claude/BACKEND.md` still says "A turn is one model call, or more when a draft has to be asked for again". It is stale since feature 13, and `/sync` owns that file.
- [ ] Decide separately whether `strict=True` structured output is worth turning on for every call.
- [ ] When a paused framework returns, check its `offer` and `keep_chatting` templates for the slot shape this spec assumes, and design the `grounding` ending stage (in `ENDING_STAGES`, used only by paused frameworks), which this spec leaves in `in_stages`.
