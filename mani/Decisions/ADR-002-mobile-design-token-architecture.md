---
type: decision
status: accepted
date: 2026-09-14
apps: [mobile]
tags: [decision, mobile, design-system, nativewind]
---

# ADR-002: Mobile design tokens live in CSS `@theme`, mirrored in TS for non-className cases

**Status:** accepted
**Affects:** mobile

## Context

Porting the UI/design system from the `mani-app` reference project (`apps/mani-app/packages/design-tokens`, a separate workspace package) into `mobile/`, which uses NativeWind v5 (CSS-first Tailwind v4) rather than the reference project's plain `StyleSheet.create` + TS token imports.

The reference tokens are TS objects: `colors.primary[900]`, `spacing[4]`, `radii.lg`, consumed as `import { colors } from '@mani/design-tokens'`. NativeWind resolves `className` utilities from Tailwind theme tokens declared in CSS, not from arbitrary TS objects — there's no way to point NativeWind's compiler at a `.ts` file as its source of truth.

Some values genuinely can't be expressed as a `className` regardless of styling approach: `expo-linear-gradient`'s `colors` prop, `react-native-svg` `stroke`/`fill`, and Reanimated `interpolateColor` outputs all take raw color values, not classes.

## Options considered

### Option A — CSS `@theme` only, components read colors via className
- Pros: one source of truth, fully matches the `expo-react-native` skill's className-first rule, no drift possible.
- Cons: nothing to import for the genuinely-dynamic cases (gradients, SVG, animated interpolation) — would need `useColorScheme`-style string introspection or duplicate literals inline.

### Option B — TS tokens only, keep `StyleSheet.create`
- Pros: lowest-effort port, byte-identical to the reference project.
- Cons: abandons NativeWind entirely, contradicts the `expo-react-native` skill's explicit "do not write StyleSheet.create for new components" rule.

### Option C — CSS `@theme` tokens (for className) + a TS mirror (for non-className cases)
- Pros: className stays the default per the skill; the ~5 components needing a raw color value (gradients, SVG, animated colors) have a typed source instead of inline hex literals.
- Cons: two files describe the same palette. Nothing enforces they stay in sync — a color change made in one and not the other silently diverges.

## Decision

Option C. `mobile/src/global.css` carries the full palette in an `@theme` block (`--color-primary-900`, `--color-secondary-500`, etc. — see the block for the full list), generating `bg-primary-900` / `text-secondary-500` / etc. utilities. `mobile/src/lib/tokens.ts` exports the identical values as a plain `colors` object, documented in its header as a hand-maintained mirror, for use only where an API takes a raw color value instead of a class.

Spacing was **not** re-declared: the reference project's 4px-based spacing scale (`spacing[4]` = 16px) is numerically identical to Tailwind's built-in default scale (`p-4` = 16px), so overriding `--spacing-*` would just reimplement what Tailwind already provides for free.

**Font weights are declared as separate `--font-*` family tokens, not via `--font-weight-*`.** Each Montserrat weight (Regular/Medium/SemiBold/Bold) is a discrete embedded font file/family, not a single variable font — so Tailwind's stock `font-semibold`/`font-bold` utilities (which only ever emit CSS `font-weight`) do nothing on native, where weight selection means swapping `fontFamily`. `global.css` instead declares `--font-sans`, `--font-sans-medium`, `--font-sans-semibold`, `--font-sans-bold`, each mapped to the exact PostScript name baked into the corresponding ttf (verified by parsing each file's `name` table, not assumed from the filename). Components use `font-sans-semibold`, never `font-semibold`.

## Consequences

- Adding shared components is straightforward: `className="bg-primary-900"` works immediately, matching the skill.
- Any future palette change must be made in **both** `global.css` and `tokens.ts` by hand. There is no lint rule or codegen catching drift yet — if this becomes a real pain point (it will, eventually), the fix is a small script that generates one from the other, not a person remembering.
- The single-theme (dark-green) decision means no `dark:` variant tokens exist yet; `app.json` sets `userInterfaceStyle: "dark"` so the system light/dark toggle can't fight the fixed palette. See [[mani-mobile-ui-port]] for the broader porting decisions this sits inside.

## Links

- Related: [[mani-mobile-ui-port]]
