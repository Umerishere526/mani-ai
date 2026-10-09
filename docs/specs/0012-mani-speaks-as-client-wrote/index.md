# 0012. Mani speaks and asks as the client wrote

**Date**: 2026-10-08
**Status**: In Progress
**Decision record**: [rationale.md](rationale.md) (context, premise notes, options considered, rationale)

## Summary

Mani asks too many questions before it offers a set of questions, and its three styles do not behave the way the client's October 8 style document describes. In muhammad's chat tester run, the offer came at turn 8, where the client wants about 2 to 4 exchanges. The cause is stacked prompt rules, each asking for one more question. This spec cuts and rewrites those rules in the client's own words, removes two `[ctx]` lines (hidden facts sent to the model each turn) that contradict the client, and renames the Direct button to the client's Directive. Nothing new is added to the prompts, and the guardrail code stays.

## Requirements

**User stories**:
- As a person talking to Mani, I want it to understand my issue in a few exchanges and then offer help, rather than keep asking.
- As a person who chose Directive, Supportive or Reflective, I want each reply to do what that style does in the client's document, without stock phrases.
- As muhammad, I want the prompts shorter after this change, not longer, so the model has fewer rules to trip over.

**Acceptance criteria**:

- **AC-1**: In `backend/content/prompts/mani_base.md`, `rules` line 1 reads exactly "Use their words. Never name a feeling they have not named, and never make it bigger than they did." The clause "not as a fact, a guess or a question" is gone. `rules` line 2 ("Never label or define what they are going through. If you understand more than they said, ask, so they can confirm or correct it.") is unchanged and is the client's check rule.
- **AC-2**: The `styles` lines `direct`, `supportive` and `reflective` are exactly the drafts in *Feature design*. `styles.all` is unchanged. No line of `mani_base.md` contains "Start with what they feel", "Feelings first", "never the facts" or "the soonest to offer".
- **AC-3**: In `mani_base.md` `questions`: line 1 no longer contains "built from their feeling and situation so it could only be asked of this person right now", and its other sentences are unchanged. Line 2 is exactly the draft in *Feature design*, so it no longer contains "Follow the feeling" or "pick what is worst". Line 3 is exactly "No generic check ins, no announcing or narrating the conversation."
- **AC-4**: In `mani_base.md` `offers`: line 1's first sentence is exactly "Offer once you can tell what the issue is and which set fits, and do not keep asking once it is clear." Line 3 is exactly the draft in *Feature design*, so it no longer contains "only once you have learned what its Starts when line names" or "If two fit". The second sentence of line 1 and all of lines 2, 4 and 5 ("Write the whole offer…", the pain line, "Asked what it involves…") are byte for byte unchanged; the offer wording belongs to feature 15.
- **AC-5**: In `backend/content/prompts/response_format.md`: reasoning step 2 is exactly "What the style leads with. Which set in the Framework Index is this heading toward, or none? Set heading_toward to its id, or null." The `layers` `Framework Index` line is exactly "Framework Index: the sets of questions you may offer. Each has a Description line, then eight lines, when it starts, how it sounds, when to skip it for another, its stages, when it ends, how to offer it, and what never to do. The stages after the | on its Stages line are the ones you work through together. While one runs, the stage you are on is named in [ctx]." The `ctx` lines `clarification_lines` and `question_focus` are deleted. No other line of the file changes.
- **AC-6**: The code sends neither line. `mani/chat/context.py` builds no `clarification_lines` and no `question_focus` line, and both leave `CTX_KEYS`. `Replies.clarification_lines` is deleted from `mani/prompts/replies.py`, and `clarification_lines` (with its comment) from `content/prompts/replies.md`. `tests/unit/test_prompts_name_what_exists.REMOVED` gains `clarification_lines`, `question_focus` and `feeling_then_way_through`. `REPLIES_REFUSED` in `tests/unit/test_config_rows.py` gains a case: a `replies` row that still has `clarification_lines` is refused. In `tests/unit/test_config_rows.py`, the three refusal cases that edit `clarification_lines` (an empty list, a pipe, a newline) are rewritten to edit `after_framework_questions`, which uses the same `CtxLine` type, so that validation stays covered. In `tests/unit/test_chat_context.py`, the `question_focus` test (around line 470) and the two `clarification_lines` tests (around lines 557 and 571) are deleted.
- **AC-7**: The `Starts when` lines of `abcde.md`, `thought_reframe.md`, `act_choice_point.md` and `behavioral_activation.md` in `backend/content/frameworks/` are exactly the drafts in *Feature design*. Each keeps only what identifies the issue (the first one or two stages, which are what the person describes when they state it). The stages after those, and the clauses that can only be learned by asking (whether they want a brief or a deep look), are cut; the stage ledger (spec 0010) asks any stage still missing after the yes. `dbt_stop.md` and `structured_problem_solving.md` are unchanged. Every line stays within `seed.py`'s 220 character cap, and `python scripts/seed.py` accepts all six files.
- **AC-8**: The style buttons read Directive, Supportive, Reflective, in that order. Only the label changes: `content/prompts/replies.md` `style_labels.direct` is `Directive`, and the key `direct`, the `SupportStyle` value, the `[ctx]` value and every stored thread stay `direct`. A tap on a "Direct" button stored on a greeting from before the change still picks `direct`, because `chosen_style` matches against that message's own stored options. `tests/unit/test_greeting.py` and `tests/integration/test_turn.py` (around line 1187) expect `Directive`, and `chat-tester/app.py` `STYLES` maps `direct` to `Directive`, so its style caption shows for threads started after the change (an older thread tapped as Direct shows no caption, which is accepted).
- **AC-9**: `mani_base.md` and `response_format.md` together are under 150 lines and under 3616 words, as `wc -lw` reports (150 lines and 3616 words on 2026-10-08). The before and after numbers are recorded in the journal note.
- **AC-10**: `backend/docs/specs/conversational-styles.md` follows the client's October 8 document (`docs/client-share-docs/directive, reflective, supportive .docx`), with exactly these edits: every "Direct" that names the style becomes "Directive" (the title, the tables and the headings), and the `backend/docs/specs/README.md` index row likewise; the source line at the top names the October 8 .docx instead of the earlier PDF; and the scenario sections are replaced by the document's four scenarios (panic, the friend's text, scrolling, deadline stress) in all three styles, as it writes them. The framework entry text with its 2 to 4 exchanges and the per style behavior lists are already there and stay. The comment above the `client_*` scenarios in `scripts/eval_conversations.yaml` no longer says their user turns are verbatim. The scenarios themselves are not changed (muhammad, 2026-10-08).
- **AC-11**: Three real model conversations, one run each, after the reseed and only after muhammad's yes, with `get-credits` checked first: `eval_replies.py --scenario client_anxiety --style direct`, `--scenario client_overthinking --style reflective`, and `--scenario client_stress --style supportive`. Before reading a run, the builder confirms its thread has `conversation_style` set, because `eval_replies.py` taps the label from the file while the buttons come from the seeded row. A run passes when the `first offer at message` column shows an offer at their message 2 to 4, printed as a list such as `['2:abcde']` (the greeting, the style tap and the opener are not counted; `client_anxiety` and `client_stress` hold three user messages, so for them the window is 2 to 3; `[None]` means no offer and is a fail), and when a case insensitive search of the `--verbose` replies, with straight and curly apostrophes, finds none of "I hear you", "That makes sense" or "I'm here for you". The search is done by hand, because `validators.style_findings` does not flag all three in every style. The results are recorded as measured, pass or fail, in the journal note and under the measurements in `backend/PORT-STATUS.md`. A failing run is reported, never rerun until it passes.
- **AC-12**: The whole `pytest` passes with pristine output. The builder records the passed, skipped and deleted counts before and after, and checks that the integration tests were not skipped. In the same change, `backend/PORT-STATUS.md` is edited in place: line 64 (chat turn step 3, the lines Mani may say word for word), line 76 (the Frameworks paragraph's "once Mani has learned what its Starts when line names"), line 139 (the spec 0011 decision in force, same phrase), line 161 (the only word for word lines are the clarification lines and the after framework questions), and the "Open decisions for muhammad" section gains a line to tell the client the two check lines are gone. Scope feature 14's done line is rewritten to AC-9 and AC-11.

**Not in this spec**:
- The offer's own wording, its three buttons and Tell me more. That is feature 15, which builds on the `offers` lines this spec leaves.
- New eval scenarios or turns from the October 8 document. muhammad chose to leave the scenarios as they are.
- More than three real conversations. muhammad capped the real runs at 2 to 3.
- The body ending and the after framework questions. Neither changes.

## Decision

**Chosen option**: Option 1: cut and replace prompt rules with the client's own phrases, and delete the two `[ctx]` lines that contradict the client.

The style lines become the client's behavior lists in the client's phrases, the offer gate becomes the client's "once you can tell what the issue is and which set fits", the Starts when lines shrink to what identifies the issue, and the rules that each asked for one more question are cut.

**Implementation skills**: none (backend seeded content and a small Python cut).

## Rationale

Reasoning and options: see [rationale.md](rationale.md).

## Feature design

**Data model**: no schema change and no migration. The `admin.prompts` rows `mani_base`, `response_format` and `replies`, and four `admin.frameworks` rows, change on reseed.

**State transitions**: none. Offers, stages and the cooldown work as today.

**Interface changes** (no HTTP shape change):

| Where | Before | After |
|---|---|---|
| Greeting buttons | Direct, Supportive, Reflective | Directive, Supportive, Reflective |
| `[ctx]`, no framework running | `clarification_lines`, `question_focus`, `cooldown_passed`, … | `cooldown_passed`, … |
| `replies` row | has `clarification_lines` | no `clarification_lines` |
| `Replies` model | `clarification_lines` required | field gone, unknown keys still refused |

**Prompt wording** (drafts; muhammad reviews them before the reseed, as for specs 0010 and 0011):

`mani_base.md`, `styles` (each is one line in the file):

```yaml
  direct: Leads. Actively leads the conversation forward, asks clear, purposeful questions, responds directly to what they say, gives direction when it is needed, and keeps it focused without rushing them. For example, "Okay. I'll guide you through it one step at a time."
  supportive: Accompanies. Acknowledges what they share without over validating every statement, with warmth and empathy, asks gently rather than pushing for an answer, and encourages when it is useful, never with repeated reassurance. For example, "Okay. We'll take it one step at a time together."
  reflective: Mirrors and explores. Reflects the meaning and important details in what they actually say, selectively, when it adds value, stays close to their language without repeating it back, and asks what helps them look more closely. For example, "Okay. Let's look at it together, one step at a time."
```

`mani_base.md`, `questions` line 1 (only the clause is cut):

```yaml
  - While you are understanding and while the questions run, every reply ends in one question. Comfort goes inside the reply, never instead of the question. The exceptions are the offer, someone who asked only to be heard, and the ending, which says what to ask.
```

`mani_base.md`, `questions` line 2:

```yaml
  - Ask as a perceptive friend would, in plain words, about what happened or what it is like for them. Never ask for what they made clear or the same thing the same way twice, and if they have named no feeling or problem, pick up the one thing they gave rather than asking for one.
```

`mani_base.md`, `offers` line 1's first sentence, then line 3:

```yaml
  - Offer once you can tell what the issue is and which set fits, and do not keep asking once it is clear. To the person it is only some questions you can go through together, so never say its name, its id or the word framework.
  - Offer only when cooldown_passed is yes. Pick the one whose Starts when and Sounds like lines fit what they told you in their own words, not only the words of its examples. Never offer one its Skip when or Never lines rule out, or one that ruled_out names. When they ask for a kind of help, ask about it and follow their answer rather than offering.
```

Framework `Starts when` lines:

| Framework | Draft | What it keeps and cuts |
|---|---|---|
| `abcde` | Starts when: you have learned the event that set it off and what it came to mean about them. | keeps activate and belief; consequence and "they want to look at it in depth" are cut |
| `thought_reframe` | Starts when: you have learned the one thought going round, in their words, and the moment it is tied to. | keeps thought; significance and "they want a brief look rather than a deep one" are cut |
| `act_choice_point` | Starts when: you have learned what they cannot change and the thought or feeling that stays, which no plan or evidence settles. | keeps situation and present; pull and "they want to choose how to respond" are cut, and "which no plan or evidence settles" says the same distinction from what they said |
| `behavioral_activation` | Starts when: you have learned what they have stopped or avoid doing, and that they know what they could do but cannot begin, with no physical cause or recent death behind it. | keeps stopped; "what gets in the way" (the barrier stage, after the `|`) is cut |

The ABCDE and Thought Reframe split that the cut "in depth" and "brief look" clauses carried stays on their Skip when lines: Thought Reframe skips "an event, belief and effects to unpack (abcde)".

**Value sourcing**:

| Action | Value | Source |
|---|---|---|
| Whether an offer may be made | `cooldown_passed` | `tuning.offers.clear_offer_after` and their message count (`context.cooldown_passed`, unchanged) |
| When to offer, inside that | the model's judgment | `offers` line 1 and the Framework Index's Starts when lines in the system prompt |
| What each reply does | the style line | `[ctx]` `conversation_style` and `mani_base.md` `styles` |
| The style button's text | `Directive` | `replies.style_labels.direct` |
| The style a tap picks | `direct` | the stored options on that thread's greeting message (`orchestrator.chosen_style`) |
| The prompt size | lines and words | `wc -lw` on the two files |
| The real run results | first offer message, stock phrases | `eval_replies.py` output, the `first offer at message` column and the replies with `--verbose` |

**Key invariants**:
- No rule is added to any prompt; every edit cuts or replaces a line that exists.
- The offer's own wording lines and buttons are untouched, so feature 15 starts from them as they are today.
- The guardrails stay: the grief veto, `cooldown_passed`, the safety line, `guards.check` and the crisis handling are not touched.
- The stored style value stays `direct`; only what the button shows changes.

**Security model**: no new route and no new data. Conversation text stays special category health data; this change logs nothing new, and the real runs use throwaway users that `eval_replies.py` removes.

**Failure and edge cases**:
- Deploy order. `Replies` refuses unknown keys and today requires `clarification_lines`, so old code fails on a reseeded row without it, and new code fails on an old row that still has it. `cache.load()` reloads as soon as its snapshot is stale (`prompt_cache_ttl`, 300 seconds), so an old instance breaks on its first reload after the seed, not when new code lands. Seed, deploy and restart back to back, so chat turns fail only until the new code is running. No code that accepts both row shapes is built: that is backward compatibility and needs muhammad's explicit yes. Locally, reseed and restart together.
- A greeting stored before the change still shows Direct and its tap still picks `direct` (AC-8).
- Without `question_focus`, the style rests on the style lines alone. That line was added on 2026-09-24 because "the style rule in the long prompt alone did not hold". The three real runs are the only check that it now holds. If it fails, the fix is to adjust the style line, not to bring the `[ctx]` line back.
- Without the check lines, Mani checks its understanding in its own words, the way the client's lines do ("Does that feel right?"), as `rules` line 2 says.
- A short scenario. `client_anxiety` and `client_stress` hold three user messages each, so an offer must come by their third message to be seen at all. A run that never offers is a fail and is reported.

**Critical test scenarios** (scripted; few, and existing tests are rewritten rather than added to):
- `[ctx]` with nothing running has `conversation_phase` and `cooldown_passed` and neither `clarification_lines` nor `question_focus`: covered by the contract test (`CTX_KEYS` against `response_format.md` `ctx`, both ways) and by `REMOVED`, verifies **AC-5**, **AC-6**.
- The `replies` row loads without `clarification_lines`, and one that still has it is refused (the new `REPLIES_REFUSED` case), verifies **AC-6**.
- `after_framework_questions` refuses an empty list, a pipe and a newline (the moved cases), verifies **AC-6**.
- The greeting's buttons are Directive, Supportive, Reflective (the existing `test_greeting.py` and `test_turn.py` assertions, rewritten), verifies **AC-8**.
- The seed accepts the six framework files (the existing seed tests), verifies **AC-7**.

## Migration plan

**Strategy**: no schema migration. One change, shipped whole.
**Phases**:
1. Code, content and tests change together on this branch; muhammad reviews the drafted wording.
2. After his yes, `python scripts/seed.py`, restart, the full `pytest`.
3. Hosted: seed, deploy and restart back to back. An old instance fails every chat turn from its first cache reload after the seed (within 300 seconds) until the new code replaces it, so keep that gap as short as the deploy.
**Rollback**: revert the commit and reseed. The content comes back from git and no data is touched.
**Risks**: chat turns fail on old instances between the seed and the new code (see *Failure and edge cases*), and style drift without `question_focus` (see *Consequences*).

## Build plan

The build approach is Tracer Bullet (scope header): one thin thread through code, content, seed and tests first, then the close out and the real runs.

1. Tracer. Delete `question_focus` and `clarification_lines` from `context.py`, `CTX_KEYS`, `Replies`, `replies.md` and `response_format.md`; add both to `REMOVED`; move the three `CtxLine` refusal cases to `after_framework_questions`; delete the three `test_chat_context.py` tests. Set `style_labels.direct` to `Directive` and update `test_greeting.py`, `test_turn.py` and `chat-tester/app.py`. Write the `mani_base.md` and `response_format.md` edits and the four Starts when lines from the drafts. `pytest tests/unit` passes; the integration tests read the seeded rows, so they wait for the reseed in step 2. Satisfies **AC-1**, **AC-2**, **AC-3**, **AC-4**, **AC-5**, **AC-6**, **AC-7**, **AC-8**.
2. Review and reseed. muhammad reviews the wording; after his yes, `python scripts/seed.py`, restart, the full `pytest` with counts before and after and the integration tests checked as not skipped, then `wc -lw` on the two prompts. Satisfies **AC-9**, **AC-12**.
3. Close out. Refresh `backend/docs/specs/conversational-styles.md` from the October 8 document; correct the comment above the `client_*` scenarios; edit `PORT-STATUS.md` in place; write the journal note; rewrite scope feature 14's done line. Satisfies **AC-10**, **AC-12**.
4. Real runs. Ask muhammad, check `get-credits`, then the three conversations, one run each, recorded as measured. Satisfies **AC-11**.

## Consequences

**Positive**:
- The rules that each asked for one more question are gone, so the cadence the client describes (understand, check, offer) is what the prompt says.
- Each style line is the client's own behavior list, so a reader can check the prompt against the client document line by line.
- Two `[ctx]` lines, one `replies` key, one model field and three tests leave the code. The prompts get shorter, never longer.
- The button says the client's word, Directive.

**Negative / tradeoffs**:
- `question_focus` was muhammad's 2026-09-24 fix for styles that drifted. Removing it puts all the weight on the style lines, and only three real conversations check it, one per style.
- The client's check lines ("Do I have this right?", "What would you like us to focus on today?") are gone. They came from an earlier client document. The client should be told (AC-12).
- Direct loses "never telling them what to do". "Gives direction when it is needed" is the client's phrase; `rules` line 3, "No advice they did not ask for", still holds it in check.
- The Starts when lines no longer ask whether the person wants a brief or a deep look, so ABCDE and Thought Reframe are told apart by their Skip when lines and the model's reading alone.
- Three runs show a direction, not a rate. One lucky or unlucky run can mislead; feature 11 is where offers get measured properly.

**Neutral**:
- `heading_toward` stays; only the reasoning step's Starts when question goes.
- No migration, no endpoint and no frontend change beyond the label text the API already returns.

## Follow-up

- [ ] Tell the client that the two check lines are gone and Mani checks its understanding in its own words (client list in `PORT-STATUS.md`, AC-12).
- [ ] Feature 15 designs the offer's wording and buttons on top of the `offers` lines this spec leaves.
- [ ] After the build, `/sync` marks spec 0008's `clarification_lines` criterion (its AC-10) as changed by this spec.
- [ ] Feature 16's audit can skip `clarification_lines` and `question_focus`; this spec removes them.
- [ ] If the real runs show the styles drifting, adjust the style lines under feature 11 with muhammad's yes for each run.
