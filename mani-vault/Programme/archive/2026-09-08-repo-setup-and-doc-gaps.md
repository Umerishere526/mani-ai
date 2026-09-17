> **ARCHIVED — evidence, not instructions.** Point-in-time record. Parts of this are
> superseded; see `README.md` in this folder for exactly which. Current instructions live
> in `../START-HERE.md`, and where the two disagree, that one wins.

# 2026-09-08 — Fresh-clone setup and doc gaps

> A full repository audit followed this session — see
> [[2026-09-08-repo-audit]]. Several doc gaps recorded below are re-listed there
> alongside code-level findings.

Setting up the repo end-to-end on macOS (Darwin 25.6.0) for Expo Go, following
`ExpoGO(Setup).md`. Machine LAN IP at time of setup: `192.168.88.100`.

## Environment at setup time

| Tool   | Version |
| ------ | ------- |
| node   | 24.20.0 |
| pnpm   | 9.15.1  |
| Docker | 29.7.2  |

## Test baseline on a clean clone

| Package         | Before `.env`                        | After `.env`      |
| --------------- | ------------------------------------ | ----------------- |
| `@mani/api`     | 4 suites, 76 tests pass              | unchanged         |
| `@mani/backend` | 19 suites, 353 tests pass            | unchanged         |
| `@mani/mobile`  | 8 of 12 suites **fail to run**       | 12 suites, 237 ✓  |

The mobile failure is not a test bug. `src/lib/supabase.ts` throws at module load
when `EXPO_PUBLIC_SUPABASE_URL` / `EXPO_PUBLIC_SUPABASE_ANON_KEY` are absent, and
`src/test/render.tsx` pulls it in through `RootNavigator`. `apps/mobile/.env` is
gitignored, so a clean clone cannot run the mobile suite. Creating `.env` fixes it.

## Bug found: strict UUIDs reject two seed users

`pnpm test:chat "..."` with no `--user` flag returned HTTP 500 from `messages.chat`:
`ZodError … path: ["userId"], "Invalid UUID"`, thrown from `getOrCreateThread`.

Zod v4's `.uuid()` enforces RFC 9562 — the version nibble must be 1-8 and the variant
nibble 8/9/a/b, with only the nil and max UUIDs exempted. `seed.sql` gave
`admin@example.com` the id `00000000-0000-0000-0000-000000000001` and
`user@example.com` `…002`. Both have a `0` version nibble, so neither is a valid UUID,
and Postgres's `uuid` column type accepts any 128-bit hex so nothing caught it at
insert time. Three schemas validate `userId` this way:
`lib/schema/threads.ts:36`, `lib/schema/messages.ts:58`, `lib/schema/summaries.ts:55`.

`test1`-`test3@example.com` were already using `a0000000-0000-4000-8000-0000000000NN`
— correct v4 — which is why `--user 1|2|3` worked and the default `--user 0` did not.

Fixed by bringing the two older users onto the same convention rather than relaxing
the schema: the schema's intent is a real UUID, and loosening it to accommodate fake
test data would weaken validation that production traffic relies on. The two literals
appeared only in `seed.sql`, so the change is contained. The provider rows at
`seed.sql:226` and `:248` share the same malformed shape but are never UUID-validated,
so they were left alone.

Real users were never affected — `AuthProvider.tsx` uses `signInAnonymously()` and
`signUp()`, and Supabase mints proper v4 UUIDs. This only ever broke the seed
accounts, which is exactly what local testing and the Expo Go walkthrough use.

Applying it needs `supabase db reset`, which also drops prompts, exercises and the
`storage.objects` rows — re-run `pnpm db:seed` and `pnpm db:seed:exercises` after.

## Backend `SUPABASE_URL` must be the LAN IP, not loopback

`services/exercises.ts:25` builds audio URLs with `createSignedUrl`, and the host
comes from whatever `SUPABASE_URL` the service client was constructed with. Set it to
`127.0.0.1` and the phone receives a loopback URL it cannot fetch — the app runs and
audio silently fails. Verified with the LAN IP set: signed host came back as
`http://192.168.88.100:54331` and the MP3 fetched (200, 5.3 MB).

`NEXT_PUBLIC_SUPABASE_URL` can stay on `127.0.0.1` — it only serves the admin login
UI in a browser on the same machine.

## Gaps found in `ExpoGO(Setup).md`

1. **No step creates `apps/backend/.env`.** Steps 6 and 7 (seed, start backend)
   cannot work without it — `scripts/seed-prompts.ts` and `scripts/seed-exercises.ts`
   both read `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` from that file via
   `dotenv.config()`, and exit 1 when missing. `scripts/test-chat.ts` also needs
   `NEXT_PUBLIC_SUPABASE_ANON_KEY` from it.
2. **"Keep the legacy `EXPO_PUBLIC_SUPABASE_ANON_KEY` from `.env.example`"** — that
   file only holds the placeholder `your-anon-key`. There is no legacy key to keep.
3. **`EXPO_NO_METRO_WORKSPACE_ROOT` is absent from `.env.example`**, so the flag the
   doc calls "required" is invisible to anyone who only copies the example file.
4. **`supabase` was pinned at `^2.65.0`**, not the `^2.116.0` the doc claims. Bumped.

The doc's Metro explanation is accurate — verified in
`node_modules/@expo/config/build/paths/paths.js:156`, where `getMetroServerRoot`
returns `projectRoot` early when `EXPO_NO_METRO_WORKSPACE_ROOT` is set.

## Side effect of the CLI bump

CLI 2.117.0 warns `config section [inbucket] is deprecated. Please use [local_smtp]
instead.` Renaming the section in `config.toml` would break anyone still on 2.65, and
`[inbucket]` still works, so it was left as-is. Worth doing once everyone is upgraded.

`supabase status` also reports `imgproxy` and `pooler` as stopped services. Both are
disabled or commented out in `config.toml`, so that is expected, not a failure.

## Other repo/doc mismatches (not setup blockers — left alone)

- `README.md` points at `.tool-versions` for the Node version; no such file exists.
- `README.md` and root `CLAUDE.md` say Next.js 15; `apps/backend` is on `next@^16.0.8`.
- `OPENROUTER_API_KEY` is the primary LLM credential (`services/llm.ts:123`) but is
  absent from both `apps/backend/.env.example` and the env table in
  `apps/backend/CLAUDE.md`.
- `apps/backend/CLAUDE.md` documents `GOOGLE_APPLICATION_CREDENTIALS`, which nothing
  in the codebase reads. App Check uses `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`,
  `FIREBASE_PRIVATE_KEY`.
- `PROMPT_DEBUG_LAYERS` (`services/prompts.ts:19`) and `API_URL`
  (`scripts/test-chat.ts:25`) are undocumented.
- `supabase/seed.sql:6` and `scripts/seed-prompts.ts:8` tell you to run
  `pnpm db:seed:prompts`; the script is named `db:seed`. The same two places point at
  `supabase/prompts/`; prompts live in `apps/backend/prompts/`.
- `apps/mobile/package-lock.json` (669 KB) is tracked in git even though root
  `.gitignore` lists `package-lock.json` — gitignore does not untrack existing files.
- `supabase/.branches/_current_branch` and `supabase/.temp/cli-latest` are tracked at
  the repo root, left over from running the CLI outside `apps/backend`.
- Root `package.json` carries `expo-updates@~29.0.16` as a direct dependency while
  `apps/mobile` declares `~29.0.15`. The root entry looks unintentional.
- `NarcissisticDynamics` is an accepted category in `scripts/seed-exercises.ts` and is
  listed in root `CLAUDE.md`, but `library_audio/exercises.json` has no exercise in it.

## Manifest check

`library_audio/exercises.json` holds 18 exercises, every `sourceFile` resolves to a
real MP3, and all categories are within the seed script's enum. Three entries carry no
category and `showOnHomeScreen: true` (the `Home/` audio).
