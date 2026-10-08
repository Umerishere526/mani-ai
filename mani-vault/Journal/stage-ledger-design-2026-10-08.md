---
type: journal
date: 2026-10-08
tags: [journal, frameworks, stages, ctx, tuning, gotcha]
---

# Stage ledger design (spec 0010)

Designed feature 12 as `docs/specs/0010-stages-skip-what-chat-told/`. A cross check on another model found gaps that apply beyond this feature.

## Gotchas worth keeping

- **`[ctx]` is built before the reply exists.** A free text yes is only known after the model answers (`state.accepted`), so `framework_starting` is never shown on that turn. Anything the accepting turn must be told has to ride on `offer_waiting` too.
- **A cap counted after the reply is one turn late.** The reply on the capping turn was written while `[ctx]` still named the old stage, so it asks it again and the answer lands on the next stage. Tell the model before the call (`stage_last_try`).
- **`WindowTuning` is strict (`extra="forbid"`).** A new tuning key and its code ship with the reseed in one change, either order alone breaks every turn.
- **`guards.check` nulls `framework_id` when the clamp gives no phase.** Any change to how the phase is chosen must keep the framework id independent of it, or no row gets written.
- **Hosted still has a `known` column** on `thread_technique_state` from the reverted migration 012. Never reuse that name.

## muhammad's calls

The model may move a stage back (a correction reopens it), the stall cap counts per stage across visits at 4, and the client may change that number.

Related: [[stage-skip-blocked-by-its-own-gate-2026-10-08]], [[reverting-code-does-not-revert-the-database]], [[body-ending-build-2026-10-08]]
