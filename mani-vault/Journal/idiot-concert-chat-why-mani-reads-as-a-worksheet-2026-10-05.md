---
type: journal
date: 2026-10-05
tags: [journal, conversation, frameworks, diagnosis]
---

# The "idiot / concert" chat: why Mani still reads like a worksheet

muhammad pasted a real Direct-style chat (ABCDE offered at message 4). He had to say "what?" three times and re-explain the event after "Try it". Counts for specs 0002 and 0003 all passed; the chat is still bad. See [[overfit-prompt-and-natural-mani-direction]] and [[measure-before-tuning-prompts]].

## Causes found in the repo (read, not run)

1. **The stage questions are the client's worksheet sentences, sent as written.** Every "what?" landed on one: "What did that come to mean for you?", "It affected everything. What changed first?" (the person never said "everything"), "What is a more balanced way to describe this?". Source: `backend/content/frameworks/abcde.md` `ask:` lines.
2. **Nothing the person already said is credited.** They gave the event (concert the day before an exam) and the belief ("i feel like i idiot") before "Try it". ADR-014 facts (`event`, `meaning`) are read only on turns where an offer could follow (`orchestrator.py`, `fact_turn`) and are never stored, so `framework_starting` asks the model to judge `ready_when` on its own, and ABCDE's `activate.ready_when` is strict. Result: "What happened?" again.
3. **The one hold (ADR-013) produced a worse question.** On "what?" the model improvised: a leading question offering the label "idiot", two questions in one reply.
4. **Understanding-phase replies still restate** ("You feel that going to the concert interfered with..."), the person says "yes", the turn is wasted. ADR-012 accepted a 42% restating rate and 14 "It sounds like" per 36 conversations; the offer in this chat opens with "It sounds like".
5. **Client wording that breaks the client's own rule:** `somatic.md` head line says "When anxiety sits in the head" to someone who never said anxiety.
6. **The checks measured the wrong thing.** Questions per reply, banned phrases, offer exchange, restating rate: all can pass while a person cannot follow the question. No check counts "what?" or re-explaining.

Not yet known: which model produced this chat. Causes 1 to 3 and 5 do not depend on the model.

## What was done (2026-10-05, same day) and how it read

[[ADR-015-what-the-person-said-before-accepting-is-not-asked-again]]. First replay found a hole the unit tests could not: a typed "yes" (most people do not tap) goes through the "typed past an offer" path, which my first version skipped, so "What happened?" was asked again. Fixed and covered by an integration test. Second replay: no re-asking, "what?" answered with a simple version, plain questions. Lesson: replay the real chat, with typing and tapping both, before saying a fix works. Still weak on the lite model: restating before questions, "It sounds like" surviving a redraft, and a closing question after "i don't know". Credits left about 2.6 dollars, so the stronger-model run (spec 0006) is muhammad's to fund.
