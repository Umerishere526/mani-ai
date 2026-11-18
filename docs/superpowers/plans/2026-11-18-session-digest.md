# Session Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every Claude session starts with a generated digest of the decisions in force and the failed approaches.

**Architecture:** A standard-library Python script reads `backend/PORT-STATUS.md` and the journal's frontmatter and
prints the digest; a SessionStart hook runs it; the edit hook runs its `--check` mode on journal and PORT-STATUS
writes. The journal's 91 notes are backfilled with `summary:` and `failed:` lines.

**Tech Stack:** Python 3 standard library, bash, Claude Code hooks.

**Spec:** `docs/superpowers/specs/2026-11-18-session-digest-design.md`

## Global Constraints

- The digest stays under 9,000 characters; over it, the oldest failed approaches are dropped with a last line saying
  how many and how to find them.
- The digest opens by saying it is history: decisions bind until muhammad changes them, the journal loses to current
  evidence, and a decision changes by editing its entry in place.
- `--check` reports and never blocks a write. Summary lines are taken from each note, never invented.
- Commit per task on `feat/one-call-turn`; never merge or open a PR.

## Review Focus

1. A journal note with malformed frontmatter (no closing `---`, a value with a colon): the script skips the field, never
   crashes the session start. Test in Task 1.
2. A decision whose bold line wraps onto a second line: read whole. Test in Task 1.
3. A note with `failed:` but superseded in part: its failures stay. Test in Task 1.
4. The script failing (a bad file): the hook prints nothing rather than an error into the session. Task 3 (`|| true`).
5. A fresh session actually receiving the digest. Task 3, a real session.

---

### Task 1: The digest script

**Files:** Create `.claude/hooks/digest.py`, `.claude/hooks/test_digest.py`.

**Interfaces:** `decisions(port_status: str) -> list[tuple[str, str]]` (bold line, date), `notes(journal: Path) ->
list[Note]` (name, date, summary, failed, superseded_whole), `digest(root: Path) -> str`, `missing(root: Path,
paths: list[Path]) -> list[str]`; CLI: `digest.py` prints the digest, `digest.py --check FILE` prints what is missing.

- [ ] **Step 1: Write the failing tests** in `test_digest.py` (plain asserts, run with `python3 test_digest.py`):
  a retired decision is left out; a bold line over two lines is read whole; a note whose first line is a
  `> Superseded ... — see` with no part in parentheses is left out, one with a part keeps its `failed:` lines; the
  output for a fixture of 200 failed lines is under 9,000 characters and ends with the dropped count; malformed
  frontmatter yields no fields and no exception; `missing` names a note without `summary:`.
- [ ] **Step 2: Run them.** Expected: FAIL (no module).
- [ ] **Step 3: Implement** with the standard library only (frontmatter read line by line, `failed:` as a YAML-style
  list of `- ` lines).
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit.** `git commit -m "A script that prints the decisions in force and the failed approaches"`

### Task 2: Backfill the journal

- [ ] **Step 1.** Each of the 91 notes gets frontmatter if missing (`type`, `date` from its filename, `tags`), a
  `summary:` line, and `failed:` lines where the note records an approach that did not work, each taken from the note's
  own words. Done by one subagent with these rules; then read ten notes at random against their lines.
- [ ] **Step 2.** `python3 .claude/hooks/digest.py --check mani-vault/Journal/*.md` prints nothing; `digest.py` is
  under 9,000 characters.
- [ ] **Step 3: Commit.** `git commit -m "Give every journal note a summary line and its failed approaches"`

### Task 3: Hook, check and CLAUDE.md

- [ ] **Step 1.** `.claude/settings.json`: a SessionStart hook (matchers startup, resume, clear, compact) running
  `python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/digest.py" 2>/dev/null || true` (via the update-config skill).
- [ ] **Step 2.** `.claude/hooks/check.sh`: a `mani-vault/Journal/*.md` or `backend/PORT-STATUS.md` write runs
  `digest.py --check` on it and reports any output.
- [ ] **Step 3.** CLAUDE.md "Learning and Memory Management": two lines on `summary:`/`failed:` and the digest.
- [ ] **Step 4.** Print the digest for muhammad; start a fresh `claude -p` session asking what it was told about
  decisions, to confirm it arrives.
- [ ] **Step 5: Commit.** `git commit -m "Start every session with the digest; flag a note without its summary"`
