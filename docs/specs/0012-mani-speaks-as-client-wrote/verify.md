# Verify: Mani speaks and asks as the client wrote · spec 0012 · updated 2026-10-08
_Steps derived from spec 0012 acceptance criteria and its value sourcing table. `/check verify` runs these; `/test` locks the durable ones._

## UI / manual
- [ ] Start a new thread in the chat tester → the greeting's buttons read Directive, Supportive, Reflective, in that order; tap Directive → the caption shows `style: Directive` (new threads only) and the thread's `conversation_style` is `direct`        → AC-8 (value: the style button's text, the style a tap picks)
- [ ] Open a thread whose greeting was stored before the change (buttons say Direct), tap Direct → the style is `direct`        → AC-8
- [ ] In a new thread with nothing running, read the `[ctx]` block for the first message (debug view or log) → it has `conversation_phase` and `cooldown_passed`, and no `clarification_lines` and no `question_focus`        → AC-5, AC-6

## Commands
- [ ] `cd backend && source .venv/bin/activate && pytest` → all pass with pristine output; passed, skipped and deleted counts recorded before and after; integration tests not skipped        → AC-12
- [ ] `wc -lw backend/content/prompts/mani_base.md backend/content/prompts/response_format.md` → total under 150 lines and under 3616 words        → AC-9 (value: the prompt size)
- [ ] `grep -n "not as a fact, a guess or a question\|Start with what they feel\|Feelings first\|never the facts\|the soonest to offer\|pick what is worst\|Follow the feeling\|reaches, unseen\|If two fit\|only once you have learned" backend/content/prompts/mani_base.md` → no matches        → AC-1, AC-2, AC-3, AC-4
- [ ] Diff `mani_base.md` against `main` → `offers` lines 2, 4 and 5 and the second sentence of line 1 are unchanged; every `styles`, `questions` and `offers` change matches the drafts in `index.md`        → AC-2, AC-3, AC-4
- [ ] `grep -n "have I not learned\|what to learn first\|clarification_lines\|question_focus" backend/content/prompts/response_format.md` → no matches        → AC-5
- [ ] `grep -rn "clarification_lines\|question_focus\|feeling_then_way_through" backend/mani backend/content` → no matches; all three names are in `REMOVED` in `tests/unit/test_prompts_name_what_exists.py`        → AC-6
- [ ] `grep -h "^Starts when" backend/content/frameworks/*.md` → the four drafted lines appear exactly; `dbt_stop` and `structured_problem_solving` are unchanged from `main`        → AC-7
- [ ] `python scripts/seed.py` → accepts all six framework files and the `replies` row; then `docker exec supabase_db_mani psql -U postgres -tAc "select content from admin.prompts where name = 'replies'" | grep -c clarification` → `0`        → AC-6, AC-7
- [ ] `grep -n "Direct\b" backend/docs/specs/conversational-styles.md backend/docs/specs/README.md` → no match for the style name; the source line names the October 8 .docx; the scenario sections are the four October 8 scenarios; the comment above the `client_*` scenarios in `scripts/eval_conversations.yaml` does not say verbatim        → AC-10
- [ ] `grep -n "clarification lines\|clarification_lines\|learned what its Starts when" backend/PORT-STATUS.md` → no match describing current behavior (lines 64, 76, 139, 161 edited); the "Open decisions for muhammad" section has the check lines line; the client list has the check lines line; scope feature 14's done line matches AC-9 and AC-11        → AC-12

## Real runs (only after muhammad's yes, `get-credits` first)
| Run | Command | First offer at message (2 to 4) | Stock phrase found | Result |
|---|---|---|---|---|
| 1 | `python scripts/eval_replies.py --scenario client_anxiety --style direct --verbose` | `[None]` | none of the three | fail, 2026-10-08 (asked twice about the chest tightness) |
| 2 | `python scripts/eval_replies.py --scenario client_overthinking --style reflective --verbose` | `['2:thought_reframe']` | none of the three | pass, 2026-10-08 |
| 3 | `python scripts/eval_replies.py --scenario client_stress --style supportive --verbose` | `['2:structured_problem_solving']` | none of the three | pass, 2026-10-08 |

Before reading each run, confirm its thread has `conversation_style` set. The column prints a list such as `['2:abcde']`; `[None]` is a fail; for `client_anxiety` and `client_stress` the window is 2 to 3. Stock phrases: search the `--verbose` replies by hand, case insensitive, straight and curly apostrophes, for "I hear you", "That makes sense", "I'm here for you". Record as measured; never rerun until it passes        → AC-11 (value: the real run results)

## Acceptance-criteria coverage
- AC-1 … mani_base grep · AC-2 … grep and diff · AC-3 … grep and diff · AC-4 … grep and diff · AC-5 … `[ctx]` step and response_format grep · AC-6 … `[ctx]` step, code grep, seed step · AC-7 … Starts when grep and seed · AC-8 … the two button steps · AC-9 … `wc -lw` · AC-10 … the docs step · AC-11 … real runs table · AC-12 … `pytest` and PORT-STATUS steps
