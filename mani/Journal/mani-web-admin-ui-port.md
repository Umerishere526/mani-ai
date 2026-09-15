---
type: journal
date: 2026-09-15
apps: [web]
tags: [journal, web, design-system, port]
---

# Porting mani-app's admin dashboard UI into web/ (UI layer only, no API)

## What happened

Asked to move the UI layer, design system, theme, and types from a reference
project (`/Users/mac/Desktop/mani-app/apps/backend`) into this repo's `web/`
— UI/design-system only, no API layer, no scripts, no Supabase. Same brief
as the mobile port ([[mani-mobile-ui-port]]), applied to web.

**First correction of the session**: muhammad's instruction said to read
`apps/backend` expecting a Python API. It isn't — `apps/backend` is actually
a second **Next.js 16 app** (`@mani/backend`, port 3001) that bundles both a
tRPC API *and* a full admin dashboard UI (`/admin/*`: prompts, providers,
exercises, chat transcripts). There is no `apps/web` in the source at all.
Surfaced this immediately rather than guessing which folder "the web UI"
meant — confirmed "the admin dashboard" was correct before touching
anything.

Read the whole source admin surface first (~30 UI files, the
`@mani/design-tokens` package, `globals.css`, `components.json`) before
proposing a plan, same discipline as the mobile port. Found the UI's
data coupling is total: every page is an async Server Component starting
`await requireAdmin(); await listX()`, and every type traces back to
`ObjectToCamel<Database[...]>` off a generated Supabase types file. That's
the one thing a UI-only move can't dodge, so it became the first question
rather than an assumption.

## Decisions (asked, not assumed)

Two rounds of `AskUserQuestion` before writing code, since several answers
changed the actual code shape, not just cosmetics:

- **Data**: static placeholder files in `web/lib/`, mirroring mobile's
  `placeholder-exercises.ts` pattern — real UI rendered from fake rows, form
  submits are no-ops (`console.log`, not silent).
- **Tokens**: copied into `web/app/globals.css`'s `@theme inline` block, no
  shared package, no codegen — deliberately accepting some drift risk against
  mobile's copy rather than standing up a workspace, which CLAUDE.md
  explicitly rules out ("no workspace root").
- **Font**: Montserrat (matches mobile + the design-tokens package), not
  Outfit (what source's `globals.css` actually — inconsistently — loads).
  Source itself has this Montserrat/Outfit mismatch; flagged rather than
  silently picked one.
- **Types**: hand-written interfaces in `web/types/`, narrowed to what the
  UI actually renders (e.g. `AdminThread`/`AdminMessage` from the admin
  action return types, not the full chat-runtime `Thread`/`Message` schema
  with fields like `responseStyles` the admin UI never touches). No
  `types/supabase.ts`, no `ts-case-convert`.
- **Strings**: extracted to `dictionaries/en.json` *during* the port, not as
  a deferred sweep — every file lands dictionary-clean.
- **Styling — reversed mid-session**: I first proposed keeping source's
  hand-written `.btn`/`.card`/`.badge` CSS classes (fastest, highest source
  fidelity) with only inline `style={{}}` converted to Tailwind. muhammad
  caught that this contradicted the `nextjs-best-practices` skill's own
  "Tailwind utility classes only — no custom CSS unless genuinely
  unavoidable" / "Never use inline `style={{}}`" rules. Asked which to
  follow; the skill won. Wrote [[ADR-003]] since this is a real,
  muhammad-confirmed exception being made explicit, not a routine choice.

## Stage 1 — tokens, font, globals.css

Ported the full `@mani/design-tokens` palette (bg/text/border, primary +
secondary 9-step ramps, accent, error, success, radii, shadows) into
`@theme inline`, namespaced `mani-*` (`--color-mani-accent`, not
`--color-accent`) to avoid colliding with the Next.js scaffold's own
`--background`/`--foreground` tokens. Swapped `Geist`/`Geist_Mono` for
`Montserrat`/`JetBrains_Mono` via `next/font/google`.

Deliberately **not** ported: `spacing` (identical to Tailwind's stock 4px
scale — same finding as the mobile ADR), `transitions` (one-off duration
literals, covered by Tailwind's `duration-*` utilities), `radii.none`/`.full`
(Tailwind's `rounded-none`/`rounded-full` already match).

**Verification habit that paid off repeatedly this session**: `tsc --noEmit`
and even `next build` succeeding does NOT prove a Tailwind utility class
actually resolved to real CSS — Tailwind silently drops unparseable
utilities rather than erroring. Every stage, I planted a throwaway probe
component using the new classes, ran a real build, and grepped the compiled
`.next/static/chunks/*.css` for the literal expected CSS rule before
declaring anything done. This caught two real, silent bugs (below). Probes
were always deleted afterward, confirmed via `git status`/`git diff`.

## Stage 3 — shared primitives: a genuine bug caught by the probe habit

Ported `AdminNav`'s noise-texture sidebar background as a data-URI packed
into a Tailwind arbitrary value (`bg-[url('data:image/svg+xml,...')]`).
`tsc` was clean, `next build` said "Compiled successfully." **The compiled
CSS was still wrong** — Tailwind's arbitrary-value parser rewrites spaces to
underscores as an escaping convention, so the actual output had
`viewBox="0_0_400_400"` instead of `"0 0 400 400"`, a corrupted SVG that
would have rendered as nothing/broken in a real browser. Caught only because
I grepped `background-image:url(...)` out of the compiled chunk directly
instead of trusting the green build. Fixed by extracting the SVG to a real
asset (`public/textures/noise.svg`) referenced by URL — the general lesson:
**never pack a real asset (SVG, image) into a Tailwind arbitrary value
string; always use a real file + URL reference.**

Added `lucide-react` as a new dependency (confirmed with muhammad first,
pinned to source's `^0.555.0`) — required for the icon set `icons.ts`/
`AdminNav`/`BackLink` all depend on.

## Stage 4 — forms: a lint rule catching a design mistake, not a style nit

Added `react-hook-form`, `zod`, `@hookform/resolvers` (confirmed first,
pinned to source's versions) to preserve the real form-validation schemas
rather than rewriting validation from scratch.

Built `hooks/use-provider-models.ts` to replace `PromptForm`'s two real
`useEffect` fetches (`listProviders()` on mount, `fetch('/api/admin/models?
provider=X')` on provider change) with placeholder-data lookups — but
muhammad's instruction was to **keep the async-shaped state** (`loadingProviders`,
`loadingModels`, `modelsError`) so the loading/error UI branches stay
reachable rather than becoming permanently dead code. First draft routed the
now-synchronous placeholder reads through `useEffect` + `setState`, which
the React-Compiler-era `react-hooks/set-state-in-effect` lint rule correctly
flagged as an error, not a warning — **exact same rule class the mobile
port's Stage 4 already hit** (`useNotificationPreference`). The fix pattern
generalizes: when a "loading" delay stops being real (source's async call
replaced by synchronous local data), don't fake the effect — initialize
state directly via `useState(data)` and reserve `useEffect` only for a
genuine one-time side effect into something external (here: the parent
form's `setValue`). Routing sync data through async-shaped plumbing is a
smell the compiler-era lint now catches structurally, not just stylistically.

`ExerciseForm` (source) referenced CSS classes (`.form-group`, `.form-input`,
`.btn-secondary`, etc.) that **don't exist anywhere in source's own
`globals.css`** — dead references, rendering with unstyled browser defaults
in the original app. A real inconsistency in source, not something to
silently "fix" by inventing meaning; flagged it and mapped the evident
intent to the same Tailwind conventions used in the other two forms.

## Stage 5 — pages: the auth question, and reading past the fold

**Biggest architectural call of the session**: every source page opens with
`await requireAdmin()` (redirects to login/unauthorized) and
`getAdminPermissions()` (drives `canEdit`/`canAdmin`/`canRollback`, the last
gated by an env flag defaulting false). None of this exists in `web/` — no
Supabase, no session. Flagged this explicitly (had noted it as a Stage-1
deferred decision) rather than silently picking an approach, since it
touches every single page file about to be written. muhammad chose: drop
the gate entirely, hardcode `ADMIN_PERMISSIONS = { canEdit: true, ... }`
(not even a stubbed `requireAdmin()`-shaped function — simpler, since
nothing calls it). Login/unauthorized ported visually, reachable only by
direct URL, nothing redirects into them (yet).

**Reading past what I'd already read bit me once, caught before it shipped**:
I'd read the head of source's `chats/page.tsx` in Stage 0 recon and thought
I had the whole page. Re-reading in full during Stage 5 turned up real
pagination (`nextCursor` + "Load More"), a `formatRelativeTime` helper, and
a Normal/Crisis status column I'd have otherwise missed entirely. Lesson:
partial reads from early recon are not a substitute for a full re-read
immediately before porting a file — recon is for scoping, not for source of
truth. Also caught mid-write: `formatRelativeTime` rendering "Just now"/"Xm
ago" is user-facing text — Golden Rule 5 doesn't exempt `lib/utils/`
functions just because they're not components. Fixed by having the util
take the display strings as parameters (keeping `lib/utils` free of a
`dictionaries/` import) rather than hardcoding them.

Dropped the chats list's cursor pagination UI ("Load More") — unreachable
against a flat 3-row static array with no cursor concept. Removed the
corresponding now-dead dictionary key rather than ship unreachable UI.
Flagged as a scope call, not silently done.

Wrote a small Node script to cross-check every dictionary leaf key against
actual usage across the source tree — found exactly one unused key of my
own (`loadMore`, after dropping pagination) plus one pre-existing scaffold
leftover (`common.retry`, not mine to touch). Worth reusing this check
pattern at the end of any dictionary-heavy port stage.

**Verification for this stage went beyond static checks**: started the
built production server and fetched every real route with real placeholder
IDs via Node's `fetch` (including a genuine unknown-ID 404 for `notFound()`),
then asserted specific data strings (crisis badges, transcript content,
category grouping) actually appeared in the returned HTML — not just that
the page compiled. This is the same category of discipline as the CSS-grep
habit: a successful build proves the code is syntactically valid, not that
it does the right thing at runtime.

## Post-port restructure: admin/ vs auth/ split

After Stage 5 shipped, muhammad asked to split the routing: delete the
Next.js scaffold `app/page.tsx`, redirect `/` → `/auth/login` via
`next.config.ts`, add `/admin` → `/admin/prompts` (source had this,
I'd skipped it as out-of-scope in Stage 5), and move `login/` out from
under `admin/` into a new sibling `auth/` section with its own minimal
layout. Auth-gating logic itself (redirect unauthenticated → login, bounce
authenticated-at-login back to `/admin/prompts`) is explicitly future work,
not built now — no real auth exists yet to gate on.

Used a `permanent: false` (307) redirect for `/` → `/auth/login` rather than
307's `permanent: true` sibling — a permanent redirect gets aggressively
browser-cached, which would be painful to undo once real auth logic replaces
this placeholder. Small thing, but this class of "will this decision be
annoying to reverse" question is worth asking for anything config-level
before defaulting to whichever flag reads as more "correct."

Two stale path references the move would have silently broken if not
grepped for: `unauthorized/page.tsx`'s "Back to Login" link and
`AdminNav`'s sign-out `router.push`, both still pointing at the deleted
`/admin/login`. `grep -rn "admin/login"` across `app/`/`components/`/
`dictionaries/` before considering the move done.

## Applies to

Any future port from `mani-app` into this repo — the "read the whole file,
not just the head, immediately before porting it" lesson and the
"grep compiled CSS output, don't trust a green build" habit both apply to
any styling/JSX port, not just this one. The `set-state-in-effect` pattern
(sync data behind async-shaped state) will recur any time a placeholder
replaces a real network call but the surrounding UI's loading/error
branches need to stay alive for a future backend swap-in.

## Links

- [[mani-mobile-ui-port]] — the precedent this port followed (placeholder
  data, dictionary-as-you-go, domain component folders). **Not present on
  this branch** (`mani-web-revamp`) — it lives on the sibling
  `mani-mobile-revamp` branch, which diverged from the same `fbffecf` first
  commit. The two branches' vault journals have not been reconciled; see the
  note in [[ADR-001]]'s consequences, and flag to muhammad if cross-branch
  journal visibility becomes a real problem.
- [[ADR-001]]
- [[ADR-003]] — the Tailwind-only styling exception for this port
