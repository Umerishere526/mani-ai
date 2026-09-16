---
name: expo-react-native
description: React Native and Expo SDK 57 standards for the mobile/ app — expo-router navigation, NativeWind v5 styling, component patterns, lists and performance, platform differences, Reanimated, and the SDK 57 APIs that replaced older ones. Use when writing or reviewing anything under mobile/, adding a screen or route, styling a component, building lists, handling navigation or gestures, or when the user mentions React Native, Expo, expo-router, NativeWind, Reanimated, iOS, or Android.
---

# React Native & Expo SDK 57

Scope: the `mobile/` app — Expo SDK 57, React Native 0.86.3, React 19.2.3, expo-router, NativeWind v5, TypeScript 6.

## Read the versioned docs first

**Expo changes substantially between SDKs.** Before writing code against any Expo API, read the exact versioned page at:

**https://docs.expo.dev/versions/v57.0.0/**

Do not rely on remembered patterns from older SDKs, and do not copy snippets from blog posts or Stack Overflow answers without checking them against v57 — module APIs, import paths, and config plugin options all shift between releases. If you cannot verify an API against the v57 docs, say so rather than guessing.

Requires Node 22.13+ (this machine runs v24).

## Project layout

```
mobile/src/
├── app/                    # expo-router routes only
├── components/
│   ├── shared/             # generic, reusable UI primitives (Text, buttons, inputs, …)
│   └── <feature>/          # domain-specific composites (chat/, settings/, …), one folder
│                           # per feature area, each with its own barrel — siblings of shared/
├── hooks/                  # custom hooks, max 80 lines each
├── providers/              # React context providers (state + a useX hook to read it)
├── lib/utils/              # utility functions (cn() lives here)
├── types/                  # shared TypeScript types
└── dictionaries/           # user-facing strings (en.json, …)
```

Anything inside `src/app/` becomes a route. Shared code goes in the siblings above, imported via `@/*` (`@/lib/utils`, `@/components/shared/button`).

A context provider (state + a `useX()` hook to read it, e.g. a drawer-open/closed provider) belongs in `providers/`, not `hooks/` or `components/shared/` — it's neither pure hook logic (the 80-line hook cap doesn't fit a component that renders `<Context.Provider>`) nor rendered UI on its own.

`components/shared/` is for primitives with no domain knowledge — a component doesn't care whether it's used in chat or settings. Once a cluster of components only makes sense together for one feature area (a chat drawer's nav section, thread list, and profile footer; a settings row and section), give that feature its own top-level folder under `components/` — `components/chat/`, `components/settings/` — as a sibling of `shared/`, each with its own `index.ts` barrel. Don't nest feature folders inside `shared/`; that folder is reserved for things any feature could reach for.

---

# The golden rules

These are project-wide rules, enforced in `mobile/` and `web/` alike. Code that violates them gets rejected.

## Golden Rule 1 — Minimize work on the JS thread

The web app's rule is "Server Components by default." React Native has no server rendering, so the equivalent discipline is **keeping the JS thread free**, because that is what determines whether the UI feels native.

- Run animations through `react-native-reanimated` (v4 installed) so they execute on the **UI thread**, not the JS thread. Never animate via `setState` in a loop.
- Never do heavy synchronous work during render. Parsing, sorting, or mapping large arrays inline drops frames in a way web apps don't exhibit.
- Virtualize long lists (`FlatList`/`SectionList`) instead of `.map()`-ing inside a `ScrollView`.
- React Compiler is enabled in `app.json`, so manual `useMemo`/`useCallback` wrapping is usually unnecessary — don't add memoization preemptively.
- Keep state as local as possible. State lifted to a root layout re-renders every screen beneath it.

## Golden Rule 2 — Small components, max 150 lines

**No component file exceeds 150 lines.** Past 100 lines, start extracting. Under 50 lines is ideal.

- Each component does one thing well. One component per file.
- Repeated UI → `src/components/shared/`
- Complex logic → a custom hook in `src/hooks/`, **max 80 lines each**
- Utility functions → `src/lib/utils/`

Screens grow fastest — a screen that is fetching, transforming, and rendering has three responsibilities and should be three units.

## Golden Rule 3 — Always use optional chaining

Never assume data exists. API responses, route params, and nested properties can be null or undefined.

```ts
// Correct
const name = user?.profile?.firstName ?? "Guest";
const avatar = user?.profile?.avatar?.url ?? "/default.png";
const count = data?.items?.length ?? 0;
const isAdmin = user?.roles?.includes("admin") ?? false;

// Wrong — crashes if null
const name = user.profile.firstName || "Guest";
const count = data.items.length;
```

**Use `??`, not `||`.** `||` treats `0`, `""`, and `false` as falsy, so `count || 10` returns `10` when count is `0` — wrong. `??` triggers only on null/undefined.

This matters more on mobile than web: an unhandled undefined crashes the app to the home screen rather than showing a broken component. `useLocalSearchParams()` values are a common source — always treat them as possibly undefined.

## Golden Rule 4 — Code reusability

**Before writing new code, search for an existing implementation.** If you write the same logic twice, extract it.

| Kind | Home |
|------|------|
| Shared components | `src/components/shared/` |
| Shared hooks | `src/hooks/` |
| Shared utilities | `src/lib/utils/` |
| Shared types | `src/types/` |

Check `web/` too — types and pure utilities describing the same backend data often belong in both, and divergent copies cause bugs.

## Golden Rule 5 — Always update dictionary files

**Never hardcode user-facing strings in components.** All visible text comes from `src/dictionaries/`.

- Adding or changing text → update **all** language files (`en.json` and every other language).
- Removing a feature → remove its dictionary entries.
- Renaming → update the keys and every reference.

Applies to accessibility strings too — `accessibilityLabel`, `accessibilityHint`, and any text passed to `Alert`.

---

## APIs that replaced older ones

Reaching for the old name is the most common SDK 57 mistake:

| Use | Not |
|-----|-----|
| `expo-audio` | `expo-av` (audio) |
| `expo-video` | `expo-av` (video) |
| `expo-file-system` | `expo-file-system/legacy` |
| `expo-image` | React Native's `Image` |
| `expo-router` navigation | bare React Navigation setup |

`expo-file-system` ships both the current API (`from "expo-file-system"`) and the old one (`from "expo-file-system/legacy"`). Use the current one in new code; the legacy path exists only for migration.

## Navigation — expo-router

File-based routing. A file in `src/app/` **is** a route.

- Routes live in `src/app/`. Root layout is `src/app/_layout.tsx`.
- `typedRoutes` is enabled in `app.json`, so route strings are type-checked. Let it catch your typos — don't cast to `any` to silence it.
- Navigate declaratively with `<Link href="/profile">` where possible; use `router.push()` / `router.replace()` for imperative cases.
- `router.push` adds to the stack; `router.replace` swaps the current entry. Use `replace` after login so back doesn't return to the auth screen.
- Layout files define shared chrome via `<Stack>`, `<Tabs>`, or `<Drawer>`. Configure screens with `<Stack.Screen options={{...}} />`.
- Dynamic segments are `[id].tsx`, read with `useLocalSearchParams()`. Groups are `(folder)` and don't appear in the URL.
- Prefer `useLocalSearchParams` over `useGlobalSearchParams` — global re-renders on any route change.

## Styling — NativeWind v5

Use `className` with Tailwind utilities. Do not write `StyleSheet.create` for new components.

```tsx
<View className="flex-1 items-center justify-center bg-white dark:bg-black">
  <Text className="text-3xl font-bold text-amber-700">Home</Text>
</View>
```

- NativeWind is on a **preview** release (`^5.0.0-preview.4`). Read v5 documentation specifically — v4 material is wrong in places, and expect occasional churn on upgrade.
- Styling is wired through `metro.config.js` (`withNativewind`) and `src/global.css`, which `src/app/_layout.tsx` imports. That import is load-bearing — keep it.
- `nativewind-env.d.ts` is generated. Never edit it by hand.
- Not every web utility maps to native. Layout, spacing, color, and typography work; anything web-specific (grid, float, most pseudo-selectors) does not. Check before assuming.
- Use `dark:` variants for dark mode — `app.json` sets `userInterfaceStyle: "automatic"`, so the system theme drives it.
- Use `cn()` from `@/lib/utils` for conditional classes, exactly as web does:
  ```tsx
  <Pressable className={cn("rounded-lg p-4", isActive && "bg-amber-600", className)} />
  ```
- Mobile-first is the default here — write base classes, then add `sm:`/`md:` only if the app targets tablets or web.
- Support dark mode with `dark:` variants; `app.json` sets `userInterfaceStyle: "automatic"`.
- Drop to `style={{}}` only for genuinely dynamic values (an animated height, a measured offset) or Reanimated's `useAnimatedStyle`. Mixing both on one element is fine when the dynamic part can't be a class.

## Component standards

- **Named exports everywhere.** The one exception is route files in `src/app/` — expo-router requires a default export from `page`-equivalent files and layouts.
- **Explicit props interface — never `any`.**
- Destructure props in the function signature.
- `index.ts` barrel files for component folders.
- One component per file.
- `cn()` for conditional classes.
- Accept an optional `className?: string` prop on shared components so callers can extend styling without wrapper views.

```tsx
interface UserCardProps {
  name: string;
  avatarUrl?: string | null;
  className?: string;
}

export function UserCard({ name, avatarUrl, className }: UserCardProps) {
  return (
    <View className={cn("flex-row items-center gap-3 p-4", className)}>
      <Image
        source={avatarUrl ?? require("@/assets/default.png")}
        accessibilityLabel={`${name} avatar`}
        className="h-10 w-10 rounded-full"
      />
      <Text className="text-lg font-medium">{name}</Text>
    </View>
  );
}
```

- Every screen is a default-exported component in its route file. Shared components go outside `src/app/` so they aren't mistaken for routes — `src/components/shared/` is the home.
- Use `@/*` path aliases (`@/components/shared/button`) instead of `../../` chains.
- `<Text>` is required for all text. A bare string inside `<View>` crashes at runtime — unlike web, React Native has no implicit text node.
- `<View>` does not scroll. Use `<ScrollView>` for short content, a list component for long content.
- Wrap screens in `SafeAreaView` from `react-native-safe-area-context` (installed), or use its `useSafeAreaInsets` hook — notches and home indicators will otherwise clip content.
- Prefer `<Pressable>` over the older `TouchableOpacity`/`TouchableHighlight` for new touchables.
- React Compiler is enabled in `app.json`, so manual `useMemo`/`useCallback` wrapping is usually unnecessary. Don't add memoization preemptively.

## Lists and performance

- **Never** render a long list by `.map()`-ing inside a `<ScrollView>` — it mounts every row at once. Use `<FlatList>` (or `<SectionList>` for grouped data), which virtualizes.
- Always give `keyExtractor` a stable unique id. Array index as key breaks reordering and item identity.
- Keep `renderItem` components small and defined outside the parent render where practical.
- Use `expo-image` rather than RN's `Image` — it handles caching and transitions properly, and supports `writeToCacheAsync`/`readFromCacheAsync` in SDK 57.
- Run animations through `react-native-reanimated` (v4 installed) so they execute on the UI thread rather than the JS thread. `react-native-worklets` is its required peer — do not remove it.
- Avoid heavy synchronous work in render; it blocks the JS thread and drops frames in a way web apps don't exhibit.

## Data fetching

- **Never call external APIs directly from the app — always route through the FastAPI backend** (`backend/`). Same rule as web: the backend owns third-party credentials and shapes responses.
- There is no server rendering, so all fetching is client-side. Use SWR or React Query rather than bare `useEffect` + `fetch` — you get caching, retries, and request dedup for free.
- Never put an API base URL or key in the source. Use `EXPO_PUBLIC_*` env vars for non-secret config, and remember **anything `EXPO_PUBLIC_*` ships in the bundle** — secrets belong on the backend only.
- Always handle the three states: loading, error, empty. On mobile a spinner that never resolves is indistinguishable from a hang.
- Assume offline. Network calls fail more often than on web — surface a retry rather than an empty screen.

## Accessibility

The mobile counterpart to web's SEO rules — different mechanism, same obligation.

- Every interactive element needs an `accessibilityLabel`; add `accessibilityHint` when the outcome isn't obvious from the label.
- Set `accessibilityRole` (`"button"`, `"link"`, `"header"`, …) on custom touchables.
- Touch targets at least 44×44pt. Padding counts; a 20pt icon needs padding around it.
- Never convey state by color alone — pair it with text or an icon.
- Label images meaningfully, or mark decorative ones `accessibilityElementsHidden`.
- All accessibility strings come from `src/dictionaries/`, per Golden Rule 5.

## Platform differences

- Branch with `Platform.OS === "ios"` / `"android"`, or `Platform.select({ ios: ..., android: ... })`.
- Platform-specific files work by extension: `button.ios.tsx`, `button.android.tsx`, `button.web.tsx`. Metro picks the right one.
- `app.json` targets all three — `web.output` is `"static"`, so anything native-only must be guarded or given a `.web` variant.
- `expo-glass-effect` is iOS-only. Guard its use or provide an Android fallback.
- Test both simulators before calling a UI change done. Shadows, fonts, and safe areas diverge noticeably.

## Prefer installed modules

Before adding a dependency, check whether an installed Expo module already covers it: `expo-image`, `expo-font`, `expo-symbols`, `expo-glass-effect`, `expo-web-browser`, `expo-linking`, `expo-constants`, `expo-device`, `expo-splash-screen`, `expo-status-bar`, `expo-system-ui`, `expo-file-system`, `expo-asset`, `expo-keep-awake`.

Adding a native dependency is an architectural decision — discuss it with muhammad first, per the root CLAUDE.md. Many require a config plugin entry in `app.json` and a rebuild, not just an install.

## Gotchas

- `npm run reset-project` is listed in `package.json` but broken — `scripts/reset-project.js` does not exist. Don't run it expecting it to work.
- `overrides.lightningcss` (pinned `1.30.1`) and the `allowScripts` block in `package.json` exist to make installs succeed. Don't strip them.
- After changing `app.json` plugins or adding a native module, a JS reload is not enough — the native project needs rebuilding.
- TypeScript is `~6.0.3` here, ahead of web's v5.

## Checks

After changing anything under `mobile/`:

```bash
cd mobile
npm run lint
npx tsc --noEmit
```

The project's PostToolUse hook runs both automatically on edit.
