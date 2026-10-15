# MANI conversation flow: what changed, how the chat works now, and what is still open

Date: 2026-10-13. Branch: `feat/abcde-framework-revamp`. **Nothing is committed**: every change below is in the working tree (HEAD is `c2470fd`). Companion documents: the audit and plan in `2026-10-13-mani-conversation-flow-audit.md`, the journal note `mani-vault/Journal/conversation-flow-like-the-reference-chat-2026-10-13.md`.

---

## 1. What was asked, in one paragraph

Make MANI chat the way Lolly experienced the ChatGPT conversation about workplace frustration. It listens, asks questions that find the core of what is going on, names the pattern it sees, and only then offers a framework (ABCDE is the only one for now). A framework fitting is not a reason to offer it. The model decides when the person is ready, not a message count. If the person keeps chatting, Mani comes at the same situation from another angle and may offer again later. If someone says "just tell me what to do", Mani says it cannot hand over a solution but can help work it out, and asks a question that leads there.

## 2. What was done, by change

| # | Change | Why | Where |
|---|---|---|---|
| 1 | A typed question while an offer is open is no longer treated as "asking about the offer". It counts only when the model's own reply reports the open offer with `accepted` left empty. Anything else is Keep chatting. | Before, any message containing `?` re-attached the ABCDE offer. "Can we just work out what to do?" got ABCDE offered again. | `mani/chat/orchestrator.py` (`_asked_about`) |
| 2 | A stage asked twice is not asked a third time in the text the person reads. The recorded stage moved on before, but the reply still asked the old question. Now the reply asks the next stage's question, and a draft that stays gets one redraft first. | The 2026-10-12 "no third ask" rule only changed bookkeeping. | `mani/chat/redraft.py` (`reasons`), `mani/chat/repairs.py` (`apply`) |
| 3 | Readiness to offer is the model's explicit choice, `next_move` (`ask`, `acknowledge`, `offer`, `answer_request`), filled in before the reply text. The count floor (offer no earlier than message 3), the forced "closest fit" offer (message 4 or 6) and `offer_fit` are removed. The only counts left: no offer in the Keep chatting reply or the two after it, and 45 messages after a finished framework. | A count was deciding the offer. Fit and readiness were the same decision. | `mani/llm/schema.py`, `mani/chat/context.py`, `mani/chat/redraft.py`, `mani/chat/orchestrator.py`, `content/frameworks/abcde.md`, `content/prompts/mani_base.md`, `content/prompts/response_format.md` |
| 4 | How Mani talks before an offer was rewritten. It finds the core issue so the person thinks "yes, that is it". Either/or questions are allowed. It may say its understanding for the person to confirm. It never offers in its first reply, even when the first message holds the whole story. A reply may skip the question only when any question would be unreasonable. The offer opens with two or three sentences naming the pattern, then the client's ABCDE line and "Would you like to try it?". After Keep chatting it comes from another angle. "Tell me what to do" gets "I can't hand you a solution, but I can help you work it out" plus a question. | muhammad's decisions after Lolly's ChatGPT example. | `content/prompts/mani_base.md`, `content/prompts/response_format.md`, `_MEANING` strings in `mani/chat/context.py`, the `heading_toward` description in `mani/llm/schema.py` |
| 5 | Scenarios for the matrix of situations, including Lolly's conversation (`reference_frustration`). | To measure before and after. | `scripts/scenarios.json` |
| 6 | The 2026-10-12 work that was already uncommitted stays: `stage_asks` counter, `stage_asked` in `[ctx]`, `said_before_yes`, the debug ledger fallback. | Built earlier; this work builds on it. | `supabase/migrations/011_technique_stage_asks.sql`, `mani/db/threads.py`, `mani/models/rows.py`, `mani/chat/context.py` |

## 3. Files touched (22 modified, 4 new, nothing committed)

**Runtime code**
- `backend/mani/chat/orchestrator.py` readiness gates removed, `_asked_about`, `may_offer`, cooldown wiring
- `backend/mani/chat/context.py` count gates removed, new `[ctx]` meanings, cooldown 4 after decline
- `backend/mani/chat/redraft.py` `next_move` checks, asked-twice note, closest-fit and earliest-wait checks removed
- `backend/mani/chat/repairs.py` replaces a third ask with the next stage's question
- `backend/mani/llm/schema.py` `next_move` added, `offer_fit` removed
- `backend/mani/db/threads.py`, `backend/mani/models/rows.py` the `stage_asks` counter (from 2026-10-12)

**Content (what the model reads; changes nothing until `python scripts/seed.py`)**
- `backend/content/prompts/mani_base.md`, `backend/content/prompts/response_format.md`
- `backend/content/frameworks/abcde.md` (`earliest_offer_message` removed)
- `backend/content/prompts/memory_fold.md`, `backend/content/prompts/summarization.md` (2026-10-12 edits)

**Database**
- New: `backend/supabase/migrations/011_technique_stage_asks.sql` (adds `thread_technique_state.stage_asks`)
- `backend/docs/database-schema-reference.md` (documents it)

**Tests**
- `backend/tests/integration/test_turn.py`, `tests/unit/test_chat_context.py`, `test_redraft.py`, `test_repairs.py`, `test_composer.py`, `test_chain.py`
- Removed tests were about removed gates only (earliest offer, closest fit due, `offer_fit`). New tests cover `next_move`, the Keep chatting cooldown, a first-message offer, a typed request, and the third ask.

**Docs and tooling**
- `backend/PORT-STATUS.md` decisions edited in place; `backend/scripts/scenarios.json`; `chat-tester/app.py` (2026-10-12 edit)
- New notes: the audit/plan, this document, two journal notes under `mani-vault/Journal/`

## 4. Does the backend or the database need changes?

**Backend code: no further changes are required for this work.** Full `pytest` was 447 passed, 4 skipped (the 4 are the known JWKS-token skips) after Task 5, and the Task 6 fix round re-ran the unit suite at 350 passed, 4 skipped.

**Local database (checked now):**
- `thread_technique_state.stage_asks` exists (smallint, default 1). ✔
- Only one framework is active: `abcde`. ✔
- Prompts are seeded (`mani_base`, `response_format`, `summarization`, `memory_fold`, `title_generation`). Seeding was run after the last content edit. ✔
- **One thing to know:** the local migrations table stops at `010`, even though the `stage_asks` column exists. It was applied outside the migration runner. A `supabase db reset` applies `011` properly. Nothing else in the schema changed.

**Hosted/production database: changes ARE required before this code runs there, and I did not touch it:**
1. Run `supabase db push` so migration `011` creates `stage_asks`. Without it, every turn's write to `thread_technique_state` fails.
2. Run `python scripts/seed.py` against it so the prompts and `abcde.md` match. The old rows still carry the count floor and `offer_fit` wording.
3. Deploy the code in the same window as steps 1 and 2. New code with old content, or old code with the new column, is a mixed state.

## 5. How a chat reply works right now (flow and decision points)

```
Person types a message
        │
        ▼
POST /v1/threads/{id}/messages            mani/routers/threads.py
        │  JWT verified, user id from token only
        ▼
orchestrator.send                          mani/chat/orchestrator.py
 │
 ├─ 1  same client_message_id seen?  ─yes─► return the stored reply (no model call)
 ├─ 2  lock this thread (one turn at a time)
 ├─ 3  thread crisis-locked?  ─yes─► 403 "conversation is paused"
 ├─ 4  load: last 20 messages, summary, memory, thread state (framework row, styles used)
 ├─ 5  message is a style button (Direct/Supportive/Reflective)?
 │        ─yes─► fixed opening question, style saved on the thread, NO model call
 ├─ 6  framework finished last turn? ─► retire it (45-message cooldown starts)
 ├─ 7  did they tap a button?  Try it ─► accepted | Keep chatting ─► declined
 │        typed message while an offer is open ─► "deferred" (decided after the model replies)
 │
 ├─ 8  SAFETY SCREEN (deterministic phrases, no model, every turn)
 │        CRISIS  ─► lock thread, fixed safety text, STOP (no model call)
 │        CONCERN ─► this turn: no offer, no stage question, stay with them
 │
 ├─ 9  build the prompt
 │        system:  mani_base + Framework Index + response_format + profile + memory + summary
 │        history: last 20 messages
 │        user:    [ctx] block + their message
 │                 [ctx] says: style, phase (understanding | framework | talking),
 │                 cooldown_passed yes/no, offer waiting, stage + next stage if a framework runs,
 │                 stage_asked twice, said_before_yes, recent openers
 │
 ├─ 10 MODEL CALL (one), structured reply, in this order:
 │        reasoning → style → heading_toward → next_move → stages_known → text → buttons → state
 │
 ├─ 11 CHECKS that can send it back for ONE redraft (a second model call):
 │        • offer button but next_move is not "offer"
 │        • next_move "offer" but no Try it button (when an offer is allowed)
 │        • offer not allowed now (cooldown after Keep chatting) 
 │        • offer after what they said rules it out (vetoes)
 │        • no question and the draft did not choose "acknowledge" or a no-question shape
 │          (two redrafts allowed for this one)
 │        • the same question as last turn
 │        • inside a framework: state.step disagrees with its own ledger,
 │          or it stays on a stage already asked twice
 │
 ├─ 12 typed answer to an open offer?
 │        accepted:true ─► framework starts   |  asked about it (accepted left empty) ─► offer stays open
 │        anything else ─► Keep chatting (offer declined)
 │
 ├─ 13 REPAIRS in code (no model call):
 │        strip leaked script text and internal words; their name at most once
 │        build the offer: Mani's part + client's "Would you like to try it?" + Try it / Tell me more / Keep chatting
 │        drop any button that is not allowed; validate framework id and stage
 │        stage asked twice and the reply still stays ─► move to the next stage AND ask its question
 │
 ├─ 14 safety concern on this turn? ─► strip offers and stage changes (framework paused, not ended)
 ├─ 15 framework running? body check-in / practice / Chat More + Go to Library handled in code
 │
 ├─ 16 write: both messages, framework row (stage, ask count), styles used, title  (one transaction)
 ├─ 17 framework just finished? ─► one small second model call picks an exercise
 └─ 18 more than 20 messages since the last summary? ─► summary refreshed in the background
        │
        ▼
Reply + buttons returned (buttons only on the newest Mani message)
```

### Where the decisions are made

| Decision | Who decides | Where |
|---|---|---|
| Is this a crisis? | Code (phrase screen) | `mani/chat/safety.py` |
| What does Mani understand about them? | Model, from the last 20 messages plus summary | prompt only; not stored as state |
| Does ABCDE fit? | Model (`heading_toward`) | prompt |
| Is it time to offer? | **Model (`next_move`)**. Code only blocks it in the cooldown after Keep chatting, after a crisis concern, or when what they said rules it out | `schema.py`, `redraft.py`, `context.py` |
| Ask a question, or acknowledge only? | Model (`next_move`); code asks again if it chose neither | `redraft.py` |
| Did they accept or decline? | Their tap, or the model reading their typed reply | `orchestrator.py` |
| Is a stage's purpose met, so Mani moves on? | Model (`stages_known`); code caps any stage at two asks | `redraft.py`, `repairs.py` |
| Which stage is recorded? | Code, checked against the framework's allowed order | `techniques.py` |
| How Mani sounds | The style they picked (`[ctx]` + `mani_base.md`) | prompt |

### How the three styles are carried
The style lives on the thread (set by tapping Direct, Supportive or Reflective, or from the profile). It goes into `[ctx]` every turn, into the stage note inside a framework, into the offer wording, and into the body route. It changes how Mani talks, not when it offers. It no longer changes any count either, because the count was removed.

## 6. Measured effect (live model, three runs per scenario and style)

Baseline (before Task 5), then after Task 5. The post-Task-6 runs are in section 7.

- Before: nearly every conversation offered ABCDE at exactly their message 3, which was the count floor. `practical_request` never offered.
- After Task 5 (no floor, no forced offer): offers moved with the situation. `reference_frustration` (Lolly's conversation) now offers at messages 4 to 6. Some conversations never offer in the scenario length. But on messages that already held the whole story, 12 of 36 runs offered at message 1. That conflicted with "gather more insight first", so Task 6 added the rule that Mani never offers in its first reply.

## 7. After Task 6 (what the new prompt text does)

Message number at which the first offer came, across all runs (each scenario is 3 to 6 person messages long, so "no offer" can also mean the scripted chat ended first). The baseline had 9 scenarios, the later two had 12, so compare shares, not totals.

| | runs | no offer | at message 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|---|
| Before (count floor at 3) | 81 | 9 | 0 | 0 | 62 | 10 | 0 | 0 |
| After Task 5 (model decides) | 108 | 28 | 17 | 12 | 26 | 14 | 9 | 2 |
| After Task 6 (core first, never in first reply) | 108 | 46 | 2 | 16 | 17 | 19 | 7 | 1 |

What this shows, and what it does not:
- Offers are no longer pinned to message 3, and they follow the conversation. Lolly's conversation (`reference_frustration`) now offers at messages 4 to 6 in all three styles, close to her ChatGPT example (message 6).
- First-message offers fell from 17 of 108 to 2 of 108. The prompt rule helped but did not fully hold, as flagged in section 8 item 3.
- More conversations end without an offer (46 of 108). Two scenarios (`left_out_of_meetings`, `practical_request`) never offered in any run. Whether that is right is a product call. `practical_request` is meant not to offer (no problem-solving framework exists yet), but `left_out_of_meetings` is the exact kind of event ABCDE was built for, so check why it holds off.
- Every reply before an offer still asked a question (0 without one in 309). The "acknowledge without a question" path was never used in these runs.

What the replies look like, from the `reference_frustration` runs (Direct):
- Questions are grounded in what the person said, with no either/or choices used and no restating of their whole sentence.
- Some questions are still generic ("What's been getting to you most?", twice in one Direct chat) and one asks about "today" when the person never said today.
- The offer's opening is one sentence naming the pattern ("people not following through leaves you dealing with the extra work"), not the three or four sentences in Lolly's example. If you want the longer pattern reflection, that is a prompt change to the `offers` rule.
- 14 automatic flags across the runs (restating, internal words, a repeated question). Not broken down here.

## 8. What still needs a decision or more evidence

1. **Not measured for tone.** Counts of offers are measured; whether replies actually read like Lolly's ChatGPT chat is a reading task. Please read the three runs of `reference_frustration` in all three styles. The transcripts are in the session scratchpad (`after6_*.json`).
2. **Either/or questions** are allowed freely. The journal records that menus at message 1 once made Direct read as "a questioning jerk" (2026-10-10). The prompt now keeps them grounded in what the person said and forbids them only where a question would be unreasonable. Say if you want them limited.
3. **"Never offer in the first reply"** is a prompt rule, not code. The model can ignore it. If the post-Task-6 runs still show first-message offers, the next step is a small code check that drops a first-reply offer. That would be a count rule, so it needs your OK.
4. **Re-offer after Keep chatting:** the rule is "not in that reply or the next two". Whether the model re-offers too soon or never is unmeasured. The scenario that tests it does not exist yet (the runner stops at the first offer).
5. **"Tell me what to do"** while Structured Problem-Solving stays paused: Mani answers with "I can't hand you a solution but can help you work it out" and a question. Whether the client accepts that wording is theirs to say.
6. **Typed carry-on that re-offers with `accepted` left empty** is read as "asked about the offer", so it stays open instead of being declined. This depends on the model reporting `accepted: false` when it is carrying on. Worth an eval.
7. **Understanding is not stored.** The model re-derives it every turn from the last 20 messages and a short summary. No evidence yet that this loses context inside 20 messages. If it does, a stored list of what the person has said and confirmed is the next step.
8. **Hosted database and deploy order** (section 4) is yours to schedule. I have not touched hosted.
9. **Commits:** nothing is committed or pushed, as you asked. The work exists only in the working tree. Back it up or commit it when you decide.
10. **Docs drift worth fixing later:** `PORT-STATUS.md` "Status, 2026-10-01" still says `mani_base` runs at reasoning effort `high`, but the file now says `low`. The `abcde.md` footer still says each letter is named in the chat, which contradicts the 2026-10-09 decision.
