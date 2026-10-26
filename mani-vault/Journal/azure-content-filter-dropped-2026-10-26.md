---
type: journal
date: 2026-10-26
tags: [journal, openrouter, routing, content-filter, lessons]
---

# Azure's content filter stopped ordinary replies, so chat goes to OpenAI only (2026-10-26)

muhammad got `502 llm_unavailable` five times in a row on one message in a Directive conversation about an
inept boss and whether to leave the job. The log said `Could not parse response content as the request was
rejected by the content filter`.

## What the evidence showed

- `scripts/llm_call_providers.py`: every call since the database reset, 28 of 28, was served by Azure. The
  10 failures were 5 sends of one message, 2 attempts each, every one stopped after about 13 tokens with
  `native_finish_reason: content_filter`.
- The thread had nothing harmful in it. Azure's default filter (hate, sexual, violence, self-harm at medium)
  belongs to OpenRouter's Azure deployment; we cannot configure it.
- A filtered reply is a finish reason, not an HTTP error, so OpenRouter's `allow_fallbacks` never moved the
  call to OpenAI, and our one schema retry went back to Azure, the fastest endpoint at the time.
- The message was lost each time, because `complete()` raises before the turn writes anything, and the
  error told them to "try again", which could not work.

## Decision

Calls go only to `openai` (muhammad, 2026-10-26). For a companion people bring distress to, a provider
filter that turns a hard moment into a 502 is a correctness and safety failure, not a latency trade.

## History

This was already listed in `docs/superpowers/plans/chat-prompt-restructure.md` ("The content filter crashes
a turn") as a decision for muhammad, and never taken. The 2026-10-14 routing choice
([[provider-tail-latency-2026-10-14]]) weighed speed and data protection, not the filter.

## Still open

- The typed message is lost whenever a call fails.
- A filtered reply is retried even though the retry is very likely to be filtered too.
- Not verified that OpenAI answers the exact message; it was never stored. Needs muhammad's yes for a live call.
