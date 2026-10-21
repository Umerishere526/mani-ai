---
type: journal
date: 2026-10-21
tags: [journal, latency, streaming, reasoning, lessons]
---

# `504 llm_timeout` again: the tail is thinking time, so the call is streamed and cut (2026-10-21)

muhammad kept getting `504 llm_timeout` a week after [[provider-tail-latency-2026-10-14]]. That fix holds: every call
in the last 24 hours was served by OpenAI, none by a slow Azure region.

## What the call log said (`admin.llm_calls`, last 24 h, 161 chat calls)

| | now (effort `medium`) | 2026-10-14 (effort `low`) |
|---|---|---|
| output tokens per call | 642 on average, 453 of them hidden reasoning | about 300 |
| p50 / p90 / max | 9.7 s / 16 s / 27 s | 6.2 s / 12 s / 28 s at p99 |
| timeouts at the 30 s deadline | 3 (1.9 percent) | 2 in 3 days |

The visible reply and its JSON are about 190 tokens. The slowest calls are the ones that think longest: OpenRouter
reported the first token of the 27 s call at 22 s. The working tree's `mani_base.md` had `reasoning_effort: medium`
(the committed file and the 2026-10-12 decision say `low`); muhammad kept it on purpose, see
[[one-call-turns-at-low-effort-2026-10-12]] for why `low` was chosen.

## What changed

The chat call streams (`langchain-openai` `astream` with its own `stream_chunk_timeout`, 15 s), and a call that sends
nothing for that long is cut and tried once more, the cut attempt recorded as its own `timeout` row. The flat 30 s
deadline stays as the cap on one attempt. Verified offline with a mock SSE server before building: the structured
stream yields raw (with the id and usage), parsing_error and parsed, so `chain.usage_from` and `generation_id_from`
needed no change.

## Lessons

- A deadline around a blocking call can only fail a slow call. When the slowness is thinking before the first token,
  the useful limit is on the silence, not the total.
- Streaming does not make a thinking-heavy call faster. It turns an error into a slow success on about 2 to 4 percent
  of turns, and a cut attempt is probably billed. If timeouts stay above about 1 percent the lever is effort, not
  another timeout.
- The stream path emits a Pydantic serializer warning from inside `langchain-openai` (`chunk.model_dump()` on a chunk
  whose `parsed` it types as None). The reply is intact. `pytest.ini` ignores that one message; the cause is upstream.

To watch (needs muhammad's chat turns): `timeout` rows near 15 s, usage and `generation_id` still on `ok` rows of
streamed calls, and the share of turns that end in `LLM_TIMEOUT`.
