---
type: journal
date: 2026-11-25
apps: [backend]
tags: [journal, safety, crisis, pause, client]
summary: "A new conversation no longer asks about a past pause; only the conversation the pause began in reads the first message back."
failed:
  - "Tried asking about a pause in every conversation, as the opening of a new one; failed because the client opened a new chat and was asked about a pause she never had, then told what Mani had been worried about"
---
2026-11-25

Lolly, testing Directive on a shared test account, opened a new chat and got `greeting.RETURN_OPENER` in place of the
style's opener. She said she was never paused. Mani then repeated the pause's reason from the facts ("you being on your
own and scared you might hurt yourself"). Signing out and back in changed nothing, because the question followed the
account into every new conversation until someone answered it. Her words: "I do not want my chat's to start this way.
Get rid of it." muhammad decided the same day (R179 supersedes R103, which the client had never been told about).

## What changed

- The turn context loads only its own conversation's latest pause that has run out (`threads.load_turn_context`,
  `cp.thread_id = t.id`). So `pause.return_check` fires only in the conversation the pause began in, and nothing else
  needs a guard.
- Deleted: `greeting.RETURN_OPENER` and `openers()`, `pauses.owed`, `pauses.mark_checked`, `pauses.clear_checked`,
  `rewind.note_checked`, `Pause.checked_at`, and the cross-conversation settling in `worry.standing` (`Standing.reset`).
  Also the `return-check` suite conversation and the `SETUPS` hook in `evals/check_suite.py`.
- Kept: the question, `RETURN_CHECK_REPLY` and `RETURN_DANGER_REPLY` on the first message back in the paused
  conversation, the answering phase, the 423 gate, and the END_CHECK after a framework.

## Why the past failures no longer apply

- 2026-11-13, "loading only the conversation's own pause hid a later pause from one that answered its own"
  ([[crisis-pause-fires-on-refusal-2026-11-13]]). Hiding another conversation's pause is now the intent.
- 2026-11-19, "honouring `checked_at` in the paused conversation alone leaves it at danger"
  ([[crisis-pause-one-rule-and-the-worry-forgets-its-kind-2026-11-19]]). Nothing answers elsewhere now. The paused
  conversation always asks its own question, and its own answer moves its state.

## Left

- `chat_pauses.checked_at` and the UPDATE policy and grant that exist only for it are unused. Dropping them needs a
  migration that muhammad approves (`PORT-STATUS.md`, Open engineering).
- `recent_crisis` stays. It adds the "go gently; never mention it" line when another conversation had a crisis in the
  last 30 days, so new chats are still not fully separate. The line gives no reason, so the model cannot repeat
  details as it did here, but whether it ever brings the crisis up has not been measured against the model.
