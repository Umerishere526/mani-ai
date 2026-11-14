---
type: journal
date: 2026-11-13
apps: [backend, chat-tester]
tags: [journal, threads, api, lessons]
---

# A conversation is created by its first message (2026-11-13)

2026-11-13. History, not rules. The decision in force is "A conversation exists only once the person sends it their
first message" in `backend/PORT-STATUS.md`.

- What it was: loading the page (`POST /v1/threads/current`, which created a thread when the account had none) and New
  conversation (`POST /v1/threads`, `create_or_reuse`) each wrote a thread and its greeting before anyone spoke. A
  style tap was stored as their message plus the opener, so a tap alone made a thread count as one they spoke in: it
  was never reused, it was folded into memory with a paid call, and it counted toward the rate limit.
- The rows stayed the same (greeting, tap, opener, then the turn), now written in one request with the first message.
  Storing only the style on the thread would have been a cleaner transcript, and it would have moved every message
  count, the cadence floors, rewind's opening guard, the tester's opening view and many tests.
- "Good to see you again" has to count only conversations they wrote in: counting greeting-only threads greeted a
  first-time person as returning. Open for muhammad: deleted conversations still count.
- A retried first message has two traps. A retry arriving while the first try waits on the model finds no
  conversation yet and makes a second; `runner.start` waits on the first in process (another instance can still make a
  second, noted for the whole-branch review). And the chat-tester must keep the draft's `client_message_id` across
  attempts, or a timeout and a resend make a second conversation.
- Greeting-only threads already in a database are hidden from every list (`threads.WRITTEN_IN`), not deleted.
- The memory fold stays on the New conversation click, so the first reply still sees what earlier chats taught, but
  with no thread yet there is nothing to keep out of it: the app posts `/v1/threads/memory-fold`, which takes no thread
  and folds only conversations last written before the request arrived. `memory_fold_pending` is gone from the start
  response.

Related: [[crisis-pause-audit-findings-2026-11-13]] (built first because "no new conversation during a pause" is
easiest to enforce once a conversation exists only with a message).
