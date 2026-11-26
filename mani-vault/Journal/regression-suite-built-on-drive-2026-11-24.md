---
type: journal
date: 2026-11-24
tags: [journal, evals, regression, testing]
summary: "The conversation regression suite (evals/regress.py) reuses drive.py's real-stack conversations; what it checks deterministically, what it leaves to the judge, and what blocked a free end-to-end run."
failed:
  - "Tried running the whole suite against scripts/fake_openrouter.py for a free check; failed because the fake only streams, so the model-played person and the judge (non-streaming calls through run_eval.structured) get a 400. Only script-only scenarios with --no-judge run against it."
  - "First version let one scenario's exception end the asyncio.gather and lose every other scenario; same failure class as [[one-failed-call-lost-a-whole-scenario-run-2026-11-16]]. Each scenario now fails on its own (play.error_record)."
---
2026-11-24

Built on `evals/drive.py` rather than a second harness: `converse` gained a `script` (sent in order, a button's label
taps it), `person` (reuse a person, for the isolation scenario) and `until` (stop at the offer, for the lead-in
buttons). Decision recorded in `backend/PORT-STATUS.md` (regression suite entry).

What surprised me:
- The local database's `mani` prompt row was still `minimax/minimax-m3.1-flash` after PR #61 changed `mani.md` to
  DeepSeek: nothing reseeds local. muhammad's manual Test 1 that day ran on MiniMax. Every run report now names the
  chat model(s) from `admin.llm_calls`, so a run can be tied to its model.
- Deterministic checks read the trace and buttons, not prose, wherever possible: offer turn = first reply carrying
  `LEAD_IN_LABELS`; stages from `trace.stage` against the active registry; safety from `trace.safety.level`. Prose
  checks (forbidden words, banned phrases, one question, repeated opener, invented he/she) come straight from the
  client's Behavioral Framework, Safety Guardrails and Pacing Rules, which are not yet in `docs/client`.
- The pronoun check exists because Test 1 had Mani say "him" when the person only ever said "they".

Unit tests for the checks: `tests/unit/test_regression_checks.py`. The unit suite runs without `.env`, so CI needs no
secrets for it.
