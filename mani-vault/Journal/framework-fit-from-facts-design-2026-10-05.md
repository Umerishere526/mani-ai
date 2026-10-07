---
type: journal
date: 2026-10-05
tags: [journal, frameworks, router, design]
---

# Designing "a framework is chosen from facts the model states" (row 8)

Spec: `docs/specs/0005-framework-fit-from-stated-facts/`. Triggered by two chats on 2026-10-05: stress about work, parents and society got Structured Problem Solving, and a panic attack got ACT, both as the closest fit forced at message four with nothing matched by the phrase router.

## What muhammad wanted and how it landed

- He wanted a semantic router, not more phrases, and brought research proposing an embedding hybrid (hard rules, semantic candidates, decision layer). We kept the three layers but made the semantic layer the chat model's own checklist of ten facts with quoted words, because the client's table is structural (event named or not, knows what to do or not) and embeddings always return a nearest guess. Chat 1 needed "nothing named yet", which only facts can say.
- His expectation that chat 1 should get ABCDE or Thought Reframe was premature: no event and no single thought had been named. The right move there is a question, then ABCDE or Reframe once one is said. Chat 2 is DBT STOP by the client's own overview.
- He explains well when the question is plain. Two of my questions came back as "explain simply and ask again"; leading with what the code does today worked better.

## Things that were not obvious

- **The client's documents disagree about DBT STOP.** The overview lists "panicked" under STOP; the detailed STOP spec and our file cover only pausing before an action, and our offering boundary forbids offering before an action is named. Widening the description alone would have told a panicking person "you are about to send the message". STOP needs a `panic` key per stage, now on the sign off list.
- **ADR 010's lost wallet chat says "I am panicking".** Making panic absolute for STOP would have flipped it from Structured Problem Solving. Only `about_to_act` is absolute.
- **The checklist comes out with the reply**, so anything in `[ctx]` (built before the call) can only use last turn's facts. Steering therefore happens from the model's own checklist in the same reply, and code checks afterwards.
- **A nearest fit that is not a full fit can only be ABCDE or Structured Problem Solving**, the only frameworks with two fact sets. Grief reaches an offer only through `cannot_control`.
- **The old rules looked only at the last two messages** (`router._fired`); facts need the same recency for the two STOP facts, or one panic message keeps STOP first for the whole window.

Related: [[stage-moves-on-design-2026-10-04]], [[what-every-conversation-is-for]], [[measure-before-tuning-prompts]].
