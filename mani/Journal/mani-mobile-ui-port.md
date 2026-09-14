---
type: journal
date: 2026-09-14
apps: [mobile]
tags: [journal, mobile, design-system, port]
---

# Porting mani-app's mobile UI into mobile/ (UI layer only, no API)

## What happened

Asked to move the UI layer and design system from a reference project
(`/Users/mac/Desktop/mani-app/apps/mobile`, a monorepo app on Expo SDK 54 +
React Navigation 6 + tRPC + Supabase) into this repo's `mobile/` (Expo SDK 57 +
expo-router + NativeWind v5), UI/design-system only — no backend, no auth,
no `@mani/api` types.

Read the whole source app first (screens, components, hooks, design-tokens
package, navigation, providers) before proposing anything. Confirmed several
SDK-57-specific facts against live docs via a subagent rather than from
training-data memory, per the `expo-react-native` skill's instruction to read
versioned docs — two of my own pre-verification assumptions turned out wrong:

- **`@expo/vector-icons` is deprecated as of SDK 56.** Expo's own icon guide
  says to migrate to `@react-native-vector-icons/*`. Its SDK 57 reference page
  404s. Used `/feather` and `/ionicons`, imported via the `/static` subpath
  (not the default dynamic-loading import) since we already need dev builds
  for custom font embedding (Montserrat), so there's no Expo-Go-only path to
  protect. All glyph names (`menu`, `chevron-left`, `book-open`, etc.) are
  identical between the old and new packages — verified against both
  packages' glyphmap JSON files before committing to the swap. It's a pure
  import-path translation everywhere it's used.
- **`expo-blur` needs `BlurTargetView` on Android in SDK 57** — a `BlurView`
  just overlaid on siblings (the source's `PhoneContainer` pattern) renders
  unblurred on Android without it. Not yet ported (that's Stage 3); noting it
  here so it isn't rediscovered the hard way.

Design tokens live in a separate `@mani/design-tokens` workspace package in
the source (colors, typography, spacing, radii, shadows, transitions as TS
objects). Ported the palette into `mobile/src/global.css`'s `@theme` block
(Tailwind v4 CSS-first tokens NativeWind resolves natively) plus a TS mirror
at `mobile/src/lib/tokens.ts` for the handful of cases that take a raw color
value instead of a className (gradients, SVG, animated interpolation). Full
reasoning in [[ADR-002]].

Deliberately did not carry over the source's spacing scale — its 4px-based
scale is numerically identical to Tailwind's built-in default, so redeclaring
it would just be reimplementing something already free.

## Insight

**`npx expo install <pkg>` can fail on `EALLOWSCRIPTS` even for a
non-scripted package**, when the project's `package.json` already declares
its own `allowScripts` field — `expo install`'s npm wrapper passes
`--allow-scripts` unconditionally, which plain npm refuses for project-scoped
installs once `allowScripts` exists in `package.json`. Fix: fall back to a
plain `npm install <pkg>` for anything `expo install` chokes on this way; it
still resolves the correct SDK-compatible version from the registry, it just
skips Expo's own compatibility-pinning step (worth a manual version glance
after, which `expo-doctor` also catches).

**A metro/hermes export with `--platform ios` produces a `0B` web CSS file —
this is expected, not a broken build.** Native NativeWind styles compile
directly into the JS/Hermes bundle, not a separate stylesheet; the CSS output
path is web-only. Don't read `0B` there as evidence anything is wrong. I
initially misread this as a failure and had to double-check before reporting
it — worth remembering so a future me doesn't re-panic over the same file.

**Verifying "does `className` survive next to a Reanimated `style` prop" is
not something a bundle export can answer.** Tree-shaking excludes anything
not imported by a reached route, and a successful Hermes bytecode compile
doesn't prove runtime style resolution behaves right — Hermes bytecode isn't
inspectable with `grep` either. Wrote a real spike component
(`src/components/shared/NativewindReanimatedSpike.tsx`, not wired into any
route) with instructions for a manual simulator check, and confirmed only
that wiring it into a real route compiles cleanly (1670 modules, no errors).
**The actual visual behavior is still unverified** — this environment has no
simulator. Whoever picks up Stage 2/3 should run the spike on a real
simulator before leaning on `className` + Reanimated `style` together at
scale; if `className` drops, the fix is upgrading past `nativewind@5.0.0-preview.4`.

**Made one real (not cosmetic) architectural split under skill pressure**:
the source's `useResponsiveTypography` (91 lines) exceeded the hooks' 80-line
cap. Rather than trim lines arbitrarily, split out `layout`/`notificationStack`
(positioning/animation constants, not type scale) into a sibling
`useResponsiveLayout` hook — a real seam, not a cosmetic one. This is a
genuine behavioral divergence from source: code that previously read
`typography.layout.horizontalPadding` from one hook now calls
`useResponsiveLayout().horizontalPadding` from a second one. Both hooks
land at 64 and 35 lines. Flagging explicitly since it'll affect how Stage 4
screens (Home, onboarding steps) get written relative to the source files.

**`app.json`'s `expo-font` plugin needs the per-platform object form, not the
flat `fonts: [...]` array, when the app has more than one weight of the same
family and needs identical `fontFamily` strings on both platforms.** The flat
array only sets a custom family name via XML on Android when given `{
fontFamily, fontDefinitions }` objects; given plain string paths (what I
wrote on the first pass), iOS resolves by the font file's own embedded
PostScript name (works out because `@expo-google-fonts` ships files whose
PostScript name already is `Montserrat-SemiBold` etc.) but **Android copies
the file as a raw asset keyed by filename** (`Montserrat_600SemiBold`, not
`Montserrat-SemiBold`) with no family override — so `fontFamily:
'Montserrat-SemiBold'` would silently fall back to the system font on
Android only, an iOS-only-looking bug that's easy to ship unnoticed since
this environment has no Android emulator either. Fixed by moving to
`ios.fonts` (flat array, PostScript-name resolution) + `android.fonts`
(object form, explicit `fontFamily` declared to match). Verified the actual
PostScript names by parsing each ttf's `name` table directly (`struct` over
the raw sfnt bytes) rather than assuming — this is worth doing for any font
family being embedded this way, not just trusting the filename.

**RN's `Text`/CSS's `font-weight` and native `fontFamily` selection are two
different mechanisms, and Tailwind's stock `font-semibold`/`font-bold`
utilities only touch the former.** Discrete font files per weight (not a
single variable font) need a `fontFamily` swap to actually render bolder —
`font-weight: 600` alone does nothing on native unless RN can fake-embolden
the *system* font, which isn't what "SemiBold Montserrat" means. Defined
custom `--font-sans-medium` / `--font-sans-semibold` / `--font-sans-bold`
tokens in `global.css` (verified via `expo export --platform web`, which is
the one export target that produces inspectable CSS — confirmed
`.font-sans-semibold { font-family: var(--font-sans-semibold) }` in the
actual compiled output before trusting the pattern for eight components).
Use `font-sans-semibold`, not `font-semibold`, everywhere in this app.

**Reanimated 4's `withSpring` does not accept RN Animated's `{ speed,
bounciness }` config shape** — it's `{ mass, damping, stiffness }` or `{
duration, dampingRatio }` (mutually exclusive per Reanimated's own type).
`tsc` catches this immediately (not a silent behavior change), but the
*translation* still needs a human call: `speed: 50, bounciness: 4` was RN's
way of saying "fast, barely any overshoot" — the nearest equivalent is a
short `duration` with `dampingRatio` close to (not at) 1, not a guess at
unrelated `mass`/`stiffness` numbers.

**One real fidelity bug caught by re-deriving the animation from source
rather than porting on sight**: `GradientSphere`'s breathing pulse is
`Animated.loop(Animated.timing(0 -> 1))` — a sawtooth (snaps back to 0, no
reverse) — with a `[0, 0.5, 1] -> [1, 1.08, 1]` scale interpolation. The
up-then-down *visual* pulse comes entirely from that interpolation curve,
not from the animation reversing. My first Reanimated draft used
`withRepeat(withTiming(1), -1, true)` (reverse=true) with a linear `1 +
value * 0.08` mapping — technically "a pulse," but on a different curve and
effectively double the period. Fixed by keeping `withRepeat(..., -1, false)`
(sawtooth, matching source) and porting the exact `interpolate([0, 0.5, 1],
[1, 1.08, 1])` call. Generalizes: when porting an `Animated.loop` +
`.interpolate()` pair, the reverse/no-reverse choice on the Reanimated side
and the shape of the interpolation are coupled — changing one without the
other changes the felt motion even though both "look like a breathing
animation" in isolation.

## Applies to

Any future Expo SDK upgrade in `mobile/` (re-check `@expo/vector-icons`
status, expo-blur Android behavior, and the nativewind/reanimated interaction
each time — none of these are settled facts, they're SDK-57-specific).
Also applies whenever adding a dependency that needs a native
config-plugin entry (fonts, icon sets) — those require a dev build, not
Expo Go, so a decision to add one is also implicitly a decision to require
dev builds project-wide.

## Stage 2 (primitives) — additional findings

**React Native Vector Icons' components (`Feather`, `Ionicons` via `/static`)
are not confirmed NativeWind-`className`-aware.** They compile fine with a
`className` prop (NativeWind's babel transform accepts `className` on
arbitrary components without a type error), but that only proves it doesn't
crash — not that the resulting style actually applies, and this environment
has no simulator to check visually. Standing rule for this codebase: **never
put layout classes (margin, etc.) via `className` on a vector icon
component — always use `style={{ ... }}`**, which is guaranteed to work
regardless of whether NativeWind wraps that specific library.

**`react-native-marked` jumped a major version (source used ^7.1.1, SDK 57
resolved ^8.3.0) and the `Renderer` base class's method signatures changed**
for `paragraph`/`listItem`/`blockquote` (now `ViewStyle`, were `TextStyle`)
and `code` (gained a `containerStyle` parameter, shifting `textStyle` to 4th
position). A verbatim copy of source's `NoScaleRenderer` override fails to
compile — `tsc` catches the type mismatch immediately, but the *fix* still
needs a human call on which new parameter maps to which old one (mapping
`code`'s old single `styles` param to the new `textStyle`, not
`containerStyle`, matches what the old single-param version was styling).
Before porting any file that subclasses/extends a third-party library's
class, diff the installed version's `.d.ts` against what the source code
assumes — a passing `npm install` says nothing about API compatibility.

## Stage 3 (composite components) — findings

**Extracting genuine business logic (not UI) triggers the CLAUDE.md testing
rule even mid-port.** `groupThreadsByDate` (bucketing chat threads into
Today/Yesterday/Older) is real logic with edge cases, unlike everything else
ported so far which is presentational. Installed `jest` + `jest-expo` +
`@react-native/jest-preset` (had to pin the last one to `^0.86.3` — jest-expo
now treats it as an explicit peer dependency rather than bundling it, and
without the exact RN-version-matched preset the whole suite fails to even
load) purely to cover this one function properly, with fake `ThreadListItem`
objects and an injectable `now` parameter so the test isn't mocking `Date`
globally. Small, deliberate scope increase — flagged and confirmed with
muhammad first rather than assumed.

**React Compiler (enabled via `app.json`, mandatory per the skill) and
Reanimated's `sharedValue.value = ...` mutation idiom have a real, and
non-obvious, compatibility trap tied to *code order within the component*,
not just presence.** `send-button.tsx` (Stage 2) passed lint fine with
handlers defined before `useAnimatedStyle`. Writing the same pattern in
`smart-prompt-chip.tsx` with `useAnimatedStyle` defined *before* the
handlers that later mutate the same shared value produced two failures:
`"Compilation Skipped: Existing memoization could not be preserved"` and
`"This value cannot be modified"` on the `.value =` assignment — as if
React Compiler's static analysis, on encountering `useAnimatedStyle`'s
closure first, commits to treating the shared value as already-resolved/
immutable, and then flags every later mutation of it as illegal. Moving the
handler definitions above `useAnimatedStyle` — no other change — fixed both
errors. **Standing rule: in any component combining `useSharedValue` +
`useAnimatedStyle` + a mutating handler, define the handlers that mutate
`.value` before calling `useAnimatedStyle`, even though "compute the style,
then define handlers that trigger it" is the more natural reading order.**
This will bite again the first time someone writes a new Reanimated
component in the natural order. Also worth restating the skill's own
guidance that bit me first: React Compiler makes most `useMemo` unnecessary,
and a stale one *copied from source without re-justifying it* is what
triggered the memoization-cascade error in the first place — question every
`useMemo`/`useCallback` carried over from source, don't just copy it.

**`ChatDrawer` (551 lines in source) decomposed into 4 files, 277 lines
total** — shell + nav-section + thread-list + profile-footer, plus the
pure `groupThreadsByDate` utility pulled out separately. The line-count drop
isn't just "fewer features ported" — StyleSheet objects are genuinely more
verbose than Tailwind classNames for the same visual result, so the
NativeWind port compresses real UI code, not just cuts corners.

**`ChatHeader.tsx` in source is dead code** — grep confirms `ChatScreen`
actually renders `AppHeader`, and nothing outside `ChatHeader`'s own file
and its own barrel export references it. Skipped porting it entirely per
the agreed cleanup policy; `AppHeader` (which *is* used) covers the same
visual ground and more.

**Discovered `rgba(255, 244, 225, ...)` throughout source is always
`secondary-500` (`#FFF4E1`) at some opacity** — verified byte-for-byte via
Python, not eyeballed. Wherever source hardcodes that rgba triplet with a
varying alpha, the port uses `bg-secondary-500/N` (Tailwind's opacity
modifier) instead of a raw rgba string or arbitrary value, keeping it a
named-token reference instead of a magic literal.

**Added a `src/providers/` folder** (not in the `expo-react-native` skill's
documented layout) to hold `DrawerProvider` — a context provider is neither
a hook (no JSX capping rules make sense for it) nor a rendered UI component.
Confirmed with muhammad before adding a new top-level convention; the skill
itself should probably be updated to document this rather than leaving it
implicit — flagged as a follow-up, not yet done.

**Font family literals belong in `lib/tokens.ts`, not re-typed per file.**
First draft of `markdown-styles.ts` (react-native-marked's raw style object,
which can't take a className) re-declared `'Montserrat-Regular'`/
`'Montserrat-Bold'` as local constants — caught on review as a Golden-Rule-4
violation, since those exact strings already exist as the `--font-sans*`
CSS tokens from Stage 1. Added a `fonts` export to `lib/tokens.ts`
mirroring them, matching how `colors`/`radii` already work there.

## Post-Stage-3 restructure: chat/crisis/settings moved out of shared/

muhammad asked to move `components/shared/chat`, `/crisis`, `/settings` out
from under `shared/` — they're now `components/chat/`, `components/crisis/`,
`components/settings/`, siblings of `shared/` rather than nested in it.
`shared/` is reserved for primitives with no domain knowledge (Text, buttons,
inputs); once a cluster of components only makes sense together for one
feature, it gets its own top-level folder under `components/`. Updated the
`expo-react-native` skill's layout section and reuse-lookup table to
document this distinction, same as the `providers/` addition in Stage 3 —
neither was in the skill's original layout, both came from real folders this
port needed and got confirmed with muhammad before landing in the skill.

Mechanically: `mv` (not `git mv` — untracked files, git saw the source as
"empty"), then fixed each moved file's `'../text'`-style relative imports
that used to reach into the parent `shared/` folder — now that they're
siblings, not parent/child, those became `@/components/shared` barrel
imports instead of a relative path climbing back up. Barrel header comments
that hardcoded the old `@/components/shared/chat` path also needed updating
— easy to miss since they're just comments, not import statements a
type-checker would catch.

## Stage 4 (screens + routing), phases A-D — findings

**expo-router's `typedRoutes` type-checks route strings against a generated
file (`.expo/types/router.d.ts`) that is NOT regenerated by `tsc` alone.**
Creating `src/app/chat.tsx` doesn't make `router.push('/chat')` type-check
anywhere else until something re-scans the route tree — `expo start`, `expo
export`, or (found by accident) `expo customize <file>` all trigger it as a
side effect. Building routes in dependency order (leaf screens before the
things that link to them) means living with expected, temporary `tsc`
errors on every not-yet-created route — confirmed this repeatedly by diffing
the error list before/after each new file, rather than treating any
route-shaped error as a real bug mid-build.

**`react-hooks/set-state-in-effect` (a React-Compiler-era lint rule, not the
older `exhaustive-deps`) flags `void someAsyncFn()` inside a bare
`useEffect`, even when the setState calls happen inside the async
function's own `.then`/`await` continuation, not synchronously in the
effect body.** The rule apparently can't statically follow the promise
chain through an extracted `useCallback`. Fix: inline the promise chain
directly in the effect with an explicit `isMounted` guard and cleanup
function — satisfies the linter and is the more correct pattern anyway
(no state update after unmount). `useNotificationPreference` needed this;
worth checking any other "load once on mount" hook for the same shape.

**`AppHeader`'s source coupling to `useNavigation()`/`useNavigateToNewChat()`
was replaced with `onBack`/`onNewChatPress` callback props** (decided in
Stage 3, paid off here) — every screen supplies its own `router.back()` /
`router.push(...)` without `AppHeader` itself importing expo-router. Same
pattern extended to `ChatDrawer`'s nav callbacks in `GlobalDrawer`
(`components/global-drawer.tsx`, composed in `_layout.tsx` as a sibling of
`<Stack>`, matching the verified-in-Stage-1 idiom).

**Chat has no backend, so ChatScreen's tRPC orchestration was replaced with
`useChatSimulation`** — a local hook that appends the user's message,
waits ~900ms, and appends a canned reply, with a magic-keyword trigger
("crisis"/"unsafe"/"emergency") for the crisis-detected path so
`CrisisBanner` and the crisis drawer are actually reachable and demoable,
not dead code. Confirmed this scope with muhammad before building it,
since source's real send/receive loop is ~70% network plumbing with
nothing to preserve fidelity against.

**ChangeEmailScreen and ChangePasswordScreen share enough structure
(dark background + noise overlay + back-button header + fade-in form) that
a shared `AuthScreenShell` was worth extracting** before writing either
screen, not after — avoided ~60 lines of duplicated boilerplate. Both
screens replace `useAuth()` or Supabase calls with local `setTimeout`-
delayed state transitions and generic (not server-parsed) error messages,
per the same "port the full UI shape, stub the network" pattern as chat.

**`change-email.tsx` came in at 158 lines** (over the 150-line cap) after
porting both phases (enter-email, verify-OTP) into one file. Split into
`ChangeEmailForm` and `VerifyOtpForm` — the same two-form-per-screen
pattern that will recur heavily in onboarding (Stage 4 phase E), so this is
worth remembering as the standard decomposition move for multi-phase
screens, not a one-off.

**Full app boots**: a real `expo export --platform ios` bundled the root
layout, all of Home/Chat/Settings/Exercises(index/category/player)/
ChangePassword/ChangeEmail together with no errors — the first point in
this port where every route actually resolves as one app, not isolated
component exports.

## Links

- [[ADR-002]]
- Stage 1 (foundation: tokens, fonts, icons, assets, responsive hooks),
  Stage 2 (11 shared primitives), and Stage 3 (chat/crisis/settings
  composite components + AppHeader + DrawerProvider, later moved to be
  siblings of shared/ rather than nested in it) are done. Stage 4 phases
  A-D (routing skeleton, Home/Settings/Exercises, Chat, ChangePassword/
  ChangeEmail) are done. Onboarding (Stage 4 phase E, by far the largest
  remaining piece — 11 steps + animated background + a UI-only state
  machine) has not been started as of this entry.
