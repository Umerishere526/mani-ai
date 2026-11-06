---
type: journal
date: 2026-11-05
tags: [journal, backend, database, scaling, turn]
---

# Why the turn was split into read, think, write (2026-11-05)

**The problem.** A chat turn opened its transaction in the route (`UserConn`) and held it across the model call,
6 to 30 s (the chat deadline is 45 s). Inside that call `client._record` took a second connection for the cost row.
With 10 connections per instance and no acquire timeout, 10 turns in flight on one instance hung it: every turn held
one connection and waited on another. Each instance also opened its own pool against the session pooler, so
connections grew with instances. For ~100 beta testers now and 500 at once later, this was the first thing to break.

**Decision (muhammad).** No database connection is held during a model call. Stated in PORT-STATUS, "Decisions in
force", with its tests.

**How, and why that way.** `orchestrator.send` is 1,375 lines with about 20 locals flowing from the pre-model part
into 250 lines after it. Splitting it into `prepare()` and `finish()` would have been a 600-line refactor, and
`finish()` would still have had to re-read thread state, or it writes back the understanding it read before the
model call over a reading that landed meanwhile (the turn lock's guarantee). `chat/runner.py` replays the steps
instead:

- The read runs `send` in a transaction that rolls back, and stops at the model call (`runner.Model` raises once it
  has recorded the request and the thread's version).
- The model is called holding nothing.
- The write runs `send` again under `_lock_thread`, from the thread as it is then, and answers the model call with
  the reply. A moved version is a 409.

The same replay gives the edit route its promise for free: undo plus send in both passes, so a failure anywhere
leaves the original exchange.

**What was lost, and the fix.** The database lock on `client_message_id` used to span the model call, so a
mid-call retry paid nothing. It cannot span it any more. An in-process lock per message id (`runner._one_at_a_time`)
restores that within an instance. Across instances a duplicate pays once more, and the write still stores one turn.

**Watch for.**

- Anything in `send` before the model call runs twice. Keep it deterministic and free of side effects outside the
  transaction: no network calls, and no fire-and-forget.
- The version is message count plus newest message id. A change that should invalidate a reply without adding or
  removing a message needs to be in it, or be re-read by the write (as understanding is).
- The minute limit counts stored messages, so a person firing many requests at once on different threads passes it
  until one lands. The model-call slots bound that.

**The load test found the same class three more times.** At 500 people every send failed `busy`. All five pooled
backends sat `idle in transaction` right after `rewind.save`, for up to 23 s. The read pass called `cache.load()`, which
reloads a stale cache on a second connection under one process-wide lock. The lock holder waited 5 s for a sixth
connection that never came, then the next waiter did the same, each holding its own connection all the while. The TTL
is 1 s in development, so locally it fired constantly; in production (300 s) it would stall every instance once every
five minutes. Summaries and the memory fold held a connection across their own model calls too. The fix was a rule,
not three patches: `pool` refuses a second connection, a model call or a cache read to a task that holds one, so a
test fails where production would stall. It tracks the holding task, not a context variable, because a background task
started during a request copies the request's context. The guard then caught a fourth nested acquire, in a test helper.

Related: [[latency-where-the-wait-goes-2026-11-05]], [[provider-tail-latency-2026-10-14]].

**Found on the way, not fixed (unrelated to this change).**

- `scripts/test_db.sh` stops in `tests/sql/test_grants.sql` on "foreign keys with no index:
  admin.turn_traces(llm_call_id)". Migration 027 added the foreign key without an index. It fails the same way
  without this change, so the one assertion after it in that file has not run since 027.
- The log sweep for model or user text is listed in muhammad's summary for this change. Only audit #3 (the crisis
  reason) and #5 (pydantic's `input_value=`) were fixed.
