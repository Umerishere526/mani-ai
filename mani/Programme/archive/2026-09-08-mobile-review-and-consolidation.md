> **ARCHIVED — evidence, not instructions.** Point-in-time record. Parts of this are
> superseded; see `README.md` in this folder for exactly which. Current instructions live
> in `../START-HERE.md`, and where the two disagree, that one wins.

# 2026-09-08 — Mobile review + consolidated assessment

Companion to [[2026-09-08-repo-audit]] (findings),
[[2026-09-08-technical-assessment.md]] (judgment) and
[[2026-09-08-repo-setup-and-doc-gaps]] (setup evidence). This document is the
consolidation intended for Thursday.

## Conclusion status — flagged first, as requested

**The mobile review does not change the "no major rebuild" conclusion. It strengthens it.**

The mobile app is conventional, coherent React Native. Its module layout is sane, its
provider composition is explicit, its chat failure handling is genuinely well built, and
its persistence choices are correct (session in SecureStore, not AsyncStorage). The
problems found are **localized resilience and configuration gaps**, not architectural
incoherence — three of them are single-file fixes.

Had I found, say, business logic duplicated across screens, no contract with the backend,
or state managed by ad-hoc mutation across unrelated components, I would be telling you
the opposite. That is not what is there.

One new HIGH finding did come out of this pass (session persistence silently failing on
Android), and it is quantified below.

---

# 1. Mobile architecture as built

```
index.js  registerRootComponent
   └── App.tsx
        ├── Text/TextInput.defaultProps mutation      ← no-op on React 19 (LOW)
        ├── useFonts()  ──── gates EVERYTHING ────────← H10, no failure path
        │      7 faces / ~1.46 MB, error discarded
        └── <Providers providers={[...]}>              ← array of render fns, order-critical
             ├── SafeAreaProvider
             ├── SecurityProvider        deviceId + X-API-Key / X-App-Check(TODO)
             ├── AuthProvider            session, profile, pendingFlow, 20 auth actions
             ├── DrawerProvider          global drawer open/close
             ├── NavigationContainer     theme from useColorScheme()
             └── SecurityHeaderBridge → trpc.Provider → QueryClientProvider
                  └── RootNavigator                    ← ref written during render (M)
                       │  gate: hasCompletedOnboarding(profile) || pendingFlow==='password_reset'
                       ├── OnboardingScreen  (11 steps, useOnboardingState)
                       ├── HomeScreen
                       ├── ChatScreen        ← sole crisis enforcement point (C3)
                       ├── ExercisesStack    Categories → Category → Player
                       ├── SettingsScreen, ChangeEmail, ChangePassword
                       └── GlobalDrawer (ChatDrawer + CrisisDrawer)
```

**No error boundary at any level** (H11). Any throw in this tree unmounts to the Expo Go
error screen.

Two client-side data channels, deliberately:

```
  ┌─────────────────────────────────────────────────────────────┐
  │  apps/mobile                                                │
  │                                                             │
  │  lib/supabase.ts ──────────► Supabase Auth  :54331          │  channel 1: auth only
  │    (anon key, SecureStore)      GoTrue                      │
  │         │                                                   │
  │         │ getAccessToken()                                  │
  │         ▼                                                   │
  │  util/api/trpc.ts ─────────► Next.js /api/trpc  :3001       │  channel 2: everything else
  │    Authorization: Bearer <jwt>                              │
  │    X-Device-ID, X-API-Key                                   │
  └─────────────────────────────────────────────────────────────┘
```

This is a reasonable trade for using Supabase Auth, but it means **two base URLs, two
failure modes, and two places a misconfiguration can hide** — which is exactly what bit
the Expo Go setup. It is intentional design, not drift.

---

# 2. End-to-end flow traces

## 2.1 Auth / session

```
OnboardingScreen
  └─ ensureAuthenticated()            AuthProvider:171
       └─ supabase.auth.signInAnonymously()      ──► GoTrue  ──► auth.users row (v4 uuid)
            └─ onAuthStateChange  ──► setSession()
                 └─ secureStorage.setItem(session JSON)   ← 1861–2080 bytes  ✱ NEW HIGH
  └─ updateProfile({ageVerified})     → user_metadata
  └─ updateProfile({nickname})        → user_metadata     ← unbounded length ✱
  └─ updateProfile({topics})          → user_metadata
  └─ updateProfile({supportStyle})    → user_metadata
       └─ RootNavigator re-gates on profile.nickname → leaves onboarding
```

Every request thereafter:

```
trpc.ts headers()
  ├─ securityHeaderProvider() → X-Device-ID (+ X-API-Key if mode=api_key)
  └─ getAccessToken() → supabase.auth.getSession() → Authorization: Bearer <jwt>
        │
        ▼
route.ts  extractAuth() → supabase.auth.getUser(token)  ← validated by GoTrue, signature-based
        │                                                  (host-agnostic; LAN vs loopback is fine)
        ├─ appAuthMode: 'none' → appAuthorized = true unconditionally      (M4, fails open)
        └─ ctx = { userId, publicClient: SERVICE ROLE, adminClient: SERVICE ROLE }
                                          └──────────── bypasses RLS ────────── ROOT CAUSE 1
```

## 2.2 Chat / messages

```
ChatScreen.handleSend()                     guards: !content || isPending || isChatBlocked  ✔ good
  ├─ randomUUID() → clientMessageId          (idempotency key)
  ├─ setOptimisticMessage(...)
  └─ chatMutation.mutate({content, threadId, clientMessageId})
        │
        ▼  messages.chat  (verifiedEmailProcedure)
   routers/messages.ts
     └─ buildChatSendContext()
          ├─ getOrCreateThread()            ← z.uuid() on userId  (was C-bug, fixed in setup)
          ├─ fetchMessagesForContext()
          │     ├─ summary exists  → .gt(created_at, checkpoint)   NO .limit()   H5
          │     └─ no summary      → .limit(RECENT_MESSAGES_WINDOW = 20)
          └─ prompts.composeSystemPrompt()   6 layers, ~34 KB
        │
        ▼  services/messages.ts  (~1600 lines)          ────────────── ROOT CAUSE 3
     generateObject() ──► OpenRouter ──► Gemini 3 Flash
        ├─ regeneration triggers ×5 (duplicate, leakage, phase, repeated prompt, forbidden word)
        │    └─ up to 6 LLM calls/turn; each restarts from the pristine message array
        │    └─ crisis check sits AFTER these  ──► crisis flag droppable          H3
        ├─ createPair() → RPC insert_message_pair   ← ATOMIC ✔ … and world-writable  C4
        └─ 8 further writes, NO transaction:
             updateTechniqueTracking, addTechniquesOffered*, updateTechniqueTracking,
             markLibraryOffered, appendResponseStyle*, updateLastMessage, updateTitle
             (* = read-modify-write, lost-update race)
        │
        ▼
   ChatScreen.onSuccess  → refetch → clear optimistic → setCrisisBlocksChat → maybe openCrisisDrawer
   ChatScreen.onError    → parseChatError → retryable? → Alert with Retry   ✔ good
```

## 2.3 Crisis state — the one that matters most

```
model self-reports  crisis: {reason} | null        ← llm.ts:51-60, no deterministic detector
        │
        ├─ regeneration may replace the whole object first  ──► signal lost silently   H3
        │
        ▼
  markCrisis(thread)  → threads.crisis_detected = true
        │
        ├─ RETURNED to client: crisisDetected, crisisBlocksChat
        │     └─ ChatScreen:299  isChatBlocked = crisisDetected && crisisBlocksChat   ← ONLY gate  C3
        │
        ├─ chat() NEVER reads thread.crisisDetected on entry                          C3
        ├─ normal return path hardcodes crisisDetected: false                         C3
        └─ user can PATCH /rest/v1/threads {crisis_detected:false}                     H2
             (table-wide UPDATE grant, no column restriction)
```

**There is no layer at which crisis state is authoritative.** Client enforces, model
detects, user can rewrite. For this product that is the single most important structural
defect, ahead of the data-exposure criticals in product terms even though they rank higher
in security terms.

## 2.4 Frameworks / techniques

```
system prompt (techniques.md) ──► model returns:
     prompts: [{label, technique?, library?}]      technique = FREE STRING            H8
     state:   {technique, step, accepted?}         used as TECHNIQUE_PHASES[technique] H8
        │
        ▼ persisted to threads columns
   techniques_offered[]      ← offers recorded as if completed                        H6
   last_technique_name/outcome/at_count/phase
   response_styles[]         ← bounded to last 7 ✔
        │
        ▼ next turn
   [ctx]…[/ctx] block PREPENDED to the user's message, and PERSISTED with it           M11
        └─ by turn 10 the model sees 10 contradictory ctx blocks
        └─ user can forge a second [ctx] block to spoof cooldown state                 L3
        │
        ▼ mobile
   SmartPromptChip renders label; handlePromptPress handles `library` navigation only.
   `technique` is never read client-side — backend infers acceptance from free text
   or state.accepted.  Missing state.accepted ⇒ treated as DECLINE                     H7
```

## 2.5 Exercises / audio

```
exercises.list (fullyProtectedProcedure)
  └─ services/exercises.ts:25  createSignedUrl(audioPath, 3600s)
        └─ host = whatever SUPABASE_URL the server holds
             └─ loopback ⇒ phone cannot fetch (silent audio failure)  ← setup-doc gap
  └─ ExercisePlayerScreen: Audio.Sound.createAsync(uri)
        ├─ API_URL = Constants.expoConfig?.extra?.apiUrl ?? 'http://localhost:3001'
        │      └─ `extra.apiUrl` DOES NOT EXIST → always the localhost fallback        M
        └─ 1-hour URL expiry not renewed; unload on unmount ✔ (unawaited)
```

---

# 3. Mobile findings

Structure per request: severity · evidence/root cause · impact · recommended solution ·
cheaper alternative.

## MOB-1 · HIGH · Session silently fails to persist on Android (NEW)

**Evidence.** Measured against the running local Supabase:

| Session contents | Bytes | vs Android 2048-byte SecureStore limit |
| --- | --- | --- |
| baseline (`ageVerified`, short `nickname`) | 1,861 | 187 bytes headroom |
| + full onboarding profile (all 6 topics, `supportStyle`) | 1,999 | **49 bytes headroom** |
| + a `pending_flow` (password reset / email change) | **2,080** | **OVER LIMIT** |

**Root cause — three independent decisions combining:**
1. `expo-secure-store` on Android is backed by SharedPreferences+Keystore with a
   ~2048-byte practical value limit; supabase-js persists the **entire session JSON**
   (access token + refresh token + full user object) as one value.
2. `nickname` has **no length cap** — not in `packages/api/src/schemas/user.ts:36`
   (`z.string().optional()`) and not in the `NicknameStep` input. A ~55-char nickname
   alone consumes the remaining headroom.
3. `lib/supabase.ts:33-39` **swallows the write failure**, warning only under `__DEV__`:
   ```ts
   catch (error) { if (__DEV__) console.warn(...) }
   ```
   In production there is no signal at all.

**Impact.** Android users who complete full onboarding and then start a password reset or
email change — or who simply choose a long nickname — exceed the limit. The write fails,
the session is never persisted, and the user is signed out on every app launch, with no
error surfaced anywhere. Silent, permanent, and indistinguishable from "the app forgot me".

**Recommended solution.** Stop persisting the whole session in one SecureStore value.
Store only the refresh token in SecureStore and keep the access token in memory; or split
the value across chunked keys. Cap `nickname` in the shared schema (`z.string().max(40)`)
so the client and server agree. Stop swallowing the write failure — surface it.

**Cheaper alternative.** Cap `nickname` at 40 chars and stop writing `pending_flow` into
`user_metadata` (keep it in local state or a dedicated table). That reclaims ~80–120 bytes
and pushes the worst case back under the limit without touching the storage adapter. Add a
non-`__DEV__` error report on write failure so the next occurrence is visible. This is a
~10-line change and buys real headroom, but it is a margin fix, not a bound.

## MOB-2 · HIGH · Font loading gates the app with no failure path

**Evidence.** `hooks/useFonts.ts:15-31` returns only `fontsLoaded`; `error` is logged and
discarded. `App.tsx:81` renders a bare `ActivityIndicator` whenever `!fontsLoaded`.
7 faces, ~1.46 MB measured (Montserrat 4 × ~331 KB, Urbanist 3 × ~42 KB), fetched over the
LAN from Metro in Expo Go on top of the 9.4 MB dev bundle.

**Root cause.** A boolean gate over a fallible, network-dependent, multi-asset operation,
with the failure channel deliberately dropped by the hook's return signature.

**Impact.** Any font failure = indefinite spinner. No timeout, no retry, no degraded
render, and the caller *cannot* react because the error never reaches it. This is the most
probable explanation for the observed Android "loads for minutes, then Something went
wrong".

**Recommended solution.** Return `[fontsLoaded, error]` and have `App.tsx` render the app
with system-font fallback on error, reporting to error tracking. Fonts are a
presentation concern and should never block boot.

**Cheaper alternative.** Change the gate to `if (!fontsLoaded && !error)`. One line, and
it converts a hang into a rendered app with fallback fonts. Add a timeout only if you see
it in telemetry.

## MOB-3 · HIGH · No error boundary anywhere

**Evidence.** Zero occurrences of `ErrorBoundary`, `componentDidCatch`, or
`getDerivedStateFromError` in `apps/mobile/src` or `App.tsx`.

**Root cause.** Never added; no framework default supplies one.

**Impact.** Any render throw unmounts the entire tree to the Expo Go / red-box screen.
Combined with MOB-2 and `retry: false`, the app has no resilience layer: a transient
failure and a genuine crash are indistinguishable to the user.

**Recommended solution.** One boundary just inside `Providers` with a "something went
wrong / retry" screen, wired to error tracking. Optionally a second around
`ExercisePlayerScreen` since `expo-av` is the most likely native thrower.

**Cheaper alternative.** A single ~40-line class component wrapping `<RootNavigator />`
with a reload button. No dependency, no telemetry, covers the whole tree.

## MOB-4 · MEDIUM · `AuthProvider`'s `useMemo` never memoizes

**Evidence.** `profile` (`:168`) and `pendingFlow` (`:169`) are recomputed via
`safeParse` on every render, producing fresh object identities, and both appear in the
memo's dependency array (`:559-560`).

**Root cause.** Derived objects computed inline in the render body, then used as memo
dependencies — a self-defeating cycle.

**Impact.** `contextValue` is a new object every render, so **every `useAuth()` consumer
re-renders whenever `AuthProvider` renders**. With 20+ consumers including `ChatScreen`,
this is the app's main avoidable render cost. The 30-entry dependency array accomplishes
nothing.

**Recommended solution.** Wrap both derivations in their own `useMemo` keyed on
`user?.user_metadata`, so identity is stable when metadata has not changed.

**Cheaper alternative.** Key them on the serialized metadata
(`useMemo(..., [JSON.stringify(user?.user_metadata)])`). Slightly wasteful but two lines
and immediately correct.

## MOB-5 · MEDIUM · `ensureAuthenticated` has no in-flight guard

**Evidence.** `AuthProvider.tsx:171-182` — `if (session) return;` then
`signInAnonymously()`. `session` is React state, stale within a render cycle.

**Impact.** Two near-simultaneous callers both observe `null` and both create an anonymous
`auth.users` row. Orphaned accounts, and the second session supersedes the first, so any
data written against the first is stranded.

**Recommended solution.** Hold the in-flight promise in a ref and return it to concurrent
callers.

**Cheaper alternative.** A `useRef(false)` boolean guard. Three lines.

## MOB-6 · MEDIUM · Reads a config key that does not exist

**Evidence.** `ExercisePlayerScreen.tsx:26`
`Constants.expoConfig?.extra?.apiUrl || 'http://localhost:3001'`. Verified `app.json`
`extra` is `{"eas":{"projectId":"3ab55271-…"}}` — **no `apiUrl`**. Also depends on
`expo-constants`, which is **undeclared** in `package.json` and has **two versions
installed** (18.0.11 root, 18.0.13 under `expo-linking`).

**Root cause.** Config drift: the file uses a config mechanism the rest of the app
abandoned in favour of `EXPO_PUBLIC_API_URL`.

**Impact.** `API_URL` is *always* the localhost fallback, which on a physical device is the
phone itself. Currently harmless only because signed audio URLs are absolute, so the
branch is dead — a live trap for the next person who relies on it.

**Recommended solution.** Use `process.env.EXPO_PUBLIC_API_URL` as everywhere else and
delete the `expo-constants` import.

**Cheaper alternative.** Same change, three lines — there is no cheaper option and no
reason to defer it.

## MOB-7 · MEDIUM · Background audio requested but not permitted

**Evidence.** `Audio.setAudioModeAsync({ staysActiveInBackground: true })` while
`app.json` `ios.infoPlist` contains only `ITSAppUsesNonExemptEncryption`. No
`UIBackgroundModes`.

**Impact.** Background playback cannot work on iOS. Meditation audio stops when the user
backgrounds the app or locks the screen — plausibly the primary way the feature is used.
Invisible in Expo Go; will surface on a real build.

**Recommended solution.** Add `"UIBackgroundModes": ["audio"]` to `ios.infoPlist` and
verify on a dev build.

**Cheaper alternative.** If background audio is not intended, set
`staysActiveInBackground: false` so code and configuration agree. Either is one line —
but pick deliberately, it is a product decision.

## MOB-8 · MEDIUM · Ref mutated during render

**Evidence.** `RootNavigator.tsx:~54-56` assigns `wasShowingOnboardingRef.current` in the
component body; the comment concedes "order matters".

**Impact.** Under React 19 concurrent/double-invoked rendering the ref can be written by a
render that is then discarded, so `justCompletedOnboarding` is derived from work React
threw away — the user can land on the wrong screen after completing onboarding.

**Recommended solution.** Move the write into a `useEffect`, or derive the transition from
state rather than a render-time ref.

**Cheaper alternative.** Leave the logic but move only the assignment into an effect
(~3 lines). Behaviour is unchanged in practice today; this removes the future hazard.

## MOB-9 · MEDIUM · Six uncancelled `setTimeout`s in `ChatDrawer`

**Evidence.** `ChatDrawer.tsx:124, 131, 138, 146, 153, 160` — all inside event handlers,
none stored in a ref or cleared. Verified by sweep: `set=6, clear=0`.

**Impact.** Rapid taps on two nav items queue two navigations. If the drawer unmounts
before a timer fires, the callback runs against an unmounted parent — including
`onOpenCrisisDrawer`, i.e. a crisis drawer that can open after teardown.

**Recommended solution.** One `useRef` holding the pending timer, cleared on new taps and
in a cleanup effect.

**Cheaper alternative.** Since every handler is `onClose()` + delayed action, extract one
`closeThen(fn)` helper that stores and clears a single shared timer ref. ~10 lines,
removes all six sites at once.

## MOB-10 · MEDIUM · `retry: false` globally on queries

**Evidence.** `util/api/queryClient.ts` — `queries: { retry: false }`, no `staleTime`, no
`networkMode`, no `gcTime`.

**Nuance worth recording:** this affects **queries only**. The chat **mutation** has a
genuine retry UX (`failedMessageRef` + `parseChatError` + Alert with Retry) and
`isMounted` guards on both success and error. Chat failure handling is one of the better
parts of the app; do not let this finding imply otherwise.

**Impact.** A transient blip while loading a thread list or exercise list produces a
terminal error state with no automatic recovery and, given MOB-3, nothing above it to
catch.

**Recommended solution.** `retry: 2` with exponential backoff for queries, plus a
`staleTime` so navigation does not refetch everything.

**Cheaper alternative.** `retry: 1` on the two list queries only, leaving the global
default alone. Two lines, no behavioural surprise elsewhere.

## MOB-11 · LOW · cluster (evidence-backed, low individual impact)

| Finding | Evidence | Impact | Fix / cheaper option |
| --- | --- | --- | --- |
| `Text.defaultProps` mutation is a no-op on React 19 | `App.tsx:29-31`; React 19 removed `defaultProps` for function components | The font-scaling protection the comment claims silently does not apply; third-party text still scales | Wrap library text in the existing `src/components/base` wrappers / cheaper: delete the dead code and the misleading comment |
| `isAnonymous = user?.is_anonymous ?? true` | `AuthProvider.tsx:167` | A signed-**out** user reports as anonymous, conflating "no session" with "anonymous session" | Return `false` when `user === null` / cheaper: same one-line change |
| Device-id fallback never persisted, `error` discarded | `deviceId.ts:42-47` | New device id every launch if SecureStore throws; defeats any device-based limiting | Persist the fallback and report the error / cheaper: at minimum log it non-`__DEV__` |
| Notification preference read *and* write both `catch { // Silently fail }` | `useNotificationPreference.ts:18, 29` | Toggle appears to work and does not persist; no user feedback | Surface the failure in UI / cheaper: revert the toggle state on write failure |
| Two sequential `updateUser` calls | `AuthProvider.tsx:420 & 430`, `:354 & 368` | If the second (setting `pending_flow`) fails, the reset/email-change flow is unresumable | Single `updateUser` carrying both / cheaper: same — they can be merged into one call |
| Force-signout by string match | `AuthProvider.tsx:193-198` — `error.message.includes('does not exist')` | Breaks silently if upstream wording changes; user stuck in a broken session | Match on the error code / cheaper: keep the string check but add the code as primary |
| Audio `unloadAsync()` unawaited/uncaught | `ExercisePlayerScreen.tsx:~157` | Unhandled rejection on unmount | `void unloadAsync().catch(noop)` |
| Stale TODO in shipped code | `apps/backend/src/lib/schema/messages.ts:16` — "Uncomment once messages table exists"; it has existed since migration `20251210000000` | Misleads readers about schema state | Delete the comment |

---

# 4. Expo configuration, dependencies, build & release

## Configuration and environment handling

| Item | State | Note |
| --- | --- | --- |
| `EXPO_PUBLIC_*` env handling | Correct mechanism | Inlined at build time — public by design. Verified below. |
| `EXPO_NO_METRO_WORKSPACE_ROOT` | **Required, undocumented in `.env.example`** before this week | Verified in `@expo/config/build/paths/paths.js:156` |
| `app.json` `extra` | Missing `apiUrl` that code reads | MOB-6 |
| `app.json` `googleServicesFile` ×2 | Files absent from repo | Config-parse warnings in Metro; EAS build will fail |
| `expo-system-ui` | Referenced in `app.json`, **undeclared** | knip |
| `metro.config.js` | `disableHierarchicalLookup: true` | expo-doctor flags mismatch (expects `false`); required by the hoisted pnpm layout, so **intentional** |
| `eas.json` | 3 build profiles, **no `channel` on any** | OTA branch/channel mapping unwired while `app.json` sets `updates.url` |
| `expo-updates` | Declared in **both** root (`~29.0.16`) and mobile (`~29.0.15`), **unused** per knip | Root entry looks unintentional; version skew between the two |

## Dependency posture (mobile-relevant)

- **Three SDK majors behind**: SDK 54 installed, 57 current. `pnpm outdated` showing Expo
  packages at `57.x` is the SDK moving as a unit, **not** 13 independent upgrades.
  Treat as one deliberate migration.
- `react-native-reanimated` **3.17.5 vs SDK-expected ~4.1.1** — confirmed **inert** three
  independent ways: no import anywhere in `apps/mobile/src`; the only "reanimated" strings
  in the built bundle are the unrelated zero-dependency `react-native-reanimated-table`
  (via `react-native-marked`) plus one comment in `react-native-screens`. Do not chase it.
- `react-native` **hand-patched** (`patches/react-native@0.81.5.patch`) purely to accept
  React 19.1.2 instead of 19.1.0 — verified as version-string-only across three renderer
  files, no logic changes. Correct and minimal, but it must be re-derived on every RN
  upgrade: a standing maintenance cost.
- **5 declared-but-unused deps** (`@react-navigation/bottom-tabs`, `expo-auth-session`,
  `expo-linking`, `expo-web-browser`, `react-native-keyboard-aware-scroll-view`) and
  **~19 dead files**.
- `expo-constants` **undeclared but imported**, two versions installed.

## Build & release

No CI exists (`.github` absent), so there is no gate on typecheck, lint, test or
migrations for the mobile app either. `eas.json` has no channels. The `publish` script
(`eas update --branch preview`) shells out through `grep`/`xargs` over `.env`, which will
break on any value containing spaces. There is no documented staging build or internal
distribution flow beyond the profile names.

---

# 5. What the client enforces that the server should

This was called out specifically, and it is the most important section for the security
narrative.

| Control | Enforced in | Should be | Consequence |
| --- | --- | --- | --- |
| **Crisis chat block** | `ChatScreen.tsx:299` only | Server: reject `chat()` when `thread.crisisDetected` | C3 — any non-UI caller bypasses the safety gate; the response even reports `crisisDetected: false` |
| **Thread ownership on read** | Nothing — assumed | Server/DB: `ctx.userId` filter or RLS | C1 — reproduced cross-user transcript read |
| **Thread ownership on write** | Nothing | DB: `WITH CHECK` on `messages` INSERT | C2 — forged `role:"mani"` turns into any thread |
| **`crisis_detected` immutability** | Nothing | DB: column-restricted UPDATE grant | H2 — user can `PATCH` the flag off |
| **Technique cooldown / frequency** | Model + `[ctx]` block in the message body | Server-side derived state, not in-band text | L3 — user can forge a second `[ctx]` block |
| **App attestation** | `SecurityProvider` sets headers | Server verifies — but `app_check` client side is an unimplemented `TODO` | M4/M8 — only `none` or a bundle-readable shared key are usable |
| **Double-submit** | `ChatScreen` `isPending` guard ✔ | Fine at client level given `clientMessageId` idempotency | Correctly placed |
| **Rate limiting** | Nothing anywhere | Server | M6 — `messages.chat` unmetered, each call paid |

The pattern: **everything protective except double-submit lives on the wrong side of the
trust boundary.** A mobile client is an untrusted input source; four of these controls
assume it is trusted.

---

# 6. Client-side security & privacy — measured

Evidence taken from the actual 9,467,693-byte iOS dev bundle.

| Probe | Hits | Reading |
| --- | --- | --- |
| Supabase **anon** JWT | 2 | Present in plaintext — **by design** for `EXPO_PUBLIC_*`. This is the foundation of the client trust model, and it is why C2/H2 are exploitable from any installed copy. |
| `http://192.168.88.100:3001 / :54331 / :8081` | 5 | Backend, Supabase and Metro URLs embedded — expected |
| **service-role** key | 0 | ✔ not present. Only one unique JWT in the bundle, the anon key |
| `sb_secret` | 0 | ✔ |
| OpenRouter key / `sk-or-v1` | 0 | ✔ LLM credentials never reach the client |

**That is the right outcome** — the genuinely dangerous secrets are server-side only. The
risk is not leaked secrets; it is that the *intended-public* anon key plus over-broad table
grants equals a usable write path (C2/H2).

**Local storage.** Session JSON and device id in `expo-secure-store` (Keychain / Keystore);
only a notification boolean in `AsyncStorage`. This is the correct split — no tokens in
plaintext storage. `clearAuthStorage` exists as a debug helper and is dead code.

**Logging.** 29 `console.*` calls in mobile source, and they log **error objects, not
conversation content** — materially better than the backend, where
`packages/api/src/routers/messages.ts:196-315` writes thread ids and chat context to
`console.debug` unconditionally. Mobile's remaining exposure is that these calls are not
`__DEV__`-gated, so Supabase error strings (which can contain email addresses) reach
device logs in production. LOW.

---

# 7. Documentation vs mobile reality — design or drift?

| Documented | Actual | Verdict |
| --- | --- | --- |
| `TabNavigator (bottom tabs)` with `DashboardStack`, `AboutStack`, `InformationScreen`, `AboutScreen` (root `CLAUDE.md`) | Four `createNativeStackNavigator`, zero tab navigators; `bottom-tabs` unused; those two screens do not exist | **Drift** — describes an app that no longer exists. Undocumented but real: `OnboardingScreen`, `chat`, `exercises`, `ChangeEmail`, `ChangePassword` |
| `expo-auth-session` among native deps "it uses" (`ExpoGO(Setup).md`) | Unused, with `expo-web-browser` and `expo-linking` | **Drift** |
| Two Supabase/API base URLs on the client | Matches code | **Intentional design** — consequence of Supabase Auth |
| `metro.config.js` overrides | expo-doctor flags them | **Intentional** — required by hoisted pnpm; keep, and document why |
| `EXPO_PUBLIC_*` values are public | Matches bundle evidence | **Intentional** |
| Editing `prompts/*.md` + re-seed changes behaviour | `title_generation.md` and `summarization.md` are never read | **Drift** — dead files with a live-looking workflow |

The distinction matters for Thursday: the mobile *architecture* is not drifting from
intent. The *documentation* is. In an AI-assisted codebase that is an active defect, since
every session ingests `CLAUDE.md` as ground truth — and it is the cheapest thing on the
remediation list.

---

# 8. Why 30+ findings — including Criticals — still does not mean a rebuild

This is the question the report has to answer with structure, not assertion.

## 8.1 The findings collapse into six root causes

| # | Root cause | Findings it produces | Weight |
| --- | --- | --- | --- |
| **RC1** | Service-role client bypasses RLS; per-method `userId` discipline is the only control | C1, C2, C4, H2, L1, parts of the privacy exposure | ~40% of severity-weighted risk |
| **RC2** | Safety state is client-enforced and model-reported | C3, H3, H9, L3 | product-critical |
| **RC3** | One 1,600-line orchestrator doing context, LLM retries, a state machine and 9 writes | H5, H6, H7, H8, M9–M12, both concurrency races | maintainability ceiling |
| **RC4** | No operational scaffolding (no CI, no error tracking, no rate limiting) | H4's silence, most reliability findings, unbounded cost | systemic but additive |
| **RC5** | Documentation and configuration drift | all doc findings, most config findings | cheap |
| **RC6** | Mobile resilience gaps | MOB-1, MOB-2, MOB-3, MOB-10 | localized |

**Thirty-plus findings are not thirty-plus problems.** They are six causes with many
symptoms. That distinction is the whole argument.

## 8.2 The layers that are expensive to change are the ones that are correct

A rebuild is justified when the parts you *cannot* cheaply change are wrong. Ranked by
cost-to-retrofit:

| Layer | Cost to change later | State |
| --- | --- | --- |
| Data model / schema | Very high (live data migration) | **Sound** — 24 sequential migrations, correct cascades, indexes match query shapes, `db lint` clean, no drift in generated types |
| Module boundaries & dependency direction | Very high (touches everything) | **Correct** — `apps → packages`, never inverted |
| Client/server contract | High | **Single-sourced** — tRPC + zod, four packages type-check clean |
| Bundle isolation | High | **Enforced** — `@mani/api` vs `/server`, backed by an eslint rule |
| Authorization *mechanism* | **Low** — one client construction + policies | **Wrong**, and cheap to fix |
| Orchestrator internals | Medium — extraction behind existing tests | **Overgrown**, not misdesigned |
| Ops scaffolding | Low — additive | **Absent** |
| Docs | Very low | **Stale** |

The wrongness is concentrated in the *cheap* rows. That is the opposite of the profile that
justifies a rebuild.

## 8.3 The criticals are small diffs, not redesigns

| Finding | Fix shape | Rough size |
| --- | --- | --- |
| C1 cross-user read | pass `ctx.userId` through 3 call layers | ~5 lines |
| C4 unauthenticated RPC insert | `auth.uid()` guard in the function + revoke `anon` EXECUTE | ~10 lines SQL |
| C2 cross-thread insert | add `WITH CHECK` on one policy | 1 migration |
| C3 crisis not enforced | guard clause at `chat()` entry | ~5 lines |
| H1 magic-link login broken | one entry in the `proxy.ts` allow-list | 1 line |
| H2 user can clear crisis flag | column-restricted UPDATE grant | 1 migration |

Severity measures *consequence*, not *structural depth*. These are severe because the data
is sensitive, not because the architecture cannot express the fix.

## 8.4 Nothing found is a platform or paradigm limitation

Not one finding reduces to "tRPC cannot express this", "Supabase cannot enforce this",
"Expo cannot support this", or "the schema cannot represent this". Every finding is an
implementation or configuration choice made inside a design that can accommodate the
correct choice. RC1 in particular is *fixable in the direction the architecture already
points*: RLS policies already exist and are already correct — they are simply not
consulted. The fix is to start using what is already built.

## 8.5 The counter-test

What would have changed my conclusion, and did not hold:

- ✗ **Wrong data model** requiring live-data migration → schema is sound
- ✗ **Tangled boundaries** where changes cascade unpredictably → boundaries are clean and lint-enforced
- ✗ **Framework that cannot meet requirements** → tRPC/Supabase/Expo all fit
- ✗ **No test safety net** for refactoring → 666 real tests, 19.4% mock-assertion ratio, no self-mocking modules
- ✗ **Business logic duplicated across the client** → mobile holds presentation and one misplaced safety gate, not duplicated logic
- ✗ **Mobile architecturally incoherent** → checked this pass; it is conventional and coherent

All six fail. The conclusion stands, and the mobile pass removed the last open question.

## 8.6 The honest caveat

"No rebuild" is **not** "low risk". The severity is real, two criticals were reproduced
against a running system, and the product handles suicidal-ideation disclosures. The claim
is narrower and should be stated exactly this way on Thursday:

> The defects are severe in consequence and shallow in structure. They are concentrated in
> six root causes, the most damaging of which is fixed by *enabling protection that already
> exists*. Rebuilding would consume the remediation budget re-deriving the parts that are
> already correct, while leaving the authorization model — the actual problem — untouched.

---

# 9. Keep / Fix / Restructure / Replace

## KEEP — correct, do not touch

- Monorepo layout and the `apps → packages` dependency direction
- `packages/api` as the single contract; tRPC + zod end to end
- `@mani/api` vs `@mani/api/server` split and the eslint rule enforcing it
- Database schema, migrations, cascade behaviour, index design — *superseded 2026-09-14: with
  beta data confirmed throwaway, the schema is being rebuilt from scratch rather than kept.
  Cascade behaviour and index design were right and carry over; the migration history gets
  squashed and six structural changes land in one pass. See
  [[2026-09-14-architecture-decisions]] #1.*
- `lib/security/encryption.ts` — AES-256-GCM, per-op IV, enforced auth tag, PBKDF2, production salt check
  — *still correct, but it leaves the chat request path: the OpenRouter key moves to
  ai-service's environment (#4), which also fixes M5.*
- Prompts as versioned markdown + DB seeding + admin portal — *keep the mechanism; direction of
  authority was undefined and is now decided — the portal is authoritative, markdown is
  bootstrap-only (#7).*
- `packages/design-tokens` and the generated CSS variables
- **Client persistence split** — session in SecureStore, preferences in AsyncStorage
- **`ChatScreen` failure handling** — `isMounted` guards, optimistic message, retryable-error Alert
- **`createPair` via the transactional RPC** (the function's *authorization* needs fixing; its atomicity is right)
- The `react-native` patch (minimal and correct) — but track it as a standing cost
- `metro.config.js` overrides — intentional for hoisted pnpm; document rather than "fix"
- The test suite as the refactoring safety net

## FIX — targeted, bounded changes

Security/safety: C1 `messages.list` ownership · C2 INSERT `WITH CHECK` · C4 RPC guard +
revoke `anon` · C3 server-side crisis gate · H2 column-restricted UPDATE grant · H1
`proxy.ts` allow-list · M7 anon key in the auth callback · H9 bound and escape `nickname`
· pin `search_path` on the three `SECURITY DEFINER` functions.

Correctness: H4 summarisation provider coherence · H5 missing `.limit()` · M10 title cap
mismatch · the two read-modify-write array appends.

Mobile: MOB-1 · MOB-2 · MOB-3 · MOB-4 · MOB-5 · MOB-6 · MOB-7 · MOB-8 · MOB-9 · MOB-10.

Config/infra: `turbo.json` `globalEnv` · `vercel.json`/README conflict · `.eslintignore`
excluding `__tests__` · `design-tokens` lint config · `eas.json` channels · add
`pnpm-lock.yaml` and `src/types/supabase.ts` to `.prettierignore` · drop 6 redundant
indexes.

Docs: root `CLAUDE.md` navigation section · the two dead prompt files · the
"constraints last" claim · `README.md` `.tool-versions` and Next version · `ExpoGO`
dependency list.

## RESTRUCTURE — same architecture, different internal shape

1. **Authorization mechanism → make Postgres the authority.** Build the per-request
   `publicClient` from the user's JWT so RLS applies; reserve service-role for genuinely
   cross-user admin work under a distinct name. Then decide explicitly whether the mobile
   client may ever hit PostgREST directly — the code says no, so revoke table DML from
   `authenticated`. This is the single highest-leverage change in the whole assessment.
2. **`services/messages.ts` → extract three modules**: a technique state machine with an
   explicit validated transition table; a regeneration policy chain with a retry budget and
   one re-validation pass; a single transactional turn-persistence unit covering the pair
   *and* the thread-state writes.
3. **Model-output trust boundary** → technique and step identifiers become zod enums
   validated before use as keys, indexes or persisted values.
4. **`[ctx]` control block** → out of the message body and out of persistence; pass it as
   structured context, not in-band text.
5. **`AuthProvider`** → split the 20-action context into auth-state and auth-actions
   contexts so consumers stop re-rendering on unrelated state.

## REPLACE — genuinely swap out

Very little, which is itself the finding.

- **`firebase-admin`** — carries 4 of the 6 critical advisories for App Check, which is off
  by default and has an unimplemented client side. Either implement App Check properly or
  remove the dependency. Carrying it as-is is not defensible either way.
- **The `useFonts` boot gate** — replace the boolean gate with an error-aware one.
- **`expo-constants` usage in `ExercisePlayerScreen`** — replace with `EXPO_PUBLIC_API_URL`.
- **Expo SDK 54 → 57** — one deliberate unit migration, not per-package bumps.
- **`expo-av`** — deprecated in SDK 54 and removed in later SDKs; the 57 migration will
  force `expo-audio`. Plan it with the SDK move, not separately.
- Consider replacing the hand-rolled `.env`-parsing `publish` script with `eas env`.

**Not replaced:** Supabase, Vercel, Expo, tRPC, TanStack Query, Next.js, the schema.

---

# 10. Recommended order of work

Sequenced by severity **and dependency** — each phase is shippable, and later phases assume
the earlier safety net.

## Phase 0 — Stop the bleeding (days) · no refactoring permitted

Ordered so that data exposure closes first.

1. C1 — pass `ctx.userId` through `messages.list` → service → `getForThread`
2. C4 — `auth.uid()` validation inside `insert_message_pair`; revoke `anon` EXECUTE
3. C2 — `WITH CHECK` on `messages` INSERT validating thread ownership
4. H2 — restrict the `threads` UPDATE grant to user-editable columns
5. C3 — reject `chat()` on a crisis-flagged thread; stop returning `crisisDetected: false`
6. H1 — allow-list `/admin/auth/callback` in `proxy.ts`
7. H4 / H5 — make summarisation's provider config coherent; add the missing `.limit()`
8. MOB-2 + MOB-3 — error-aware font gate and one error boundary

*Why this order:* 1–4 are independent and close the reproduced exploits. 5 depends on
nothing but is the safety control. 8 is included here because it converts your current
Android dead end into a legible error, which every later phase benefits from.

## Phase 1 — Build the net (1–2 weeks) · prerequisite for Phase 2

9. CI on every PR: typecheck, lint, test, migration check
10. `pnpm lint` to zero; stop excluding `__tests__`; add `design-tokens` lint config
11. Error tracking on backend **and** mobile
12. Rate limiting on `messages.chat` (`deviceId` is already collected and unused)
13. Staging Supabase project + Vercel preview environment
14. Fix `turbo.json` `globalEnv` and the `vercel.json`/README conflict
15. MOB-1 (cheaper option: cap `nickname`, move `pending_flow` out of `user_metadata`)
16. Remove unconditional `console.debug` from `packages/api/src/routers/messages.ts`

*Why before Phase 2:* the RLS migration and the orchestrator extraction are the two
riskiest changes in the plan. Doing them without CI, staging or error tracking is how you
turn a security fix into an outage.

## Phase 2 — Structural fix (2–4 weeks) · highest leverage

17. JWT-scoped `publicClient`; RLS becomes the authority — rehearsed on staging
18. Revoke table-level DML from `authenticated` once 17 is proven
19. Extract the technique state machine; write tests against it *before* moving it
20. Model-output trust boundary (zod enums for technique/step)
21. Regeneration policy chain with a retry budget; move the crisis check ahead of it (H3)
22. Single transactional turn persistence; replace the two read-modify-write appends
23. MOB-4, MOB-5, MOB-8, MOB-9, MOB-10

*Why this order:* 17 makes 18 safe. 19 must precede 21, because the regeneration triggers
read state-machine state. 22 last, because it touches every write site the earlier steps
move.

## Phase 3 — Carrying cost (ongoing, parallelizable)

24. `firebase-admin`: implement App Check or remove
25. Expo SDK 54 → 57 as one unit; `expo-av` → `expo-audio`; re-derive or retire the RN patch
26. MOB-6, MOB-7, MOB-11 cluster
27. Delete ~19 dead files and 5 unused dependencies; drop 6 redundant indexes
28. `.prettierignore` for generated files

## Phase 4 — Truth and governance

29. Correct root `CLAUDE.md` navigation; wire or delete the two dead prompt files;
    reconcile "constraints last"
30. Data-retention policy + enforcing migration; access logging on the admin chat viewer;
    log redaction
31. Cost telemetry: tokens and LLM calls per turn, alert on regeneration rate

*Phase 4 is last in sequence but item 29 is the cheapest item in the entire plan and can be
done at any time — it is only last because nothing depends on it.*

---

# 11. Evidence appendix — mechanical checks run this pass

| Check | Result |
| --- | --- |
| Bundle secret scan (9,467,693 bytes, iOS dev bundle) | anon JWT ×2, LAN URLs ×5, **service-role 0, OpenRouter 0** |
| Session payload measurement vs Android SecureStore 2048 B | 1,861 baseline → 1,999 post-onboarding → **2,080 with `pending_flow` (over)** |
| `nickname` length constraint | **none** in schema or input |
| SecureStore / AsyncStorage inventory | session + deviceId in SecureStore; notification flag only in AsyncStorage |
| Mobile `console.*` census | 29 non-test calls, all error objects, no transcript content |
| Timer/listener leak sweep | `ChatDrawer` set=6 clear=0; `BackHandler` correctly removed; no other leaks |
| Font payload | 7 faces, 1,459,712 bytes total |
| Error-boundary search | 0 occurrences of all three React APIs |
| `app.json` `extra` / `infoPlist` | no `apiUrl`; no `UIBackgroundModes` |
| CI presence | **no `.github` directory** |
| Observability / rate limiting SDKs | **none declared** in any `package.json` |
| Reanimated reachability | 0 imports in `src`; bundle hits are `react-native-reanimated-table` + one comment |
| `react-native` patch contents | version strings only, 3 files, no logic |
| Generated-types drift | **no schema drift**; 820-line diff is entirely Prettier |
| User-deletion cascade | CASCADE on all four user tables ✔ |

---

# 12. Still open

- **Backend service internals** — per-method error handling and edge cases; the original
  pass died there and it was covered only where other angles surfaced it. Would likely add
  MEDIUM findings; would not change the verdict.
- **Runtime confirmation of MOB-2** on muhammad's device. The mechanism is proven by code
  reading and measurement; the specific failing asset fetch is not. `adb logcat` during a
  failed load would confirm it in one attempt.
