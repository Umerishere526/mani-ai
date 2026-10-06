# Scope epic: Conversation

How Mani talks: how natural its replies sound, the body check at the end of a framework, which framework is offered, and how each framework's questions follow the client's document for the Direct, Supportive and Reflective styles. Back to [the index](index.md).

## Slice 1: The flow works

### 1. Somatic check asked once, then moves on · needs a decision

The body question is asked one time. When the person says yes or describes their body, Mani acknowledges it and moves to asking where. Today the fixed question is added to every reply while the stage is still the check in, so "yes" gets the same question again.
**Done when:** in a replay of the panic chat, "yes" is followed by "where", never by the body question a second time, and a person who already named a place skips the "where" question.

- [ ] Design it (spec): `/architect somatic check asked once`

### 2. Where in the body, with buttons, then the exercise · needs a decision

After the check in, Mani asks where, with the four buttons (Chest, Head, Stomach, Somewhere else). "idk" or an unclear answer gets the buttons again, not a plain text guess. The matching exercise is always given before any Chat More or Go to Library choice appears.
**Done when:** the chat can never reach Chat More or Go to Library from the somatic stages without an exercise having been given, unless the person declines, skips for action, or mentions pain, trouble breathing or feeling faint.

- [ ] Design it (spec): `/architect somatic location and exercise`

## Slice 2: Client wording

### 3. Per style wording from the client · needs a decision

Chest, head, stomach and somewhere else exercises in the client's exact words for each style. Direct and Supportive add a line after the exercise (for example "Just notice"), and Reflective sets the steps one per line. Each ends with "How do you feel now?". Today there is one shared text for all three styles.
**Done when:** every style and place pairing matches the client's document word for word, and the evals check it.

- [ ] Design it (spec): `/architect somatic per style wording`

### 4. Returns in waves, then the library offer

After "calmer, then it comes back", Mani says it is common and comes in waves, that the same exercise helps, and offers the library. Buttons are "take me to the library" and "want to keep chatting" (shorter label "Library Tools" if too long). Choosing the library gets the client's handoff line.
**Done when:** that exact path works in all three styles, and the buttons appear only here and after the exercise, never earlier.

- [ ] Build it: `/develop somatic waves and library offer`

## Slice 3: Right framework offered

### 5. ABCDE is offered when an event and a belief about it are named · done

In a replay of the manager chat (Supportive style: "my manager embarrassed me today because he wants me to fail", "EVERYTHING WENT WRONG", "I felt really embarrassed"), Mani offered structured problem solving. The client's document says this fits ABCDE: a specific event, a belief about it (his motive), and an emotional effect, with the person wanting to understand it rather than make a plan. This feature covers when each of ABCDE, Thought Reframe, Structured Problem Solving and ACT Choice Point gets offered, and how the offer reads in each style. It also covers the client's rule that an assumed motive and a broad "everything went wrong" are handled inside ABCDE, not used to pick a different framework.
**Done when:** the manager chat above ends with the ABCDE offer, and the client's example lines for the other three frameworks still pick theirs, each covered by a test. The wording of the offer itself is row 6.
Spec: [0001](../specs/0001-abcde-framework-offer.md) · code in backend/mani/chat/, backend/content/frameworks/abcde.md

- [x] Design it (spec): `/architect abcde framework offer`
- [x] Build it: `/develop abcde framework offer`
  - [x] ABCDE motive signals in abcde.md and the four message router window (AC-1, AC-2, AC-6, AC-7)
  - [x] Closest fit carries the top framework's offer wording (AC-3)
  - [x] Tests, full pytest, PORT-STATUS.md update (AC-4, AC-5)
- [x] Verify it: `/check verify abcde framework offer`
- [x] Test it: `/test abcde framework offer`

## Natural Mani: current focus

From the client meeting in October 2026 and the client's style document ("directive, reflective, supportive"). The client finds Mani robotic, too complicated, too full of questions, and repeating "I hear you"; people do not feel heard. This phase is built first, ahead of the slices below: measure (row 32), then rewrite (rows 42, 44, 33, 34, 18, 40, 41, 6), then choose the model (row 35) on the same check.

### 42. Mani follows the client's documents, and our conversation rules that disagree are removed · in-progress

The client says Mani is moving in a direction they do not want. Their documents are the target: "Good, Acceptable, Bad Conversations" (each "Mani Standard" reply is one short line that adds meaning in fresh words, then one clear question, often a "most" question such as "What worries you most about that?"), the style document, and the framework document. Over time we added word bans, question rules, redrafts and offer gates, many recorded in ADRs that now block this. Every conversation rule the documents do not ask for, or that they contradict, goes, and so does the ADR behind it (muhammad, 2026-10-06: the client's documents win, and stale ADRs may be deleted). Safety, privacy and permissions stay out of reach: the crisis screen, crisis replies, the grief veto, row level security and token checks change only through their own rows. Overrides row 40's ranking ban (spec 0008).
**Done when:** every rule in the base prompt, the answer format, the `[ctx]` notes, the redrafts and the repairs is either traced to a line in the client's documents or removed; every ADR whose rule was removed is deleted with its index line; nothing in the prompt forbids a "Mani Standard" reply; replays of muhammad's 6 October chat and three of the document's bad transcripts, run after muhammad says yes, read like the corrected responses; and the safety, privacy and permission tests still pass unchanged.

Spec: [0010](../specs/0010-mani-follows-client-documents/index.md) (the client's documents in source order, newest first, with Lolly's email of 6 October on top; the model judges the offer, the steps and the synthesis; six offer refusals and one extra attempt per step stay in code; every framework ends in the somatic check, whose answer is stored in `framework_outcomes`; the Done when's paid replays are replaced by muhammad's three live conversations in chat-tester; covers row 6's three button offer) · code in backend/mani/chat/, backend/mani/db/outcomes.py, backend/mani/llm/schema.py, backend/content/, backend/supabase/migrations/013_llm_call_decision.sql to 015_framework_outcomes.sql, backend/scripts/wording.py

- [x] Design it (spec): `/architect Mani follows the client's documents`
- [ ] Build it: `/develop Mani follows the client's documents`
  - [x] The prompts on the client's rules, the model chooses the offer, no redrafts, the three button offer, the call log decision (AC-1 to AC-4, AC-9, AC-10)
  - [x] Steps judged by the model and every ending into the somatic check (AC-5, AC-6)
  - [x] Mani answers what they report, and the outcome table (AC-7, AC-8)
  - [x] Evals and tests on the client's rules, the ADRs and specs deleted, ADR-019 and the records (AC-9, AC-11 to AC-13)
  - [ ] muhammad's three live conversations, read against Lolly's nine points (AC-14)
- [ ] Verify it: `/check verify Mani follows the client's documents`
- [ ] Test it: `/test Mani follows the client's documents`

### 44. Mani follows Lolly's review of the meetings chat · in-progress

Lolly reviewed a Direct Thought Reframe chat on hosted (left out of meetings, "I don't know if I'm making too much of it") line by line on 6 October 2026, and said she hates talking to Mani. Her review is now the newest client document, and muhammad said to make Mani as she says (2026-10-06). Many of the lines she rejects are her own earlier wording (the "one step at a time" consent lines, the Direct "Tell me more" text, "I have a structured approach", the body check in and the chest practice), so this rewrites her documents as well as ours. What she asks for:
- **Plain spoken words.** Replies sound said, not written. Use the person's own words ("my responsibilities haven't changed") instead of a stiff paraphrase, and skip the say back when it only restates them. Never make what they said stronger than it was: "left out of meetings" is not "dropped", "I'm worried it could mean" is not "it points to", "my responsibilities haven't changed" is not "your role stayed the same". No filler ("leaves things up in the air", "decide on your next move") and no mirroring their words back.
- **Understand before acting.** Direct does not jump to who to ask or what to do while the situation is still unclear.
- **Name the framework.** The offer says "Thought Reframe" and what it looks at, then asks. **Tell me more** names it and explains what you will look at, with no "focused questions", "without rushing you" or "you stay in control".
- **No filler on a yes.** The consent line ("one step at a time") goes. Mani goes straight to the first step their words have not already met, and never asks them to confirm a thought the offer was built on.
- **Questions anyone can answer at once.** Concrete and specific ("What's one other reason you might not be included in those meetings?"), not abstract ("What makes that thought matter so much?", "What else could be going on?").
- **Synthesis instead of the worksheet ask.** Where Mani has what it needs, it states what they established, in their words and no further, instead of "Putting those together, what would you say is true about this?" (Thought Reframe and ABCDE). It never sounds like correcting faulty thinking ("what you were filling in").
- **No "Skip this one".** The button goes from every question. It made the framework a form.
- **One body question, no assumed effect.** The bridge into the somatic practice never presumes something settled or helped, and the generic body check in before "Where do you feel that most right now?" goes, so the body is asked about once. The practice drops the general claims about bodies ("The chest is often where the body holds tension first") and the filler ("Let's do something brief together").
- **A negative answer closes.** After the practice, when they say it did not help or the whole experience was bad, Mani says so in one plain line ("I hear you. This didn't help, so I'm going to stop here.") and stops: no question, no further practice, and no exercise offered. Today `orchestrator._offer_exercise` runs on every ending whatever they report.

The decisions it owed (buttons on a negative close, unchanged closing like worse, typed skip, the new wording, transcribing her review) are settled in spec 0011. Covers row 6 (Lolly confirmed the naming here). Reverses spec 0010's "no framework name reaches the person" (AC-4) and the eval check that flags the name. Source tracing in the journal note `lolly-meetings-chat-objections-land-on-her-own-lines-2026-10-06`.
**Done when:** a replay of the meetings chat in each style, run after muhammad says yes, shows no stronger restatement of their facts, names the framework in the offer and in Tell me more, has no consent filler, no thought asked a second time, no "Skip this one", a stated synthesis instead of the "Putting those together" ask, one body question before the practice, a practice with no general claim about bodies, and a negative answer after the practice that gets one closing line with no question and no exercise; the whole `pytest` passes.

Spec: [0011](../specs/0011-lolly-review-meetings-chat/index.md) (the framework named in the offer and Tell me more, no consent line or Skip button, a stated conclusion at the last step, one body question with place buttons, trimmed practices, "This didn't help, so I'm going to stop here." with Chat More and Go to Library and no exercise after a worse or unchanged answer, and Mani talking like a good therapist that says it is an AI and answers their questions inside the guardrails; no schema change; muhammad's Direct replay in chat-tester is the real model check) · code in backend/mani/chat/ (repairs.py, orchestrator.py, context.py), backend/mani/prompts/composer.py, backend/content/ (prompts and the six framework files)

- [x] Design it (spec): `/architect Mani follows Lolly's review of the meetings chat`
- [ ] Build it: `/develop Mani follows Lolly's review of the meetings chat`
  - [x] The offer names the framework, Tell me more explains it, no consent line, the first step already met, no Skip button (AC-1 to AC-6, AC-15)
  - [x] Spoken words never stronger than they said, concrete questions, the stated conclusion, the therapist voice and answers to their questions (AC-7 to AC-9, AC-18, AC-19)
  - [x] One body question with place buttons, the re ask and decline close, trimmed practices, the stop line and no exercise (AC-10 to AC-14)
  - [ ] Tests, records, and muhammad's Direct replay in chat-tester (AC-15 to AC-17)
- [ ] Verify it: `/check verify Mani follows Lolly's review of the meetings chat`
- [ ] Test it: `/test Mani follows Lolly's review of the meetings chat`

### 32. The client's style conversations are a standing check

The client's style document has four conversations (panic, overthinking a friend's text, compulsive scrolling, stress before a deadline), each written for all three styles. They become real model scenarios that save every transcript for a person to read side by side, and count per reply and per conversation: questions asked, phrases repeated across replies ("I hear you", the same opener), dashes, and the exchange at which the offer comes. Every later row in this phase is judged on this check, run three times before and after a change, never once.
**Done when:** the four conversations run in all three styles against the real model, the counts print per run, and a baseline from today's instructions and model is saved to compare against.

- [x] Build it: `/develop client style conversations as a standing check`

### 33. Mani speaks naturally: short, neutral, humble instructions

The base instructions are about 500 lines of rules, and code redrafts any reply that skips a question (ADR 008), uses a feeling word the person did not say (ADR 006) or repeats a question (ADR 011), which pushes every reply into the same shape. The client's own examples break several of these rules ("It sounds like a lot is happening at once"). The styles overshoot: Direct reads robotic, Supportive overly emotional, Reflective over interprets. This rewrites the base instructions short and open, so Mani reads what is actually happening and answers like a down to earth person ("I'm in pain" gets "Can you tell me more about it?"), checks its understanding as a question instead of stating it, and keeps one neutral voice in all three styles, with the style showing in what Mani does (Direct leads, Supportive accompanies, Reflective explores) and not in how emotional it sounds. The redrafts that enforce tone are retired; safety checks, offer vetoes and stage tracking stay. The ADRs it overrides are superseded by a new one, not edited.
**Done when:** on row 32's check, against the saved baseline, replies carry fewer questions, no stock phrase repeats within a conversation, no reply states a feeling or meaning the person did not give without checking it, the styles differ in what Mani does but not in emotional intensity, and the team reads the transcripts and agrees they sound like a person.
Spec: [0002](../specs/0002-mani-speaks-naturally/index.md) · code in backend/mani/chat/, backend/content/prompts/, backend/scripts/eval_client_style.py

- [x] Design it (spec): `/architect Mani speaks naturally`
- [x] Build it: `/develop Mani speaks naturally`
  - [x] Extend the check and record the baseline numbers (AC-1, AC-5, AC-6, AC-7, AC-8, AC-12)
  - [x] Read short replies against Mani's last question (AC-4)
  - [x] Retire the tone redrafts and the sentence drop, measure the code change alone (AC-2, AC-3)
  - [x] Rewrite the prompts and tune on the check, three runs each time (AC-1, AC-6 to AC-12): written and measured; with the feeling and size redraft restored, 0 of 36 feelings never used
  - [x] Extend the check once more: size phrases never used, `style_read.md`, the blind meaning read (AC-8, AC-9)
  - [x] Ban "It sounds like" in the instructions and the check, measured alone (AC-7, task 4c): two rounds, "sounds like" or "seems like" 49 at baseline, 26 before, 3 after round 2 and 9 to 15 on the later prompts; muhammad accepted the rate, no redraft (AC-7 is met only in part, `/architect` to amend its bar)
  - [x] Ban restating the person's words in understanding replies, measured by the read (AC-14, task 4d): restating 88% before, 42% after; the style lines (task 4b) got AC-9 to 10 of 18 in two rounds, not 15
  - [x] Read the transcripts (blind model reader, muhammad checks the flagged cases): AC-8 and AC-14 met, AC-9 not met (task 4b spent)
  - [x] Accept ADR-012 and close the figures (AC-13): accepted by muhammad 2026-10-04, PORT-STATUS, index and journal updated
- [x] Verify it: `/check verify Mani speaks naturally`
- [x] Test it: `/test Mani speaks naturally`

### 34. No dashes in any reply

Mani's replies never use a dash as punctuation. The base instructions use dashes themselves, and the model copies them. The instructions lose them, and a plain code step swaps any dash that still appears for a comma or a full stop before the reply is saved.
**Done when:** no reply in row 32's check contains an em dash, an en dash or a spaced hyphen, hyphenated words such as "check-in" are left alone, and a unit test covers the swap.

- [ ] Build it: `/develop no dashes in replies`

### 18. A framework stage moves on after one answer · in-progress

Inside a framework, whatever the person replies to a stage's question (a real answer, "I don't know", "sure", "yeah", "yes", or a question of their own), Mani moves to the next stage instead of asking again in other words. A question they ask is answered first, then Mani goes on. Today a stage holds until its `ready_when` is met (ADR 011), and "I don't know" gets up to three options, a draft, or the same question reworded (ADR 010). The cost to design around: the next stage must work with what it has, so a skipped answer never leaves a later stage with nothing to ask about (for example ABCDE's dispute step after "I don't know" at the belief step). This also settles the open client question about suggesting options when someone is stuck.
**Done when:** in every framework, a real answer, "I don't know", "yes", "sure" and a question of their own each move to the next stage within one reply, no stage question is asked twice, the framework still reaches the body check in, and a test covers each framework.

Spec: [0003](../specs/0003-stage-moves-on-one-answer/index.md) · code in backend/mani/chat/, backend/content/frameworks/, backend/content/prompts/, backend/scripts/eval_replies.py

- [x] Design it (spec): `/architect a framework stage moves on after one answer`
- [x] Build it: `/develop a framework stage moves on after one answer`
  - [x] Code moves the stage on and limits what a reply records (AC-1, AC-2, AC-3, AC-10)
  - [x] Prompt rules for moving on, the holds and pick for me (AC-4, AC-5, AC-11)
  - [x] ABCDE end to end: split stage, content, walk test, eval run and read (AC-6 to AC-9)
  - [x] The other five frameworks, one at a time, with muhammad's if_earlier_missing questions (AC-6 to AC-9)
  - [x] The hold count: migration, stored count, redirect mark, the recorded stage rule (AC-2, AC-8, AC-12)
  - [x] Prompt and content for the two holds, DBT counted branches, first_action's question (AC-4, AC-5, AC-6, AC-11, AC-13, AC-14)
  - [x] Measure the holds again and read every held turn with muhammad (AC-9)
  - [x] The redirect is decided in code from the reply, and the mark is removed (AC-4, AC-12, AC-15)
  - [x] The notes: reworded, and a note of its own on a stage that picks from options (AC-13, AC-16)
  - [x] Measure again against the bar and read one transcript per framework (AC-9a)
  - [x] ADR-013, PORT-STATUS and the journal entry (AC-9)
  - [x] A request to hear the question again is recognised in code and held (AC-14, AC-16, AC-17)
  - [x] Measure again against the bar and verify again (AC-9b)
- [ ] Verify it: `/check verify a framework stage moves on after one answer`
- [ ] Test it: `/test a framework stage moves on after one answer`

### 38. A request to hear a question again also reads "whats that mean" · in-progress

Spec 0003 recognises a request to hear a question again from a short list of phrases. A check of 40 typings found the gaps: "whats that mean" (the shared word cleanup turns "what's" into "what s" and has no entry for "whats"), the past tense ("I didn't understand"), "say that again", "repeat that" and the texting forms "what do u mean" and "wdym". The past tense and the repeat forms read as a story or an objection inside a longer sentence, so they count only on their own.
**Done when:** the phrases people actually type for "I did not understand", with and without apostrophes, are recognised, a longer statement about their situation is not, each is covered by a test, and spec 0003's list says so.

Spec: [0003](../specs/0003-stage-moves-on-one-answer/index.md) · code in backend/mani/chat/context.py

- [x] Design it (spec): `/architect the request to hear a question again also reads whats that mean`
- [x] Build it: `/develop the request to hear a question again also reads whats that mean`
  - [x] Free phrases and the anchored set, with the filler and blocked words (AC-17)
  - [x] Typed positives and negatives as tests (AC-17)
- [ ] Verify it: `/check verify the request to hear a question again also reads whats that mean`
- [ ] Test it: `/test the request to hear a question again also reads whats that mean`

### 40. Mani's questions can be answered without stopping to think · in-progress

The team lead points to questions from the earlier Mani ("What does being alone feel like for you today?", "What would you like to explore first?") as plain, neutral and down to earth. Many questions today are not: framework steps send the client's worksheet sentences as written ("What did that come to mean for you?", "What is a more balanced way to describe this?"), and people answer "what?" (journal `idiot-concert-chat-why-mani-reads-as-a-worksheet-2026-10-05`). Every question, before the offer and at every framework step, uses everyday words and asks about one concrete thing the person already said. At most one short line comes before it, and that line adds meaning instead of restating, as in the "Mani Standard" rewrites in the client's "Good, Acceptable, Bad Conversations" document ("What time are you aiming for right now?"). The old chat also shows the limit: its open "what would feel most supportive" question and its either/or questions got "i dont know" and "i cant decide", so a person who is stuck gets one simple concrete question, not a choice. Where a client question cannot be followed, this overrides row 17's "the client's own question" (muhammad allowed rewriting client wording on 2026-10-05). Where this row's rules disagree with the client's documents (its ban on "most" questions among them), row 42 removes them (muhammad, 2026-10-06). Notes: journal `questions-easy-to-answer-old-mani-chat-2026-10-05`.
**Done when:** replays of the concert chat, the "i am depressed" chat and three of the document's bad transcripts reach the offer and the body check with no question a reader marks as hard to follow; no framework step question uses worksheet words ("belief", "balanced", "perspective", "come to mean"), and the evals check it; a person who says they are stuck or cannot decide is never given an either/or choice; and the team lead reads the transcripts and agrees they read like the old examples.

Spec: [0008](../specs/0008-questions-answerable-without-thinking/index.md) (the step questions themselves were already rewritten plainly on 2026-10-05; the spec targets the clause the model puts in front of them, its own abstract and ranking questions, the stuck check "Are you feeling stuck?", and two body check lines; the Done when's replays are narrowed to the concert and "i am depressed" chats, one paid run after muhammad says yes) · code in backend/mani/chat/context.py, backend/content/prompts/, backend/content/frameworks/, backend/tests/evals/validators.py, backend/scripts/client_style_counts.py

- [x] Design it (spec): `/architect Mani's questions can be answered without stopping to think`
- [ ] Build it: `/develop Mani's questions can be answered without stopping to think`
  - [x] Free question counts in the evals, with the exemptions (AC-7)
  - [x] Content: the DBT STOP panic line, two body check lines, the framework index wording, and a test over every authored question (AC-5, AC-6, AC-11)
  - [x] Plain step questions in every stage note and prompt line (AC-1)
  - [x] Base prompt: question rule, Supportive line, the stuck check, within 115 lines (AC-2, AC-3, AC-4) (118 lines, muhammad raised the limit on 2026-10-05)
  - [x] The depressed_alone scenario, ADR-017, PORT-STATUS and journal, then the six conversation paid run after muhammad says yes (AC-8, AC-9, AC-10)
- [x] Verify it: `/check verify Mani's questions can be answered without stopping to think`
- [x] Test it: `/test Mani's questions can be answered without stopping to think`

### 41. A person who stays stuck while Mani is understanding is offered ABCDE · in-progress

From the client meeting in October 2026. Someone comes to Mani in pain, in their body or their mind, and Mani asks questions to understand. The pain itself starts nothing. If they keep saying "I don't know" or "I can't think", or the conversation goes round in a loop, Mani offers ABCDE, because its questions walk them step by step through what is going on. If a thought is what hurts, Thought Reframe is offered, as today. This changes settled rules, so `/architect` decides it first: ABCDE today needs an event and what they made of it (spec 0005's full fit); its own "when not to use" list names an unclear issue and a person who cannot answer reflective questions; the client's overview puts "stuck" under Behavioral Activation; spec 0008 AC-4 says "Are you feeling stuck?" never leads to an offer; and Mani offers nothing to someone in physical pain. The spec settles what counts as stuck or looping and after how many turns, how this sits with "Are you feeling stuck?", and what ABCDE's first steps ask someone who has named no event. Builds on rows 8 and 40.
**Done when:** in a replay of the "i am depressed" chat (`depressed_alone`), a person who still answers "i dont know" or "cant think" after Mani's understanding questions is offered ABCDE; a person who names a thought that hurts is offered Thought Reframe; nothing is offered under `safety: concern`; and someone who named no event can answer the ABCDE steps that follow.

Spec: [0009](../specs/0009-stuck-person-offered-abcde/index.md) (a `stuck` fact kept only after "Are you feeling stuck?", fitting ABCDE below every other fit; ABCDE opens with "What goes through your mind when you feel this?"; the body pain hold lifts on this route; the paid run is shared with spec 0008's) · code in backend/mani/chat/router.py, backend/mani/chat/techniques.py, backend/mani/chat/context.py, backend/mani/chat/orchestrator.py, backend/mani/chat/redraft.py, backend/content/frameworks/abcde.md, backend/content/prompts/mani_base.md

- [x] Design it (spec): `/architect A person who stays stuck while Mani is understanding is offered ABCDE`
- [ ] Build it: `/develop A person who stays stuck while Mani is understanding is offered ABCDE`
  - [x] The `stuck` fact, the check gate, the fit below every other, and the fit text (AC-1, AC-2, AC-3)
  - [x] ABCDE's stuck branches, the offer turn, the passed over first step, and the pain hold, with the integration test (AC-4, AC-6, AC-7, AC-8)
  - [x] The base prompt's stuck check and pain lines within 118 lines (AC-5, AC-6)
  - [ ] The stuck_body_pain scenario, expect_offer, ADR-018, PORT-STATUS and journal, then the shared paid run after muhammad says yes (AC-9, AC-10, AC-11)
- [x] Verify it: `/check verify A person who stays stuck while Mani is understanding is offered ABCDE`
- [x] Test it: `/test A person who stays stuck while Mani is understanding is offered ABCDE`

### 43. The team sees whether conversations helped · needs a decision · from spec 0010

Spec 0010 stores how a person felt after the somatic practice (better, mixed, unchanged, worse, unsure) with the framework, style and how the framework ended. The team reads it with SQL for now. An admin view shows the counts by framework, style and ending, so the client can judge effectiveness and not only engagement.
**Done when:** an admin can see outcome counts by framework, style and ending over a chosen period, behind the existing admin access, with no person's words shown.

- [ ] Design it (spec): `/architect the team sees whether conversations helped`

### 6. The offer names the framework, introduces it, and gives three choices · needs a decision

When Mani offers a framework it says the framework's plain name and a short introduction to what it does, then the client's three choices: "Yes, let's try it", "Tell me more" and "I want to keep talking". "Tell me more" gets a short explanation in the style in force, then the other two choices again. Today the shared rules forbid the name and the word "framework", the offer has two buttons (Try it, Keep chatting), and the app adds a stored description and "Would you like to try it?". The client's style document says "I have a structured approach..." with no name, so the naming needs the client's confirmation in writing. Lolly confirmed it in her review of 6 October 2026, and the naming is now built as part of row 44. The October 2026 review still applies: Thought Reframe's description promises "you will be able to see the situation differently", and Structured Problem Solving's names a feeling ("overwhelming").
**Done when:** every offer in every style names the framework and introduces it in plain words, carries the three choices, "Tell me more" returns the remaining two, no introduction promises a result or names a feeling the person did not use, and row 32's check covers it.

- [ ] Design it (spec): `/architect the offer names and introduces the framework`

### 35. The model is chosen on real conversations · in-progress

Every reply today comes from the smallest, cheapest tier of a single model family. An earlier comparison only checked whether a model could carry a conversation through every stage. Candidates from the major providers and from the open model families are compared on row 32's check with the new instructions: how natural the replies read, whether it follows what the person means, whether it completes a framework through the body check in, how reliably it returns the structured reply, time per reply, and cost per conversation. Since 5 October 2026 the first test is row 8's fact checklist: the current model marks facts by topic and changes them every turn, so framework choice fails on the stress, grief and deadlines chats (journal `framework-fit-from-facts-first-runs-2026-10-05`); those five chats are the cheapest discriminating check. The choice covers two roles: the main model (every reply) and the secondary model (summaries, memory folding, titles). Conversation content is health data, so a candidate needs a zero data retention route and must not have mental health messages blocked by provider moderation. The test budget is small (about 3.7 dollars of credit on 5 October), so candidates are run cheapest first.
**Done when:** at least four candidates, two of them open models, run on row 8's five chats and three times each on row 32's check, the numbers and one transcript per candidate are recorded in the decision, and the chosen main and secondary models are in the seeded prompts.

Spec: [0006](../specs/0006-main-model-chosen-on-conversations/index.md) (step one: Gemini 3.8 Flash only; the wider comparison in Done when stays open) · code in backend/mani/llm/, backend/mani/chat/orchestrator.py, backend/scripts/, backend/content/prompts/mani_base.md

- [x] Design it (spec): `/architect the model is chosen on real conversations`
- [ ] Build it: `/develop the model is chosen on real conversations`
  - [x] Reasoning effort, max tokens and routing reach the call from the prompt file (AC-1, AC-2)
  - [x] The runner tries a model in its own process, zero retention by default, figures kept before cleanup (AC-3, AC-4)
  - [ ] The paid run after muhammad says yes, then switch or record (AC-5, AC-6, AC-7)
- [ ] Verify it: `/check verify the model is chosen on real conversations`
- [ ] Test it: `/test the model is chosen on real conversations`

## Slice 4: Offers and checks

### 7. The manager chat is a standing real conversation check

The reported manager chat becomes a scenario in the real model evals, so a later change that moves the offer back to structured problem solving is caught. From spec 0001.
**Done when:** the scenario runs in all three styles and fails if ABCDE is not the framework offered.

- [ ] Build it: `/develop manager chat eval scenario`

## Slice 5: Judgment, not phrase lists

### 8. Mani picks the best framework from the person's situation and steers toward it · in-progress

Framework choice today rests on phrase lists in the router, and every missed case means another phrase or rule (row 5 was one). Instead, Mani should judge which framework fits from the whole conversation and the client's distinction rules, and use its questions to find out what is missing for that framework (event, belief, effect, what the person wants), so a chat moves toward an offer and does not circle. This decides what the phrase router is still for, how the choice is made and checked, and how the steering is measured. It touches ADR 002 (one model call per turn) and ADR 007 (offers follow confidence), so the decision is recorded before anything is built. Two chats from 5 October 2026 show the gap: "work pressure, parents pressure, society pressure" got Structured Problem Solving as the closest fit at message four before any event, thought or single problem was named; and "I might have a panic attack" got ACT as the closest fit after grounding, although the client's overview lists "panicked" under DBT STOP and our DBT STOP file only covers "about to act".
**Done when:** a set of real style chats (the manager chat, the two 5 October chats, and the client's own examples for all six frameworks) each reach the best suited framework offer within the client's cadence without adding a phrase to the router, and a chat that fits none of them keeps talking instead of looping.

Spec: [0005](../specs/0005-framework-fit-from-stated-facts/index.md) · code in backend/mani/chat/, backend/mani/llm/schema.py, backend/content/frameworks/, backend/content/prompts/, backend/mani/prompts/composer.py, backend/scripts/eval_replies.py

- [x] Design it (spec): `/architect how Mani chooses and steers toward a framework`
- [ ] Build it: `/develop how Mani chooses and steers toward a framework`
  - [x] The checklist in the reply, the words check, fit sets and tie rules (AC-1 to AC-5)
  - [x] DBT STOP for panic, then chat 2 end to end: redraft chain, computed offers, urgent STOP lines (AC-6 to AC-9, AC-11, AC-14)
  - [x] Chat 1 and the manager chat, and the prompt rewritten around facts (AC-10, AC-14)
  - [x] Phrase scoring removed, tests rewritten, ADR 014 and the records (AC-12, AC-13)
  - [ ] The three chats as eval scenarios, then the small paid run once muhammad says yes (AC-15)
  - [x] Full fits only: offers are the pick or nothing, the closest fit retired, tests rewritten (AC-5, AC-7, AC-16)
  - [x] Prompt and records: nearest wording out, the runner prints fact ids and redraft reasons, ADR 014 and docs (AC-16, AC-17)
  - [ ] The re-check: stress three times, grief and deadlines once, after muhammad says yes (AC-17)
- [ ] Verify it: `/check verify how Mani chooses and steers toward a framework`
- [ ] Test it: `/test how Mani chooses and steers toward a framework`

## Slice 8: Guides match the client

### 17. Guide questions match the client's wording · needs a decision

The October 2026 review compared each framework file with the client's document. The stages are right, but some questions are not: ABCDE's effect step assumes "it affected everything" and its balanced belief step states the conclusion; some replies carry all three tones in one line; most steps use one question for every tone; some "never" rules apply only at the offer step; Thought Reframe treats "I am a failure" as too big for it; ACT has added lines that judge the person's choice and imply relief; Behavioral Activation keeps two replies in the wrong stage; and some comparisons between frameworks are dropped before they reach Mani. Some follow up replies still carry the client's example details ("She has also trusted you", "your coworker and your manager", "the entire report"), so Mani can bring in people the person never mentioned. Structured Problem Solving has nothing for a person who proposes revenge, deception or an unsafe confrontation partway through, and ACT does not say what happens after "practical problem solving may fit better".
**Done when:** every stage's question is the client's own question for that stage, each tone has its own wording where the client gave one, every client "never" rule holds for the whole framework, no reply carries example details the person did not give, nothing added to a file contradicts the client's document, and the evals check stage questions and follow up replies alike.

- [ ] Design it (spec): `/architect guide questions match the client`

### 19. Body check in follows every framework · in-progress

A shared rule skips the body check in when the person's last answer names something they plan to do. Structured Problem Solving, Behavioral Activation, ACT and DBT STOP almost always end that way, so the check in is usually skipped. In every one of the client's examples Mani still asks "What do you notice in your body?". This waits on the client's answer in the index.
**Done when:** the client's worked example for each of the six frameworks reaches the body check in (or the agreed exception), covered by a test.

Spec: [0007](../specs/0007-framework-ends-with-conclusion/index.md) (muhammad decided on 2026-10-05: always ask, no exception; the spec also replaces each framework's closing question with a short conclusion) · code in backend/mani/chat/, backend/content/frameworks/, backend/content/prompts/, backend/scripts/

- [x] Design it (spec): `/architect body check in follows every framework`
- [ ] Build it: `/develop body check in follows every framework`
  - [x] The shared body check stage, the conclusion note and the question drop, then ACT end to end (AC-1 to AC-4)
  - [x] The other five frameworks and the tests that name `closing` (AC-1, AC-7)
  - [x] The two balanced thought branches for "I don't know" (AC-5)
  - [x] The base prompt paragraph, ADR-016, PORT-STATUS and the journal (AC-6, AC-7)
  - [ ] The real model read of the endings, after muhammad says yes (AC-8)
- [ ] Verify it: `/check verify body check in follows every framework`
- [ ] Test it: `/test body check in follows every framework`

### 39. Stage questions flagged in the 2026-10-05 chats · needs a decision · from spec 0007

Two things in muhammad's marked up chats are not part of the ending change. In the ABCDE chat, "From what you know so far, what seems fairest to say about your work?" was the question asked for a missing earlier answer at the balanced stage. It fired after the person answered "yes" at the evidence for stage, although the evidence against stage had real evidence, and muhammad marked it as a bad question. In the ACT chat, the person's answer to "what matters" already named a response (the half day), so the toward stage was skipped, and Mani then asked a second action question ("what is the next small thing") before ending.
**Done when:** the test for "nothing usable was said at an earlier stage" no longer fires when a later stage held the real answer, the balanced stage's missing answer question is reworded, and a person who names a response while answering what matters is not asked two action questions.

- [ ] Design it (spec): `/architect stage questions flagged in the 2026-10-05 chats`

### 20. A framework stops when the person asks · needs a decision

The client says the person can stop at any time. Today there is no "stopped" state, so a framework keeps asking its stage questions until the model walks it to the end.
**Done when:** "I want to stop" (and close variants) ends the framework in every style, Mani offers to keep chatting, and no stage question follows.

- [ ] Design it (spec): `/architect framework stops when the person asks`

### 27. Client rules the app never reads · needs a decision

Each framework file has parts Mani never sees: the "when it fits" and "when not to use it" lists and the written explanation with the worked example and the "responses to avoid" table. Some client rules live only there, for example "the user cannot take part in reflective questions" (ABCDE, Thought Reframe, ACT), "do not assume what the user will do" (DBT STOP), and "do not make the user responsible for another person's harm" and "do not treat going along with others as the best choice" (ACT). Today they change nothing. The decision is whether the app reads those parts, or every rule moves into a part it does read.
**Done when:** every rule in the client's document for each framework is in a place Mani reads, and a check fails when a file holds a rule nothing reads.

- [ ] Design it (spec): `/architect client rules the app never reads`

### 28. Shared Mani rules agree with the client's document · dropped

Dropped in October 2026: folded into row 33 (the base instructions are rewritten as a whole) and row 6 (the offer now names the framework). The client's newer style document also asks for selective mirroring, not a mirror before every question.

Mani's shared base instructions contradict the client's document in several places that affect every framework: mirroring the person's words is called "never required" where the client wants a brief mirror before every question; the client's lines for a correction ("I misunderstood your meaning...") and for stopping ("What would be most helpful right now?" in DBT STOP) are overridden; and the shared rule against saying "framework" clashes with client lines that use it. Each conflict needs one agreed answer.
**Done when:** the shared instructions and every framework file agree on mirroring, corrections, stopping and the word "framework", and nothing in the shared instructions contradicts the client's document without a recorded client decision.

- [ ] Design it (spec): `/architect shared rules agree with the client`

### 29. Our additions to the frameworks get client sign off · needs a decision

The team added rules the client's document does not have: a grief rule that blocks Behavioral Activation for the whole chat on words like "died" (so "my phone died" blocks it too), fatigue and long covid exclusions, "Thought Reframe is too light for I am a failure", ACT lines that question a choice made to ease a feeling and say "That would help the anxiety settle", "a concrete goal is enough" in ACT, a breathing anchor in DBT STOP, ending ABCDE when abuse comes up, the waiting rules before a framework may be offered, and from spec 0005 a panic branch on every DBT STOP stage and the rule that panic does not come before a full Structured Problem Solving fit. Some may be right, but each one changes the client's design.
**Done when:** every addition is either signed off by the client, changed, or removed; the grief rule no longer fires on everyday words; and each kept addition is noted where a clinician reading the file can see it.

- [ ] Design it (spec): `/architect our framework additions signed off`

### 30. DBT STOP follows the client's cadence and never delays help · needs a decision · GA

The app can offer STOP on a person's very first message ("time critical: this overrides whatever else"), while the client says STOP never replaces the usual conversation and comes only after the issue is understood and a style is chosen. Protective actions such as "I'm about to call the police" or "an ambulance for my mum" are fast tracked to STOP when they should be supported, never paused. Inside STOP, the "never tell them to put the phone down" rule only holds during the pause step, "I already sent it" has no way out of the framework, and wanting to leave Mani lacks the client's "no pressure" rule.
**Done when:** STOP is only offered within the client's cadence (or an agreed exception), a protective action is never routed to STOP, its "stay with Mani" and "no pressure" rules hold for every step, and "already acted, nothing else coming" ends it.

- [ ] Design it (spec): `/architect DBT STOP follows the client's cadence`

### 31. Every framework's worked example is a standing check

The client's document ends each framework with a full worked conversation. Only the manager chat (row 7) runs as a real model check today, so a change that breaks ABCDE's effect question or skips the body check in for Problem Solving goes unnoticed.
**Done when:** the client's worked example for each of the six frameworks runs against the real model in all three styles, and fails when a stage question, the completion question or the body check in differs from the client's.

- [ ] Build it: `/develop framework worked examples as real model checks`

## Slice 9: Robust for open launch

### 22. Reply shape built into Mani's answer format · dropped

Dropped in October 2026: fixing "a mirror, then exactly one question" into every reply is the opposite of the Natural Mani direction. Reply shape is now part of row 33.

The client's rule "mirror their words, then exactly one question" is checked today by word lists and regular expressions after the reply is written, with up to two extra model calls to fix it. Nothing catches more than one question. Making mirror, question and the evidence for finishing a stage separate parts of the model's answer would make those rules hard to break and cut the slowest turns.
**Done when:** no reply can carry more than one question or a mirror with no question, a stage only moves on when the person's own words support it, and a turn finishes within an agreed time limit.

- [ ] Design it (spec): `/architect reply shape built into the answer format`
