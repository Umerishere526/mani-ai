# Verify: one model call, no redraft or repairs · spec 0006 · updated 2026-10-07
_Steps derived from spec 0006 acceptance criteria. `/check verify` runs these; `/test` locks the durable ones._

Run everything from `backend/` with `.venv` active, against local Supabase. The spec chose no real model runs, so
nothing here spends credit. One test, `test_an_offer_they_typed_past_is_flagged_then_closed`, fails until the
spec 0005 frameworks are reseeded (the database still holds the old ABCDE `offering` stage block); it is not
caused by this change.

## Commands
- [ ] `pytest` → every test passes except the one named above; the only skips are the four JWKS auth tests; `tests/integration/test_turn.py` ran, not skipped; no warning (`filterwarnings = error`) → AC-11
- [ ] `pytest tests/integration/test_turn.py -k "used_to_be_asked_for_again"` → five cases pass, each with `scripted.calls == 1` and the stored text equal to the scripted text → AC-1, AC-3, AC-6
- [ ] `pytest tests/unit/test_client.py -k "malformed or blip"` → a chat call with `retry_malformed=False` raises `LLM_UNAVAILABLE` after one attempt with one `schema_invalid` row, and a provider blip is still retried once → AC-2
- [ ] `grep -rnE "redraft|rewrite_notes|repairs|PERMISSION_QUESTIONS|CLOSEST_FIT_LABEL|_compose_offer|SCRIPT_LEAKAGE" backend/mani backend/content backend/scripts` → no match; `ls backend/mani/chat` shows `guards.py` and `ending.py` and neither `redraft.py` nor `repairs.py` → AC-1, AC-10
- [ ] `grep -rnE "FEELING_WORDS|SELF_JUDGMENTS|MAX_CAPSULE_WORDS" backend/mani` → no match; the same names are in `backend/tests/evals/vocabulary.py` → AC-10
- [ ] `grep -n "import" backend/mani/chat/ending.py` → no import from `guards`; `context.py` reads `reply_for` through `ending` → AC-10
- [ ] Mutation: change `if declined or retiring:` in `guards.py` to `if declined:`, run `pytest tests/integration/test_turn.py -k cannot_cancel_the_retirement` → fails; change it to `if retiring:` and run `-k keep_chatting` → fails; restore both → AC-4, AC-6
- [ ] Mutation: change `if handed_off:` before `updates.library_offered = True` in `orchestrator.py` to `if any(p.library for p in checked.prompts):`, run `-k does_not_silence` → fails; restore → AC-4
- [ ] `cd backend && python scripts/seed.py` is NOT run here until muhammad's review stop in spec 0005 is done; once it has been, rerun the whole `pytest` → no failure left, and the index in a composed prompt shows a `Description:` line under each framework heading → AC-8, AC-11
- [ ] Diff `PORT-STATUS.md`, "Decisions in force", first line → says a turn is one chat call, a malformed chat reply is not retried, and the exercise pick is the one scoped extra call; `grep -n "redraft" backend/PORT-STATUS.md` shows only the dated baseline measurement → AC-12

## UI / manual
- [ ] Send a chat message whose scripted or real reply breaks a prompt rule (a feeling word they never used, no question) → the stored and returned text is exactly what the model wrote, and `admin.llm_calls` shows one `chat` row for the turn → AC-1, AC-3
- [ ] Say "my dog died" then describe not being able to start anything, with no framework running → `[ctx]` (visible through `ScriptedModel.last_messages` in the integration test) carries `ruled_out: behavioral_activation`, no `offer: behavioral_activation`, and the shortlist does not name it → AC-7
- [ ] Type past an open offer ("Keep chatting" in words) with the model offering again → the thread's outcome is `declined`, the reply shows no offer buttons → AC-4, AC-6
- [ ] Reach a framework's last stage and tap Chat More with the model sending a technique button → the framework stays retired and the reply carries no buttons → AC-4
- [ ] A reply that does not parse → the app shows the retryable "Mani had trouble responding" error after one attempt; one `schema_invalid` row; nothing stored for the turn → AC-2

## Value sourcing
- [ ] Reply text: send a reply with surrounding whitespace and every old repair trigger (their name first, leaked `**Mani:**` text, a repeated clarification question) → stored text equals the model's `text` with only the ends trimmed → AC-3
- [ ] Buttons: send six buttons with a duplicate, a 6 word label and a feeling label outside an offer → all six stored, in order → AC-4
- [ ] Stored framework and stage: report `state` for an unknown framework, for a framework that is not the running one, and a stage two ahead → the first two are ignored, the third is clamped; each leaves one note naming the guard, never the value → AC-5
- [ ] `ruled_out` ids: vary the person's messages across the 20 message window (loss words inside, then outside the window) → the line appears while the words are inside the window and disappears when they scroll out; no line while a framework runs or on a safety concern → AC-7
- [ ] Offer candidate: with Behavioral Activation ruled out and another framework confident, the candidate is the other one; with none confident, no `offer:` line → AC-7
- [ ] `Description:` line: a framework with a summary shows it whitespace collapsed under its heading, one with an empty summary shows none → AC-8
- [ ] `library_offered`: set only after the two choices the orchestrator writes; a stray library button mid framework leaves `library_pending: yes` on the next turn → AC-4
- [ ] Guard notes: the log line is `checked reply on thread <id>: <notes>` and holds no text the person or the model wrote → AC-5

## Acceptance-criteria coverage
- AC-1 … covered by the `used_to_be_asked_for_again` cases and the grep step · AC-2 … the client unit tests and the unparseable reply step · AC-3 … the first Value sourcing step and `test_the_reply_goes_out_as_the_model_wrote_it...` · AC-4 … the guard unit tests, the two mutation steps and the state guard integration tests · AC-5 … the state Value sourcing step and the guard unit tests · AC-6 … the early offer and decline cases · AC-7 … the ruled_out steps and `test_what_they_said_rules_out_is_told_not_offered_by_the_router` · AC-8 … the `Description:` steps and the composer tests · AC-9 … `grep` for removed text, plus reading `mani_base.md` `offers` and `response_format.md` `ruled_out` · AC-10 … the grep and import steps · AC-11 … the full `pytest` step, blocked on the 0005 reseed · AC-12 … the PORT-STATUS and scope diff step.
