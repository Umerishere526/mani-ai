---
type: journal
date: 2026-10-05
tags: [journal, frameworks, stakeholder, specs, direct-style]
---

# Stakeholder feedback: "stop making me do the work" conflicts with the client's specs

A stakeholder read a Direct-style framework chat (presentation praised, they called it luck) and said Mani asks questions whose answers it already has, and should synthesise the insight itself ("The evidence suggests that luck is not the full explanation...").

## What the code does (both main and fix/improvement-mani)

- One stage per reply, none skipped: `techniques.validate_transition` refuses `SKIPPED_PHASES` and `clamp` corrects to the next stage. No signal anywhere says "they already reached it".
- Every stage's only output is an `ask:` question. The only non-question framework turn is the conclusion (ADR-016, this branch).
- `context._MOVE_ON_NOTE` / "never send it bare" mandates reflect-clause + question every framework turn: the exact pattern complained about.
- Only ABCDE `activate` and `belief` can be credited from earlier words (ADR-015, `answered_by`), and only on the start turn.
- On this branch 34 of 36 non-offer stage asks are identical across Direct/Supportive/Reflective (main 26 of 40); the Direct-only evidence branches from main ("What conclusion do the full facts support?") were removed. Direct is barely distinct inside a framework.

## The real conflict

The stakeholder's model reply breaks written client rules: `framework-thought-reframe.md` (user reaches their own conclusion; "Immediate contradiction ... reaches the conclusion for the user" is a must-avoid), `framework-abcde.md` (does not skip to a balanced belief, does not summarize), `six-frameworks-overview.md` ("MANI does not summarize"), and the boundaries "must not decide the belief is false" / "must not write a polished reframe". [[ADR-016-a-framework-ends-with-a-conclusion-and-the-body-check]] also rejected Mani writing the balanced thought. This needs a spec decision from the client before code, not a prompt tweak.

The colleague question in the chat is the model smuggling the conclusion into a rhetorical question because it is forbidden to state it; that already breaks the boundary on both branches.

## Which code produced it

muhammad confirmed: the stakeholders tested **main** on `gemini-3.1-flash-lite` at temperature 1. On main a stage holds as long as the model judges its `ready_when` unmet ("An answer is not enough"), with no limit in code, and ABCDE `examine` / Thought Reframe `facts` each demand three things before moving on. That is the most likely cause of "a conclusion that became clear several exchanges ago". This branch limits a stage to one hold, removes `closing`, and drops the redraft that forced a question before the offer. None of that is checked against a real model yet.

Related: [[idiot-concert-chat-why-mani-reads-as-a-worksheet-2026-10-05]], [[measure-before-tuning-prompts]].
