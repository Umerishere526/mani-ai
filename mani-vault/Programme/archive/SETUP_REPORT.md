> **ARCHIVED — evidence, not instructions.** Point-in-time record. Parts of this are
> superseded; see `README.md` in this folder for exactly which. Current instructions live
> in `../START-HERE.md`, and where the two disagree, that one wins.

# Mani — end-to-end setup report

Repo set up from a clean clone and verified running on Expo Go infrastructure.
Everything below was executed and observed, not assumed.

---

## 1. Status

| Area                     | State                                                |
| ------------------------ | ---------------------------------------------------- |
| Dependencies             | Installed — 1622 packages, react-native patch applied |
| Local Supabase           | 12/12 containers healthy, 25 migrations applied      |
| Seed data                | 5 prompts, 18 exercises, 18 storage objects, 5 users |
| Backend API              | Running on `:3001`                                   |
| Metro bundler            | Running on `:8081`, Expo Go mode                     |
| Type checks              | 4/4 packages pass                                    |
| Tests                    | 35 suites, 666 tests, all pass                       |
| Chat (real LLM)          | Verified — Gemini 3 Flash via OpenRouter             |
| Exercise audio on device | Verified — signed URL fetched over LAN, 200, 5.3 MB  |

The one thing not verified is the phone itself. Scanning the QR code is yours to do —
see [§6](#6-what-is-left-for-you).

### Environment

| Tool   | Version | | Value |
| ------ | ------- |-| ----- |
| node   | 24.20.0 | LAN IP | `192.168.88.100` |
| pnpm   | 9.15.1  | Supabase CLI | 2.117.0 |
| Docker | 29.7.2  | | |

---

## 2. What is running

| Port  | Service         | URL                          |
| ----- | --------------- | ---------------------------- |
| 3001  | Backend API     | http://192.168.88.100:3001   |
| 8081  | Metro bundler   | http://192.168.88.100:8081   |
| 54331 | Supabase (Kong) | http://192.168.88.100:54331  |
| 54332 | Postgres        | `postgres:postgres@…:54332`  |
| 54333 | Supabase Studio | http://localhost:54333       |
| 54334 | Mailpit (email) | http://localhost:54334       |

Seed logins, all with password `testpassword123`:

| Email             | UUID                                   | Access             |
| ----------------- | -------------------------------------- | ------------------ |
| admin@example.com | `a0000000-0000-4000-8000-000000000001` | Admin portal       |
| user@example.com  | `a0000000-0000-4000-8000-000000000002` | Mobile (default)   |
| test1–3@example.com | `…-0000000000{11,12,13}`             | Parallel style tests |

---

## 3. Changes made

Seven files. Each one is either required for setup to work or fixes something broken.

### `apps/backend/package.json` — bumped the Supabase CLI

`supabase` was pinned at `^2.65.0`. `ExpoGO(Setup).md` claims the repo is already at
`^2.116.0` and that this pin is what prevents the storage-migration crash loop
documented in its troubleshooting section. It wasn't. Bumped to `^2.116.0`, resolving
to 2.117.0. Supabase then came up clean on the first attempt — no crash loop.

### `apps/backend/supabase/seed.sql` — fixed invalid seed UUIDs (**bug**)

See [§4](#4-the-bug). Two seed users had non-RFC UUIDs that made chat return HTTP 500.

### `apps/backend/src/services/__tests__/{exercises,threads}.test.ts` — fixed type errors

Two pre-existing `tsc` failures on `main`, unrelated to my work. Both were mock
factories missing a required field, so spreading `Partial<T>` over them left the field
optional and the return type stopped satisfying `T`:

- `createMockExercise` was missing `subtitle` → added `subtitle: null`
- `createMockThread` was missing `responseStyles` → added `responseStyles: []`

Worth knowing because the repo's own `Stop` hook in `.claude/settings.local.json` runs
`lint:types` on every turn, so these were failing on every session.

### `.prettierignore` (new) — stopped lockfile diff churn

Root `lint:fix` runs `prettier --write '**/*' --ignore-unknown`, and with no root
`.prettierignore` that reformats `pnpm-lock.yaml`. pnpm then rewrites it canonically on
the next install. The two tools flip-flop forever, so any install produces a ~10,000
line spurious diff.

**This is why `pnpm-lock.yaml` looks enormous in the diff.** The only semantic change
in it is the two-line supabase bump; the rest is de-prettification. Committing it is
correct — it restores pnpm's own format, and the new ignore file stops the loop.

### `apps/mobile/.env.example`, `apps/backend/.env.example` — documented what setup needs

Additive only. Added `EXPO_NO_METRO_WORKSPACE_ROOT=1` (the doc calls it required but it
was absent from the example), local-Supabase URL guidance, and `OPENROUTER_API_KEY`
— which `seed.sql` tells you to set but neither `.env.example` nor
`apps/backend/CLAUDE.md` ever lists.

### `ExpoGO(Setup).md` — corrected the walkthrough

The doc could not be followed to completion as written. Fixes in
[§5](#5-corrections-to-expogosetupmd).

---

## 4. The bug

`pnpm test:chat "I lost my phone"` returned HTTP 500 from `messages.chat`:

```
ZodError: [{ "code": "invalid_format", "format": "uuid",
             "path": ["userId"], "message": "Invalid UUID" }]
  at getOrCreateThread
```

**Root cause.** Zod v4's `.uuid()` enforces RFC 9562 — the version nibble must be 1–8
and the variant nibble 8/9/a/b, with only the nil and max UUIDs exempt. `seed.sql` gave
`admin@example.com` the id `00000000-0000-0000-0000-000000000001` and
`user@example.com` `…002`. Both have a `0` version nibble, so neither is a valid UUID.
Postgres's `uuid` column accepts any 128-bit hex, so nothing rejected them at insert.

Three schemas validate `userId` this way — [threads.ts:36](apps/backend/src/lib/schema/threads.ts#L36),
[messages.ts:58](apps/backend/src/lib/schema/messages.ts#L58),
[summaries.ts:55](apps/backend/src/lib/schema/summaries.ts#L55).

`test1`–`test3@example.com` already used `a0000000-0000-4000-8000-0000000000NN`, which
is correct v4. That is why `--user 1|2|3` worked and the default `--user 0` never did.

**Fix.** Brought the two older users onto the convention the same file already used,
rather than relaxing the schema. The schema's intent is a real UUID; loosening it to
accommodate fake test data would weaken validation production traffic depends on. Both
literals appeared only in `seed.sql`, so the change is contained. The provider rows at
`seed.sql:226` and `:248` share the malformed shape but are never UUID-validated, so
they were deliberately left alone.

**Blast radius: none for real users.** [AuthProvider.tsx:174](apps/mobile/src/providers/AuthProvider.tsx#L174)
uses `signInAnonymously()` and `signUp()`, and Supabase mints proper v4 UUIDs. This only
ever broke the seed accounts — which is exactly what local testing and the Expo Go
walkthrough use.

Verified after `supabase db reset` + re-seed:

```
Mani: You lost your phone. How can I support you right now?
```

Multi-turn via `--thread` also verified.

---

## 5. Corrections to `ExpoGO(Setup).md`

**No step created `apps/backend/.env`.** Steps 6 and 7 as written could not work on a
clean clone — both seed scripts and the API server read it, and the scripts
`process.exit(1)` without `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`. Added as a new
step 6; later steps renumbered.

**"Keep the legacy `EXPO_PUBLIC_SUPABASE_ANON_KEY` from `.env.example`"** — there was
no key there to keep, only the placeholder `your-anon-key`. Now points at
`supabase status`.

**Backend `SUPABASE_URL` must be the LAN IP, not loopback.** This wasn't in the doc at
all and would have cost you real debugging time.
[exercises.ts:25](apps/backend/src/services/exercises.ts#L25) builds audio URLs with
`createSignedUrl`, and the host comes from whatever `SUPABASE_URL` the service client
was built with. Point it at `127.0.0.1` and the phone gets a loopback URL it cannot
fetch — the app runs fine and audio silently fails. Verified with the LAN IP set:
signed host came back `http://192.168.88.100:54331`, MP3 fetched 200 / 5.3 MB.
`NEXT_PUBLIC_SUPABASE_URL` can stay on loopback; it only serves the admin login UI.

**What the doc got right.** The Metro 404 explanation is accurate — I confirmed
`getMetroServerRoot` returns early on `EXPO_NO_METRO_WORKSPACE_ROOT` at
`node_modules/@expo/config/build/paths/paths.js:156`. With the flag set, the manifest
serves `http://192.168.88.100:8081/index.bundle?platform=ios&…` with no `apps/mobile/`
prefix. The storage crash loop and its CLI-version cause also check out.

---

## 6. What is left for you

**Scan the QR code.** Metro is running in Expo Go mode on `:8081`. Everything
server-side is verified, but I cannot hold a phone.

**One risk to watch when you scan.** Metro warns that `react-native-reanimated` is a
major version behind what SDK 54 expects — `3.17.5` installed, `~4.1.1` expected. Expo
Go ships its own native reanimated, so a JS/native mismatch here is the single most
likely cause if the app hard-crashes on load. Mitigating factor: nothing in
`apps/mobile/src` imports reanimated, it appears only as a plugin in
`babel.config.js`, so it may never be exercised. I flagged this rather than upgrading
because moving reanimated 3 → 4 is a breaking change and your call, not mine.

`react@19.1.2` also appears in that warning list against an expected `19.1.0`. That one
is deliberate — see the `react-native@0.81.5` patch note in `README.md`.

**Optional: `OPENAI_API_KEY`.** Only [summary.ts:64](apps/backend/src/services/summary.ts#L64)
uses it, for conversation summary extraction. Chat works without it; summaries will
throw when they trigger. Everything else is filled in.

---

## 7. Found but deliberately not fixed

Unrelated to setup, recorded rather than changed. Details in
`journal/2026-09-08-repo-setup-and-doc-gaps.md`.

**Deprecation from the CLI bump.** 2.117.0 warns `config section [inbucket] is
deprecated, use [local_smtp]`. Renaming it would break anyone still on 2.65 and
`[inbucket]` still works — worth doing once everyone has upgraded.

**Stale docs.**

- `README.md` cites `.tool-versions` for the Node version; no such file exists.
- `README.md` and root `CLAUDE.md` say Next.js 15; backend is on `next@^16.0.8`.
- `apps/backend/CLAUDE.md` documents `GOOGLE_APPLICATION_CREDENTIALS`, which nothing
  reads. App Check uses `FIREBASE_PROJECT_ID` / `_CLIENT_EMAIL` / `_PRIVATE_KEY`.
- `seed.sql:6` and `scripts/seed-prompts.ts:8` tell you to run `pnpm db:seed:prompts`;
  the script is `db:seed`. Both also point at `supabase/prompts/`; prompts live in
  `apps/backend/prompts/`.
- `PROMPT_DEBUG_LAYERS` and `API_URL` are read by code but undocumented.

**Repo hygiene.**

- `apps/mobile/package-lock.json` (669 KB) is tracked despite root `.gitignore` listing
  `package-lock.json` — gitignore does not untrack existing files.
- `supabase/.branches/_current_branch` and `supabase/.temp/cli-latest` are tracked at
  the repo root, left over from running the CLI outside `apps/backend`. The latter is
  rewritten on every CLI run, so it dirties the tree.
- Root `package.json` carries `expo-updates@~29.0.16` as a direct dependency while
  `apps/mobile` declares `~29.0.15`. The root entry looks unintentional.
- `NarcissisticDynamics` is an accepted category in `scripts/seed-exercises.ts` and is
  listed in root `CLAUDE.md`, but no exercise in `library_audio/exercises.json` uses it.

---

## 8. Cold restart

```bash
# 1. Supabase (Docker must be running)
cd apps/backend && npx supabase start

# 2. Backend
pnpm dev:backend                      # from repo root, serves :3001

# 3. Metro
cd apps/mobile && npx expo start --go
```

Re-check your LAN IP whenever you change networks — it is hardcoded in
`apps/mobile/.env` (2 values) and `apps/backend/.env` (`SUPABASE_URL`):

```bash
ipconfig getifaddr en0
```

Health check:

```bash
for p in 3001 54331 8081; do
  printf "%s: " $p
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 && echo LISTENING || echo DOWN
done
```

After editing any prompt in `apps/backend/prompts/`, re-seed — markdown changes are not
synced automatically:

```bash
cd apps/backend && pnpm db:seed
```

`supabase db reset` also drops prompts, exercises and `storage.objects`. Re-run both
`pnpm db:seed` and `pnpm db:seed:exercises` after one.
