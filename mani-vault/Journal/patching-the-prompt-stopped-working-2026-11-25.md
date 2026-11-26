---
type: journal
date: 2026-11-25
tags: [journal, chat-quality, prompt, evals, openrouter, lessons]
summary: "A day of prompt patches moved quality 2.41 to 2.91 and then stalled: what code enforces holds, what the prompt asks slips; measure with one fixed score sheet."
failed:
  - "Tried about 25 prompt rules in one day for judgment behaviours (readings as fact, plain words, re-asking); failed because a small model follows only part of a 48k-character prompt, and each tester round found a different rule dropped"
  - "Tried putting a tester's own scenario wording into the prompt as an example; failed because the model copied the sentence and all three styles opened with it"
  - "Tried an always-on second model call to rewrite every reply (CHECK-1); failed because it added about 5.5 s, timed out at 8 s on 63% of turns in a full run, and let literary lines through"
  - "Tried stronger chat models as a drop-in; failed because Kimi K3.1 Pro broke the strict reply schema on 37 of 47 turns, DeepSeek V4 Pro timed out on 12 of 60 at the 45 s deadline, and Claude and OpenAI models have no zero-retention host under our routing (404)"
  - "Tried a zero-retention ping with routing {zdr: true, sort: latency}; failed with 404 even for the current model, because the hosts must be named in `only` (sail-research, deepinfra)"
  - "Tried two judge rubrics sharing one criterion enum; failed because the judge scored all eighteen criteria, so the run reported as 2.97 was not comparable with 2.41 (like for like 2.91)"
  - "Tried reading a slow judge as an effort problem; failed because the account's OpenRouter credit was spent (402 weight_exceeds_budget) and chat calls began failing minutes later"
  - "Tried `$VAR` holding several CLI options in zsh; failed because zsh does not split an unquoted variable into words"
---

# Patching the prompt stopped working (2026-11-25)

What happened across one day of client and tester feedback on `fix/audit-remediation`, and what to do differently.
Stack facts are in `.claude/BACKEND.md`; decisions are in `backend/PORT-STATUS.md` ("Decisions in force").

## What the numbers said

- Same 16 scenarios, same ten criteria: 2.41 in the morning, 2.91 on prompt v15. Real, and then it stalled.
- A count over the v15 run's 38 judged conversations (247 scores of 2 or less) ranked the causes: readings stated as
  fact (26 conversations), repetition (25: Mani's own line 21, their words handed back 18, re-asking only 6), blunt or
  missing acknowledgment (15, 13 of them Directive), stylised wording (14), help refused or replaced by a framework
  (11), belief-fishing questions (10).
- The six crisis scenarios carried 57 of the 247 low scores, most for the pause and the fixed help lines: the judge was
  marking down what the product fixes. The score sheet now says so (`judge.STANDARD`).

## What holds and what slips

- A rule code enforces holds every time: forbidden words in every form, one question, drafts kept whole, verdict
  lines, Mani's own repeated lines, he or she never given.
- A rule only the prompt states holds some of the time. Adding a rule often traded one failure for another: banning
  "How does that make you feel?" produced "what happens in you?"; "say back a few of their words" produced echoing;
  "give two or three options" produced solutions before understanding; "I can't decide is not a want" blocked the
  ABCDE offer the notes had planned.
- An example in the prompt is copied more reliably than a rule is followed. Never take one from a test scenario.

## What to do next time

- Count causes on a full run before changing anything, and fix the largest in code where a pattern can be named.
- Change the prompt in one measured step (the consolidated rewrite waits in the scratchpad for its A/B), not in
  patches between tester messages.
- Keep one score sheet, and judge the saved baseline again when it changes (`regress.py --rejudge`).
- Keep the holdout scenarios out of the tuning loop (`evals/regression/holdout.json`).
- Watch the credit: a full run with the judge costs about 5 to 8 dollars, and the day spent about 17.
- A migration that drops a column the live code still reads must not sit in `supabase/migrations` before the deploy
  (`supabase db push` applies everything): see `docs/release/2026-11-25-release-checklist.md`.

Related: [[provider-tail-latency-2026-10-14]], [[three-styles-read-the-same-2026-10-22]].
