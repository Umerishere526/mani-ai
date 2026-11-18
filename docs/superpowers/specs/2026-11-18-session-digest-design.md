# Every new Claude session starts with the decisions in force and the approaches that failed

Approved approach: A (muhammad, 2026-11-18). Short design.

## Intent

A new Claude Code session knows only CLAUDE.md, one area file and its own auto memory. The decisions in force live in
`backend/PORT-STATUS.md` (1,053 lines, read rarely, skimmed when read) and the failed approaches in 91 journal notes
with no index. So new sessions forget decisions and repeat failed approaches (muhammad, 2026-11-18). The knowledge has
to be in front of every session, current with the code, and never a lock: it informs, and a session can still change a
decision and record the change.

## Goals

1. Every session (new, resumed, cleared, compacted) starts with a short digest: each decision in force in one line, and
   each failed approach in one line, each pointing to where the whole story is.
2. The digest is rebuilt from the files at every session start, so it is never older than the repo. No index to keep.
3. The sources stay the homes: PORT-STATUS for decisions, the journal for lessons. The digest is generated, never edited.
4. Writing a decision or a journal note without its one-line summary is flagged when it happens, not discovered later.

## Non-goals and anti-goals

- No new place to record facts; CLAUDE.md's "one home each" table stays as it is.
- Anti-goal: a digest that reads as rules. It opens by saying it is history: decisions bind until muhammad changes them
  (CLAUDE.md), the journal loses to current evidence, and changing a decision means editing its entry in place.
- Anti-goal: a digest so long the session skims it, or over the 10,000-character hook limit, past which only a preview
  arrives.

## Approaches

- **A (chosen):** a digest generated from the sources at every session start by a hook.
- B: search the sources on every message; keyword matching misses rephrasings, adds latency to every message, and
  resumed sessions replay old results.
- C: one file per decision with a generated index; a large migration of PORT-STATUS and of CLAUDE.md's rules.

## The design

1. **One summary line at each source.**
   - A decision is its bold first line, as now; the digest takes it and the date from its `Because ... (YYYY-MM-DD).`.
     Entries marked Retired are left out.
   - A journal note's frontmatter gains `summary:` (one line: what the note is about) and, where it records something
     that did not work, `failed:` (a list of one-line "tried X; failed because Y"). A note superseded as a whole is
     left out; a note with a superseded part keeps its `failed:` lines, since a failed approach stays a lesson.
   - The 18 notes without frontmatter get it. Backfilling all 91 notes is part of this work.
2. **The digest script** (`.claude/hooks/digest.py`, Python standard library only, so it runs without the backend's
   environment). It prints: a two-line preamble saying this is history and how to change a decision; "Decisions in
   force" (one line each, with its date, grouped by area when the entry names one); "Failed approaches" (newest first,
   each with its note's name). It keeps the whole output under 9,000 characters: when it would run over, the oldest
   failed approaches are dropped and a last line says how many and how to find them (`grep -l failed:` in the
   journal).
3. **The hook.** A SessionStart hook in `.claude/settings.json` (matchers `startup`, `resume`, `clear`, `compact`) runs
   the script; its output is put in front of the session.
4. **The check.** The existing edit hook (`.claude/hooks/check.sh`) runs `digest.py --check` when a file under
   `mani-vault/Journal/` or `backend/PORT-STATUS.md` is written: a note without `summary:`, or a decision entry whose
   bold line is missing, is reported back to the session so it is fixed at once. It reports; it never blocks a write.
5. **CLAUDE.md** gains two lines in "Learning and Memory Management": every journal note carries `summary:` and, when
   something failed, `failed:`; the session-start digest is generated from them and from PORT-STATUS, so keep those
   lines current.

## Verification

- Tests for the script (`.claude/hooks/test_digest.py`, run with `python3 -m pytest` or plain `python3`): a retired
  decision is left out; a note superseded as a whole is left out; the output stays under 9,000 characters and says
  what it dropped; `--check` names a note without `summary:`.
- A real run: the digest from today's repo, printed and read; then a fresh session started to confirm it arrives.

## Left to the builder

The exact digest layout, how areas are named, and the wording of each backfilled summary line (taken from the note,
never invented).
