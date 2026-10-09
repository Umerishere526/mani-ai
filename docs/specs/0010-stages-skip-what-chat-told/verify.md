# Verify: Stages skip what the chat already told · spec 0010 · updated 2026-10-09
_Steps derived from spec 0010 acceptance criteria. `/check verify` runs these; `/test` locks the durable ones. Task 2 (any stage skips once clear, the ledger readable) only; tasks 3 to 5 add theirs when built._

## Commands
Run from `backend/` with `.venv` active.

- [ ] `python scripts/seed.py` → seeds all six frameworks; `grep -c ' | ' content/frameworks/*.md` → 0 in every file → AC-10
- [ ] `pytest tests/unit/test_seed_frameworks.py` → a Stages line with a stray ` | ` is refused by the `phases` match, naming the stage that went missing → AC-10
- [ ] `pytest tests/unit/test_techniques.py -k out_of_order` → in each of the six shipped frameworks, every stage known but the second gives the second, then `closing` → AC-2, AC-10
- [ ] `grep -n "own words in this\|after the |" content/prompts/mani_base.md content/prompts/response_format.md` → nothing; `fields.state` reads "known when the conversation makes clear what it asks" → AC-11
- [ ] `pytest tests/unit/test_prompt_contract.py tests/unit/test_prompts_name_what_exists.py` → pass → AC-11
- [ ] `pytest tests/integration/test_turn.py -k call_row` → the call row holds `message_id`, `reported_stages` `{"activating_event": "known", "belief": "partial"}` (the off list `closing` entry dropped) and `stage` `belief` → AC-16, AC-17
- [ ] `pytest tests/integration/test_turn.py -k records_no_stages` → a turn with no framework running or offered leaves both null → AC-17
- [ ] `pytest tests/unit/test_link_call.py` → the retry tests pass and the stages reach `attach_message` → AC-17
- [ ] `./scripts/test_db.sh` and `./scripts/test_db.sh --local` → pass; `anon` and `authenticated` hold nothing on `admin.llm_calls` → AC-16
- [ ] `psql`: `select column_name from information_schema.columns where table_schema='admin' and table_name='llm_calls' and column_name in ('reported_stages','stage')` → both, nullable; constraint `llm_calls_reported_stages_is_object` present → AC-16

## Value sourcing
- [ ] `llm_calls.reported_stages` is `checked.stages`, not the raw reply: script a reply with an unknown id and a `Done` status → neither reaches the row → AC-17
- [ ] `llm_calls.stage` is `updates.technique.phase`: an offer turn records `offering`; a decline, a concern turn and a retiring turn record `stage` null while `reported_stages` may be set → AC-17
- [ ] The row updated is `Turn.llm_call_id`'s, in the same update that sets `message_id` → AC-17
- [ ] Chat tester caption order comes from `admin.frameworks.phases`, not jsonb key order: a ledger stored with keys out of order still shows in stage order, absent ids as `missing` → AC-18
- [ ] Chat tester recent calls order ids by the current framework's `phases`, any other ids after, sorted → AC-18

## UI / manual
Chat tester with `CHAT_TESTER_DEV_MODE=1` and "Show developer details" on. Real model turns: only with muhammad's yes.

- [ ] Run ABCDE past Try It → the caption shows `framework: abcde · stage: <phase>` then one `<stage> <status>` per stage in order, `(<n>)` only when turns are above 0 → AC-18
- [ ] Open "Recent calls" → each `chat` row with stages shows `reported: <stage> <status>, …  → <stage>`; a decline shows `→ –`; `summarize` rows show no stage line → AC-18
- [ ] The newest call may show no stages until the next rerun (linked after the reply goes out) → accepted, AC-18

## Acceptance-criteria coverage
- AC-2 (out of order, all six) · out_of_order command
- AC-10 · seed, grep, test_seed_frameworks, out_of_order
- AC-11 · grep, prompt contract tests
- AC-16 · migration columns, test_db.sh, call_row
- AC-17 · call_row, records_no_stages, test_link_call, value sourcing steps
- AC-18 · UI / manual steps and the two chat tester value sourcing steps

# Verify: task 3, counting and backstops · spec 0010 · updated 2026-10-09
_`stage_last_try` was dropped and the cap set to 3 (muhammad, 2026-10-09), so a stuck stage is asked at most 4 times with no prompt line._

## Commands
Run from `backend/` with `.venv` active.

- [ ] `python scripts/seed.py` → seeds; `select content from admin.prompts where name = 'tuning'` carries `stage_turn_cap: 3` under `windows`, with the comment that the stage is asked once more than the cap → AC-12
- [ ] `pytest tests/unit/test_ledger.py` → a partial stage at the cap is passed and noted; a known or passed stage keeps its status past it → AC-4
- [ ] `pytest tests/integration/test_turn.py -k cap_is_passed` → `stage_turn_cap` partial turns on `belief`: still `belief` one turn before, then `belief` passed with `turns` 3, phase `consequences`, note `passed by the cap: belief` → AC-4, AC-14
- [ ] `pytest tests/integration/test_turn.py -k no_stage_holds` → a model that reports no stage reaches `closing` after ledger stages × `stage_turn_cap` turns, and not one turn before → AC-14
- [ ] `pytest tests/integration/test_turn.py -k "naming_another or no_state"` → the stage is held and counted (`turns` 1), with the note → AC-4
- [ ] `pytest tests/integration/test_turn.py -k concern_turn_leaves` → phase and ledger counts unchanged on a concern turn → AC-8
- [ ] `pytest tests/integration/test_turn.py -k try_it_on_a_concern` → Try It on a concern turn stores `offering` and `{}`; the next turn lands on `dispute` with every count 0 → AC-8
- [ ] `pytest tests/integration/test_turn.py -k "from_closing_on"` → the ledger is frozen from `closing` → AC-6
- [ ] `pytest tests/integration/test_turn.py -k "completes_the_ledger or held_on_closing"` → `ending_from` is set on the turn that reaches `closing`; a thread held on `closing` retires before the call at `ending_turn_cap`, not one turn short → AC-7

## Value sourcing
- [ ] The counted stage is the stored `phase` (the one they were answering), not the stage the ledger gives after the reply → AC-4
- [ ] The cap is `tuning.windows.stage_turn_cap`: change it in `content/prompts/tuning.md`, reseed, and the pass moves with it → AC-12
- [ ] Ledger frozen when `Registry.ending_open(framework_id, stored phase)` → AC-6
- [ ] Concern turn is `assessment.blocks_framework or model_concern`: both a screened message and a reply with `crisis` leave the row alone → AC-8
- [ ] `ending_from` is `count_after` on the first recorded phase where `ending_open` is true → AC-7

## Not a key
- [ ] `grep -rn stage_last_try backend/mani backend/content` → nothing; the turn that reaches the cap still asks that stage once, by design → AC-9, AC-12

## Acceptance-criteria coverage
- AC-4 · test_ledger, cap_is_passed, naming_another, no_state
- AC-6 · from_closing_on
- AC-7 · completes_the_ledger, held_on_closing
- AC-8 · concern_turn_leaves, try_it_on_a_concern
- AC-12 · seed and tuning row
- AC-14 · no_stage_holds, cap_is_passed

# Verify: tasks 4 and 5, evals and close out · spec 0010 · updated 2026-10-09
_Real model runs spend the client's credit: only with muhammad's yes, one style at a time._

## Commands
Run from `backend/` with `.venv` active.

- [ ] `pytest tests/unit/test_baseline.py -k expect_stage` → a skipped `@accept` line is held to the stage after the last line sent; a wrong stage is a `stage` finding naming the stored framework → AC-13
- [ ] `python scripts/eval_replies.py --scenario stages_abcde_told_before_offer --style supportive --verbose` → line 5 stores `dispute`; the reply asks what supports the belief or what questions it → AC-13
- [ ] `--scenario stages_abcde_free_text_yes` → the typed yes lands on `dispute`, the same as the tap → AC-13
- [ ] `--scenario stages_abcde_out_of_order` → `consequences` after the offer is taken, then `effective_new_belief`, no D question in between → AC-13
- [ ] `--scenario stages_abcde_one_side_of_dispute` → `dispute` after the offer is taken; the reply asks only for what questions the belief → AC-13
- [ ] `--scenario stages_abcde_stall` → `belief` held through line 3, `consequences` at line 4, note `passed by the cap: belief` → AC-14
- [ ] `--scenario stages_abcde_vague_meaning` → started on `activating_event`, `belief` after line 2; the reply asks only for what it came to mean → AC-13
- [ ] The five `stages_<framework>_told_before_offer` scenarios → each lands on its third stage (`facts`, `control`, `pull`, `choose`, `observe`) → AC-13
- [ ] `pytest` → whole suite green, integration count about 155, the only skips the four JWKS ones → AC-15

## Value sourcing
- [ ] `expect_stage` reads the stored `thread_technique_state.phase` after the line (`_framework_after`), not the reply's `state.step` → AC-13

## Docs
- [ ] `backend/PORT-STATUS.md`: the ledger decision line says 3 turns and 4 asks; the ending cap line counts from `closing`; the client list has the stages line; the 2026-10-09 measurement line is there → AC-15
- [ ] `backend/docs/database-schema-reference.md`: `stage_ledger` says it is not hosted's `known`; `ending_from` is set at `closing`; `reported_stages` and `stage` on `admin.llm_calls` → AC-15

## Acceptance-criteria coverage
- AC-13 · expect_stage unit test, the eleven `stages_*` scenarios
- AC-14 · stages_abcde_stall
- AC-15 · pytest, docs steps
