> **ARCHIVED — evidence, not instructions.** Point-in-time record. Parts of this are
> superseded; see `README.md` in this folder for exactly which. Current instructions live
> in `../START-HERE.md`, and where the two disagree, that one wins.

# 2026-09-08 — Full repository audit

Report only. No fixes applied. Repo state: `main` @ `e7776ed`, plus the setup changes
recorded in `2026-09-08-repo-setup-and-doc-gaps.md`.

Size audited: 274 source files / ~45,000 lines — backend 19.5k, mobile 18.3k,
`packages/api` 2.9k, design-tokens 285, scripts 513, tests 3.7k, 24 migrations, 5 prompts.

## Coverage of this audit — read this first

| Domain | Covered | How |
| --- | --- | --- |
| Mechanical baseline | Full | eslint, knip, expo-doctor, pnpm audit, supabase db lint, coverage, production build |
| Configuration | Full | direct review of every config file |
| Docs vs code | Full | direct verification |
| Security | Full | dedicated pass; top findings independently re-verified and one exploited live |
| Prompts / AI orchestration | Full | dedicated pass; highest-severity claims re-verified |
| Request gatekeeper (`proxy.ts`) | Full | direct review + live HTTP test |
| Database layer | Full | second pass — policies, grants, indexes, FKs, functions, triggers, type drift, all verified against the live DB |
| Test quality | Full | second pass — assertion census, log hygiene, config |
| Backend service internals | Full | second pass — concurrency, transaction boundaries, double-write |
| Mobile app | Full | third pass — 12 largest files read in full, remainder by tooling and pattern sweeps |
| Backend services / tRPC (logic) | **Partial** | per-method error handling and edge cases only as surfaced by other passes; this is the one remaining gap |

Four of six original domain passes terminated on an account spend limit. Database, tests
and service internals were completed in a second pass; mobile in a third. See the
completeness statement at the end for exactly what was and was not read.

Confidence labels below mean:
- **EXPLOITED** — I ran it and observed the result.
- **VERIFIED** — I read the code/schema myself and traced it.
- **REPORTED** — surfaced by the audit pass; consistent with the code but I did not
  independently trace it. Treat as a strong lead, not an established fact.

## Severity summary

| | Count |
| --- | --- |
| CRITICAL | 4 |
| HIGH | 11 |
| MEDIUM | 24 |
| LOW | 20 |

Three of the four criticals are cross-user data exposure or injection in a mental-health
app. C1 and C4 were reproduced against the running stack.

---

# CRITICAL

## C1. Any authenticated user can read any other user's entire conversation

**EXPLOITED.** `packages/api/src/routers/messages.ts:72`

`messages.list` never passes `ctx.userId`:

```ts
list: verifiedEmailProcedure
  .input(z.object({ threadId: z.uuid(), limit: …, cursor: … }))
  .query(async ({ input, ctx }) =>
    ctx.services.messages.list(input.threadId, input.limit, input.cursor))
```

It flows to `apps/backend/src/services/messages.ts:410` → `lib/db/messages.ts:79`, whose
query is `.eq('thread_id', threadId)` on `publicClient` — the **service-role** client,
which bypasses RLS. `threads.get` and `threads.delete`, twelve lines away in the same
router, both correctly pass `ctx.userId`. This one method omits it.

The RLS policy `messages / Users can select own messages / USING (auth.uid() = user_id)`
would have blocked this had a user-scoped client been used. This is precisely the
exposure the `TODO` at `apps/backend/src/app/api/trpc/[trpc]/route.ts:100-115` hedges on:
the "explicit userId filtering in service implementations" that the security model relies
on is absent here.

**Proof.** Signed in as `test1@example.com`, called `messages.list` with a `threadId`
owned by `user@example.com`, and received that thread's full message history — including
a message in which the thread owner disclosed suicidal ideation. Content not reproduced
here; it is in the local dev DB, thread `b1007228`.

For an emotional-support app, cross-user disclosure of crisis content is the highest
possible severity. Thread UUIDs are not secret: they appear in `/admin/chats/[id]` URLs
and are logged throughout the chat pipeline.

## C2. Any authenticated user can inject messages into another user's thread

**VERIFIED** against the live schema. `apps/backend/supabase/migrations/20251211000001_update_messages_for_threads.sql:36-38`

Live policy:

```
messages | Users can insert own messages | INSERT | CHECK=(auth.uid() = user_id)
```

There is no check that `thread_id` belongs to the caller, and `authenticated` holds
`INSERT` on `public.messages`. The anon key and Supabase URL are compiled into the app
bundle by design (`EXPO_PUBLIC_*`), so any user can `POST /rest/v1/messages` with their
own `user_id` and a victim's `thread_id`, choosing `role: "mani"` and arbitrary
`prompt_options`.

Both read paths filter on `thread_id` alone (`lib/db/messages.ts:79`,
`routers/messages.ts:180`), so the forged row renders in the victim's chat **and** is fed
to the LLM as an assistant turn on their next message. The attacker controls the
"therapist" voice and the tappable capsules shown to a person in distress.

I verified the policy and grant but did not run this one end to end.

## C3. Crisis lock is client-side only

**VERIFIED.** `apps/backend/src/services/messages.ts:454` (entry), `:351`, `:1602`

`chat()` never reads `thread.crisisDetected`. Enforcement lives solely in
`apps/mobile/src/screens/chat/ChatScreen.tsx:299`
(`isChatBlocked = crisisDetected && crisisBlocksChat`). The documented behaviour —
"crisis detection blocks user from sending messages" — is advisory.

Worse, the normal return path hardcodes `crisisDetected: false` (`:351`, `:1602`) even for
a thread already flagged in the DB, so the response actively contradicts the persisted
state the admin portal displays.

Any caller that doesn't honour the flag — the `test:chat` CLI, a direct tRPC call, a
reinstalled app before `threads.get` resolves — keeps a crisis conversation going with no
server-side backstop. This is a safety control, which is why it is CRITICAL rather than
HIGH.

---

# HIGH

## H1. Magic-link admin login is broken

**EXPLOITED.** `apps/backend/src/proxy.ts:11-16`, `:70-72` vs `apps/backend/src/app/admin/login/page.tsx:33`

`proxy.ts` (Next 16's renamed middleware) matches `/admin/:path*` and allow-lists only
`/admin/login` and `/admin/unauthorized`. `/admin/auth/callback` is therefore gated — but
at callback time no session cookie exists yet, so `getUser()` returns null and the proxy
redirects away before the route can exchange the code.

```
GET /admin/auth/callback?code=testcode123
→ 307  location: /admin/login?redirectTo=%2Fadmin%2Fauth%2Fcallback
```

`signInWithOtp` (login page, line 30) is dead in the water. `signInWithPassword` (line 40)
sets cookies client-side and works, which is why nobody has noticed.

## H2. Users can clear their own `crisis_detected` flag

**VERIFIED** against live schema. `apps/backend/supabase/migrations/20251211000000_create_threads_table.sql:31-34`

```
threads | Users can update own threads | UPDATE | USING=(auth.uid() = user_id) | CHECK=NULL
```

`authenticated` holds table-wide `UPDATE` on `public.threads` with only a row-level
predicate and no column restriction. With the bundled anon key a user can
`PATCH /rest/v1/threads?id=eq.<own>` with `{"crisis_detected": false}`, and likewise
rewrite `techniques_offered`, `last_technique_*`, `response_styles`, and `message_count`
to defeat technique gating and cooldowns. (`user_id` reassignment is blocked — Postgres
reuses `USING` as the implicit `WITH CHECK`.)

Combined with C3, there is no layer at which the crisis flag is authoritative.

## H3. Crisis flag discarded by response regeneration

**REPORTED**, and the ordering is **VERIFIED**: the crisis check sits at
`apps/backend/src/services/messages.ts:1104`, downstream of four regeneration paths
(`:781`, `:815`, `:994`, `:1031`, `:1091`) that replace `llmResponse` wholesale.

Crisis detection is entirely the model's self-reported `crisis` field
(`services/llm.ts:51-60`). If the first generation sets `crisis` **and** trips any
regeneration trigger — script leakage, duplicate technique, phase skip, repeated prompt —
the retry prompt does not restate the crisis contract, so a retry that omits `crisis`
silently drops it. No drawer, no `crisis_detected`, conversation continues normally.

Highest-consequence finding in the AI layer: a safety signal destroyed by a
cosmetic-quality retry.

## H4. Conversation summarisation is dead in any deployment following `.env.example`

**VERIFIED.** `apps/backend/src/services/summary.ts:24`, `:64`

```ts
const EXTRACTION_MODEL = 'gpt-4o-mini';
…
const apiKey = process.env.OPENAI_API_KEY;
if (!apiKey) throw new Error('OPENAI_API_KEY environment variable is required…');
```

`OPENAI_API_KEY` is absent from `apps/backend/.env.example`. The throw is swallowed by the
background catch at `messages.ts:1576`, so summarisation fails silently and no summary is
ever created. History stays hard-capped at 20 messages with **nothing replacing** what
falls off — from turn 21 the model has no knowledge of the first half of the session.

Separately, the seeded `summarization` prompt is dead: `grep` finds no reference to
`'summarization'` as a prompt name anywhere in `apps/backend/src` or `packages/api/src`.
`prompts/summarization.md` configures openrouter / `openai/gpt-oss-120b`, which no code
reads. Editing it and re-seeding does nothing.

## H5. Unbounded history fetch once a summary exists

**VERIFIED.** `packages/api/src/routers/messages.ts:186-205`

The summary-checkpoint branch applies `query.gt('created_at', checkpointCreatedAt)` with
**no `.limit()`**. Only the checkpoint-missing fallback (`:206`) and the no-summary branch
(`:210`) cap at `RECENT_MESSAGES_WINDOW`.

Because summarisation is fire-and-forget and the checkpoint only advances on success, a
thread whose summaries start failing (see H4) sends every message after the stale
checkpoint on every turn. Token cost per turn grows without bound until hard
context-limit failures, with no degradation path.

## H6. Technique offers are recorded as if completed

**REPORTED.** `apps/backend/src/services/messages.ts:1324`, `services/prompts.ts:237`, `:746`

A merely *offered* technique is written to `techniques_offered`, which is rendered to the
model as "The user has already tried these techniques… Do NOT offer them again" and used
as the duplicate-regeneration blocklist. Nothing distinguishes offered-and-declined from
completed. The local variable is even named `acceptedTechniques` (`:492`) while holding
all offers.

With only two techniques in the library, one declined offer of each permanently exhausts
both for the rest of the thread — and if the user later asks for one by name, the model's
correct offer trips the duplicate check and is regenerated away.

## H7. Silent "declined" on a missing model field loses the technique mid-exercise

**REPORTED.** `apps/backend/src/services/messages.ts:886-918`, `:1346-1355`; schema `services/llm.ts:73-79`

`state` is nullable and `state.accepted` is `.optional()`. Absence of `accepted === true`
is treated as an explicit decline, which also nulls phase tracking and starts a cooldown.
A user who says "yeah, let's try that" while the model begins the technique but omits the
flag ends up mid-exercise with the state machine recording a refusal.

## H8. Model-supplied technique and step IDs are never validated

**REPORTED.** `apps/backend/src/constants/techniqueSteps.ts:68`, `:86-98`; `packages/api/src/types/services.ts:47`

`prompts[].technique` is a bare `z.string().optional()` that is persisted and drives
cooldowns; `state.technique` is used directly as an object index
(`TECHNIQUE_PHASES[technique]`), and unknown techniques or steps make
`validatePhaseTransition` return `{isValid: true}`. A hallucinated technique can be
rendered as a capsule and burn cooldowns that block the two real techniques. The prototype
-key case (`state.technique: "toString"`) throwing a 500 was flagged as SUSPECTED
reachability — worth a direct check.

## H9. System-prompt injection via user-writable `nickname`

**REPORTED.** `apps/backend/src/services/prompts.ts:219-229`; source `packages/api/src/routers/messages.ts:130-145`

`nickname` is read from `user_metadata` — writable by the user via
`supabase.auth.updateUser({data})` with the bundled anon key — and interpolated
unbounded and unescaped into the **system** prompt. That is higher trust than user turns,
and with crisis detection being a model-self-reported field (C3/H3) it is a plausible
route to suppressing the safety signal. No length cap, so it can also crowd out real
prompt layers. Self-affecting rather than victim-facing.

---

# MEDIUM

| # | Finding | Location | Confidence |
| --- | --- | --- | --- |
| M1 | **606 eslint problems / 419 errors.** `pnpm lint` uses `--max-warnings=0`, so lint is a hard failure repo-wide | api 9, backend 261, mobile 336 | VERIFIED |
| M2 | 12 env vars read by code are missing from `turbo.json` `globalEnv`, so Turbo's build cache won't invalidate on change. `NEXT_PUBLIC_SUPABASE_URL`/`_ANON_KEY` are inlined into the client bundle at build time — a cached build can ship the wrong Supabase target | `turbo.json:3-10` | VERIFIED |
| M3 | Backend unit tests are **never linted** — `.eslintignore` excludes `**/__tests__/**`. This is why two `tsc` errors sat undetected on `main` | `apps/backend/.eslintignore:7` | VERIFIED |
| M4 | App-attestation **fails open**: `getAppAuthMode()` returns `'none'` for any unrecognised value, so a typo (`api-key`, `apikey`) silently disables it. The `default:` deny branch is unreachable | `lib/security/apiKeyVerifier.ts:22-28`, `route.ts:70-73`, `:90-92` | VERIFIED |
| M5 | Decrypted provider API key is serialized into the RSC payload — `ProviderForm` is a client component receiving the whole `provider` object, so the plaintext key reaches the browser even though the field renders empty | `admin/providers/[id]/page.tsx:15,42`, `ProviderForm.tsx:14-17` | REPORTED |
| M6 | No rate limiting anywhere on `messages.chat`; `ctx.deviceId` is collected but never used. One account can loop 10,000-char messages and drain OpenRouter credits | `packages/api/src/routers/messages.ts:89-122` | VERIFIED |
| M7 | Admin auth callback exchanges the session using `SUPABASE_SERVICE_ROLE_KEY` where every comparable path uses the anon key. Privilege-scoping defect; also masks a missing anon key | `admin/auth/callback/route.ts:10-11,18` | VERIFIED |
| M8 | Open redirect: `` `${origin}${redirectTo}` `` with `redirectTo` from the query string — a value starting with `@` makes the authority attacker-controlled | `admin/auth/callback/route.ts:8,38` | REPORTED |
| M9 | `clearTechniquePhase` is self-undoing: writes `null` to the DB but not to the in-memory thread, and step 9.5 rewrites the phase from `state.step` in the same request. The model keeps closing an exercise the user finished turns ago | `services/messages.ts:473-482`, `:623`, `:1367-1376` | REPORTED |
| M10 | `title` is `.max(50)` in the schema but the consumer slices to 100. A 55-char title is a hard `generateObject` validation failure — the user loses the whole turn over a thread label | `services/llm.ts:42-44` vs `services/messages.ts:1459-1462` | REPORTED |
| M11 | Every user message is persisted **with** its `[ctx]…[/ctx]` prefix and replayed to the LLM verbatim; stripping happens only on client read paths. By turn 10 the model sees ten contradictory context blocks | `services/messages.ts:1264`, `:674-679` | REPORTED |
| M12 | `composeSystemPrompt` silently omits any layer missing from the cache (no `else`, no throw), and `refreshCache` sets `initialized = true` even when the query errored. Deactivating `response_format` in the admin portal leaves chat running with no constraints layer | `services/prompts.ts:131-177`, `:49-53` | REPORTED |

---

# LOW

| # | Finding | Location | Confidence |
| --- | --- | --- | --- |
| L1 | `authenticated` holds `TRUNCATE` (and `DELETE`, `REFERENCES`, `TRIGGER`) on all four public tables. RLS does **not** apply to `TRUNCATE`. Not reachable via PostgREST, so exploitation needs a direct Postgres connection — but the grant is far wider than needed | live grants on `messages`, `threads`, `thread_summaries`, `exercise_completions` | VERIFIED |
| L2 | `ADMIN_EDITING_ENABLED` gates only rendering; the 5 mutating server actions never call `isAdminEditingEnabled()`, so an admin can POST directly to the server action | `admin/lib/permissions.ts:27`; `admin/actions.ts:69,89,326,343,373` | REPORTED |
| L3 | Users can forge a second `[ctx]` block in their message to override technique cooldown state; the strip regex is anchored and non-greedy so only the first block is removed | `services/messages.ts:623-625`; `lib/db/messages.ts:382` | REPORTED |
| L4 | API-key comparison is not constant-time and the early length check leaks the configured key length. Moot in practice — `api_key` mode ships the secret in the app bundle anyway | `lib/security/apiKeyVerifier.ts:58-69` | VERIFIED |
| L5 | `cursor: z.string().optional()` accepts arbitrary text where a timestamp is required. No injection found (PostgREST 400s on cast failure); should be `z.string().datetime()` | `routers/messages.ts:69`, `routers/threads.ts:14` | VERIFIED |
| L6 | Encryption is sound (AES-256-GCM, per-encryption random IV, auth tag enforced, PBKDF2 100k, production refuses a short salt). Residual: no key version or AAD, so ciphertexts aren't bound to their provider row and rotation needs a full re-encrypt; dev fallback salt is `SHA256(secret)`; `IV_LENGTH=16` where 12 is standard for GCM | `lib/security/encryption.ts:62-75`, `:96-149` | VERIFIED |
| L7 | `techniques_offered` dedupes by exact string but receives both display names (`"ABCDE"`) and IDs (`"abcde"`), so the "already used" prompt layer lists the same technique repeatedly | `lib/db/threads.ts:216` | REPORTED |

---

# Mechanical baseline

## eslint — 606 problems, 419 errors

| Package | Problems | Errors | Warnings |
| --- | --- | --- | --- |
| `@mani/api` | 9 | 4 | 5 |
| `@mani/backend` | 261 | 180 | 81 |
| `@mani/mobile` | 336 | 235 | 101 |

Top rules: `no-console` 87, `no-unsafe-member-access` 82, `no-non-null-assertion` 48,
`no-unsafe-call` 46, `no-unsafe-assignment` 39, `import/order` 38, `global-require` 18,
`react-native-a11y/has-valid-accessibility-descriptors` 15.

Worst files: `apps/backend/src/lib/db/exercises.ts` (91),
`apps/mobile/src/screens/OnboardingScreen/hooks/__tests__/useOnboardingState.test.ts` (32),
`apps/backend/scripts/test-chat.ts` (26), `apps/backend/scripts/seed-exercises.ts` (24).

Prettier fails on one file: `apps/mobile/src/screens/OnboardingScreen/steps/NicknameStep.tsx`.

Notable individual hits worth treating as bugs rather than style:
- `apps/mobile/src/screens/exercises/ExercisePlayerScreen.tsx:17` — `expo-constants`
  imported but not declared in `package.json`
- `apps/mobile/src/screens/chat/ChatScreen.tsx:393` — floating promise
- `apps/mobile/src/screens/chat/ChatScreen.tsx:175` — `useEffect` missing
  `closeCrisisDrawer`
- `apps/mobile/src/screens/chat/ChatScreen.tsx:68`, `:388` — `openDrawer` and
  `handleNewChat` assigned but never used. Given commit `a2734fd`
  ("simplify the header new chat handler"), this looks like an unfinished refactor.

## pnpm audit — 191 advisories: 6 critical, 109 high, 61 moderate, 15 low

All 6 criticals are transitive. **Four originate from `firebase-admin`**:
`fast-xml-parser` (via `@google-cloud/storage`), `protobufjs` (via `@google-cloud/firestore`),
`websocket-driver` (via `@firebase/database`), plus its tree. The other two are
`handlebars` (via `ts-jest`, dev-only) and `tar`/`shell-quote` (via `expo-updates` →
`@expo/cli`, tooling).

`firebase-admin` exists solely for App Check verification, which is off by default and —
per M4 and the unimplemented client side — cannot currently be turned on. That is a large
critical-vulnerability surface carried for a feature that does not work. `next` alone
carries 14 high advisories.

## expo-doctor — 15/18 passed

- Metro config mismatch: `resolver.disableHierarchicalLookup` expected `false`, got `true`
- Duplicate native module `expo-constants`: `18.0.11` (root) vs `18.0.13` (nested under
  `expo-linking`)
- 14 packages off SDK 54: `react-native-reanimated` a **major** behind (`3.17.5` vs
  `~4.1.1`), `react-native-svg`/`react-native-webview` a minor ahead, 11 patch-level

Note on reanimated: nothing in `apps/mobile/src` imports it — it appears only as a plugin
in `babel.config.js`, and the only "reanimated" hits in the built bundle are the unrelated
zero-dependency `react-native-reanimated-table` (pulled in by `react-native-marked`) plus
a comment in `react-native-screens`. The major mismatch is likely inert. Do not treat it as
the default explanation for a runtime crash.

## knip — dead code and dependency drift

19 unused files, 11 unused dependencies, 5 unused devDependencies, 4 unlisted
dependencies, 94 unused exports, 61 unused exported types.

Verified by hand:
- `apps/mobile/src/components/animation/UnicornAnimation.tsx` has **no importers**. It is
  the WebView that renders `${EXPO_PUBLIC_API_URL}/animation`, so the backend's
  `/animation` page and its `unicornstudio-react` dependency exist to serve a component
  nothing mounts.
- `@react-navigation/bottom-tabs` — unused (see docs section).
- `expo-auth-session`, `expo-web-browser`, `expo-linking` — unused.

Unlisted (resolving only by hoisting, fragile): `expo-constants`
(`ExercisePlayerScreen.tsx:17`), `expo-system-ui` (`app.json`), `@jest/globals` (eval tests).

Unused backend deps: `autoprefixer`, `class-variance-authority`, `clsx`, `pino-http`,
`tailwind-merge`. Unused root dep: `expo-updates`.

## Coverage

| Package | Statements | Branches |
| --- | --- | --- |
| `@mani/backend` | 57.8% | 46.3% |
| `@mani/api` | 75.9% | 71.7% |

Zero-coverage, security-relevant: `src/proxy.ts` (the request gatekeeper, 70 lines),
`lib/security/appCheckVerifier.ts`, `lib/supabase-ssr.ts`, `lib/supabase.ts`,
`lib/firebase-admin.ts`, `services/index.ts`.

Barely covered data layer: `lib/db/threads.ts` 6%, `messages.ts` 8%, `providers.ts` 10%,
`prompts.ts` 13%, `summaries.ts` 20%.

`services/messages.ts` — the 1,600-line chat orchestrator holding most of the CRITICAL and
HIGH findings above — sits at 70.9% statements / 60.9% branches, and none of the
regeneration paths implicated in H3 are covered.

## Clean results

- Production build (`pnpm turbo build --filter=@mani/backend`) passes in 14s, 21 routes.
  So the `transpilePackages` omission below is cosmetic.
- `supabase db lint` — no schema errors.
- `tsc --noEmit` — all 4 packages pass (after the two fixes in the setup session).
- 666 tests pass (api 76, backend 353, mobile 237). Note: passing, not necessarily
  meaningful — the test-quality pass did not complete.
- Every tRPC procedure uses `verifiedEmailProcedure` or `fullyProtectedProcedure`; there
  is no unauthenticated procedure. `publicProcedure`/`protectedProcedure`/
  `appAuthorizedProcedure` are exported but unused.
- Admin authorization reads `app_metadata.admin_role`, not the user-writable
  `user_metadata`, and `requireAdmin()` is called in every admin page and all 27 server
  actions.
- RLS is enabled on all four public tables.

---

# Configuration issues

1. **`turbo.json` `globalEnv` is missing 12 of the env vars the code reads** — see M2.
   Missing: `ADMIN_EDITING_ENABLED`, `AI_DEBUG_MODE`, `API_URL`, `APP_API_KEY`,
   `APP_AUTH_MODE`, `CRISIS_BLOCKS_CHAT`, `FIREBASE_*` (3),
   `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, `PROMPT_DEBUG_LAYERS`.
   (`OPENROUTER_API_KEY` is read dynamically via `process.env[envKeyName]` in
   `llm.ts:124`, so static greps under-report it — it is declared.)
2. **Backend `__tests__` excluded from eslint** — see M3.
3. **`packages/design-tokens` has no eslint config and no `lint` script** — never linted.
4. **`turbo.json` declares `build` with `outputs: ["dist/**"]` and
   `lint.dependsOn: ["^build"]`, but 3 of 4 packages have no `build` script.** Vestigial.
   Likewise `packages/api`'s `composite`/`declaration`/`outDir: ./dist` is dead config —
   the package is consumed as source via its `exports` map.
5. **`vercel.json` and `README.md` disagree about the Vercel root.** `vercel.json` sets
   `outputDirectory: apps/backend/.next` (repo-root-relative); `README.md:158` says to set
   Vercel's root directory to `apps/backend`. Applying both resolves to
   `apps/backend/apps/backend/.next`.
6. **`next.config.js` lists `@mani/api` in `transpilePackages` but not
   `@mani/design-tokens`**, which `src/app/animation/page.tsx:4` imports as raw
   TypeScript. The build passes (Turbopack covers it), so this is an inconsistency to
   resolve deliberately, not a defect.
7. **`eas.json` build profiles define no `channel`**, yet `app.json` sets `updates.url`
   and the mobile `publish` script targets `eas update --branch preview`. OTA
   branch/channel mapping is unwired — and `expo-updates` is itself unused.
8. **`[inbucket]` is deprecated** in Supabase CLI 2.117 (`[local_smtp]` now). Left alone
   because renaming breaks older CLIs.
9. **`apps/mobile/package-lock.json` (669 KB) is tracked** despite root `.gitignore`
   listing `package-lock.json` — gitignore does not untrack existing files. An
   `npm install` in that directory would fight pnpm.
10. **`supabase/.branches/_current_branch` and `supabase/.temp/cli-latest` are tracked**
    at the repo root, left over from running the CLI outside `apps/backend`. The latter is
    rewritten on every CLI run, so it dirties the working tree.

---

# Docs that contradict the code

These matter more than usual: `CLAUDE.md` is loaded into every AI session on this repo, so
a wrong statement there is actively harmful.

1. **Root `CLAUDE.md` "Mobile Navigation Structure" is largely fictional.** It documents
   `TabNavigator (bottom tabs)` with `DashboardStack`, `AboutStack`, `InformationScreen`
   and `AboutScreen`. Reality: four `createNativeStackNavigator` instances and **zero** tab
   navigators; `@react-navigation/bottom-tabs` is unused; `InformationScreen` and
   `AboutScreen` do not exist. Undocumented but real: `OnboardingScreen`, `chat`,
   `exercises`, `ChangeEmailScreen`, `ChangePasswordScreen`.
2. **`prompts/title_generation.md` is dead.** No reference to `title_generation` exists in
   `apps/backend/src` or `packages/api/src`; `prompts.ts` hardcodes a different instruction
   inline. The CLAUDE.md-prescribed workflow of editing the file and re-seeding changes
   nothing.
3. **`prompts/summarization.md` is dead** — see H4.
4. **The documented "constraints last" invariant breaks on long threads.** The thread
   summary is appended *after* `response_format` (`services/messages.ts:650-656`), and the
   `AI_DEBUG_MODE` block after that. So on exactly the threads where behaviour matters
   most, constraints are no longer the final layer. Layers 1-6 are otherwise in the
   documented order. REPORTED.
5. **`buildUserContext` emits only `nickname`**, dropping the documented "topics"
   (`services/prompts.ts:219-229`).
6. **`ExpoGO(Setup).md` lists `expo-auth-session`** among native deps "it uses" — unused.
7. **`README.md` and root `CLAUDE.md` say Next.js 15**; backend is on `next@^16.0.8`.
8. **`README.md` cites `.tool-versions`** for the Node version; no such file exists.
9. **`apps/backend/CLAUDE.md` documents `GOOGLE_APPLICATION_CREDENTIALS`**, which nothing
   reads, and omits `OPENROUTER_API_KEY`, the actual primary LLM credential.
10. **`seed.sql:6` and `scripts/seed-prompts.ts:8`** tell you to run `pnpm db:seed:prompts`
    (the script is `db:seed`) and point at `supabase/prompts/` (prompts live in
    `apps/backend/prompts/`).
11. **`NarcissisticDynamics`** is an accepted category in `scripts/seed-exercises.ts` and
    listed in root `CLAUDE.md`, but no exercise in `library_audio/exercises.json` uses it.

---

# Suggested order of work

Not a mandate — the triage is yours.

1. **C1** — one line: pass `ctx.userId` through `messages.list` → `list` → `getForThread`.
   Smallest fix, largest consequence.
2. **C3 + H2** — reject `chat()` on a crisis-flagged thread, and restrict the `threads`
   UPDATE grant to specific columns.
3. **C2** — add a `WITH CHECK` on `messages` INSERT validating thread ownership, or revoke
   `INSERT` from `authenticated` entirely (the app writes via the service role anyway).
4. **H3** — move the crisis check ahead of the regeneration paths, or carry `crisis`
   forward across retries.
5. **H1** — add `/admin/auth/callback` to the `proxy.ts` allow-list.
6. **H4** — decide whether summarisation runs on OpenRouter or OpenAI, then make the code
   and the seeded prompt agree. **H5** — add the missing `.limit()`.
7. Acting on the `route.ts:100-115` TODO — a user-JWT-scoped Supabase client for
   `publicClient` — would have neutralised C1, C2 and H2 at the database layer. Worth
   considering as the structural fix rather than patching each call site.
8. **M1/M3** — get `pnpm lint` to zero and stop excluding `__tests__`, so the next
   regression of this class is caught mechanically.
9. Consider dropping `firebase-admin` until App Check is actually implemented — it carries
   4 of the 6 critical advisories for a non-functional feature.

# Second pass — database, tests, service internals

Completed after the initial write-up. Mobile remains the only uncovered domain.

## C4 (CRITICAL, new) — unauthenticated forged message injection via RPC

**PROVEN reachable.** `public.insert_message_pair`, created by
`migrations/20260127000000_add_atomic_message_pair_insert.sql`

The function is `SECURITY DEFINER` owned by `postgres`, so it **bypasses RLS entirely**.
`EXECUTE` is granted to both `authenticated` **and `anon`**. Its signature takes
`p_user_id` and `p_thread_id` as caller-supplied parameters, and the body performs **no
validation whatsoever** — no `auth.uid() = p_user_id` check, no thread-ownership check.
It inserts a `user` row and a `mani` row, and the message-count trigger fires.

Probed with only the bundled anon key and **no `Authorization` header**, using a
deliberately non-existent `user_id` so nothing would be written:

```
POST /rest/v1/rpc/insert_message_pair
→ 23503  "Key (user_id)=(…099) is not present in table \"users\""
```

Execution reached the INSERT. The only thing that stopped it was the
`messages_user_id_fkey` foreign key — i.e. the sole remaining barrier is knowing a real
`user_id`, and both UUIDs appear in `/admin/chats/[id]` URLs and application logs.
Verified nothing persisted (`count = 0`).

This is strictly worse than C2: no account required, `user_id` is forgeable (so messages
can be attributed to another user), and RLS does not apply. An attacker can write
fabricated `role: 'mani'` turns into a stranger's therapy conversation.

Note the irony: `createPair` correctly uses this RPC to get real atomicity
(`lib/db/messages.ts:336`) — the transactional fix is also the security hole.

## Database — remaining findings

| Sev | Finding | Evidence |
| --- | --- | --- |
| 🔵 LOW | **3 `SECURITY DEFINER` functions with unpinned `search_path`**: `insert_message_pair`, `increment_thread_message_count`, `decrement_thread_message_count`. **Not currently exploitable** — `authenticated` and `anon` have no `CREATE` on `public`, `admin`, or `extensions`, so the shadowing attack has no foothold. Hardening only (Supabase's own linter flags this class) | `pg_proc.proconfig` NULL; `has_schema_privilege(…,'CREATE') = false` |
| 🔵 LOW | **6 redundant indexes** — write overhead for no read benefit. `idx_messages_user_id` is a prefix of `idx_messages_user_created`; `idx_threads_user_id` of `idx_threads_last_message`; `idx_completions_user` of `idx_completions_user_recent`; `idx_admin_prompts_name` duplicates `prompts_name_key`; `idx_admin_providers_name` duplicates `providers_name_key`; `idx_thread_summaries_thread` duplicates `thread_summaries_thread_id_key` | `pg_indexes` |
| 🔵 LOW | **3 un-indexed FKs, all `ON DELETE NO ACTION`**: `thread_summaries.last_summarized_message_id → messages`, `admin.prompts.created_by → auth.users`, `admin.prompt_versions.created_by → auth.users`. Deleting a referenced row requires a scan, and NO ACTION means it can be blocked outright | `pg_constraint` join |
| 🔵 LOW | `src/types/supabase.ts` is **Prettier-formatted**, but `supabase gen types` emits unformatted output — so `pnpm db:types` always produces an ~820-line spurious diff. Same root cause as the `pnpm-lock.yaml` churn | normalized diff |

**Ruled out (checked, not defects):**
- **`src/types/supabase.ts` has no schema drift.** The 820-line raw diff is entirely
  semicolons, quote style, and line wrapping — zero table, column, or enum differences.
- **Thread deletion with a summary checkpoint works.** I feared the NO ACTION FK on
  `last_summarized_message_id` would block the cascade. Tested inside a transaction and
  rolled back: `DELETE 1`, remaining messages `0`. Postgres orders the cascade correctly.
- **The message-count triggers are race-free.** `message_count = message_count + 1` in a
  single UPDATE is atomic under row locking; decrement uses `GREATEST(…, 0)`.
- **`supabase db lint`** — no schema errors.
- **Index coverage for the hot query is correct**: `messages.list` filters `thread_id` and
  orders `created_at DESC`, served by `idx_messages_thread (thread_id, created_at)` via a
  backward scan.

## Service internals — concurrency and transaction boundaries

| Sev | Finding | Location |
| --- | --- | --- |
| 🟡 MEDIUM | **Up to 8 independent writes per chat turn with no surrounding transaction.** Only the message pair is transactional. If any later write fails, the messages persist while thread state is partially updated — technique recorded but phase unset, style not appended, `last_message_at` stale, title lost. The service logs and continues | `services/messages.ts` L1259 (pair), then L1302, L1324, L1367, L1402, L1421, L1442, L1464 |
| 🟡 MEDIUM | **Two read-modify-write lost-update races.** `addTechniquesOffered` and `appendResponseStyle` both SELECT the row, merge in JS, then UPDATE. Two concurrent turns on one thread — plausible given the floating promise on send (`ChatScreen.tsx:393`) and no rate limiting (M6) — silently discard one append. `client_message_id` idempotency protects message rows but **not** these thread updates. Postgres `array_append`/jsonb concat would make each a single atomic statement | `lib/db/threads.ts` ~206-225 and ~328-350 |

**Ruled out:** `createPair` genuinely is atomic — it delegates to the `insert_message_pair`
RPC rather than issuing two INSERTs (`lib/db/messages.ts:336`). The docblocks at
`services/messages.ts:445` and `lib/db/messages.ts:280` claiming transactional storage are
accurate, but they apply *only* to the message pair, not to the thread-state writes above.

## Test quality

| Sev | Finding | Location |
| --- | --- | --- |
| 🟡 MEDIUM | **No `coverageThreshold` in any jest config** — coverage can regress to zero without failing CI. Backend is already at 57.8% | `apps/backend/jest.config.js`, `apps/mobile/jest.config.js`, `packages/api/jest.config.js` |
| 🟡 MEDIUM | **Degradation paths are exercised without asserting their logs** — a direct violation of the project standard "if logs are expected to contain errors, these MUST be captured and tested". `messages.test.ts` triggers the script-leakage path, so the suite prints `WARN: Script metadata leaked into response, regenerating`, `WARN: Regenerated response still contains script metadata, stripping`, and `INFO: Regenerated response after script leakage` — none asserted. Only `llm.test.ts:24` mocks the logger; `test/setup.ts` does not silence pino | `src/services/__tests__/messages.test.ts`; `test/setup.ts`; `lib/logger.ts:10` |
| 🟡 MEDIUM | **Unconditional `console.debug`/`console.warn` in a production router** — not gated by any debug flag, so `[Chat Context] Summary state` and `[Chat Context] Built context` log thread ids and summary metadata in production as well as in tests | `packages/api/src/routers/messages.ts:196, 204, 213, 277, 315` |
| 🔵 LOW | Property-based generators emit random strings (`shape: "AQ\krIhF)-"`, `voice: "K. y_8P"`) that flow into logged thread state, making test output hard to read | `packages/api/src/test/mockGenerators.ts` |
| 🔵 LOW | `test/setup.ts` suppresses any `console.error` whose first argument contains `"not wrapped in act"`. Reasonable in intent, but it is a substring match that could mask an unrelated real error | `apps/backend/test/setup.ts:14-20` |

**Ruled out — the suite is not predominantly tautological.** Census across all 35 test
files: 1,168 `expect()` calls, of which 227 (**19.4%**) are mock-call assertions
(`toHaveBeenCalled*`). The bulk are real value assertions — 472 `toBe`, 79
`rejects.toThrow`, 54 `toEqual`, 30 `toMatchObject`. No module is mocked such that the
code under test doesn't execute. This is a healthier ratio than the zero-coverage areas
suggested, and I found no instance of a test asserting only that a mock was called.

# Third pass — mobile app

All 114 files in `apps/mobile/src` accounted for: the 12 largest read in full, the
remainder covered by eslint, knip, and targeted pattern sweeps (uncancelled timers,
unremoved listeners, swallowed catches, unawaited promises).

## H10 (HIGH) — font loading gates the whole app with no failure path

**This is the most likely explanation for the Android "loads for minutes, then
Something went wrong" symptom.**

`hooks/useFonts.ts:15-31` calls `useExpoFonts` for **7 faces** and returns **only**
`fontsLoaded` — `error` is logged and then discarded:

```ts
const [fontsLoaded, error] = useExpoFonts({ /* 7 faces */ });
if (error) console.error('Font loading error:', error);
return fontsLoaded;
```

`App.tsx:81` hard-gates the entire tree on it:

```tsx
if (!fontsLoaded) return <View><ActivityIndicator /></View>;
```

So **any** font-loading failure leaves `fontsLoaded === false` forever: an indefinite
spinner, no timeout, no retry, no degraded render. Expo Go eventually gives up and shows
its own error screen. The caller cannot react to the failure because the hook throws the
error away.

Weight of the payload in Expo Go, where assets are fetched over the LAN from Metro:

| Face | Bytes |
| --- | --- |
| Urbanist Medium / SemiBold / Bold | 42,748 / 42,736 / 42,632 |
| Montserrat Regular / Medium / SemiBold / Bold | 330,948 / 330,872 / 333,988 / 335,788 |

**~1.46 MB of fonts on top of the 9.4 MB dev bundle**, all required before first paint.
On a flaky or partially-blocked LAN this is exactly the shape of failure observed.

## H11 (HIGH) — no error boundary anywhere in the app

Verified: zero occurrences of `ErrorBoundary`, `componentDidCatch`, or
`getDerivedStateFromError` in `apps/mobile/src` or `App.tsx`. Any render-time throw
anywhere in the tree unmounts the whole app and surfaces as the Expo Go / red-box error
screen with no in-app recovery. Combined with H10 and `retry: false` (below), the app has
no resilience layer at all.

## Mobile findings

| Sev | Finding | Location |
| --- | --- | --- |
| 🟡 MEDIUM | **`AuthProvider`'s `useMemo` never memoizes.** `profile` and `pendingFlow` are recomputed through `safeParse` on every render, producing new object identities, and both sit in the memo's dependency array. So `contextValue` is a fresh object every render and **every `useAuth()` consumer re-renders whenever `AuthProvider` renders** — the memo and its 30-entry dep array accomplish nothing | `providers/AuthProvider.tsx:168-169`, deps at `:559-560` |
| 🟡 MEDIUM | **`ensureAuthenticated` has no in-flight guard.** `if (session) return;` then `signInAnonymously()`. Two near-simultaneous callers both observe `session === null` and both create an anonymous account | `providers/AuthProvider.tsx:171-182` |
| 🟡 MEDIUM | **Reads a config key that does not exist.** `Constants.expoConfig?.extra?.apiUrl` — `app.json`'s `extra` is `{"eas":{"projectId":…}}` only, so `API_URL` **always** falls back to `http://localhost:3001`, which on a physical device is the phone itself. Currently masked because signed audio URLs are absolute, so the branch is dead — but it is a live trap, and it is inconsistent with the rest of the app, which uses `EXPO_PUBLIC_API_URL`. It also relies on `expo-constants`, an **undeclared** dependency with **two installed versions** | `screens/exercises/ExercisePlayerScreen.tsx:26` |
| 🟡 MEDIUM | **Background audio requested but not permitted.** `Audio.setAudioModeAsync({ staysActiveInBackground: true })` while `app.json` declares no `UIBackgroundModes: ["audio"]` — background playback cannot work on iOS | `ExercisePlayerScreen.tsx` (~:105); `app.json` `ios.infoPlist` |
| 🟡 MEDIUM | **Ref mutated during render.** `wasShowingOnboardingRef.current = showOnboarding` runs in the component body, and the comment concedes "order matters". Under React 19 concurrent/double-invoked rendering, `justCompletedOnboarding` can be derived from a render that was discarded, so the app can land on the wrong initial screen after onboarding | `navigators/RootNavigator.tsx:~54-56` |
| 🟡 MEDIUM | **6 uncancelled `setTimeout`s**, all in event handlers, none stored in a ref or cleared. Rapid taps on two nav items queue two navigations; if the drawer unmounts before a timer fires, the callback runs against an unmounted parent — including `onOpenCrisisDrawer`, the crisis path | `components/chat/ChatDrawer.tsx:124, 131, 138, 146, 153, 160` |
| 🟡 MEDIUM | **`retry: false` globally with no `staleTime` or `networkMode`.** A single transient network blip yields a terminal error state, and with no error boundary there is nothing above it to recover | `util/api/queryClient.ts` |
| 🔵 LOW | **`Text.defaultProps` mutation is a no-op on React 19**, which removed `defaultProps` for function components. The comment claims it is "the only way to affect library components", but the font-scaling protection it is meant to provide silently does not apply | `App.tsx:29-31` |
| 🔵 LOW | `isAnonymous = user?.is_anonymous ?? true` — a signed-**out** user is reported as anonymous, conflating "no session" with "anonymous session" | `providers/AuthProvider.tsx:167` |
| 🔵 LOW | Device-id fallback is never persisted and the caught `error` is discarded, so if SecureStore throws the device gets a new id on **every** launch | `services/security/deviceId.ts:42-47` |
| 🔵 LOW | Notification preference read *and* write both `catch { // Silently fail }` — the toggle silently fails to persist with no user feedback | `hooks/useNotificationPreference.ts:18, 29` |
| 🔵 LOW | Two sequential `updateUser` calls where the second sets `pending_flow`. If it fails, the email-change / password-reset flow is mid-state with no metadata to resume from | `providers/AuthProvider.tsx:420 & 430`, `:354 & 368` |
| 🔵 LOW | `updateProfile` decides to force sign-out by string-matching `error.message.includes('does not exist')` — breaks silently if the upstream message text changes | `providers/AuthProvider.tsx:193-198` |
| 🔵 LOW | `getUserProfile` swallows all errors and returns null, so the nickname prompt layer is dropped silently on a transient failure | `packages/api/src/routers/messages.ts:142` |
| 🔵 LOW | Audio cleanup calls `unloadAsync()` without awaiting or catching — an unhandled rejection if it fails during unmount | `ExercisePlayerScreen.tsx` (~:157) |

## Mobile — ruled out (checked, not defects)

- **No double-submit on send.** `handleSend` guards `chatMutation.isPending` and
  `isChatBlocked` before doing anything (`ChatScreen.tsx:302-303`). My earlier note citing
  `ChatScreen.tsx:393` as a send-path floating promise was imprecise — line 393 is
  `Haptics.impactAsync` inside `handleNewChat`. This lowers the likelihood of the
  read-modify-write races in `lib/db/threads.ts`: reaching them needs a non-UI caller
  (a retry, the CLI, a second device), not a double-tap.
- **`BackHandler` is correctly cleaned up** — `return () => backHandler.remove()`
  (`OnboardingScreen.tsx:126`).
- **Audio is unloaded on unmount** and on `audioUrl` change, with an `isMounted` guard
  that unloads a sound that arrives late. No gross leak.
- **The `react-native@0.81.5` patch is clean** — only the version strings `19.1.0` →
  `19.1.2` across the three renderer implementations, no logic changes. Exactly what
  `README.md` describes.
- **No leaked intervals or listeners** anywhere else in `apps/mobile/src`.
- **Most `catch {}` blocks are deliberate and commented** (Server Component cookie
  writes, "not a structured error — fall through"), not swallowed failures.

# Coverage of the repository — completeness statement

Read in full or audited directly: all of `packages/api/src`, `apps/backend/src`
(services, lib, db, security, app routes, proxy, constants), all 24 migrations plus the
live schema, `apps/backend/scripts`, `apps/backend/prompts`, the 12 largest
`apps/mobile/src` files, every config file in the repo, `patches/`, and all root docs.

Covered by tooling and pattern sweeps rather than line-by-line reading: the remaining
~100 small `apps/mobile/src` components, `apps/backend/src/components/admin`,
`packages/design-tokens/src` (285 lines, data plus one `generateCSSVariables` function),
and the test suites — via eslint (606 problems), knip, coverage instrumentation, and
targeted greps for timers, listeners, swallowed catches and unawaited promises.

Not examined, and judged not worth it: `apps/backend/ITERATION_LOG.md` (50 KB dev log,
not code), `library_audio/` (18 MP3s, validated against the manifest during setup),
`apps/mobile/assets/`, `apps/backend/public/`, `.claude/skills/`, and `__mocks__/`
directories.
