---
type: reference
app: mobile
tags: [reference, mobile]
---

# Mobile

Expo SDK 57, expo-router, React Native 0.86.3, React 19.2.3, NativeWind v5 (preview), TypeScript 6.

**Source of truth:** `.claude/MOBILE.md` and the `expo-react-native` skill. Stack facts belong there.

**Before writing Expo code, read https://docs.expo.dev/versions/v57.0.0/** — the SDK changes substantially between versions and remembered patterns are often wrong.

```bash
cd mobile && npx expo start
```

## Shape

- Routes at `src/app/`, expo-router file-based, typed routes enabled
- Styling is `className` via NativeWind v5 — no `StyleSheet.create` in new code
- Version control is the repo-root git repository, shared with `web/` and `backend/`

## Decisions

```dataview
LIST FROM #decision WHERE contains(apps, "mobile")
```

## Notes

-
