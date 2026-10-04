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

From the client meeting in October 2026 and the client's style document ("directive, reflective, supportive"). The client finds Mani robotic, too complicated, too full of questions, and repeating "I hear you"; people do not feel heard. This phase is built first, ahead of the slices below: measure (row 32), then rewrite (rows 33, 34, 18, 6), then choose the model (row 35) on the same check.

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

### 18. A framework stage moves on after one answer · needs a decision

Inside a framework, whatever the person replies to a stage's question (a real answer, "I don't know", "sure", "yeah", "yes", or a question of their own), Mani moves to the next stage instead of asking again in other words. A question they ask is answered first, then Mani goes on. Today a stage holds until its `ready_when` is met (ADR 011), and "I don't know" gets up to three options, a draft, or the same question reworded (ADR 010). The cost to design around: the next stage must work with what it has, so a skipped answer never leaves a later stage with nothing to ask about (for example ABCDE's dispute step after "I don't know" at the belief step). This also settles the open client question about suggesting options when someone is stuck.
**Done when:** in every framework, a real answer, "I don't know", "yes", "sure" and a question of their own each move to the next stage within one reply, no stage question is asked twice, the framework still reaches the body check in, and a test covers each framework.

- [ ] Design it (spec): `/architect a framework stage moves on after one answer`

### 6. The offer names the framework, introduces it, and gives three choices · needs a decision

When Mani offers a framework it says the framework's plain name and a short introduction to what it does, then the client's three choices: "Yes, let's try it", "Tell me more" and "I want to keep talking". "Tell me more" gets a short explanation in the style in force, then the other two choices again. Today the shared rules forbid the name and the word "framework", the offer has two buttons (Try it, Keep chatting), and the app adds a stored description and "Would you like to try it?". The client's style document says "I have a structured approach..." with no name, so the naming needs the client's confirmation in writing. The October 2026 review still applies: Thought Reframe's description promises "you will be able to see the situation differently", and Structured Problem Solving's names a feeling ("overwhelming").
**Done when:** every offer in every style names the framework and introduces it in plain words, carries the three choices, "Tell me more" returns the remaining two, no introduction promises a result or names a feeling the person did not use, and row 32's check covers it.

- [ ] Design it (spec): `/architect the offer names and introduces the framework`

### 35. The model is chosen on real conversations · needs a decision

Every reply today comes from the smallest, cheapest tier of a single model family. An earlier comparison only checked whether a model could carry a conversation through every stage. Candidates from the major providers and from the open model families are compared on row 32's check with the new instructions: how natural the replies read, whether it follows what the person means, whether it completes a framework through the body check in, how reliably it returns the structured reply, time per reply, and cost per conversation.
**Done when:** at least four candidates, two of them open models, run three times each on row 32's check, the numbers and one transcript per candidate are recorded in the decision, and the chosen model is in the seeded prompts.

- [ ] Design it (spec): `/architect the model is chosen on real conversations`

## Slice 4: Offers and checks

### 7. The manager chat is a standing real conversation check

The reported manager chat becomes a scenario in the real model evals, so a later change that moves the offer back to structured problem solving is caught. From spec 0001.
**Done when:** the scenario runs in all three styles and fails if ABCDE is not the framework offered.

- [ ] Build it: `/develop manager chat eval scenario`

## Slice 5: Judgment, not phrase lists

### 8. Mani picks the best framework from the person's situation and steers toward it · needs a decision

Framework choice today rests on phrase lists in the router, and every missed case means another phrase or rule (row 5 was one). Instead, Mani should judge which framework fits from the whole conversation and the client's distinction rules, and use its questions to find out what is missing for that framework (event, belief, effect, what the person wants), so a chat moves toward an offer and does not circle. This decides what the phrase router is still for, how the choice is made and checked, and how the steering is measured. It touches ADR 002 (one model call per turn) and ADR 007 (offers follow confidence), so the decision is recorded before anything is built.
**Done when:** a set of real style chats (the manager chat and the client's own examples for all six frameworks) each reach the best suited framework offer within the client's cadence without adding a phrase to the router, and a chat that fits none of them keeps talking instead of looping.

- [ ] Design it (spec): `/architect how Mani chooses and steers toward a framework`

## Slice 8: Guides match the client

### 17. Guide questions match the client's wording · needs a decision

The October 2026 review compared each framework file with the client's document. The stages are right, but some questions are not: ABCDE's effect step assumes "it affected everything" and its balanced belief step states the conclusion; some replies carry all three tones in one line; most steps use one question for every tone; some "never" rules apply only at the offer step; Thought Reframe treats "I am a failure" as too big for it; ACT has added lines that judge the person's choice and imply relief; Behavioral Activation keeps two replies in the wrong stage; and some comparisons between frameworks are dropped before they reach Mani. Some follow up replies still carry the client's example details ("She has also trusted you", "your coworker and your manager", "the entire report"), so Mani can bring in people the person never mentioned. Structured Problem Solving has nothing for a person who proposes revenge, deception or an unsafe confrontation partway through, and ACT does not say what happens after "practical problem solving may fit better".
**Done when:** every stage's question is the client's own question for that stage, each tone has its own wording where the client gave one, every client "never" rule holds for the whole framework, no reply carries example details the person did not give, nothing added to a file contradicts the client's document, and the evals check stage questions and follow up replies alike.

- [ ] Design it (spec): `/architect guide questions match the client`

### 19. Body check in follows every framework · needs a decision

A shared rule skips the body check in when the person's last answer names something they plan to do. Structured Problem Solving, Behavioral Activation, ACT and DBT STOP almost always end that way, so the check in is usually skipped. In every one of the client's examples Mani still asks "What do you notice in your body?". This waits on the client's answer in the index.
**Done when:** the client's worked example for each of the six frameworks reaches the body check in (or the agreed exception), covered by a test.

- [ ] Design it (spec): `/architect body check in follows every framework`

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

The team added rules the client's document does not have: a grief rule that blocks Behavioral Activation for the whole chat on words like "died" (so "my phone died" blocks it too), fatigue and long covid exclusions, "Thought Reframe is too light for I am a failure", ACT lines that question a choice made to ease a feeling and say "That would help the anxiety settle", "a concrete goal is enough" in ACT, a breathing anchor in DBT STOP, ending ABCDE when abuse comes up, and the waiting rules before a framework may be offered. Some may be right, but each one changes the client's design.
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
