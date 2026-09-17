# START HERE

The entry point for Mani. Read this first; it tells you what the project is, what is wrong
with it, what order to fix it in, and which document to open next.

**Rule for this folder:** documents at this level are **instructions** — they describe what is
true now and what to do next. Documents in `archive/` are **evidence** — point-in-time records,
cited but never executed. If the two disagree, this level wins. When a decision changes, update
the document here in the same sitting; do not leave two live answers.

---

## 1. What Mani is

An emotional-support companion app. A person talks to it; it responds with warmth, reflects
what they said, and — when the moment is right — offers a structured therapeutic exercise or an
audio meditation from its library.

```
Expo / React Native  ──tRPC──▶  Next.js backend  ──▶  Supabase (Postgres + Storage)
   apps/mobile                    apps/backend              │
                                       │                    └── prompts, threads, messages,
                                       └──▶ OpenRouter           exercises, audio files
                                            (Gemini 3 Flash)
```

Shared contract in `packages/api` — tRPC routers, Zod schemas, service interfaces. Mobile
imports types only. Dependency flow is `apps → packages` and never inverts.

**The core of the product is the chat.** Everything else supports it.

## 2. What the chat actually does

One user message runs this, in order. Know this before changing anything in it.

1. **Resolve what just happened.** Did they type, or tap one of Mani's capsule buttons?
   A tap can mean accepting or declining a technique. A typed reply is ambiguous, so the
   decision is deferred until the model has answered.
2. **Build a hidden `[ctx]` block** prepended to their message — technique cooldown, what has
   been tried, current exercise phase, recent response shapes. The user never sees it.
3. **Compose the system prompt** — identity, technique library, user context, title
   instruction, then all constraints last.
4. **Call the model.** Structured JSON comes back: `text`, `prompts`, `title`, `crisis`,
   `state`, `reasoning`, `style`.
5. **Inspect and possibly discard.** Six checks can throw the answer away and call the model
   again: duplicate technique, leaked script text, phase skip, missing offering, repeated
   buttons, forbidden words. Worst case today is ~21 provider calls for one message.
6. **Persist.** Message pair atomically, then roughly eight more writes for technique tracking,
   style history, library state, timestamps, title.
7. **Background** summarisation, when it triggers.

Two things to hold onto. **Those six repair checks are the agent logic** — they are what a
Python agent would own, and they should become deterministic code rather than extra model
calls. And **step 5 is not cleanly after step 4**: the phase-skip check reads thread state this
same request wrote, which is the one genuinely tangled part of the flow.

## 3. What is wrong — the honest summary

Three categories, in order of how much they matter.

**Safety is not implemented.** The crisis drawer's four help links have no handler attached.
No helpline number exists anywhere in the codebase. At the moment crisis is detected the
backend returns an empty string, so Mani goes silent and the input locks. Human escalation is
a `TODO`. Crisis is stored as a bare boolean with no timestamp, so "how many crisis events last
week" cannot be answered. A crisis eval fixture exists and has never been run.

**Two things block store submission outright.** There is no in-app account deletion anywhere in
the codebase — Apple has required it since 2022. The Terms and Privacy links in onboarding are
unclickable text pointing at documents that do not exist.

**The system cannot explain or measure itself.** No link from a message to the prompt version
that produced it. No cost or token accounting. No error tracking. No CI at all. An eval suite
exists but runs against a 727-line hand-maintained copy of the chat logic.

Underneath all that, the architecture is sound. Every assessment reached the same verdict:
repair, not rebuild. The module boundaries, the tRPC contract, the encryption, the service
injection pattern and 666 tests are all worth keeping.

## 4. The route

Phases are ordered by dependency, not preference. Each is shippable on its own.

| # | Phase | Why it is here |
|---|---|---|
| 0 | **Stand up the clean repo** | Everything else needs somewhere to land |
| 1 | **Crisis path + store blockers** | The only work where the cost of delay is a person, not a deadline |
| 2 | **Schema rebuild, RLS included** | Beta data is disposable — this window closes forever once real users exist |
| 3 | **Kill the regeneration waste** | ~20× cost cut, in TypeScript. Do it before porting, not after |
| 4 | **ai-service v1** | Prompt composition + the model call. Behaviour identical to today |
| 5 | **Cut over, delete the TypeScript path** | One implementation again |
| 6 | **v2 — registry, tools, frameworks** | Six-plus frameworks, tiered loading, exercise targeting, the style layer |
| 7 | **v3 — the worker** | Background orchestration, second process type, same codebase |
| 8 | **Store release** | Last, because it is the only irreversible step |

**Phase 1 is decided to happen in the new repo only.** That means the new repo's first
milestone is *a shippable build with the crisis path working* — not "everything migrated."
Get to that point, ship it, then continue. The consequence of this choice is that beta testers
stay on the broken path until that ship happens, so it should be measured in days.

### The first file to write

`apps/mobile/src/constants/crisisResources.ts`. It does not exist. The four dead links cannot
be wired until it does, and nothing else in the plan is blocked by anything.

Then `CrisisDrawer.tsx` (pass `onPress` to each `ActionLink` — the component already accepts
one), then the two `content: ''` returns in the chat service.

**The helpline content is a decision you own, not an engineering task.** Which countries, which
services. Do not let an AI supply numbers; a wrong helpline is worse than no button. Source
them officially per region, and use `findahelpline.com` as the interim answer if the user
geography is not settled.

## 5. The nine architecture decisions

Full reasoning in [[2026-09-14-architecture-decisions]]. In brief:

1. Schema rebuilt from scratch, not migrated. RLS written correctly in the same pass.
2. ai-service is **stateless**; the backend keeps every database write. The orchestrator does
   not move to Python.
3. ai-service owns prompt composition, reading prompt and framework tables **read-only**.
4. The OpenRouter key lives in **ai-service's environment** — not the database, not decrypted
   per request.
5. **No streaming in v1.** Keep turns short rather than masking latency.
6. The background worker is a **second process type in the same Python codebase**, not a
   separate service.
7. The **admin portal is the source of truth** for prompts; markdown is bootstrap-only.
   Non-technical people will be editing prompts.
8. Portal governance is therefore required work: draft → publish, fatal version writes, preview
   that runs the evals.
9. Cache invalidation endpoint, or prompt edits wait out the TTL across a service boundary.

## 6. Repo layout to build toward

```
mani/
├── apps/
│   ├── mobile/          Expo React Native
│   ├── backend/         Next.js — tRPC, auth, admin portal, ALL persistence
│   └── ai-service/      Python FastAPI — prompt composition, model call, worker process
├── packages/
│   ├── api/             the tRPC contract, shared with mobile
│   └── design-tokens/
└── journal/             this folder
```

`ai-service` lives in the monorepo. Two process types from one image: `uvicorn` serving
requests, and a worker loop claiming jobs.

## 7. Which document to open

| You are doing | Read |
|---|---|
| Understanding the whole programme | [[DEV-START]] |
| Anything touching the AI layer | [[2026-09-14-architecture-decisions]], then [[ai-service-contract]] |
| Building ai-service | [[ai-service-contract]] — it is the spec |
| Background on why the split works this way | [[2026-09-09-fast-api-infra-from-scratch]] |
| Standing up a machine | [[SETUP]] |
| Working a ticket, wondering what finding it came from | [[AUDIT-TICKET-MAP]] |
| Safety, privacy, or regulatory work | [[2026-09-13-fundamental-review]] |
| Wanting the evidence behind a claim | `archive/` — read, do not execute |

## 8. Moving into the clean repo

Copy `journal/` across first, before any code. It is the only thing that carries the reasoning.

Then, in order:

1. **Scaffold** — `pnpm-workspace.yaml`, `turbo.json`, root `package.json`, `.gitignore`,
   `.prettierignore` (this one matters — without it `lint:fix` reformats `pnpm-lock.yaml` and
   every install produces a ~10,000-line spurious diff).
2. **`packages/api`** — the contract. Nothing compiles without it.
3. **`packages/design-tokens`**.
4. **`apps/backend`** — but write the schema fresh rather than copying the 24 migrations.
   Squash to one `initial_schema.sql` carrying the six structural changes and proper RLS.
5. **`apps/mobile`**.
6. **`apps/ai-service`** — last, and not before phase 3.

**Carry these fixes across; they exist only as uncommitted changes in the old repo:**

- `seed.sql` — two seed users had non-RFC UUIDs, which made chat return HTTP 500 under Zod v4's
  `.uuid()`. Use the `a0000000-0000-4000-8000-0000000000NN` form.
- `supabase` CLI pinned `^2.116.0` — anything older hits a storage-migration crash loop that
  tears down the whole stack.
- `.prettierignore` at root — see above.
- Two test files had pre-existing `tsc` failures: `createMockExercise` missing `subtitle`,
  `createMockThread` missing `responseStyles`.
- Both `.env.example` files gained `EXPO_NO_METRO_WORKSPACE_ROOT=1`, `OPENROUTER_API_KEY`, and
  local-Supabase URL guidance.

**Fix these in the move rather than copying them forward:**

- `seed.sql` and `scripts/seed-prompts.ts` tell you to run `pnpm db:seed:prompts` (the script is
  `db:seed`) and point at `supabase/prompts/` (prompts live in `apps/backend/prompts/`).
- `README.md` cites a `.tool-versions` file that does not exist, and says Next.js 15 where the
  backend is on `^16.0.8`. Root `CLAUDE.md` repeats the version error and describes a
  navigation structure that is fictional.
- `apps/backend/CLAUDE.md` documents `GOOGLE_APPLICATION_CREDENTIALS`, which nothing reads.
- `apps/mobile/package-lock.json` is tracked despite being gitignored; `supabase/.branches` and
  `supabase/.temp` are tracked at the repo root. Do not carry any of them.
- `getAppAuthMode()` defaults to `'none'` on an unrecognised `APP_AUTH_MODE`, so a typo silently
  disables app attestation. Make it throw before you create new environments.
- Add `.github/workflows/` from the start — `tsc --noEmit` plus the test suites. **Leave lint
  out of the gate** until the 419 existing errors are cleared, or the first red build teaches
  you to ignore CI.

## 9. Open questions that gate real work

1. **Regulatory and claims posture.** Is Mani positioned as wellness, or does any copy make a
   clinical claim? The prompts implement two named CBT protocols, and exercise copy says things
   like "calms anxiety" and "resets your nervous system". This drives GDPR special-category
   handling and how store review treats the app. Ask someone with legal or clinical standing.
2. **Crisis detection ownership.** Model-driven today, with recall never measured.
   Recommendation: keep it model-driven *and* add a deterministic pre-check. Fail closed.
3. **Is any beta data worth keeping?** Answered: no. Recorded because the schema rebuild
   depends on it staying true.
4. **A per-user LLM cost ceiling.** A number is needed to size the retry budget.
5. **Which countries for helpline resources.** Blocks phase 1.
