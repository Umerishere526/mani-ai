# Verify: the model is chosen on real conversations · spec 0006 · updated 2026-10-05
_Steps derived from spec 0006's acceptance criteria. `/check verify` runs the free ones; `/test` locks the durable ones. Run commands from `backend/` with the venv active (`source .venv/bin/activate`). The paid steps are muhammad's to run and report; nothing here has been run against the real model._

## Free checks (no model call, no spend)
- [x] `pytest -q` → 1258 passed, 4 skipped (integration ran, not all skipped) → all ACs
- [ ] `pytest -q tests/unit/test_chain.py -k "reasoning or build_makes or tool_call_runnable"` → the effort goes in the request body as `reasoning.effort`, none sent when unset, a new effort is a new cached model, the tool call runnable sends it too → AC-1
- [ ] `pytest -q tests/unit/test_prompt_cache.py` → `low`, `medium`, `high` and no effort are accepted; any other value (`max`, `LOW`, an empty string, `none`, a number) is refused at load, naming the prompt → AC-1
- [ ] `pytest -q tests/integration/test_turn.py -k "reasoning_effort or without_an_effort or exercise_pick"` → the first draft and the redraft carry the effort and `maxTokens`; the exercise pick carries the effort and `exerciseMaxTokens` (default 200); a prompt without them sends none → AC-1
- [ ] `pytest -q tests/unit/test_seed_prompts.py` → `routing` in a prompt file's frontmatter reaches the row; absent seeds `{}` → AC-2
- [ ] `python scripts/seed.py` then `docker exec -i supabase_db_mani psql -U postgres -c "select name, model_id, model_parameters, routing from admin.prompts order by name"` → five rows, routing `{}` for all while `mani_base.md` names none (checked once on 2026-10-05, including a temporary file with routing that was written and then cleared by the next reseed) → AC-2
- [ ] `pytest -q tests/unit/test_model_trial.py` → the route is pinned (`order`, no fallbacks, `zdr`, `require_parameters`) and keeps `data_collection: deny`; a model without a provider is refused; the override changes model, effort and room and keeps the rest; install and undo only touch `composer.model_settings`; cost takes cached tokens out of input; only the trial model's calls are priced; the header names everything including uncommitted changes → AC-3, AC-4, AC-5
- [ ] `python scripts/eval_replies.py --model google/gemini-3.8-flash` → refused: a model to try needs a provider → AC-3
- [ ] Rehearsal of a stopped run, free because the key is blank: `OPENROUTER_API_KEY= python scripts/eval_replies.py --scenario stress_nothing_named_yet --style supportive --verbose --model google/gemini-3.8-flash --provider google-vertex/global --reasoning-effort low --max-tokens 4096 --exercise-max-tokens 1024` → the header shows the model, effort, room and route; the first turn is reported as `turn failed (config_error)`; the run says `stopped`; then `docker exec -i supabase_db_mani psql -U postgres -c "select count(*) from auth.users where email like '%@eval.mani.local'"` is 0 (done once on 2026-10-05) → AC-3, AC-4, AC-5

## Value sourcing (one per row of the spec's table)
- [ ] Model, parameters, routing for a chat, title or exercise call come from `composer.model_settings`, or the runner's replacement of it → `test_installing_the_override_changes_composer...` and the rehearsal header → AC-3
- [ ] Effort and max tokens: sent when set, not when absent; 2048 when absent → `test_a_prompt_without_an_effort_sends_none` → AC-1
- [ ] Exercise pick room: `exerciseMaxTokens`, default 200 → `test_the_exercise_pick_keeps_its_small_default_room` → AC-1
- [ ] Reply time: the runner's own timing of each `orchestrator.send`, printed as `[time]` per turn and a median and longest per run (the rehearsal prints `0.0s` for a turn that failed before any call) → AC-5
- [ ] Cost and schema failures: read from `admin.llm_calls` per run before the users are removed, printed as `calls: ..., schema failures: ...` and one line per purpose, model and outcome → `test_figures_price_only_the_trial_model_and_count_schema_failures` → AC-5

## Paid measurement (muhammad runs it; about $0.70 to $0.90, check the credit first)
Check the credit before and after (OpenRouter MCP `get-credits`, or the OpenRouter dashboard). If the credit is under $1.50, stop and ask. `mkdir -p .eval/model_trial` first (the folder is git ignored). Reseed first (`python scripts/seed.py`) so the prompts in the database are the files in the tree. `COMMON` is the same for every run; the three price flags make the run print the cost (Vertex standard prices on 2026-10-05).

```
COMMON="--style supportive --verbose --model google/gemini-3.8-flash --provider google-vertex/global --reasoning-effort low --max-tokens 4096 --exercise-max-tokens 1024 --price-input 0.75 --price-cached-input 0.075 --price-output 3.75"
python scripts/eval_replies.py $COMMON --scenario stress_nothing_named_yet 2>&1 | tee .eval/model_trial/stress-1.txt
```

- [ ] **Route check first**: the stress run above, alone. It must not say `turn failed`. If it says the route was refused (the endpoint tag not accepted, no zero retention endpoint, an endpoint that cannot honour structured output or reasoning), stop and report the message; do not try another route. Check the first turn's cost against the Vertex standard prices to confirm the tier → AC-4
- [ ] `stress_nothing_named_yet` three runs (stress-1, stress-2, stress-3) → each: no offer by message 4 (the `first offer at message` column is `[None]`), and the last replies ask about what happened → AC-5, AC-6
- [ ] `grief_dog_steering` three runs → each reaches an offer and never Behavioral Activation → AC-5, AC-6
- [ ] `deadlines_steering` three runs → each reaches Structured Problem Solving → AC-5, AC-6
- [ ] `panic_attack_grounding` once → DBT STOP offered → AC-5, AC-6
- [ ] `manager_embarrassed_me` once → ABCDE offered → AC-5, AC-6
- [ ] `journey_abcde` once → reaches the body check in, and the hand-off picks an exercise. **Prerequisite**: the local catalog has no exercises (checked 2026-10-05: 0 active), so the pick never runs. Run `python scripts/seed_exercises.py` first (it uploads the audio to the local `exercises` bucket and fills `admin.exercises`; Supabase must be running). Then the figures must show a line `exercise_select  ok` for this run; `schema_invalid` there means the model made no tool call and the first exercise was used instead → AC-5
- [ ] Across all 12 runs: `schema failures: 0` in every run (one that only worked on the retry still counts); no `turn failed`; the validators' FAIL lines compared with the lite model's runs of the same chats in the journal note `framework-fit-from-facts-first-runs-2026-10-05` → AC-5, AC-6

## Decision
- [ ] All 12 runs meet their expected outcome and have no schema failure → switch: set `mani_base.md` to `model_id: google/gemini-3.8-flash`, `model_parameters` `reasoning_effort: low`, `maxTokens: 4096`, `exerciseMaxTokens: 1024` (if the journey needed it) and `routing` `order: [google-vertex/global]`, `allow_fallbacks: false`, `zdr: true`, `require_parameters: true`; `python scripts/seed.py`; `pytest -q` → AC-6
- [ ] Any run misses → change nothing; report the figures. Do not try a second effort level without saying so → AC-6
- [ ] Either way: the journal note, PORT-STATUS (including that production chat on AI Studio is probably not zero retention today, and that summaries and memory folding are not), and on a switch ADR 015 → AC-7

## Acceptance-criteria coverage
- AC-1 chain, cache, orchestrator tests · AC-2 seed tests and the database check · AC-3 runner flags, trial tests, the rehearsal · AC-4 the route check and the rehearsal · AC-5 the 12 paid runs · AC-6 the decision rule · AC-7 the records step
