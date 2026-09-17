> **ARCHIVED — evidence, not instructions.** Point-in-time record. Parts of this are
> superseded; see `README.md` in this folder for exactly which. Current instructions live
> in `../START-HERE.md`, and where the two disagree, that one wins.

# Running Mani on Expo Go

This app runs fine on **Expo Go** — no development build is required. Every native
dependency it uses (`expo-av`, `expo-blur`, `react-native-webview`, `reanimated`,
`expo-secure-store`, `expo-haptics`, `expo-auth-session`, `react-native-svg`) ships
inside Expo Go, and the project has no custom native code.

If Expo Go fails for you, it is almost always one of the two issues in
[Troubleshooting](#troubleshooting) below, not an incompatibility.

## Prerequisites

- Node + `pnpm`
- **Docker Desktop running** (local Supabase runs in Docker)
- Expo Go installed on your phone
- Phone and computer **on the same Wi-Fi network**

## Setup

### 1. Install dependencies

From the repo root:

```bash
pnpm install
```

### 2. Create the mobile `.env`

`apps/mobile/.env` is gitignored, so you must create it yourself:

```bash
cp apps/mobile/.env.example apps/mobile/.env
```

### 3. Set your machine's LAN IP

Expo Go runs on a physical phone, so `localhost` will not resolve — it must be your
computer's IP address on the local network.

```bash
ipconfig getifaddr en0        # macOS Wi-Fi
```

Edit `apps/mobile/.env` and set both URLs to that IP:

```bash
EXPO_PUBLIC_API_URL=http://<YOUR_IP>:3001
EXPO_PUBLIC_SUPABASE_URL=http://<YOUR_IP>:54331
```

> Re-check this whenever you change networks. A stale IP produces
> `TypeError: Network request failed` at sign-in.

### 4. Add the Metro workspace-root flag (required)

Add this line to `apps/mobile/.env`:

```bash
EXPO_NO_METRO_WORKSPACE_ROOT=1
```

**Without this, Expo Go fails immediately with a 404** — see
[Bundle 404](#1-bundle-404-unabletoresolveerror) for why.

### 5. Start Supabase

```bash
cd apps/backend && npx supabase start
```

Wait for the services table to print. Confirm the API gateway is up:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:54331/auth/v1/health   # expect 200
```

Now fill in `EXPO_PUBLIC_SUPABASE_ANON_KEY` in `apps/mobile/.env` — `.env.example`
ships a placeholder, so you need the real value:

```bash
cd apps/backend && npx supabase status
```

Use the `ANON_KEY` it prints. Newer Supabase CLIs also print a `sb_publishable_…`
key; either authenticates correctly against local auth.

### 6. Create the backend `.env`

`apps/backend/.env` is gitignored too, and the seed scripts and API server all read
it. Nothing in the next two steps works without it:

```bash
cp apps/backend/.env.example apps/backend/.env
```

From the `supabase status` output above, set:

```bash
SUPABASE_URL=http://<YOUR_IP>:54331
SUPABASE_SERVICE_ROLE_KEY=<SERVICE_ROLE_KEY>
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54331
NEXT_PUBLIC_SUPABASE_ANON_KEY=<ANON_KEY>
```

> `SUPABASE_URL` takes the LAN IP rather than `127.0.0.1` on purpose. Exercise audio
> is served through storage signed URLs built from this value and handed to the
> phone, which cannot reach your machine's loopback address. Point it at loopback and
> the app still runs — audio playback just fails.

Then generate the encryption secrets and add your OpenRouter key, which the chat
endpoint needs:

```bash
openssl rand -base64 48    # ENCRYPTION_SECRET
openssl rand -base64 48    # ENCRYPTION_SALT
```

```bash
OPENROUTER_API_KEY=<your key>
```

### 7. Seed the database

```bash
cd apps/backend
pnpm db:seed              # prompts
pnpm db:seed:exercises    # exercises + uploads audio to storage
```

Expected: 5 prompts, 18 exercises, 18 storage objects.

### 8. Start the backend

```bash
pnpm dev:backend          # from repo root — serves :3001
```

Verify from your phone's perspective (use your LAN IP, not localhost):

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://<YOUR_IP>:3001    # expect 200
```

### 9. Start Metro and scan

```bash
cd apps/mobile && npx expo start --go
```

Scan the QR code with Expo Go. If prompted, choose **Expo Go**, then
**Proceed anonymously**.

## Verify before you scan

All three should be listening:

```bash
for p in 3001 54331 8081; do
  printf "%s: " $p
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 && echo LISTENING || echo DOWN
done
```

| Port  | Service         |
| ----- | --------------- |
| 3001  | Backend API     |
| 54331 | Supabase (Kong) |
| 8081  | Metro bundler   |

## Troubleshooting

### 1. Bundle 404 (`UnableToResolveError`)

**Symptom** — on scanning, Expo Go shows:

```
The development server returned response error code: 404
URL: http://<IP>:8081/apps/mobile/index.bundle?platform=android...
Body: {"type":"UnableToResolveError","targetModuleName":"./apps/mobile/index", ...}
```

**Cause** — in a monorepo, the Expo CLI derives Metro's server root from
`pnpm-workspace.yaml` via `getMetroServerRoot()`
(`@expo/config/build/paths/paths.js`), so it advertises a bundle URL prefixed with
`apps/mobile/`, which Metro cannot resolve.

**Fix** — `EXPO_NO_METRO_WORKSPACE_ROOT=1` in `apps/mobile/.env` (step 4). This is
read by that same function and pins the server root to the app directory, keeping the
CLI and Metro in agreement.

Do **not** also set `config.server.unstable_serverRoot` in `metro.config.js` — that
moves only Metro's half of the pair and reintroduces the same 404 in mirror image
(`apps/mobile/apps/mobile/index`).

After changing this, restart with a cleared cache — the old URL is cached:

```bash
npx expo start --go --clear
```

### 2. `TypeError: Network request failed` at sign-in

The app is running but cannot reach Supabase or the backend. In order:

1. **Wrong IP** — re-run step 3. `localhost` never works on a physical device.
2. **Supabase down** — check port 54331 is listening.
3. **Backend down** — check port 3001 is listening.
4. **Different networks** — phone and computer must share one Wi-Fi network.

### 3. Supabase won't start (storage migration crash loop)

**Symptom** — `supabase start` logs this repeatedly, then `Stopping containers...`:

```
Migration failed. Reason: duplicate key value violates unique constraint "migrations_name_key"
supabase_storage_mani-backend container is not ready: unhealthy
```

Port 54331 never binds, so the app reports `Network request failed`.

**Cause** — version skew. An outdated pinned `supabase` CLI pulls a newer
`storage-api` image that renumbers its migrations and re-inserts names the older
schema already holds. The CLI treats one unhealthy service as fatal and tears down the
*entire* stack, including Kong.

**Fix** — upgrade the CLI:

```bash
cd apps/backend && pnpm add -D supabase@latest && npx supabase start
```

The repo is pinned at `supabase: ^2.116.0`, which resolves this. Commit
`package.json` + `pnpm-lock.yaml` if you bump it further.

Your data survives — it lives in Docker volumes, not the containers.

### Other useful states

**`supabase start` says "already running" while services are stopped** — wedged
state. Stop and restart:

```bash
npx supabase stop && npx supabase start
```

**`Conflict. The container name "…" is already in use`** — remove the leftover:

```bash
docker rm -f supabase_storage_mani-backend
```

## Known gaps (not Expo Go blockers)

- `app.json` references `./google-services.json` and `./GoogleService-Info.plist`,
  and neither file is in the repo. Harmless for Expo Go, but a native/EAS build will
  fail until they are supplied.
- `expo-updates` is a dependency but inert in Expo Go. Testing OTA update behavior
  genuinely does require a development build.
- Metro prints a list of packages whose versions differ from what SDK 54 expects.
  Most are patch-level, but `react-native-reanimated` is a major behind (`3.17.5`
  installed, `~4.1.1` expected). Expo Go ships its own native reanimated, so a
  mismatch here is the most likely cause if the app crashes on load. Nothing in
  `apps/mobile/src` imports reanimated — it appears only as a plugin in
  `babel.config.js` — so this may never be exercised.
- `react@19.1.2` also shows in that list against an expected `19.1.0`. That one is
  deliberate: see the `react-native@0.81.5` patch note in `README.md`.
