# 0010. Rationale: a stage ledger

The decision record for [index.md](index.md). `/develop` builds from the index; this file holds the why.

## Context

> ⚠️ Premise note: the scope's done line says "no stage already answered is asked again", and muhammad chose to let the model move a stage back when the person corrects or takes back an answer. The two only agree with that exception written in, so AC-13 carries it. The cost is that a model slip and a real correction look the same in the ledger; only the notes and the evals tell them apart.

> ⚠️ Premise note: the work stage rule ("known only in the person's own words in this conversation") cannot be checked by code without storing their words, which this design refuses. It rests on the prompt and is checked only by real model evals, which cost the client's credit and run only with muhammad's yes.

Every framework's `Starts when` line tells Mani to learn its first stages before offering it. ABCDE asks for the event, what it came to mean and how believing it shapes them, which are stages A, B and C. Then, once the person says yes, the stage machine starts from the first stage again. The better Mani understands before the offer, the more repetitive the framework feels. muhammad saw this live as Mani asking a stage already answered.

Three places hold the walk in order, and changing one changes nothing because the other two pull the stage back (journal: `stage-skip-blocked-by-its-own-gate-2026-10-08`):

- `Registry.clamp` in `backend/mani/chat/techniques.py`, called from `guards.check`, stores at most one stage forward per turn. A reply that jumps from A to D is stored as B, and the next `[ctx]` says `stage: belief`, so Mani asks B again.
- `mani_base.md` `in_a_framework` says "never skip a stage".
- `response_format.md` `framework_starting` allows exactly one skip, on the accepting turn.

A second gap sits beside it: the ending cap counts from `ending_from`, which is set only once the stored stage is `somatic_checkin` or `somatic_practice`. A framework stuck on `closing` or earlier has no backstop, and while a framework runs the router is off, so nothing else can be offered.

The forces: one model call per turn (decision in force, spec 0006), no code that reads words to drive the conversation (spec 0007), conversation content is special category health data (`.claude/BACKEND.md`), and the client's specs still require that ABCDE "does not skip directly from the event to a balanced belief" (`backend/docs/specs/framework-abcde.md` section 19). An earlier attempt, reverted on 2026-10-07, stored the person's words per stage in a `known` jsonb column; that column still exists on the hosted database, which is seven migrations ahead of the code.

## Options considered

### Option 1: Fix in place, loosen the clamp

Let `Registry.clamp` accept any forward move of the model's `step`, drop "never skip a stage" and the one skip rule.

**Pros**:
- The smallest change: no column, no schema field, no new `[ctx]` line.

**Cons**:
- The model reports only a pointer, so a partial stage is invisible: the next turn cannot tell "asked once, half answered" from "not asked".
- No memory between turns beyond the pointer, so once the history window scrolls the earlier answers into the summary, the model loses what it skipped and why.
- Gives no backstop for a stuck stage.

### Option 1b: Loosen the clamp and count turns per stage

Option 1 plus a per stage turn counter and the ending cap from `closing`: the model's pointer may jump forward to `closing`, and partial or "known out of order" live only in the prompt and the history.

**Pros**:
- Fixes the skip and closes both backstop gaps with a counter column instead of a ledger and a schema field.
- Fewer output tokens per turn.

**Cons**:
- A partial stage is still invisible to the next turn, and once the history window (20 messages) scrolls the answers into the summary, the model cannot tell what was half answered from what was never asked.
- A stage answered out of order (C told, B not) cannot be represented by one pointer.

### Option 2: A stage ledger of statuses (chosen)

The model reports every stage's status each turn in the same call, the code stores statuses and counts and picks the stage.

**Pros**:
- Partial is explicit, so Mani asks only the missing part.
- The code owns order and limits; the model owns judgement. Matches how the ending is split (spec 0009).
- Holds no words, so it adds no health content to the database.
- The per stage count gives a backstop that bounds the whole framework.

**Cons**:
- More output tokens on every running turn, and a new column and schema field.
- The model can still misjudge a stage; the code cannot check "their own words".

### Option 3: Store the person's words per stage

What the reverted `known` column did: keep what they said for each stage and feed it back, so the next turn knows what is answered.

**Pros**:
- The model sees exactly what answered each stage, so a judgement is easier and checkable by a reviewer.

**Cons**:
- Stores health content in a new place, with its own retention and access questions.
- The words duplicate the history and summary that already carry them.
- It was built and reverted once.

### Option 4: Code detects answered stages

Match the person's messages against stage patterns in Python.

**Pros**:
- Deterministic and free per turn.

**Cons**:
- Reverses spec 0007 (no code that reads words), and phrase matching already fails on plain phrasing (the router misses "I've been avoiding my friends because I've been overwhelmed").

## Rationale

Option 2 is the only one that makes a partial stage visible and bounds a stuck framework without storing words. Option 1 fixes the jump but not the partial case or the missing backstop, and the history window would still erase what the pointer skipped. Option 1b closes the backstops more cheaply, but the scope's done line asks that a partial stage gets only its missing part, which a pointer cannot carry. Option 3 solves the same problem by keeping health content the history already holds, and it was already reverted. Option 4 contradicts a decision in force.

muhammad's calls on the details, with the reasoning:

- **The ledger covers the stages between `offering` and `closing`.** `closing` is the ending's first question ("how it sits now"), and the client's flow and spec 0009 require it to be asked, so it is never skippable.
- **Work stages are marked by a ` | ` in the Stages line, not a frontmatter field.** No code can check "their own words", so the code has no use for the split; a ` | ` replaces a ` > ` and costs no characters on lines already at 318 of 320.
- **The model may move a stage back** (recommended was making `known` final). muhammad chose fidelity to a changed mind; the cost is in the premise note above. The guard against abuse is the notes and AC-13.
- **The stall cap is per stage, counted across every visit, at 4** (recommended was a total cap that jumps to `closing`). Counting across visits matters: with moves back allowed, a count that reset on each visit could loop forever, while a running total bounds the framework at ledger stages × 4. The `passed` status is final and written only by code, so a passed stage cannot be reopened and the work stage rule stays honest: passed is not known. 4 is two tries plus two from a new angle, as `in_a_framework` already says, and may change on the client's requirement.
- **The ending cap starts at `closing`**, because `Registry.ending_open` already treats `closing` as the ending; one cap then covers it rather than adding the stall cap to a stage the ending owns.
- **The ledger is frozen from `closing` on**, so the ending runs as spec 0009 built it and the ending cap stays meaningful.
- **A reply without a ledger holds and still counts**, so a model that drops the field cannot hold the thread past the cap. **A concern turn counts nothing**, because Mani asked no stage question.
- **One jsonb column, not a child table.** The row is already written every turn; a table would add policies, grants, an index and up to eight writes per turn for a value read only by this row's turn. It is named `stage_ledger` because hosted's leftover `known` column would make `add column known` fail there.
- **No compatibility code for frameworks running at deploy** (backward compatibility needs muhammad's yes, and muhammad declined it). An empty ledger reads as all missing and the first reply reports the whole ledger.

Calls made in writing the spec (each with its runner up):

- The reply carries `stages` as a list of `{stage, status}`, not an object keyed by stage id, because the keys differ per framework and a JSON schema cannot name them (runner up: the object, shorter but shapeless to the model).
- `state.step` stays and counts only from `closing` on, so the ending is untouched (runner up: dropping it, which reopens spec 0009).
- `next_stage` leaves `[ctx]`: it existed for the one skip on the accepting turn, and `framework_stages` already gives the ending's order (runner up: keeping it, a line of meaning the ledger now replaces).
- The guard drops an off list entry rather than the whole ledger, the same rule as `style`, so one bad value costs one entry (runner up: dropping the whole ledger, which loses a turn's good judgements).
- After the cross check (another model, 2026-10-08), muhammad took every recommended fix. Two are worth the why. `stage_last_try` exists because the reply on the capping turn is written before the code knows the stage will pass; without it Mani asks the stage a fifth time and the answer lands on the next stage. A code check refusing `known` on work stages during the accepting turn was weighed and left out: it would ask again someone who already worked out a fairer view in their own words before the offer, and it would need the code to read the split.
- `eval_replies.py` checks the stored stage after each turn (`expect_stage`), because the stored stage is the one value the code decides and the transcript alone cannot show it (runner up: reading transcripts by hand only).
