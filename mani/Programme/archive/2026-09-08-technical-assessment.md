> **ARCHIVED — evidence, not instructions.** Point-in-time record. Parts of this are
> superseded; see `README.md` in this folder for exactly which. Current instructions live
> in `../START-HERE.md`, and where the two disagree, that one wins.

# 2026-09-08 — Technical foundation assessment

> Superseded for consolidation purposes by
> [[2026-09-08-mobile-review-and-consolidation]], which completes the mobile pass, adds
> the data-flow traces, and carries the Keep/Fix/Restructure/Replace verdict and order of
> work. This document remains the dimension-by-dimension judgment.

Judgment layer over the evidence in [[2026-09-08-repo-audit]] and
[[2026-09-08-repo-setup-and-doc-gaps]]. Where those two record *what is true*, this
records *what it means* and *what I would do*.

## Verdict

**A well-architected codebase with an authorization model that guarantees recurring
data-exposure bugs, and effectively no operational maturity.**

The engineering taste on display is genuinely good — the module boundaries, the type
contract, the prompt-as-versioned-artifact approach and the local dev story are all above
average for this stage. None of that is the problem. The problem is that a deliberate
architectural decision — bypass Postgres row-level security and rely on every service
method to remember a `userId` filter — is a design that fails silently and catastrophically.
Two methods forgot. The result is cross-user access to therapy transcripts containing
crisis disclosures, in a mental-health product.

That is not a bug to patch and move on from. It is a class of bug that the current design
will keep producing. Everything else in this document is secondary to fixing it.

| Dimension | Rating | One-line basis |
| --- | --- | --- |
| Architecture & module boundaries | **Strong** | service injection is real, dependency flow is correct, client/server split is deliberate |
| Type safety & data flow | **Strong** | tRPC + zod end to end, single contract, no codegen drift |
| Database schema & indexing | **Good** | 24 sequential migrations, sound indexes, correct cascades, clean `db lint` |
| **Authorization model** | **Broken** | RLS enabled but inert on the app's own path; per-method discipline is the only control |
| React Native / Expo app | **Adequate** | conventional, readable; no error boundary, brittle startup gate, three SDK majors behind |
| Dependencies | **Weak** | 191 advisories, 6 critical, 4 of them for a feature that does not work |
| Deployment & infrastructure | **Weak** | no CI, no staging, conflicting Vercel config, unwired EAS channels |
| Documentation | **Mixed** | unusually thorough, and materially false in places |
| Maintainability | **Moderate** | good structure, one 1,600-line hotspot carrying most of the risk |
| Reliability | **Weak** | no CI, no error tracking, no rate limiting, no error boundary |
| Scalability | **Adequate** | infra is fine at this stage; LLM cost per turn is the real constraint |
| Security | **Serious issues** | 4 critical, 2 reproduced against a running system |
| Privacy | **Serious issues** | plaintext crisis disclosures + cross-user read + PII in production logs |

---

## What is genuinely well built

Stating this plainly because the finding lists do not convey it, and it changes what the
right remediation is: **repair, not rewrite.**

1. **The service-injection boundary is real and enforced.** `packages/api` declares
   interfaces and routers; `apps/backend` implements; `apps/mobile` consumes types only.
   Dependency flow never inverts. Most codebases that claim this pattern leak within a
   month.
2. **The client/server entry-point split is a non-obvious, correct decision.**
   `@mani/api` vs `@mani/api/server` keeps server code out of the React Native bundle,
   backed by an eslint `no-restricted-imports` rule. Someone thought about this.
3. **tRPC is the right call for this team size.** One source of truth for the contract, no
   codegen step, no client/server drift. The 45k-line codebase type-checks clean across
   four packages.
4. **Prompts as versioned artifacts.** For an LLM product the prompts *are* the product.
   Markdown files with YAML frontmatter, seeded into a DB with version rows and an admin
   portal, is a mature answer to a problem most teams solve with string literals.
   *(2026-09-14: the mechanism is sound, but which end is authoritative was never defined —
   markdown and the portal both claimed it. Now decided: the portal is the source of truth,
   markdown is bootstrap-only, because non-technical people will be editing prompts. See
   [[2026-09-14-architecture-decisions]] #7 — and note that decision brings real governance
   work with it, listed as #8.)*
5. **Structured LLM output.** `generateObject` + zod rather than parsing free text, with
   the response shape declared once. Correct.
6. **Encryption is actually right.** AES-256-GCM, fresh random IV per operation, auth tag
   stored and enforced, PBKDF2-SHA256 100k, and production refuses to boot without a
   strong salt. I expected to find a homegrown mistake here and did not.
7. **The local development story is above average.** Custom ports to avoid collisions,
   seeded test users, an idempotent audio-seeding script, and a CLI to drive the chat API
   without the phone.
8. **The tests are not theatre.** 666 passing, and the assertion census (19.4% mock-call
   assertions against 1,168 total) shows they mostly assert real values. No module is
   mocked such that the code under test does not run.
9. **User deletion cascades correctly** to `threads`, `messages`, `thread_summaries` and
   `exercise_completions` — so "delete my account" genuinely erases user data. That is a
   real privacy asset and it was not accidental.

---

## The three structural problems

Everything in the audit reduces to these. Fix these and the finding count collapses.

### 1. The authorization model has no defence in depth

The tRPC context builds a **service-role** Supabase client (`route.ts:117`) that bypasses
RLS, hands it to every service, and relies on each service method filtering by the
JWT-derived `userId`. The `TODO` at `route.ts:100-115` states the reliance explicitly.

RLS policies exist and are correct. They are simply never consulted on the app's own code
path. So the database — the only component positioned to enforce this invariant
structurally — has been taken out of the loop, and replaced with a convention that must
hold across every present and future method.

It already failed twice: `messages.list` omits `ctx.userId` while `threads.get` twelve
lines away includes it, and the `messages` INSERT policy checks `user_id` without checking
thread ownership. And `insert_message_pair` — added to gain real transactional atomicity —
is `SECURITY DEFINER` with `EXECUTE` granted to `anon`, taking `user_id` and `thread_id`
as unvalidated parameters. The atomicity fix punched a hole straight through the
authorization model.

Compounding it: `authenticated` holds full DML (including `TRUNCATE`) on all four public
tables. The system is neither "API-mediated with locked-down tables" nor
"Supabase-direct with airtight RLS". It is half of each, which is strictly worse than
either.

### 2. Safety-critical logic lives in the client and in model output

For a product whose stated purpose is emotional support, the crisis path is the highest-
stakes code in the repo. Currently:

- **Detection** is a `crisis` field the model self-reports. Four regeneration paths replace
  the response object *before* the crisis check runs, and the retry prompts never restate
  the crisis contract — so a cosmetic-quality retry can silently discard a
  suicidal-ideation signal.
- **Enforcement** exists only in `ChatScreen.tsx:299`. `chat()` never reads
  `thread.crisisDetected`, and returns `crisisDetected: false` even for threads already
  flagged in the database.
- **The flag is user-writable.** `authenticated` has table-wide UPDATE on `threads` with no
  column restriction, so a user can `PATCH` `crisis_detected` back to false.
- **Injection into the prompt** is possible via `user_metadata.nickname`, which the user
  controls and which is interpolated unescaped into the *system* prompt.

There is no layer at which crisis state is authoritative. That is a product-risk issue
before it is a security issue.

### 3. The chat orchestrator is where all the risk concentrates

`services/messages.ts` is ~1,600 lines of procedural flow that: builds context, calls the
LLM up to six times per turn through five distinct regeneration triggers, runs a technique
state machine encoded in six nullable `threads` columns, and performs **eight independent
non-transactional writes** after the message pair.

It carries the majority of the HIGH findings, sits at 70% statement / 61% branch coverage,
and **none of the regeneration paths are covered by a test**. The state machine has no
validated transitions — model-supplied technique and step identifiers are used as object
index keys without being checked against the known set.

This file is the maintainability ceiling of the whole project. It is not badly written; it
is simply doing far too much in one scope to be reasoned about or tested.

---

## Dimension detail

### React Native / Expo application

Conventional and readable. Screens, providers, hooks and navigators are organised sensibly;
components are small; the design-token integration is clean. Two structural weaknesses:

- **No error boundary anywhere**, so any render throw takes the whole app down to the Expo
  Go error screen with no in-app recovery — and `retry: false` globally on TanStack Query
  means a single transient network blip produces a terminal error state with nothing above
  it to catch.
- **Startup is gated on a fragile precondition.** `useFonts` requires 7 faces (~1.46 MB)
  before first paint and discards the error object, so any font failure is an indefinite
  spinner. This is the most probable cause of the observed Android "loads for minutes, then
  Something went wrong".

Also: three SDK majors behind (54 vs 57), `react-native` hand-patched to tolerate a React
version mismatch, ~19 dead files, and five declared-but-unused dependencies. Nothing fatal;
all of it is accumulating carrying cost.

### Overall architecture & data flow

The happy path is clean and easy to follow: mobile signs in against Supabase directly →
holds a JWT in SecureStore → calls tRPC on Next.js with a bearer token → `route.ts`
validates the JWT via `auth.getUser` → builds a context with service-role clients →
routers delegate to injected services → services use `lib/db` query builders.

Two things muddy it. First, the mobile client talks to **two** backends — Supabase directly
for auth, and the Next.js API for everything else — which means two URLs, two failure
modes, and two places where a network config can be wrong. That is a reasonable trade for
using Supabase Auth, but it should be a documented, deliberate boundary. Second, storage
signed URLs are minted from whatever `SUPABASE_URL` the server holds and handed to the
phone, which silently couples server config to client reachability.

### Dependencies

The weakest dimension after infrastructure. 191 advisories: 6 critical, 109 high.
**Four of the six criticals arrive through `firebase-admin`**, which exists solely for App
Check — a feature that is off by default, cannot be enabled because the client side is an
unimplemented `TODO`, and whose verifier has 0% test coverage. That is a large critical-vuln
surface carried for functionality that does not work.

Beyond that: `next@16` carries 14 high advisories; the Expo SDK is three majors behind;
`expo-constants` is undeclared yet imported, with two versions installed; and the
hand-written `react-native` patch must be re-derived on every RN upgrade.

### Deployment configuration & infrastructure

**Effectively undefined.** There is no `.github` directory — no CI, no automated
type-check, lint, test or migration check on any branch. The only quality gate in the
repository is a local Claude Code `Stop` hook, which is a developer convenience, not
infrastructure.

`vercel.json` and `README.md` contradict each other on the Vercel root directory (applying
both resolves to `apps/backend/apps/backend/.next`). Twelve environment variables the code
reads are absent from `turbo.json` `globalEnv`, so the build cache will not invalidate when
they change — and two of them are `NEXT_PUBLIC_*`, inlined into the client bundle at build
time, meaning a cached build can ship the wrong Supabase target. `eas.json` defines no
channels while `app.json` configures an update URL. No staging environment is described
anywhere.

There is **no error tracking, no metrics, no tracing, and no rate limiting**. For a product
that makes paid LLM calls and runs a crisis-detection path, this means you cannot currently
answer "is crisis detection working in production?" or "why did our OpenRouter bill triple?"

### Backend & database structure

The strongest area after the module boundaries. 24 sequential migrations, sensible
composite indexes that match the actual query shapes, correct `ON DELETE CASCADE` for user
data, a real transactional RPC for the message pair, and a clean `supabase db lint`.

The defects are in privileges and policies rather than structure: over-broad grants to
`authenticated`, an INSERT policy missing an ownership predicate, `SECURITY DEFINER`
functions without pinned `search_path` (not currently exploitable — no role holds `CREATE`
on any searched schema), six redundant indexes, and three unindexed `NO ACTION` foreign
keys.

### Technical framework & documentation

Unusually thorough — four `CLAUDE.md` files, a README, an Expo Go runbook, a 50 KB
iteration log. And materially false in places, which in an AI-assisted codebase is worse
than absence, because every session ingests it as ground truth:

- The documented mobile navigation structure (bottom tabs, `DashboardStack`, `AboutStack`,
  `InformationScreen`, `AboutScreen`) does not exist. Reality is four native stacks.
- `prompts/title_generation.md` and `prompts/summarization.md` are never read by any code
  path, while `CLAUDE.md` instructs you to edit them and re-seed to change behaviour.
- The documented "constraints composed last" invariant breaks whenever a thread summary
  exists — i.e. on exactly the long conversations where it matters.

### Maintainability

Moderate, and unevenly distributed. Most of the codebase is easy to change safely. Nearly
all of the risk sits in one file. Against that: `pnpm lint` fails repo-wide with 419 errors
and `--max-warnings=0`, so the lint gate is currently decorative; backend unit tests are
excluded from linting entirely; and `packages/design-tokens` has no lint configuration at
all. A team cannot use "lint is green" as a signal today.

### Reliability

Weak, and this is mostly about missing scaffolding rather than bad code. No CI, no error
tracking, no error boundary, no retries, no rate limiting, no health checks beyond the
Supabase gateway, no alerting. Summarisation fails silently and permanently in any
deployment configured from `.env.example`, and nothing would tell you.

### Scalability

Adequate, and **the infrastructure is not the constraint.** Supabase plus Vercel will carry
this product comfortably to low tens of thousands of users; the schema and indexes support
it. The real constraints are economic and algorithmic:

1. **Cost per turn is unbounded.** Up to six LLM calls per turn against a ~34 KB system
   prompt, no rate limiting anywhere, and once summarisation fails the history fetch loses
   its `.limit()` so tokens per turn grow without bound.
2. **Two read-modify-write array appends** on `threads` will lose updates under
   concurrency. The UI guards double-submit, so this needs a retry or a second client
   today — but it is a latent correctness issue as soon as anything retries.

Nothing here calls for re-platforming.

### Security & privacy

Covered exhaustively in the audit. The material summary:

**Security** — 4 critical, two of which I reproduced against the running stack: an
authenticated user reading another user's full conversation, and an *unauthenticated*
caller reaching a `SECURITY DEFINER` insert path. All four reduce to structural problem 1.

**Privacy** — this deserves separate weight because of the product domain. The system
stores mental-health conversations including explicit suicidal-ideation disclosures, in
plaintext, and:

- those records were cross-user readable (C1) and unauthenticated-writable (C4);
- `packages/api/src/routers/messages.ts` writes thread ids and conversation context to
  `console.debug` **unconditionally**, so transcript metadata lands in production logs;
- the admin portal includes a read-only chat viewer exposing full transcripts, gated only
  by `admin_role`, with no access logging;
- `AI_DEBUG_MODE` returns the model's internal reasoning to clients;
- there is no data-retention policy, no retention migration, and no anonymisation path
  anywhere in the repository.

Account deletion cascading correctly is the one strong control. For a product in this
category, the gap between that single control and what a DPA or clinical-safety review
would expect is the largest non-code risk in this assessment.

---

## Recommended target architecture

Deliberately incremental. The existing structure is worth keeping; what it needs is for
the database to become the authority and for the orchestrator to be decomposed.

### 1. Make Postgres the authorization authority

Act on the `route.ts:100-115` TODO. Build the per-request `publicClient` from the **user's
JWT** rather than the service-role key, so RLS applies to every query on the app path:

```ts
createClient(url, anonKey, {
  global: { headers: { Authorization: `Bearer ${userJwt}` } },
});
```

Reserve the service-role client for genuinely cross-user admin operations, injected under a
distinct name so its use is visible in review. This single change makes C1, C2 and H2
structurally impossible rather than individually patched, and it converts "every method must
remember" into "the database enforces it".

Then close the direct-table surface: add a `WITH CHECK` on `messages` INSERT validating
thread ownership, restrict the `threads` UPDATE grant to the columns users may legitimately
change, revoke `TRUNCATE`/`DELETE` from `authenticated`, add `auth.uid()` validation inside
`insert_message_pair` (and revoke `anon`'s `EXECUTE`), and pin `search_path` on all three
`SECURITY DEFINER` functions.

**Decide explicitly whether the mobile client may ever talk to PostgREST directly.** If no —
and the code suggests no, since everything goes through tRPC — then revoke table-level DML
from `authenticated` entirely and let RLS protect only the auth-adjacent paths. That is the
cleanest end state and it eliminates the entire class.

### 2. Make safety state server-authoritative

- Reject `chat()` when `thread.crisisDetected` is set; never return `crisisDetected: false`
  for a flagged thread.
- Move the crisis check **ahead of** the regeneration pipeline, or carry the `crisis` field
  forward across retries so a cosmetic retry cannot drop it.
- Treat the crisis path as a tested contract: it is the one code path that warrants
  near-100% branch coverage.
- Bound and escape `nickname` before it enters the system prompt; better, stop sourcing
  prompt inputs from user-writable `user_metadata` at all.

### 3. Decompose the orchestrator behind the existing tests

Not a rewrite — an extraction, with the current suite as the safety net:

- **Technique state machine** → its own module with an explicit transition table and
  validated states. Model-supplied technique and step identifiers become zod enums at the
  trust boundary, not strings used as object keys.
- **Regeneration pipeline** → a named policy chain with an explicit retry budget and a
  single re-validation pass, replacing five ad-hoc trigger sites that each restart from the
  pristine message array.
- **Turn persistence** → one transaction (extend the existing RPC) covering the message
  pair *and* the thread-state writes, instead of one atomic write followed by eight
  unprotected ones.
- Replace the two read-modify-write array appends with single-statement
  `array_append`/jsonb concatenation.

### 4. Fix the trust boundary on model output

Every field the model returns that is used as a key, an index, a persisted enum or a
control-flow input gets validated against a closed set. Today a hallucinated technique name
becomes a rendered UI capsule and a persisted cooldown.

---

## Recommended infrastructure

**Stay on Supabase + Vercel + Expo.** It fits the team size and the product stage, and
nothing in the findings argues for re-platforming. Do not entertain Kubernetes, a custom
API gateway, or self-hosted Postgres at this stage — that would trade a solvable
authorization problem for an unsolved operations problem.

What to add, in value order:

| Priority | Addition | Why |
| --- | --- | --- |
| 1 | **CI on every PR** — typecheck, lint, test, migration check | There is none. It is the cheapest permanent defence against the regression classes found here |
| 2 | **Error tracking** (Sentry or equivalent) on backend *and* mobile | You currently cannot know that crisis detection or summarisation is failing in production |
| 3 | **Rate limiting** per user and per device (Upstash Redis or Vercel KV) | `messages.chat` is unmetered and each call is paid. `deviceId` is already collected and unused |
| 4 | **A staging Supabase project + Vercel preview env** | Migrations and RLS changes must be rehearsed somewhere that is not production |
| 5 | **Log hygiene** — remove unconditional `console.debug` from the router, redact identifiers, ship structured pino output | Transcript metadata is currently written to production logs |
| 6 | **LLM cost telemetry** — tokens and call count per turn, alerting on regeneration rate | Six calls per turn is invisible today |
| 7 | **EAS Build + dev builds, wired channels** | Expo Go is fine for smoke testing but cannot exercise `expo-updates`, App Check, or the Firebase config the repo already references |
| 8 | **Secret management for production** + a key-version byte in the encryption envelope | Rotation currently requires re-encrypting everything, and ciphertexts are not bound to their row |

Also: a documented data-retention policy with a migration to enforce it, and access logging
on the admin chat viewer. For this product category those are not nice-to-haves.

---

## Recommended development route

Sequenced so that each phase is independently shippable and the riskiest work happens after
the safety net exists.

**Phase 0 — stop the bleeding (days).** The four criticals and H1–H5. Narrowest possible
diffs: pass `ctx.userId` through `messages.list`; add ownership validation to
`insert_message_pair` and revoke `anon` execute; add the `messages` INSERT `WITH CHECK`;
restrict the `threads` UPDATE grant; reject `chat()` on a crisis thread; allow-list
`/admin/auth/callback` in `proxy.ts`; make summarisation's provider config coherent; add
the missing `.limit()`. No refactoring in this phase.

**Phase 1 — build the net (1–2 weeks).** CI with typecheck/lint/test/migrations. Lint to
zero, and stop excluding `__tests__`. Sentry on both apps. Rate limiting. Staging
environment. Fix the `vercel.json` / README conflict and complete `turbo.json` `globalEnv`.
Fix the mobile startup gate and add an error boundary — that pair alone converts your
current Android failure from a dead end into a legible error.

**Phase 2 — structural fix (2–4 weeks).** The JWT-scoped client and the RLS-as-authority
migration, rehearsed on staging. Then decompose `services/messages.ts` as described, with
tests written against the extracted state machine before it moves. Crisis path to high
branch coverage. Make the turn atomic.

**Phase 3 — pay down carrying cost (ongoing).** Drop `firebase-admin` or implement App
Check properly — carrying four criticals for dead functionality is not defensible either
way. Expo SDK 54 → 57 and re-derive or retire the `react-native` patch. Remove the ~19 dead
files and five unused dependencies. Add `pnpm-lock.yaml` and `src/types/supabase.ts` to
`.prettierignore` so generated files stop churning.

**Phase 4 — truth up the docs.** Correct the navigation section in root `CLAUDE.md`, delete
or wire up the two dead prompt files, reconcile the "constraints last" claim with what the
code does. In a codebase this AI-assisted, stale documentation is an active defect, and it
is the cheapest fix on this list.

---

## What I would not do

Stated explicitly because these are the tempting moves and I think they are wrong here.

- **Do not rewrite.** The module boundaries and type contract are the expensive part to get
  right, and they are already right. The problems are concentrated in an authorization
  decision and one oversized file — both repairable in place.
- **Do not re-platform off Supabase/Vercel.** Nothing found here is a platform limitation.
  Migrating would consume the entire remediation budget and leave the authorization model
  untouched.
- **Do not bulk-upgrade dependencies to clear the advisory count.** `pnpm outdated` shows
  Expo packages at 57.x because the SDK moved as a unit; upgrading them individually will
  break the app. Treat it as one deliberate SDK migration, and remember most of the 191
  advisories are dev-tooling transitives that never reach production.
- **Do not chase `react-native-reanimated`.** It is three checks confirmed inert: nothing in
  `apps/mobile/src` imports it, and the built bundle contains only the unrelated
  `react-native-reanimated-table`. The expo-doctor warning is a red herring for the crash.
- **Do not add abstraction to `services/messages.ts` before extracting it.** It needs less
  in one scope, not another layer on top.

## Confidence and gaps

The security and database conclusions rest on direct verification against a running system,
including two reproduced exploits. The architecture, dependency, infrastructure and
documentation conclusions rest on reading every config file and the full dependency graph.

The one thing I would want before treating this as complete: a pass over per-method error
handling and edge cases inside the backend services, which the original audit only covered
where other angles happened to surface it. It would not change this verdict, but it would
likely add findings in the MEDIUM band.
