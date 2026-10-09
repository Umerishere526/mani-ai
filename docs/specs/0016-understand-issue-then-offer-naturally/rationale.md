# 0016. Rationale: Mani understands the issue, then offers naturally

## Context

> ⚠️ Premise note: the client's transcripts come from a build before scope features 15 and 17. Their quoted offer lines ("…there are some questions we could go through together") were the model's own recap before an offer, and that can no longer happen: since spec 0013 the code replaces the model's whole reply on an offer turn with seeded text. So the recap they named is gone, but the abruptness is not. Today the person's last message before an offer gets no answer at all. They say "I've been at my current company for years… I'm worried I might regret leaving" and the next thing they see is "There's a framework called…". The fix has to restore an answer to that message without bringing the recap back.

> ⚠️ Premise note: the client asks for no fixed number of exchanges, and the code already enforces none beyond `clear_offer_after: 2` (no offer on the very first message). That floor is a guardrail, not a target, and stays. What decides the offer above it is the prompt's definition of "understood", so that definition is the lever, not a count.

> ⚠️ Premise note: "both sides are explored before any offer" (scope feature 22's done line) is how the general rule shows in a decision. The general rule is "what they are struggling with and what makes it hard". The real runs check it on one conversation, the client's own; whether it holds on other issues is feature 11's to measure.

The client reviewed one conversation, a choice between a new job and staying, in all three styles (`docs/client-share-docs/mani-response-feedback-2026-10-08.md`). Their points group into three problems. Mani hands back what the person just said, their frustration or their second guessing, in constructed language (points 1, 4, 6, 7). Mani asks a narrow question, about one option or one fear, before it knows what the decision even is (points 2, 4). And Mani moves into a set of questions abruptly, with a recap, sometimes after a single exchange (points 3, 5, 8). Their principle: understand the problem, introduce the framework naturally, use what the user already shared, and never make them explain the same situation twice.

Reading the prompts against the feedback shows where each problem comes from. Mirroring is taught three times: the `mirroring` move ("the one part that matters most, in your own words"), the `mirror and ask` shape ("reflect the part that matters"), and the first reasoning step, which asks the model every turn "what is their feeling in their words?". Nothing asks what the issue is first: the only rule about a first question covers someone who named no feeling or problem, and the client's person named one (frustration), so the model narrowed on it. The offer rule says "once you can tell what the issue is and which set fits", and on the person's second message Structured Problem Solving's Starts when already fits, which is when Supportive offered. On a yes, `framework_starting` asks the model to "say them back in a clause", a recap at the start of the questions.

Two constraints from muhammad bound the fix. Mani changes by cutting and replacing prompt rules, never adding them, because added rules make the model drift ([[prompt-changes-cut-not-add]] in the journal). And the code does not repair the model's reply (spec 0006). The offer's words stay the client's (specs 0013 and 0015).

## Options considered

### Option 1: Replace prompt lines one for one, and send the model's line before the seeded offer (chosen)

Seven lines are swapped, each for one line: the mirroring move, the `mirror and ask` shape, the first reasoning step, the second `questions` line, both `offers` lines that this touches, and `framework_starting`. On an offer turn the code keeps the model's text and puts the seeded offer after it.

**Pros**:
- Each client problem traces to a named line, and each line is replaced, not supplemented. The prompts end at the same 145 lines.
- The person's last message gets an answer, which is what makes an offer feel like a next step.
- The client's offer wording stays word for word.
- A small code change on one path; nothing new to configure.

**Cons**:
- The model's line is unchecked. A recap, a second question or a second offer sentence can come back, and only real runs show it.
- "What makes it hard" asks the model for judgment; it may keep asking longer than needed on some issues.
- The offer turn is no longer entirely seeded text, a partial step back from spec 0013's "the code writes the offer".

### Option 2: Prompt lines only, with a softer seeded lead

The same prompt cuts, and the shared `offer.text` gains an opening like "From what you've shared, a few focused questions could help". The model's text is still dropped.

**Pros**:
- No code change; the offer stays entirely seeded and exact.

**Cons**:
- The person's last message still gets no answer. A generic lead is the same in every conversation, which is the "scripted" feel the client named.
- ABCDE's per style texts (spec 0015) are the client's words and stay as abrupt as they are.

### Option 3: The model writes the whole offer

The model writes the offer in its own words, with the seeded text in the prompt as a guide.

**Pros**:
- The most natural transition the model can manage, fitted to each conversation.

**Cons**:
- Undoes specs 0013 and 0015, where muhammad and the client chose exact wording for the offer.
- Brings back the recap before the offer that the client complained about in points 3 and 8.
- Adds a guide for the offer to the prompt, against the cut, never add rule.

### Option 4: Enforce the timing in code

Raise `clear_offer_after` to 3, or hold the offer until a count of exchanges.

**Pros**:
- Certain: the Supportive case in the feedback could not happen.

**Cons**:
- It is the fixed rule the client explicitly asked not to have.
- A person whose first two messages say everything is made to answer one more question, which the client warns becomes repetition inside the framework.
- It does nothing for mirroring or the first question.

## Rationale

The client's feedback is not about timing as such ("The issue is not necessarily how soon the framework appears. It is how naturally MANI arrives there"), so a code count (Option 4) fixes the wrong thing and contradicts them. The three problems they name all trace to prompt lines that ask for exactly the behavior they dislike, which makes replacing those lines the direct fix and keeps muhammad's rule against adding rules. Measuring before tuning further ([[measure-before-tuning-prompts]]) is why the proof is three real runs of the client's own conversation, not unit tests.

The transition is the one place a prompt change alone cannot reach: the model can write the perfect bridge, and today the code throws it away. Option 2 keeps the offer exact but leaves the person's last message unanswered, and a generic lead is precisely the "scripted" quality the client called out. Option 3 answers it but at the cost of the client's own offer wording, chosen in two specs this week, and invites the recap back. Option 1 takes the narrow middle: the model gets a short text, with no question, no recap and no offer of its own, and the client's words follow. Its weakness, an unchecked line, is the same weakness every other reply already has under spec 0006, and the runs measure it.

Within Option 1, muhammad chose (2026-10-08): redefine mirroring rather than cut it (the shape names stay, so no code or test churn, and the Reflective style line still has something to point at); replace the first questions clause rather than lean on the offer line; define "understood" as the issue and what makes it hard, for all six sets, rather than editing one framework's Starts when; keep the floor of 2; cut the say back on a yes; no code check on the bridge; and one run per style of a new `client_job_decision` scenario. The edit to the `mirror and ask` description (E2) was added at write time, since leaving "reflect the part that matters" there would keep teaching the restatement the redefined move removes.

The cross check (a read only pass on another model) changed two things, both chosen by muhammad. E5 gained "when they are weighing a choice, what pulls them each way": without it, the client's second message ("good reasons for both, I'm afraid of making the wrong choice") already satisfied the rule, so the Supportive offer at message 2 would likely have come back. And the join became one rule for every offer the checks keep, including an offer made again after a typed question about it. There, the model's answer to "what would that involve?", which `offers` line 54 asks for, has always been dropped by the code; E6 was reworded from "nothing about the set" to "no offer of your own" so the two lines agree. E6 avoids a colon followed by a space, which YAML would read as a key inside the list item.

## Round 2 (2026-10-08)

> ⚠️ Premise note: round 1's three real runs of `client_job_decision` all failed AC-8. The timing half held in every style: the first reply asked what the decision was, and the offer came at message 3. The restating half did not. Every style opened a reply before the offer by handing back the person's feeling, "frustrated" as "That sounds frustrating", "afraid" as "you're worried about getting it wrong", and Reflective retold their situation in message 2. The line before the offer answered them only in Supportive. Direct wrote "I can help you sort through the choice and find a practical next step", an offer of its own, and Reflective a recap plus "We could sort through the choice step by step".

### Context

E1 to E3 redefined mirroring, but the model does not treat "That sounds frustrating" as a mirror. It is care, and four lines still teach care as naming their feeling or their details. `rules` line 18, "Use their words. Never name a feeling they have not named", reads as permission to name one they did. `warmth lead: lead with care, then ask` says nothing about what the care is about. The Supportive style line asks it to acknowledge "what they share", and the Reflective one to reflect "the meaning and important details in what they actually say", which is the recap itself. The client's own better replies show the target: a few words of care about the situation, never their feeling handed back ("Making a decision can be difficult when you keep questioning yourself.", "Sometimes the hardest part of a decision is understanding what's keeping you from making it.").

E6's "no offer of your own" was too abstract. The model did not read "I can help you sort through the choice" as an offer, and the seeded Structured Problem Solving offer then said "practical next step" twice more.

One run per style could not tell which line drove a reply: the eval removes its users and their rows, and prints no shape.

### Options considered

**Option A: swap the four lines that teach care as naming, and make E6 concrete (chosen).** E8 (`rules`), E9 (`warmth lead`), E10 (Supportive), E11 (Reflective), each one line or one span for one, and E6 rewritten to say the offer's own words already say what the questions do. Pros: each traces to a reply in the failed runs; the prompts stay at 145 lines and grow by 6 words; the client's target is said in positive form. Cons: two of the lines are the client's own style wording; with "Use their words" gone, nothing general asks for their words outside the stage questions.

**Option B: cut only "Use their words" from line 18.** The smallest change. Cons: the rest of the line still says "never name a feeling they have not named", which leaves naming a feeling they did name allowed, the exact failure. Reflective's "important details" stays.

**Option C: leave the client's style lines alone.** Keeps their wording untouched. Cons: Reflective's "Reflects the meaning and important details in what they actually say" asks for the recap the client complained about in points 7 and 8; Supportive's "Acknowledges what they share" invites the restatement in its message 2.

**Option D: relax AC-8 so a line on how the set could help passes.** The client did ask for a transition that briefly explains how the framework could help. Cons: the seeded offer already does that, so the person reads "practical next step" two or three times, the scripted feel the client named.

**Option E: diagnose first, with a run on today's prompts printing shape and reasoning.** The most certain way to find the driving line. Cons: one more round of runs before any change, for lines the reading already points at. The rerun prints the same data, so a second failure is diagnosed anyway.

### Rationale

The failed replies trace to lines that ask for them, so replacing those lines is the direct fix and keeps the cut, never add rule ([[prompt-changes-cut-not-add]]). Option B leaves the permission in place, and Option C leaves the recap instruction in place. muhammad has allowed rewording the client's text where it misleads the model, and the client's own examples are what E9 to E11 now describe. Option D accepts a repetition the client would see. Option E costs a round for information the rerun collects anyway.

muhammad chose (2026-10-08): update spec 0016 in place; all four restating lines including Supportive; E6 rewritten concretely; three runs per style with a bullet passing on 2 of 3, because one run is noise ([[measure-before-tuning-prompts]]); restating graded as a feeling handed back in any form or a sentence retelling what they said, while care about the situation passes; the say back after Try It measured only, since the client's rule inside a set is not asking again, which held; and the shape and reasoning of every reply printed on the rerun.

The round 2 cross check (a read only pass on another model) found gaps in how the runs would be measured, and muhammad applied all eight fixes. The wrapper must wrap `orchestrator.send`, since `_open_chat` makes no model call. Turning on `AI_DEBUG_MODE` would add the debug row to the system prompt and measure a different prompt, so only the orchestrator's settings are swapped. A reply's shape is found by counting `thread_response_styles` rows around each call, because the table has no message id. The `labelling` finding flags only feeling words the person did not use, so restating is graded by hand. A run with no offer fails the offer bullets out of 3. And since E8 and E9 touch every reply, `disclosure_no_question_needed` runs once per style as a measured regression record.

## Round 3 (2026-10-08)

Round 2 changed five lines and failed again. Round 3 redesigns the offer turn and moves the restating fix to the reasoning step.

### Context

Round 2's nine runs, out of 3 per style (Direct / Supportive / Reflective): no restating before the offer 0 / 0 / 2; first reply asks what the decision is 3 / 3 / 3; offer at message 3 or later 3 / 2 / 1; bridge with no question and no recap 0 / 0 / 0. Reflective's two restating passes came from offers at message 2, which left only one reply to judge.

- **Restating.** "That sounds frustrating" opened 5 of 6 Direct and Supportive runs, always under `warmth lead`, which E9 had just rewritten. Every one of those replies had reasoning that began "they need to be heard" or "a kind acknowledgment". The reasoning field is generated before `text` (schema order, [[measure-before-tuning-prompts]]). Its first step, as E3 left it, asks "What do they need right now, whether comfort, space, acceptance, agency or to be understood?". The model answers "to be heard", then writes a reply that hears.
- **Bridge.** Every bridge line made an offer of its own and ended "Would you like…?", with reasoning such as "Offer it now". The seeded generic lead then said it again ("Would it help to work through it together?"). Reading the client's feedback again, their point 5 asks for exactly what the model wrote: "make a natural transition, explain briefly how the framework could help, and allow the user to choose." So the duplicate is the generic lead, which is muhammad's wording from spec 0013, built from Structured Problem Solving's own description. The model is doing what the client asked. ABCDE is different: the client wrote its offer per style, and their text already explains and asks.
- **Timing.** Three of six Supportive and Reflective runs offered at message 2, right after "There are good reasons for both". The client calls exactly that abrupt (point 8, about Supportive). E5's "what pulls them each way" was read as satisfied by "good reasons for both".

### Options considered

**The offer turn**
- **The model's line is the offer, and the card follows (chosen).** For the five sets without the client's wording, cut the generic lead from `offer.text`, leaving "Framework: {name}" and the description. E6 says the line is the offer. ABCDE keeps the client's text alone. Pros: matches the client's point 5 and what the model already writes; removes the "practical next step" said twice (an open item since spec 0013); keeps the client's words wherever they exist. Cons: the offer for five sets is unchecked model text, which can recap; there are two paths through `offers.offer`.
- **The seeded offer alone again** (the model's line dropped on a first offer and a return, kept only for a typed question). Pros: the double offer is certain to go. Cons: the person's last message gets no answer, and the generic lead stays, which the client called scripted (point 3). It undoes round 1's reason for the join.
- **Keep the join, and cut the `response_format.md` lines that frame the reply as the offer** (`conversation_phase`'s "then offer as offers says", the reasoning step's "Then offer or not"). Pros: prompt only. Cons: a third prompt round against an instruction that failed 9 of 9, while the model never sees the text it sits in front of.

**ABCDE after a typed question**
- **The answer, then the client's text (chosen).** They asked something and get an answer. A second ask is possible.
- **The client's text alone, always.** One rule, but the question goes unanswered and the same offer is repeated.

**The restating**
- **Reasoning step 1 starts from what they face (chosen):** "What are they facing, and what do you not yet know about it?". It hits the field written first, and every failing reply's reasoning traced to it.
- **Keep the needs list and drop "to be understood".** A smaller move, but "comfort" and "acceptance" still point at hearing.
- **Step 1 plus the `acknowledgment` move.** Two levers at once, so a result can't be traced to one.
- **Measure only.** It leaves the client's most repeated point unfixed.

The client's own example sentences were not pasted into the prompt. Prompt examples come back near word for word ([[measure-before-tuning-prompts]]), and `client_job_decision` is the client's own conversation, so the runs would measure recall.

**The timing**
- **One concrete span in E5 (chosen):** "what draws them to each option, not only that both have reasons".
- **Measure only.** Reflective fails the bullet 1 of 3.
- **A floor of the third message** (`clear_offer_after: 3`). A fixed count, which the client asked not to make a rule, and still only told to the model.

### Rationale

The bridge failed because two writers made the same move, not because the model ignored E6. Making the model the writer of the offer for the sets the client has not written, and the client the writer where they have, gives the person one offer in every case. It follows the client's point 5 literally, and it keeps their documents first ([[client-documents-win-over-our-rules-and-adrs]]). The rule lives in `offer.py`, beside the choice of seeded wording it depends on, and it reads the row and the turn's path, never the model's words, so spec 0006 holds. E12 and E5 round 3 are swaps of one line and one span, so the prompts stay at 145 lines and shrink by 2 words ([[prompt-changes-cut-not-add]]).

muhammad chose (2026-10-08): the model's line as the offer with the card after; for ABCDE after a typed question, the answer then the client's text; reasoning step 1 issue first; E5 concrete; the same proof as round 2; and the fourth bullet graded as "step, help, ask" (follows from what they said, says briefly how the questions could help, asks, no recap of their details, no feeling handed back).

The round 3 cross check (a read only pass on another model) confirmed the counts, the single caller of `offers.offer`, and that `answering` is exact at the offer step. It found eight gaps, and muhammad applied all eight fixes:
- An eval test that relied on "overwhelming" in the cut lead.
- One test helper asked to give two answers for ABCDE.
- No named source for the unit test's framework row.
- No grading rule for an ABCDE or blank offer in the runs.
- A stale skip comment in the eval script.
- Comments and docstrings that still said the offer is all seeded.
- The stripped line left unstated.
- A restart missing after the reseed.

## Round 4 (2026-10-09)

muhammad saw an ABCDE offer in the client's per style wording and asked for the shared seeded offer on every set instead: the spec 0013 lead, the name, and the description from the client's intro document. Round 3 had removed the double offer by handing the offer to the model. Round 4 removes it the other way, by dropping the model's line on an offer turn.

muhammad chose (2026-10-09):
- The seeded offer goes out alone, with the model's line first only when it answers a typed question about the offer. Keeping the line next to the restored lead would bring back round 2's double ask.
- The name is shown, although the intro document says not to give it.
- Tell Me More stays as it is. For the five sets without the client's steps, it repeats the description already in the offer.

Cost: the offer turn no longer answers the person's last message, which is the cost round 3 avoided. The lead is Structured Problem Solving's own description, so for that set "practical next step" is said twice.

