# Verify: model facing text out of Python · spec 0007 · updated 2026-10-08
_Steps derived from spec 0007 acceptance criteria. `/check verify` runs these; `/test` locks the durable ones._

No real model run is part of this verification (muhammad, 2026-10-07). Every step below runs against the local database with a scripted model, or reads files and rows.

## Commands
- [ ] `cd backend && source .venv/bin/activate && python scripts/seed.py` → seeds 6 frameworks and 8 prompts, `debug` among them, with no refusal → AC-1, AC-5
- [ ] `pytest -q` with local Supabase up → 641 passed, 4 skipped (the JWKS token tests only); `pytest -q tests/integration` → 115 passed, none skipped → AC-13
- [ ] `./scripts/test_db.sh` and `./scripts/test_db.sh --local` → exit 0, no FAIL, and "PASS: a response shape added in content is stored" → AC-6
- [ ] `docker exec supabase_db_mani psql -U postgres -tAc "select conname from pg_constraint where conrelid = 'public.thread_response_styles'::regclass"` → no `response_styles_shape_known`, `response_styles_voice_known` still there → AC-6
- [ ] `grep -rn "stage_note\|closest_fit\|offer_fit\|DISCRIMINATORS\|SHAPES\b\|is_confident\|DEBUG_LAYER" backend/mani backend/content` → nothing → AC-1, AC-2, AC-6, AC-7, AC-8, AC-9

## Behaviour against the seeded database (scripted model)
- [ ] Compose a system prompt with a profile, memory, an offered list and a summary → after the three static layers, only `## User Context`, `## Memory`, `## Techniques Already Offered` and `## Conversation Context` with `key: value` or `- id` lines; no sentence of instruction → AC-1
- [ ] Set `AI_DEBUG_MODE=true` → the last layer is the `debug` row's text; deactivate the row → the layer is absent and one warning is logged → AC-1
- [ ] A turn while a framework runs → `[ctx]` has `stage:` and `next_stage:` and no `stage_note`; a Direct conversation before a framework → `question_focus: feeling_then_way_through` → AC-2
- [ ] A thread with a summary that lists a technique that did not help → `[ctx]` `history:` and `## Conversation Context` both read `<name> (not_helpful)` → AC-1, AC-2
- [ ] Tap Keep chatting under an offer → the model's last user message ends `tapped: Keep chatting` → AC-3
- [ ] A summary run on a thread with no summary → the user message starts `## New Messages`, with no `## Existing Summary` and no instruction sentence → AC-3
- [ ] A memory fold → the user message has `## Known so far` then `## Conversation` → AC-3
- [ ] An exercise pick with an issue and recent lines → user message `current_issue: ...` then one `said: ...` per line → AC-3
- [ ] Walk `Reply`, `Extraction`, `Memory` and `StartExercise` schemas, both `model_json_schema()` and `convert_to_openai_function` → no description with text at any depth → AC-4
- [ ] Edit `mani_base` in the portal so `reply_shapes` is gone, invalidate the cache, send a turn → an error is logged, the turn succeeds, and its reported shape is dropped → AC-6
- [ ] Add a seventh shape under `reply_shapes`, reseed, script the model to report it → the turn stores it in `thread_response_styles` → AC-6
- [ ] Give a framework in the portal a distinction with `priority: 0` → `Registry` logs "framework distinction dropped" and the other rules still route → AC-7
- [ ] Five messages whose words match no phrase list → no `framework_shortlist`, `offer:` or `closest_fit` line on any turn → AC-8, AC-9
- [ ] An abcde phrase in the first message, then five that match nothing → `framework_shortlist: abcde` still present on the sixth → AC-9
- [ ] One message that scores six frameworks and says a loss word → `framework_shortlist` lists five ids, no scores, and `ruled_out: behavioral_activation` → AC-9
- [ ] "I am about to send it" as the first message → `framework_shortlist: dbt_stop` and `cooldown_passed: yes` → AC-10
- [ ] Script an offer of a set off the shortlist → the button goes out and one info line reads `offer on thread <id>: <fid> on_shortlist: no shortlist: none cooldown_passed: yes`, with no message text → AC-11

## Value sourcing
- [ ] Allowed shapes: change `reply_shapes` in `mani_base.md`, reseed, wait out the cache → `config.reply_shapes` matches the new keys, lowercased
- [ ] Stored shape: a shape outside the seeded set is dropped by the guard before any write, and one inside it is stored
- [ ] Ordered rules: swap two priorities in the framework files, reseed → `registry.distinctions` order follows the new priorities
- [ ] Urgency phrases: the only rule with an empty `over` (dbt_stop's) is the one `router.urgent` reads
- [ ] Older message weight: a sign at distance 5 scores `0.15` per phrase, not 0
- [ ] Shortlist ids: a ruled out framework never appears in `framework_shortlist`
- [ ] `[ctx]` keys: `_line("anything_new", ...)` raises; `CTX_KEYS` and `response_format.md` `ctx` agree both ways
- [ ] Layer headings: `LAYER_HEADINGS` and `response_format.md` `layers` agree both ways
- [ ] `question_focus`: Direct gives `feeling_then_way_through`, Supportive and Reflective give `feelings`
- [ ] `## User Context`: comes from `public.profiles` nickname and topics, each line only when set
- [ ] `## Memory`: one line per non empty `admin.user_memory` list, keyed by its field name
- [ ] Issue, summary, techniques tried: come from `public.thread_summaries`, rendered by `composer.tried_line` in all three places
- [ ] `## Techniques Already Offered`: the framework ids in `thread_techniques_offered`, plus any accepted this turn
- [ ] Exercise pick message: the `current_issue` and `said` arguments of `client.choose_exercise`
- [ ] Debug layer: the `debug` row's content, edited in the portal, shows on the next turn after the cache reloads
- [ ] Moved sentences: edit any one in `response_format.md`, reseed, and the next composed prompt carries it with no code change
- [ ] Offer log: the offered id comes from the kept buttons, the shortlist from the turn, `cooldown_passed` from `context.cooldown_passed`

## Acceptance criteria coverage
- AC-1 composer layers and debug row · AC-2 `[ctx]` keys and stage rules · AC-3 the four messages · AC-4 schema walk · AC-5 seed and moved sentences · AC-6 shapes, guard, migration 019 · AC-7 distinctions, seed refusals, registry soft failure · AC-8 no closest fit at any message · AC-9 uncut ranked ids and recency tail · AC-10 urgency on the first message · AC-11 offer log · AC-12 contract tests in `tests/unit/test_prompt_contract.py` · AC-13 suite, database suites, PORT-STATUS and schema reference
