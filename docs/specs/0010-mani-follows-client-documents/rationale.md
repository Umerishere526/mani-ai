# 0010. Mani follows the client's documents: rationale

## Context

> ⚠️ Premise note: Lolly asked to keep the next checkpoint smaller and to test one fresh conversation "before we make another large set of changes". This spec is a large set of changes: it removes about a hundred rules across the prompts, the `[ctx]` notes, the redrafts, the repairs and the router. The build plan is therefore sliced so that slices 1 and 2 (the conversation up to the offer, the steps and the move into the somatic check) can be checked live before slices 3 and 4. If the checkpoint has to happen first, run it after slice 2.

The client says Mani is moving in a direction they do not want. In real trials and in the client's own marked up transcripts, Mani reads as interrogating: it asks question after question, repeats the person's words, and inside a framework keeps asking until a person says the conclusion they have already reached. The client's documents describe a different Mani: one short line that adds meaning, then one clear question; an offer once there is enough understanding, after about two to four exchanges; a framework that adapts; and a somatic check that always follows.

Over the last month the team answered each failure with a rule. A failure in tone became a banned word or phrase, then a redraft (a second model call that asks for the reply again) when the ban did not hold. A wrong offer became a fact the model must quote, a check that the quote is in the person's words, a fit table, tie rules, an earliest message, an owed offer and a redraft for each mismatch. A repeated question became a code limit on how a stage moves. Each rule was recorded in an ADR, so a later change had to argue past it. The inventory below counts 38 base prompt rules, 23 answer format rules, 51 `[ctx]` lines and notes, 12 redraft reasons, 35 repairs, 13 router rules, 32 orchestrator rules and 31 eval checks. Several contradict the client's writing: the client's own replies use "It sounds like a lot is happening at once", "I'm here with you", "What feels most pressing right now?" and questions of over twenty words, all of which our rules forbid.

The client's documents also disagree with each other. The six frameworks document (the oldest) asks for a mirror before every question and a stage that waits until its purpose is clear; the style document asks for selective mirroring and an offer within two to four exchanges; the PDF marks repetition and generic validation as the main faults; Lolly's email of 6 October allows Mani to state a conclusion the person has established and asks that a framework never be forced to completion. muhammad's direction (2026-10-06): the client's documents win over our rules; the client's spoken instructions from the meeting count like a document; ADRs that block this are deleted; safety, privacy and permissions are out of reach.

The forces: Mani is health software for people in distress, so the safety guards stay exactly as they are. The main model is Gemini 3.8 Flash at low reasoning effort, so whatever judgment moves from code to the model must be within its reach. The test budget for real model runs is small, so the checkpoint is muhammad's own live conversations. Nothing is deployed and the web and mobile apps still run on placeholder data, so there is no live migration to protect.

## Options considered

### Option 1: Fix in place, rule by rule

Keep the structure (facts, fit table, redrafts, stage machinery) and loosen the rules that contradict the documents: drop the word bans, raise the question limit, allow ranking questions, allow a conclusion at the last stage.

**Pros**:
- The smallest change; every existing test keeps its shape.
- Code still catches a wrong framework choice.

**Cons**:
- It keeps the mechanism the client is objecting to: the code still counts and gates, and the model is still told what it may not do in many places.
- Lolly's email asks for judgment that a gate cannot express ("I do not want the system measuring whether the user has given enough answers").
- The ADRs stay, so the next change argues past them again.

### Option 2: Replace the conversation rules in place, keep structural and safety guards (chosen)

The prompts carry only the client's rules; the model judges the offer, the steps and the synthesis; code keeps six offer refusals, one extra attempt per step, the mandatory somatic check, the body route, the structural repairs and every safety guard. The ADRs and specs that held the removed rules are deleted, and one ADR records the new source order.

**Pros**:
- Matches what the client wrote, including Lolly's principles, in one place.
- One model call per turn again.
- Far less code, and the remaining guards are the ones nobody disputes.

**Cons**:
- A wrong framework choice is no longer caught in code.
- A large change in one branch, against a client request for smaller steps (mitigated by the slicing).

### Option 3: Strangler behind a flag

Build the new rules beside the old, choose per thread by a setting, compare on real conversations, then retire the old path.

**Pros**:
- Old and new can be compared side by side; instant rollback.

**Cons**:
- Two conversation layers to maintain while the client is waiting, in a codebase with no live traffic to protect.
- The comparison needs paid runs the budget does not have.
- The old path keeps every rule this spec exists to remove.

## Rationale

Option 2 is chosen because the problem is the mechanism, not the wording of individual rules. The client's complaint, Lolly's email and the PDF all describe a conversation steered by judgment, and the code we have was built to stop the model from judging. Loosening the rules one by one (Option 1) leaves the gates in place, and the gates are what produce the interrogation: an offer forced at message four, a stage moved on by count, a question required where a sentence would do.

A strangler (Option 3) is the right instinct for a production system, but nothing is deployed, there is no traffic, and a side by side comparison needs real model runs the budget cannot pay for. Revert is a complete rollback here. The slicing gives the incremental proof the strangler would have given: slice 1 can be read live before the steps change.

The guards that stay are the ones that protect the person rather than shape the prose: the safety screen and flag, the grief veto, no offer on a first message or during a decline's cooldown, one extra attempt per step (Lolly's "one reasonable attempt"), and the mandatory somatic check (Lolly: "it remains a required part of the MANI cadence"). The outcome table exists because Lolly asked for effectiveness, "not only engagement", and nothing today records it.

The tradeoff accepted: framework choice and step completion now rest on the model. That is what the client asked for. If the checkpoint shows the model choosing badly, the answer is a better model or better guidance in the prompt (scope row 35), not a gate.

## Source order

Where two sources disagree, the newer wins: Lolly's email of 6 October 2026, then the "Good, Acceptable, Bad Conversations" PDF, then the style document, then the six frameworks document. The client's spoken instructions from the October meeting count like a document. Each source keeps its own topic where nothing newer speaks to it: the frameworks document for what each step asks and in what order, the style document for the cadence, the offer and the styles, the PDF for how a reply reads.

Clashes this settles:

| Point | Older source | Newer source, which wins |
|---|---|---|
| A mirror before every question | Frameworks document | Style document: mirror selectively; PDF: a line that adds meaning |
| A stage waits until its purpose is clear | Frameworks document | Email: move on once the step has what it needs, one more attempt, then adjust, pivot or stop |
| Mani never summarises or states the conclusion | Frameworks document | Email: Mani may state what the person has established |
| A stopped framework offers to keep chatting | Frameworks document ("You want to stop here. Would you like to continue chatting?") | Email: every framework, stopped included, goes to the somatic check (open question for Lolly in the spec's Follow-up) |
| Stuck goes to Behavioral Activation | Frameworks document overview | The client's meeting: stuck goes to ABCDE (ADR-018 stays) |

## Lolly's email, 6 October 2026

> Hi Muhammad,
>
> I agree with the direction you are recommending, with one important modification.
>
> I want us to change the current rule that MANI must never reach or state the conclusion. I believe that rule is contributing to the repetitive questioning and interrogation problem we have been seeing in testing.
>
> The distinction I want us to use going forward is this:
>
> When the user has already provided enough information to establish a pattern or insight, MANI can state that observation plainly based on what the user has already said. MANI does not need to keep asking questions simply to get the user to say a conclusion they have effectively already reached.
>
> For example, if the user has provided several pieces of evidence showing that luck does not fully explain their success, MANI can say:
>
> For the imposter-syndrome example, I would make it sound like this:
>
> "You've worked hard for this, and what you've shared shows that. Luck may have played a part, but it doesn't explain everything you've accomplished."
>
> Or, if you want it more direct:
>
> "This doesn't sound like luck alone. You've earned your place through what you've done."
>
> MANI should then move forward rather than asking another question designed to lead the user to that same conclusion.
>
> However, MANI should not go beyond the evidence the user has provided. It should not decide what the user feels, tell them what they should believe, declare that their belief is wrong, or introduce an interpretation that the user has not established.
>
> So the operating principle should be:
>
> MANI may synthesize what the user has already established.
>
> MANI should not impose a conclusion the user has not reached.
>
> I would also modify your recommendation that MANI should always "check once that it fits." I do not want that to become another required question. If MANI is making an interpretation or there is genuine uncertainty, it should check. If the evidence is already clear and MANI is simply reflecting what the user has established, it should be able to state the observation and move forward.
>
> The greater the inference MANI is making, the more important it is to check. The clearer the evidence from the user, the less MANI needs to ask.
>
> This also applies to the frameworks. The framework should guide MANI's reasoning, but it should not force MANI to continue questioning after a step has effectively been completed. Once the user has provided what is needed for that step, MANI should recognize completion and move to the next appropriate part of the conversation.
>
> There is also an important distinction when the user has not provided enough information to satisfy a framework step. MANI can make one reasonable attempt to clarify or approach the question differently. If the user still cannot provide the information, MANI should not manufacture the missing insight or conclusion simply to complete the framework. It should recognize that the framework may no longer be serving the conversation and adjust, pivot, or stop the framework. The user's response determines what happens next, not the framework's need to reach its final step.
>
> I also want to anticipate the implementation question this creates: How should MANI determine when there is enough evidence to synthesize versus when there is not enough evidence and it needs to clarify or pivot?
>
> I do not want us to solve that by creating another rigid trigger or requiring a specific number of user statements. MANI should evaluate whether the conclusion it is about to state is directly supported by what the user has already said.
>
> A useful test is: Could MANI point to the user's own statements as the basis for this conclusion without adding a new assumption?
>
> If yes, MANI can synthesize it.
>
> If MANI has to infer an important piece that the user has not established, it should not state that inference as the user's conclusion. Depending on the conversation, it can check the interpretation once, ask for clarification, or recognize that the framework is not getting us where we need to go and pivot.
>
> In other words, I do not want the system measuring whether the user has given "enough answers." I want it evaluating whether the proposed synthesis is actually supported by what the user has said.
>
> The somatic/grounding component is different. It remains a required part of the MANI cadence.
>
> Whether the framework reaches its expected conclusion, MANI appropriately synthesizes what the user has already established, or the framework needs to pivot or stop because it is no longer helping, MANI should still transition into the somatic experience.
>
> The reason we made this mandatory is important. The somatic experience is not simply the next step after a framework. It is part of how MANI helps the user move from thinking about what is happening to noticing what is happening internally. The user's response afterward also gives us an important signal about whether the conversation had an effect. We need to understand effectiveness, not only engagement.
>
> So the architecture should be:
>
> Conversation → Framework → Framework resolves or appropriately pivots/stops → Mandatory Somatic Experience → User Response/Effectiveness Signal → Close
>
> The framework is adaptive. MANI should never force a framework to completion, manufacture an insight, or keep questioning simply because a completion trigger has not been met. But once the framework has been appropriately resolved, pivoted, or stopped, MANI should transition naturally into the required somatic experience.
>
> The transition needs to feel connected to the conversation rather than procedural. And after the somatic experience, MANI needs to respond to what the user actually reports. If the user feels better, unchanged, worse, or simply does not know, that response matters. MANI should not assume the somatic experience worked or treat the conversation as successful simply because the sequence was completed.
>
> So yes, please rewrite the existing rule that prevents MANI from stating conclusions and incorporate these distinctions into the framework behavior.
>
> For tomorrow, I agree with keeping the checkpoint smaller and testing one fresh conversation from beginning to end. I want us to evaluate the full experience you outlined: naturalness, consistency across Direct, Supportive, and Reflective, listening versus interrogating, framework selection and introduction, recognizing when framework steps are complete, the ability to pivot when the user changes direction, the transition into the required somatic experience, the user's response afterward, and whether MANI closes appropriately based on that response.
>
> This should give us a much clearer indication of whether the underlying conversational behavior is improving before we make another large set of changes.
>
> Best,
> Lolly

The "direction you are recommending" refers to a message from muhammad to Lolly that is not in the repository.

## Rule inventory and what happens to each

Ids are from the read only inventory taken on 2026-10-06. Line numbers drift; the ids name the rule.

### Kept, with their source

| Rule | Ids | Source |
|---|---|---|
| Not a clinician, no clinical words | MB-01, EV-02 | Frameworks document ("no clinical language") |
| One voice, no repeated phrase or formula | MB-02, MB-03 (as formula only), RF-22 (as formula only) | Style document ("Do not create repetitive language patterns"; "I hear you" not as a formula) |
| One short line that adds meaning, never their sentence back | MB-04 | PDF ("reflect meaning without repeating the user's words"); style document (Reflective) |
| No feeling word they did not use | MB-05, EV-01 | Frameworks document; style document ("does not introduce emotions") |
| Short replies, one clear question | MB-06, MB-07 (one question, no lead clause), RF-19, RF-20, EV-06 | PDF ("one clear, thoughtful question"; lead clauses marked as grammar faults); frameworks document ("one question at a time") |
| No silver linings, danger never made milder | MB-11, EV-03 | Frameworks document (forced positivity; reframing danger) |
| No dashes | MB-12, CS-02 | PDF (em dashes marked as faults) |
| Name at most once, never first (prompt only) | MB-13 | PDF ("How does that feel for you, Montana?" marked weak) |
| `their_last`, `answering`, correction, heard | MB-15, MB-17, MB-18, CX-09 to CX-13, CX-19 | Frameworks document's "any stage" handling and the client's correction line |
| "Are you feeling stuck?" and the stuck offer | MB-16 (without "never a choice of two"), CX-38, OR-09 | Client meeting (ADR-018) |
| Three styles | MB-19, CX-14 | Style document |
| No framework name | MB-20, CP-04, EV-18 | Style document (the offer never names it) |
| Never under a safety concern; grief veto | MB-23, RF-09, RT-02, CP-05 | Out of reach (safety) |
| Pain asked about once (prompt only) | MB-24 without the code hold | Muhammad's 6 October chat marked it fine |
| Accept on yes, the client's opening lines per style | MB-27 (opening lines) | Style document |
| Client's three lines (another issue, misunderstood, stop) | MB-34, RP-33 | Frameworks document |
| Time critical risk named at once | MB-33 | Frameworks document (DBT STOP) |
| After Chat More, the client's three questions | MB-36, CX-21, EV-19 | Client |
| Off topic, prompt injection, no reveal | MB-37, MB-38, RF-01, CX-07, OR-03 | Runtime contract |
| Clarification question once | RF-03, CX-18 (prompt only; RP-07 goes) | Style document ("Ask, check, and confirm") |
| Memory never cited | RF-07, CP-08, EV-15 | ADR-005 |
| Library after the questions | RF-08, RF-18 | Style document cadence |
| Recent openers and shapes in `[ctx]` | RF-11, CX-25, CX-26, EV-09 | Style document (varied language) |
| Decline cooldown, finished not offered again, asking for a declined one is a yes | CX-03, CX-05, RF-04 to RF-06, OR-07, OR-17 to OR-19, OR-31, CP-09 | Style document ("I want to keep talking") |
| No offer on the first message | CX-01 (reduced to the first message) | Style document (understand first) |
| Urgent DBT STOP lines, panic branch | RT-01 (without the fact), OR-08, CX-27, CX-50, MB-33 | Frameworks document (DBT STOP); ADR-010 |
| One extra attempt per step, never backward | RP-26 (one counted hold), TQ-04 (backward and unknown only), TQ-05 | Email ("one reasonable attempt") |
| No other framework while one runs | RF-21 (first sentence), RP-16 | Frameworks document ("does not move to another framework") |
| Body route and somatic stages | RP-31 (keeps the line), RP-32, RP-34, OR-24 to OR-28 | Client's somatic flow; email (mandatory) |
| Structural repairs | RP-01, RP-10, RP-15, RP-18, RP-20, RP-21, RP-22 (new questions), RP-24, RP-25, RP-29, RP-30, OR-29 | Runtime contract |
| Safety flag and pause | RF-16, CX-15, CX-16, OR-16, OR-22, OR-23 | Out of reach (safety) |
| One model call a turn | ADR-002 | Runtime contract |

### Removed

| Rule | Ids | Why |
|---|---|---|
| Banned phrases as words ("It sounds like", "It seems like", "I am here with you", "that makes sense") | MB-03, RF-22, RP-05, RD-02, CS-01 | The client's own replies use them; only the formula is banned |
| Banned words ("example", "pattern", "belief", "process", "explore", "reflect", "conclusion", "meaning") | MB-09, EV-16 | The client's documents use them; plain words stay a principle |
| Size words ("a lot", "heavy", "overwhelming") | MB-10, RP-04, EV-05, CS-05 (size half) | The PDF's corrected replies use "a lot" |
| Ranking ban, 16 word limit, either/or ban | MB-07 (limit), MB-08, MB-16 (choice half), EV-16 | The client's replies ask "What feels most pressing", "Which one keeps pulling at you the most", and offer choices |
| Never state a meaning or conclusion | MB-04 (old form), the conclusion only note | Email |
| Presence line for loneliness | MB-14 | Ours; the style document covers Supportive warmth |
| Facts, quote check, fit sets, tie rules, nearest fit | MB-21, MB-22, RF-15 (facts step), RT-03 to RT-13, OR-10 (fit use), OR-12, OR-13, CP-02, CP-06 (message number), `fits_when` | Style document: offer once there is enough understanding; the model chooses |
| Earliest offer message, owed offer, offer redrafts | CX-02, CX-06, OR-14, OR-20 (reduced), RD-03 to RD-12, RP-17 (reduced to the six refusals) | Style document: "a range, not a required count" |
| Pain hold in code | RD-11 | Goes with the owed offer |
| Two button offer, "Tell me more" dropped | MB-25, MB-26, RP-11, OR-06 (labels) | Style document: three buttons |
| Code enforced tone | RD-01, RD-02, RP-02 (runtime use), RP-03 (runtime use), RP-07, RP-08, RP-09, RP-12 to RP-14, OR-15, OR-21, CX-51 | Muhammad: the prompt states the rules, no tone code |
| One stage per reply, none skipped, told and passed over stages | MB-28 to MB-32, RF-13, RF-14, RF-21 (order half), CX-28 to CX-37, CX-39 to CX-49, TQ-01 to TQ-03, TQ-04 (skip refusal), RP-27, RP-28, OR-30 | Email: the model recognises completion |
| Ending with a conclusion and no question | MB-35, CX-44, CX-45 | Email: a connected bridge, then the somatic check |
| Evals of removed rules | EV-07, EV-12, EV-13, EV-17, CS-03, CS-07, CS-08, CS-10 (meaning as fact), CS-11 | Measure only what the client asks |

Evals that stay as measurements only: EV-01 to EV-04, EV-06, EV-08 to EV-11, EV-14, EV-15, EV-18, EV-19, CS-01 (repetition only), CS-02, CS-04 to CS-06 (feelings), CS-09, CS-12.

### ADRs

| ADR | Fate | Why |
|---|---|---|
| 001, 003, 004, 009 | stay | Not the conversation layer |
| 002 | stays | One model call per turn becomes true again |
| 005 | stays | Memory |
| 006, 007, 008, 011, 012, 013, 014, 015, 016, 017 | deleted | Their rules are removed or replaced above |
| 010 | stays | The panic guidance is framework content (scope rows 29 and 30) |
| 018 | stays | The client's spoken instruction |
| 019 (new) | written | Source order and Lolly's principles |
