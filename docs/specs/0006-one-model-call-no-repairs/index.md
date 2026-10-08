# 0006. One model call per turn, with integrity guards and no reply repairs

**Date**: 2026-10-07
**Status**: In Progress
**Decision record**: [rationale.md](rationale.md) (context, options considered, rationale)

## Summary

Every chat turn makes exactly one model call, and the reply goes to the person as the model wrote it. The redraft loop (asking the model again when a draft broke a rule) and the code that rewrites replies (cutting feeling sentences, removing their name, building the offer from the client's text, dropping buttons) are removed. What stays is a small set of integrity guards (checks that stop a bad id or value from the model reaching the database or the app), plus the body check in code that feature 7 owns. The model is told the offer timing and the grief veto in `[ctx]` (the block of turn facts sent with every message) instead of being corrected afterwards.

## Requirements

**User stories**:
- As muhammad, I want every turn to cost one model call, so a turn is cheaper and faster and its cost is predictable.
- As someone talking to Mani, I want to read what Mani actually wrote, whole, rather than a reply with sentences cut out or text bolted on.
- As a maintainer, I want the code after the model call to only guard stored state, so a prompt change is the one place behaviour is tuned.

**Acceptance criteria**:
- **AC-1**: Every chat turn makes exactly one chat provider call when the reply parses, whatever the draft contains: a feeling word they never used, no question, the question asked last turn, an offer while `cooldown_passed: no`, an offer of a framework in `ruled_out`, or no offer while `closest_fit: due`. `mani/chat/redraft.py`, `context.with_rewrite_notes` and every `rewrite:` line in `[ctx]` no longer exist.
- **AC-2**: A chat reply that does not parse raises the existing retryable `LLM_UNAVAILABLE` error after one attempt, recorded as one `schema_invalid` row, and the turn stores nothing. A provider blip on a chat call (`InternalServerError`, `APIConnectionError`, not a timeout) is still retried once. Every other call purpose (summary, memory fold, exercise pick, voice translation) keeps today's one schema retry.
- **AC-3**: The reply text stored and returned is the model's `text` with only surrounding whitespace removed. No sentence is removed or added for a feeling word, their name, a repeated clarification question, leaked script markers, an offer's words, the client's framework description or a permission question. The one exception is the body ending owned by feature 7 (the check in script, the practice for a place, the returning reply).
- **AC-4**: Buttons are stored as the model sent them, in its order, with its labels, with no count cap and no duplicate removal. The only changes are the integrity guards, applied in this order:
  1. A button with an empty label is dropped.
  2. A button whose `technique` is not in the registry (matched after `_normalize`) is dropped.
  3. A button with any `technique` is dropped while a framework is running.
  4. A button with any `technique` is dropped on a turn whose outcome is a decline (Keep chatting, typed or tapped) and on a turn that retires a finished framework (`retiring_framework_id` set). Otherwise its OFFERED row would overwrite the decline or cancel the retirement.
  5. Every `technique` button is dropped on a safety concern turn (unchanged, in the orchestrator).
  6. When any of these drops a `technique` button, the offer's other buttons go with it (a `decline` button, and a label in `EXPLAIN_LABELS`), so no button is left pointing at an offer that is not there.
  7. A `library` value maps to its canonical `LibrarySection` spelling, and an unknown one to `home`.

  The body ending buttons owned by feature 7 (Chat More, Go to Library, the place labels) are unchanged. `threads.library_offered` is set only by the Chat More / Go to Library handoff the orchestrator writes (`_handoff()`), never by a library button the model sends.
- **AC-5**: The state guards hold as today: `state` naming a framework not in the registry, or one other than the running framework, is ignored. The reported stage is validated and clamped with `Registry.validate_transition` and `Registry.clamp`, including the rule that the yes turn may already be on the second stage. A `style.shape` off the `SHAPES` list is dropped. The title goes through `clean_title` unchanged (quotes and a trailing period stripped, trimmed to 100 characters). A reply whose text is empty raises the retryable error and stores nothing. Each guard that fires adds a note to one logged line. A note names the guard and the field (`dropped a technique button: not in the registry`), never a value the model or the person wrote.
- **AC-6**: Offer timing is told, not enforced. An offer made while `cooldown_passed: no`, outside the closest fit window, or of a framework already finished, is stored and shown as the model wrote it. On a decline turn or a retiring turn, the offer's words are shown as written and its buttons are dropped by the AC-4 guard, so the stored state stays the decline or the retirement. The `cooldown_passed`, `closest_fit` and `this_thread` lines in `[ctx]` are unchanged.
- **AC-7**: When `router.vetoes` finds a phrase from a framework's `never_offer_when_said` in the person's messages within the context window (the last 20 messages plus this one, the same window as today), the orchestrator removes that framework from the shortlist before it picks the offer candidate. `router.is_confident` and the candidate then work on the filtered list, so the offer goes to the next framework if it is confident, or to none. `[ctx]` carries one line `ruled_out: <id>[, <id>]` on every turn where no framework is running (by `context.build`'s own `running` rule) and there is no safety concern, whether or not a shortlist is shown. `mani/chat/router.py` and `tests/unit/test_router.py` are unchanged.
- **AC-8**: The Framework Index carries each framework's client description as one line, `Description: <summary>`, directly under its heading and before its eight lines. A framework with an empty summary gets no description line. The index's closing sentence no longer says the description is added for the model. It says to describe the questions in fresh words from that line when offering, and keeps "never its name, its id, or the word framework".
- **AC-9**: The `offers` rules in `mani_base.md` say the model writes the whole offer. That means one sentence in their words showing it understood, what the questions would help with taken from the description in fresh words, and one question asking if they want to try, in the style, with the same two buttons. They also say never to offer one that `ruled_out` names. A closest fit offer keeps `offer_fit: closest`, and the model words it and labels its button itself (there is no fixed "Try the closest fit" label). In `response_format.md`, the `rewrite:` entry is deleted and a `ruled_out:` entry says the frameworks named there may not be offered in this conversation. No prompt file, schema description or code comment in `backend/mani/` says the description or the permission question is added by the backend, or mentions a redraft or rewrite notes.
- **AC-10**: `mani/chat/repairs.py` becomes `mani/chat/guards.py`, whose `check()` returns `Checked` (defined in `guards.py`, and also the type `_body_route_step` takes and returns) and holds only the guards in AC-4 and AC-5. The body ending helpers (`with_the_check_in`, `PLACE_LABELS`, `named_place`, `declines_or_acts`, `reply_for`, `practice_for`, `practice_in`, `first_sentence`, `comes_back`, `returning_reply`) move unchanged to `mani/chat/ending.py`, which imports nothing from `guards.py`; `context.py` imports `reply_for` from it. `FEELING_WORDS`, `SELF_JUDGMENTS`, `MAX_CAPSULE_WORDS`, `WORD` and `words()` move to `tests/evals/vocabulary.py`, and nothing in `backend/mani/` imports them. `PERMISSION_QUESTIONS`, `CLOSEST_FIT_LABEL`, `SCRIPT_LEAKAGE`, `_compose_offer`, `introduced_feelings`, `without_feeling_sentences`, `MAX_PROMPTS`, `ENDING_STAGES` and the other text and button helpers are deleted. `EXPLAIN_LABELS` stays in `greeting.py` for the AC-4 pair guard. `Reply.offer_fit` stays: it is generated before `text` and shapes how the model words a closest fit offer. The orchestrator code that only fed removed checks goes: `clear_ok`, `closest_ok`, `framework_going`, `needs_question`, the `name_said_before` block and `_finished`.
- **AC-11**: The whole `pytest` suite passes with the integration tests running against the local database (not skipped), with no warning (`pytest.ini` sets `filterwarnings = error`) and no error log a test does not capture and assert. Tests that assert a removed behaviour (a redraft, a text edit, a button policing rule, an offer timing drop, offer composition) are deleted. The new tests are the ones listed under Critical test scenarios.
- **AC-12**: `backend/PORT-STATUS.md`, "Decisions in force", has its first line edited in place to say a turn is one chat call, a malformed chat reply is not retried, and the exercise pick is the one scoped extra call. In `docs/scope/scope.md`, feature 5's Done when no longer names the ABCDE replay. No text in `backend/` (outside the dated `docs/ai-layer-audit.md`) or in the scope still describes a redraft or reply repairs as current behaviour.

## Decision

**Chosen option**: Option 2: Remove the redraft and every reply edit, keep integrity guards.

Each chat turn makes one call with no schema retry, the reply goes out as written apart from the integrity guards and feature 7's body ending, and offer timing and the grief veto are told to the model in `[ctx]`.

## Feature design

**Data model sketch**: no schema change and no migration. `admin.frameworks.summary` already holds each framework's description and is read by the index. `public.thread_technique_state` is written exactly as today, behind the same guards.

**State transitions**: unchanged. `offering` → accepted → each id in `phases` → `closing` → `somatic_checkin` → `somatic_practice` → retired. A decline sets the outcome to declined, and Keep chatting on an open offer is still a decline (orchestrator logic, not a repair).

**API surface**: no HTTP change. `POST /v1/threads/{thread_id}/messages` keeps its request and response models. A malformed chat reply now returns the existing `LLM_UNAVAILABLE` error shape (`retryable: true`) after one attempt instead of two. The internal seams that change:

| Seam | Change | Inputs | Outputs | Failure |
|---|---|---|---|---|
| `mani/llm/client.py::complete` | new keyword `retry_malformed: bool = True`; when `False`, a schema failure on any attempt raises once its row is recorded, with the message "model returned no parseable reply" (no attempt count); the provider blip branch is unchanged | as today plus the flag | `Call` | `ServiceError(LLM_UNAVAILABLE, retryable=True)` |
| `mani/chat/orchestrator.py::send` | one `client.complete(..., retry_malformed=False)`; the `_why` loop and the `redraft` import go, along with `clear_ok`, `closest_ok`, `framework_going`, `needs_question`, the `name_said_before` block and `_finished`; computes `ruled_out` and filters the shortlist before the candidate; calls `guards.check`; sets `library_offered` only from `_handoff()` | | | empty text raises as today |
| `mani/chat/redraft.py` | deleted | | | |
| `mani/chat/context.py::build` | new parameter `ruled_out: list[str]`, rendered as `ruled_out:`; receives the already filtered shortlist and candidate; `with_rewrite_notes` deleted; the `cooldown_passed` docstring no longer says repairs enforce it | `TurnContext`, shortlist, `ruled_out` | `[ctx]` text | none |
| `mani/chat/guards.py::check` | the integrity guards of AC-4 and AC-5 | reply, registry, `current_framework_id`, `current_phase`, `accepted_this_turn`, `framework_running`, `declined` (outcome is a decline this turn), `retiring` (`retiring_framework_id` is set), `wants_title` | `Checked(text, prompts, title, framework_id, phase, style, notes)` | none |
| `mani/chat/ending.py` | the body ending helpers, moved unchanged | | | |
| `mani/prompts/composer.py::framework_index` | a `Description:` line per framework; new closing sentence | `Registry` | index text | none |
| `content/prompts/response_format.md` | `rewrite:` entry deleted, `ruled_out:` entry added | | prompt text | |
| `tests/evals/vocabulary.py` | the word lists and `words()`, moved | | | |
| `scripts/eval_replies.py` | captures `checked reply` lines as `guard_notes` and prints them as `[guard]` | | | |

**Value sourcing**:

| Action | Value produced / displayed | Source |
|---|---|---|
| Chat turn | the reply text | the model's `text`, stripped of surrounding whitespace (body ending: `ending.py`, feature 7) |
| Chat turn | the buttons | the model's `prompts`, after the AC-4 guards |
| Chat turn | stored framework and phase | the model's `state`, after the AC-5 guards and `Registry.clamp` |
| `[ctx]` | `ruled_out` ids | `router.vetoes(activation, user_texts)` for every `registry.activations` entry with `never_offer_when_said`; `user_texts` is the user messages in `messages_db.recent_for_context` (the last `CONTEXT_WINDOW` = 20 messages) plus this one, as today |
| Orchestrator | the offer candidate | the top of the shortlist after the `ruled_out` ids are removed, under today's `is_confident` and `closest_fit_due` rules applied to that filtered list |
| Guards | `declined`, `retiring` | the orchestrator's `outcome is TechniqueOutcome.DECLINED` and `retiring_framework_id is not None` |
| Thread update | `library_offered` | set only when the orchestrator wrote the `_handoff()` buttons this turn |
| `[ctx]` | `cooldown_passed`, `closest_fit`, `this_thread` | unchanged: `context.cooldown_passed`, `closest_fit_due`, `closest_fit_ok`, `thread_technique_state` |
| Framework Index | `Description:` line | `admin.frameworks.summary`, whitespace collapsed |
| Model reply | the offer's description and permission question | written by the model from the `Description:` and `Offer:` lines and the conversation style |
| Chat call | whether a schema failure retries | `retry_malformed=False` at the chat call site |
| Log | guard notes | the guards that fired, naming the guard and the field only, never a value |

**Key invariants**:
- One chat provider call per turn whose reply parses. The exercise pick at the end of a framework is the only other call in a turn.
- No code in `backend/mani/` adds, removes or replaces a sentence of the model's reply, except `ending.py` for the body ending (feature 7).
- No model supplied framework id, stage, library section or style shape is stored without passing its guard.
- `[ctx]` never names the same framework on both `offer:` and `ruled_out:`.
- A model button never changes stored state on a decline or retiring turn: the decline and the retirement are what get written.
- No button is left pointing at an offer whose technique button was dropped.
- `library_offered` reflects only the handoff the orchestrator wrote.
- The Framework Index stays in the cached prefix: the description line is static per framework.

**Security model**: no change in who may read or write what. The guards are the security relevant part. They treat every id the model returns as untrusted until it matches the registry, so a model reply cannot write a framework or stage that does not exist into `thread_technique_state`. The safety screen, the crisis lock and the safety concern pause are untouched (feature 10). Conversation content is health data, so guard notes name the guard and the field only, never a value the model wrote (a library value has been seen carrying a topic phrase) or anything the person said.

**Configuration required**: none. `content/prompts/mani_base.md` changes, so it is reseeded with `python scripts/seed.py` in the same deploy as the code.

**Critical test scenarios** (scripted model, real database for the integration tests; no mocks of our own code):
- Integration: for each draft that used to be redrafted (a feeling word they never used, no question, last turn's question, an offer while the cooldown has not passed, an offer of Behavioral Activation after loss words, no offer while the closest fit is due), the turn records exactly one chat `llm_calls` row and stores the text exactly as scripted. Verifies **AC-1**, **AC-3**, **AC-6**.
- Unit, client: a chat call with `retry_malformed=False` whose reply does not parse raises `LLM_UNAVAILABLE` after one attempt with one `schema_invalid` row, and a provider blip on the same call is retried once. The existing retry tests keep covering the default. Verifies **AC-2**.
- Unit, `context.build`: given `ruled_out=["behavioral_activation"]` and no running framework, it renders `ruled_out: behavioral_activation`, also with an empty shortlist. With a framework running, or a safety concern, there is no `ruled_out` line. Verifies **AC-7**.
- Integration, veto: in the "offer of Behavioral Activation after loss words" case above, with Behavioral Activation top of the shortlist, the `[ctx]` the scripted model received (`ScriptedModel.last_messages`) carries `ruled_out: behavioral_activation` and names no `offer: behavioral_activation`. Verifies **AC-7**.
- Integration, state guards: a typed Keep chatting reply on an open offer, scripted with a technique button, stores the decline (outcome declined) and no button. A retiring turn scripted with a technique button retires the framework, and the reply carries the handoff only. A mid framework reply scripted with a library button leaves `library_pending: yes` on the next turn. Verifies **AC-4**, **AC-6**.
- Unit, guards: a technique button dropped as unknown takes its Keep chatting and Tell me about this buttons with it, and an empty label is dropped. Verifies **AC-4**.
- Unit, `composer.framework_index`: two frameworks render a `Description:` line from their summaries under their headings, one with an empty summary renders none, and the closing sentence says nothing about a description being added. Verifies **AC-8**.
- The existing guard tests (unknown technique, state for another framework, phase clamp, the yes turn, library section, style shape, title) move to `tests/unit/test_guards.py` and pass. The body ending helper tests (`named_place`, `practice_for`, `comes_back`, `with_the_check_in`, `first_sentence`) move to `tests/unit/test_ending.py`. The empty reply integration test scripts an empty `text` directly. The answered offer test in `test_turn.py` (about line 832) finds the offer by its technique button rather than `PERMISSION_QUESTIONS`, since the behaviour it checks stays. Verifies **AC-4**, **AC-5**, **AC-10**.

## Build plan

Tracer Bullet: the one call turn goes through end to end first, then the offer, then the guards.

1. One call end to end: add `retry_malformed` to `client.complete` and pass `False` from the chat turn. Delete the `_why` loop, `needs_question` and `redraft.py`, and remove `redraft.ruled_out` from the `cooldown_passed` argument. Delete `context.with_rewrite_notes` and the `rewrite:` entry in `response_format.md`. Compute `ruled_out` in the orchestrator and filter the shortlist before the candidate is picked. Render `ruled_out:` in `context.build` and add its `response_format.md` entry. Add the client test, the `context.build` test, and the integration one call and veto tests. Satisfies **AC-1**, **AC-2**, **AC-7**.
2. Offer in the model's words: add the `Description:` line and the new closing sentence to `framework_index`, and rewrite the `offers` rules in `mani_base.md` (whole offer, closest fit, `ruled_out`). Delete `_compose_offer`, `_without_permission_question`, `PERMISSION_QUESTIONS` and the offer sentence cuts, and switch the answered offer test off `PERMISSION_QUESTIONS`. Fix the comments in `context.py` and `composer.py` that say the backend adds the description. Add the composer test, then reseed both prompt files. Satisfies **AC-8**, **AC-9**, **AC-3**.
3. Guards only:
   - Rename `repairs.py` to `guards.py` (`check`, `Checked`), keeping only the AC-4 and AC-5 guards, and add the decline or retiring guard and the offer button pair guard.
   - Set `library_offered` only from `_handoff()`.
   - Delete the text edits, the button policing, the cooldown, closest fit and already offered drops, `CLOSEST_FIT_LABEL`, `MAX_PROMPTS` and `ENDING_STAGES`, and the orchestrator code that fed them (AC-10).
   - Move the body ending helpers to `ending.py` and the word lists to `tests/evals/vocabulary.py`.
   - Update every import: `orchestrator.py`, `context.py`, `tests/integration/test_turn.py`, `tests/evals/validators.py`, `tests/evals/test_negative_set.py`, and the `router.py` and `routers/messages.py` docstrings and `schema.py` comments that name `repairs`.
   - Switch the log line to `checked reply`, and `eval_replies.py` to `guard_notes` and `[guard]`.
   - Add the state guard integration tests and the guard unit tests.

   Satisfies **AC-3**, **AC-4**, **AC-5**, **AC-6**, **AC-10**.
4. Tests and docs:
   - Delete `tests/unit/test_redraft.py` and every unit and integration test asserting a removed behaviour. Move the guard tests to `test_guards.py` and the body ending helper tests to `test_ending.py`, and rescript the empty reply test.
   - Run the whole `pytest` with the local database up, and check the count of integration tests run.
   - Edit the PORT-STATUS decision line in place, and the PORT-STATUS lines that describe the redraft and repairs pipeline.
   - Edit feature 5's Done when and the scope lines (feature A and feature 5's intent) that name redraft and repairs.
   - Fix the remaining stale text: `content/frameworks/behavioral_activation.md` line 8 (reseed), `schema.py` line 29, the `test_baseline.py` docstring, and the orchestrator comment on `user_texts`.
   - Add a journal note.

   Satisfies **AC-11**, **AC-12**.

## Consequences

**Positive**:
- A turn is one call. Redrafted turns (two or three calls today) and malformed chat replies (two) stop paying twice, and their latency drops with it.
- The person reads what Mani wrote, whole. No more replies with a sentence missing or an offer stitched from three sources.
- About 700 lines of regular expressions, word lists and their tests leave `backend/mani/`, and behaviour is tuned in one place, the prompts.

**Negative / tradeoffs**:
- No backstop. An early offer, a feeling they never named, their name used twice or a repeated question now reaches the person whenever the model slips. Only the evals would show how often, and none are run for this feature.
- When a guard drops a `technique` button (an unknown id, a running framework, a decline or retiring turn, a safety concern turn), the offer's words stay with no button under them. Its companion buttons go too, so nothing points nowhere, but the words read as an open question. Today's repair cut those words. A typed yes to such words starts nothing, because no offer was stored. The guard note logs each case.
- A malformed chat reply now reaches the person as an error to retry. The app can resend with the same `client_message_id`, but the person sees a failure where today a second call hid it.
- The client's permission questions and description are no longer sent word for word.
- Quality after this change is unmeasured: there is no real run and no after baseline.

**Neutral**:
- No migration. A reseed is needed for `mani_base.md`.
- `ending.py` is a holding place until feature 7 redesigns the body ending.
- `tests/evals/` now owns the feeling word and judgment lists that only checks read.

## Migration plan

**Strategy**: no migration needed. Code and the reseeded `mani_base.md` ship in the same deploy, as spec 0005 already requires for the frameworks.
**Rollback**: revert the commit and reseed. No stored data changes shape.
**Risks**: the new code on the old `mani_base.md` and `response_format.md` would tell the model the description is added for it while nothing adds it, so offers would arrive with no description and no permission question, and the model would read no meaning for `ruled_out:`. Reseed in the same deploy.

## Follow-up

- [ ] `/sync`: `.claude/BACKEND.md` still lists `redraft.py` and `repairs.py` under Layout and says "A turn is one model call, or more when a draft has to be asked for again" under Conventions.
- [ ] Before this reaches hosted traffic, check the share of chat rows in `admin.llm_calls` with outcome `schema_invalid`. That share is now the share of turns the person sees fail.
- [ ] No real run proves quality here. Feature 11 (tuning from measurements) is where an after baseline against `after-lean-frameworks` would first show what this change cost in findings.
- [ ] Spec 0005 AC-3 says the index carries name, id and eight lines. This spec adds the `Description:` line beside them.
- [ ] Feature 7 inherits `mani/chat/ending.py` and the body ending text edits AC-3 leaves in place.
- [ ] Feature 10: the orchestrator logs the model's free text `crisis.reason` (`model reported a safety concern on thread …`), which is health data in a log line. Out of this spec's reach. Decide it with the crisis work.
- [ ] The veto reads only the last 20 messages, so a loss said earlier in a long thread stops ruling Behavioral Activation out. That is today's limit too. Revisit with the open "grief veto" decision in PORT-STATUS.
