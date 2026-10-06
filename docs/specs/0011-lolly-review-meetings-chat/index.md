# 0011. Mani follows Lolly's review of the meetings chat

**Date**: 2026-10-06
**Status**: In Progress

## Summary

Lolly tested a Direct Thought Reframe conversation (left out of meetings) and reviewed it line by line. Mani sounded written rather than spoken, made her facts sound worse than she said, hid the framework's name, asked her to confirm what she had already said, put "Skip this one" under every question, asked about the body twice, and after she said the whole chat was horrible it asked what next and offered another breathing exercise. This spec makes Mani do what she asked: plain words in her own terms, the framework named, no filler, a stated conclusion instead of a worksheet question, one body question, and a plain stop when it did not help. It also takes in her wider ask, that Mani talk like a plain, down to earth therapist who can handle anything, including a person's own open questions, without ever claiming to be a therapist or crossing a guardrail. It changes prompts, framework content and a few code paths in the chat turn; there is no schema change and no new endpoint.

## Requirements

Linked scope feature: row 44 in [docs/scope/conversation.md](../../scope/conversation.md), "Mani follows Lolly's review of the meetings chat". Source, newest first: Lolly's review of 6 October 2026 (transcribed by this spec into `backend/docs/specs/client-review-meetings-chat-2026-10-06.md`), then the sources spec 0010 lists. muhammad, 2026-10-06: "make it as she is saying", and later the same day: "the client wants to have plain natural therapist with down to earth. that is capable to handle any situation (even the open ended questions). it must never cross the guardrails." muhammad settled that this means talking like a good therapist, never claiming to be one, and that "open ended questions" means the person's own questions to Mani. This spec replaces spec 0010's AC-4 rule that no framework name reaches the person, and changes parts of its AC-6 (the check in line) and AC-7 (what follows the practice). Everything else in 0010 stands: the six offer refusals, one chat call per turn, one extra attempt per step, every ending into the somatic check, the outcome table.

**User stories**:
- As a person talking to Mani, I want it to talk like a person and use my own words, so that I feel listened to and not processed.
- As a person offered a framework, I want to know what it is called and what we will look at, so that I can decide whether to try it.
- As a person inside a framework, I want Mani to move on when I have already said something and to say the conclusion when it is clear, so that it feels like a conversation and not a form.
- As a person for whom it did not help, I want Mani to stop plainly, so that I am not handed another decision or another exercise.
- As a person who asks Mani something directly ("What do you think I should do?", "Is this normal?"), I want a plain answer, so that I am not just asked another question back.

**Acceptance criteria**:

- **AC-1** (the offer names the framework): an offer reply contains the framework's stored display name (`admin.frameworks.name`, matched without regard to case), in one sentence of Mani's own on what it will look at in their situation, then the style's permission question and the three buttons, both unchanged from spec 0010. The model is told the name and what it looks at on both routing paths: `composer.framework_index` gains a column "What you look at together" holding each framework's `summary` (the path hosted runs, where `SEMANTIC_ROUTER` is off and the model chooses the offer), and on a turn whose router `action` is an offer `[ctx]` also carries `offer_name:` and `offer_looks_at:`. The name check runs on the model's part after the permission question is stripped: the full stored name as a whole word, ignoring case, with a space and a hyphen treated as the same ("Structured Problem Solving" matches "structured problem-solving"); a partial name or a bare acronym ("ACT", "DBT") does not count. When it is missing, `repairs` puts `It's called {name}.` after the model's part and before the permission question (alone, when the part is empty) and logs a note. The path that drops an offer sitting under another question is unchanged. The word "framework" and the framework id still never reach the person. The base prompt rule "never its name, its id or the word "framework"" becomes "say its name; never its id or the word "framework"".
- **AC-2** (Tell me more names and explains it): on the turn answering **Tell me more** (tapped, or a typed question about the waiting offer), `[ctx]` carries `offer_name:` and `offer_looks_at:` and no longer `explain_offer:`. The reply is two or three sentences in the style that name the framework and say what you will look at together, fitted to their situation, with no question; the two buttons stay as today. On an explaining turn `repairs` removes any question from the reply in code (as `without_questions` does elsewhere) and keeps the two buttons, rather than sending it down the path that drops offer buttons under a question. When the name is missing, `repairs` puts `It's called {name}.` at the start, matched as in AC-1. When the turn is explaining because they typed a question past the offer (`deferred` and "?" in their message, `orchestrator.send`) and the question is not about the offer ("Is this normal?"), the reply answers their question first in a sentence (AC-19), then explains; `[ctx]` carries `their_question: yes` on such a turn so the model knows. The per style texts in `greeting.EXPLANATIONS` are deleted, so "focused questions", "without rushing you" and "You stay in control of what you want to share" have no source left.
- **AC-3** (what each framework looks at): the six framework files' `summary` lines are rewritten as one plain sentence each on what you look at together, modelled on Lolly's Thought Reframe example ("the thought you're having, what supports it, what doesn't, and whether there's a more accurate way to look at the situation"), with no promised result and no feeling word, and reseeded.
- **AC-4** (no filler on a yes): accepting an offer (tapped or typed) gets no consent line. The three "one step at a time" lines leave `mani_base.md`, `response_format.md` and `context._START_NOTE`. The first reply in the framework asks the first step their words have not already met, with at most one short line before it.
- **AC-5** (a step the offer was built on is already met): every framework's first question step (`thought`, `activate`, `situation`, `stopped`, `stop`, `problem`) has its `ready_when` rewritten so that what they said before the offer meets it, including the thought, event or problem the offer sentence named; Thought Reframe's `thought` no longer asks for a mirror and a confirmation. The prompt says that the step an offer was built on is met when they accept. Reseeded.
- **AC-6** (no Skip this one): no reply carries a **Skip this one** button. `repairs.SKIP_LABEL` and the code that attaches it go, and the prompt line "Every question carries **Skip this one**" goes. A skip still moves on: `repairs.skips_the_step`, the `skipped` `[ctx]` line and the step advance stay, and `skipped` is computed from `skips_the_step(content)` alone, whether the words were typed or came from a tap. So a **Skip this one** button already stored on an open thread's newest message still skips when tapped after deploy, because its label matches the typed pattern; no compatibility code is written for it.
- **AC-7** (questions anyone can answer at once): the prompt says each step's question is concrete to their situation, using their words for the thing asked about, and the stored `ask` is a guide, never sent word for word when it would be abstract. Thought Reframe's asks become: `significance` "What makes that thought hard for you?", `facts_against` "Is there anything that makes you think it might not be true?", `alternative` "What's one other reason this could be happening?", in all three styles. Reseeded.
- **AC-8** (a stated conclusion at the last step): at Thought Reframe's `reframe` and ABCDE's `balanced`, when their own statements support a conclusion without a new assumption, Mani states it plainly, in their words and no further (what they know, what does not fit the worry, and what is still unknown, as in "So far you know X, but Y and Z. There isn't enough here to know W."), asks nothing, and reports `ending: resolved`; the statement is the bridge line in front of the body question (AC-10). When it would have to infer something, it asks the step's fallback question instead: Thought Reframe "What would be a more balanced thought?", ABCDE "What would be a more balanced belief?" (each specification's primary question). "Putting those together, what would you say is true about this?" leaves both files. The statement never sounds like correcting their thinking ("what you were filling in"). Backstop in `repairs._stage_after_a_reply`: a reply to the last question step that carries no question and no `ending` is recorded as `ending: resolved` with the move to `somatic_checkin`, and a note is logged, so a stated conclusion the model forgot to report never leaves the person with a statement and nothing to answer.
- **AC-9** (spoken words, never stronger than they said): `mani_base.md` replaces "Before a question, say in one short line of your own what you understood ..." with: a question may stand alone; a line before it only when it adds something; their own words for the facts they gave; never stronger than what they said (a worry about a possibility stays a possibility, "left out of meetings" is not "dropped"); spoken, not written; no filler line. Direct "leads toward clarity first; a next step or action comes only once what is happening is understood". `tests/evals/test_base_prompt.py` asserts the new rules, and the body stays within `MAX_LINES` (130). The lines this spec removes (the consent lines, the Skip rule, the old say back rule) pay for the ones it adds; if the rules of AC-9, AC-18 and AC-19 still do not fit, the cap is raised by exactly the lines they need and the reason is written in the commit, as on 6 October, never by compressing the safety or clinical rules.
- **AC-10** (one body question, no assumed effect): when a framework ends, the reply is Mani's bridge line, then the style's place question, then the buttons **Chest**, **Head**, **Stomach**, **Somewhere else**. The place questions are the ones the practice stage already asks: Direct "Where do you feel that most right now?", Supportive "Where are you feeling that most right now?", Reflective "Where do you feel that in your body?". They become `somatic_checkin`'s `ask` in `somatic.md`; the step keeps its name. Code appends the question with `repairs.with_the_check_in` (which already removes any question of the model's) and sets the four place buttons in the same block of `orchestrator.send` (today near line 757), before the block that filters hand off buttons, so they survive it. The client's check in questions ("What do you notice in your body now?" and its two siblings) and the `if_unclear` branch "What do you notice in your body?" are removed, and `somatic_checkin`'s purpose is rewritten to the bridge plus the place question. The bridge never presumes an effect ("settles", "eases", "feels lighter") unless they said so. That rule goes in `mani_base.md` under "Ending gently" and in the `[ctx]` step note for the last question step, because the model writing the bridge sees only the question steps, not `somatic.md`. When their answer on the ending turn already names a place (`named_place`, read as in AC-11), the place question is not asked: that reply is the bridge plus the place's practice, with the stored phase `somatic_practice`, replacing today's `described_early` path that asked where and handed off. Otherwise their answer naming a place gets that place's practice on the next reply, as today.
- **AC-11** (an answer that names no place): after the place question, an answer that names no place and is not a decline or "nothing" (for example "?" or "what do you mean") gets one plainer re ask: one short line of the model's, then the same place question and the same four buttons. "Nothing", "I don't feel anything", a decline, or a second answer with no place skips the practice and gets the decline line `somatic.md` already holds ("You'd rather not check in with your body right now. Would you like to keep chatting or go to the Library?") with **Chat More** and **Go to Library**; no outcome row is written, as for a decline today. The body is never asked about a third time. Rules for `_body_route_step`:
  - **First or second answer**: the first is the turn whose stored phase is `somatic_checkin`; the second is the turn whose stored phase is `somatic_practice` with the place buttons waiting (`_awaiting_place(history)`). The re ask stores `somatic_practice` and carries the place buttons.
  - **A place**: a tapped place button, or a message of six words or fewer that `named_place` matches. A longer message is read as naming no place even if it contains a place word ("I can't go back to that meeting"). A place wins over "nothing" ("nothing, just my head" is Head).
  - **"Nothing"**: a new pattern in `repairs` matched against the whole message only, short messages: "nothing", "nothing really", "not anything", "I don't feel anything", "I can't feel anything", "I feel fine", "no". "Nothing helps" is not matched.
  - **The close is set in code**, never left to the model's wording: on "nothing", a decline (`declines_or_acts`), or a second answer with no place, the text is the decline line (`reply_for` on `somatic_checkin`'s declines branch, in the style), the stored phase is `somatic_practice`, and the buttons are `_handoff()`. The framework retires on their next message, as a decline does today.
- **AC-12** (the practices are instructions, not claims): the twelve practice texts in `somatic.md` (four places, three styles) lose their opening general claim about bodies ("The chest is often where the body holds tension first", "When your head is spinning, it usually shows up as ...", "Anxiety in the stomach often ...", "When it shows up in your chest, that's often where the body reacts to perceived risk", and the like) and their filler ("Let's do something brief together", "Let's quiet that for a moment", "Let's loosen that", "Let's observe it for a moment"). The instructions and the closing "How do you feel now?" stay word for word. The pain reply and the "it comes back" waves reply are unchanged. Reseeded; `repairs.practice_in` and `practice_place` still recognise the new texts, since they read them from the stage, and a unit test asserts that within each style the twelve trimmed practices stay distinct by their first 30 characters (the key those functions match on, `repairs.py` near line 319).
- **AC-13** (it did not help, so Mani stops): on the turn answering the practice, when `felt_after` is `worse` or `unchanged` and `repairs.comes_back` does not match, the reply text is exactly "This didn't help, so I'm going to stop here." in every style, with **Chat More** and **Go to Library** and no question. The prompt says: an answer that the practice did not help, or that the whole conversation was bad or did not help ("This whole chat was horrible"), is `worse`; an answer that the practice helped but the conversation did not ("the breathing helped but this chat was bad") is `mixed`. Exceptions and order:
  - When their message asks a question of its own ("it's worse, is that normal?"), the model's reply stands instead of the fixed line: it answers their question (AC-19) and asks nothing, and code removes any question from it; the buttons are still the two.
  - It applies only when a practice was given on the last reply (`practiced_place` is set, which is the only case `felt_after` is computed) and never on a turn with a safety concern (where `felt_after` is already null).
  - In `orchestrator.send` it runs after the `comes_back` block (so the waves reply wins when the feeling came back) and before the block that adds the hand off.
  - The outcome row is written as spec 0010 says, with `body_place` the practiced place.
- **AC-14** (no exercise when nothing helped or nothing was done): `orchestrator._offer_exercise` is not called on a turn closed by AC-13, nor on the turn that retires a framework whose body route ended without a practice (the decline close of AC-11: a decline, "nothing", or no place twice), so the turn's `exercise` is null and no `exercise_select` call is logged. Better, mixed and unsure answers to a practice keep today's exercise hand off.
- **AC-15** (the records follow): Lolly's review is transcribed word for word into `backend/docs/specs/client-review-meetings-chat-2026-10-06.md` with a source banner, and is first in the source order. Spec 0010's `index.md` gets one line under its Summary saying 0011 replaces its AC-4 naming rule and parts of AC-6 and AC-7. `tests/evals/validators.says_framework` stops flagging a framework's name and keeps flagging the word "framework". `backend/PORT-STATUS.md` records the change. The journal note `lolly-meetings-chat-objections-land-on-her-own-lines-2026-10-06` is linked from the PORT-STATUS entry.
- **AC-16** (nothing else moves): safety (the screen, the crisis replies, the model flag and its pause, the grief veto), the offer refusals, RLS and the token checks behave as before, and their tests pass unchanged. The OpenAPI schema is byte identical to `main` before this change. The whole `pytest` passes with `filterwarnings = error` and the integration tests run, not skipped.
- **AC-17** (the checkpoint): after `pytest` passes and the content is reseeded locally, muhammad replays Lolly's meetings conversation once in Direct in chat-tester on the real model, typing her messages and ending with her "This whole chat was horrible". Before the offer he also types "Is this normal?" and, in a second fresh thread of three or four turns, "Are you a therapist?" and "What do you think I should do?". He reads both against AC-1 to AC-14, AC-18 and AC-19. What he finds goes into a journal note, with the turn decisions read from `admin.llm_calls.decision` and the outcome row from `public.framework_outcomes`. No other real model run is part of this spec.
- **AC-18** (talks like a good therapist, never claims to be one): `mani_base.md`'s "Who you are" says Mani talks the way a good therapist does: plain, down to earth, calm with whatever comes up, understanding before anything else. It never calls itself a therapist, counsellor or clinician, and never calls what it does therapy, counselling, a session or treatment (the existing clinical word rules stay). Asked "are you a therapist?" or "are you real?", it says plainly that it is an AI, not a therapist, there to talk things through, in one sentence, and carries on. `test_base_prompt.py` asserts both lines.
- **AC-19** (answers their open questions): when they ask Mani something directly ("What do you think I should do?", "Is this normal?", "Why do I keep doing this?", "What would you do?"), the reply answers it first, in a sentence or two, from what they have told it: a plain honest view, or the options they named with what each would mean, with the choice left theirs. It never only asks a question back. Inside the guardrails, which win over the answer: no diagnosis or label for them or their thinking, no medication or medical advice (a medical question is answered by saying plainly that a doctor is the right person for it), no general claim about people stated as a fact about them, nothing that makes abuse, threats or danger sound milder, and the safety screen, crisis replies and the model's safety flag behave exactly as today. The base prompt's "Never give advice, a solution or a tip unasked" stays; this AC covers the asked case and replaces "Asked directly, say what you can and leave the choice theirs". At most one question follows the answer. A question outside what Mani is for (code, homework, research) still gets the existing one line. Inside a running framework, a question of theirs that Mani answers holds the step without counting toward its one extra attempt, as the client's lines do (`carries_redirect`); the model reports the same step, and `[ctx]` marks the turn with `their_question: yes` (a message ending in "?" that is not the answer the step asked for). The base prompt line "They ask you to choose: it is theirs to say; you may suggest one option they named, with a reason" is rewritten to this rule.

## Decision

**Chosen option**: Option 1: fix in place, in the existing prompts, content and chat turn code, with code holding only what must be exact.

The model keeps judging the conversation (spec 0010); code guarantees the four things Lolly needs to be exact every time: the name is in the offer and in Tell me more, no Skip button, one body question with the place buttons, and the plain stop with no exercise after a negative answer.

**Implementation skills**: none of the installed community skills govern prompt and content changes in `backend/`; `supabase-postgres` is not needed because no schema changes.

## Rationale

Reasoning and options: see [rationale.md](rationale.md).

## Feature design

**Data model sketch**: no change. No migration. The content changes are stored as today: `admin.frameworks.summary` (AC-3), `admin.frameworks.stages` (AC-5, AC-7, AC-8, and the somatic stages merged in by `scripts/seed.py`, AC-10 to AC-12), `admin.prompts` for `mani_base` and `response_format` (AC-4, AC-6, AC-7, AC-9). `public.framework_outcomes` is written exactly as spec 0010 says, including on a negative close.

**State transitions** (the end of a framework, `thread_technique_state.phase`):

last question step → (ending set, or the AC-8 backstop) one of:
- their answer already named a place → `somatic_practice`: bridge + that place's practice (AC-10), then as "names a place" below
- otherwise → `somatic_checkin`: bridge + place question + four place buttons → their answer:
- names a place → `somatic_practice`: that place's practice, "How do you feel now?" → their answer, the retire turn:
  - `felt_after` worse or unchanged, no `comes_back` → "This didn't help, so I'm going to stop here." + Chat More / Go to Library, no exercise (AC-13, AC-14)
  - `comes_back` → the waves reply, as today
  - otherwise → today's reply (name what shifted, in their words) + Chat More / Go to Library + the exercise hand off
- no place, not a decline or "nothing", first time → `somatic_practice` with the place buttons: one plainer re ask (AC-11)
- "nothing", a decline, or no place a second time → set in code: the decline line + Chat More / Go to Library, `somatic_practice`, no practice (AC-11) → retired on their next message with no outcome row and no exercise (AC-14)

**API surface**: no new endpoint and no schema change. Inside `POST /v1/threads/{thread_id}/messages` (`send`):

| What | Change |
|---|---|
| `prompts` in the turn response | no **Skip this one**; the place buttons come with the first body question; Chat More / Go to Library on the negative close |
| `exercise` in the turn response | null on a negative close and after a body route with no practice (the field is already nullable) |
| Reply text | the offer and Tell me more carry the framework name; the negative close is the fixed line |

**Value sourcing**:

| Action | Value | Source |
|---|---|---|
| Offer, Tell me more | the framework name | `Framework.name` from the registry, for the offer button's `technique` id (offer) or the waiting offer's framework (Tell me more) |
| Offer, Tell me more | what it looks at | `Framework.summary`, rewritten by AC-3, sent as `offer_looks_at` |
| Offer, Tell me more | the inserted sentence when the name is missing | constant in `repairs`: `It's called {name}.` |
| Offer | permission question and buttons | unchanged: `repairs.PERMISSION_QUESTIONS`, `repairs.offer_buttons` |
| Offer turn, router off (hosted) | the name and what it looks at | the Framework Index, built by `composer.framework_index` from the registry: `name` and the new "What you look at together" column from `summary` |
| Offer turn, router on | `offer_name`, `offer_looks_at` in `[ctx]` | the decided framework of `offer.decide` |
| Tell me more | which framework | `pending_offer(history)`'s `technique`, as `orchestrator.send` computes `explaining` today |
| Tell me more, typed | `their_question` | `deferred` and "?" in their message and not a tap, as today's typed explain trigger |
| Name check | the match | the full `Framework.name` as a whole word, case ignored, space and hyphen equal, on the model's part after the permission question is stripped |
| First step met | whether their earlier words meet it | the model, from the rewritten `ready_when` (AC-5) |
| Last step | state or ask | the model, from the stage purpose and the base prompt's synthesis test (AC-8) |
| Skip | whether they are passing the question | `repairs.skips_the_step(content)` alone, tapped or typed |
| Their question mid framework | `their_question`, an uncounted hold | their message ends in "?", it is not the answer the step asked for; held like `carries_redirect` |
| Last step backstop | resolved without an ending | `repairs._stage_after_a_reply`: stored phase is the last question step, reply has no "?" and no `ending` |
| Body question | the place question per style | `somatic_checkin.ask[style]` in `somatic.md`, rewritten by AC-10 |
| Body question | the four buttons | `repairs.PLACE_LABELS` |
| Body route | first or second answer | first: stored phase `somatic_checkin`; second: stored phase `somatic_practice` and `_awaiting_place(history)` |
| Body route | a place | a tapped place button, or a message of six words or fewer matched by `repairs.named_place`; a place beats "nothing" |
| Body route | "nothing" | a new pattern in `repairs`, whole message only: "nothing", "nothing really", "not anything", "I don't feel anything", "I can't feel anything", "I feel fine", "no" |
| Ending turn | a place already named | their message on the ending turn, read by the same place rule |
| Decline close | the text, phase and buttons | set in code: `reply_for` on `somatic_checkin`'s declines branch in the style, `somatic_practice`, `_handoff()` |
| Negative close | `felt_after` | `repairs.known_value(reply.felt_after, FELT_AFTER)` on the retire turn, as spec 0010 computes it |
| Negative close | the closing line | constant in `repairs`: `NOT_HELPED_LINE = "This didn't help, so I'm going to stop here."` |
| Negative close | whether the waves reply wins | `repairs.comes_back(content)`, checked first |
| Negative close | whether their own question keeps the model's reply | "?" in their message on the retire turn |
| Exercise | whether to pick one | skipped on a turn closed by AC-13, and on the retire turn after a decline close (no practice was given: `practiced_place` is null on that turn) |

**Key invariants**:
- An offer and a Tell me more reply always carry the framework's name; no reply carries the word "framework" or a framework id.
- No reply carries **Skip this one**.
- After a framework ends, the body is asked about at most twice (the place question and one re ask), never "what do you notice" and "where" both, and never when they already named a place.
- Every body route reply that ends it without a practice carries the two buttons, set by code.
- A Tell me more reply carries no question and always the two buttons.
- A practice text never opens with a general claim about bodies.
- A `worse` or `unchanged` answer to the practice gets the fixed line with no question, the two buttons, and no exercise, unless the feeling came back.
- Still one `chat` call per turn.
- Mani never calls itself a therapist, counsellor or clinician, and says it is an AI when asked.
- A question the person asks is answered before any question back, and the answer never diagnoses, labels, gives medical or medication advice, or softens danger.

**Security model**: unchanged. `framework_outcomes` stays health data under spec 0010's RLS and grants. Nothing new reaches `admin.llm_calls` but ids and codes.

**Configuration required**: none. The content changes need `python scripts/seed.py` locally and against hosted after deploy; `scripts/embed_frameworks.py` does not need re running, since no `exemplars` or `to_find_out` change.

**Critical test scenarios**:
- Happy path, Direct Thought Reframe (integration, scripted model): the offer sentence comes back without the name and the reply carries `It's called Thought Reframe.` before "Would you like to try it with me?"; Tell me more's `[ctx]` has `offer_name` and `offer_looks_at`; the accept reply has no consent line; no reply has a Skip button; the ending reply ends with "Where do you feel that most right now?" and the four place buttons; "chest" gets the Direct chest practice with no "The chest is often"; "this whole chat was horrible" with `felt_after: worse` gets exactly the closing line, Chat More and Go to Library, no exercise call, and one outcome row with `worse`. Verifies **AC-1**, **AC-2**, **AC-4**, **AC-6**, **AC-10**, **AC-12**, **AC-13**, **AC-14**.
- No place: "?" gets one re ask with the four buttons; a second "?" gets the decline line and the two buttons with no outcome row; "nothing" on the first answer goes straight to the decline line. Verifies **AC-11**.
- Positive and returning answers: `felt_after: mixed` keeps the model's reply and the exercise hand off; "it came back" with `felt_after: worse` gets the waves reply, not the closing line. Verifies **AC-13**, **AC-14**.
- Skip without the button: "skip" typed on a running step advances it with no button on any reply; a tap on a **Skip this one** button stored on the last message also advances it. Verifies **AC-6**.
- Name check: "structured problem-solving" in the offer counts for Structured Problem Solving; "ACT" alone does not count for ACT Choice Point and gets the inserted sentence; an empty model part gets the sentence alone. Verifies **AC-1**.
- Tell me more: a reply with a question loses the question and keeps both buttons; a typed "Is this normal?" under an offer carries `their_question: yes` in `[ctx]`. Verifies **AC-2**, **AC-19**.
- Last step backstop: a statement with no question and no ending at `reframe` is recorded as resolved and gets the place question. Verifies **AC-8**, **AC-10**.
- Place named early: "it's in my chest" on the ending turn gets the bridge and the chest practice, no place question. Verifies **AC-10**.
- No place, edges: "I can't go back to that meeting" is no place (re ask); "nothing, just my head" is Head; "nothing helps" is not "nothing"; a decline close carries the two buttons even when the scripted model wrote something else, and the next message retires it with no exercise call. Verifies **AC-11**, **AC-14**.
- Practice keys: within each style the twelve trimmed practices are distinct by their first 30 characters. Verifies **AC-12**.
- Worse and mixed: "the breathing helped but this chat was bad" scripted as `mixed` keeps the model's reply; "it's worse, is that normal?" with `worse` keeps the model's answer with no question and the two buttons. Verifies **AC-13**.
- A question mid framework: "Is this normal?" at `facts_for` holds the step and leaves `holds` at 0. Verifies **AC-19**.
- Content: every framework's first step `ready_when` mentions what they said before the offer; no `ask` contains "Putting those together"; no practice text contains the removed claims; every summary is one sentence with no feeling word. Verifies **AC-3**, **AC-5**, **AC-7**, **AC-8**, **AC-12**.
- Prompt: `test_base_prompt.py` asserts the naming rule, the say back rule, the stop rule, the Direct pace line, the identity and AI lines, the answer first rule with its guardrails, and the line cap. Verifies **AC-1**, **AC-9**, **AC-18**, **AC-19**.
- Safety and contract: the crisis, concern and refusal tests pass unchanged; the OpenAPI schema is unchanged. Verifies **AC-16**.

## Build plan

Tracer Bullet: each slice changes one stretch of the conversation end to end (prompt, content, code, tests) and leaves `pytest` green, so a partial build is still a coherent Mani.

**Slice 1: the offer and the way in**
1. [x] Rewrite the six `summary` lines; reseed, satisfies **AC-3**
2. [x] The Framework Index column from `summary`; `[ctx]` `offer_name` and `offer_looks_at` on router offer and Tell me more turns; delete `greeting.EXPLANATIONS` and the `explain_offer` line; the name check and `It's called {name}.` in `repairs`; questions removed from an explaining reply with both buttons kept; `their_question` on a typed explain turn; the base prompt naming rule; `says_framework` keeps only the word, satisfies **AC-1**, **AC-2**, **AC-15**
3. [x] Remove the consent lines from the prompts and `_START_NOTE`; rewrite the six first steps' `ready_when` and the prompt line on the step an offer was built on; reseed, satisfies **AC-4**, **AC-5**
4. [x] Remove `SKIP_LABEL` and the button; `skipped` from `skips_the_step(content)` alone; the prompt line, satisfies **AC-6**

**Slice 2: inside the framework**
5. [x] The say back, stronger than they said, spoken words and Direct pace rules in `mani_base.md`; the concrete question rule; `test_base_prompt.py`, satisfies **AC-7**, **AC-9**
6. [x] Thought Reframe's three asks; the `reframe` and ABCDE `balanced` purposes and fallback asks for the stated conclusion; the last step backstop in `_stage_after_a_reply`; reseed, satisfies **AC-7**, **AC-8**
7. [x] "Who you are" as a good therapist who never claims to be one, the AI line, and the answer first rule for their questions with its guardrails; the "They ask you to choose" line rewritten; `their_question` as an uncounted hold mid framework; `test_base_prompt.py`, satisfies **AC-18**, **AC-19**

**Slice 3: the body and the close**
8. [x] `somatic_checkin` asks the place question, the place buttons set before the hand off filter; remove the check in lines and the "what do you notice" branch; the bridge rule in "Ending gently" and the last step's note; a place named on the ending turn goes straight to its practice, replacing `described_early`; reseed, satisfies **AC-10**
9. [x] In `_body_route_step`: first and second answer by stored phase, the six word place rule, the anchored "nothing" pattern, and the decline close set in code, satisfies **AC-11**
10. [x] Trim the twelve practice texts and add the first 30 characters test; reseed, satisfies **AC-12**
11. [x] `NOT_HELPED_LINE` on a worse or unchanged retire turn after the `comes_back` block, their own question keeping the model's reply, the `felt_after` prompt lines for worse and mixed; no `_offer_exercise` on that turn or after a decline close, satisfies **AC-13**, **AC-14**

**Slice 4: records and checks**
12. [x] Rewrite or delete the tests the slices change (the Skip tests, the check in then where test, the offer composition tests, the exercise hand off test); full `pytest` with integration running; OpenAPI diff against `main`, satisfies **AC-16**
13. [x] Transcribe Lolly's review; the line in spec 0010; PORT-STATUS, satisfies **AC-15**
14. [ ] muhammad's Direct replay in chat-tester, read against AC-1 to AC-14, journal note, satisfies **AC-17**

## Consequences

**Positive**:
- The conversation Lolly hated loses every line she pointed at, including the ones from her own documents, so her next test starts from her current view.
- A person who says it did not help is no longer handed a question and a second exercise.
- The framework becomes something the person can name and decide about.
- One fewer model call (the exercise pick) on every negative close and every body route that ended without a practice.

**Negative / tradeoffs**:
- Much of what she rejected was her approved wording. Her earlier documents (the style document's consent lines, Tell me more texts and check in lines, the practice texts) now disagree with the product, and she has to be told so, or a later reviewer will "restore" them.
- The negative close depends on the model reporting `felt_after` correctly. "This whole chat was horrible" read as `unsure` or nothing still gets today's path.
- Stating the conclusion at the last step leans further on the model's judgment of what they established; a conclusion that goes past their words is the risk spec 0010 already accepted, now on a step that used to ask.
- Dropping the generic check in removes the "compared with when we started" signal; the only effectiveness signal left is the answer after the practice.
- A person who feels nothing gets no practice, so the somatic step is skipped more often than "mandatory" suggests.
- Answering their questions gives the model more room to say something wrong than deflecting did; the guardrails in AC-19 are prompt rules, and only the safety screen and the crisis replies are enforced in code.
- The web and mobile apps, when they connect, must not render a Skip button and must render place buttons on the ending reply.

**Neutral**:
- `somatic_checkin` keeps its name though it now asks where; renaming it would touch the phases in every framework, the stored rows and the outcome logic for no gain.
- `skips_the_step` stays reachable only by typed words.
- Row 6 of the scope is covered by this spec.

## Follow-up

- [ ] Tell Lolly which of the lines she rejected came from her own documents (the journal note lists them), and ask whether her style document and the framework documents should be updated to match.
- [ ] The other five frameworks' asks were not rewritten one by one (AC-7 covers them by the prompt rule); scope row 39 still owns a content pass.
- [ ] Supportive and Reflective get their real model check at Lolly's next checkpoint, not in this spec.
- [ ] If the negative close misses because `felt_after` came back `unsure`, measure how often from `framework_outcomes` before adding any word matching.
