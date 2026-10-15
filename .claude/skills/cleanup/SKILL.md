---
name: cleanup
description: Find and remove dead code (unused files, functions, exports, components, endpoints, dependencies, directories) and code smells (spaghetti code, duplication, oversized components, deep nesting, half-finished migrations) in web/, mobile/, backend/ and chat-tester/. Use when muhammad asks to clean up, remove dead or unused code, delete unused files, reduce tech debt, find code smells or bad code, tidy a module, or after a redesign or migration to remove the old path, even without the word "cleanup".
---

# Cleanup

Tools and grep find candidates. Claude verifies each one. muhammad approves before anything is deleted. Deletion happens in small batches, with verification after each.

Never delete from memory or a quick read. Static analysis gives false positives in this repo (file-based routing, decorators, Pydantic, seeded content), and an LLM guess gives more.

## Phase 0: Read what must stay

Before scanning, read:
- "Decisions in force" in `backend/PORT-STATUS.md`. Anything a decision keeps is not dead, however unused it looks. For example, a framework that is paused rather than removed keeps its files, rows, tests and specs.
- Any spec in `docs/specs/` or journal note in `mani-vault/Journal/` from an earlier unused-code audit (`grep -ril "unused" docs/specs mani-vault/Journal`). Its keep list stands, and its lessons say what that audit got wrong.
- These always stay: guardrails (the crisis screen and its records), audit columns a person reads when something goes wrong (which model served a call, why it failed, who edited a prompt, `created_at`/`updated_at`), `.agents/skills/` and `skills-lock.json`.

## Phase 1: Scan (read-only)

Run each app separately, `cd`-ing into it first as CLAUDE.md requires. If a tool isn't installed, ask muhammad before adding it. Prefer `npx`, or a one-off runner, over a new dev dependency. `ruff` and `vulture` are not in either venv.

**web/ and mobile/**
- First check whether the app calls the backend yet (`grep -rE "fetch\(|API_URL" app lib src`). If it doesn't, "unused" there often means "not wired yet". Class those findings as **Not wired yet** (see Phase 2), never Dead.
- Unused files, exports, types, dependencies: `npx knip`. Knip turns on framework plugins from `package.json`. Check that its plugin list covers expo-router routes under `mobile/src/app/`.
- Type errors and lint: `npx tsc --noEmit`, then `npm run lint`.
- Copy-paste duplication: `npx jscpd --min-lines 8 <src dirs>`.

**backend/ and chat-tester/** (activate the venv first)
- Grep is the primary tool. For each module-level function, class and constant, grep its name over the app, `tests/`, `scripts/` and `content/`.
- `vulture . --exclude .venv,venv --min-confidence 80` is a cross check only. On this codebase it flags route handlers, Pydantic `model_config` and validators, response model fields and Streamlit `session_state` attributes, and the last audit found nothing with it that grep missed.
- Unused imports and variables, and complexity: `ruff check --select F401,F841,C901,PLR0912,PLR0913,PLR0915 .`
- Duplication: `npx jscpd --min-lines 8 --format python <src dirs>`, with the venv excluded.

**Repo-wide**
- Hotspots, the files changed most often, so effort goes where it pays:
  `git log --since="6 months ago" --format= --name-only | sort | uniq -c | sort -rn | head -30`
- Directories with no inbound imports: `git log -1 --format=%cr -- <dir>` for their last change.

### Smell checklist

Check against the golden rules in CLAUDE.md first, since they are this repo's definition of bad code:
- components over 150 lines, hooks over 80, more than one component per file
- `||` used for defaults
- hardcoded user-facing strings
- `"use client"` on a whole page
- frontends calling external APIs directly

Then general smells:
- functions over about 50 lines, nesting deeper than 3, more than 4 parameters
- god modules that everything imports, circular imports
- duplicated logic, commented-out code, unused feature flags
- two implementations of the same thing. This is a half-finished migration, the most expensive smell. Always report it.

## Phase 2: Verify every candidate

Before calling anything dead, rule out these false positives:

- **Framework entry points are never unused:**
  - `web/app/**` route files (page, layout, loading, error, not-found, route, template)
  - `mobile/src/app/**` routes and layouts
  - `chat-tester/app.py`
  - config files, and scripts named in `package.json`
- **FastAPI:** handlers registered by decorators or `include_router` look unused to tools. A backend endpoint is dead only if:
  - nothing in `web/`, `mobile/` or `chat-tester/` calls it,
  - no spec in `docs/specs/` or client document in `backend/docs/specs/` requires it,
  - and the frontends are wired. While they run on placeholder data, an endpoint they will call is **Not wired yet**.
- **Seeded content:** files in `backend/content/` are read by the seed by name, and their names are checked by tests. Grep for the file stem as a string.
- **Dynamic references:** grep for the name as a string. This catches dynamic imports, `getattr`, keys built at runtime, and `dictionaries/` keys read through object paths (knip does not check JSON keys).
- **Kept on purpose:** anything from Phase 0.
- **Used only by tests:** the code is dead. Delete it together with its tests, and say so.

Classify each finding:
- **Dead**: verified unused, with the evidence.
- **Probably dead**: evidence is incomplete; muhammad decides.
- **Not wired yet**: built ahead of the wiring, in `web/` or `mobile/`. Report it, but never propose deleting it. muhammad decides whether the plan still needs it.
- **Smell**: used, but needs refactoring.

**Database objects** (columns, grants, policies, functions) are out of this skill's batches. Removing one is a migration, so list it in the report and propose a spec through `/architect`. The last audit's lessons apply there:
- ask who opens an audit column when something goes wrong, not which function reads it
- grep every `.sql` test file before revoking a grant
- drop a column from the select lists in the same change

## Phase 3: Report, then stop

Present one report per app:

| Path / symbol | Kind | Evidence | Class | Proposed action |
|---|---|---|---|---|

Order smells by hotspot rank, not by ugliness. Messy code nobody touches is cheap debt; messy code changed every week is expensive.

If a smell is really a design problem, flag it for the `architecture-reviewer` agent instead of proposing a local refactor (see "When the design is the problem" in CLAUDE.md). Two examples: spaghetti that comes from how modules are split, and a half-finished migration.

Then stop and wait. muhammad's approval of the report is permission to delete exactly the approved items, nothing more.

## Phase 4: Remove and refactor in batches

- One batch = one app and one kind, for example "unused files in web/" or "unused deps in backend/".
- After each batch, run the app's checks:
  - `web/`: `npx tsc --noEmit`, `npm run lint`, `npm run build`. There is no test script.
  - `mobile/`: `npx tsc --noEmit`, `npm run lint`, `npm test`.
  - `backend/`: the test commands in `.claude/BACKEND.md`, with pristine output, and confirm `fastapi dev main.py` boots. Never run `scripts/scenario_check.py` or a live model conversation, because they spend the client's credits.
  - `chat-tester/`: its tests and a `streamlit run app.py` boot.
- If a batch breaks anything, revert the whole batch and re-verify the candidates. Don't patch forward.
- Propose one commit per batch, with a message naming what was removed and why it was unused. Commit only when muhammad says so.
- Smell refactors go one at a time. If no test covers the code's behavior, first write one that passes before the refactor and after it.
- Commented-out code is dead code, not documentation, so remove it. Real comments follow the comment rules in CLAUDE.md.
- Removing a dependency means removing it from `package.json` or `requirements*.txt`, and the lockfile, in the same batch.

## Afterwards

- Record confirmed false positives in a journal note, for example `knip-false-positives.md`. Propose matching ignores in `knip.json` or a vulture whitelist so the next scan is cleaner. Config changes need muhammad's approval.
- Update "Decisions in force" if a removal reflects a decision, such as dropping a library.
- End with a short summary: what was removed, lines deleted, and what was deferred and why.
