# FastAPI infra from scratch

Status: scope and protocol decided 2026-09-10, **further decisions 2026-09-14**, nothing
implemented yet.

> **Read [[ai-service-contract]] and [[2026-09-14-architecture-decisions]] alongside this.**
> This note remains the background and the reasoning; the contract is what gets built. Four
> things here have changed: streaming is **not** in v1 (reversing the "effectively required"
> conclusion below), the service is **stateless** with the backend keeping all persistence,
> the OpenRouter key lives in ai-service's **environment** rather than being decrypted and
> passed per request, and the split now sits **fourth** in the order of work rather than first.

Confirmed with muhammad:

- **Scope**: the Python/FastAPI service owns the AI/agent layer only. Next.js keeps the mobile-facing tRPC API, Supabase, auth, and the admin portal, and remains the only front door for mobile and admin. FastAPI is a private internal service that Next.js calls. Moving the whole mobile-facing API to Python was considered and rejected — that is a full backend rewrite (loses the `packages/api` shared contract, tRPC end-to-end inference, the server-rendered admin portal, and existing test suites) and should not happen as a side effect of wanting Python for the agent.
- **Protocols**: tRPC stays on mobile ↔ Next.js (TypeScript both ends, already built). REST/JSON on Next.js ↔ FastAPI. tRPC was never viable on that leg — it requires TypeScript on both ends. *(2026-09-14: plain request/response REST. SSE is out of v1 — no streaming.)*
- **Driver**: tool calling and growth into an agent — see the driver section below for the assessment of that reasoning, including which parts of it hold up.

Still open: only the hosting platform choice and whether `AI_DEBUG_MODE` reasoning output survives the split. Everything else in the questions at the end of this note is now resolved — see [[2026-09-14-architecture-decisions]] and [[ai-service-contract]].

## Current state (recap, verified in code)

- `apps/backend` is a single Next.js app. It hosts the tRPC API mobile talks to, the admin portal, Supabase access, and the LLM call itself.
- The chat LLM call lives in `apps/backend/src/services/llm.ts` and uses the Vercel AI SDK's `generateObject` (structured JSON output), not free-form tool-calling. See lines 196-204 for the call, lines 25-115 for the output schema.
- There is no function/tool-calling today. "Recommending an exercise" is just the model filling in a `prompts[].library` field in its structured JSON response — a UI-navigation hint the mobile client reads, not an invocation of any service.
- System prompts are markdown files in `apps/backend/prompts/`, seeded into the DB (`pnpm db:seed`), and composed at request time in `composeSystemPrompt` (see `apps/backend/src/services/prompts.ts`).
- The exercises feature (audio library, completions) is a fully separate CRUD path: `packages/api/src/routers/exercises.ts` → `apps/backend/src/services/exercises.ts` → Supabase. It has no code path connecting it to the chat/LLM flow.
- `packages/api` is the shared contract — tRPC routers, Zod schemas, service interfaces — consumed by both mobile (client-safe entry point) and backend (`/server` entry point with the router). This is what gives mobile end-to-end type safety.

## What "moving the AI part to FastAPI" would actually mean

Only the LLM call path moves. Concretely: `apps/backend/src/services/llm.ts` (chat completion) and `apps/backend/src/services/summary.ts` (thread summarization, uses `generateText`) would become HTTP calls from Next.js to a new Python service, instead of in-process calls to the AI SDK.

Everything else stays put:
- tRPC router, Supabase access, admin portal, auth — stay in Next.js. Rewriting these in Python would break the `@mani/api` type-sharing contract with mobile and require rebuilding the admin UI — a much bigger, separate decision, not a consequence of this split.
- Exercises stay untouched — they were never wired to the AI layer.
- Prompt *storage* (the DB tables, the admin UI for editing prompts) stays in Next.js/Supabase. **Resolved 2026-09-14:** FastAPI owns prompt *composition* and reads the prompt and framework tables **read-only**; the backend sends a structured `context` object, not finished prompt text. It never writes to the prompt DB.

## Possible causes / reasons to do this

None of these are confirmed as muhammad's actual motivation yet — listed so we can check which (if any) apply:

- **Python-only AI tooling** — wanting LangGraph/LangChain-style agent orchestration, a specific eval/observability library, or heavier ML tooling that's Python-first.
- **Real tool-calling / agentic behavior** — if the plan is to give the model actual function-calling (e.g., "fetch and hand over this specific exercise," multi-step tool use), that's new work regardless of language, and a Python agent framework might make it easier to build correctly.
- **Team skillset** — someone working on the AI layer is stronger in Python than TypeScript.
- **Isolating the AI layer's deploy/scaling profile** — LLM calls have different latency/cost/scaling characteristics than the rest of the API; splitting lets it scale or fail independently of the Next.js app.
- **Model/provider experimentation** — wanting to run multiple models, local models, or heavier pre/post-processing (e.g., embeddings, classifiers) that don't fit naturally into a Vercel serverless function's constraints (execution time limits, cold starts, package size).

If none of these are the actual driver, the split adds complexity (a second service, a second deploy target, a network hop) without a clear payoff — worth confirming before building anything.

## Driver, as stated by muhammad (2026-09-10)

The AI layer is expected to need real tool calling, repeated retrieval of the right content per turn, and to grow into an agent over time. The split is wanted so that complexity is isolated in its own service from the start.

Assessment of that reasoning:

- **Tool calling alone does not justify leaving TypeScript.** The Vercel AI SDK already in use (`generateObject`, `apps/backend/src/services/llm.ts:196-204`) supports tool calling and multi-step agent loops. If tool calling were the only requirement, staying in Next.js would be the cheaper correct answer.
- **The argument that does hold is runtime shape, not language.** An agent loop making several sequential model calls plus retrieval hops per user turn can run for tens of seconds. Next.js on Vercel runs in serverless functions with an execution ceiling (plan-dependent — check the current limit rather than assuming). A long-lived container does not have that ceiling. This is the load-bearing reason for the split, and it dictates the deploy target: a container platform (Fly.io / Railway / Cloud Run), **not** Lambda-style hosting, which reproduces the same timeout problem.
- **Secondary language argument**: LangGraph-class orchestration (durable agent state, checkpointing, interrupts) is genuinely more mature in Python than the TS equivalent. Valid, but secondary to the runtime argument.
- **The app-store argument is sound**: with agent complexity behind a frozen tRPC contract, the agent can evolve arbitrarily server-side without a new mobile build or review cycle.

Consequences that follow directly from this driver:

1. ~~**Streaming is now effectively required, not an open question.**~~ **Reversed 2026-09-14 — no streaming in v1.** The product argument still stands: a long silent wait in an emotional support chat is a failure. What changed is the conclusion drawn from it. Rather than build streaming to *mask* latency, keep turns short — which is achievable now that the six regeneration loops are becoming deterministic code instead of extra model calls (~21 provider calls per turn today, worst case). Dropping streaming from v1 removes the SSE contract, connection-holding, and most of the hosting constraint. Revisit when a real agent loop makes turns genuinely long.
2. ~~**Agent state ownership must be decided.**~~ **Resolved 2026-09-14: stateless.** The backend owns every write; ai-service returns a response and persists nothing. The recommendation below was taken. One refinement — ai-service does get **read-only** access to the prompt and framework tables, since it owns prompt composition and the content has to come from somewhere. That is configuration, not state: no session, no user identity, no writes. Background work that genuinely needs to checkpoint runs as a separate worker process against a job table, not inside the request path.
3. **YAGNI boundary**: build the service boundary and keep today's behavior working across it first. Do not build agent orchestration, checkpointing, or retrieval infrastructure ahead of a concrete need for them.

## How it would be implemented, if we go ahead

1. **New service skeleton** — `apps/ai` (or a separate repo, TBD) running FastAPI, with its own `pyproject.toml`/`requirements.txt`, a `/health` endpoint, and structured logging from day one.
2. **Contract first** — define the request/response shape as the Python equivalent of the current `generateObject` schema (`apps/backend/src/services/llm.ts:25-115`). This schema should be the single source of truth on both sides; consider generating the Pydantic model from the same source the Zod schema is generated from, or keeping them hand-synced with a test that fails if they drift.
3. **Internal-only exposure** — FastAPI is never called from mobile directly. It sits behind Next.js, reachable only by the backend (network policy / internal URL / shared secret header), same as any other internal service.
4. **Move `llm.ts` logic over** — prompt-to-model call, JSON parsing/validation, error handling (rate limits, malformed model output, timeouts). Next.js's `messages` service calls FastAPI instead of the AI SDK, then persists the result to Supabase exactly as it does today.
5. **Move `summary.ts` logic over** as `POST /v1/summarize`. **Resolved 2026-09-14 — it moves.** It currently hardcodes `gpt-4o-mini` and reads `OPENAI_API_KEY` directly, bypassing the provider system entirely; moving it unifies that.
6. **Auth between services** — a shared secret or signed internal token so the FastAPI service only accepts requests from the Next.js backend, not the public internet.
7. **Observability** — decide whether `AI_DEBUG_MODE` / reasoning-log output (used by `conversation-test` skill) moves to FastAPI's responses or stays derivable from Next.js. The turn-by-turn testing workflow depends on this.
8. **Testing** — FastAPI gets its own test suite (pytest) mirroring the "fake concrete objects from real interfaces" pattern already used in the Jest suites; Next.js's existing LLM-related tests get updated to mock the new HTTP call instead of the AI SDK call.

## External pipeline, if required

Depends on where FastAPI runs — this needs a decision, not assumed:

- **Deploy target**: Vercel doesn't run long-lived Python services well (serverless functions only, with cold-start and duration limits similar to what might be motivating the move away from Next.js for this). Realistic options: Fly.io, Railway, Render, AWS (ECS/Lambda via Mangum, or App Runner), or a Docker container on any VM. Each has different implications for cost, cold starts, and ops overhead.
- **CI/CD**: a second pipeline (GitHub Actions job, or whatever's used today) to lint/test/deploy the Python service independently of the `turbo.json` pipeline that currently builds mobile + backend together.
- **Secrets**: the OpenRouter API key lives **encrypted in the `admin.providers` table** and is `decrypt()`ed on every request (`llm.ts:130`); the env var is only a development override. **Resolved 2026-09-14:** it moves to ai-service's own environment and the backend never sees it. That removes `decrypt()` from the request path and fixes M5, where the decrypted key currently reaches the browser in the admin portal's RSC payload.
- **Networking**: Next.js needs a reachable internal URL for FastAPI in every environment (local dev, staging, prod) — likely a new env var alongside `EXPO_PUBLIC_API_URL`.
- **Monitoring**: error tracking/logging for a Python service (Sentry or similar) if that's already used in Next.js and should stay consistent.

## Incorporating the existing Next.js backend alongside FastAPI

The two services would not be peers — Next.js stays the system of record and the only thing either client (mobile, admin portal) talks to. FastAPI is a private dependency of Next.js, not a second front door. Concretely:

- **Next.js keeps owning**: the tRPC contract mobile is built against (`packages/api`), auth/session, Supabase (users, threads, messages, exercises, prompt storage), and the admin portal. None of this changes shape — mobile's `EXPO_PUBLIC_API_URL` still points only at Next.js, in dev and in production app store builds alike. This matters for release: mobile ships to the App Store/Play Store as compiled binaries that are expensive to force-update, so the mobile ↔ backend contract (tRPC types from `packages/api`) needs to stay stable regardless of what happens behind Next.js. The FastAPI split should be invisible to mobile.
- **Next.js becomes the caller of FastAPI**, not a pass-through. The existing flow — `messages` service composes the prompt, calls the model, validates/parses the structured response, persists to Supabase, returns to mobile via tRPC — stays the same shape; only the "call the model" step swaps from an in-process AI SDK call to an HTTP call to FastAPI. Failure handling matters more once this is a network call: Next.js needs timeouts and a defined fallback (e.g., a "something went wrong, try again" message shape already in `packages/api`'s schemas) for when FastAPI is slow, down, or returns malformed output — today an AI SDK failure is a single in-process try/catch; after the split it's a service dependency that can be down independently of Next.js being up.
- **Environments need to line up.** Whatever environments exist for Next.js today (local, staging/preview, production) need a matching FastAPI deployment and a corresponding internal URL env var in each, the same way `EXPO_PUBLIC_API_URL` is environment-specific today (see `apps/backend/.env.example` / `apps/mobile/.env.example`). A production mobile build talking to a production Next.js that's misconfigured to hit a staging or missing FastAPI instance is the kind of failure mode that's easy to introduce here and hard to debug after it's already in users' hands via the app stores.
- **Rollout order matters given app store review latency.** Because mobile releases go through App Store/Play Store review (not instant, and hard to roll back quickly), the safest sequencing is: ship and stabilize the FastAPI split behind the existing tRPC contract first (Next.js and FastAPI both server-side, deployable instantly), confirm parity with today's chat behavior via the existing `conversation-test`/`conversation-review` skills, and only then let that be part of what ships in the next mobile build — rather than coupling a mobile release to the infra migration landing at the same time. If FastAPI has a bad rollout, you want to be able to fix or roll it back server-side without needing a new app store release.
- **Secrets/config split**: the OpenRouter key moves to (or is duplicated in) FastAPI's environment; Next.js no longer needs it once `llm.ts`'s direct call is replaced by an HTTP call, which is one less production secret mobile-adjacent infra depends on.

## Protocol between Next.js and FastAPI: REST/JSON

Decided 2026-09-10. tRPC was never a candidate for this leg — it depends on TypeScript types being imported at compile time on both ends, and there is no Python client, so "tRPC to FastAPI" would be hand-written HTTP with none of the inference benefit. tRPC stays on the mobile ↔ Next.js leg only.

REST/JSON is the right fit for the internal leg because there is one caller and one callee (no multi-language fan-out to justify gRPC codegen overhead), FastAPI is built around Pydantic with auto-generated OpenAPI, and that OpenAPI spec can generate TypeScript types for the Next.js side — recovering most of what tRPC gives us without a shared language.

**Resolved 2026-09-14: v1 is plain request/response REST, no streaming.** The earlier caveat below is superseded. Keeping turns short is the answer rather than streaming to mask latency — which is achievable once the six regeneration loops become deterministic code instead of extra model calls. Revisit SSE at v2, when tool calls genuinely lengthen a turn; it stays a low-stakes, reversible decision of roughly one call site in Next.js and one route handler in FastAPI, and should not absorb attention that belongs on the split itself.

## Content access: tools, not retrieval

Measured 2026-09-10, before deciding:

- 18 exercises total in `library_audio/exercises.json`, with `id`, `title`, `description`, `subtitle`, `type`, `displayOrder`, `showOnHomeScreen`.
- `techniques.md` is 1,795 words and is already loaded in full into every request as layer 2 of `composeSystemPrompt`. There are two techniques (`thought_reframing`, `abcde`), defined in `apps/backend/src/constants/techniqueSteps.ts:23-52`.
- The entire prompt corpus across all five files is 5,731 words, roughly 7-8k tokens, against Gemini 3 Flash's context window.

**No retrieval layer is justified at this size.** No vector search, no embeddings, no pgvector, no RAG. The full content library fits in context with room to spare. Semantic search would only earn its place when matching free-text user language against a corpus where category filtering genuinely fails — nowhere near the case at 18 items.

**Decision: the AI service exposes tools for exercises and techniques** rather than inlining the catalog into the prompt. *(2026-09-14: this is **v2**, not v1. v1 ships prompt composition plus the model call with behaviour identical to today, and proves parity first. Tools, the framework registry, tiered prompt loading, and the support-style layer all land afterwards.)* My recommendation had been to inline the 18-item catalog as one more prompt layer (simpler, no round-trip), but muhammad chose tools, and the reasoning holds up:

- Signed audio URLs expire and are generated per-request, so they cannot be inlined at all.
- Completion state is per-user and changes between turns.
- Keeping the catalog out of the base prompt leaves that prompt focused on voice and behavior, which is the part under constant iteration.
- The tool boundary is already in place if the library grows well past 18.

Two constraints on the implementation:

1. **Tools read Supabase directly (read-only), and must not call back into Next.js.** Otherwise a single turn becomes Next.js → FastAPI → Next.js, and internal REST endpoints would have to be exposed purely to serve our own AI service. Consistent with the prompt-access decision above.
2. **Signed-URL generation stays in Next.js.** That logic lives in `apps/backend/src/services/exercises.ts` and must not be duplicated in Python. The agent returns an exercise *id*; Next.js resolves it to a signed URL on the way out. One implementation, and the Python service never needs Storage credentials.

Cost to budget for: each tool call is another model round-trip, compounding per-turn latency. *(2026-09-14: this is the argument that would bring streaming back — but it applies to v2, when tools actually exist. v1 has no tools and no streaming. Watch p95 turn latency once tools land and revisit then, with data.)*

## Open questions for a clearer vision

1. ~~What content is the agent accessing repeatedly?~~ Resolved 2026-09-10 — see "Content access: tools, not retrieval" below.
2. ~~Does summarization (`summary.ts`) move too, or just chat completion?~~ **Resolved 2026-09-14 — it moves**, as `POST /v1/summarize`. It currently hardcodes `gpt-4o-mini` and reads `OPENAI_API_KEY` directly, bypassing `admin.providers`, `admin.prompts` and the LLM service entirely; moving it unifies that. Wire the dead `summarization` and `title_generation` prompts as part of the move, or delete them.
3. ~~Does prompt *composition* move to FastAPI, or does Next.js hand over finished text?~~ **Resolved 2026-09-14 — composition moves to ai-service.** The backend assembles a structured `context` object from the database and ai-service turns it into prompt text however it likes. Prompt content reaches it through read-only access to the prompt and framework tables. This also means an invalidation endpoint is required, or an admin edit waits out the cache TTL — see [[2026-09-14-architecture-decisions]] #9.
4. ~~Is streaming required?~~ Resolved twice. First as "effectively yes"; then **reversed 2026-09-14 — not in v1.** Keep turns short instead of masking latency. Revisit when tools make turns genuinely long.
5. Where does this run? Needs to be a container platform (Fly.io / Railway / Cloud Run) rather than Lambda-style hosting, per the runtime argument. Which one is still undecided. *(2026-09-14: whichever is chosen must support **two process types from one image** — `uvicorn` serving requests and a worker loop claiming jobs. All three do. Not one process doing both, or a long orchestration job starves the request path. Internal-only, behind a shared-secret header; the backend needs an ai-service URL variable per environment.)*
6. ~~Is this a step toward real tool-calling?~~ Resolved: yes, tool calling and agent growth are the stated intent.
7. Does `AI_DEBUG_MODE` reasoning-log output need to survive the split for the `conversation-test` / `conversation-review` skills to keep working, and if so, in what shape?
8. Timeline/urgency — is this near-term work or a longer-term direction to keep in mind while building other things?
