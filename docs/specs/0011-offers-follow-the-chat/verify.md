# Verify: frameworks offered when the chat fits · spec 0011 · updated 2026-10-08
_Steps derived from spec 0011 acceptance criteria and its value sourcing table. `/check verify` runs these; `/test` locks the durable ones._

## UI / manual
- [ ] Start a thread, tap a style, send "I've been avoiding my friends because I've been overwhelmed", then "and I feel guilty about ignoring them" → the second `[ctx]` has `cooldown_passed: yes` and no `framework_shortlist`; if Mani offers, the button is stored and the log reads `offer on thread <id>: <framework> cooldown_passed: yes` with no word of what was said        → AC-1, AC-8
- [ ] New thread, first message "I am about to send a message I will regret" → `cooldown_passed: no`, no offer button        → AC-5 (value: whether an offer may be made)
- [ ] New thread, say "my dog died", then "I have stopped doing things I enjoy" → `[ctx]` has `ruled_out: behavioral_activation` and Mani never offers Behavioral Activation        → AC-3 (value: which sets are ruled out)
- [ ] Vary the input: say "a grievance at work" with no loss words → `ruled_out` is absent (whole words only)        → AC-3
- [ ] Send a technique button whose id is not a framework → it is dropped and nothing is stored        → AC-1 (value: whether the offered id is real)

## Commands
- [ ] `cd backend && source .venv/bin/activate && pytest` → all pass with pristine output, integration tests not skipped        → AC-9
- [ ] `grep -rni shortlist backend/mani backend/content backend/scripts` → no matches        → AC-7
- [ ] `ls backend/mani/chat/router.py` fails, `backend/mani/chat/vetoes.py` exists with `ruled_out`        → AC-2
- [ ] `grep -rn "strong_signals\|distinctions\|redirects" backend/content/frameworks` → no matches        → AC-4
- [ ] Add `signals: [x]` to a framework file's `activation` and run `python scripts/seed.py` → refused, naming the file        → AC-4
- [ ] Set `never_offer_when_said` to a string in a framework file and run the seed → refused, naming the file        → AC-4
- [ ] `docker exec supabase_db_mani psql -U postgres -tAc "select id, activation from admin.frameworks order by id"` → only `behavioral_activation` holds a key, `never_offer_when_said`        → AC-4
- [ ] `docker exec supabase_db_mani psql -U postgres -tAc "select content from admin.prompts where name = 'tuning'" | grep router` → no match, and the tuning row loads        → AC-6
- [ ] Edit a framework's `activation` in the database to `{"never_offer_when_said": ["died", " "]}`, restart, send a message → one error log naming the framework id and no phrase, and the veto ignored        → AC-3

## Acceptance-criteria coverage
- AC-1 … covered by steps 1, 5 · AC-2 … `router.py` check · AC-3 … steps 3, 4 and the log step · AC-4 … framework, seed and database steps · AC-5 … step 2 · AC-6 … tuning step · AC-7 … grep step · AC-8 … step 1 · AC-9 … `pytest` step
