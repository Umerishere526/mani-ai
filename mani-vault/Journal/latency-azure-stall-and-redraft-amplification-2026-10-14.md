---
type: journal
date: 2026-10-14
tags: [journal, latency, openrouter, redraft, measured]
---

# Latency: an Azure stall multiplied by redrafts (2026-10-14)

Chat turns went from ~6 s (10-12) to 30-100 s with timeouts (10-14). Same model, same token sizes.

- **Upstream.** The real prompt pinned to Azure timed out or returned 408 on 2 of 2 replays; pinned to
  OpenAI, 2 of 2 completed every turn at ~9 s a turn. Degradation started around 21:00 PDT on 10-13.
  OpenRouter fallbacks never help a stall: they fire on an error, not on a slow answer.
- **Amplification.** On main ~3% of chat calls are redrafts; on the abcde-revamp working tree ~60%, so a
  turn is ~2.6 calls. A healthy provider hides it, a slow one multiplies it.
- **The SDK timeout is per read, not per call.** A call ran 83 s under a 60 s timeout. Now bounded by
  `asyncio.timeout` in `client.complete`.

Fixes: total per-call timeout, redraft fallback to the first draft, `REDRAFT_BUDGET_MS`, local `.env`
provider order `["openai","azure"]` (code default untouched: production routing is a data decision).

Colleague without the problem: same code default routes Azure first, so the difference is most likely
which branch he runs (main: one call a turn) or his `.env` order. Unverified.
