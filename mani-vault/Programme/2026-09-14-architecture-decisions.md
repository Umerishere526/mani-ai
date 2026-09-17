# Architecture decisions — AI service, schema, and prompt ownership

Date: 2026-09-14

Settles nine questions that were open across [[DEV-START]] and
[[2026-09-09-fast-api-infra-from-scratch]]. Several of these **supersede** what those documents
say; where that happens it is called out explicitly and those files have been updated.

Companion: [[ai-service-contract]] — the v1 request/response contract between the Next.js
backend and the FastAPI service.

---

## The question that started this

"Do we build the FastAPI layer, or correct the existing project first?"

**Answer: both, in this order — safety, schema, cost, then the service.** The FastAPI split is
still happening. What changed is its position in the sequence and, more importantly, the
reasoning that justifies it.

### Two corrections to earlier reasoning, recorded because they matter

**1. "`llm.ts` is already a clean seam" was wrong.** `llm.ts` is a *provider adapter* — key
decryption, model construction, one `generateObject` call. The actual agent logic is the six
`llmService.chat(...)` sites inside `messages.ts` (lines 781, 815, 994, 1031, 1091, 1181), each
rebuilding a feedback-augmented message array to repair a different failure. That is
prompt-repair policy, already written in TypeScript, and it is exactly what a Python agent
would own.

Consequence: the option to split does not expire, but **its price rises** the more agent logic
accumulates in TypeScript. Do not build an elaborate regeneration policy chain in TypeScript
while intending to own it in Python.

**2. The six regeneration triggers should not be model calls at all.** Every one is a
deterministic post-check on output: duplicate technique, script leakage, phase skip, missing
offering, repeated prompt, forbidden words. Dedupe an array. Strip a string. Correct the
`state` field. Worst case today is ~21 provider calls for one user message (six regenerations
× `maxRetries: 2`, each resending a ~9K-token prompt), measured at ~570K tokens across three
messages.

This is the single highest-value change available and **it has nothing to do with Python**.
Doing it first means porting the cheap version rather than paying to rebuild it later.

---

## The nine decisions

### 1. Database schema is rebuilt from scratch

Beta tester data is throwaway (confirmed with muhammad), so drop and recreate rather than
migrate. Squash the accumulated migrations into one readable `initial_schema.sql`.

**Check first:** confirm no remote Supabase project holds anything worth keeping. Local
throwaway is clear; a forgotten staging or preview project is the thing that bites.

Six structural changes, done as one batch while it is free:

| # | Change | Fixes |
|---|---|---|
| 1 | Framework/technique state into its own table, not six nullable `threads` columns plus two read-modify-write arrays | The state smear and both lost-update races |
| 2 | `crisis_events` table — timestamp, reason, thread, resolution | FR-6; a bare boolean has no time dimension, so crisis volume is unanswerable |
| 3 | `llm_calls` table — message id, prompt version, model, provider, tokens, latency, outcome | FR-19, FR-20, FR-23 |
| 4 | `frameworks` registry — id, kind, summary, body, activation conditions, phases | Required for 6+ frameworks |
| 5 | Retention and deletion columns, plus the deletion path | FR-10, FR-16 |
| 6 | `exercise_id` on the prompt/signal path | The AI cannot currently name a specific exercise |

**And do RLS properly in the same pass.** Building the per-request client from the user's JWT
instead of the service-role key was the highest-leverage finding in the whole audit, deferred
in [[DEV-START]] Stage F as "the single riskiest migration — do not attempt without a staging
environment." With an empty database and a from-scratch rebuild, that risk largely evaporates.
This window never gets cheaper.

Expect the test suite to break where shapes changed. That is the safety net working — budget
for the test-update pass.

### 2. ai-service is stateless; the backend keeps persistence

Per [[ai-service-contract]]. ai-service owns prompt composition, the model call, and
structured-output validation. The backend owns every database write.

This reverses an intent stated mid-conversation to move the orchestrator into Python. The
deciding argument is decision-in-brief #2 above: once the six repair loops become deterministic
code, what remains in `messages.ts` is bookkeeping — thirteen writes. There is no agent left in
there to move.

### 3. Prompt content reaches ai-service via read-only database access

The contract says ai-service turns `context` into prompt text "however it likes" but never says
where prompt *content* comes from. Resolved: **ai-service reads the prompt and framework tables
read-only.** That is configuration, not state — no session, no user identity, no writes — so
statelessness holds in the sense that matters.

### 4. The OpenRouter key lives in ai-service's environment

Not in the database, not decrypted and forwarded. The encryption machinery exists to support
admin-managed multi-provider configuration that is not being used — there is one provider,
pinned in `seed.sql`. Moving to an env var removes `decrypt()` from the request path and kills
M5 (the decrypted key currently reaching the browser's RSC payload) permanently.

Config stays in the database and stays admin-editable. Secrets do not.

### 5. No streaming in v1

Removes the SSE contract, connection-holding, and most of the hosting constraint. Plain
request/response REST. **Supersedes** the "streaming is effectively required" conclusion in
[[2026-09-09-fast-api-infra-from-scratch]].

Consequence: without streaming you cannot mask latency, so turns must stay short. Acceptable
while there is no agent loop; revisit when there is.

### 6. The worker is the same Python codebase, a second process type

Background and orchestration work runs as `python worker.py` claiming jobs from a table,
alongside `uvicorn` serving requests — one image, two process types, as supported by Fly,
Railway, and Cloud Run.

Not one process doing both: a long orchestration job would starve the request path, and you
would discover it during a conversation.

### 7. The admin portal becomes the source of truth for prompts

**Reversed mid-discussion.** The initial recommendation was markdown-as-source with a read-only
portal, because git supplies review, history, diffing, and rollback for free. That was correct
*until* muhammad confirmed **non-technical people will add prompts and inputs over time**.

That flips it. Markdown becomes bootstrap-only for a fresh database; the portal is authoritative.

**Resolves [[DEV-START]] open question 5**, which had both claiming authority — an admin edit is
silently clobbered by the next `pnpm db:seed`.

### 8. Portal governance is now a feature, not a config choice

Everything git was giving for free has to exist in the portal, because non-technical editors
cannot read a diff or revert a commit.

Small, do first:
- Make the version-snapshot write **fatal** — today a failed snapshot still publishes, and the
  prior content is gone permanently
- Stop deletion cascading version history away
- Make `ADMIN_EDITING_ENABLED` gate the server actions, not only the rendering (L2)
- Make `db:seed` refuse to run against a populated database — previously a footgun, now it
  would erase other people's work

The real work:
- **Draft → publish.** Edits are drafts until explicitly published. The mechanism that stops a
  half-finished thought reaching users in five minutes
- **Preview before publish** — run the pending prompt against fixed test conversations. This is
  where the dormant eval harness earns its keep: publishing runs evals, a regression warns or
  blocks. CI for prompts
- **Show who changed what, when.** `created_by` is stored but never rendered; there is no
  `updated_by`

Edit permissions split by column, not by source: **text fields** (prompt content, framework
summaries and bodies, activation wording, model config) are portal-editable; **structural
fields** (`kind`, phase sequences, validation enums) stay engineering-only, because changing
them breaks the state machine rather than the tone.

Consequence: reproducibility matters more, not less. Without git, the database version history
is the only record of what Mani was instructed to do — which makes the missing message →
prompt-version link load-bearing. Build it with the call log.

### 9. Cache invalidation is required, not optional

ai-service must cache prompts. Next.js today uses a 5-minute TTL, so an admin edit takes up to
five minutes to appear — across a service boundary that gets worse, and the documented prompt
workflow is edit → test → repeat.

Add `POST /v1/cache/invalidate`, called by the admin portal after a publish. Roughly ten lines,
and it is the difference between a tight iteration loop and a frustrating one.

---

## Order of work

1. **Crisis path, account deletion, policy documents** — days of work, blocked by nothing,
   and none of it lives in the layer being moved. Four `onPress` handlers, helpline content,
   a non-empty crisis reply, a delete mutation, two legal documents.
2. **Schema pass** — clean baseline, RLS properly, the six structural changes.
3. **Kill the regeneration waste in TypeScript** — ~20× cost reduction. Before the port, not
   after.
4. **ai-service v1** — composition plus the model call, parity proven against the evals.
5. **Cut over**, delete the TypeScript path.
6. **v2** — framework registry, tiered loading, tools, style layer, crisis as a tool call.
7. **v3** — the worker.

## Still open

- **Crisis detection ownership.** Model-driven today. Recommendation: keep it model-driven
  **and** add a deterministic pre-check — belt and braces, failing closed. It is the product's
  only safety mechanism and its recall has never been measured. Import the four orphaned
  scenarios in `apps/backend/test/evals/scenarios.ts:64-85` so it is finally asserted.
- **The regulatory and claims posture** — [[DEV-START]] open question 4, still unanswered, and
  it gates store submission.
- **A per-user LLM cost ceiling** — a number is needed to size the retry budget.
