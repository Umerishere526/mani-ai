---
type: journal
date: 2026-10-09
tags: [journal, router, frameworks, decisions]
---

# The phrase router is gone; the model chooses the framework

muhammad asked for it straight after a review of who decides the framework. The old `router.py`
scored phrase lists (`signals`, `strong_signals`) over the last four messages, reordered with
five hardcoded clinical rules and gated its own confidence. Literal phrase matching cannot read a
paraphrase, so the model was being handed a ranked guess that was silently wrong whenever the
person worded it differently, and nothing flagged it.

Now `mani/chat/eligibility.py` holds the two checks code owns: `urgent` (an imminent action, which
makes DBT STOP the candidate at once) and `vetoes` (`never_offer_when_said`). Everything else the
router did was a relevance judgement, which is the model's, from the Framework Index
(`central_indication`, `distinctions`, `contraindications`). Cooldown, already-offered and unknown
ids are still enforced by `redraft.py` and `repairs.py`.

## Not measured

No live conversations were run before or after (see [[measure-before-tuning-prompts]]: one run is
noise, three before and three after is a measurement). The 2026-10-08 result, 4 of 10 wrong SPS
offers falling to 0 once a weak guess stopped being the candidate, is the evidence this direction
is sound, not proof the new state is better. Run `scripts/scenario_check.py` three times and
compare offers before trusting it.

The `signals` and `strong_signals` lists were deleted from the six framework files, so the
database needs `python scripts/seed.py` (see [[reverting-code-does-not-revert-the-database]]).
