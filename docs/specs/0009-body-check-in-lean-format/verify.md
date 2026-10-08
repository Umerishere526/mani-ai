# Verify: body check in lean format · spec 0009 · updated 2026-10-08
_Steps derived from spec 0009 acceptance criteria. `/check verify` runs these; `/test` locks the durable ones. Nothing here runs against a real model (muhammad, 2026-10-08). Run the manual steps after the reseed._

## Commands
- [ ] `cd backend && source .venv/bin/activate && python scripts/seed.py`, then `select id, phases, stages from admin.frameworks` → every framework's `phases` ends `closing, somatic_checkin, somatic_practice` and `stages` is `{}`; the seed runs with `content/prompts/somatic.md` gone → AC-2
- [ ] `docker exec supabase_db_mani psql -U postgres -c "\d public.thread_technique_state"` → `ending_from integer`, nullable, with `technique_state_ending_from_not_negative` → AC-9
- [ ] Put a throwaway thread on `somatic_practice` and one on `closing`, apply migration 020 (`supabase migration up --local`) → only the `somatic_practice` row gets `ending_from` equal to its thread's `message_count` → AC-9
- [ ] `./scripts/test_db.sh` and `./scripts/test_db.sh --local` → both pass, `authenticated` still holds no insert or update on `thread_technique_state` → AC-9
- [ ] `cd backend && pytest -rs` → whole suite passes with pristine output; the only skips are the four JWKS endpoint tests, and the integration tests ran, not skipped → AC-13
- [ ] `grep -rn "chat.ending\|_body_route_step\|is_final\|\.stages" backend/mani` → nothing under `mani/chat/` reads `stages`, defines `_body_route_step` or imports `ending` → AC-11
- [ ] `grep -n "stage_purpose\|stage_ask\|stage_if_unclear" backend/content/prompts/*.md` → no hits, and `test_prompts_name_what_exists` lists all six → AC-3, AC-13

## UI / manual (scripted model, no real run)
- [ ] Build `[ctx]` for a running abcde on `closing`, `somatic_checkin` and `somatic_practice` → only `stage` and `next_stage`, no `stage_*` or `next_stage_*` line; the `CTX_KEYS` contract test passes → AC-3
- [ ] `Registry.ending_open` on `closing`, `somatic_checkin`, `somatic_practice` of a seeded framework is true; false on a mid stage, a null phase, an unknown id, and a registry whose phases have no ending ids → AC-5
- [ ] Guards: `choice` and ` Keep_Talking ` are kept while the ending is open; `choice` on a mid stage, on no framework, and with a reported phase past the stored one (stored `closing`, reported `somatic_checkin`) are dropped with a note; a kept `ending` drops a technique button even when nothing is running → AC-4, AC-5
- [ ] Stored `somatic_practice`, scripted `ending: choice` with its own buttons and a state reporting `somatic_practice` → stored phase null, `ending_from` null, `library_offered_since` true, buttons exactly Chat More and Go to Library (home), the exercise card picked, next turn has no `library_pending` → AC-6, AC-8
- [ ] Same with `keep_talking`, from `somatic_practice` and from `somatic_checkin` → no buttons, no card, no exercise pick call, next `[ctx]` says `conversation_phase: talking`, no `library_pending`, no `active_framework` → AC-7
- [ ] A reply on `closing`, `somatic_checkin` or `somatic_practice` with model buttons and no `ending` → no buttons reach the person → AC-8
- [ ] A concern message ("I don't want to be here anymore") with `ending: choice` scripted → phase and outcome left as stored, no buttons → AC-5
- [ ] A crisis message on a thread stored in `somatic_practice` → thread locks, framework retired, no buttons → AC-12
- [ ] First reply reported in `somatic_checkin` → `ending_from` equals the thread's count; a later `somatic_practice` reply keeps it; a step back to `closing` keeps it; retirement clears it → AC-9
- [ ] `ending_from` 24 messages behind with an unfinished ending → retires before the call, the scripted model sees no `active_framework`, no buttons, no card, log line names the thread id and the cap and no message text; 22 behind → does not retire → AC-10
- [ ] Reseed ran against the DB while a thread was already in `somatic_practice` → that thread carries on in the ending → AC-2

## Value sourcing
- [ ] Vary the stored phase (`closing`, `somatic_checkin`, `somatic_practice`, a mid stage, null) against `ending_open` passed to `guards.check`; it is true only for the first three and only for an accepted framework → AC-5
- [ ] Vary the clamped reported phase against the stored one (hold, step back, one forward, a skip) → only a hold or a step back may carry `ending` → AC-5
- [ ] Vary `thread.message_count` and `ending_from` around the cap (`(count - ending_from) // 2` at 11, 12, 13) → the retire fires from 12 → AC-10
- [ ] Vary the style (supportive, reflective, direct) in `[ctx]` on the ending turns → `conversation_style` changes, no per style ending text appears in `[ctx]` → AC-3
- [ ] Eval files: `panic_somatic_once` turns match the spec; `missing_handoff` flags exactly one of Chat More / Go to Library on a move from an ending phase to retired and accepts both or neither → AC-13

## Acceptance-criteria coverage
- AC-1 … `mani_base.md` `ending` section, wording reviewed by muhammad before the reseed (open) · AC-2 … seed steps · AC-3 … `[ctx]` steps · AC-4 … guard steps and the `fields.ending` line · AC-5 … `ending_open`, guard and concern steps · AC-6 … `choice` step · AC-7 … `keep_talking` step · AC-8 … model buttons step · AC-9 … migration and `ending_from` steps · AC-10 … cap steps · AC-11 … grep step · AC-12 … crisis step · AC-13 … pytest, `REMOVED` and eval steps
