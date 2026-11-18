---
type: journal
date: 2026-11-17
tags: [journal, model, prompt, cost, latency, spike]
summary: "Flat replies came from the model, not the prompt: prompt changes stopped helping while bare API models wrote short."
failed:
  - "Tried prompt changes to close the gap with ChatGPT; failed because they stopped moving it and the model was the cause."
---

# Flat replies were the model, not the prompt

On the one-call spike (`spike/one-call-turn`, worktree `mani-ai-spike-a`) muhammad compared Mani with ChatGPT on
the same messages, and ChatGPT read much richer. Several prompt changes closed part of the gap (ideas to explore,
a fair perspective, "I want to highlight", what-if questions, options with reasons, no either-or questions), then
it stopped moving.

## What isolated it

The same two messages through five configs (`scratchpad/isolate.py`):

- Our prompt made `gpt-6-luna` *longer*, not flatter. Every API reasoning model with a bare prompt, the flagship
  `gpt-6-astra` included, wrote 23 to 54 words.
- ChatGPT is served by `openai/gpt-chat-latest` (the Instant chat model). With our exact prompt and JSON reply it
  wrote ChatGPT's replies. So the gap was the model all along.
- JSON against plain text made no difference to quality, length or layout. `verbosity: high` changed nothing.
- No prompt change got lists or bold out of any API model; muhammad dropped the layout, kept the phrasing.

## The models, through the real stack, our prompt, seven scenarios (safety and frameworks)

| Model | Rules | Median / p90 | Per turn |
|---|---|---|---|
| `gpt-chat-latest` | clean | 5.2 s | $0.019 measured |
| `claude-sonnet-5.5`, reasoning low, cached | clean, no failed calls in 49 | 9.6 / 14.5 s | about $0.013 |
| `minimax-m3.1-flash`, low, ZDR hosts | wrote a template after a declined offer; offered while safety was open | 5.1 / 16.3 s | about $0.0005 |
| `deepseek-v4.1-flash`, none, ZDR hosts | crammed stages; a provider error left the chest-pain turn unanswered | 8.6 / 11.7 s | about $0.001 |
| `claude-haiku-5.5`, none | never offered a framework; coached instead | 16.8 / 23.7 s | about $0.0014 |

muhammad chose Sonnet 5.5 alone (2026-11-17), after `gpt-chat-latest` was too expensive (40x Luna).

## Gotchas found on the way

- Anthropic models cache nothing unless the request carries a top-level `cache_control`; without it Haiku showed
  0 cached tokens and Sonnet would cost more than the chat model. `chain.request_body` sets it on the spike.
- Settings' default provider list allows only OpenAI, so any other model 404s until routing names its provider.
- `gpt-6.1-sol` rejects a non-strict JSON schema; the backend's own client already sends a strict one.
- The `chat-latest` alias changes whenever OpenAI updates ChatGPT: pin a dated version if it is ever used.
- When code refuses an action the model took (an offer while safety is open), the reply still says it. Code
  should state what is allowed in the facts before the call, not overrule the reply after it.
- A call that fails leaves the person with an error, safety turn or not: every turn needs a fallback.

Related: [[transcript-is-the-memory-2026-10-13]], [[one-call-turns-at-low-effort-2026-10-12]],
[[a-session-not-a-set-of-rules-2026-10-29]].
