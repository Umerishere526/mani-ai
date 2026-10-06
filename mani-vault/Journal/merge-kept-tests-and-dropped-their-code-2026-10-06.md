---
date: 2026-10-06
tags: [journal, merge, backend, testing]
---

# A merge kept one branch's tests and the other's code

`cedab6d` merged `fix/improvement-mani` into `dummy-merge-branch`. Both branches had
rewritten the same turn code in opposite directions, and the merge took one side's
`orchestrator.py` while keeping the other side's tests, migrations and content. Nothing
conflicted, so it looked clean, and `main` shipped to prod with three failing checks.

What was lost without a conflict:

- The semantic router's wiring. `semantic_router.py`, `offer.py`, `framework_vectors.json`
  and their unit tests all survived; the ~70 lines in `orchestrator.py` that called them did
  not. `SEMANTIC_ROUTER` stayed in `config.py` and nothing read it, so setting it did
  nothing. The unit tests still passed, because they test the module, not its use.
- `phase_since`: migration 017 applied, the integration test kept, the insert and the model
  field gone.
- `offer_unnamed`: a validator deleted while its test stayed.

## What to actually do about it

**A merge between two branches that touched the same module is not done when it has no
conflicts.** Run the suite, and treat each failure as a question about what was dropped
rather than a test to update.

**A flag nothing reads is invisible.** Both `grep -rn "settings\.<flag>"` returning one hit
(its own definition) and the suite passing are consistent with the feature being gone. If a
flag is worth having, something should fail when its wiring disappears - the integration
tests from `297fc7a` would have.

**The suite was reading `SEMANTIC_ROUTER` from `.env`.** So the tests tested whatever the
machine was set to, and on a machine with the flag on, every framework test made a real
paid embedding call. `tests/conftest.py` now pins it off and the router's own tests turn it
on themselves. Worth checking for other per-deployment flags read the same way.

See [[duplicate-migration-versions-after-merge-2026-10-06]], the same merge's other damage.
