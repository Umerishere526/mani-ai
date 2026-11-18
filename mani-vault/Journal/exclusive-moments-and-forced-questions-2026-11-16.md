---
type: journal
date: 2026-11-16
tags: [journal, cadence, safety, framework, design, client-test]
---
> Superseded 2026-11-17 (moments, and every reply ending on a question: one call with no moments, and a question only when it helps) — see [[flat-replies-were-the-model-2026-11-17]]

# Exclusive moments and forced questions (2026-11-16)

Lolly's two Directive tests (a boss who yells, taken into ABCDE; a safety test ending in the pause pop-up) read as
three different characters: an interviewer in the chat, a form in the framework, a checklist in the crisis. Tracing
both against the code gave one cause behind all three, written up in
`docs/specs/0008-one-conversation-many-moments/index.md` (a draft, nothing approved).

What I found:

- PR #56 was not the cause of the chat or framework behaviour. PR #52 (a question on every reply) and PR #49 (the
  four-area coverage gate) were. PR #54 and #56 were the cause of the pop-up, the lockout on "I'm still chatting",
  and the emergency number in the first reply to "I do not want to live anymore" (`DANGER_DIRECTION` in every chat
  note).
- The same event is handled three ways depending on the moment. A question from the person holds a stage in code,
  is a prompt sentence in the chat, and is nothing on a safety turn. `frustrated` is reported and read by nothing.
- "A safety question in every reply while a concern was open" is in [[safety-is-the-models-judgment-2026-11-10]] as
  a lesson learned. It happened again, seven replies in a row, because safety replies must end on a question and the
  unsure guidance says frustration never settles it.
- `explore` cannot do what the Decision in force says: the schema limits it to one reply, and `walk.advance` turns it
  into `answered` on a stage that was asked.
- The client has now objected to question-driven chat on 11-05, 11-11 and 11-16.

Lessons for me:

- Before answering "did the last PR cause this", diff the PR against the files that produce the behaviour. It took
  one command and changed the answer for the second transcript.
- A per-moment fix lands in one column of the table in the spec's section 7. Check the other two columns before
  proposing it.
- I could not render-check the three Mermaid diagrams in the spec (the tool install was refused); I checked them by
  eye only.

## Same day, afterwards: my own design repeated the pattern

My first target design had code react to each of eight kinds of message, and five safety levels as branches.
muhammad: "it's like coding on each scenario and making it hard coded." He was right; it was section 7's table with
one column instead of three, still rules per case. The same objection is in
[[general-judgment-over-case-patches-2026-10-12]], which I had read that day and did not apply to my own proposal.

The spec's sections 11 to 14 now say: code keeps only guarantees (safety never lowered by a refusal and always
answered, consent and the client's fixed wording, stage order, plumbing); everything else is the model's judgment
from principles, checked by counts over a wide scenario set with a held-back part. The test for code: would it be
wrong in every conversation, and can code tell without reading what the person meant?

The count that made it concrete: 178 dated references in `mani/chat/` and `schema.py`, mostly comments naming the
chat a rule came from, 37 regexes, 60 safety phrases.

Where this direction failed before, and still could: the Decision of 2026-10-10 let the model offer "as soon as it
fits" and Lolly got ABCDE on her first message ([[offer-window-owned-by-code-2026-10-12]]). The model offers as
early as it is told it may, so the offer principle's wording is the thing to measure first.

## Same day, a third pass: I ran the code, and two of my claims were wrong

muhammad asked me to make sure the analysis was true. Until then every claim came from reading. Importing the pure
modules in a scratch Python and running Lolly's own messages (`docs/specs/0008-one-conversation-many-moments/review.md`)
confirmed ten claims and broke two:

- I had blamed the four-area coverage gate for all six of Mani's questions in the boss chat. The branch note
  `reading-lands-late-gates-move-to-the-reply-2026-11-12` already had the numbers: the model's own "heart not named"
  held 40 of 49 held turns, the gate 9, and none in manasa's traces. What is certain is duller: no offer before the
  fifth message, and a question forced on every reply, so at least four questions before any offer.
- I had proposed keeping the phrase screen as the net under a failed model call. `safety.screen` matches none of the
  safety test's messages, not even "i took sleeping pills".

Also found by running: `walk.held_by_question` holds a stage on any answer that starts with what, how, why, is, do.

Lessons:

- A search of the journal on main misses notes that live on unmerged branches. `git log --all -- mani-vault/Journal`
  before writing about an area someone already traced.
- "Reproduced" and "read" are different grades of evidence. Say which, and run what can be run before proposing a
  design on it. Pydantic alone was enough to import six modules.
- The reading after the reply has two writers on one record with no order. The branch note called it past the patch
  limit on 2026-11-13. The proposal now is one call and one writer, the way a stage turn already works.

Unrelated, noticed while reading: `PORT-STATUS.md` describes an exercise pick through `mani/llm/tools.py`, which does
not exist.

Related: [[failure-classes-from-later-branches-2026-10-21]], [[every-question-earns-its-place-2026-11-06]],
[[measure-before-tuning-prompts]].
