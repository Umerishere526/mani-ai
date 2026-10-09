# 0016. Mani understands the issue, then offers naturally

**Date**: 2026-10-08
**Status**: In Progress
**Decision record**: [rationale.md](rationale.md) (context, premise notes, options considered, rationale)

## Summary

The client's feedback on all three styles says Mani hands back what the person just said, narrows on one part before it knows what the issue is, and moves into a set of questions abruptly. This spec fixes that by replacing six prompt lines, one for one, so the prompts end no longer than they started, and by one small code change: on an offer turn, the model's own short line now goes out before the seeded offer instead of being thrown away. The offer still waits for the person's second message at the earliest; after that, Mani's judgment of "I understand what they are struggling with and what makes it hard" decides when. Three real runs of the client's own job decision conversation, one per style, are the proof.

Round 2 (2026-10-08). Those three runs failed: the timing held, but every style still handed the person's feeling back ("That sounds frustrating…"), and the line before the offer drifted into offering or recapping. The cause was lines round 1 left alone, which teach care as naming their feeling. So five more lines are swapped one for one (E6 rewritten, E8 to E11), aiming at the client's own examples: a few words of care about what they are facing, never their feeling handed back. The proof is nine runs, three per style, with each reply's shape printed so a second failure points at its line.

Round 3 (2026-10-08). Round 2's nine runs failed too. "That sounds frustrating" still opened most Direct and Supportive replies, each time after reasoning that said the person needs to be heard. Every line before the offer made an offer of its own, which the seeded lead then repeated. So three things change. First, for the five sets without the client's own wording, the model's line becomes the offer (a step from what they said, how the questions could help, and the ask), and the seeded part shrinks to the set's name and description. ABCDE keeps the client's words alone, unless the person typed a question about it, in which case the model's answer goes first. Second, the first reasoning step asks what they are facing instead of what they need. Third, the offer line says concretely what must be known about a choice before offering. The proof is the same nine runs plus three measured.

Round 4 (2026-10-09). muhammad reversed round 3's offer half. Every set, ABCDE included, is offered in the same seeded words again: the spec 0013 lead ("We'll go through a few focused questions. … Would it help to work through it together?"), then `Framework: {name}` and the set's description from the client's intro document. The model's line is dropped, except when it answers a typed question about the offer, when it goes first. ABCDE's per style offer text is removed from `replies.md`, and only its per style Tell Me More stays. E6 becomes "The offer's words and its three buttons replace your reply, so write it as one short line." E5 and E12 stay. AC-8's fourth bullet no longer applies, since the offer turn has no words of the model's to grade.

## Requirements

**User stories**:
- As a person talking to Mani, I want it to answer what I said rather than repeat it back to me, so it feels like a conversation and not a transcript.
- As a person who opens with something vague, I want Mani to ask what the issue is before it asks about one part of it.
- As a person offered a set of questions, I want the offer to follow from what I just said and let me choose, without feeling rushed into it.
- As a person who says yes, I want the first question to build on what I already told, so I never explain the same situation twice.
- As muhammad, I want this reached by replacing prompt rules, never adding them, so the prompts do not grow.

**Acceptance criteria**:

- **AC-1**: Mirroring confirms understanding, never restates. In `backend/content/prompts/mani_base.md`, the `moves.mirroring` line and the `reply_shapes."mirror and ask"` line are replaced, and in `backend/content/prompts/response_format.md` the first `reasoning.steps` line is replaced, each exactly as written under *Prompt edits* (E1, E2, E3). The shape names do not change, so `reply_shapes` keeps the same six keys and `guards.check` accepts the same set. Round 2: care never hands their feeling back either. In `mani_base.md`, the first `rules` line, the `reply_shapes."warmth lead"` line, and the `styles.supportive` and `styles.reflective` lines are replaced exactly as E8, E9, E10 and E11. Round 3: in `response_format.md`, the first `reasoning.steps` line (E3's result) is replaced exactly as E12, so the reasoning written before the reply starts from what they face, not from a need to be heard.
- **AC-2**: The first questions find out what the issue is. The second line under `questions` in `mani_base.md` is replaced exactly as E4.
- **AC-3**: The offer comes once Mani knows what they are struggling with and what makes it hard. The first line under `offers` in `mani_base.md` is replaced exactly as E5, and in round 3 one span in it is replaced exactly as E5 round 3, so "good reasons for both" is not enough to offer on. `tuning.offers.clear_offer_after` stays `2`, and nothing in `backend/content/prompts/tuning.md` changes, so `cooldown_passed` is still `no` on the person's first message and `yes` from their second.
- **AC-4**: The offer opens with the model's own line. The second line under `offers` in `mani_base.md` reads exactly as E6's round 2 text. In `backend/mani/chat/orchestrator.py`, at the offer step, the text sent and stored is the model's checked `text`, a blank line (`"\n\n"`), then the seeded offer text from `offers.offer`. When the model's checked `text` is blank, the seeded offer text goes out alone, exactly as today. The join applies on every offer the checks keep, one rule: a first offer, a return after a decline, and an offer made again because they typed a question about it (the `deferred` path with `asked_about_it`). On that last one the model's line is its answer to their question, as `mani_base.md`'s `offers` line 54 asks ("Asked what it involves, answer in two sentences of your own"), which today is dropped. It does not apply where no offer survives: a tap on Tell Me More (no model call), a typed yes, an offer inside a running framework or on a turn that declines or retires one (`guards.check` drops the button), and a safety concern (the offer is dropped and the model's line goes out alone, as today). Nothing else on that path changes: the three buttons and their stored options, the `offered` technique row, the offer log line, `style` recorded as `None`, and the Tell Me More reply (still the seeded text alone). The code never checks, edits or drops the model's line (spec 0006).

  **Round 3** replaces the join above, and the E6 text named above, with one rule, which lives in `backend/mani/chat/offer.py` (where the seeded wording is already chosen), not in the orchestrator. `offers.offer` takes the model's checked `text` (already stripped by `guards.check`, so it is passed as is) and an `answering` flag, and returns the turn's text and buttons:
  - A framework with its own wording under `replies.offer.by_framework` for the style (today only ABCDE): that `text` alone. The model's line is dropped, by rule and without reading it. When `answering` is true, the model's checked text, `"\n\n"`, then that `text`.
  - Any other framework: the model's checked text, `"\n\n"`, then the shared `offer.text` filled from the framework row, which round 3 cuts to the card `"Framework: {name}\n\n{description}"` (R1). A blank model text gives the card alone, and the three buttons carry the choice.
  - `answering` is true only on the offer made again after a typed question about a live offer: the `deferred` path in `orchestrator.send` where the outcome stays `OFFERED` (the `asked_about_it` branch). It is false on a first offer and on a return after a decline.
  - The orchestrator passes `checked.text` and the flag, and uses the returned text as is. Nothing else listed above changes: buttons, stored options, the `offered` row, the log line, `style=None`, Tell Me More, the safety drop, and offers dropped inside a framework. The second line under `offers` in `mani_base.md` reads exactly as E6 round 3, so the model writes its line as the offer.
- **AC-5**: The first stage question builds on what they told, without saying it back. The `ctx.framework_starting` line in `response_format.md` is replaced exactly as E7.
- **AC-6**: The prompts do not grow. After both rounds, `mani_base.md` has 74 lines and `response_format.md` 71 (145 together, as before the build), and together they hold 3424 words (`wc -w`): the 3391 before the build, 3418 after round 1 (E1 to E7), and 3424 after round 2 (E6 rewritten, E8 to E11), applied exactly. Any other count means something else changed. No other prompt file, no framework file under `backend/content/frameworks/`, and no line of `mani_base.md` or `response_format.md` outside E1 to E12 changes. Round 3: after E6 round 3, E5 round 3 and E12, still 74 and 71 lines, and 3422 words together (simulated on 2026-10-08 against the round 2 tree, each Old text matched once, both files parsing as YAML). Outside those two files, round 3's content change is only R1 in `backend/content/prompts/replies.md` (the `offer.text` line and the two comments named there). Its other touched files are `offer.py`, `orchestrator.py`, the docstrings in `mani/prompts/replies.py` and `mani/routers/messages.py`, the comment in `scripts/eval_replies.py`, and the tests in AC-7.
- **AC-7**: Tests, all in `backend/tests/integration/test_turn.py`:
  - The scripted `_offer` reply's `text` becomes a plain bridge line with no offer words (for example `"That is a lot to weigh."`). `EARLY_OFFER` and `GRIEF_OFFER` (near lines 228 to 239) get bridge lines too, replacing their offer sentence.
  - Every assertion that an offer turn's content equals `_offer_text(...)` (near lines 288, 383, 424, 450 and 957) expects the scripted line, `"\n\n"`, then the seeded text.
  - `test_the_turn_is_stored_and_the_thread_state_follows_it` (near line 476) already scripts an offer with `text=""` and expects the seeded text alone. It stays, and its docstring is reworded to say a blank line falls back to the seeded offer alone. No duplicate test is added.
  - `test_asking_about_an_offer_leaves_it_open` (near line 930) flips: the content is the model's answer, `"\n\n"`, then the seeded offer, and its comment says the answer goes out with the offer. The offer stays `offered`.
  - The Tell Me More assertions do not change. After the reseed, the whole `pytest` passes with pristine output; the builder records passed and skipped counts before and after, and checks that the integration tests were not skipped.
  - Round 3: `_offer_turn` in `test_turn.py` gains a keyword `answering: bool = False`, mirroring `offers.offer`. A framework with its own wording (ABCDE) expects that text alone, or with `answering` the scripted line, `"\n\n"`, then that text; any other expects the scripted line, `"\n\n"`, then the card. The assertions that call it (near lines 288, 391, 432 and 458) follow the helper, so the parametrized ABCDE cases now expect the client's text alone. `test_asking_about_an_offer_leaves_it_open` (ABCDE) passes `answering=True`, still expects the answer, `"\n\n"`, then the client's text, and its comment says a typed question is the one case where the model's line goes before the client's own wording. The blank line test near line 484 (ABCDE) is unchanged. The docstring of the parametrized offer test (near line 377, "its own line leads, and the words and the three buttons after it are the seeded offer's") and its comment near line 392 ("the shared frame never says it") are reworded to the round 3 rule; the assertion there stays.
  - Round 3: a new `backend/tests/unit/test_offer.py`, built on the real seeded `Replies` (`scripts.seed.load_replies()`) and a real `Framework` row (`Framework.model_validate(parse_framework(FRAMEWORKS_DIR / "structured_problem_solving.md"))`, the seed's own parser; the ABCDE case parses `abcde.md` the same way), with no mocks, holds the four cases of the rule: own wording alone, own wording after a question, the shared card after the line, and the card alone for a blank line. The expected card is `"Framework: {name}\n\n{description}"` filled from `framework.name` and `framework.description`.
  - Round 3: `backend/tests/evals/test_style_findings.py`, `test_the_reply_checks_skip_an_offer_the_code_wrote`, builds its reply from a literal offer turn the model could write, holding one feeling word and a framework name, then the card from `load_replies().offer.text`. For example: `"Feeling overwhelmed makes this hard. Thought Reframe could help you look at the thought. Want to try?\n\n"` followed by the formatted card. Both assertions stay (`said a framework` and `labelling` fire with `offered=False`, neither with `offered=True`), and its docstring says the offer turn is read by hand, so the model's checks are not run on it.
- **AC-8**: The real runs. `backend/scripts/eval_conversations.yaml` gains the scenario `client_job_decision`, exactly as drafted under *Feature design*, with no `expect_framework`. After the reseed, and only after muhammad's yes with `get-credits` checked first, it is run once per style: `python scripts/eval_replies.py --scenario client_job_decision --style direct --verbose`, then `--style supportive`, then `--style reflective`. Before reading a run, the builder confirms its thread has `conversation_style` set. A run passes when, read by hand from the `--verbose` output:
  - no reply before the offer opens by restating what the person just said, their words or their feeling;
  - the reply to their first message asks what the decision is;
  - no offer comes before their third message (the `first offer at message` column shows `3` or later, and `[None]` is a fail), so both sides are heard first;
  - the offer turn's first line answers what they just said, with no question and no recap, and the seeded offer follows it;
  - the reply after Try It asks nothing they already told. An offer at their fifth message or later is never tapped (the script has five lines), so this bullet is recorded "not reached", which counts as a fail, since Mani asked too long.

  `eval_replies.py` skips `validators.check` on a reply that offers, so the bridge line is judged by hand only. Each run is recorded as measured, pass or fail per bullet, in the journal note and under the measurements in `backend/PORT-STATUS.md`. A failing run is reported to muhammad, never rerun until it passes.

  **Round 2.** Round 1's three runs (2026-10-08) all failed and stay recorded as measured. After the round 2 reseed, muhammad's yes, and `get-credits`, the scenario runs three times per style, nine runs, each a separate invocation of a scratchpad wrapper (no repo change), so each run creates and removes its own user as `main()` does. The wrapper:
  - Runs `eval_replies.main()` with the same arguments as round 1 (`--scenario client_job_decision --style <style> --verbose`).
  - Prints each thread's stored `conversation_style` after the style tap, by wrapping `eval_replies._open_chat` as in round 1.
  - Wraps `eval_replies.orchestrator.send`, which every scripted turn calls. Around each call it counts that thread's `public.thread_response_styles` rows before and after: a new row is that reply's shape, and no new row means an offer turn or a dropped style, printed as "n/a, read from reasoning". After each call it prints the returned `Turn.reasoning`.
  - Fills `Turn.reasoning` by replacing `orchestrator.get_settings` alone with a function returning a copy of the settings with `ai_debug_mode=True`. `AI_DEBUG_MODE` stays off in the environment, so `composer.debug_layer` adds no debug row and the system prompt is the production one.

  The same five bullets apply, with these rules:
  - A bullet passes for a style when it holds in at least 2 of that style's 3 runs; the count is always out of 3. A run with no offer (`[None]`) fails the third, fourth and fifth bullets. The fourth is judged on the offer turn even when the third failed because the offer came too early. AC-8 passes when every bullet but the fifth passes in every style.
  - Restating, for the first bullet, graded by hand: a reply before the offer fails if it hands back a feeling they used in any of their messages so far, in any form ("frustrated" as "frustrated" or "frustrating", "afraid" as "worried"), or if it opens with a sentence retelling what they said ("You keep getting close to a decision…"). A line of care about what they are facing passes, as in the client's "Making a decision can be difficult when you keep questioning yourself." The eval's `labelling` finding is an aid only: it flags feeling words they did not use, so a feeling handed back word for word passes it.
  - The offer turn's first line, for the fourth bullet, is its text before the first blank line.
  - The fifth bullet stays as written. A reply after Try It that says their reasons back before its question is recorded as measured, not failed.
  - Every restating reply is recorded with its shape and reasoning, in the journal note and in `PORT-STATUS.md`.
  - Regression, measured only: `disclosure_no_question_needed` (the person who only wants to be heard) once per style through the same wrapper, three runs. Its findings and whether any reply reads cold or bare are recorded, not graded pass or fail.

  **Round 3.** Round 2's nine runs (2026-10-08) failed and stay recorded as measured. After the round 3 reseed, muhammad's yes, and `get-credits`, the same nine runs and three regression runs go through the same wrapper, with the same 2 of 3 rule and the same first, second, third and fifth bullets. The fourth bullet becomes: the offer turn's text before the card follows from what they just said, says in a few words how the questions could help, and asks if they want to, with no recap of their details and no feeling handed back; the card follows it. Grading rules for round 3:
  - The offer turn is split at the first `"\n\nFramework:"`. The text before it is what the fourth bullet grades. A blank text before the card fails the bullet.
  - Each run records the framework it offered. `client_job_decision` has no `expect_framework`, so the model may offer ABCDE, which has no card and carries no model line. An ABCDE offer is "not applicable" for the fourth bullet. For each style, that bullet passes when it holds in at least 2 of the runs where it applies, and the count is given out of those runs. A style with no applicable run is recorded "not measured", which fails AC-8. The ABCDE path itself is proven by AC-7's tests.
  - The wrapper is the one AC-8 round 2 describes, recreated in the scratchpad by `/develop`, since the round 2 copy does not outlive its session. It also prints each offer turn's framework id (from the offered button's `technique`).
  - `eval_replies.py` still skips `validators.check` and `says_framework` on an exchange that offers, so the model's offer is read by hand only. The comment above that skip (near line 336, "An offer is the seeded words after one line of the model's") is reworded to say that an offer turn is the model's offer and the card, or the client's own wording, and is graded by hand. `labelling` would not catch a feeling handed back in any case, since it flags only feeling words they did not use. `unasked_before_offer` still checks a little for free: a model offer with no `?` gives a "stalled" finding, since the card has no question.
- **AC-9**: In the same change:
  - `backend/PORT-STATUS.md` line 82 and the "Decisions in force" line near 151 ("once it can tell what the issue is and which set fits"): edited in place to say Mani offers once it knows what they are struggling with and what makes it hard, from their second message at the earliest, with no count beyond that floor (spec 0016).
  - `backend/PORT-STATUS.md`, chat turn step 6 near lines 73 to 78 ("The model's text and style on that turn are dropped") and the decision "The reply goes out as the model wrote it, except an offer" near lines 136 to 142: both say the model's own line goes before the seeded offer, and only its style is dropped.
  - `backend/PORT-STATUS.md`, "Open decisions for muhammad": one line to tell the client that the offer now opens with one line of Mani's own before their wording, and that no count of exchanges is enforced beyond holding the first offer until the person's second message.
  - Spec 0012's AC-11 pass criterion "an offer at their message 2 to 4" was changed by this spec's design run to point here; the builder checks it still reads so.
  - A journal note records the counts before and after, the three runs and anything learned.
  - Round 2: "Open decisions for muhammad" gains one line to tell the client that the Supportive and Reflective style lines were reworded from their text (E10, E11) so care is about what the person faces, never their feeling handed back. The measurements gain the round 2 runs. The journal note gains a round 2 section.
  - Round 3, edited in place in `backend/PORT-STATUS.md`: chat turn step 6 and the decision "The reply goes out as the model wrote it, except an offer" say that for a set without the client's wording the model's line is the offer and the name and description follow, and that ABCDE goes out in the client's words alone unless it answers a typed question. In "Open decisions for muhammad", the spec 0013 line ("every offer now opens with the same lead") and round 1's line ("one line of Mani's own before their wording") are edited in place to say the same for the client. The measurements gain the round 3 runs, and the build journal note a round 3 section.

**Not in this spec**:
- What Mani says after the questions end, and the body check (scope feature 21, waiting on the client).
- The per style offer text for the five frameworks without a client document (feature 17).
- The `ending` and `after_framework_questions` lines, which also say "reflect". They belong to the ending and to feature 21.
- Other lines that still lean toward restating, left alone on purpose and only measured: `mirror and hold`, `acknowledgment` ("receive what they said"), `in_a_framework`'s "say what you now understand" for a stage still partial, the `ending` line "Then reflect their answer", `ctx.after_framework_questions`' "Reflect what they said", and Reflective's lead "Mirrors and explores". The first two apply before an offer; the rest belong to later parts of the conversation. The Reflective style line was on this list in round 1 and is replaced in round 2 (E11).
- Whether Mani offers the right set across many conversations (feature 11). The runs here measure one conversation in three styles.
- A code check on the bridge line. Spec 0006 removed reply repairs on purpose; the runs measure whether the prompt line holds.
- The say back after Try It (round 1: Direct and Supportive said their reasons back before the first stage question). Measured only. If it persists, the next line to look at is `stage_lines`' "built from what they have told you, in their words".
- Tell Me More for the five sets without the client's wording repeats the card the offer just showed (`more_text` and the round 3 `offer.text` are the same card). True before round 3 as well, since the old `offer.text` ended in the same card; it waits for their documents (feature 17).
- The framework's name on the card, which the client's intro document says not to give. An open decision from spec 0013, unchanged here.
- The `acknowledgment` move and the `goal` line's "Help them feel heard". Round 3 changes the reasoning step instead (E12), so a pass or a fail traces to one lever.

## Decision

**Chosen option**: Option 1: replace six prompt lines one for one, and send the model's own line before the seeded offer.

Round 2 keeps this option and widens the cut: four more lines that teach care as naming their feeling (E8 to E11), and E6 made concrete about what the seeded offer already says.

Round 3 changes the offer half of Option 1. For the five sets without the client's wording, the model's line is the offer and the seeded part is the card (name and description); ABCDE goes out in the client's words alone, with the model's answer first only after a typed question. The restating is worked through the reasoning step written before the reply (E12), and the timing through one concrete span in E5.

The model still decides when to offer and which set, the code still writes the offer from seeded rows (spec 0013, spec 0015), and the floor of the person's second message stays. What changes is what the prompt asks for before the offer (what the issue is and what makes it hard, without handing their words back) and that the model's reply to their last message is no longer discarded on the offer turn.

**Implementation skills**: none (backend seeded content, one small Python change, tests and the eval scenario).

## Rationale

Reasoning and options: see [rationale.md](rationale.md).

## Feature design

**Data model and API surface**: no change. No migration, no new column, no endpoint or response field change. An offer message's `content` holds one more line; its `prompt_options` are as today.

### Prompt edits

Each edit replaces exactly one existing line with exactly one line. Indentation and YAML keys stay as they are.

**E1**, `mani_base.md`, `moves`, line 26:
- Old: `  mirroring: the one part that matters most, in your own words. Never a recap, never their sentence handed back, never the same way twice running.`
- New: `  mirroring: only to check you understood something they did not quite say, so they can correct it. Never their words or their feeling handed back.`

**E2**, `mani_base.md`, `reply_shapes`, line 33:
- Old: `  mirror and ask: reflect the part that matters, then ask one question.`
- New: `  mirror and ask: a mirror, as mirroring says, then one question.`

**E3**, `response_format.md`, `reasoning.steps`, line 56:
- Old: `    - What do they need right now, whether comfort, space, acceptance, agency or a question about how they feel, and what is their feeling in their words?`
- New: `    - What do they need right now, whether comfort, space, acceptance, agency or to be understood?`

**E4**, `mani_base.md`, `questions`, line 46:
- Old: `  - Ask as a perceptive friend would, in plain words, about what happened or what it is like for them. Never ask for what they made clear or the same thing the same way twice, and if they have named no feeling or problem, pick up the one thing they gave rather than asking for one.`
- New: `  - Ask as a perceptive friend would, in plain words, about what happened or what it is like for them. Never ask for what they made clear or the same thing the same way twice. Until you know what the issue is, ask what it is, plainly, before asking about any part of it.`

**E5**, `mani_base.md`, `offers`, line 50:
- Old: `  - Offer once you can tell what the issue is and which set fits, and do not keep asking once it is clear. Never say its id.`
- New: `  - Offer once you know what they are struggling with and what makes it hard for them, and when they are weighing a choice, what pulls them each way. That is less than every detail, since the set's own questions ask the rest. Do not keep asking once it is clear. Never say its id.`

**E6**, `mani_base.md`, `offers`, line 51:
- Old: `  - To offer, carry one button with the framework id as technique. The offer's words and its three buttons replace your reply, so write it as one short line.`
- New: `  - To offer, carry one button with the framework id as technique. Your text goes just before the offer's words, which say what the questions do and ask if they want to, so answer only what they just said, in a few words, with no question and no recap.`
- Round 1 built an earlier New, quoted under *Round 2 edits*; the round 2 build matches on that.

**E7**, `response_format.md`, `ctx`, line 18:
- Old: `  framework_starting: they just said yes. Judge every stage on stage_ledger against all they told you before, in state.stages, and ask the first one not known. If earlier ones are known, say them back in a clause, in their words, never asking them to confirm.`
- New: `  framework_starting: they just said yes. Judge every stage on stage_ledger against all they told you before, in state.stages, and ask the first one not known, built on what they already told you. Never say it back or ask them to confirm it.`

The line numbers are those in the working tree on 2026-10-08. If they have moved, match on the old text.

### Round 2 edits

Each replaces exactly one line, or a span within one line, in `mani_base.md`. All five parse as YAML (checked with the venv's `yaml`) and hold no colon followed by a space inside a list item.

**E6, round 2**, `offers`, line 51:
- Old (built in round 1): `  - To offer, carry one button with the framework id as technique. Your text goes just before the offer's words and its three buttons, so keep it short, answering what they just said, with no question, no recap and no offer of your own.`
- New: `  - To offer, carry one button with the framework id as technique. Your text goes just before the offer's words, which say what the questions do and ask if they want to, so answer only what they just said, in a few words, with no question and no recap.`

**E8**, `rules`, line 18:
- Old: `  - Use their words. Never name a feeling they have not named, and never make it bigger than they did.`
- New: `  - Never hand their feeling back to them, and never name one they have not named or make it bigger than they did.`

**E9**, `reply_shapes`, line 31:
- Old: `  warmth lead: lead with care, then ask.`
- New: `  warmth lead: a few words of care about what they are facing, then ask.`

**E10**, `styles.supportive`, line 41, a span within the line; the rest of the line is unchanged:
- Old: `Acknowledges what they share without over validating every statement`
- New: `Acknowledges what they are facing without over validating every statement`

**E11**, `styles.reflective`, line 42, a span within the line; the rest of the line is unchanged:
- Old: `Reflects the meaning and important details in what they actually say, selectively, when it adds value, stays close to their language without repeating it back, and asks`
- New: `Reflects the meaning behind what they say, never its details, selectively, when it adds value, and asks`

### The offer step

Rounds 1 and 2 only, superseded by *The offer step, round 3* below; build round 3 from that section.

In `orchestrator.send`, where `offers.offer(...)` returns the seeded text today and replaces `checked.text`, the text becomes the two joined by a blank line, skipping a blank model line:

```python
text = "\n\n".join(part for part in (checked.text, seeded) if part)
```

`checked.text` is already stripped by `guards.check`. The comment above that step changes from "its words and buttons are the seeded offer's, so no style is recorded for text the person never sees" to say that the model's line leads and the seeded offer follows, and that no style is recorded because the shape it reported describes a reply, not a bridge line. `offer.py` does not change.

### Round 3 edits

Each replaces exactly one line or one span. E6 round 3, E5 round 3 and E12 were checked on 2026-10-08: each Old matches once in the round 2 tree, and both files still parse as YAML.

**E6, round 3**, `mani_base.md`, `offers`, line 51:
- Old (built in round 2): `  - To offer, carry one button with the framework id as technique. Your text goes just before the offer's words, which say what the questions do and ask if they want to, so answer only what they just said, in a few words, with no question and no recap.`
- New: `  - To offer, carry one button with the framework id as technique. Your text is the offer: a step from what they just said, a few words on how the questions could help, then ask if they want to, with no recap.`

**E5, round 3**, `mani_base.md`, `offers`, line 50, a span within the line; the rest of the line is unchanged:
- Old: `what pulls them each way`
- New: `what draws them to each option, not only that both have reasons`

**E12**, `response_format.md`, `reasoning.steps`, line 56:
- Old (E3's result): `    - What do they need right now, whether comfort, space, acceptance, agency or to be understood?`
- New: `    - What are they facing, and what do you not yet know about it?`

**R1**, `replies.md`, `offer.text`, line 36:
- Old: `  text: "We'll go through a few focused questions. By the end, you will have turned a problem that feels unclear or overwhelming into a practical next step. Would it help to work through it together?\n\nFramework: {name}\n\n{description}"`
- New: `  text: "Framework: {name}\n\n{description}"`
- The comment above `offer:` (three lines) becomes exactly:
  ```
  # The card the code puts after the model's offer, for a set with no wording of its own under
  # by_framework below: the model's words are the offer, and this follows them, filled from that
  # framework's row. {name} is its name and {description} its summary, the only two fields allowed,
  # and both are required. Spec 0016.
  ```
- The `by_framework` comment's "sent instead of `text` and `more_text` above" becomes "sent instead of `text` and `more_text` above, alone, with the model's line dropped unless it answers a typed question about the offer".
- The `Offer` docstring in `backend/mani/prompts/replies.py` becomes "The card the code puts after the model's offer, the client's own offer wording where it exists, and the reply to Tell me more."
- The `send` docstring in `backend/mani/routers/messages.py` (the sentence "An offer is the exception … written from seeded rows (`chat/offer.py`)") becomes: "An offer is the exception (`chat/offer.py`): where the client wrote it, it goes out in their words, and otherwise the model's words are followed by a seeded card; its buttons, and the reply to Tell me more, which makes no call, come from seeded rows."
- The `OfferText` validator (both fields required) still holds, so `seed.py` and `test_config_rows.py` need no change.

### The offer step, round 3

`offer.py`:

```python
def offer(
    replies: Replies, framework: Framework, style: str, line: str, *, answering: bool
) -> tuple[str, list[dict]]:
```

- `styled = _styled(replies, framework, style)`. When `styled`: the text is `styled.text`, or, when `answering`, `"\n\n".join(part for part in (line, styled.text) if part)`.
- Otherwise: `"\n\n".join(part for part in (line, _filled(replies.offer.text, framework)) if part)`.
- The buttons are as today. The docstring says the client's own wording stands alone and the model's line is the offer for the rest.

`orchestrator.send`, at the offer step: `answering` is true when `deferred` and the outcome is still `TechniqueOutcome.OFFERED` (the turn answered a typed question by offering again). The call becomes `offers.offer(config.replies, config.registry.get(offered), style_now, checked.text, answering=answering)`, and its text replaces `checked.text` as is. The comment above the step says the model's line is the offer for a set without the client's wording and the client's wording stands alone, except after a typed question, and that no style is recorded because the shape describes a reply, not an offer.

### The eval scenario

Added to `scripts/eval_conversations.yaml` beside the other `client_` scenarios. The first three lines are the client's, word for word, from `docs/client-share-docs/mani-response-feedback-2026-10-08.md`.

```yaml
# The client's job decision conversation (feedback of 2026-10-08), run once per style (spec 0016).
# Their principle: understand the problem, introduce the set naturally, use what they already shared.
- name: client_job_decision
  turns:
    - "I'm facing an important decision, and I keep going back and forth. Every time I think I've made up my mind, I start questioning myself again. I'm frustrated because I don't understand why I can't just decide."
    - "I'm trying to decide whether to accept a new job opportunity or stay where I am. There are good reasons for both, and I'm afraid of making the wrong choice."
    - "The new job offers better pay and more responsibility, but I've been at my current company for years. I know the people, I'm comfortable there, and I'm worried I might regret leaving."
    - "@accept|I just want to stop going back and forth and be able to decide."
    - "@accept|Okay, let's try it."
```

If Mani offers after the third message, the fourth line taps Try It and the reply is the first stage question; the fifth is then skipped. If Mani offers after the fourth, the fifth taps it. An offer after the fifth is never tapped (AC-8).

### Value sourcing

| Action | Value produced or shown | Source |
|---|---|---|
| Any reply before an offer | whether to ask what the issue is, and whether to mirror | the model, from E1 to E4 |
| `[ctx]` offer timing | `cooldown_passed` | `context.cooldown_passed`, from `tuning.offers.clear_offer_after` (`2`, unchanged) |
| Offer turn | when to offer and which set | the model, from E5 and each framework's Starts when, Sounds like and Skip when lines (unchanged) |
| Offer turn | the bridge line | the model's `text` on that turn, after `guards.check`; on a typed question about the offer, its answer |
| Offer turn | the offer's words | `offers.offer`: `replies.offer.by_framework.<id>.<style>.text`, else the shared `offer.text` filled from the framework row (spec 0015) |
| Offer turn | the style for the seeded words | `context.resolve_style(ctx, tuning.offers.default_style)`, as today |
| Offer turn | the stored and sent content | derived: bridge line, `"\n\n"`, offer words; offer words alone when the bridge is blank |
| Offer turn | the buttons | `offers.offer`, unchanged |
| Reply after Try It | the first stage question | the model, from E7, `stage_ledger` and the framework's Stages line |
| Eval run | pass or fail per bullet of AC-8 | read by hand from `--verbose`; `first offer at message` from `eval_replies.py` |
| Any reply before an offer | care without their feeling handed back | the model, from E8 to E11 |
| Round 2 eval run | each reply's shape | the new row in `public.thread_response_styles` for that thread across one `orchestrator.send`, counted before and after the call by the wrapper; none on an offer turn |
| Round 2 eval run | each reply's reasoning | `Turn.reasoning` returned by `orchestrator.send`, filled because the wrapper replaces `orchestrator.get_settings` with a copy where `ai_debug_mode` is true; the composer's own settings stay off |
| Round 2 eval run | pass per style | derived: a bullet holds in at least 2 of the style's 3 runs; a run with no offer fails bullets 3 to 5 |
| Round 2 eval run | the offer turn's first line | derived: the offer turn's text before the first blank line (round 2 only; round 3 splits at `Framework:`, below) |
| Round 3 offer turn, a set without its own wording | the offer's words | the model's checked `text`, from E6 round 3 and the set's Description line in the Framework Index |
| Round 3 offer turn, a set without its own wording | the card after it | `replies.offer.text` (R1), filled with `{name}` and `{description}` from the framework row by `offer._filled` |
| Round 3 offer turn, ABCDE | the offer's words | `replies.offer.by_framework.abcde.<style>.text`, the style from `context.resolve_style` |
| Round 3 offer turn | `answering` | derived in `orchestrator.send`: `deferred` and the outcome still `TechniqueOutcome.OFFERED` after the deferred branch |
| Round 3 offer turn | the stored and sent content | `offers.offer(..., line, answering=...)`, as AC-4 round 3 states |
| Any reply | the first reasoning step | the model, from E12 |
| Round 3 eval run | the offer turn's text before the card | derived: the offer turn's text before `Framework:` |

### Key invariants

- `mani_base.md` plus `response_format.md` never end this change with more lines than 145.
- The offer's words, its buttons and the Tell Me More reply come only from seeded rows. The model contributes a short text before the offer and nothing after it.
- No offer before the person's second message, as told by `cooldown_passed` (told, not enforced, as today).
- The code does not inspect or repair the bridge line.
- Round 3 changes the second invariant: for a set without the client's own wording, the model writes the offer's words and the seeded rows supply only the card and the buttons. Where the client wrote the offer (ABCDE), their words go out unchanged, and nothing of the model's goes before them except an answer to a typed question.
- Whether the model's line goes out is decided from the framework row and the turn's path, never from the line's content.

### Security model

No change. The same user scoped connection, the same RLS and the same `mani_service` privileges. The bridge line is the model's reply text, stored where reply text is stored today. Conversation content stays out of logs and Sentry: the offer log line still carries ids and a flag only.

### Configuration required

None. No new environment variable, tuning key or row field.

### Failure and edge cases

- **Blank model line on an offer turn**: the seeded offer goes out alone (AC-4, AC-7).
- **The bridge line asks a question or recaps**: sent as written, so the person sees two questions or a recap before the offer. Not repaired (spec 0006); AC-8 measures it, and a failure is reported to muhammad.
- **The bridge line itself offers** ("there are some questions we could go through"): the offer reads twice. Same handling: measured, not repaired. E6 says the offer's own words already say what the questions do, for this reason. Round 1 measured it: "I can help you sort through the choice" came back under the earlier wording.
- **Safety concern on an offer turn**: the guard drops the offer as today, and the model's line goes out alone, as today.
- **An offer before `cooldown_passed`**: logged by id, not enforced, as today.
- **A typed question about a live offer** ("what would that involve?"): the model answers and offers again, and its answer now goes out before the seeded offer, where today it is dropped (AC-4). The offer stays `offered`.
- **Tell Me More, Try It, Keep Chatting, a typed yes, and typing past an offer**: unchanged. Taps are matched by stored button keys, which do not change; a typed yes or no is read from `state.accepted` as today, and no offer is made on those turns.
- **Offers stored before this change** (no bridge line): read and answered exactly as before.
- **Deploy order**: the reseed must land before the new code. Old code with the new prompt drops the model's line, which is today's behavior and harmless. New code with the old prompt prepends a line written under "write it as one short line", which is often an offer sentence, so the offer would read twice. No row model changes, so neither order fails a turn.
- **Round 3, a blank model line on an offer for a set without its own wording**: the card goes out alone, with the three buttons. No fallback lead.
- **Round 3, the model's offer recaps or names their feeling**: sent as written (spec 0006). The fourth AC-8 bullet measures it.
- **Round 3, the model offers ABCDE and writes its own offer**: dropped by rule; the client's text goes out alone. After a typed question, the answer goes first and may end in its own ask, so the person can read two asks. Accepted, since the person asked something and gets an answer.
- **Round 3, deploy order**: reseed first, as before. Old code with the new rows joins the model's offer line to the card, which reads correctly for the five sets; for ABCDE it puts the model's offer before the client's, the double offer of round 2, until the code lands. New code with the old rows drops the model's line for ABCDE (fine) and puts the model's offer before the old generic lead for the rest (a double offer). Reseed and deploy together; neither order fails a turn. Restart after the reseed: the running app keeps prompts and replies in its prompt cache (`orchestrator.cache`) until it expires, so without a restart the old rows outlive the code change.
- **Round 3, a typed question about an offer for one of the five sets**: E6 round 3 ("a step, how the questions could help, then ask") and `offers` line 54 ("Asked what it involves, answer in two sentences of your own") both apply, and either may win. The text goes out with the card after it whichever wins. Left open on purpose, since the runs do not reach it; measure it if it shows up in real transcripts.

### Critical test scenarios

- Offer turn with a scripted bridge line: stored and returned content is the line, a blank line, then the seeded offer for the thread's style; buttons and technique row as before. Verifies **AC-4**, **AC-7**.
- Offer turn with a blank scripted line (the existing test near line 476): content is the seeded offer alone. Verifies **AC-4**, **AC-7**.
- A typed question about a live offer, answered and offered again: content is the answer, a blank line, then the seeded offer; the offer stays `offered`. Verifies **AC-4**, **AC-7**.
- Tell Me More after an offer with a bridge line: the Tell Me More reply is the seeded text alone, no model call. Verifies **AC-4**.
- First message in a new thread: `cooldown_passed: no`; second: `yes` (existing tests, unchanged). Verifies **AC-3**.
- `wc -l` and `wc -w` on the two prompt files, and `git diff` limited to E1 to E7. Verifies **AC-1**, **AC-2**, **AC-3**, **AC-5**, **AC-6**.
- The three real runs. Verifies **AC-8**.
- Round 2: `wc -l`, `wc -w` (74, 71, 3424), and `git diff` on `mani_base.md` since round 1 touching only E6, E8, E9, E10 and E11. Verifies **AC-1**, **AC-4**, **AC-6**.
- Round 2: the nine real runs with shapes and reasoning printed, 2 of 3 per bullet per style. Verifies **AC-8**.
- Round 2: `disclosure_no_question_needed` once per style, measured only. Verifies **AC-8** (regression record).
- Round 3, unit (`test_offer.py`, real seeded rows): ABCDE in each style gives the client's text alone; ABCDE with `answering` gives the line, a blank line, then the client's text; Structured Problem Solving gives the line, a blank line, then the card; a blank line gives the card alone. Verifies **AC-4**, **AC-7**.
- Round 3, integration: an ABCDE offer turn's content is the client's text alone, whatever the scripted line; a Structured Problem Solving or Thought Reframe offer turn is the scripted line then the card; a typed question about a live ABCDE offer gives the answer then the client's text, and the offer stays `offered`. Verifies **AC-4**, **AC-7**.
- Round 3: `wc -l` and `wc -w` (74, 71, 3422), and `git diff` since round 2 touching only E6, E5's span, E12 and `replies.md`'s `offer.text` with its comment. Verifies **AC-1**, **AC-3**, **AC-6**.
- Round 3: the nine graded runs and three regression runs. Verifies **AC-8**.

## Migration plan

**Strategy**: no schema migration. One change, shipped whole, with the reseed before the code.
**Phases**:
1. Code, content and tests together on this branch. muhammad reviews the seven prompt edits.
2. After his yes, `python scripts/seed.py`, restart, the full `pytest`.
3. After a second yes, and `get-credits`, the three real runs (AC-8).
4. Hosted: reseed first, then deploy and restart.
5. Round 2 (content only, no code): muhammad's yes on the five lines, reseed, restart, the full `pytest`; after a second yes and `get-credits`, the nine runs. Hosted takes the reseed alone.
6. Round 3 (code and content): code, tests and the four content edits on this branch; muhammad's yes, reseed, restart, the full `pytest`; after a second yes and `get-credits`, the nine runs and three measured. Hosted: reseed and deploy in the same window (see *Failure and edge cases*, round 3 deploy order).

**Rollback**: revert the commit and reseed. No data is touched. Offers stored with a bridge line stay readable, and their buttons are matched by stored keys as before.
**Risks**: between a hosted code deploy and its reseed, offers read twice (see *Failure and edge cases*, deploy order). Reseeding first removes it.

## Build plan

The build approach is Tracer Bullet (scope header): one thin thread through the offer turn first, then the prompt cuts, then the real runs and the close out.

1. Tracer: the bridge. Join the model's line and the seeded offer in `orchestrator.send` and update the comment there. Apply E6 to `mani_base.md`. Update `_offer` and the offer content assertions in `test_turn.py`, and add the blank line test. Reseed locally, restart, run `tests/integration/test_turn.py`. Satisfies **AC-4**, **AC-7** (offer tests).
2. The prompt cuts. Apply E1, E2, E3, E4, E5 and E7. Check `wc -l` (74 and 71) and `wc -w` (under 3616 together) and that `git diff` on the two files touches only E1 to E7. Reseed, restart, run the whole `pytest` with counts before and after and the integration tests checked. Satisfies **AC-1**, **AC-2**, **AC-3**, **AC-5**, **AC-6**, **AC-7**.
3. The scenario and the real runs. Add `client_job_decision`. Ask muhammad, check `get-credits`, then one run per style, each confirmed to have `conversation_style` set, each read against AC-8 and recorded as measured. Satisfies **AC-8**.
4. Close out. Edit `PORT-STATUS.md` in place as AC-9 lists, check spec 0012's AC-11, and write the journal note. Satisfies **AC-9**.
5. Round 2. Apply E6 (round 2), E8, E9, E10 and E11. Check 74 and 71 lines, 3424 words, the YAML parse and the diff. After muhammad's yes, reseed, restart, and run the whole `pytest` (684 passed and the 4 JWKS skips at round 1, integration not skipped). After a second yes and `get-credits`, the nine runs through the wrapper (wrapping `orchestrator.send` and `orchestrator.get_settings`, environment debug off), each with `conversation_style` confirmed and every reply's shape and reasoning printed, then `disclosure_no_question_needed` once per style. Grade with the 2 of 3 rule, record per bullet per style, and update `PORT-STATUS.md` and the journal. Satisfies **AC-1**, **AC-4**, **AC-6**, **AC-8**, **AC-9**.
6. Round 3, as one tracer through the offer turn then the prompt swaps:
   1. The rule: `offers.offer` takes the line and `answering`, and the orchestrator computes `answering` and passes `checked.text`. Write `tests/unit/test_offer.py` first, red, then the code. Satisfies **AC-4**, **AC-7**.
   2. R1 (`offer.text` and both comments in `replies.md`), the `Offer` and `send` docstrings, then `_offer_turn` with `answering`, the ABCDE expectations and reworded docstrings in `test_turn.py`, `test_style_findings.py`'s offer test, and the skip comment in `eval_replies.py`. Satisfies **AC-4**, **AC-6**, **AC-7**, **AC-8**.
   3. E6 round 3, E5 round 3, E12. Check 74 and 71 lines, 3422 words, the YAML parse and the diff. Satisfies **AC-1**, **AC-3**, **AC-6**.
   4. After muhammad's yes: reseed, restart, the full `pytest` with counts before and after (684 passed and 4 JWKS skips at round 2, integration 147 not skipped). After a second yes and `get-credits`: the nine runs and three measured, through the round 2 wrapper, recreated, also printing each offer's framework id. Grade with the round 3 rules of AC-8 (the split at `Framework:`, ABCDE not applicable, blank fails) and the 2 of 3 rule. Satisfies **AC-7**, **AC-8**.
   5. `PORT-STATUS.md` in place and the journal round 3 section. Satisfies **AC-9**.

## Consequences

**Positive**:
- The person's last message before an offer gets an answer, so the offer follows from the conversation instead of cutting across it.
- A question about an offer finally gets the answer `offers` line 54 has always asked the model to write; until now the code dropped it.
- The prompts stop asking the model to hunt for and hand back a feeling, the root of the client's points 1, 4, 6 and 7.
- No count of exchanges: the client's "understand the problem" is the rule, with only the existing floor beneath it.
- No new rule, no new line, no new key; each change is one line swapped and a reseed.

**Negative / tradeoffs**:
- The offer is no longer entirely seeded text. The model's line is unchecked, so a recap or a second question can come back, and only real runs show it.
- "What makes it hard" is a judgment the model can read as needing more questions, which is the late offer problem of spec 0012 in reverse. One conversation per style is a small sample.
- Removing "pick up the one thing they gave rather than asking for one" means a vague opener ("I'm upset") now gets a plain "what's going on" question, as the client writes, rather than a question built on their words.
- Three real runs spend the client's credit, about the cost of a three run baseline.
- The deploy order constraint (reseed before code) applies again, as for specs 0013 and 0015.
- Round 2 rewords two of the client's own style lines (Supportive, Reflective). muhammad allowed wording fixes for comprehension, but the client has to be told (AC-9).
- With "Use their words" gone from `rules`, nothing general asks for their words any more; the stage questions keep it in `stage_lines` and `in_a_framework`. A reply could drift toward Mani's own phrasing for what they said, which the `labelling` finding still catches for feelings.
- Twelve real runs (nine graded, three measured) cost about four times round 1, about 0.24 dollars. Measured on 2026-10-08: 0.03 dollars for all twelve.
- Round 3: the offer for five sets is the model's unchecked words, so a recap or a feeling handed back can return in the offer itself; only the runs show it. The generic lead (spec 0013, muhammad's wording) is gone.
- Round 3: an ABCDE offer answers nothing of what the person just said. The model's line is written under E6 and then dropped, and the client's words go out alone. That is a deliberate trade for the client's own wording, and it is close to the scripted feel their point 3 names; if they object, the answer is their wording, not a model line in front of it.
- Round 3: ABCDE and the other five now take two different paths through `offers.offer`. The difference is a property of the row (has the client written it), so a sixth framework's client document moves it from one path to the other with no code change.
- Round 3: E12 drops "comfort, space, acceptance, agency" from the first reasoning step. The person who only wants to be heard still has `questions`' exception and the `mirror and hold` and `presence only` shapes; the regression runs check that they still get space.

**Neutral**:
- No schema, API, button, tuning or framework file change.
- The `mirror and ask` shape name stays, though its meaning narrows. Old stored shapes stay valid.

## Follow-up

- [ ] Tell the client the offer now opens with one line of Mani's own before their wording, and that only the first message is held back from an offer (AC-9 records it).
- [ ] `.claude/BACKEND.md` says the offer's "text and buttons … are written by the code from seeded rows"; once built, the model's leading line makes that partly untrue. `/sync` owns that file.
- [ ] If the runs show the model asking too long before offering on other issues, measure it under feature 11 before touching E5 again.
- [ ] If round 2 still restates, the printed shapes name the line to look at next (for example `acknowledgment` if the shape is `warmth lead` and the line still names a feeling).
- [ ] Spec 0012's AC-1 and its quoted style lines are superseded by E8, E10 and E11.
- [ ] Spec 0013's "every offer opens with the same lead" is replaced by round 3 (R1). Its status line is left as it is; a note there pointing here is `/architect`'s to add when 0013 is next touched.- [ ] If round 3 still restates, the next levers are `goal`'s "Help them feel heard" and `moves.acknowledgment`, then the reply schema itself.
