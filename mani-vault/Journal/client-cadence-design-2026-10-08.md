---
type: journal
date: 2026-10-08
tags: [journal, prompts, styles, offers, client, design]
---

# Designing spec 0012: Mani speaks and asks as the client wrote

Spec: `docs/specs/0012-mani-speaks-as-client-wrote/`. Scope feature 14.

## What the client doc contradicted in our own rules

Found by reading `mani_base.md` against the October 8 style docx line by line. These were not in the scope row and only showed up on a side by side read:

- "Never name a feeling… not as a fact, a guess or a question" forbids the client's own check lines ("Does it feel like your body is activated…?"). The client forbids new emotions, motives and meanings, but checks interpretations as questions.
- "Never ask them to sort, label or pick what is worst" forbids "What feels strongest right now?", which the client asks in several scenarios.
- `question_focus` in `context.py` told Supportive and Reflective to ask about feelings, never the facts. Every client Supportive and Reflective example asks about what happened.
- "built … so it could only be asked of this person right now" forbids the client's plain "Tell me what's going on."
- The client names the style Directive; our button said Direct.

Before cutting a client facing line, grep for it first: [[client-lines-the-code-matches-exactly]].

## muhammad's choices (2026-10-08)

- Feature 14 only. The offer's wording and buttons stay for feature 15, split line by line inside `offers`.
- Style lines: a hybrid, one line per style joined from the client's own phrases. He asked to see the options as drafts before choosing, because the abstract descriptions were confusing. **Show drafts, not descriptions, when asking about prompt wording.**
- Real runs capped at 2 to 3 conversations. He chose three, one per style.
- `clarification_lines` cut here, not left for the feature 16 audit.
- Eval scenarios left as they are, even though their turns predate the October 8 doc.

## Caught by the cross check, not by me

- `cache.load()` reloads as soon as the snapshot is stale, so after a reseed an old instance breaks within 300 seconds. Spec 0011 also claimed old instances keep their snapshot until new code lands, and that was wrong.
- Integration tests read the seeded rows, so a tracer that changes a strict row model cannot pass the whole `pytest` before the reseed.
- I wrote a rule ("leave the stages before the `|`") that my own Starts when drafts broke. Check a rule against its examples before writing it into an AC.
- The project tier is Beta (the scope `**Workflow:**` line). Read it before saying a feature has no tier.

Related: [[offer-late-root-cause-prompt-not-code-2026-10-08]], [[stage-ledger-design-2026-10-08]], [[measure-before-tuning-prompts]]
