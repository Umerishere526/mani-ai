---
type: journal
date: 2026-10-14
tags: [journal, latency, openrouter, routing, lessons]
---
> Superseded 2026-10-21 (the deadline that was never retried, and "next if slow turns persist") - see [[streamed-chat-call-cut-and-retried-2026-10-21]]

# Provider tail latency, and why the pinned order was wrong (2026-10-14)

muhammad kept getting `504 llm_timeout`. The calls themselves were steady: about 7k tokens in and 300 out. The
time they took was not. Our log over 3 days of chat had a p50 of 6.2 s, a p90 of 12 s and a p99 of 28 s, plus
calls of 64 s and 102 s and two timeouts at the 30 s deadline. The prompt was not the cause.

## What OpenRouter's own figures showed (MCP `list-model-endpoints`, last 30 min)

| endpoint | latency p50 / p90 / p99 | throughput p50 / p90 |
|---|---|---|
| `azure` | 8.4 s / 39.6 s / 128.7 s | 30 / 4 |
| `azure/us` | 6.4 s / 30.8 s / 146.7 s | 29 / 6 |
| `azure/eu` | 0.87 s / 1.6 s / 6.3 s | 54 / 40 |
| `openai` | 2.7 s / 10.5 s / 34.7 s | 69 / 34 |
| `openai/flex` | 4.6 s / 20.2 s / 50.3 s | 52 / 28 |
| `openai/fast` | 1.0 s / 4.0 s / 13.3 s | 93 / 48 (double price) |

## Facts from OpenRouter's docs

- A base slug such as `"azure"` matches every region of that provider. Tier endpoints (`openai/flex`,
  `openai/fast`) are never matched by a base slug, so they need explicit opt in.
- An explicit `order` turns off load balancing and sticky routing.
- Fallback happens on an error, never on slowness.
- `sort: "latency"` puts the fastest endpoint first, going by recent figures.
- `preferred_max_latency` and `preferred_min_throughput` are preferences on 5 minute rolling percentiles, and
  never block a request.

## The lesson

`order: ["azure", "openai"]` was carried from the previous system's provider row and never chosen for speed. It
sent turns to whichever Azure region OpenRouter picked inside the pin, however slow that region was at the time.
We now use `only: ["azure", "openai"]` with `sort: "latency"` (muhammad: Azure and OpenAI, never flex).

## The reviewer's correction

Fable 5.1 checked the plan. Our p50 of 6.2 s means most turns were already served by a fast endpoint, because a
call to `azure` global at its p50 would take about 18 s. So the tail is per endpoint and per moment, and the
claim that `azure` global served most of our calls was wrong. We could not prove which endpoint served the slow
calls either, because `admin.llm_calls` had no provider. Every call now records OpenRouter's `generation_id`.
`scripts/llm_call_providers.py` resolves those ids to the endpoint.

## Gotchas

- LangChain keeps OpenRouter's id in `raw.response_metadata["id"]` and drops the top level `provider` field.
  `raw.id` is LangChain's own run id. On a schema failure the id is on `exc.completion.id`.
- A request cut off by our deadline has no id, and is probably still billed. Match it by time on
  openrouter.ai/activity.

## Next if slow turns persist

Use streaming, not hedged requests. A stream carries the id and the provider on its first chunk, and it allows
a first token deadline and one retry that `ignore`s the slow endpoint. A hedge doubles the cost of every turn
past the hedge point, and while the tail was untraced it would have been a guess.

## Not solved here

R2's target (median 4 s, slowest 10 s). A 300 token reply at `azure/eu`'s speed is about 6.5 s, and only
`openai/fast`, at double the price, reaches 4 s. That is a cost decision for muhammad and the client.

Related: [[transcript-is-the-memory-2026-10-13]]
