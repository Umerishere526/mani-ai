---
type: journal
date: 2026-10-14
tags: [journal, abcde, stages, voice, lessons]
---

# A missing stage is asked about their situation (2026-10-14)

muhammad's Directive run (thread 425f6a55). A had just been confirmed as "your manager gives you work
outside your responsibilities". Then Mani sent "B is for Belief. What did you start telling yourself
about what was happening?". The person answered "regarding?". Only Mani's follow-up was about their
situation: "I mean what you told yourself when your manager gave you work outside your
responsibilities…".

## Cause

It was a design decision. Since 2026-10-12 code sent the client's `ask` word for word for a stage
reached as missing and threw the model's text away. The reason, from
[[plain-questions-not-rewritten-2026-10-12]], was that free rewording at low effort produced stacked
lines. That failure came from five prompt lines ordering the model to reword every question, and
those lines were cut the same day. The premise was gone, but the code kept the stricter rule.

The client's own document adapts the question in its final requirement 2: "D is for Dispute. What makes
you believe your manager is planning to replace you, and what makes you question it?".

## What changed

- **Missing stages.** B to E reached as missing, and A when no feeling word is known, now send Mani's
  own question: the client's `ask` as written, with what it refers to in their words. When the text
  asks nothing, the client's `ask` is sent instead, logged "missing asks nothing".
- **A with a feeling word.** A keeps the client's Situation 3 line with the feeling word. It is already
  about them.
- **Unjudged stages.** A stage reached unjudged (see [[reach-judged-in-its-own-field-2026-10-14]]) keeps
  the client's line, because the text was not written for it.
- **No example sentence.** muhammad chose context only for the first question. Examples of the kind of
  thought stay on the follow-up, when they are unsure.

Planned and reviewed with Fable 5.1 (option 3 of three: the model writes it). It was preferred over a
model-filled slot in the client's line, whose grammar would break inside "about …", and over a slot
filled by code from the previous stage's words.

## Lessons

- When a past failure justified a rule, check whether its cause is still there before keeping the
  rule. Here the cause was cut the same day, and the stricter rule outlived it by two days.
- A bare client question can read as generic once it follows a confirmed, specific A. The client's own
  examples adapt it, so the client's words are the shape of the question, not always its exact text.

To watch in the first live run (muhammad's yes): stacked or literary questions coming back, and how often
"missing asks nothing" fires.
