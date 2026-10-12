---
type: journal
date: 2026-10-12
tags: [journal, prompts, reflecting, questions, lessons]
---

# Restating is not reflecting (2026-10-12)

Lolly's job decision feedback (`docs/client/messages/2026-10-12-job-decision-testing-feedback.md`):
in every style Mani handed the person's frustration and second-guessing back to them, and asked
what felt most uncertain before knowing what the decision was. Her rule: mirroring confirms or
shows understanding when needed, never just restates their words or emotions.

## Cause

- The reasoning read the feeling first ("Their feeling, in their words. What is under it..."), so
  the reply was built on the feeling and dug under it before the situation was known.
- `reflecting` taught how to say a feeling back ("Their own words for the core of it are fine"),
  not when not to.
- It quoted the banned shapes word for word. Directive's reply, "The frustration of questioning
  yourself again ... is clear", is almost the ban's own example, "The frustration of X is clear". A
  quoted bad example is a template for a low-effort model.
- "Say 'hard' or 'worries you most'" in `voice` primed "most" questions ("most unsure", "most
  uncertain").
- Our bans on two-part questions and "what would it mean" forbade the two questions she asked for.
  Cut, with muhammad's yes.

All fixed by cutting: `mani_base.md` from 2640 to about 2480 words, `response_format.md` from 1023 to
about 1000.

## Live after the cut (3 runs x 3 styles, window enforced)

- The first reply asked what the decision is in every conversation. Directive: "What decision are
  you trying to make?"
- Directive no longer restates. Its second reply asked "What would making the wrong choice mean to
  you?" once, and narrowed to the fear once ("What are you worried might happen if you choose
  wrong?").
- Supportive restated on the second reply in 2 of 3 runs ("Both options have good reasons behind
  them, and the fear of choosing wrong keeps pulling you back into doubt").
- Reflective restated in both replies in all 3 runs ("You get close to deciding, then start
  questioning yourself again").
- Every first offer came at the third message.

## Still open, and why

What is left restates in the styles whose examples restate. The client's Reflective examples in
`style_reflective.md` open on their words ("Your chest feels tight and your thoughts are racing",
"You decide to stop, but somehow you find yourself still scrolling", "So 'one more' keeps turning
into more"). The model follows examples over rules (see [[measure-before-tuning-prompts]]). The
styles document (older) shows restating; this feedback (newer) rejects it. The newer one wins, so the
fix is in the examples, not another rule.

## Gotcha

`backend/.env` has `PAUSE_FIRST_OFFER_WINDOW=true` for watching the flow. `scenario_check.py` reads
it, so offers come on the first message and the questions are never measured. Run it with
`PAUSE_FIRST_OFFER_WINDOW=false` in the environment. The script also prints only the first line of a
reply, so a question after a line break is not shown.

See [[plain-questions-not-rewritten-2026-10-12]], [[styles-from-client-document-2026-10-12]].
