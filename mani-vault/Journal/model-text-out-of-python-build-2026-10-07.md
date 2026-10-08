---
type: journal
date: 2026-10-07
tags: [journal, prompts, tests, database, gotcha]
---

# Building spec 0007: model facing text out of Python

## test_db.sh passed once, then failed every time

The throwaway Postgres (`postgres:17`) runs a temporary server during init, on the unix socket
only, then stops it and starts the real one. `scripts/test_db.sh` waited with `psql -c 'select 1'`
over the socket, so it could see the temporary server, print "ready", and send the harness into the
restart gap: `connection to server on socket ... failed`. The first run won the race, the next two
lost it. The temporary server does not listen on TCP, so the wait now uses `psql -h 127.0.0.1`.
Three runs in a row passed after that.

**How to apply:** a readiness check against the official postgres image must go over TCP.

## LangChain always writes a description

`convert_to_openai_function` puts `"description": ""` on the function even when the class has no
docstring. A contract test that asserts no `description` key at all can never pass; assert that no
description has text (`tests/unit/test_prompt_contract.py`).

## A closed set had a fourth home: the SQL suite

Migration 019 dropped the shape CHECK. `tests/sql/test_rls.sql` still asserted that an off list shape
is refused, which only `scripts/test_db.sh` runs, never `pytest`. When a constraint changes, grep
`tests/sql/` too. See [[closed-sets-live-in-more-places-than-the-code]].

## Stale docs found, left for /sync

- `.claude/BACKEND.md` lists framework activation keys (`central_indication`, `to_find_out`,
  `earliest_offer_message`, `contraindications`) that spec 0005 removed; the file now holds
  `strong_signals`, `signals`, `redirects`, `never_offer_when_said` and `distinctions`.
- `backend/docs/database-schema-reference.md` says `admin.frameworks.body` is read by nothing. The
  composer renders it into the Framework Index.

Related: [[prompt-text-names-index-sections]], [[guard-test-passed-without-its-guard-2026-10-07]]
