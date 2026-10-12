---
type: journal
date: 2026-10-12
apps: [web, mobile, backend]
tags: [journal, cleanup, knip, tooling]
---

# What the dead-code scanners get wrong here

2026-10-12 cleanup audit. Things the tools flagged that are in use, so the next scan can skip
re-verifying them.

## knip

- **`mobile/metro.config.js`** reported as an unused file. Metro reads it; it wraps the config in
  `withNativewind`.
- **`@expo-google-fonts/montserrat`** reported as an unused dependency. `app.json` loads the font
  files by path from `node_modules`, which knip does not read.
- **`expo-updates`** reported as unlisted. Nothing references it; knip infers it from `app.json`.
- **`postcss`** in `web/` reported as unlisted. It arrives through `@tailwindcss/postcss`.
- **Dictionary keys knip does not check at all.** A leaf-key grep flags
  `admin.forms.categories.*` in `web/`, but those keys are read dynamically through
  `CATEGORY_LABELS[category]`.
- `@expo/ui`, `expo-glass-effect` and `expo-symbols` stay in `node_modules` after being removed
  from `mobile/package.json`. They are regular dependencies of `expo-router`, not something the
  app has to list.
- knip run through `npx` fails with `Cannot find package 'typescript'` from its own cache. Install
  `knip` and `typescript` together in a scratch folder and run that binary.

## Backend, by grep

- Every `routers/*` handler looks unreferenced. Decorators register them.
- `openrouter_allow_fallbacks` is read through `self` in a `Settings` property.
- `python-multipart` (for `UploadFile`) and `python-dotenv` (for pydantic-settings' `env_file`) are
  never imported, but both are required.

## What was actually dead

- `langchain` and `email-validator` were pinned in `requirements.txt` without being installed in
  `.venv`, and the suite passed. A pin the venv does not have is a strong sign it is dead.
  `pip show <name>` answers this faster than grepping.
- The integration tests skipped silently because Docker was down, and before that the local DB
  held migrations 018–026 from another branch. A green suite there would have meant nothing. See
  [[switching-branch-leaves-the-database-ahead-2026-10-09]].
- `nativewind-reanimated-spike.tsx` was removed. By then, `className` plus an animated `style` on
  the same component was used in eight places (message bubbles, typing indicator, chat drawer,
  secondary button, auth shell), so every chat screen exercises the check it was written for.
  See [[mani-mobile-ui-port]].
