# Verify: Mani follows the client's documents · spec 0010 · updated 2026-10-06
_Steps derived from spec 0010 acceptance criteria. `/check verify` runs these; `/test` locks the durable ones._

## Commands
- [ ] `cd backend && .venv/bin/pytest -q` → 1330 passed, 4 skipped (the JWKS auth tests), no integration test skipped → AC-1 to AC-13
- [ ] `cd backend && ./scripts/test_db.sh` and `./scripts/test_db.sh --local` → both pass, including the five `framework_outcomes` checks → AC-8, AC-13
- [ ] `cd backend && .venv/bin/python scripts/seed.py`, then restart `fastapi dev main.py` → the new prompts and framework files are live before the live steps

## UI / manual (chat-tester, real model, one fresh conversation per style)
- [ ] First message → any offer is removed; `select decision from admin.llm_calls order by created_at desc limit 1` shows `"refused": "first_message"` → AC-3, AC-10
- [ ] By the second to fourth message → the offer is Mani's own sentence then the style's permission question (Direct "Would you like to try it with me?", Supportive "Would you like to try it together?", Reflective "Would you like to try it?"), with Yes, let's try it / Tell me more / I want to keep talking → AC-4
- [ ] Tap Tell me more → an explanation in the style, no question, two buttons (Yes, let's try it / I want to keep talking) → AC-4
- [ ] Tap I want to keep talking → no offer for the next four messages; the call log says `cooling_down` → AC-3
- [ ] Say "my dog died" → Behavioral Activation is never offered (`vetoed` if the model tries) → AC-3, AC-13
- [ ] Accept, then answer one step in a way that also answers the next → Mani asks a later step; `decision` shows `step_from` and `step_to` more than one step apart → AC-5
- [ ] Answer "I don't know" twice on one step → one more attempt, then a later step or the framework ends; `holds` goes 1 then 0 → AC-5
- [ ] Say "I want to stop" mid framework → a bridge line, then the client's check in word for word; `thread_technique_state.ending` is `stopped` → AC-6
- [ ] Give clear evidence for a conclusion → Mani states it plainly and moves on, no question leading to it → AC-2
- [ ] Reach the practice and say "a bit better but still tight" → Mani names what shifted in your words, then Chat More / Go to Library; `select * from public.framework_outcomes` shows one row with `mixed`, `chest`, the style and the ending → AC-7, AC-8
- [ ] Read each conversation against Lolly's nine points (naturalness, consistency across styles, listening versus interrogating, framework choice and introduction, step completion, pivoting, the move into the somatic check, the response after it, the close) and write the findings in a journal note → AC-14

## Value sourcing checks
- [ ] Tap a style, then send one message → the tap is not counted: the first message refusal still applies → offer refusal, first message
- [ ] Type a message without tapping a style → it is your first message; the next one may carry an offer → offer refusal, first message
- [ ] "I am about to send it" as the very first message → DBT STOP's offer may stand → urgent exemption
- [ ] A framework that reaches the check in from its last step with no `ending` reported → `ending` is `resolved`; from an earlier step → `pivoted` → `ending`
- [ ] A safety concern on the turn answering the practice → no `framework_outcomes` row → outcome row, concern
- [ ] An off list `felt_after` ("kind of okay") → no row, and the turn still succeeds → outcome row, normalisation

## Acceptance-criteria coverage
- AC-1 … `tests/evals/test_base_prompt.py` · AC-2 … synthesis live step, hard rules test · AC-3 … first message, decline, grief, urgent steps · AC-4 … offer and Tell me more steps · AC-5 … step skip and one more attempt steps · AC-6 … stop step, ending checks · AC-7 … practice step · AC-8 … outcome step, value checks, `test_db.sh` · AC-9 … pytest (`scripted.calls == 1` tests) · AC-10 … `decision` queries · AC-11 … pytest evals · AC-12 … records in the repo · AC-13 … pytest and `test_db.sh` · AC-14 … the nine points read
