---
type: decision
status: accepted
date: 2026-09-15
apps: [web]
tags: [decision, web, styling, tailwind]
---

# ADR-003: Ported admin UI styles entirely as Tailwind utilities, not hand-written CSS

**Status:** accepted
**Affects:** web

## Context

Porting mani-app's admin dashboard UI into `web/` (see
[[mani-web-admin-ui-port]]). Source styles the admin dashboard almost
entirely through ~450 lines of hand-written CSS classes in `globals.css`
(`.btn`, `.card`, `.badge`, `.table-container`, `.action-link`, form input
selectors) plus heavy inline `style={{ color: 'var(--color-text)' }}` on
individual elements.

The `nextjs-best-practices` skill governing `web/` states plainly:
"Tailwind utility classes only — no custom CSS unless genuinely
unavoidable" and "Never use inline `style={{}}`." The first plan for this
port proposed keeping source's `.btn`/`.card`/`.badge` classes as-is
(fastest port, highest fidelity to source, matches how the rest of
`globals.css`'s hand-written classes already look) and converting only the
inline `style` props to Tailwind. muhammad caught that this contradicted the
skill's own rule before any code was written.

## Options considered

### Option A — keep hand-written CSS classes, convert only inline styles
- Pros: fastest port; smallest diff from source; lowest risk of visual
  drift during the move
- Cons: directly contradicts the skill's documented rule for every other
  file in `web/`; leaves the admin UI styled differently from how the rest
  of the app is expected to be built going forward

### Option B — full Tailwind utility rewrite, no custom CSS classes
- Pros: consistent with the skill and with every other file in `web/`;
  `globals.css` stays limited to `@theme inline` tokens and genuinely
  unavoidable CSS (e.g. a custom `@keyframes` animation, which Tailwind has
  no utility-only way to express)
- Cons: more work per component; higher risk of a silent visual mismatch
  during conversion (realized during the port — see the noise-texture bug
  in [[mani-web-admin-ui-port]])

## Decision

Option B. Every hand-written CSS class from source (`.btn`, `.card`,
`.badge`, `.action-link`, `.empty-state`, form input styling, etc.) was
rewritten as Tailwind utility class compositions — either inline
`className` strings, small shared constants
(`components/admin/form-field-classes.ts`), or `cn()`-composed variant maps
— reading the `mani-*` design tokens declared in `@theme inline`
([[mani-web-admin-ui-port]], Stage 1). Inline `style={{}}` props were
converted the same way. `globals.css` carries only `@theme inline` token
declarations, light/dark `:root` overrides, and the one custom
`@keyframes fade-in` + `--animate-fade-in` token (a real exception —
Tailwind v4 has no utility-only way to declare a custom keyframe animation;
the `--animate-*` + `@keyframes` pair is Tailwind's own documented pattern
for this, the same mechanism its built-in `spin`/`pulse`/`bounce` use).

## Consequences

- The ported admin UI is styled consistently with the rest of `web/` and
  with the skill's own rules — no special-cased section for a future
  contributor to trip over.
- Every component-class conversion was a manual, judgment-based translation
  (source's classes carry no 1:1 Tailwind equivalent table), which is
  slower and carries real risk of silent mismatch — proven out when the
  `AdminNav` sidebar's noise-texture background, first ported as a Tailwind
  arbitrary-value data-URI, silently compiled to corrupted CSS (Tailwind's
  arbitrary-value escaping rewrites spaces to underscores). The general
  fix and lesson: never pack a real asset into an arbitrary Tailwind value;
  extract it to a real file under `public/` and reference it by URL. This
  now stands as a concrete instance of "verify the compiled CSS output
  directly, not just that the build succeeds" for any future Tailwind
  conversion in this repo.
- `globals.css`'s only non-token content is the one custom animation
  keyframe — if a future port needs another CSS-only capability Tailwind
  utilities can't express (another custom animation, a pseudo-element
  trick), the same `--animate-*`/`@theme` pattern is the precedent to
  follow, not a return to hand-written component classes.

## Links

- [[mani-web-admin-ui-port]]
- Related: [[ADR-002]] — mobile's equivalent token-architecture decision,
  referenced by the mobile port journal but not present on this branch
  (`mani-web-revamp`); it lives on the sibling `mani-mobile-revamp` branch
  and was never written as a standalone ADR file there either, only
  referenced from the journal entry
