---
name: nextjs-best-practices
description: Project rules and Next.js 16 App Router standards for the web/ app — the five golden rules (server-side first, 150-line components, optional chaining, reusability, dictionary files), plus data fetching, caching, Server Actions, SEO, performance, styling with cn(), and component standards. Use when writing or reviewing anything under web/, adding a route, page, or component, fetching data, handling forms or mutations, writing metadata or SEO, styling with Tailwind, or when the user mentions Next.js, App Router, RSC, server components, server actions, or revalidation.
---

# Next.js — project rules & standards

Scope: the `web/` app — Next.js 16.3.4, React 19.2.8, App Router, Tailwind v4, TypeScript.

**These are enforced rules, not suggestions.** Code that violates them gets rejected.

## Project layout

Routes live in `web/app/`. Shared code lives in siblings of `app/`, never inside it — a folder inside `app/` becomes a route segment.

```
web/
├── app/                    # routes only
├── components/shared/      # reusable UI
├── hooks/                  # custom hooks, max 80 lines each
├── lib/utils/              # utility functions (cn() lives here)
├── types/                  # shared TypeScript types
└── dictionaries/           # user-facing strings (en.json, …)
```

Import via the `@/*` alias: `@/lib/utils`, `@/components/shared/button`.

---

# The five golden rules

## Golden Rule 1 — Server-side first

Server-side rendering is the goal, for SEO and performance. **Every component is a Server Component by default.**

Add `"use client"` only when the component genuinely needs: `useState`/`useReducer`, `useEffect`, event handlers (`onClick`, `onChange`), or browser APIs (`localStorage`, `window`).

**If a page is 90% static with one interactive widget, keep the page a Server Component and extract only that widget into a tiny Client Component. Never mark an entire page `"use client"` because of one button.**

| Server Component (default) | Client Component (`"use client"`) |
|---|---|
| Displaying data | Forms with input state |
| Layouts, navigation (`next/link`) | Buttons with `onClick` |
| Images (`next/image`) | Dropdowns, modals, tooltips, accordions |
| SEO content | Animations |
| Fetching data, passing to children | Browser APIs (`localStorage`, `window`) |
| Anything without browser interaction | Client-only libraries (charts, maps, editors) |

Mechanics that follow from this:

- Push `"use client"` **down** to the leaf that needs it. Marking a layout or page client drags its whole subtree into the bundle.
- A Server Component may render a Client Component. A Client Component may **not** import a Server Component — pass it as `children` or a prop:
  ```tsx
  // app/page.tsx (server)
  <InteractiveShell><ServerRenderedContent /></InteractiveShell>
  ```
- Never pass non-serializable values (functions, class instances) across the server→client boundary.
- Secrets are safe in Server Components. Once a module is imported by a client component, assume its contents ship to the browser.

## Golden Rule 2 — Small components, max 150 lines

**No component file exceeds 150 lines.** Past 100 lines, start extracting. Under 50 lines is ideal.

- Each component does one thing well. One component per file.
- Repeated UI → `components/shared/`
- Complex logic → a custom hook in `hooks/`, **max 80 lines each**
- Utility functions → `lib/utils/`

## Golden Rule 3 — Always use optional chaining

Never assume data exists. API responses, user objects, and nested properties can be null or undefined.

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

## Golden Rule 4 — Code reusability

**Before writing new code, search for an existing implementation.** If you write the same logic twice, extract it.

| Kind | Home |
|------|------|
| Shared components | `components/shared/` |
| Shared hooks | `hooks/` |
| Shared utilities | `lib/utils/` |
| Shared types | `types/` |

## Golden Rule 5 — Always update dictionary files

**Never hardcode user-facing strings in components.** All visible text comes from `dictionaries/`.

- Adding or changing text → update **all** language files (`en.json` and every other language).
- Removing a feature → remove its dictionary entries.
- Renaming → update the keys and every reference.

Hardcoded user-facing strings get the PR rejected.

---

# Frontend standards

## Data fetching

- In Server Components, fetch directly with `async`/`await`.
- Static pages: fetch at build time, no `revalidate`.
- Periodically-updating content: ISR — `{ next: { revalidate: 3600 } }`.
- Highly dynamic data: `{ cache: 'no-store' }`.
- In Client Components (only when needed): SWR or React Query.
- **Never call external APIs directly from the frontend — always route through the FastAPI backend** (`backend/`, `http://127.0.0.1:8000` in dev). See `.claude/BACKEND.md`.
- Loading states via `loading.tsx` or `<Suspense>`; errors via `error.tsx`.
- Fetch in parallel when requests are independent — sequential `await`s create waterfalls:
  ```tsx
  const [user, posts] = await Promise.all([getUser(id), getPosts(id)]);
  ```

## Caching and revalidation

Next.js 16 does not cache `fetch` by default — opt in explicitly.

- `{ cache: "force-cache" }` to cache; `{ next: { revalidate: 60 } }` for time-based.
- Tag data and invalidate precisely after mutations:
  ```tsx
  fetch(url, { next: { tags: ["posts"] } });
  revalidateTag("posts"); // after the mutation
  ```
- `revalidatePath("/posts")` when a whole route's data is stale.
- Reading `cookies()`, `headers()`, or `searchParams` makes a route dynamic and silently disables static rendering.
- In Next.js 16 these are **async** — always `await` `cookies()`, `headers()`, `params`, `searchParams`.

## SEO — every page must have

- **Unique title, 50–60 chars** and **meta description, 150–160 chars** via the Metadata API (`metadata` export, or `generateMetadata` for dynamic routes). Never hand-write `<title>`/`<meta>`.
- **Canonical URL** to prevent duplicate content (`alternates.canonical`).
- **Open Graph tags** for social sharing.
- **One H1 per page**, then H2s, H3s — never skip levels.
- **Structured data (JSON-LD)** where applicable: Article for blog posts, FAQ for FAQ pages, Organization for about.
- **Alt text on every image.**
- **Semantic HTML** — `main`, `article`, `section`, `nav`, `header`, `footer`, not generic divs.

## Performance

- Server Components by default — zero JS shipped.
- Dynamic-import heavy components with `next/dynamic`, `ssr: false` for client-only libraries.
- `<Suspense>` boundaries for progressive loading.
- `priority` on above-the-fold images (LCP); `placeholder="blur"` to prevent layout shift.
- **Never import entire libraries.** `import { format } from "date-fns"`, not `import * as dateFns`.
- Use `next/image` for images, `next/link` for links, `next/font` for fonts, `next/script` for third-party scripts.

## Styling

- **Tailwind utility classes only** — no custom CSS unless genuinely unavoidable.
- Use `cn()` from `@/lib/utils` for conditional classes.
- **Mobile-first**: base classes for mobile, then `sm:`, `md:`, `lg:`.
- Dark mode via the `dark:` prefix.
- **Never use inline `style={{}}`.**

Tailwind v4 here is CSS-first: no `tailwind.config.js`, tokens go in the `@theme inline { … }` block in `app/globals.css`, PostCSS wired via `@tailwindcss/postcss`.

## Component standards

- **Named exports everywhere.** The only exceptions are `page.tsx`, `layout.tsx`, and other special files Next.js requires to default-export.
- **Explicit props interface — never `any`.**
- Destructure props in the function signature.
- `index.ts` barrel files for component folders.
- One component per file.
- `cn()` for conditional Tailwind classes.
- Every image: `next/image` with `alt`, `width`, `height`, `sizes`.
- Every link: `next/link`.

```tsx
interface UserCardProps {
  name: string;
  avatarUrl?: string | null;
  className?: string;
}

export function UserCard({ name, avatarUrl, className }: UserCardProps) {
  return (
    <article className={cn("flex items-center gap-3 p-4", className)}>
      <Image
        src={avatarUrl ?? "/default.png"}
        alt={`${name} avatar`}
        width={40}
        height={40}
        sizes="40px"
        className="rounded-full"
      />
      <h2 className="text-lg font-medium">{name}</h2>
    </article>
  );
}
```

## Routing

| File | Purpose |
|------|---------|
| `page.tsx` | Route UI |
| `layout.tsx` | Shared shell; preserves state across navigation |
| `loading.tsx` | Suspense fallback |
| `error.tsx` | Error boundary; must be a Client Component |
| `not-found.tsx` | 404, triggered by `notFound()` |
| `route.ts` | API endpoint (cannot coexist with `page.tsx` in a segment) |

Group routes without affecting the URL using `(folders)`.

## Server Actions

- Mark with `"use server"`. Use for mutations rather than hand-rolled API routes.
- **Always validate input inside the action** — it's a public HTTP endpoint; client validation guarantees nothing.
- **Always re-check authorization inside the action.** Never trust a client-supplied ID.
- `revalidateTag`/`revalidatePath` after a successful mutation.
- `useActionState` for pending and error states.

## Common failure modes

- **Hydration mismatch** — `Date.now()`, `Math.random()`, or `typeof window` during render. Move to `useEffect`.
- **"useState only works in Client Components"** — missing `"use client"`.
- **Stale UI after mutation** — missing `revalidateTag`/`revalidatePath`.
- **Unexpectedly dynamic route** — something read `cookies()`/`headers()`/`searchParams` deeper in the tree.
- **Secret leaked to the bundle** — a module holding a secret got imported by a client component. Only `NEXT_PUBLIC_*` is meant to be public.

## Checks

```bash
cd web
npm run lint
npx tsc --noEmit
```

The PostToolUse hook runs both automatically on edit.
