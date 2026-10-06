# Verify: how Mani chooses and steers toward a framework · spec 0005 · updated 2026-10-05
_Steps derived from spec 0005 acceptance criteria. `/check verify` runs these; `/test` locks the durable ones. Run commands from `backend/` with the venv active. Paid steps (marked) need muhammad's yes first._

## Commands
- [ ] `pytest -q` → all pass, only the 4 known skips (integration ran, not all skipped) → AC-13
- [ ] `pytest -q tests/unit/test_schema.py` → `facts` before `text`; no `heading_toward` or `offer_fit`; a malformed fact is dropped and the reply still reads → AC-1
- [ ] `pytest -q tests/unit/test_framework_fit.py -k "quote or fact or panic or older"` → a fact counts only in the person's own words, within one message, two words at least; the two "right now" facts only from their last two messages; unknown ids noted → AC-2
- [ ] `pytest -q tests/unit/test_framework_content.py -k "fit or panic"` → every framework has `fits_when` with known facts only; every DBT STOP stage has a `panic` branch with no action words; the panic offer waits until Mani has asked what is happening → AC-3, AC-11
- [ ] `pytest -q tests/unit/test_framework_fit.py` → each framework fits on its own facts; the six tie rules and the three conflict cases (including the lost wallet facts going to Structured Problem Solving); leading framework and missing fact; an excluded framework is never picked → AC-4, AC-5
- [ ] `pytest -q tests/unit/test_router.py` → the imminent action phrases are urgent, an urge or idiom is not, only the last two messages count; vetoes match whole words → AC-6
- [ ] `pytest -q tests/integration/test_turn.py -k imminent` → an urgent first message carries DBT STOP's `offer_*` lines and no `framework_shortlist` → AC-6
- [ ] `pytest -q tests/unit/test_redraft.py` → each of the six reasons in order, the manager chat at message 2 held as too early, the panic redirect carrying STOP's panic wording → AC-7
- [ ] `pytest -q tests/integration/test_turn.py -k "still_wrong or manager_chat or panic_is_redrafted or nothing_said or only_point_to or full_fit_not_offered"` → a twice wrong offer is never stored; the manager chat goes to ABCDE; panic goes to DBT STOP; chat 1 has no offer and no `closest_fit` line at message 4; an event alone is never offered; a full fit unoffered by message 4 is asked for → AC-8, AC-14, AC-16
- [ ] `pytest -q tests/unit/test_chat_context.py -k "due or owed or keep_chatting or come_back"` → `offer_due` from message 4, never after a decline, never in `[ctx]` → AC-16
- [ ] `pytest -q tests/unit/test_composer.py -k nearest` → no prompt and no generated Framework Index text says nearest, closest fit or that an offer is due → AC-16
- [ ] `grep -rnwiE "closest|closest_fit_ok|closest_fit_due|CLOSEST_FIT_AFTER|CLOSEST_FIT_LABEL|COOLDOWN_AFTER_DECLINE|cooldown_for|offer_kind" mani scripts content` (from `backend/`) → nothing (whole words, so `CLEAR_COOLDOWN_AFTER_DECLINE` stays) → AC-16
- [ ] `pytest -q tests/unit/test_composer.py -k "fit or field"` → the Framework Index lists every framework's facts in plain words; no prompt file names a removed field → AC-10
- [ ] `grep -rn "shortlist\|is_confident\|strong_signals\|ROUTER_MIN" mani content scripts` → nothing (only negative assertions in tests) → AC-12

## Value sourcing (one per row of the spec's table)
- [ ] Kept facts: a fact quoting words only Mani said, or split across two of their messages, is dropped → `test_a_fact_quoted_only_from_mani_is_dropped`, `test_a_quote_spanning_two_messages_is_dropped` → AC-2
- [ ] Fact turn: on a tapped button, a running framework, an accepted offer or a safety concern, facts are ignored (no `facts ... pick` log line for that turn; run any tapped offer integration test with `-o log_cli=true`) → AC-2
- [ ] Pick: the same facts with ABCDE excluded pick Thought Reframe → `test_an_excluded_framework_is_never_picked` → AC-5
- [ ] Leading and missing fact: `event` alone leads to ABCDE missing `meaning`, and the redraft text says "what they took that event to mean" → AC-5, AC-7
- [ ] Offered framework: `redraft.offered` reads the offer button's id; an unknown id is never treated as an offer → AC-7
- [ ] Offer guidance: DBT STOP's redraft uses the panic branch when `overwhelmed_now` is present without `about_to_act`, the action branch otherwise → `test_3_a_panicked_person...`, `test_3_about_to_act_keeps_stops_action_wording` → AC-7, AC-11
- [ ] Offer timing: with `clear_ok` false nothing is offered, even with no pick (reason 2 before reason 5); a framework they only point to is never offered or asked for → `test_2_an_offer_during_a_cooldown...`, `test_5_...`, `test_6_a_framework_they_only_point_to...` → AC-7, AC-16
- [ ] Repairs: `cooldown_passed` is true only when `offers_the_pick`, the pick is allowed now and not ruled out → `test_only_the_pick_may_be_offered`, `test_a_framework_they_only_point_to_is_never_offered` → AC-8, AC-16
- [ ] Urgency: an imminent action phrase counts as `about_to_act` and DBT STOP skips the wait → AC-6

## Real model (paid, ask first)
- [ ] `python scripts/eval_replies.py --scenario <name> --style supportive --verbose` for `stress_nothing_named_yet`, `panic_attack_grounding`, `manager_embarrassed_me`, `grief_dog_steering` → stress: no offer by message 4 and asks what happened; panic: DBT STOP; manager: ABCDE; grief: an offer, never Behavioral Activation → AC-15. Last measured 2026-10-05: panic, manager and grief as expected; stress 1 of 3 (open, see the journal note `framework-fit-from-facts-first-runs-2026-10-05`).
- [ ] The re-check after full fits only: `stress_nothing_named_yet` three times (three separate invocations), `grief_dog_steering` and `deadlines_steering` once, each `--style supportive --verbose` → stress: no offer by message 4 in each run; grief: an offer, never Behavioral Activation; deadlines: Structured Problem Solving. Read the `[choice]` lines (fact ids, pick, redraft reasons) to tell a loosely marked fact from a push → AC-17

## Acceptance-criteria coverage
- AC-1 schema step · AC-2 quote steps and fact turn · AC-3 content step · AC-4 fit step · AC-5 fit step, pick, leading · AC-6 router and imminent steps, urgency · AC-7 redraft step, offer guidance · AC-8 still wrong step · AC-9 repairs (replaced by AC-16) · AC-10 composer step · AC-11 content and offer guidance steps · AC-12 grep step · AC-13 full suite · AC-14 integration chats · AC-15 paid runs · AC-16 offer due, nearest and grep steps, repairs · AC-17 re-check
