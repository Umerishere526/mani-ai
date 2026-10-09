---
type: journal
date: 2026-10-08
tags: [journal, offers, client, replies, build]
---

# Building spec 0015: the offer and Tell Me More per framework and style

Spec: `docs/specs/0015-offer-per-framework-style/`. Scope feature 17. Design note: [[offer-per-style-design-2026-10-08]].

## Counts

- Before: 670 passed, 4 skipped. After the reseed: 684 passed, 4 skipped (14 new tests).
- The 4 skips are `tests/unit/test_endpoint_auth.py`, which cannot mint a symmetric token on a JWKS project. The integration tests ran.

## The real run (AC-7), measured once, after muhammad's yes

`python scripts/eval_replies.py --scenario abcde_told_more --style reflective --verbose`, 5 chat calls, 0 findings.

- The offer at message 2 and Tell Me More were the seeded Reflective text, exactly.
- After Try It: "Okay. Let's look at it together, one step at a time. You said your manager questioned two recommendations, and you started thinking you're bad at your job. How has that thought affected how you feel or what you've done since?" No steps listed again, no second ask for the event. The ledger went straight to `consequences`. **Passed.**
- Not this spec's to judge: no letter was named ("C is for Consequences"), which feature 20's client doc wants. That needs feature 20's own real run.

## Things worth remembering

- **The client's .docx puts a non breaking space (U+00A0) after each step name** ("A: Activating Event: What happened"). A plain string compare against `word/document.xml` flags every step line as different. Normalise ` ` before comparing; the seeded text uses a plain space.
- The "keys are exactly the three styles" check now lives once, in `_keyed_by_every_style` in `mani/prompts/replies.py`, used by `style_labels`, `openers` and each `by_framework` entry.
- No system `python` on this Mac: heredoc scripts need `./.venv/bin/python`.

Related: [[abcde-client-doc-2026-10-08]], [[offer-in-client-words-build-2026-10-08]]
