# 0013. The offer in the client's words

**Date**: 2026-10-08
**Status**: In Progress
**Decision record**: [rationale.md](rationale.md) (context, premise notes, options considered, rationale)

## Summary

Today the model writes each offer of a set of questions in its own words, with two buttons, Try it and Keep chatting. The client wants every offer to show the same words, the framework's name and its description from the client's intro document, with three buttons: Yes, let's try it · Tell me more · I want to keep talking. A model cannot copy text exactly every time. So the model still decides when to offer and which set, and the code writes the offer from seeded rows (rows loaded into the database from `backend/content/`), so a reseed changes any of it. Tell me more shows the name and description again until the client gives its own wording, and the chat tester hides the text field while an offer is open.

## Requirements

**User stories**:
- As a person talking to Mani, I want an offer to tell me plainly what the questions are and what I will come away with, so I can choose.
- As a person shown an offer, I want to say yes, ask for more or keep talking with one tap, and not have to type.
- As muhammad, I want the offer's words, names, descriptions and button labels in seeded content, so changing them needs only a reseed.

**Acceptance criteria**:

- **AC-1**: `backend/content/prompts/replies.md` has an `offer` block exactly as drafted in *Feature design*: `text`, `more_text` and `labels` with the keys `accept`, `more` and `decline`. `mani/prompts/replies.py` parses it into an `Offer` model on `Replies` that refuses a row in four cases: a missing `offer`, a `text` or `more_text` that does not carry both `{name}` and `{description}`, a `text` or `more_text` that carries any other field, or a blank label or two labels that match ignoring case. The refusal happens wherever `Replies` is checked today (seed, admin write, cache load). `tests/unit/test_config_rows.py` gains these refusal cases in its existing `REPLIES_REFUSED` style.
- **AC-2**: The `name:` and `summary:` of the six files in `backend/content/frameworks/` are exactly the table in *Feature design*: the client's names and descriptions from the intro .docx, word for word, except that "This Framework" is written "This framework". `scripts/seed.py` refuses a framework whose `summary` is missing or blank.
- **AC-3**: No framework file has an `Offer:` line. `FRAMEWORK_LABELS` in `scripts/seed.py` is the seven labels without `Offer`, so the seed accepts the six files and refuses a body that still has eight lines. Every comment, docstring and test name that says a framework has eight lines says seven: `scripts/seed.py`, `mani/prompts/composer.py` (`framework_index`), `mani/models/rows.py`, `tests/evals/test_negative_set.py`, `tests/unit/test_composer.py` (the docstring near line 190 and the test named `..._eight_lines` near line 86) and `tests/unit/test_seed_frameworks.py` (its `ABOUTME` line, which says "eight labelled lines", and the tests named `..._eight_lines` near lines 42 and 120).
- **AC-4**: An offer is written by the code, by one rule: whenever the reply still carries a button with `technique` after `guards.check`, the safety concern and the ending checks in `orchestrator.py`, it is an offer. Then the text sent and stored is `offer.text` with `{name}` filled from that framework's `name` and `{description}` from its `summary`, whitespace collapsed the way `composer.framework_index` does (`" ".join(summary.split())`). None of the model's `text` is sent or stored. The replacement happens before the empty text check (`if not checked.text`), so an offer turn never fails on text it throws away. The model's `style` is not recorded on that turn (`updates.style` stays unset), because the person never saw that text. The stored `prompt_options` are exactly, in order, `{label: accept, technique: <id>}`, `{label: more, more: true}` and `{label: decline, decline: true}`, and every other button the model sent is dropped. The returned `prompts` show the same three labels in that order. The offer's state row, the offer log and the `cooldown_passed` log line work as today.
- **AC-5**: A Tell me more tap makes no model call. A tap is a message matching, ignoring case, the label of a stored option with `more: true` on Mani's newest message whose pending offer's framework is in the registry. The reply is `offer.more_text` filled the same way, stored with `selected_prompt` set to the stored option's label. Its stored options are `{label: accept, technique: <same id>}` and `{label: decline, decline: true}`, and the returned `prompts` show those two labels. The thread's technique row is not touched, so it stays offered on the `offering` phase. The returned `Turn` sets `crisis_blocks_chat` from `settings.crisis_blocks_chat` (as the model path does), `title` from the thread, `was_duplicate` from the stored pair, `llm_call_id` to none and `needs_summary` to false; a summary that falls due is picked up on the next turn, because that check is `>=`. A tap on Yes, let's try it after it starts the framework exactly as a tap on the offer does today.
- **AC-6**: Typed text while an offer is pending is handled as today (`offer_waiting`, `state.accepted`, `asked_about_it`), and AC-4's one rule decides what is sent: when the reply carries a technique button that survives the checks, the full offer goes out again with its three buttons and the model's text is dropped; when it does not, it is a decline and no buttons go out, as today. No client reaches this path while the field is hidden (AC-9); it stays for any client that still sends text.
- **AC-7**: When the guards drop the technique button, a safety concern removes it, or the ending clears the buttons, there is no offer: the model's text goes out as written, with no offer buttons, exactly as today.
- **AC-8**: In `backend/content/prompts/mani_base.md`, `offers` lines 1, 2 and 5 are exactly the drafts in *Feature design*, and lines 3 and 4 are byte for byte unchanged. In `backend/content/prompts/response_format.md`, four lines change, and each is exactly its draft: the `prompts` field, the `state` field (only "which is Keep chatting" becomes "which is I want to keep talking"), the `buttons` line 1 and the `layers` `Framework Index` line. No other line of either file changes. In `backend/content/prompts/tuning.md`, the comment "After \"Keep chatting\"" says "After \"I want to keep talking\"". muhammad reviews these drafts before the reseed.
- **AC-9**: In `chat-tester/app.py`, the whole `st.container(key="composer_bar")` block (the text area, Send and the mic) is not rendered while Mani's newest message carries a button with `technique` set, and `show_recorder` is reset to false then, so an open recorder does not come back on the next render. It shows again after any reply without one. The Enter key script already does nothing when the bar is absent. The backend's API does not change.
- **AC-10**: The old labels are gone from what the code and tests treat as offer buttons. Every `Try it` and `Keep chatting` button built in `tests/` becomes `Yes, let's try it` and `I want to keep talking`, except the decline word cases in `tests/unit/test_schema.py`, which test what the model may write and stay. `scripts/eval_conversations.yaml`'s `@tap:Keep chatting` becomes `@tap:I want to keep talking`, and its comment near line 194 that quotes "Try it" names the new label. `chat-tester/README.md` (near lines 15 and 105) names the new labels. The docstrings and comments in `mani/chat/guards.py` and `mani/chat/orchestrator.py` that name the old labels name the new ones. The `mani/llm/schema.py` docstring stays: it records what the model was seen writing, which is still true.
- **AC-11**: After the reseed, the whole `pytest` passes with pristine output. The builder records the passed and skipped counts before and after, and checks that the integration tests were not skipped. No real model conversation is run for this spec.
- **AC-12**: In the same change, `backend/PORT-STATUS.md` is edited in place, and three edits are made:
  - Decisions in force: "The reply goes out as the model wrote it" now names the one exception (an offer's text and buttons, and the Tell me more reply, are written by the code). "The lines Mani sends without the model live in the `replies` row" now includes the offer and Tell me more.
  - The client list gains two lines: the shared lead on every offer, and the interim Tell me more.
  - Scope feature 15's row links this spec.

  `.claude/BACKEND.md` line 65 ("the reply goes out as the model wrote it") names the same exception, and its `chat/` layout line names `offer.py`. The `send` docstring in `mani/routers/messages.py` that says the same thing is corrected. A journal note records the before and after counts and anything learned.
- **AC-13**: `scripts/eval_replies.py` does not run `validators.says_framework` or `validators.check` on a reply the code wrote: an offer (a turn whose `prompts` carry a technique button) or the answer to a Tell me more tap. Otherwise the name in "Framework: <name>" and "overwhelming" in the lead (`tests/evals/vocabulary.py`) would flag every offer and skew the baselines. The model's replies are checked as today.

**Not in this spec**:
- The real Tell me more wording. It gets its own spec once the client provides it; until then it shows the name and description.
- What Mani says after Yes, let's try it. The model writes it as today, guided by the style lines.
- Web and mobile. Neither is wired to the API yet; when they are, they hide the field the way AC-9 does.
- The greeting's text field. Nothing hides it today, and this spec does not change that.

## Decision

**Chosen option**: Option 1: the code writes the offer and its buttons from seeded rows, and the model only decides when and which.

The model keeps marking an offer with one button carrying the framework id. The code replaces that turn's text with the fixed offer and its three buttons, answers a Tell me more tap without the model, and keeps every guard that decides whether an offer may go out.

**Implementation skills**: none (backend seeded content, a small Python module and the Streamlit chat tester).

## Rationale

Reasoning and options: see [rationale.md](rationale.md).

## Feature design

**Data model**: no schema change and no migration. On reseed, the `admin.prompts` rows `replies`, `mani_base`, `response_format` and `tuning`, and all six `admin.frameworks` rows (`name`, `summary`, `body`), change. A stored option in `messages.prompt_options` (jsonb) may carry a new key, `more: true`, written only by the code and never part of the model's reply schema, in the same way the greeting's `style` key is (`orchestrator.chosen_style`).

**State transitions**: none new. An offer is still `offered` on the `offering` phase until a yes (`accepted`) or a no (`declined`). A Tell me more tap leaves it as it is.

**Interface changes** (no HTTP shape change; `TurnOut.prompts` and `MessageOut.prompts` are still `SmartPrompt` lists, so `more` is not sent to clients, just as `style` is not):

| Where | Before | After |
|---|---|---|
| Offer turn text | the model's own offer | `offer.text` with the name and description |
| Offer turn buttons | Try it · Keep chatting, labels from the model | Yes, let's try it · Tell me more · I want to keep talking, from `replies` |
| Tell me more | no such button | `offer.more_text`, then Yes, let's try it · I want to keep talking, no model call |
| Typed text past an offer that the reply keeps open | the model's answer and its two buttons | the full offer again, with its three buttons (no current client reaches this) |
| Framework file body | eight lines | seven lines (no `Offer:`) |

**The `offer` block in `replies.md`** (YAML keys are not `yes` and `no`, which YAML reads as booleans; see the journal note `prompt-word-budget-and-yaml-yes-key-2026-10-07.md`):

```yaml
# The offer the code writes when the model offers a set, filled from that framework's row: {name} is
# its name and {description} its summary, the only two fields allowed, and both are required.
# Wording from muhammad (2026-10-08) and the client's intro document in docs/client-share-docs/.
offer:
  text: "We'll go through a few focused questions. By the end, you will have turned a problem that feels unclear or overwhelming into a practical next step. Would it help to work through it together?\n\nFramework: {name}\n\n{description}"
  # What a tap on Tell me more gets until the client gives its own wording.
  more_text: "Framework: {name}\n\n{description}"
  # The three buttons, in this order. A tap is matched to its label ignoring case, so no two may match.
  labels:
    accept: "Yes, let's try it"
    more: Tell me more
    decline: I want to keep talking
```

**Framework names and descriptions** (`name:` and `summary:` in each file):

| File | `name` | `summary` |
|---|---|---|
| `abcde.md` | ABCDE Framework | This framework helps you separate what happened from what you told yourself about it, question what may not be serving you, and come away with a clearer and more useful way of seeing the situation. |
| `behavioral_activation.md` | Behavioral Activation | This framework helps you identify what you have stopped doing and choose one realistic activity you can begin. By the end, you will have a specific, manageable action that helps you start moving forward again. |
| `structured_problem_solving.md` | Structured Problem Solving | This framework moves through five questions. By the end, you will have turned a problem that feels unclear or overwhelming into a practical next step. |
| `act_choice_point.md` | ACT Choice Point | This framework helps you notice the difficult thought or feeling, reconnect with what matters to you, and choose an action that reflects the person you want to be. By the end, you will have a direction you can take even when the situation or your feelings have not changed. |
| `dbt_stop.md` | STOP Framework | This framework helps you interrupt an automatic reaction so you can pause, understand what is happening, and choose how you want to respond rather than simply reacting. |
| `thought_reframe.md` | Thought Reframe | This framework helps you examine a troubling thought and consider a more balanced perspective. By the end, you will be able to see the situation differently. |

**One offer as the person sees it** (Thought Reframe):

```
We'll go through a few focused questions. By the end, you will have turned a problem that feels unclear or overwhelming into a practical next step. Would it help to work through it together?

Framework: Thought Reframe

This framework helps you examine a troubling thought and consider a more balanced perspective. By the end, you will be able to see the situation differently.

[Yes, let's try it] [Tell me more] [I want to keep talking]
```

**Prompt wording** (drafts; muhammad reviews them before the reseed, as for specs 0010 to 0012).

`mani_base.md`, `offers` line 1 (accepted by muhammad in the interview):

```yaml
  - Offer once you can tell what the issue is and which set fits, and do not keep asking once it is clear. Never say its id.
```

`mani_base.md`, `offers` line 2 (accepted):

```yaml
  - To offer, carry one button with the framework id as technique. The offer's words and its three buttons replace your reply, so write it as one short line.
```

`mani_base.md`, `offers` line 5 (accepted):

```yaml
  - Asked what it involves, answer in two sentences of your own. Asked how it works, give an everyday example with a made up situation, never theirs. A no, or talking on without answering, is I want to keep talking, so follow them and offer nothing in that reply. Asking for it later is a yes.
```

`response_format.md`, `fields` `prompts` (draft):

```yaml
  prompts: the buttons under your reply, never more than three, or null when no buttons are appropriate. Each has a label. technique is set only on the offer's button, to the framework id it offers. decline is true only on a button that declines the offer. library is set only on a button that opens the Library, to one of home, EmotionalIntelligence, NarcissisticDynamics, BuildingHabits, Boundaries, Anxiety or Burnout, where home is the Library's front page, for a general Go to Library button.
```

`response_format.md`, `buttons` line 1 (draft):

```yaml
  - Only under an offer. Never in ordinary conversation, and never in the ending, which carries none from you. The offer's buttons, Chat More and Go to Library are added for you.
```

`response_format.md`, `layers` `Framework Index` (draft):

```yaml
  Framework Index: the sets of questions you may offer. Each has a Description line, then seven lines, when it starts, how it sounds, when to skip it for another, its stages, when it ends, and what never to do. The stages after the | on its Stages line are the ones you work through together. While one runs, the stage you are on is named in [ctx].
```

The `prompts` line keeps its decline clause because `decline` stays a `SmartPrompt` field, and `test_prompt_contract.py` requires every field to be named in that line. "Seven lines" in the Framework Index line is right though it lists six things: the body has two `Never` lines (`FRAMEWORK_LABELS`), as "eight lines" with seven things did before.

`response_format.md`, `fields` `state`: only the clause "or carry on talking without answering it, which is Keep chatting" becomes "or carry on talking without answering it, which is I want to keep talking".

**Where the code changes**:
- `mani/prompts/replies.py`: an `Offer` model (`text`, `more_text`, `labels` with `accept`, `more` and `decline`) on `Replies`, with a check beside `_only_the_name_field` that allows exactly `{name}` and `{description}` and requires both.
- `mani/chat/offer.py` (new): builds an offer's text and stored options from `Replies` and a framework row, and the Tell me more reply and its two options, the same way `greeting.py` builds the style buttons. Its first lines are the two `ABOUTME:` comments.
- `mani/chat/orchestrator.py`, three changes:
  - A helper `explained_offer(history, content)` beside `chosen_style`, which reads the stored dicts.
  - A `_explain_offer` path modelled on `_open_in_style`, taken right after the style check. If the pending offer's framework is no longer in the registry, the turn falls through to the model as today.
  - One step after the ending checks and before the empty text check and `messages_db.create_pair`, which applies AC-4 and leaves `updates.style` unset on an offer turn. Stored options are written as dicts so `more: true` is kept; `Turn.prompts` stays a `SmartPrompt` list.
- `scripts/eval_replies.py`: skips the reply validators on code written replies (AC-13).
- `scripts/seed.py`: seven `FRAMEWORK_LABELS`, and a blank `summary` refused.

**Value sourcing**:

| Action | Value | Source |
|---|---|---|
| Whether this turn offers, and which set | the technique button's id | the model's reply, after `guards.check`, the safety concern and the ending checks |
| The offer's text | lead, layout, name, description | `replies.offer.text`, filled from `admin.frameworks.name` and `.summary` (whitespace collapsed) through the registry |
| The three button labels | accept, more, decline | `replies.offer.labels` |
| Which stored button is Tell me more | `more: true` | written by `offer.py` into `messages.prompt_options` |
| The Tell me more reply | name and description | `replies.offer.more_text`, filled from the pending offer's framework row |
| The yes after Tell me more | the framework id | the `technique` on the accept option `offer.py` stored with the Tell me more reply |
| Whether the chat tester hides its field | a technique button on the newest Mani message | the turn's `prompts` (`technique` set) |
| The model's text and style on an offer | not used | dropped; the stored and sent text is `offer.text`, and no style is recorded |
| The Tell me more turn's other fields | `crisis_blocks_chat`, title, duplicate flag | `settings.crisis_blocks_chat`, the thread's title, the stored pair (AC-5) |
| Whether the eval checks a reply | written by the code or by the model | a technique button on the turn, or a tap on the `more` option (AC-13) |

**Key invariants**:
- The model decides whether to offer and which set; the code never offers on its own, and every guard that can stop an offer runs before the code writes it.
- The offer's words exist only in seeded content: `replies.offer` and the framework rows. No offer sentence is written in `backend/mani/` (the decision in force from spec 0007).
- A tap is told apart by a stored key, never by reading words: `technique`, `decline` and `more` on the stored options.
- An offer always carries all three buttons, and the reply to Tell me more always carries the two.

**Security model**: no new route, no new data and no new grant. Conversation text stays special category health data. The Tell me more path writes through `create_pair` under the user scoped connection, as `_open_in_style` does, and the thread lock check before it still applies.

**Failure and edge cases**:
- **Deploy order.** `Replies` refuses unknown keys, and the new model requires `offer`. Old code therefore fails on the reseeded row at its first cache reload, within 300 seconds, and new code fails on an old row. Seed, deploy and restart back to back, as for spec 0012. Code that accepts both row shapes is not built, because that is backward compatibility and needs muhammad's explicit yes. Locally, reseed and restart together.
- **An offer stored before the change.** It still shows Try it and Keep chatting, and both taps still work, because taps match the stored options.
- **A typed question past an offer, from a client that does not hide the field.** If the model carries the offer again, the person gets the full offer again rather than an answer. Accepted (muhammad, 2026-10-08): no current client reaches it, and one rule is simpler than telling the cases apart.
- **A different set offered while one is pending.** The same rule: the full offer goes out for the new id, and the state is written as today.
- **The pending offer's framework is gone from the registry when Tell me more is tapped.** `find_tapped_prompt` still matches the label, so the model gets "tapped: Tell me more" as an unrecognised tap with no `offer_waiting`, and answers it.
- **The fixed lead in `recent_openers`.** The model sees "We'll go through a few focused questions" as a recent opener on later turns. Harmless; it only steers the model away from starting that way.
- **The new names reach the model.** "ABCDE Framework" and "STOP Framework" become the Framework Index headings and the name passed to the exercise pick (`choose_exercise`). Accepted.
- **A model that ignores line 2 and writes a long offer.** Its text is dropped anyway; the only cost is output tokens.
- **The lead repeats Structured Problem Solving's description, and promises a practical next step for the other five.** This is muhammad's call; see the premise note in [rationale.md](rationale.md).

**Critical test scenarios** (scripted, through the existing integration harness and unit tests; existing offer tests are rewritten rather than added to where they already cover the path):
- A scripted reply carrying a technique button for `thought_reframe` sends and stores the filled `offer.text` and the three options in order, and none of the scripted text. Verifies **AC-4**.
- A tap on Tell me more makes no model call (`ScriptedModel.calls` is the same after the tap as after the offer turn; it counts the whole test and repeats its last reply when called again, so "zero" is the wrong check), sends the filled `more_text` with the two options, and leaves the technique row offered. A tap on Yes, let's try it after it accepts. Verifies **AC-5**.
- Typed text past an offer, with a scripted reply that re-carries the same technique, sends the full offer again with three options; without the button it is a decline (the existing `test_carrying_on_past_an_offer_is_keep_chatting` and `test_asking_about_an_offer_leaves_it_open`, rewritten). Verifies **AC-6**.
- An offer turn whose scripted text is empty still sends the offer, and stores no style. Verifies **AC-4**.
- A scripted offer with a safety concern, or for an unknown id, goes out with the scripted text and no buttons (the existing tests, relabelled). Verifies **AC-7**.
- `Replies` refuses a missing `offer`, a template without `{description}`, one with `{other}`, and two labels that match. Verifies **AC-1**.
- The seed accepts the six seven line files, and refuses an eight line body and a blank summary. Verifies **AC-2**, **AC-3**.

## Migration plan

**Strategy**: no schema migration. One change, shipped whole.
**Phases**:
1. Code, content and tests change together on this branch. muhammad reviews the `response_format.md` drafts.
2. After his yes, `python scripts/seed.py`, restart, the full `pytest`.
3. Hosted: seed, deploy and restart back to back. An old instance fails every chat turn from its first cache reload after the seed until the new code replaces it.
**Rollback**: revert the commit and reseed. The content comes back from git and no data is touched. Offers stored with the new buttons still work after a rollback, because taps on `technique` and `decline` match as before. A Tell me more tap then reaches the model as an unrecognised tap, and the model answers it.
**Risks**: chat turns fail on old instances between the seed and the new code (see *Failure and edge cases*).

## Build plan

The build approach is Tracer Bullet (scope header): one thin thread from seeded content through the turn to a scripted test first, then the other paths, then the content and the close out.

1. Tracer. Add the `offer` block to `replies.md` and `Offer` to `Replies` with its checks and refusal cases. Write `mani/chat/offer.py` and the orchestrator step for a new offer. Reseed locally (the wording is muhammad's own from the interview), restart, and rewrite `test_an_offer_is_made_on_the_second_message_in_any_style` and `test_tapping_the_offer_records_acceptance` in `tests/integration/test_turn.py` to the new text and labels. Satisfies **AC-1**, **AC-4**.
2. The other paths. Add the Tell me more tap path with its scripted test, and rewrite the typed past offer tests to AC-6. Relabel the remaining offer tests in `test_turn.py`, `test_guards.py` and `test_chat_context.py`, the docstrings and the chat tester README. Satisfies **AC-5**, **AC-6**, **AC-7**, **AC-10**.
3. Content. Write the six names and summaries, cut the `Offer:` lines, set the seed to seven labels and add the blank summary check (fix `test_seed_frameworks.py` and `test_composer.py` fixtures that carry an `Offer:` line), the `mani_base.md`, `response_format.md` and `tuning.md` edits, and `@tap:` in `eval_conversations.yaml`. muhammad reviews the drafts; after his yes, reseed, restart, and run the full `pytest` with counts before and after and the integration tests checked as not skipped. Satisfies **AC-2**, **AC-3**, **AC-8**, **AC-10**, **AC-11**.
4. Chat tester. Hide the composer while the newest Mani message has a technique button. Satisfies **AC-9**.
5. Close out. Skip the reply validators on code written replies in `eval_replies.py`. Edit `PORT-STATUS.md`, `.claude/BACKEND.md` and the `send` docstring in place, link scope feature 15, and write the journal note. Satisfies **AC-12**, **AC-13**.

## Consequences

**Positive**:
- Every offer shows exactly the words muhammad chose and the client's description, in every style and every run.
- The model writes less on an offer turn and reads less every turn: six `Offer:` lines and the offer wording rule leave the prompt.
- Three buttons and a hidden field mean a person answers an offer with one tap, and the typed past offer path is no longer the common case.
- Changing any offer wording, name, description or label is a reseed.

**Negative / tradeoffs**:
- The decision in force "the reply goes out as the model wrote it" now has an exception: on a new offer the model's text is thrown away. It is the second place the code writes what Mani says mid conversation, after Chat More and Go to Library.
- The offer is the same in every style. The client's style document shows the offer worded per style ("I have a structured approach…"); that is given up for exact text.
- The shared lead promises "a practical next step" for all six sets, and repeats Structured Problem Solving's own description on its offer (muhammad's call, see rationale).
- The name is shown, against the intro document's "do not give them the name" (muhammad's call; already on the client list).
- Tell me more says nothing new until the client's wording arrives.
- The model still spends output tokens on text that is dropped.
- A client that lets the person type a question past an offer gets the offer again instead of an answer (AC-6).

**Neutral**:
- `heading_toward`, the cooldown, the grief veto and the offer log do not change.
- The model's reply schema does not change; `more` is a stored only key.
- The framework format goes from eight lines (spec 0005) to seven.

## Follow-up

- [ ] Tell the client that every offer now opens with the same lead, and that Tell me more shows the name and description until they send its wording (client list in `PORT-STATUS.md`, AC-12).
- [ ] A spec for the Tell me more wording, once the client provides it (scope feature 17).
- [ ] Hide the text field in web and mobile, the way AC-9 does, when they are wired to the API.
- [ ] Commit spec 0012's work before `/develop` of this spec; 0013 builds on its `offers` lines.
- [ ] After the build, `/sync` marks spec 0005's eight line format and spec 0007's "offer in the model's words" as changed by this spec.
