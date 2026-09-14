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

## Applies to

Any future Expo SDK upgrade in `mobile/` (re-check `@expo/vector-icons`
status, expo-blur Android behavior, and the nativewind/reanimated interaction
each time — none of these are settled facts, they're SDK-57-specific).
Also applies whenever adding a dependency that needs a native
config-plugin entry (fonts, icon sets) — those require a dev build, not
Expo Go, so a decision to add one is also implicitly a decision to require
dev builds project-wide.

## Links

- [[ADR-002]]
- Stage 1 (foundation: tokens, fonts, icons, assets, responsive hooks) is
  done. Stages 2–4 (primitives, composite components, screens/routing) not
  yet started as of this entry.
