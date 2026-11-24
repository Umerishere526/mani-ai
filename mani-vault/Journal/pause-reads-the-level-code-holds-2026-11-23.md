---
type: journal
date: 2026-11-23
apps: [backend, chat-tester]
tags: [journal, safety, crisis, pause]
summary: "Two pause gaps on feat/crisis-paused-rework: a body refusal checked the model's level instead of the level code raised it to, and a danger answer after a pause waited for still_there; also a 30 s pause and a readable chat behind the closed pop-up, for testing."
---
2026-11-23

# The pause reads the level code holds

Found while muhammad asked what in the crisis flow could be missed, on `feat/crisis-paused-rework`. Both proven by
running `worry.step` directly before the fix, then by test rows that fail on the old rule.

- **Body refusal.** `safety.danger_of` raises a body symptom the model judged unsure to danger (chest pain held at
  unsure in 7 of 30 runs, [[body-emergency-every-time-2026-11-18]]), and the call-now line went out, but the pause
  check read the model's raw level. "I'm not calling an ambulance, it's still hurting" judged unsure never paused.
  `worry.step` now computes the held level once and every check reads it.
- **Answer after a pause.** "I took more pills" in answer to how things are paused only if the read also set
  `still_there`; otherwise the next message paused. muhammad chose that a danger read pauses too.

Lesson: when code overrides the model's judgment, every later rule must read the overridden value, not the raw one.
The same shape as [[unsure-never-pauses-2026-11-20]], the other way round.

Also on this branch the same day, at muhammad's ask: the pause is 30 seconds (`CRISIS_PAUSE_SECONDS`, he keeps it for
now and changes it in another branch if needed), and closing the chat-tester's pop-up with its cross leaves the
conversation readable with nothing that sends. A local Supabase stack `mani_pause` (ports 5744x, outside the repo in
`../mani-ai-pause-test`) signs tokens with ES256, so its backend checks them by JWKS, not the shared secret.
