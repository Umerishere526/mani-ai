# 0004. The ABCDE walk and its memory: rationale

The decision record behind [index.md](index.md).

## Context

Lolly tested two chats on 2026-10-12 ([message](../../client/messages/2026-10-13-two-versions-confusion.md)). Version A (ours) talked more naturally. Version B (the colleague's `feat/abcde-framework-revamp`) seemed better at remembering what she had already said. She also found that once ABCDE starts, Mani does not explain what A to E stand for or walk through them as her ABCDE document defines. That gave two requirements: R6 (once the framework begins, remember what they explained) and R12 (introduce each letter and its name as the stage is reached, use what they said, ask only what is missing).

The architecture review of 2026-10-13 found that neither version stores anything per stage. Every turn the model rebuilds `stages_known` from the last 20 messages (`db/messages.py` `CONTEXT_WINDOW`) and the Conversation Context summary. The ledger is used once, to correct `state.step` (`reply_checks.with_ledger_step`), and then it is thrown away. `TechniqueState` holds only `phase`. B felt better because it paid more per turn: a second call when the ledger and the step disagreed, effort `high`, and questions built from the person's words. We cut all three on purpose for R2 (latency) and R3 (ornate reworded questions). Copying B would undo R2.

Two decisions in force stand in the way of R12. "The chat never names a stage" (muhammad, 2026-10-09) was made after a manual test where labels were written into replies and a Not sure button skipped C and D. "A stage their words already answer is skipped, with no check and no mention" (2026-10-09) contradicts the document's three cases for A (known, possible, missing). muhammad agreed on 2026-10-13 that the client's newer message reverses both.

There is also a defect. `with_ledger_step` sets the stored step from the ledger without touching the text, so the stored step can name a stage the person was never asked. Any design here must keep one chat call at effort `low` (a Decision in force), and must not move judgments of meaning into phrase lists (also in force).

## Options considered

### Option 1: Restore Version B's approach

A second call or a higher effort, and questions built from their words, so the model remembers better within one turn.

**Pros**:
- It is known to feel better to the client.

**Cons**:
- It undoes R2 (one call at `low`) and R3 (plain client questions).
- It still stores nothing, so anything past 20 messages is lost anyway.

### Option 2: A stage store owned by code, with a one stage walk that code steps (chosen)

The model reports only what changed this turn and how they answered the stage in force. Code merges the report into a column, steps one stage, and renders the letter line and the client's lines.

**Pros**:
- The memory survives the window at no extra call.
- The letter lines are exact.
- The step can never disagree with the question.
- The store is keyed by framework, so a paused framework can use it later. The walk itself is ABCDE's, because only its stages have an `intro`.

**Cons**:
- It adds a migration and a merge with rules to get right.
- Confirming each known stage costs turns.
- The model still has to write the right kind of `text` for the stage code will pick, and it cannot be corrected without a second call. That gets logged.

### Option 3: Store the ledger, but keep the model's skipping walk

Persist today's `stages_known` and keep the model choosing `state.step`, possibly several stages ahead.

**Pros**:
- It is the smallest change, and fast when much is known.

**Cons**:
- It keeps the step and text disagreement.
- It conflicts with one stage per reply.
- It cannot place a letter line per stage without restructuring the reply anyway.

## Rationale

The force that decides this is R2 against R6. The memory has to get better without paying per turn. Only a store held by code does that, so Option 1 is out. Option 3 stores the memory but leaves the model owning the step, which is the source of the step bug and makes per stage letter lines impossible to place reliably.

The walk choices were muhammad's, on the 2026-10-13 panel:
- **One stage per reply, and a known stage confirmed once.** The runner up was the document's chain (name each known stage and go on to the first gap). muhammad chose one per reply so every reply ends on a question and the person can correct each stage. It departs from the document's Situation 1, so it is recorded as a conflict and the client is to be told.
- **Code places the letter line, and A uses the client's own templates.** The runner up was the model writing the rest of each stage, which risks R3 drift on the only stage where the client wrote exact lines.
- **The model writes only the naming sentence for B to E.** The client wrote no known case wording for those.
- **Confirm phrases from a pool of four, never repeating the previous stage's.** muhammad asked for variety. The runner up was one phrase in every style.
- **The letter line only on the first reply of a stage.** The runner up was every reply, which repeats.
- **A no with new words is the answer, and the walk moves on.** The runner up was confirming again, which is a second confirm on one stage (R5).
- **A correction to an earlier stage updates the words without going back.** The runner up was going back, which asks again for stages already passed.
- **Only the changes this turn are reported.** The runner up was the full ledger every turn, which costs more output and lets the model drift stored words.
- **A typed `stage_answer`, with code moving one stage.** The runner up was the model setting the step and code checking it, which keeps the disagreement bug.
- **A jsonb column on the technique row, keyed by framework, kept for the thread.** It rides the turn's existing single read and upsert. The runner up was a new table with one row per stage, which needs RLS, grants and an extra round trip for at most five rows. muhammad chose thread lifetime over one run; the cost is not clearing it at retire.

After the cross check (another model, 2026-10-13), muhammad decided three more:
- **No acknowledgement when the walk moves on.** The reply is the letter line and the next question. It follows the client's B to E examples and R3. The runner up was one short sentence after the letter line.
- **Only A has `possible`.** For B to E, a likely but unsaid answer is treated as missing and asked, so Mani never says back words they did not give. The runner up was a hedged confirm sentence.
- **A code backstop at two `not_yet` in a row** (a `tries` count in the store). One confirm per stage creates a new loop risk, which the model's reading alone does not bound. The runner up was logging the streak only.

The other cross check findings were applied as recommended (muhammad, 2026-10-13):
- the start turn is read from the row;
- `stages_known` is written by its own statement, never by the shared upsert;
- BODY carries the stage fields on the closing stage;
- a two branch `text` line in `[ctx]`, with fallbacks for text that does not fit its case;
- `said` is capped and disarmed;
- a new start clears the framework's entry;
- the latest words win on the stage in force;
- `let_go` is split from `answered`;
- a confirm phrase formula that guarantees neighbouring stages differ;
- structural validity rules for `stage_answer`;
- the turn order of operations;
- the full list of files and tests the build touches.

Calls made in writing the spec:
- **The feeling word for A missing comes from a `feeling` field on the start turn.** The client's Situation 3 line needs it and nothing stores it. The runner up was always using `activate.ask`, which drops the client's wording whenever a feeling was named.
- **The confirm phrase is chosen by a fixed formula from the thread id and stage position.** muhammad's "random" holds per thread, a test can predict it, and neighbouring stages never repeat. The runner up was a true random pick, which no test can assert.
- **A run in progress at deploy time continues with an empty store.** The runner up was a backfill from history, which would need a model call per thread for a few test threads.
