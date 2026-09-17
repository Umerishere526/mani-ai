# archive — evidence, not instructions

Everything in this folder is a **point-in-time record**. It is here so that a finding can be
traced back to the evidence behind it, and so the reasoning that produced a decision is not
lost.

**Do not execute anything in here.** Several of these documents contain plans, phase
orderings, and recommendations that have since been superseded. Where any of them disagrees
with a document one level up, the level above wins — always.

Current instructions live in `../START-HERE.md`.

---

## What each file is, and what in it is stale

### `2026-09-08-repo-audit.md`
The evidence register. Every finding with its ID (C1–C4, H1–H11, M1–M12, L1–L7), file path and
line number. **This is the most useful file here** — cite it when working a ticket. The
findings themselves remain accurate; what changed is the order they get fixed in, and that
several are absorbed by the schema rebuild rather than patched individually.

*Stale:* the regeneration count is given as five triggers in places; it is six, worst case ~21
provider calls per turn.

### `2026-09-08-technical-assessment.md`
Engineer-facing judgment — what is good, what is wrong, what it would cost. Keeps its value as
reasoning.

*Stale:* the Phase 0–4 ordering; the requirement that migrations and RLS changes be rehearsed
on staging (the database is being rebuilt from scratch, so RLS is written correctly the first
time); "prompt version management — keep as is" (the portal becomes authoritative and needs
real governance).

### `2026-09-08-mobile-review-and-consolidation.md`
The mobile findings (MOB-1 to MOB-11) plus the KEEP / FIX / RESTRUCTURE / REPLACE verdict and
flow traces. Sections 1–8 and 11 are genuinely valuable evidence — measured behaviour, traced
code paths.

*Stale:* sections 9–10, which are instruction-shaped: the order of work and the staging
prerequisite.

### `2026-09-08-repo-setup-and-doc-gaps.md`
Session record of a clean-clone setup. Most of its "gaps found" list **has since been applied**
— `EXPO_NO_METRO_WORKSPACE_ROOT` and `OPENROUTER_API_KEY` are in the `.env.example` files now,
and the Supabase CLI is pinned. Superseded as a runbook by `../SETUP.md`.

### `TECHNICAL-ASSESSMENT.md`
**A client deliverable**, not an engineering document — written for Manasa and Lolly, with no
file paths or finding IDs. Kept as a record of what was communicated externally and when.

*Stale throughout as instructions:* it still says a schema change requires migrating live data,
still lists prompt version management and the database schema under "keep as-is", and carries a
Phase 0–4 plan. All three are now false. Do not work from it. If another client update is
needed, write a new one rather than editing this.

### `SETUP_REPORT.md`
The verification record of a clean clone being brought up and tested end to end — including the
seed-UUID bug diagnosis and the explanation for the enormous `pnpm-lock.yaml` diff (prettier
de-formatting; the only semantic change is the Supabase bump, and committing it is correct).
Superseded as a runbook by `../SETUP.md`, but the diagnoses are worth keeping.

### `ExpoGO(Setup).md`
The original Expo Go walkthrough. Fully absorbed into `../SETUP.md`, including its
troubleshooting section.

*Stale:* its opening line lists `expo-auth-session` among the app's native dependencies. That
package is declared but unused.
