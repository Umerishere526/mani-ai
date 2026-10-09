---
type: journal
date: 2026-10-09
tags: [journal, prompts, questions, wording, design]
---

# Short plain questions: designed as spec 0017

Spec: `docs/specs/0017-mani-asks-short-plain-questions.md`. Scope feature 23.

## What muhammad asked for

Plain everyday words in every reply the model writes, not only questions: "No Dramatic, Fancy, Poetic or Mouthful phrases." The client's ABCDE C question is the bar, "or" and all: "How did that thought affect how you felt or what you did?" An "or" between two sides of one thing passes; two questions joined by "or" fail. A few words of acknowledgment before a question are fine; their story said back is not.

## The evidence

Local thread `cbc5c13d` (left out of meetings, Directive): "how does the possibility of losing your job sit with you now?", "With that distinction in mind", "what feels like a fair way to describe what you know right now?", "notice the support beneath them", and a restatement before most questions. The local database had only this one thread after the reset, so it is the whole before sample.

## The diagnosis

The model was obeying the sentences around the plain rule, not ignoring it. Three groups cause it:

- Story packing: "never bare", "in their words, about their situation", "built from what they have told you", "built on what they already told you", "specific to what they just said", and "in their words" on four Stages lines.
- Restating first: "say what you now understand, name what is still missing in fresh words".
- Synonym chasing: "never … the same thing the same way twice" and "do not reuse your own phrasing". These are where "sit with you" and "a fair way to describe" come from. `recent_openers` still varies openers, so cutting them costs little.

Cut all of them, and reword `reply` line 1 to "texts a friend" with the bans named. No line is added.

## Gotchas the cross check caught

- Spec 0010 line 163 said the Stages "in their words" stays. Cutting it reversed a decision in a sibling spec. Fixed in place, pointing to 0017.
- Spec 0016 AC-2 and AC-5 pin the exact text of `questions` line 2 and `framework_starting`. Any later prompt spec that rewords a line an earlier spec pinned "exactly" breaks that spec's verify, unless the earlier AC is edited in place to point at the later spec. Check for exact text pins before rewording a prompt line.
- Reasoning step 3 ("specific to what they just said") was a fourth packing phrase that none of the scope's named sentences covered. Search the `reasoning` steps, not only the rule sections.

## Next levers if the runs fail

The `mirror and ask` shape, the persona "forty years" line, the Reflective "reflects the meaning", and "gentle attention" in the body check. All are listed in 0017's Follow-up, and none was cut without evidence.

Related: [[stage-skip-and-short-questions-scope-2026-10-09]], [[understand-then-offer-design-2026-10-08]], [[stage-ledger-design-2026-10-08]]
