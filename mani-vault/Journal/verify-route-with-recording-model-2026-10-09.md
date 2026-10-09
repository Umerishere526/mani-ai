---
type: journal
date: 2026-10-09
tags: [journal, verify, llm_calls, stages, offer]
---

# Verifying a turn through the real route without spending credit

`/check verify` for spec 0010 needed proof that `link_call` writes `reported_stages` and `stage` through `routers/messages.py`, not only when a test calls `link_call` directly (`test_turn.py`'s call row test does the latter).

What worked, as a scratch test outside the repo, run with `pytest -c pytest.ini --rootdir=.` from `backend/`:

- Import the fixtures from `tests.integration.test_turn` (`alice`, `no_real_exercise_call`, `start`, `past_the_opening`, `_land_on`) into the scratch module, so pytest finds them.
- Monkeypatch `orchestrator.client.complete` with a model that inserts a real `admin.llm_calls` row (`llm_calls.record` as admin) and returns its id in `client.Call`, so the route's `fire_and_forget(link_call(...))` has a row to update.
- `httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app()))` with `app.dependency_overrides[current_user] = lambda: alice`. No lifespan runs; the `alice` fixture opens the pool.
- After each POST, `await asyncio.gather(*mani.background._pending)` before reading the row.
- The chat tester's own readers (`framework_debug_state`, `ledger_text`, `call_stages_text`) can be run on the same threads from its venv in a subprocess, before the fixture cleans up.

## Gotcha

A typed question about an open offer stays open only when the reply makes the offer again (a prompt with a technique) and the message has a `?` (`orchestrator.py`, the `deferred` branch). A scripted reply without the buttons is a decline, which looks like an AC-5 failure and is not.

`offer_waiting` means they typed past the offer; a tap on Keep Chatting is not an offer waiting, so `[ctx]` carries no `stage_ledger` on that turn.

Related: [[stage-cap-and-expect-stage-build-2026-10-09]], [[stage-ledger-design-2026-10-08]]
