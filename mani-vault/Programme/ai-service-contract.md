# AI Service Contract (v1 draft)

Contract between **backend** (Node/Next.js) and **ai-service** (FastAPI).

Decisions that shape this contract are recorded in [[2026-09-14-architecture-decisions]].
Background on the split itself: [[2026-09-09-fast-api-infra-from-scratch]].

## Principles

1. **ai-service is stateless.** No user identity, no session, no writes. Read-only access to the
   prompt and framework tables is permitted — that is configuration, not state.
2. **Backend owns all persistence.** Every DB write (messages, technique tracking, crisis flags,
   style history, titles) happens in the backend after ai-service returns.
3. **Backend owns content retries; ai-service owns transport.** ai-service returns one
   completion per call and never retries for content quality. Its only internal retry is a
   single attempt on `schema_validation_failed` — a malformed structured response, which the
   backend cannot fix. Everything else the backend handles by post-processing, not by asking
   again. See "Retries" below; this is where the current implementation burns tokens.
4. **The response schema is the integration surface.** Fields below are consumed by concrete
   backend logic; dropping one silently breaks a feature.

---

## `POST /v1/chat`

### Request

```jsonc
{
  "message": "string",                    // the user's new message

  "history": [                            // prior turns, oldest first
    { "role": "user" | "assistant", "content": "string" }
  ],

  "context": {
    "nickname": "string | null",          // from user profile
    "topics": ["string"],                 // user's selected topics
    "summary": "string | null",           // rolling thread summary (memory system)

    "techniques_offered": ["string"],     // for frequency limiting
    "techniques_tried": [                 // from ThreadSummary.techniquesTried
      { "name": "string", "helpful": true, "context": "string | null" }
    ],

    "active_technique": {                 // null when no technique in progress
      "technique": "string",              // e.g. "thought_reframing" | "abcde"
      "step": "string"                    // e.g. "offering" | "surface" | "ground"
    },

    "recent_styles": [                    // last N, for variety enforcement
      { "shape": "string", "voice": "string | null" }
    ],

    "should_generate_title": false        // true after 2 exchanges
  },

  "options": {
    "max_tokens": 2048,
    "temperature": 1.0
  }
}
```

**Note on `context`:** the backend assembles this from the DB. ai-service turns it into prompt
text however it likes — the backend does not care about prompt structure. That is the point of
the boundary.

**Not in v1, planned for v2:** `support_style` (the user's onboarding choice of supportive /
reflective / direct, captured today and reaching nothing) and framework selection once the
registry exists.

### Response

```jsonc
{
  "text": "string",                       // REQUIRED, non-empty. The user-facing reply.

  "prompts": [                            // null or 0-3 items. Tappable suggestion buttons.
    {
      "label": "string",                  // REQUIRED. User voice: "Yes, let's try it"
      "technique": "string | null",       // set ONLY when initially offering a technique
      "library": "string | null",         // library section id; navigates instead of chatting
      "decline": true                     // marks the offered technique as declined
    }
  ],

  "title": "string | null",               // <= 50 chars. Only when should_generate_title was true.

  "crisis": {                             // null when no crisis signal
    "reason": "string"
  },

  "state": {                              // null when no active technique
    "technique": "string",
    "step": "string",
    "accepted": true                      // user accepted an offer in free text
  },

  "style": {                              // null if no mirroring
    "shape": "string",
    "voice": "string | null"
  },

  "reasoning": "string | null",           // debug only; backend logs it, never sends to client

  "usage": {                              // NEW — required for cost tracking
    "input_tokens": 0,
    "output_tokens": 0,
    "cached_input_tokens": 0,
    "upstream_calls": 1                   // how many provider calls this request consumed
  }
}
```

### Why each field exists

Do not drop these — each drives a specific backend DB write:

| Field       | Backend consumer                                              |
| ----------- | ------------------------------------------------------------- |
| `text`      | `messagesDb.createPair()` — the stored assistant message       |
| `prompts`   | Stored as `promptOptions`; `technique` feeds `addTechniquesOffered()` |
| `title`     | `threadsDb.updateTitle()`                                      |
| `crisis`    | `threadsDb.markCrisis()` + crisis UI panel on mobile           |
| `state`     | `threadsDb.updateTechniqueTracking()` — drives phase progression |
| `style`     | `threadsDb.appendResponseStyle()` — variety tracking           |
| `usage`     | Cost monitoring (does not exist today; add it)                 |

### Errors

```jsonc
{ "error": { "code": "string", "message": "string", "retryable": true } }
```

Codes: `provider_error` (502), `provider_timeout` (504), `invalid_request` (400),
`schema_validation_failed` (422) — the model returned unparseable structured output.

---

## `POST /v1/summarize`

Thread summarization moves here (open question 2, resolved). Today `summary.ts` hardcodes
`gpt-4o-mini` and reads `process.env.OPENAI_API_KEY` directly, bypassing `admin.providers`,
`admin.prompts`, and the LLM service entirely — moving it unifies that. Note that the seeded
`summarization` and `title_generation` prompts are read by no code at all today; wire them as
part of this move, or delete them.

## `POST /v1/cache/invalidate`

Called by the admin portal after a prompt is published. Without it an edit takes up to the cache
TTL to appear, which makes the prompt-iteration loop painful across a service boundary. See
[[2026-09-14-architecture-decisions]] #9.

## `GET /health`

`200 {"status":"ok"}`. Must not call a provider.

---

## Retries — the expensive part

The current implementation regenerates the whole completion on **six** separate validation
failures, each resending the full ~9K-token system prompt, on top of `maxRetries: 2` in the
AI SDK. Worst case is ~21 provider calls for one user message. Measured cost: ~570K tokens
across 3 messages.

The six triggers, at their `llmService.chat(...)` call sites in `messages.ts`:

| Line | Trigger                                          |
| ---- | ------------------------------------------------ |
| 781  | Duplicate techniques offered                     |
| 815  | Script metadata leaked from technique examples    |
| 994  | Technique phase-skipping                         |
| 1031 | Technique skipped `offering` phase                |
| 1091 | Repeated prompt label                            |
| 1181 | Forbidden words present                          |

(994 and 1031 are mutually exclusive, so the ceiling is six calls per turn, not seven.)

Every one is a **deterministic post-check on the output**. None require a full regeneration:

- Duplicate techniques / repeated prompts → dedupe the array in code.
- Script leakage / forbidden words → strip or filter in code.
- Phase-skipping / missing `offering` → correct `state` in code, or reject that field only.

**Recommendation for v1:** ai-service performs at most **one** regeneration, and only for
`schema_validation_failed`. All content-quality checks move to deterministic backend
post-processing. Set the provider SDK's internal retry to 0 and handle transport retries
explicitly with backoff.

**Do this in TypeScript before the port**, so the cheap version is what gets moved rather than
the expensive one.

Also enable **prompt caching** on the static prompt prefix (~9K tokens, identical every call).
That alone is a 60–90% cut on input tokens.

---

## Open questions

1. **Crisis detection ownership.** Currently model-driven via the `crisis` field. If ai-service
   changes models, crisis-detection behavior changes with it. Decide explicitly whether this
   stays model-driven, moves to a deterministic classifier, or both (belt and braces). This is
   the one field where a silent regression has real user consequences — it must fail closed.
   Recommendation: both. Note the target state too — crisis as a **tool call** rather than a
   response field, because a field can be silently dropped when a regeneration replaces the
   response object (H3, live today) whereas a tool call is an event that already happened.

2. ~~**Summarization.**~~ Resolved — moves to ai-service as `POST /v1/summarize`.

3. ~~**Streaming.**~~ Resolved — not in v1. See [[2026-09-14-architecture-decisions]] #5.

4. ~~**Provider config.**~~ Resolved — ai-service holds its own credentials in env; the backend
   never sees them. Model *config* stays in the database and stays admin-editable; secrets do
   not. Removes `decrypt()` from the request path and fixes M5.
