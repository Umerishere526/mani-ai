---
type: journal
date: 2026-11-05
tags: [journal, latency, openrouter, prompt-cache, vercel, lessons]
---

# Where a chat turn's wait goes, and what the cache and Vercel were doing (2026-11-05)

2026-11-05. Read-only report on production, 2026-11-01 to 05: `backend/docs/latency-report-2026-11-05.md`. 154 chat
calls, p50 9.8 s, p90 19.6 s. The decisions taken from it are in `backend/PORT-STATUS.md`, "Decisions in force"
(priority tier for chat, body check-in at `low`, 45 s deadline, sticky keys, text streaming deferred).

## Thinking is the wait

- Before the first token: p50 6.0 s, about 75% of a chat call (1,057 of 1,612 s summed). Reasoning is 65% of output
  tokens at `medium`. Latency follows output tokens almost exactly (r = 0.94, about 12.4 ms a token).
- After the first token: p50 1.6 s. That is why streaming the text to the person was deferred: it would show the
  reply about 1.6 s sooner.
- Our own overhead around the call: p50 0.33 s. The platform is not the chat's problem.
- The levers that touch the 75% are fewer thinking tokens (effort) and a faster endpoint (`openai/fast`, 109 against 65
  tokens a second, double price). Both were taken, effort only for the body check-in.

## A schema change resets the prompt cache, but costs money, not wait

- The first call after a change of reply schema had 0 cached tokens in 12 of 15 cases, against 4 of 79 when the
  schema stayed the same. Cleanest case: chatting → chatting with `may_move`, where the system prompt and history are
  identical and only `response_format` differs.
- Chat and `understanding` keep two separate caches; each caches from its own previous call. That fits the schema
  sitting at the start of the cached prefix.
- Uncached input did not lengthen the wait (r = −0.29 with latency). Fixing it is about price, not speed.

## Unexplained: turn 2 is almost never cached

- Turn 2 was cached in 1 of 8 threads, though turn 1 had the same schema and system prompt 8 to 121 s earlier. Turn 3
  always cached turn 1's whole input.
- Hypothesis: no `prompt_cache_key` and no `session_id` were sent, so OpenAI's routing put turn 2 on a machine that
  did not yet hold turn 1's prefix, and OpenRouter pins a conversation only after a cache hit when no `session_id` is
  sent. The 2026-11-05 change sends both (`<thread_id>:<purpose>`), so it tests this: if turn 2's ratio rises after
  deploy, the hypothesis holds. If it does not, `prompt_cache_key` is probably not reaching OpenAI: OpenRouter's docs
  describe it only as a sticky key.

## Unexplained: the cached count stays fixed during stages and body

- In `in_stages` the cached count sat at 11,407 or 10,815 for the whole run, in `body` at 9,692 or 9,100, while input
  grew, so 3 to 6k tokens were re-read uncached every turn. In `chatting` it grows with the conversation.
- So something placed after the first ~11.4k tokens changes on every stage or body turn. Not located. A first place to
  look: what `compose_framework` / `compose_moment` put after `voice` and before the history, and whether `[ctx]` or a
  layer that changes each turn sits before the transcript.

## Vercel suspends `fire_and_forget`

- Production is Vercel Hobby functions (iad1); the database is in ca-central-1. `mani/background.py` uses
  `asyncio.create_task`, which Vercel does not wait for. `waitUntil` exists only for Node and Edge.
- Evidence: 15 of 49 `understanding` calls timed out at 61 to 335 s against a 60 s wait; background calls spent p50
  6.3 s between OpenRouter finishing and our row (chat: 0.33 s); both memory-fold retries never wrote a row. So the
  picture and memory are being lost for real people.
- muhammad kept Vercel for now (2026-11-05). The fix is a container host near ca-central-1 or a queue; recorded in
  PORT-STATUS "Open engineering". Any background latency read from `admin.llm_calls` on Vercel includes time the
  process was suspended. It is not a measure of the model.

Related: [[streamed-chat-call-cut-and-retried-2026-10-21]], [[provider-tail-latency-2026-10-14]],
[[504s-follow-what-the-reply-writes-before-text-2026-11-03]].
