# Verify: the offer in the client's words · spec 0013 · updated 2026-10-08
_Steps derived from spec 0013 acceptance criteria and its value sourcing table. `/check verify` runs these; `/test` locks the durable ones._

## UI / manual (chat tester, after the reseed and a restart)
- [ ] Talk until Mani offers (or use a scripted thread) → the message is the lead, a blank line, `Framework: <name>`, a blank line and that framework's description, exactly as in `index.md`; the buttons are Yes, let's try it · Tell me more · I want to keep talking; the text field, Send and mic are hidden        → AC-4, AC-9 (values: the offer's text, the three labels, the hidden field)
- [ ] Tap Tell me more → Mani answers `Framework: <name>` and the description, with Yes, let's try it · I want to keep talking; the field stays hidden; the API log shows no model call for that turn        → AC-5, AC-9
- [ ] Tap Yes, let's try it → the framework starts on its first stage not yet known; the field shows again        → AC-5, AC-9
- [ ] In a second thread, tap I want to keep talking on an offer → Mani follows them with no buttons; the field shows again; the thread's technique row is declined        → AC-4, AC-9

## Commands
- [ ] `cd backend && source .venv/bin/activate && pytest` → all pass with pristine output; passed and skipped counts recorded before and after; integration tests not skipped        → AC-11
- [ ] `pytest tests/integration/test_turn.py -k "offer or tell_me_more or carrying_on"` → the offer (including empty scripted text, no style stored), Tell me more (model call count unchanged by the tap), typed past offer and no offer cases pass        → AC-4, AC-5, AC-6, AC-7
- [ ] `pytest tests/unit/test_config_rows.py tests/unit/test_seed_frameworks.py` → the `offer` refusal cases, the seven line check and the blank summary refusal pass        → AC-1, AC-2, AC-3
- [ ] `grep -n "^name:\|^summary:" backend/content/frameworks/*.md` → the six names and summaries match the table in `index.md` exactly        → AC-2
- [ ] `grep -c "^Offer:" backend/content/frameworks/*.md` → `0` for every file; `grep -rn -i "eight lines\|eight model\|eight labelled\|eight_lines" backend/mani backend/scripts backend/tests` → no match        → AC-3
- [ ] Diff `mani_base.md`, `response_format.md` and `tuning.md` against the commit before the build → only `offers` lines 1, 2 and 5, the four `response_format.md` lines and the `tuning.md` comment change, each matching its draft        → AC-8
- [ ] `grep -rn "Keep chatting\|Try it\b" backend/mani backend/tests backend/scripts chat-tester` → matches only in `tests/unit/test_schema.py`'s decline word cases and the `mani/llm/schema.py` docstring        → AC-10
- [ ] Run one scripted or cached eval transcript through `eval_replies.py`'s checks → no `says_framework` or feeling finding on the offer or the Tell me more reply; the model's replies are still checked        → AC-13
- [ ] `grep -n "as the model wrote it" .claude/BACKEND.md backend/mani/routers/messages.py` → each names the offer exception; `.claude/BACKEND.md`'s `chat/` line names `offer.py`        → AC-12
- [ ] `python scripts/seed.py` → accepts the six framework files and the `replies` row; then `docker exec supabase_db_mani psql -U postgres -tAc "select name from admin.frameworks order by display_order"` → the six client names        → AC-1, AC-2
- [ ] `PORT-STATUS.md`: the two decisions in force are edited in place, the client list has the shared lead and the interim Tell me more lines, and scope feature 15 links spec 0013        → AC-12

## Acceptance-criteria coverage
- AC-1 … config rows tests and the seed step · AC-2 … the frontmatter grep and the names query · AC-3 … the `Offer:` and eight lines greps · AC-4 … the first UI step and the integration tests · AC-5 … the Tell me more steps · AC-6 … the integration tests · AC-7 … the integration tests · AC-8 … the prompt diff · AC-9 … the UI steps · AC-10 … the label grep · AC-11 … `pytest` · AC-12 … the PORT-STATUS and BACKEND.md steps · AC-13 … the eval step
