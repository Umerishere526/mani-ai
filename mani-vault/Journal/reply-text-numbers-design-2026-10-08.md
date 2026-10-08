---
type: journal
date: 2026-10-08
tags: [journal, prompts, config, gotcha, preferences]
---

# Designing spec 0008: reply text and numbers out of Python

## Facts the first draft got wrong (caught by the cross check)

- `ErrorCategory.INVALID_REQUEST` maps to **422**, not 400 (`mani/errors.py`). The admin write refusals in `config_tables._refuse` use it.
- `scripts/seed.py` upserts every prompt row `on conflict (name) do update`, with no `prompt_versions` snapshot. A reseed silently overwrites any portal edit. The files in `content/` are the source of truth; a portal edit is a trial until the next seed.
- A number can have a second home outside the turn: `summarize.reconcile_due(threshold=20)` (the cron route `/internal/cron/fold-summaries`) copies `CONTEXT_WINDOW`. When moving a constant, grep for its value too, not only its name.
- `cache.load()` only re-raises `ServiceError`; any other exception from `_read` keeps the old snapshot and logs. A parser that raises `ValueError` there is swallowed, not loud.
- `parse_reply_shapes` lives in `cache.py`, which imports `config_tables`. A check that `config_tables` imports cannot import from `cache.py` without a cycle.
- `Config` is a frozen dataclass with a defaulted last field; new required fields go before it, and tests build `Config(...)` directly.
- `clarification_used` only ever saw the 20 message window, so "the line is asked once per conversation" was never strictly true.
- `REMOVED` in `test_prompts_name_what_exists.py` matches substrings: removing `after_framework_question` while adding `after_framework_questions` trips it.

## muhammad's calls in this design

- Ending labels stay for feature 7, all crisis text for feature 10, even though the scope row listed them for feature 9.
- Delete the `their_last` phrase lists **and** their rules, let the model judge; tests only, no real run.
- Two commits on the same branch (pure moves, then behaviour), not two PRs.
- Refuse bad content at every write, no defaults in code (unlike spec 0007's soft failures).

Related: [[client-lines-the-code-matches-exactly]], [[closed-sets-live-in-more-places-than-the-code]], [[model-text-out-of-python-build-2026-10-07]]
