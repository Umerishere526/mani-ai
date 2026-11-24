---
type: journal
date: 2026-11-19
apps: [backend]
tags: [journal, summaries, catch-up, bugs]
summary: "A code review of backend/mani found three summary and catch-up bugs unrelated to the pause work; none is fixed yet."
---
2026-11-19

# Summary batch cap and catch-up bugs, found in a review, not fixed

Found by `/code-review` over `backend/mani/`, `backend/supabase/` and `chat-tester/` on branch
`feat/crisis-paused-rework`, while looking for gaps in the crisis pause. Unrelated to the pause, so recorded here and
left alone for that branch. I read each place in the code; nothing was run.

## Bugs

- **A long thread is marked fully summarized after one batch** (`summarize.update`). It reads at most `BATCH` (200)
  messages after the checkpoint, then writes `summarized_message_count=thread.message_count` with
  `summarized_through_message_id` set to the 200th message. A thread with 500 messages and no summary looks caught up
  after one run, so messages 201 onward are in no summary once they leave the model's window. Likely fix: record the
  count of messages actually folded in, or loop until the checkpoint reaches the last message.
- **Catch-up counts failures as done** (`summarize.reconcile_due`). `update_quietly` swallows every exception, and
  `done += 1` runs for every row, so `catch_up` reports `summaries: N` while nothing was summarized. Likely fix:
  `update_quietly` returns whether it worked, and only those are counted.
- **Failing threads can fill the catch-up queue** (`summaries.due_for_summary`, `catch_up.LIMIT = 10`). It orders by
  `last_message_at` ascending, so ten threads whose summary keeps failing take every slot of each run until they age
  out of `CATCH_UP_FOR` (1 day), and newer due threads are not reached. Not reproduced; depends on the first fix
  above, since a capped batch is one way a thread keeps being due.

## Other small findings from the same review

Unused `answered` in `turn._apply` and unused `field` import in `db/threads.py` (ruff F841, F401); the chat-tester
README line 131 and the `client.follow_up` docstring still describe the removed memory panel and reading; the
tester's 401 handler refreshes the session with no lock, so the main thread and the follow-up thread can refresh with
the same refresh token. The two pause gaps (stale `DANGER_ABOUT` in `judged.judge`, `return_check` ignoring
`checked_at` on the paused-thread branch) belong to the pause rework, see [[crisis-next-message-decides-and-the-pause-follows-them-2026-11-16]].
