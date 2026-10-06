# Verify: A person who stays stuck while Mani is understanding is offered ABCDE · spec 0009 · updated 2026-10-05
_Steps derived from spec 0009 acceptance criteria. `/check verify` runs these; `/test` locks the durable ones._

Run every command from `backend/` with the venv active, local Supabase running, and `python scripts/seed.py` run after any content edit.

## Commands
- [ ] `pytest tests/unit/test_framework_fit.py -k stuck` → `stuck` dropped with "dropped stuck before the check" when Mani never asked it, kept when Mani asked "are you feeling STUCK" in any case → AC-1, AC-2
- [ ] `pytest tests/unit/test_framework_fit.py -k "stuck or full_fit"` → `{stuck}` picks ABCDE with `stuck_route` true and no `leading`; `{stuck, painful_thought}` picks Thought Reframe; `{stuck, about_to_act}` and `{stuck, overwhelmed_now}` pick DBT STOP; `{event, meaning, stuck}` picks ABCDE with `stuck_route` false; ABCDE excluded leads nowhere → AC-3
- [ ] `pytest tests/unit/test_composer.py -k stuck_set` → ABCDE's fit line ends "(only when no other set fits)" → AC-3
- [ ] `pytest tests/unit/test_stuck_route.py` → candidate only on the turn right after the check, not on their second message, not while a framework runs, not when ruled out, yes after a decline; `offer_when_stuck` line carries "only if they answered yes"; tapped and typed starts ask "What goes through your mind when you feel this?" with no `already_told` and no `if_earlier_missing`; with an event known the start is as before; pain does not hold a due stuck route offer but holds others; "painful" alone is not pain → AC-4, AC-6, AC-7, AC-8
- [ ] `pytest tests/integration/test_turn.py -k stuck_check` → check, "yes", ABCDE offered and kept, "Try it" answered with the stuck line, stage stored as `belief`, four model calls → AC-2, AC-4, AC-7, AC-8
- [ ] `pytest tests/evals/test_base_prompt.py` → body within 118 lines, "A yes may bring an offer" and "only a `stuck` fit may be offered" present → AC-5, AC-6, AC-11
- [ ] `pytest tests/unit/test_eval_stage_findings.py -k expect` → a different or missing first offer is a `journey` finding → AC-9
- [ ] `pytest` → 1536 passed, 4 skipped (the JWKS auth tests), no warnings → AC-11

## Value sourcing
- [ ] The check is read from Mani's messages only: a `stuck` fact quoting the person's words with "Are you feeling stuck?" only in a *person's* message is dropped (vary who said it) → AC-2
- [ ] The check must be in the 20 message window: a thread where the check is older than the window drops `stuck` (accepted limitation) → AC-2
- [ ] The stuck route is read from `known` at the start: with `known` `{stuck}` the start is passed over, with `{stuck, event}` it says back the event (vary `event`) → AC-7
- [ ] The candidate gate reads the thread's message count: at message count 5 (their second message) no `offer_when_stuck`, at 7 it appears → AC-4
- [ ] Seeded content: `docker exec -i supabase_db_mani psql -U postgres -tAc "select activation->'fits_when' from admin.frameworks where id='abcde'"` → `[["event", "meaning"], ["stuck"]]` → AC-3

## Real model (paid: muhammad says yes first, check credit with get-credits)
- [ ] `python scripts/eval_replies.py --scenario depressed_alone --verbose` and `--scenario stuck_body_pain --verbose`, each style (6 conversations, plus spec 0008's `idiot_concert_direct` ×3 for nine) → first offer ABCDE, no `journey` finding, after "Are you feeling stuck?" in at least two of three styles; when accepted, the first question is "What goes through your mind when you feel this?" → AC-10
- [ ] `idiot_concert_direct` → still offered ABCDE through `event, meaning`, the start says back the event (no stuck route) → AC-10
- [ ] muhammad reads the offers and the first ABCDE replies; the figures go in the journal → AC-10

## Acceptance-criteria coverage
- AC-1: fit tests · AC-2: fit tests, integration, value sourcing · AC-3: fit and composer tests, seeded row · AC-4: stuck route tests, integration · AC-5: base prompt test · AC-6: stuck route tests, base prompt test · AC-7: stuck route tests, integration · AC-8: all the unit and integration steps · AC-9: expect_offer test · AC-10: the paid run · AC-11: base prompt test, full suite
