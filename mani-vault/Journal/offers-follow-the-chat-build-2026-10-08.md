---
type: journal
date: 2026-10-08
tags: [journal, frameworks, offers, router, vetoes, tests]
---

# Offers follow the chat (spec 0011)

Built in one run, on top of spec 0010's staged tracer (muhammad chose that over committing 0010 first). The phrase router is gone: `router.py` became `vetoes.py` with `ruled_out`, `Registry.vetoes` reads `never_offer_when_said` once per load, `[ctx]` has no `framework_shortlist`, `cooldown_passed` has no urgent branch, the `tuning` row has no `router` block, and five of the six framework files have no `activation` key.

## Counts (AC-9)

- `pytest` before: 755 passed (the 0010 tracer note). After: 666 passed, 4 skipped (the four JWKS symmetric token auth tests, as before). 139 integration tests ran, so none were skipped.
- The 89 fewer: `test_router.py` deleted whole (30 test functions, many parametrized), its veto test moved to `test_vetoes.py`; the shortlist, closest fit and urgency tests in `test_turn.py` and `test_chat_context.py` rewritten into one plain sentence test and one first message test; the distinction cases gone from `test_seed_frameworks.py`, `test_techniques.py` and `test_config_rows.py`.
- Database: local Supabase on 54342. Reseeded after muhammad accepted the wording, so it now holds spec 0010's tracer prompts and Stages lines as well (the reseed that note was waiting on).

## Gotchas worth keeping

- **Seed before code.** `Tuning` refuses unknown keys, so code without `router` against a row that still has it fails on its first load. Locally I reseeded between the code change and the full run; the integration tests were green only after.
- **The veto list is validated in `Registry`, not only in the seed.** A portal edit skips the seed, and a blank phrase would rule a framework out by a space. The error names the framework id and never a phrase.
- **`git mv` and `git rm` stage.** Everything else of mine is unstaged on top of 0010's staged work, but the rename of `router.py` and the deletion of `test_router.py` went into the index. A plain `git diff` therefore does not show them.

## Noticed, not fixed

- `database-schema-reference.md` still says `admin.frameworks.body` is "written, never read". The Framework Index reads it every turn. The sentence was already wrong before this spec.
- `PORT-STATUS.md` "Status, 2026-10-01" still quotes 641 passed.
- Whether the model offers the right set on plain phrasing is unmeasured by design. Feature 11 measures it, with muhammad's yes per real run.

Related: [[stage-ledger-tracer-build-2026-10-08]], [[stage-ledger-design-2026-10-08]]
