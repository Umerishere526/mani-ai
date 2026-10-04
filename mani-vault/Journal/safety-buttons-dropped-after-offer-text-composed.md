---
type: journal
date: 2026-10-04
tags: [journal, bug, safety, offers]
---

# Offer text can reach a person with no button, on a safety turn

Found by the cross check of [[0002-mani-speaks-naturally]] (spec in `docs/specs/`). Not fixed there, because it is not part of
the Natural Mani rewrite.

When the safety screen or the model flags a concern, `orchestrator.py` (around lines 616 to 629) drops the technique buttons.
By then `repairs.apply` has already composed the offer text (the framework description and "Would you like to try it?").
So on a panic turn the person can read the question with nothing to tap. The baseline transcript in
`backend/.eval/client_style/baseline/` shows it. `repairs.py` around lines 542 to 545 already strips orphaned offer text when a
button is dropped inside `apply`; the same strip is missing at the orchestrator's later drop.

Why it matters beyond looks: the spec's `answering` line quotes Mani's last question, so a dead offer question must not be
quoted. The spec skips a question that equals a permission question when no offer is live.

Not yet scoped as a feature. Fix when next in `orchestrator.py` for safety work (rows 9 to 11), or sooner if muhammad asks.

Related: the same cross check found a bare "yes" to Mani's own safety question passes the screen unread. That is scope row 36.
