# web — Next.js

Next.js 16.3.4 (App Router), React 19.2.8, Tailwind CSS v4, TypeScript 5. Always `cd web` first; it has its own `node_modules`.

## Commands

```bash
cd web
npm install
npm run dev      # dev server on :3000
npm run build
npm run start    # serve the production build
npm run lint     # eslint
```

## Layout

- App Router lives at `app/` — **not** `src/app/`. Mobile uses `src/`; the two apps differ deliberately, don't "fix" one to match the other.
- Entry points: `app/layout.tsx` (root layout), `app/page.tsx`.
- Global styles: `app/globals.css`. Static assets: `public/`.
- Path alias: `@/*` → `./*` (repo root of `web/`, not a `src` dir).

Shared code lives in siblings of `app/`, never inside it — a folder inside `app/` becomes a route segment:

```
web/
├── app/                    # routes only
├── components/shared/      # reusable UI
├── hooks/                  # custom hooks, max 80 lines
├── lib/utils/              # cn() and other helpers
├── types/                  # shared types
└── dictionaries/           # user-facing strings
```

Project rules — server-first, 150-line components, optional chaining, reusability, dictionaries — are enforced via the `nextjs-best-practices` skill.

## Tailwind v4

Tailwind here is **CSS-first**. There is no `tailwind.config.js` and you should not create one.

- `app/globals.css` starts with `@import "tailwindcss";`
- Theme tokens are declared in an `@theme inline { ... }` block in that same file — add design tokens there, not in a JS config.
- PostCSS wiring is `@tailwindcss/postcss` in `postcss.config.mjs`.

## Conventions

- ESLint uses flat config (`eslint.config.mjs`) composing `eslint-config-next/core-web-vitals` and `/typescript`. `npm run lint` takes no path argument by default.
- Server Components are the default in the App Router. Add `"use client"` only when a component actually needs state, effects, or browser APIs.
- `next.config.ts` is currently empty scaffold — real config goes in the `nextConfig` object.

## Backend calls

The FastAPI backend is a separate process (see [BACKEND.md](BACKEND.md)) at `http://127.0.0.1:8000` in development. There is no proxy configured in `next.config.ts`, so either add a rewrite or use the absolute URL from an env var. Never hardcode the host in a component.
