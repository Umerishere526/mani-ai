---
type: journal
date: 2026-10-08
tags: [journal, audit, cleanup, design, database]
---

# Designing spec 0014: removing what nothing reads or runs

Spec: `docs/specs/0014-audit-unused-code-files/`. Scope feature 16. Follow ups enrolled as features 18 (crisis events can be resolved) and 19 (memory folding runs on a schedule).

## muhammad's choices (2026-10-08)

- Coverage: backend, chat tester and docs. web and mobile are out: they run on placeholder data, so "unused" there mostly means "not wired yet".
- The two deferred column drops (`threads.vague_streak`, `admin.frameworks.stages`) folded into this spec.
- Grep evidence plus one vulture run, no standing dead code check (no CI to run one).
- The pool settings go and `pool.py`'s constants (2 and 10) stay, so the documented max of 5 was never what ran.
- All six unused grants revoked, plus the dead `messages_delete` policy.
- The build waits until 0012 and 0013 are committed.

## Lessons

- **"No code reads it" is not "unused".** I first recommended dropping `llm_calls.model`, `error_message` and the prompt editor columns, and muhammad agreed. Looking at the writers changed my mind. Each one is the only record of something a person reads by hand: which model served a call (the model comes from call rows and can change without a deploy), why a call failed, and who edited a prompt through the admin API. I corrected the recommendation and muhammad kept them. For an audit column, ask who opens it when something goes wrong, not which function reads it.
- **Search SQL test files too, not only migrations and Python.** The grant audit checked migrations, code and `test_grants.sql`, and missed that `tests/sql/test_rls.sql` deletes technique state as `mani_service`. That would have stopped `test_db.sh` once the grant was revoked. The cross check on another model caught it. Before revoking a grant, grep every `.sql` file for the statement it allows, not only for the grant.
- **Dropping a column means dropping it from the select lists too.** `FRAMEWORK_COLUMNS` selects `stages` and `activation_conditions` on every config load. A migration that drops them without that edit fails every turn. The first draft named the model field but not the column list.
- **Vulture on this codebase is mostly noise at 60.** It flags route handlers, Pydantic `model_config` and validators, response model fields and Streamlit `session_state` attributes. It found nothing the grep missed, and nothing at 90. That is why a standing check would need a whitelist.

Related: [[closed-sets-live-in-more-places-than-the-code]], [[reverting-code-does-not-revert-the-database]], [[duplicate-migration-versions-after-merge-2026-10-06]]
