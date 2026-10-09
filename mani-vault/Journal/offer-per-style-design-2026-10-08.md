---
type: journal
date: 2026-10-08
tags: [journal, offers, client, design, replies]
---

# Designing spec 0015: the offer and Tell Me More per framework and style

Spec: `docs/specs/0015-offer-per-framework-style/`. Scope feature 17. Builds on spec 0013: [[offer-in-client-words-design-2026-10-08]].

## muhammad's choices (2026-10-08)

- Fixed text, generalised. The client's ABCDE offers are examples for one user ("your anxiety", "Feeling overwhelmed can make you question…"), so sent to everyone they would tell people feelings they never named. Direct and Supportive are generalised; Reflective and all three Tell Me More texts stay word for word.
- In `replies.md` under `offer.by_framework.<id>.<style>`, not in the framework files (that would need a migration). The seed refuses an id with no framework file.
- The other five keep the shared offer until their documents arrive. All three styles or none. Literal text, no fields.
- No prompt change for "Try It after Tell Me More doesn't repeat": the existing `styles.all` and `questions` lines cover it, proven by one Reflective real run after his yes.
- `by_framework` required, not defaulted to `{}`. So the deploy is seed, deploy and restart back to back, as for 0013.

## Things I would have got wrong without checking

- **Markdown collapses single line breaks.** The chat tester renders with `st.write`, so the five steps as plain lines would be one paragraph. They are `- ` lines after a blank line.
- **`resolve_style` already exists** (thread, then profile, then `tuning.offers.default_style`), so the offer uses the style the model is told, with no new source.

## Caught by the cross check, not by me

- `SmartPrompt` has `extra="ignore"`, so the `more` key never reaches `turn.prompts`. An eval token has to match the seeded label, not the key.
- `expect_framework` in a scenario demands a somatic phase, so a short scenario that ends inside the stages is always flagged.
- Two more integration tests assert ABCDE's shared offer text (lines 452 and 905 of `test_turn.py`), in threads with no style, so they get the default style's text.
- `_plain_fields` treats `{{` as an escaped literal, so a "no fields" check built on it lets doubled braces through to the person. Refuse the characters instead.
- `seed()` needs a database, so a check inside it is untestable; make it a pure function and call it from there.

## Noticed, not fixed

- `framework_abcde_stages` in `eval_conversations.yaml` still starts in `phase: activate`, stale since the ABCDE stage ids were renamed. Folded into spec 0015's AC-7.

Related: [[abcde-client-doc-2026-10-08]], [[offer-in-client-words-build-2026-10-08]], [[prompt-changes-cut-not-add]]
