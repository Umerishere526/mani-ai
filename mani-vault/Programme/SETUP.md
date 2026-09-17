# SETUP — standing up Mani locally

Merged from the original Expo Go walkthrough and the clean-clone verification report, with
both sets of corrections applied. Everything here was executed and observed, not assumed.

The app runs on **Expo Go** — no development build needed. It has no custom native code, and
every native dependency it uses (`expo-av`, `expo-blur`, `react-native-webview`,
`expo-secure-store`, `expo-haptics`, `react-native-svg`) ships inside Expo Go.

If Expo Go fails, it is almost always one of the first two entries under
[Troubleshooting](#troubleshooting), not an incompatibility.

---

## Prerequisites

- Node and `pnpm`
- **Docker Desktop running** — local Supabase runs in Docker
- Expo Go on your phone
- Phone and computer **on the same Wi-Fi network**

Verified against: node 24.20.0, pnpm 9.15.1, Docker 29.7.2, Supabase CLI 2.117.0.

---

## Setup

### 1. Install

```bash
pnpm install
```

### 2. Create the mobile `.env`

```bash
cp apps/mobile/.env.example apps/mobile/.env
```

### 3. Set your LAN IP

Expo Go runs on a physical phone, so `localhost` will not resolve.

```bash
ipconfig getifaddr en0        # macOS Wi-Fi
```

In `apps/mobile/.env`:

```bash
EXPO_PUBLIC_API_URL=http://<YOUR_IP>:3001
EXPO_PUBLIC_SUPABASE_URL=http://<YOUR_IP>:54331
```

> Re-check whenever you change networks. A stale IP shows up as
> `TypeError: Network request failed` at sign-in.

### 4. Add the Metro workspace-root flag — required

```bash
EXPO_NO_METRO_WORKSPACE_ROOT=1
```

Without it Expo Go fails immediately with a 404. Cause and mechanism under
[Bundle 404](#1-bundle-404).

### 5. Start Supabase

```bash
cd apps/backend && npx supabase start
```

Wait for the services table, then confirm the gateway:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:54331/auth/v1/health   # expect 200
```

Get the real anon key — `.env.example` ships a placeholder:

```bash
cd apps/backend && npx supabase status
```

Put its `ANON_KEY` into `EXPO_PUBLIC_SUPABASE_ANON_KEY`. Newer CLIs also print a
`sb_publishable_…` key; either authenticates against local auth.

### 6. Create the backend `.env`

Both seed scripts and the API server read it, and they `process.exit(1)` without it.

```bash
cp apps/backend/.env.example apps/backend/.env
```

From `supabase status`:

```bash
SUPABASE_URL=http://<YOUR_IP>:54331
SUPABASE_SERVICE_ROLE_KEY=<SERVICE_ROLE_KEY>
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54331
NEXT_PUBLIC_SUPABASE_ANON_KEY=<ANON_KEY>
```

> **`SUPABASE_URL` takes the LAN IP, not loopback — deliberately.** Exercise audio is served
> through storage signed URLs built from this value and handed to the phone, which cannot reach
> your machine's loopback address. Point it at `127.0.0.1` and the app still runs; audio
> silently fails. `NEXT_PUBLIC_SUPABASE_URL` can stay on loopback — it only serves the admin
> login UI.

Then secrets and the LLM key:

```bash
openssl rand -base64 48    # ENCRYPTION_SECRET
openssl rand -base64 48    # ENCRYPTION_SALT
```

```bash
OPENROUTER_API_KEY=<your key>
```

In development and test this env var overrides the encrypted key on the provider row, so no
admin-portal setup is needed locally.

> `OPENAI_API_KEY` is optional and used only by conversation summarisation. Chat works without
> it; summaries throw when they trigger. This dependency disappears once summarisation moves to
> ai-service — see [[ai-service-contract]].

### 7. Seed

```bash
cd apps/backend
pnpm db:seed              # prompts
pnpm db:seed:exercises    # exercises + uploads audio to storage
```

Expect: 5 prompts, 18 exercises, 18 storage objects, 5 users.

### 8. Start the backend

```bash
pnpm dev:backend          # from repo root — serves :3001
```

Verify from the phone's point of view:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://<YOUR_IP>:3001    # expect 200
```

### 9. Start Metro and scan

```bash
cd apps/mobile && npx expo start --go
```

Scan with Expo Go. If prompted, choose **Expo Go**, then **Proceed anonymously**.

---

## Ports

| Port  | Service         | URL                        |
| ----- | --------------- | -------------------------- |
| 3001  | Backend API     | `http://<LAN_IP>:3001`     |
| 8081  | Metro bundler   | `http://<LAN_IP>:8081`     |
| 54331 | Supabase (Kong) | `http://<LAN_IP>:54331`    |
| 54332 | Postgres        | `postgres:postgres@…:54332`|
| 54333 | Supabase Studio | `http://localhost:54333`   |
| 54334 | Mailpit (email) | `http://localhost:54334`   |

Health check:

```bash
for p in 3001 54331 8081; do
  printf "%s: " $p
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 && echo LISTENING || echo DOWN
done
```

## Seed logins

Password for all: `testpassword123`

| Email               | UUID                                   | Access               |
| ------------------- | -------------------------------------- | -------------------- |
| admin@example.com   | `a0000000-0000-4000-8000-000000000001` | Admin portal         |
| user@example.com    | `a0000000-0000-4000-8000-000000000002` | Mobile (default)     |
| test1–3@example.com | `…-0000000000{11,12,13}`               | Parallel style tests |

> These UUIDs matter. Two seed users originally had non-RFC ids with a `0` version nibble,
> which Zod v4's `.uuid()` rejects under RFC 9562 — chat returned HTTP 500 from
> `getOrCreateThread` for the default user while `--user 1|2|3` worked fine. Postgres accepts
> any 128-bit hex, so nothing caught it at insert. Keep the `a0000000-0000-4000-8000-…` form.

---

## Cold restart

```bash
cd apps/backend && npx supabase start    # Docker must be running
pnpm dev:backend                          # from repo root
cd apps/mobile && npx expo start --go
```

Re-check your LAN IP after any network change — it is hardcoded in `apps/mobile/.env` (two
values) and `apps/backend/.env` (`SUPABASE_URL`).

`supabase db reset` drops prompts, exercises and `storage.objects`. Re-run both seed commands
after one.

> **Prompt editing:** the database is the runtime source of truth; markdown files are seed
> input. Today, editing a file in `apps/backend/prompts/` requires `pnpm db:seed` before the
> change has any effect. **This changes** — the admin portal becomes authoritative and
> `db:seed` will refuse to run against a populated database. See
> [[2026-09-14-architecture-decisions]] #7.

---

## Troubleshooting

### 1. Bundle 404

On scanning, Expo Go shows a 404 with `{"type":"UnableToResolveError","targetModuleName":"./apps/mobile/index"}`.

**Cause.** In a monorepo the Expo CLI derives Metro's server root from `pnpm-workspace.yaml`
via `getMetroServerRoot()`, so it advertises a bundle URL prefixed with `apps/mobile/` that
Metro cannot resolve.

**Fix.** `EXPO_NO_METRO_WORKSPACE_ROOT=1` in `apps/mobile/.env`. The same function reads it and
pins the server root to the app directory, keeping CLI and Metro in agreement. Confirmed at
`node_modules/@expo/config/build/paths/paths.js:156`.

Do **not** also set `config.server.unstable_serverRoot` in `metro.config.js` — that moves only
Metro's half and reintroduces the 404 in mirror image (`apps/mobile/apps/mobile/index`).

Restart with a cleared cache; the old URL is cached:

```bash
npx expo start --go --clear
```

### 2. `TypeError: Network request failed` at sign-in

Running, but cannot reach Supabase or the backend. In order: wrong IP (`localhost` never works
on a device), Supabase down (port 54331), backend down (port 3001), phone and computer on
different networks.

### 3. Supabase crash loop on start

`Migration failed. Reason: duplicate key value violates unique constraint "migrations_name_key"`
repeating, then `Stopping containers...`. Port 54331 never binds.

**Cause.** Version skew — an outdated pinned CLI pulls a newer `storage-api` image that
renumbers its migrations and re-inserts names the older schema already holds. The CLI treats
one unhealthy service as fatal and tears down the entire stack, Kong included.

**Fix.** Upgrade the CLI. The repo is pinned `^2.116.0`, which resolves it:

```bash
cd apps/backend && pnpm add -D supabase@latest && npx supabase start
```

Data survives — it lives in Docker volumes, not containers.

### Other states

**"already running" while services are stopped** — wedged. `npx supabase stop && npx supabase start`.

**`Conflict. The container name "…" is already in use`** — `docker rm -f supabase_storage_mani-backend`.

---

## Known gaps — not blockers

- `app.json` references `./google-services.json` and `./GoogleService-Info.plist`; neither is in
  the repo. Harmless on Expo Go, fatal for any EAS or native build.
- `expo-updates` is a dependency but inert in Expo Go. Testing OTA behaviour needs a
  development build.
- Metro warns that `react-native-reanimated` is a major behind what SDK 54 expects (`3.17.5`
  installed, `~4.1.1` expected). Expo Go ships its own native reanimated, so this is the most
  likely cause if the app hard-crashes on load — but nothing in `apps/mobile/src` imports it
  (plugin only, in `babel.config.js`), so it may never be exercised. Do not chase it.
- `react@19.1.2` against an expected `19.1.0` is deliberate — see the `react-native@0.81.5`
  patch note in `README.md`.
- The CLI warns `config section [inbucket] is deprecated, use [local_smtp]`. Leave it —
  renaming breaks anyone on an older CLI, and `[inbucket]` still works.
