---
type: reference
app: backend
tags: [reference, backend]
---

# Backend

FastAPI 0.141.1, Python 3.14, virtualenv at `backend/.venv`.

**Source of truth:** `.claude/BACKEND.md`.

```bash
cd backend && source .venv/bin/activate && fastapi dev main.py   # :8000
```

## Shape

- `main.py` holds the whole app today — one `GET /` route
- `requirements.txt` is `pip freeze` output; regenerate after adding a dependency
- No database yet — see [[Supabase]] if one is added

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | health/hello |

Keep this table current as routes are added.

## Decisions

```dataview
LIST FROM #decision WHERE contains(apps, "backend")
```

## Notes

-
