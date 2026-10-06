---
type: journal
date: 2026-10-06
apps: [backend]
tags: [journal, client-feedback, frameworks, somatic, prompts]
---

# Lolly's "left out of meetings" chat: half the objections land on her own documents' lines

Lolly reviewed a Direct Thought Reframe conversation on hosted (left out of meetings, "am I making too much of it") line by line. Traced each objection to its source before changing anything.

## Lines she rejects that are verbatim from her earlier documents

Newest client document wins ([[client-documents-win-over-our-rules-and-adrs]]), so these get rewritten, but tell her where they came from:

- "Okay. I'll guide you through it one step at a time." (style document, consent lines, all three styles).
- The Direct **Tell me more** text: "focused questions", "without rushing you", "You stay in control of what you want to share" (style document; also in `mani/chat/greeting.py`).
- "I have a structured approach that can help you ..." (style document). Our "never name the framework" rule was read from the style document's examples (spec 0010 rationale, MB-20). She now says naming it was asked for many times.
- "What do you notice in your body now?" then "Where do you feel that most right now?" (Thought Reframe spec section 22, and `somatic.md`). The duplication she calls out is the check-in and the practice's place question, both hers.
- "The chest is often where the body holds tension first. Let's do something brief together." (her Direct chest practice, word for word). Her reviewer said to compare against the approved wording before blaming us; it is the approved wording.

## Lines that are ours

- "Putting those together, what would you say is true about this?" (`thought_reframe.md` and `abcde.md` reframe asks). Her spec says "What would be a more balanced thought?". She wants Mani to synthesise here, per her 6 October email.
- "What else could be going on?" (ours; spec says "What else could be true?").
- "Skip this one" on every step (added 6 October, commit 2f617d4). She wants it gone: it makes the framework a form.
- The exercise pick (`orchestrator._offer_exercise`) runs on every retirement whatever `felt_after` says, so a "this was horrible" reply got Bee Breathing.
- "Then ask what they would like to do next" after the practice, whatever they report. She wants a negative signal to close with no question.

## Model behaviour, from the prompt

- Strengthening their facts: "dropped", "points to", "where you stand", "your role stayed the same". Fear of a possibility restated as evidence.
- Stiff, written paraphrase before every question, swapping their words for others ("overthinking" for "making too much of it"). Likely driven by the say back rule added in [[stuck-yes-dropped-and-say-back-lost-2026-10-06]] ("one short line of your own ... in fresh words") applied to every turn.
- Re-asking the thought the offer was built on, after accept.
- Bridge "notice how that settles in your body" presumes an effect.
