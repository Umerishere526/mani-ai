# 0010. Rationale: a stage ledger

The decision record for [index.md](index.md). `/develop` builds from the index; this file holds the why.

## Context

> ⚠️ Premise note: the scope's done line says "no stage already answered is asked again", and muhammad chose to let the model move a stage back when the person corrects or takes back an answer. The two only agree with that exception written in, so AC-13 carries it. The cost is that a model slip and a real correction look the same in the ledger; only the notes and the evals tell them apart.

> ⚠️ Premise note: whether a stage is clear rests on the model alone, for every stage, and no code can check it without storing their words, which this design refuses. A two sided stage (ABCDE's `dispute`) marked known from one side skips a question the person never worked through. `partial`, the real model evals (the client's credit, only with muhammad's yes) and the `llm_calls` columns are the checks, and the columns show it only after the fact.

Every framework's `Starts when` line tells Mani to learn its first stages before offering it. ABCDE asks for the event, what it came to mean and how believing it shapes them, which are stages A, B and C. Then, once the person says yes, the stage machine starts from the first stage again. The better Mani understands before the offer, the more repetitive the framework feels. muhammad saw this live as Mani asking a stage already answered.

Three places hold the walk in order, and changing one changes nothing because the other two pull the stage back (journal: `stage-skip-blocked-by-its-own-gate-2026-10-08`):

- `Registry.clamp` in `backend/mani/chat/techniques.py`, called from `guards.check`, stores at most one stage forward per turn. A reply that jumps from A to D is stored as B, and the next `[ctx]` says `stage: belief`, so Mani asks B again.
- `mani_base.md` `in_a_framework` says "never skip a stage".
- `response_format.md` `framework_starting` allows exactly one skip, on the accepting turn.

A second gap sits beside it: the ending cap counts from `ending_from`, which is set only once the stored stage is `somatic_checkin` or `somatic_practice`. A framework stuck on `closing` or earlier has no backstop, and while a framework runs the router is off, so nothing else can be offered.

The forces: one model call per turn (decision in force, spec 0006), no code that reads words to drive the conversation (spec 0007), conversation content is special category health data (`.claude/BACKEND.md`), and the client's specs still require that ABCDE "does not skip directly from the event to a balanced belief" (`backend/docs/specs/framework-abcde.md` section 19). The newer ABCDE document the client sent (`docs/client-share-docs/ABCDE Framework.docx`) asks Mani to use information already shared, ask only what remains necessary, and move on when a step is complete. An earlier attempt, reverted on 2026-10-07, stored the person's words per stage in a `known` jsonb column; that column still exists on the hosted database, which is seven migrations ahead of the code.

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
- **Any stage skips once the conversation makes it clear, the same for every stage** (muhammad, 2026-10-09, replacing a rule that work stages count only in the person's own words). In a live ABCDE chat (thread `cbc5c13d`, journal `stage-skip-and-short-questions-scope-2026-10-09`) the person gave both sides of D before the offer, one in answer to Mani's own question; the own words rule kept D open, Mani asked it fresh, and the person said "i already mentioned that". The code already skipped in any order, so the rule was the whole cause. With it gone, the ` | ` that marked the work stages has no meaning, so it and its seed check go. The prompt change is two cuts and one reword of the same length, no added rule. `known` is defined as "the conversation makes clear what it asks" rather than "they have said", so a stage Mani clearly understands counts even when it was never put as an answer (runner up: keeping "they have said", narrower, which would leave an effect Mani can see but they never named as partial). The risk is the premise note above, and the cost is accepted for a framework that never asks what it already knows.
- **The model may move a stage back** (recommended was making `known` final). muhammad chose fidelity to a changed mind; the cost is in the premise note above. The guard against abuse is the notes and AC-13.
- **The stall cap is per stage, counted across every visit, at 3, so a stuck stage is asked at most 4 times** (recommended was a total cap that jumps to `closing`). Counting across visits matters: with moves back allowed, a count that reset on each visit could loop forever, while a running total bounds the framework at ledger stages × the cap. The `passed` status is final and written only by code, so a passed stage cannot be reopened and is never read as known. 4 asks is two tries plus two from a new angle, as `in_a_framework` already says; the count may change on the client's requirement.
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
- After the cross check (another model, 2026-10-08), muhammad took every recommended fix. Two are worth the why. `stage_last_try` was added because the reply on the capping turn is written before the code knows the stage will pass; without it (with the cap at 4) Mani asks the stage a fifth time and the answer lands on the next stage. It was later dropped (next bullet). A code check refusing `known` on the later stages during the accepting turn was weighed and left out: it would ask again someone who already worked out a fairer view before the offer.
- **No `stage_last_try`; the cap is 3 instead of 4** (muhammad, 2026-10-09, the second amendment). Its `[ctx]` line was never written: task 1 built only `stage_ledger`, and the first amendment dropped the draft while saying it had shipped. Adding it now means a new line in `response_format.md`, against AC-11 and muhammad's rule that prompt changes cut, never add. Setting the cap one lower gives the same number of asks with no prompt line and no `[ctx]` key: the stage is counted on 3 answers, the reply on the third asks it a 4th time, and the next turn moves on. The cost is small: the answer to that 4th ask cannot mark the stage `known`, because it is already `passed`, but `stage_from_ledger` skips both, so the stage asked next is the same. The cross check (another model, 2026-10-09) found a second cost, accepted by muhammad: that answer counts as the next stage's first turn, so in a stall that runs on, the stage after a passed one gets 3 asks, not 4. Runner ups: dropping it and keeping 4 (a 5th ask, and the client line would change to 5), or adding the line (4 asks, the 4th answer judged, one more prompt line).
- `eval_replies.py` checks the stored stage after each turn (`expect_stage`), because the stored stage is the one value the code decides and the transcript alone cannot show it (runner up: reading transcripts by hand only).
- The reported ledger is kept on the call's `admin.llm_calls` row (muhammad, 2026-10-09; recommended was a server log line and the chat tester caption, with no schema change). muhammad chose the column so a run can be read back days later, which the journal found impossible: `llm_calls` held no reply text and the final ledger showed only the end state. Two columns, `reported_stages` (what the guard kept) and `stage` (what the code stored), because together they tell a misjudged stage from a code fault (runner up: reported only, which leaves the stored stage to be guessed from the reply). Only entries the guard kept are stored, never an unchecked model value (`guards.py`'s rule).
- The columns are written with the message link, not in the turn's transaction (muhammad, 2026-10-09). `link_call` already updates the row on the admin connection after the commit, so no grant changes; writing it inside the turn would need an UPDATE grant on `admin.llm_calls` for `mani_service`, widening the role. The cost is that a failed link loses the stages too, which is already logged.
- No server log line for the stages (muhammad, 2026-10-09): the column holds the same ids and statuses, queryable; the existing notes still log the anomalies.
- The chat tester orders both the caption and the per call list by the framework's `phases`, because jsonb keeps no key order, and shows `turns` only when above 0 so the caption stays readable (runner up: storing an ordered list, which would change the ledger's shape for a display concern).
- **The vague meaning eval runs inside a running ABCDE** (muhammad, 2026-10-09, the third amendment). The first real run of `stages_abcde_vague_meaning` got no offer in 5 messages: ABCDE's Starts when needs what the event came to mean, so a vague meaning never reaches Try It, and AC-13 asked for exactly that. The scenario now starts on `activating_event`, as the stall one does, so the partial `belief` it checks can actually happen. Runner ups: dropping the bullet (the one side of D bullet already covers a partial stage before the offer), or moving it to C (weaker, since C is "felt or did" and either half may count as known).
- Feature 23 (short questions) is its own spec, with the boundary written into *Not in this spec* (muhammad, 2026-10-09; runner ups were both in one run, or folding 23 in). The two rewrite different sentences of the same prompt lines, so neither waits on the other.
