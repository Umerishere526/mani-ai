---
type: reference
app: backend
status: not-adopted
tags: [reference, supabase, database]
---

# Supabase

**Not adopted.** Nothing in the project uses Supabase or Postgres today — [[Backend]] runs FastAPI with no database.

**Source of truth:** `.claude/SUPABASE.md` and the `supabase-postgres` skill.

Adding a database is an architectural decision. Per the root CLAUDE.md it needs discussing with muhammad first, and the outcome should be written up as an ADR in `Decisions/` before implementation starts.

## If adopted, the non-negotiables

- RLS enabled in the same migration that creates each table
- Service role key never leaves `backend/` — never in `NEXT_PUBLIC_*` or `EXPO_PUBLIC_*`
- All schema changes as migration files in version control
- Every foreign key gets an index

Full rules in `.claude/SUPABASE.md`.

## Notes

-
