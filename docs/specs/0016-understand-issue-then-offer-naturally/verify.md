# Verify: Mani understands the issue, then offers naturally · spec 0016 · updated 2026-10-08
_Steps derived from spec 0016 acceptance criteria and its value sourcing table. `/check verify` runs these; `/test` locks the durable ones._

## UI / manual (chat tester, after the reseed and a restart)
- [ ] New chat, any style, talk until Mani offers → the message opens with a short text of Mani's own that answers your last message (no question, no recap, no offer of its own), then a blank line, then the seeded offer; buttons Try It · Tell Me More · Keep Chatting        → AC-4 (values: the bridge line, the offer words)
- [ ] On a fresh offer, type "what would that involve?" → Mani's two sentence answer, a blank line, then the seeded offer and its three buttons again        → AC-4
- [ ] Tap Tell Me More → the seeded Tell Me More text alone, with no bridge line; the API log shows no model call        → AC-4
- [ ] Send a vague first message ("I'm upset") → the reply asks what is going on, and does not hand back "upset"        → AC-1, AC-2
- [ ] Send one message only → no offer, whatever it says        → AC-3 (value: `cooldown_passed`)

## Commands
- [ ] `wc -l -w backend/content/prompts/mani_base.md backend/content/prompts/response_format.md` → 74 and 71 lines, 3418 words together        → AC-6
- [ ] `git diff` on those two files against the commit before the build → exactly the seven lines E1 to E7, each matching `index.md`; no other prompt or framework file changed        → AC-1, AC-2, AC-3, AC-5, AC-6
- [ ] `git diff backend/content/prompts/tuning.md` → empty        → AC-3
- [ ] `pytest tests/integration/test_turn.py -k "offer or tell_me_more"` → the offer with a bridge line, the blank line case, the typed question re-offer, and Tell Me More pass        → AC-4, AC-7
- [ ] `cd backend && source .venv/bin/activate && pytest` → all pass with pristine output; counts recorded before and after; integration tests not skipped        → AC-7
- [ ] `grep -n "client_job_decision" backend/scripts/eval_conversations.yaml` → present, as drafted        → AC-8
- [ ] After muhammad's yes and `get-credits`: `python scripts/eval_replies.py --scenario client_job_decision --style direct --verbose`, then `supportive`, then `reflective` → each read against the five bullets of AC-8, recorded as measured; a failing run reported, not rerun        → AC-8
- [ ] `PORT-STATUS.md` lines near 73 to 78, 82, 136 to 142 and 151 edited in place; the client line added under "Open decisions"; spec 0012 AC-11 has no 2 to 4 window and points to spec 0016; the journal note exists        → AC-9

## Acceptance-criteria coverage
- AC-1 … the vague opener step, the diff and the real runs · AC-2 … the vague opener step, the diff and the runs' first reply · AC-3 … the one message step, the tuning diff and the runs' first offer column · AC-4 … the UI offer and Tell Me More steps and the integration tests · AC-5 … the diff and the runs' reply after Try It · AC-6 … `wc` and the diff · AC-7 … `pytest` · AC-8 … the three runs · AC-9 … the PORT-STATUS step

## Round 3 · updated 2026-10-08
_Steps derived from spec 0016 round 3 (AC-1, AC-3, AC-4, AC-6, AC-7, AC-8) and its round 3 Value sourcing rows._

### Commands
- [ ] `cd backend && pytest tests/unit/test_offer.py` → 6 pass: ABCDE alone in each style, ABCDE after a typed question, the model's offer then the card, the card alone for a blank line → AC-4, AC-7
- [ ] `cd backend && pytest` → 690 passed, 4 JWKS skips; `pytest tests/integration` → 147 passed, none skipped → AC-7
- [ ] `wc -l content/prompts/mani_base.md content/prompts/response_format.md` → 74 and 71; `cat` both `| wc -w` → 3422 → AC-1, AC-3, AC-6

### Real conversation (after a reseed and restart)
- [ ] A conversation offered Structured Problem Solving → the offer turn is Mani's own words, a blank line, then `Framework: Structured Problem Solving` and its description; buttons Try It · Tell Me More · Keep Chatting → AC-4, AC-8
- [ ] A conversation offered ABCDE → the client's text for the thread's style, with nothing before it → AC-4
- [ ] With an ABCDE offer waiting, type "what would that involve?" → Mani's answer, a blank line, then the client's text; the offer stays `offered` in `thread_technique_state` → AC-4 (`answering` from `deferred` and the outcome)
- [ ] With `ai_debug_mode` on, a reply's reasoning starts from what they face, not from what they need → AC-1 (E12)

### Acceptance criteria coverage
- AC-1 · E12 reasoning step · AC-3 · E5 span (offer at message 3 or later, 9 of 9 in the round 3 runs) · AC-4 · the offer rule · AC-6 · counts · AC-7 · tests · AC-8 · the twelve runs, recorded in `backend/PORT-STATUS.md`

## Round 4 · updated 2026-10-09
_Steps derived from spec 0016 round 4._

### Commands
- [ ] `cd backend && pytest tests/unit/test_offer.py` → 7 pass: ABCDE and Structured Problem Solving offered in the seeded words alone, an answer before the offer, ABCDE's Tell Me More per style, the name and description for the rest
- [ ] `cd backend && pytest` → 691 passed, 4 JWKS skips; integration not skipped
- [ ] `wc -l` of `mani_base.md` and `response_format.md` → 74 and 71; `cat` both `| wc -w` → 3409

### Real conversation (after a reseed and restart)
- [ ] An offer of any set → "We'll go through a few focused questions. …Would it help to work through it together?", a blank line, `Framework: <name>`, a blank line, the description; nothing before it; buttons Try It · Tell Me More · Keep Chatting
- [ ] An ABCDE offer → the same shared words, not the client's per style text
- [ ] Tell Me More on ABCDE → its five steps in the thread's style; on another set → its name and description
- [ ] With an offer waiting, type "what would that involve?" → Mani's answer, a blank line, then the seeded offer; the offer stays `offered`

