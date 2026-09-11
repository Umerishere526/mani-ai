---
type: reference
app: web
tags: [reference, web]
---

# Web

Next.js 16.3.4, App Router, React 19.2.8, Tailwind v4, TypeScript 5.

**Source of truth:** `.claude/WEB.md` and the `nextjs-best-practices` skill. Facts about the stack belong there — this note is for links and project-specific context that accumulates over time.

```bash
cd web && npm run dev     # :3000
```

## Shape

- Routes at `app/` (not `src/app/` — [[Mobile]] is the opposite)
- Tailwind v4 CSS-first, tokens in `app/globals.css`, no JS config
- Talks to [[Backend]] at `http://127.0.0.1:8000` in dev; no proxy configured yet

## Decisions

Decisions affecting web:

```dataview
LIST FROM #decision WHERE contains(apps, "web")
```

(Requires the Dataview plugin — otherwise link ADRs here by hand.)

## Notes

-
