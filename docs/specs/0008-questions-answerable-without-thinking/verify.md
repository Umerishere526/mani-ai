# Verify: Mani's questions can be answered without stopping to think · spec 0008 · updated 2026-10-05
_Steps derived from spec 0008 acceptance criteria. `/check verify` runs these; `/test` locks the durable ones._

Run every command from `backend/` with the venv active. The base prompt limit is 118 lines, not the 115 in AC-2 (muhammad, 2026-10-05; ADR-017).

## Commands
- [ ] `pytest tests/unit/test_chat_context.py -k plainly` → passes: every note that asks a stage question says "ask it plainly" and none says "never bare" or "never send it" → AC-1
- [ ] `grep -n "never bare\|in a clause" mani/chat/context.py content/prompts/mani_base.md content/prompts/response_format.md` → no output → AC-1
- [ ] `pytest tests/evals/test_base_prompt.py` → passes: body within 118 lines, the question rule, the stuck check, "conclusion" and "meaning", and the Supportive line are all present → AC-2, AC-3, AC-4
- [ ] `pytest tests/integration/test_turn.py -k body` with local Supabase running → passes with the Supportive check in "What are you noticing in your body right now?" → AC-5
- [ ] `pytest tests/unit/test_authored_questions.py` → passes; put "What is present for you right now, inside you or around you?" back in `dbt_stop.md` `observe` `panic` Reflective and it fails, then restore → AC-6
- [ ] `pytest tests/unit/test_authored_questions.py -k to_find_out` → passes: no `to_find_out` line uses a flagged word → AC-11
- [ ] `pytest tests/evals/test_question_findings.py tests/unit/test_client_style_counts.py` → passes: the scrolling question is caught for length and lead, "What was in that message?" is not, the either/or counts after "i cant decide" and not after "I went to a concert", inside a framework, or on the Library line → AC-7
- [ ] `python -c "import yaml; print([s['name'] for s in yaml.safe_load(open('scripts/eval_conversations.yaml'))][-1])"` → `depressed_alone`, 12 turns, "Let's try it" typed → AC-8
- [ ] `python scripts/seed.py`, then `pytest` → 1510 passed, 4 skipped (the JWKS auth tests), no warnings → AC-10

## Value sourcing
- [ ] The step question comes from the seeded stage: `docker exec -i supabase_db_mani psql -U postgres -tAc "select count(*) from admin.frameworks where stages::text like '%present for you%'"` → 0; with `[x]` on a stage note, `[ctx]` carries `stage_ask` and the note "ask it plainly" → AC-1
- [ ] The say back on a credited turn: build `[ctx]` with `framework_starting` and `known` that answers the first stage (`test_the_turn_a_framework_starts_does_not_ask_what_they_already_told_it`), and the note asks for "one short sentence of its own, never a clause leading into the question" → AC-1
- [ ] The body check lines come from `somatic.md` through the seed: `admin.frameworks` stages hold "What are you noticing in your body right now?" in all 6 rows → AC-5
- [ ] The Framework Index text comes from `to_find_out`: ABCDE's row holds "what they told themselves about it" → AC-11
- [ ] `in_framework` in the eval is true only from the accepted offer on: an either/or after "i cant decide" inside a framework is not counted (`test_question_findings_are_counted_over_the_whole_conversation_with_either_or_only_before_acceptance`) → AC-7
- [ ] A stuck message is read from that one exchange only: the same either/or after "I went to a concert" is not counted, even if an earlier message said "i dont know" → AC-7

## Real model (paid: muhammad says yes first, check credit with get-credits)
- [ ] `python scripts/eval_replies.py --scenario idiot_concert_direct --verbose` and `--scenario depressed_alone --verbose`, each style, one run each (6 conversations) → no `lead clause`, no `flagged word`, no `either/or`; at most one `long question` per conversation → AC-9
- [ ] In `depressed_alone`, "Are you feeling stuck?" appears at most once per conversation (plain text count), never under `safety: concern`, and never followed by an either/or → AC-4, AC-9
- [ ] muhammad and the team lead read the six transcripts and agree the questions read like the old examples; the figures and the read go in the journal → AC-2, AC-3, AC-9

## Acceptance-criteria coverage
- AC-1: plainly test, grep, ctx value steps · AC-2: base prompt test, real model read · AC-3: base prompt test, real model read · AC-4: base prompt test, stuck count in the real run · AC-5: integration body tests, seeded rows · AC-6: authored questions test · AC-7: question findings and counts tests · AC-8: scenario present · AC-9: the six conversation run · AC-10: seed and full suite · AC-11: to_find_out test, seeded ABCDE row
