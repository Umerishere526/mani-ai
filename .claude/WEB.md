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
- Entry points: `app/layout.tsx` (root layout) and the route folders `app/admin/` and `app/auth/`. There is no `app/page.tsx`: `/` redirects to `/auth/login` from `next.config.ts`.
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
- `next.config.ts` holds the one redirect from `/` to `/auth/login`; further config goes in the `nextConfig` object.

## Backend calls and auth

The FastAPI backend is a separate process (see [BACKEND.md](BACKEND.md)) at `http://127.0.0.1:8000` in development. The web admin calls it only from the server: `lib/api/admin-fetch.ts` sends the signed-in admin's bearer token to `/v1/admin/*`, and every call checks the admin session first. Never hardcode the host in a component, and never call the backend or Supabase from the browser.

Server-only environment variables (no `NEXT_PUBLIC_` prefix, so they never reach the browser bundle), in `web/.env.local` for development:

- `MANI_API_URL` — the FastAPI backend's base URL (`lib/api/admin-fetch.ts`).
- `SUPABASE_URL` and `SUPABASE_ANON_KEY` — the project's Auth, for the password sign-in and token refresh (`lib/auth/gotrue.ts`).

Auth: sign-in posts to a server action that exchanges email and password with Supabase Auth over fetch and keeps the tokens in httpOnly cookies (`lib/auth/session-cookies.ts`). `proxy.ts` (Next.js 16's middleware, matcher `/admin/:path*`) is the optimistic check: it sends a visitor with no session to sign-in and refreshes an expiring access token. `lib/auth/require-admin.ts` is the real check, on every read: it verifies the token with the auth server and requires `app_metadata.admin_role` to be `"admin"`, the claim the backend checks.
