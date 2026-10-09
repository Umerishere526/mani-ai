# 0015. The offer and Tell Me More per framework and style

**Date**: 2026-10-08
**Status**: In Progress
**Decision record**: [rationale.md](rationale.md) (context, premise notes, options considered, rationale)

## Summary

Today every offer of a set of questions shows one shared text, and Tell Me More shows the framework's name and description again (spec 0013). The client's ABCDE document gives an offer line for each conversation style and a Tell Me More that lists the five steps in that style. This spec adds that text to the seeded `replies` row (the lines Mani sends without the model), keyed by framework and style. So an ABCDE offer and its Tell Me More are exact, in the person's style, and change with a reseed. The other five frameworks keep the shared text until their documents arrive.

## Requirements

**User stories**:
- As a person talking to Mani, I want the offer and Tell Me More to sound like the style I chose, so the conversation keeps one voice.
- As a person who taps Tell Me More, I want to see every step the questions will take before I say yes.
- As muhammad, I want each framework's per style wording in seeded content, so adding the client's next document needs only a content edit and a reseed.

**Acceptance criteria**:

- **AC-1**: `backend/content/prompts/replies.md`'s `offer` block gains a `by_framework` map, exactly as drafted in *Feature design*, with one entry, `abcde`. That entry has `direct`, `supportive` and `reflective`, each with `text` and `more_text`. Before writing, the builder checks the client's words in the drafts against `docs/client-share-docs/ABCDE Framework.docx` (`word/document.xml`), not only against `backend/docs/specs/framework-abcde.md` §0.4 and §0.6. Any word that differs is reported to muhammad, not silently changed. `mani/prompts/replies.py` gains a `StyledOffer` model (`text`, `more_text`) and a required `by_framework: dict[str, dict[str, StyledOffer]]` on `Offer`. It refuses a row in five cases:
  - an entry whose style keys are not exactly the three in `STYLES`;
  - a blank `text` or `more_text`;
  - a `text` or `more_text` that holds any `{` or `}` character (refused outright, since the text is never formatted and `{{` would go out doubled);
  - an unknown key in an entry;
  - a missing `by_framework`.

  The refusal happens wherever `Replies` is checked today (seed, admin write, cache load). `tests/unit/test_config_rows.py` gains these cases in its `REPLIES_REFUSED` style.
- **AC-2**: `scripts/seed.py` refuses to seed, with nothing written, when a `by_framework` key is not the `id` of a file in `backend/content/frameworks/`. The check is a pure function, `check_offer_frameworks(replies, framework_ids)`, which raises `ValueError` naming the key. `seed()` calls it with `load_replies()` right after the framework files are parsed and before anything is written, so the existing refusal handling prints it as a refused seed. A unit test in `tests/unit/test_seed_frameworks.py` calls the function directly, with no database.
- **AC-3**: `mani/chat/offer.py`'s `offer()` and `told_more()` take the conversation style as a third argument, a `str` value of `SupportStyle`. When `replies.offer.by_framework` has the framework's id, they send that style's `text` (for `offer`) or `more_text` (for `told_more`), exactly as seeded. Otherwise they send the shared `offer.text` or `offer.more_text` filled from the framework row, exactly as today. The stored and returned buttons do not change: three on an offer, two on the Tell Me More reply, with the same keys and labels.
- **AC-4**: In `mani/chat/orchestrator.py`, `send` resolves the style once, as `context.resolve_style(ctx, config.tuning.offers.default_style)` (the thread's style, then the profile's, then the tuning default). It passes that style to `offers.offer` at the offer step and to `offers.told_more` through `_explain_offer`. So the offer and the reply to Tell Me More use the same style the model is told in `[ctx]`. Nothing else about either path changes: no model call on Tell Me More, the model's text and style dropped on an offer turn, and the same state row, offer log and button keys.
- **AC-5**: Try It after Tell Me More is the ordinary accept. It makes one model call, the technique row goes `accepted` on the first stage not yet known, and nothing restarts the conversation. No line in `mani_base.md`, `response_format.md` or any framework file changes for this spec. The model sees the Tell Me More reply in its history. `mani_base.md` already says to open with a short line and then the first stage question (`styles.all`), and never to explain the method (`questions`).
- **AC-6**: The other five frameworks send byte for byte what they send today, on the offer and on Tell Me More, in every style.
- **AC-7**: `scripts/eval_replies.py` gains a `@more|<fallback>` token that works like `@accept`. When a label in `last_prompts` matches `load_replies().offer.labels.more` ignoring case, it sends that label; the `more` key itself never reaches the eval, because `SmartPrompt` drops it. Otherwise it sends the fallback line and tries again at the next `@more`. Once tapped, later ones are skipped, and `@newchat` does not reset that, as with `@accept`. The exchange's `kind` is `"more"`. How `@accept` and `@more` resolve becomes one pure helper, taking the line, `last_prompts` and the two flags and returning the message, the kind and the new flags. `_run_one` calls it, and a unit test covers the tap, the fallback and the skip with no database or model. The docstring lists `@more` beside `@accept` and `@tap:`. `scripts/eval_conversations.yaml` gains a scenario `abcde_told_more`, drafted in *Feature design*, with no `expect_framework` (that check needs a somatic phase, and the scenario ends inside the stages; `missing_handoff` and the other reply checks still run). The stale `start_in: {framework: abcde, phase: activate}` in `framework_abcde_stages` becomes `phase: activating_event` (stale since the ABCDE stage ids were renamed). After muhammad's yes, one real run is made: `python scripts/eval_replies.py --scenario abcde_told_more --style reflective --verbose`. It counts as passing when the reply after Try It does not list the five steps again and does not ask again for the activating event the person already gave. The result is recorded as measured, in the journal note. A failing run is reported to muhammad, not run again.
- **AC-8**: After the reseed, the whole `pytest` passes with pristine output. The builder records the passed and skipped counts before and after, and checks that the integration tests were not skipped.
- **AC-9**: In the same change:
  - `backend/PORT-STATUS.md`, the description of an offer near lines 74 to 76 and the "reply goes out as the model wrote it, except an offer" decision near lines 135 to 141: both say a framework listed under `offer.by_framework` gets its per style text, and Tell Me More its per style steps.
  - `backend/PORT-STATUS.md`, "Decisions in force", the `replies` row line near lines 158 to 160: it says that a framework listed under `offer.by_framework` gets its offer and Tell Me More per style, literal and checked, and that the others get the shared frame. The line is edited in place.
  - The `PORT-STATUS.md` client list: the Tell Me More line near line 244 (the name and description until feature 17) is replaced with one saying ABCDE now uses their per style wording, generalised where it quoted one person ("your anxiety" became "how you're feeling", and Supportive's "Feeling overwhelmed can make you question how well you're handling things." was dropped), and that the other five keep the shared offer until their documents arrive.
  - Scope feature 17's done line already says "generalised where it quoted one person" (set at design); check it still matches what was built.
  - A journal note records the counts before and after, the real run's result and anything learned.

**Not in this spec**:
- The other five frameworks' per style text. Each is added to `by_framework` when its document arrives, as a content change and a reseed.
- The Reflective Dispute question the client words differently after Tell Me More (§0.5). The model writes stage questions, and this spec changes no prompt line.
- What Mani says after Try It, and the ending (scope feature 21).
- Web and mobile. Neither is wired to the API yet; when they are, they render the `- ` lines as a list or as plain lines.

## Decision

**Chosen option**: Option 1: per framework, per style literal text in the `replies` row, chosen by the code from the conversation style, falling back to the shared frame.

The model still decides when to offer and which set, and the code still writes the offer (spec 0013). The only change is which seeded text the code writes: the framework's own per style text when the `replies` row has it, the shared frame otherwise.

**Implementation skills**: none (backend seeded content, a small Python change and the eval script).

## Rationale

Reasoning and options: see [rationale.md](rationale.md).

## Feature design

**Data model**: no schema change and no migration. On reseed, only the `admin.prompts` row `replies` changes. Its `offer` block gains `by_framework` (YAML, parsed by `Replies`). No new key goes into `messages.prompt_options`.

**State transitions**: none new. An offer is `offered` on the `offering` phase until a yes or a no; Tell Me More leaves it so.

**Interface changes** (no HTTP shape change; `TurnOut.prompts` is unchanged):

| Where | Before | After |
|---|---|---|
| ABCDE offer text | the shared lead, `Framework: ABCDE Framework`, its description | that style's `by_framework.abcde.<style>.text` |
| ABCDE Tell Me More text | `Framework: ABCDE Framework` and its description | that style's `more_text`: a lead line and the five steps as a list |
| The other five | the shared frame | unchanged |
| Buttons | Try It · Tell Me More · Keep Chatting, then Try It · Keep Chatting | unchanged |

**The `by_framework` block in `replies.md`** (draft; the client's words checked against the .docx at build, AC-1). It goes inside `offer:`, after `labels:`:

```yaml
  # A framework's own offer and Tell Me More, one per conversation style, sent instead of `text` and
  # `more_text` above. Literal: no {fields}. A framework listed here has all three styles, each with
  # both. The rest get the shared lines above until the client sends their wording.
  # Wording from the client's ABCDE Framework doc in docs/client-share-docs/, made general where it
  # quoted one person's words (muhammad, 2026-10-08).
  by_framework:
    abcde:
      direct:
        text: "There's a framework called ABCDE that helps you identify the thoughts behind how you're feeling, question whether they're true, and replace them with more realistic ones. Would you like to try it?"
        more_text: "The ABCDE framework has five steps:\n\n- A: Activating Event: What happened or what has been happening?\n- B: Belief: What did you start telling yourself about it?\n- C: Consequences: How did that thought affect how you felt or what you did?\n- D: Dispute: What makes you believe it's true, and what makes you question it?\n- E: Effective New Belief: What's a more realistic and helpful way to think about it?"
      supportive:
        text: "There's a framework called ABCDE that can help you understand the thoughts behind how you're feeling, see whether those thoughts are really true, and find a more helpful way to think about what's happening. Would you like to try it?"
        more_text: "The ABCDE framework has five steps. Each one helps you understand what happened, what you started believing about it, and how those thoughts may be affecting you.\n\n- A: Activating Event: What happened or what has been happening that brought up these feelings?\n- B: Belief: What did you begin telling yourself about the situation?\n- C: Consequences: How did that belief affect how you felt or what you did?\n- D: Dispute: What makes you believe that thought is true, and is there anything that might suggest otherwise?\n- E: Effective New Belief: What's a more realistic and helpful way to think about what happened?"
      reflective:
        text: "Sometimes the way we interpret what's happening can make a difficult situation feel even harder. There's a framework called ABCDE that helps you examine what you're telling yourself, understand how those thoughts affect you, and consider whether there's a more realistic way to see things. Would you like to try it?"
        more_text: "The ABCDE framework has five steps that help you examine how your interpretation of an experience influences what you believe and how you respond.\n\n- A: Activating Event: What happened or what has been happening that started these concerns?\n- B: Belief: What meaning did you give to what happened?\n- C: Consequences: How did that belief influence your feelings or actions?\n- D: Dispute: What supports your interpretation, and what might suggest a different understanding?\n- E: Effective New Belief: What's a more accurate and helpful way to understand the situation?"
```

The two generalised offers differ from the client's lines only here. Direct: "the thoughts behind your anxiety" becomes "the thoughts behind how you're feeling". Supportive: the opening sentence "Feeling overwhelmed can make you question how well you're handling things." is dropped, and "your anxiety" becomes "how you're feeling". Reflective and all three Tell Me More texts are the client's words. The client's bulleted steps are written as `- ` lines after a blank line, because the chat tester renders replies as markdown and single line breaks would join the steps into one paragraph.

**One Reflective ABCDE Tell Me More as the person sees it**:

```
The ABCDE framework has five steps that help you examine how your interpretation of an experience influences what you believe and how you respond.

• A: Activating Event: What happened or what has been happening that started these concerns?
• B: Belief: What meaning did you give to what happened?
• C: Consequences: How did that belief influence your feelings or actions?
• D: Dispute: What supports your interpretation, and what might suggest a different understanding?
• E: Effective New Belief: What's a more accurate and helpful way to understand the situation?

[Try It] [Keep Chatting]
```

**The `abcde_told_more` scenario** (draft, after `journey_abcde` in `eval_conversations.yaml`):

```yaml
# Tell Me More before Try It: the reply after Try It must neither list the five steps again nor ask
# for the event they already gave (client ABCDE doc, Tell Me More). Run in Reflective (spec 0015).
- name: abcde_told_more
  turns:
    - "My manager criticized my presentation in front of the whole team."
    - "She said two of my recommendations didn't have enough support, and now I keep thinking I'm bad at my job."
    - "@more|It keeps going round in my head and I'd like to work through it."
    - "@more|Yes, I want to look at it properly."
    - "@accept|Okay, let's try it."
    - "That I'm bad at my job and everyone saw it."
    - "I stopped talking for the rest of the meeting and avoided her afterwards."
```

**Where the code changes**:
- `mani/prompts/replies.py`: a `_no_braces` check beside `_the_name_and_the_description` (refuses any `{` or `}`), a `LiteralText` type, `StyledOffer`, and `by_framework` on `Offer`, with a validator that requires each entry's keys to be exactly `STYLES`.
- `mani/chat/offer.py`: a `style` argument on `offer` and `told_more`, and one private helper that returns the framework's `StyledOffer` for the style or `None`. The `ABOUTME` lines still describe the file.
- `mani/chat/orchestrator.py`: `style_now = context.resolve_style(ctx, config.tuning.offers.default_style)` once in `send`, before the Tell Me More path, passed to `_explain_offer` (a new `style` parameter, placed before `client_message_id`) and to `offers.offer`.
- `scripts/seed.py`: `check_offer_frameworks(replies, framework_ids)`, called in `seed()` right after `parse_framework` runs over the files and before anything is written.
- `scripts/eval_replies.py`: the `@more|<fallback>` token, with `@accept` and `@more` resolved by one pure helper.
- Tests: `tests/unit/test_config_rows.py` (refusal cases), `tests/unit/test_seed_frameworks.py` (the unknown id), `tests/integration/test_turn.py` (below, including `_offer_text` and the tests at lines 452 and 905), and a unit test for the token helper beside the existing eval script tests in `tests/unit/test_baseline.py`.

**Value sourcing**:

| Action | Value | Source |
|---|---|---|
| Whether this turn offers, and which set | the technique button's id | the model's reply, after every guard (spec 0013, unchanged) |
| Which style's text | the conversation style | `context.resolve_style(ctx, tuning.offers.default_style)`: `threads.conversation_style`, else `profiles.support_style`, else `tuning.offers.default_style` |
| The ABCDE offer text | literal text | `replies.offer.by_framework.abcde.<style>.text` |
| The ABCDE Tell Me More text | literal text | `replies.offer.by_framework.abcde.<style>.more_text` |
| The other five's texts | lead, name, description | `replies.offer.text` and `.more_text`, filled from `admin.frameworks.name` and `.summary` (unchanged) |
| Which framework has its own text | presence of its id | the keys of `replies.offer.by_framework` |
| Whether a key is a real framework | the file ids | `backend/content/frameworks/*.md` `id:` at seed (AC-2) |
| The buttons and their keys | labels, `technique`, `more`, `decline` | `replies.offer.labels` and `offer.py` (unchanged) |
| The real run's pass | the reply after Try It | read by muhammad and the builder from the `--verbose` transcript (AC-7) |

**Key invariants**:
- The model decides whether and which; the code decides only which seeded text to write. No offer sentence is written in `backend/mani/` (decision in force from spec 0007).
- A framework in `by_framework` has text for every style, so no style ever falls back halfway.
- Per style text is sent exactly as seeded: nothing is filled, joined or trimmed.
- The style used for the offer is the style the model is told that turn.

**Security model**: no new route, data, grant or stored key. Conversation text stays special category health data. Tell Me More still writes through `create_pair` under the user scoped connection.

**Failure and edge cases**:
- **Deploy order.** `Replies` refuses unknown keys and requires `by_framework`, so old code refuses the reseeded row at its next cache reload (within 300 seconds), and new code refuses the old row. Seed, deploy and restart back to back, as for specs 0012 and 0013. Locally, code first, then seed, then restart. Code that accepts both shapes is backward compatibility and is not built without muhammad's explicit yes.
- **An offer stored before the reseed.** Its text stays as stored. A Tell Me More tap after the reseed gets the per style text for ABCDE, which is the intended reply.
- **A `by_framework` key with no framework.** The seed refuses it (AC-2). An admin write cannot check ids; a key written that way is never matched, so it is never sent.
- **A framework id renamed later.** The seed refuses until `by_framework` is renamed with it, so the text never silently stops being used.
- **The style changes between the offer and Tell Me More.** The thread's style is fixed once tapped. Without a thread style, a profile change in between would show Tell Me More in the new style. Accepted; it is the style the model is told on that turn too.
- **Typed text past an offer** that the model answers by offering ABCDE again gets the per style offer again, by spec 0013's one rule.
- **The fixed lines in `recent_openers`.** "There's a framework called ABCDE" and "The ABCDE framework has five steps" become recent openers the model avoids starting with. Harmless.
- **The eval's reply checks.** `eval_replies.py` already skips them on replies the code wrote (a turn whose buttons carry `technique`), and the Tell Me More reply carries Try It's `technique`. Nothing to change.
- **Markdown in other clients.** A client that shows plain text shows `- A: …` lines, which still read as a list.

**Critical test scenarios** (scripted, through the existing harness; existing tests are rewritten where they already cover the path):
- `test_an_offer_is_made_on_the_second_message_in_any_style` (Supportive thread, parametrised over `structured_problem_solving`, `abcde`, `thought_reframe`): `abcde` now expects `by_framework.abcde.supportive.text`, and the assertion `"Would you like to try it?" not in turn.content` applies only to the other two, since the client's ABCDE line ends with it. `_offer_text(technique, style, more=False)` returns `by_framework[technique][style].text` (or `.more_text` with `more=True`) when the framework is listed, and otherwise fills the shared `offer.text` (or `.more_text`) as today. Verifies **AC-3**, **AC-4**, **AC-6**.
- A new parametrised test: an ABCDE offer in a Direct, a Supportive and a Reflective thread sends that style's `text`, and a `thought_reframe` offer in a Reflective thread sends the shared frame. Verifies **AC-3**, **AC-4**, **AC-6**.
- `test_the_turn_is_stored_and_the_thread_state_follows_it` (line 452) and `test_asking_about_an_offer_leaves_it_open` (line 905) assert an ABCDE offer in a thread with no style, so they now expect `by_framework.abcde.supportive.text` (the tuning default). Verifies **AC-4**.
- `test_tell_me_more_is_answered_with_no_model_call_and_the_offer_stays_open`, run in a Reflective thread: the reply is `by_framework.abcde.reflective.more_text`, the model call count does not change, and Try It after it makes exactly one model call and accepts on `activating_event`. Verifies **AC-3**, **AC-4**, **AC-5**.
- A thread with no style and a profile with none gets `tuning.offers.default_style`'s ABCDE text. Verifies **AC-4**.
- `Replies` refuses an entry missing a style, a blank `more_text`, a `{name}` and a `{{` in per style text, an unknown key in an entry, and a missing `by_framework`. Verifies **AC-1**.
- `check_offer_frameworks` refuses `by_framework: {abcd: …}` against the six real ids and names `abcd`, and accepts the seeded row. Verifies **AC-2**.
- The token helper: `@more|<line>` sends the Tell Me More label when `last_prompts` has it and the line when it does not, and is skipped once tapped; `@accept` behaves as before. Verifies **AC-7**.

## Migration plan

**Strategy**: no schema migration. One change, shipped whole.
**Phases**:
1. Code, content and tests together on this branch. muhammad reviews the `by_framework` drafts.
2. After his yes, `python scripts/seed.py`, restart, the full `pytest`.
3. After a second yes, the one real run (AC-7).
4. Hosted: seed, deploy and restart back to back.

**Rollback**: revert the commit and reseed. No data is touched; an offer stored with per style text stays readable, and its taps match by stored keys as before.
**Risks**: chat turns fail on old instances between the seed and the new code (see *Failure and edge cases*).

## Build plan

The build approach is Tracer Bullet (scope header): one thin thread from the seeded row through the turn to a scripted test, then Tell Me More, then the seed check, the eval and the close out.

1. Tracer. Add `StyledOffer`, `LiteralText` and `by_framework` to `replies.py` with the refusal cases. Add the `abcde` block to `replies.md` after checking its words against the .docx. Add the style to `offers.offer`, and to the orchestrator offer step through `style_now`. Reseed locally and restart. Rewrite `test_an_offer_is_made_on_the_second_message_in_any_style`, and add the per style offer test. Satisfies **AC-1**, **AC-3**, **AC-4**, **AC-6**.
2. Tell Me More. Add the style to `offers.told_more` and `_explain_offer`. Rewrite the Tell Me More test in a Reflective thread with Try It after it, and add the no style default test. Satisfies **AC-3**, **AC-4**, **AC-5**.
3. Seed and eval. Add the seed's id check with its test, the `@more` token with its test, the `abcde_told_more` scenario, and the `framework_abcde_stages` phase fix. muhammad reviews the drafts; after his yes, reseed, restart, and run the full `pytest` with counts before and after and the integration tests checked. Satisfies **AC-2**, **AC-7** (code), **AC-8**.
4. Close out and the real run. Edit `PORT-STATUS.md` and the scope's done line in place. Ask muhammad for the real run; run it once if he says yes, and record it in the journal note. Satisfies **AC-7** (run), **AC-9**.

## Consequences

**Positive**:
- ABCDE's offer and Tell Me More are in the person's style and exact every time, and each change is a reseed.
- Tell Me More finally says something new: every step the questions will take.
- Adding a framework's document later is content only: one `by_framework` entry, checked at seed.

**Negative / tradeoffs**:
- ABCDE's offer no longer shows `Framework: <name>` or the intro document's description, so it differs in shape from the other five until their documents arrive.
- The generalised lines are our edit of the client's words; the client is told (AC-9).
- The Supportive offer loses its acknowledgement sentence, so Supportive and Direct read alike apart from a few words.
- `replies.md` grows by about 18 lines per framework, about 110 once all six arrive.
- Whether Try It after Tell Me More repeats the steps rests on existing prompt rules and one real run, not on code.
- The deploy order constraint of spec 0013 applies again.

**Neutral**:
- No prompt, schema, API or button change.
- `by_framework` is required, and an empty map is valid.

## Follow-up

- [ ] Add each of the other five to `by_framework` when the client sends its document (scope feature 17 stays the home for this).
- [ ] Tell the client the ABCDE offer was generalised where it quoted one user (AC-9).
- [ ] When web and mobile are wired to the API, render reply text as markdown, or accept `- ` lines as plain text.
