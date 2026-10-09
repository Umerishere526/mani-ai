# Verify: the offer and Tell Me More per framework and style · spec 0015 · updated 2026-10-08
_Steps derived from spec 0015 acceptance criteria and its value sourcing table. `/check verify` runs these; `/test` locks the durable ones._

## UI / manual (chat tester, after the reseed and a restart)
- [ ] New chat, tap Reflective, talk until Mani offers ABCDE → the message is exactly `by_framework.abcde.reflective.text`, with no `Framework:` line; the buttons are Try It · Tell Me More · Keep Chatting        → AC-3, AC-4 (values: the style, the ABCDE offer text)
- [ ] Tap Tell Me More → the reflective lead line and the five steps shown as a list; buttons Try It · Keep Chatting; the API log shows no model call for that turn. Note whether the client's "these concerns" (Reflective) and "these feelings" (Supportive) read naturally after what was said        → AC-3, AC-4
- [ ] Tap Try It → Mani opens with a short line and the first stage not yet known, with no list of the five steps and no request for the event already given        → AC-5
- [ ] Repeat the offer in a Directive and a Supportive chat → each shows its own style's text        → AC-3, AC-4
- [ ] In any style, reach an offer of a framework other than ABCDE → the shared lead, `Framework: <name>` and its description, as before; Tell Me More shows the name and description        → AC-6

## Commands
- [ ] `cd backend && source .venv/bin/activate && pytest` → all pass with pristine output; passed and skipped counts recorded before and after; integration tests not skipped        → AC-8
- [ ] `pytest tests/integration/test_turn.py -k "offer or tell_me_more"` → the per style offer, the shared frame for the others, the default style, and Tell Me More followed by Try It pass        → AC-3, AC-4, AC-5, AC-6
- [ ] `pytest tests/integration/test_turn.py -k profile_style` → a thread with no style and a Directive profile gets the Directive ABCDE offer and Tell Me More; with no profile style, the tuning default's (Supportive)        → AC-4 (value: the style, thread then profile then default)
- [ ] `pytest tests/unit/test_config_rows.py tests/unit/test_seed_frameworks.py` → the `by_framework` refusal cases and the unknown id refusal pass        → AC-1, AC-2
- [ ] Compare the three `text` and three `more_text` values with the .docx's `word/document.xml` → only the generalised words differ, as listed in `index.md`        → AC-1
- [ ] `git diff` on `mani_base.md`, `response_format.md` and `content/frameworks/` against the commit before the build → no change        → AC-5
- [ ] `grep -n "phase: activate\b" backend/scripts/eval_conversations.yaml` → no match; `abcde_told_more` is present        → AC-7
- [ ] The `@more` unit test passes        → AC-7
- [ ] After muhammad's yes: `python scripts/eval_replies.py --scenario abcde_told_more --style reflective --verbose` → the reply after Try It neither lists the five steps nor asks for the event again; the result is in the journal note        → AC-7
- [ ] `python scripts/seed.py` → accepts the `replies` row; with a `by_framework` key renamed to `abcd`, it refuses and names `abcd`, with nothing written        → AC-1, AC-2
- [ ] `PORT-STATUS.md`: the `replies` decision line names `by_framework`, the client list's Tell Me More line is replaced as AC-9 says, scope feature 17's done line is reworded, and the journal note exists        → AC-9

## Acceptance-criteria coverage
- AC-1 … config rows tests, the .docx comparison and the seed step · AC-2 … the seed test and the rename check · AC-3 … the UI steps and the integration tests · AC-4 … the UI steps in three styles and the default style test · AC-5 … the Try It step, the integration test and the prompt diff · AC-6 … the other framework UI step and the integration tests · AC-7 … the scenario grep, the `@more` test and the real run · AC-8 … `pytest` · AC-9 … the PORT-STATUS and scope step
