---
type: journal
date: 2026-09-16
apps: [mobile]
tags: [journal, mobile, nativewind, gotcha, tailwind-content-scanning]
---

# Two NativeWind gotchas: `active:` on a child View breaks Pressable's onPress, and dynamic class strings never generate CSS

## What happened

muhammad added `CardGradient` (an absolute-fill `LinearGradient`) as the first child inside `ChatDrawerNavSection`'s `Pressable` nav items, then asked for the `active:bg-secondary-500/10` highlight — previously a className directly on the `Pressable` — to come back. Since `CardGradient` now paints on top of anything the `Pressable`'s own background would show, an `active:bg-*` class on the `Pressable` itself would be invisible (children always paint over a parent's own background). My first fix moved the class onto a plain child `View` positioned after `CardGradient`:

```tsx
<Pressable className="... overflow-hidden" onPress={...}>
  <CardGradient />
  <View className="absolute inset-0 active:bg-secondary-500/10" />
  ...
</Pressable>
```

This does not work, and it's worse than a no-op: **it breaks the `Pressable`'s `onPress` from firing at all.**

## Root cause

Verified in `node_modules/react-native-css` source (this app's NativeWind v5 CSS engine) rather than assumed:

- `native/react/interaction.js` — `getInteractionHandler` sets `activeFamily(weakKey).set(true/false)` on `onPressIn`/`onPressOut`, keyed by a per-element `weakKey`.
- `native/react/rules.js` (`updateRules`) — any element whose className includes an active/hover/focus rule gets registered via `activeFamily(state.ruleEffectGetter)`, which is **per-instance**, not inherited from an ancestor. The comment in `native/conditions/index.js` is explicit: evaluating the `active` pseudo-class "modifies a global value that we use to determine if the component should be a pressable."

In other words: giving a plain child `View` an `active:` class makes react-native-css treat **that View itself** as a second, independent pressable target needing its own press handlers — it does not read the parent `Pressable`'s state. Confirmed against a matching upstream report rather than trusting the source-reading alone: [nativewind/react-native-css#262](https://github.com/nativewind/react-native-css/issues/262) and [nativewind/nativewind#1583](https://github.com/nativewind/nativewind/issues/1583) — "Pressable does not trigger when child View uses pseudo classes (active:/hover:)." Tapping the child intercepts the gesture and the outer `Pressable`'s `onPress` never fires.

## Fix

NativeWind v5's documented mechanism for this exact case is `group`/`group-active` ([nativewind.dev/v5/core-concepts/states](https://www.nativewind.dev/v5/core-concepts/states)): name the group on the parent, reference it on the descendant.

```tsx
<Pressable className="group/nav-item ... overflow-hidden" onPress={...}>
  <CardGradient />
  <View className="absolute inset-0 group-active/nav-item:bg-secondary-500/10" />
  ...
</Pressable>
```

`group/nav-item` on the `Pressable` registers it as the named interaction source; `group-active/nav-item:` on the child subscribes to that specific group's active state instead of trying to become its own pressable. Applied in `components/chat/chat-drawer-nav-section.tsx`.

## Checked whether this bug exists elsewhere in the app

Grepped every `CardGradient` usage (`home-exercise-card.tsx`, `chat-drawer-nav-section.tsx`, `conversation-style-option.tsx`):

- `home-exercise-card.tsx` uses `active:opacity-90` **directly on the `Pressable`**, not a nested child — safe, unaffected. Opacity on the `Pressable` itself composites its entire subtree (including `CardGradient`) via normal RN opacity, no pseudo-class-on-a-descendant trick needed.
- `conversation-style-option.tsx` (see [[conversation-style-picker-implementation]]) has no `active:` class at all — it animates press feedback via Reanimated's `onPressIn`/`onPressOut` + `useSharedValue`, a different mechanism entirely, also unaffected.
- Only `chat-drawer-nav-section.tsx` had the broken pattern, and only because it was mid-edit when the bug was caught.

## Generalizes

**Standing rule for this codebase: `active:`/`hover:`/`focus:` classes only go directly on the exact `Pressable`/touchable that owns the gesture.** The moment a gradient, overlay, or any other element needs to sit on top of that `Pressable`'s own background *and* show a pressed-state highlight, reach for `group/{name}` on the `Pressable` and `group-active/{name}:` on the descendant — never a bare `active:` on a non-Pressable descendant, even though it type-checks and lints clean (this is a runtime-only failure; neither `tsc` nor `expo lint` catches it). Worth checking any future `CardGradient`-or-similar-overlay addition against this before assuming a simple class move is safe.

This is the same category of risk already logged in [[mani-mobile-ui-port]] — a `className` that compiles fine but doesn't do what the visual result needs, discoverable only by reading the actual style-resolution source or hitting a real device, not by `tsc`/lint. No simulator was available to reproduce the broken-tap symptom directly in this environment; the fix was derived from reading `react-native-css`'s source and cross-checking it against the matching upstream GitHub issues, not from an observed crash.

## Follow-up: extracting DrawerActionRow almost reintroduced a different, worse bug

Once the same `CardGradient` + `group`/`group-active` pattern existed three times
(`ChatDrawerNavSection`, the new-chat row in `ChatDrawer`, and `ChatDrawerThreadList`'s
per-thread rows), muhammad asked to extract it into a shared component — correct call
per Golden Rule 4. First draft of `DrawerActionRow` took a `groupName: string` prop and
built the classNames via template literals:

```tsx
className={cn(`group/${groupName} flex-row items-center ...`, className)}
...
<View className={`absolute inset-0 group-active/${groupName}:bg-secondary-500/10`} />
```

Reasoning at the time: thread rows are rendered in a `FlatList`, so each row's group
name should probably be unique per thread (`thread-${item.thread.id}`) to be safe
against possible cross-talk between list items if group scoping were ever
name-keyed rather than instance-keyed.

**This would have silently broken all three usages.** `mobile/metro.config.js` wraps
the Metro config in `withNativewind`, which drives Tailwind v4's own source-scanning
content detection — Tailwind (confirmed via its docs) "scans your source files as
plain text" and cannot see through string interpolation. A class name that never
appears as a complete literal string anywhere in source — which `` `group/${groupName}` ``
and `` `group-active/${groupName}:...` `` never do, since `groupName` is a runtime
value — never gets its CSS generated. The utility silently does nothing; no build
error, no lint warning, `tsc` stays green (it's a string, not a type mismatch).
This is the second time this session a `className`-based fix looked syntactically
fine and would have failed only at runtime — same risk class as the `active:`-on-
nested-View bug above, but this one wouldn't even use the wrong mechanism, it just
wouldn't exist as generated CSS at all.

**Fix**: dropped `groupName` as a prop entirely. `DrawerActionRow` hardcodes one
literal group name, `group/drawer-row`, shared across every instance (nav items,
new-chat, and every thread row in the FlatList). This is actually the standard,
correct Tailwind/NativeWind pattern — `group` scoping is nearest-ancestor by tree
position (confirmed earlier in this note via `react-native-css`'s per-element
`ruleEffectGetter`/`ContainerContext` keying, not a name-string global registry),
so reusing the identical literal name across many sibling Pressables in a list is
exactly how `group`/`group-active` is meant to be used, not a corner case needing
a unique name per row.

**Generalizes further than the earlier finding in this note**: it's not just
`active:`/`hover:`/`focus:` classes that must go directly on a literal, static
class string — *any* Tailwind/NativeWind class built via template-literal
interpolation of a runtime value is at risk of silently generating no CSS, in this
specific Tailwind-v4-content-scanning setup. If a class needs to vary by a runtime
prop, the safe pattern is a lookup map of complete literal class strings (Tailwind's
own documented recommendation), never string concatenation — same shape as `cn()`
already handles conditional classes correctly (`cn('base', isActive && 'other-full-class')`
works because both `'base'` and `'other-full-class'` are complete literals Tailwind's
scanner can see, even though which one applies is decided at runtime).

## Links

- [[conversation-style-picker-implementation]] — the CardGradient usage that prompted checking this
- [[mani-mobile-ui-port]] — prior NativeWind/className-on-non-View gotchas (vector icons, react-native-svg) in the same family of risk
