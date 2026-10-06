# 0009 rationale: a person who stays stuck while Mani is understanding is offered ABCDE

Decision record for [index.md](index.md). `/develop` does not read this file.

## Context

In the October 2026 client meeting, as muhammad relayed it on 2026-10-05, the client described a person who comes to Mani in pain, in body or mind. Mani asks questions to understand. If the person keeps answering "I don't know" or "I can't think", or the conversation loops, Mani should offer ABCDE, because its steps guide them through what is going on. If a thought is causing the pain, Thought Reframe. The pain itself triggers nothing; how the conversation goes does.

Today no framework can be offered to that person. Since spec 0005 a framework is offered only when the facts the model reports fully fit one of its sets, and ABCDE needs a specific event and what the person made of it. The fact `unsure_what_to_do` says outright that a bare "I don't know" does not count, and it leads to Structured Problem Solving. Spec 0008, built the same day, added "Are you feeling stuck?" as a once only check for this person and said the check never leads to an offer. So the stuck person gets plain questions forever, which is what the old Mani chat showed ("i dont know" twice, then "i cant decide" twice).

The client's written material pulls the other way. The overview maps "stuck" to Behavioral Activation and "do not know what to do" to Structured Problem Solving, and ABCDE's own "when not to use" list names an unclear issue and a person who cannot answer reflective questions. muhammad first wanted ABCDE after the stuck check while designing spec 0008 and set it aside when the overview was shown; the meeting is why it is back. Two more forces: the body pain rule (Mani offers nothing when the pain is in the body, and `redraft.pain_mentioned` holds back any due offer once "pain", "hurts" or "ache" appears), and the reliability of the current model's fact marking, which row 35 found weak.

Not deciding leaves the client's instruction unbuilt and the stuck person with no guided path.

## Options considered

### Option 1: a `stuck` fact the model reports, kept only after the check

The model reports `stuck` with the person's own words when they keep saying they do not know or cannot think, or say yes to the check. Code keeps it only once the check is in Mani's recent messages, counts a `stuck` only fit below every other fit, and carries ABCDE's offer lines into `[ctx]` on the turn after the check.

**Pros**:
- Reuses spec 0005's fact, words check and redraft machinery with one new fact and one gate.
- The model reads stuckness and looping in any words; code still guarantees the check comes first.
- The words check holds unchanged, because the quote is their earlier stuck words, not the one word "yes".

**Cons**:
- Depends on the model marking a fact, which the current model does unreliably.
- Two places now carry candidate offer lines into `[ctx]` (DBT STOP and this).

### Option 2: code reads the answer to the check

Code sees that Mani's last message asked the check and reads the person's reply: anything but a no (or only a clear yes) makes ABCDE the pick, with no model judgment.

**Pros**:
- Fully deterministic and cheap to test.
- No dependence on the model's fact marking.

**Cons**:
- A phrase list for yes and no, the kind of rule the project moved away from in spec 0005.
- Cannot express muhammad's "after a no, two more stuck answers" without a second list for stuck answers.

### Option 3: offer straight after stuck answers, no check

After two stuck answers, ABCDE is offered with no "Are you feeling stuck?" first.

**Pros**:
- One turn faster to the guided questions.

**Cons**:
- The person never confirms they are stuck; a brief "I don't know" twice can trigger a framework.
- Spec 0008's check would have no job and would be removed, a day after it was built.

### Option 4: leave the fit rule alone

Keep spec 0005: only event plus meaning makes ABCDE fit; the check stays a check.

**Pros**:
- Matches the client's written overview and ABCDE's own limits; nothing changes.

**Cons**:
- Does not do what the client asked in the meeting.

## Rationale

muhammad chose each part in the design conversation: the trigger through the check (over offering straight away or a model only fact), the model judging stuckness (over a fixed list), two stuck answers in any order, the full fit of another framework winning, the model judging the answer to the check, ABCDE still reachable after a no once two more stuck answers come, bodily pain not holding this offer, the stuck route only lifting that hold, starting at ABCDE's second step with one line for every style, the offer line saying it is hard to sort out now, spec 0003's move on rule inside ABCDE, and the paid run folded into spec 0008's.

Option 1 is the one design that honours all of those at once. Making the model the judge of stuckness fits the project's direction since spec 0005 (judgment from the conversation, not phrase lists), while gating the fact on the check gives code a hard guarantee that the person was asked before anything is offered. Counting the `stuck` set below every other fit keeps the client's own distinction (a thought that hurts gets Thought Reframe) and keeps DBT STOP first for an action about to happen. Carrying ABCDE's offer lines into `[ctx]` on the turn after the check, the way DBT STOP's are carried, means the first draft can make the offer in the right words rather than relying on a redraft. Starting at the `belief` step through a branch, like DBT STOP's panic branch, avoids "What happened?" for someone who has named no event, and reading the route from `known` needs no new state.

Two choices go against my advice and are recorded as such. On bodily pain, muhammad chose to let ABCDE be offered. The safety screen catches medical emergencies first, which limits the risk, but ABCDE can still be offered to someone whose pain is a medical problem that has not been seen to; the base prompt keeps asking whether it has. And the route rests on a spoken instruction that contradicts the client's written overview, so the Follow-up asks for it in writing.

## Evidence

- The old Mani chat (journal `questions-easy-to-answer-old-mani-chat-2026-10-05`): "i dont know" twice, then "i cant decide" twice, no guided path.
- `router.FACTS["unsure_what_to_do"]` excludes a bare "I don't know"; `abcde.md` `fits_when` is `[[event, meaning]]` and its `not_when` names an unclear issue.
- `redraft.pain_mentioned` holds back any due offer once "pain", "hurts" or "ache" appears; `safety.py` screens "chest pain" and "cannot breathe" as medical emergencies before any framework.
- `context._stage_lines` already carries DBT STOP's offer lines as a candidate and its `panic` branch as `_when_panicked`; `redraft._offer_guidance` already switches to the panic branch from the facts.
