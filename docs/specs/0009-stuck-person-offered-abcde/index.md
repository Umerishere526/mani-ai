# 0009. A person who stays stuck while Mani is understanding is offered ABCDE

**Date**: 2026-10-05
**Status**: In Progress

## Summary

In the October 2026 meeting the client said that when someone in pain cannot get anywhere in the conversation (they keep saying "I don't know" or "I can't think", or it goes round in a loop), Mani should offer ABCDE, because its questions walk them through what is going on one step at a time. This spec makes that happen through the stuck check built in spec 0008: once Mani has asked "Are you feeling stuck?", the model may report a new fact, `stuck`, and that fact alone makes ABCDE fit, but only when no other framework fully fits. On this route ABCDE skips "What happened?" and opens with "What goes through your mind when you feel this?". Pain in the body no longer holds this one offer back. No database change, no new model call.

## Requirements

Linked scope feature: row 41 in [docs/scope/conversation.md](../../scope/conversation.md), "A person who stays stuck while Mani is understanding is offered ABCDE". Source: the client meeting, as muhammad relayed it on 2026-10-05 (journal `questions-easy-to-answer-old-mani-chat-2026-10-05`). It amends spec 0005 (a new fit set, below every other) and spec 0008 AC-4 (the check may now lead to an offer).

**User stories**:
- As a person in pain who cannot put it into words, I want Mani to offer a guided set of questions once I am clearly stuck, so that I am not asked open questions I cannot answer again and again.
- As a person whose pain comes from one thought, I want Thought Reframe, not ABCDE, so that the questions fit what I said.
- As the client, I want the stuck route to follow what I said in the meeting, in every style.

**Acceptance criteria**:
- **AC-1** (the `stuck` fact): `router.FACTS` gains `stuck`, meaning: they keep saying they do not know, cannot think or are stuck in answer to your questions (twice or more, in any order), or they answered yes to "Are you feeling stuck?"; after a no to that check, only once they have said it twice more; quote their longest stuck words. Their words are checked as for every fact and the check is unchanged: at least two words, found in one of their own messages. So someone whose only stuck answers were one word ("idk", "yes") cannot make `stuck`; that limitation is accepted and recorded, not worked around. "Twice more after a no" is the model's judgment; code does not count it. A bare "I don't know" still does not make `unsure_what_to_do`.
- **AC-2** (the check comes first): `router.kept_facts` gains a keyword argument for Mani's messages (default empty, so existing callers and tests keep working) and keeps `stuck` only when one of them, in the history the turn reads (`messages_db.recent_for_context`, 20 messages), contains "Are you feeling stuck" after `safety.normalize` on both sides (so case, curly apostrophes and punctuation do not matter). Otherwise it is dropped with the note "dropped stuck before the check". Every other fact is kept or dropped exactly as today.
- **AC-3** (ABCDE fits on `stuck`, below every full fit): `router.STUCK_FACT = "stuck"`. `abcde.md` `fits_when` becomes `[[event, meaning], [stuck]]`. `router.choose` first looks for a fit through every set that does not contain `STUCK_FACT`, exactly as today, tie rules included; only when none fits does it look at the sets that contain it, and a pick found there sets `Fit.stuck_route = True` (default false). `leading` and `missing` are computed over the sets without `STUCK_FACT` only and stay None on a stuck route pick, so `{stuck}` with ABCDE ruled out leads nowhere. A painful thought still picks Thought Reframe, an action about to happen or a panic now still picks DBT STOP. The Framework Index's "What makes each fit" (`composer.py`) writes a set with `stuck` followed by "(only when no other set fits)". Everything else that limits an offer is unchanged: the earliest offer at their third message, the cooldown after a decline, no offer under `safety: concern`, vetoes, "Never offer one when", and a finished framework not offered again.
- **AC-4** (the offer turn): ABCDE is the `[ctx]` offer candidate when all of these hold: Mani's last message contains the check (normalized, as AC-2); no framework is running (`technique` is None, or declined with its cooldown passed); no safety concern; `context.cooldown_passed`; `context.earliest_offer_ok` for ABCDE; and ABCDE is not in `_not_offerable_now` (vetoed or finished). The candidate's lines are its offering lines plus its stuck branch as `offer_when_stuck`, labelled "only if they answered yes to the check, use this instead of the lines above". `redraft._offer_guidance` uses the same stuck branch when `fit.stuck_route` is true and `event` is not among the facts. The offering stage's `stuck` branch says: one plain sentence that it is hard to put into words right now, then that there are some questions you could go through together, one step at a time; name no feeling and never say "stuck" back. The description and the permission question are added by code, as today. If another framework fully fits, the usual pick rule redrafts the offer.
- **AC-5** (the stuck check line): the `short` bullet of `mani_base.md` ends: "Before any offer, if they cannot think or decide, are confused, or say "I don't know" twice, you may ask exactly "Are you feeling stuck?" once in a conversation, never under `safety: concern`: a check, so the one exception to naming no feeling. A yes may bring an offer; otherwise ask one concrete question about something they said, never a choice of two things." The check is still asked at most once in a conversation (spec 0008). After a no, a later `stuck` makes the offer through the redraft's due offer path.
- **AC-6** (pain in the body): when `fit.stuck_route` is true, `redraft.pain_mentioned` no longer holds back a due offer. `pain_mentioned` matches its words as whole words (today "painful" counts as "pain", which holds back offers it should not). The pain sentence in "Understanding, then offering" ends: "if it is, ask if it has been seen to; only a `stuck` fit may be offered." Every other offer keeps today's body pain hold. The deterministic safety screen still runs first, so "chest pain", "cannot breathe" and the other medical emergency phrases are handled before any framework.
- **AC-7** (ABCDE's first step on this route): when ABCDE starts and the stored words (`technique.known`, written at the offer) hold `stuck` and not `event`, `activate` is passed over: one helper in `techniques.py` (beside `covered_stages`) names the stages passed over with no words, and the start turn in `context._running_lines`, the typed yes path (`offer_waiting`, where `next_stage` becomes `belief`), and the orchestrator's `skipped_stages` (so `repairs` and `registry.clamp` accept `belief` as the reported step) all use it. A passed over stage produces no `already_told` line and no say back. `belief` is then asked through its `stuck` branch: `_stage_lines` shows `stuck.ask` ("What goes through your mind when you feel this?", the same in all three styles) in place of `ask`, and leaves out `stage_if_earlier_missing`, since `activate` was never meant to be answered. When `event` is known the start turn is exactly as today (ADR-015). The later stages and spec 0003's rule that each moves on after any answer, "I don't know" included, are unchanged.
- **AC-8** (free tests): unit tests cover: `kept_facts` drops `stuck` with no check in Mani's messages, keeps it with one, and matches "are you feeling stuck" in any case; `choose` picks ABCDE on `{stuck}` with `stuck_route` true and no `leading`, Thought Reframe on `{stuck, painful_thought}`, DBT STOP on `{stuck, about_to_act}`, ABCDE through `event, meaning` with `stuck_route` false on `{event, meaning, stuck}`, and nothing with no `leading` when ABCDE is excluded; the composer writes "(only when no other set fits)" after the stuck set; the `[ctx]` offer candidate appears on the turn after the check and not on their second message, not with ABCDE vetoed or finished, and not while a framework runs; the start turn, tapped and typed, with `known` `{stuck}` asks the stuck line with no `already_told` and no `stage_if_earlier_missing`, and with `event` known is as today; a reported `belief` on that turn is not corrected back to `activate`; a due ABCDE offer on the stuck route is asked for with pain mentioned, any other due offer is not, and "painful" alone holds nothing. `tests/unit/test_authored_questions.py` covers the new `belief` branch with no change to it (the offering stage stays out of that test). One integration test runs whole turns with a scripted model: the check asked, "yes" sent, `stuck` reported and ABCDE offered, the offer kept, then "Try it" answered with "What goes through your mind when you feel this?".
- **AC-9** (eval scenarios): `scripts/eval_conversations.yaml` gains `stuck_body_pain` (pain in the body, two stuck answers of two words or more, a yes to the check, "Let's try it" typed, then short answers to the ABCDE steps). `depressed_alone` and `stuck_body_pain` gain `expect_offer: abcde`, which `eval_replies._score` compares with the framework part of `_first_offer` (its "message:framework" string), reporting a `journey` finding when the first offer is another framework or never comes.
- **AC-10** (the real model, after muhammad says yes): folded into spec 0008's AC-9 run: `idiot_concert_direct`, `depressed_alone` and `stuck_body_pain`, each style, one run each (9 conversations), after muhammad says yes and credit is checked. The bar for this spec: in `depressed_alone` and `stuck_body_pain` the first offer is ABCDE, it comes after "Are you feeling stuck?" in at least two of the three styles, and when accepted the first framework question is the stuck line; in `idiot_concert_direct` the offer is still ABCDE through `event, meaning` (no stuck route). muhammad reads the offers and the first ABCDE replies. Until this run, AC-4 to AC-7 count as built but unverified on the model.
- **AC-11** (records and a clean suite): `python scripts/seed.py` is run after the content edits; the base prompt body stays at 118 lines or fewer (`tests/evals/test_base_prompt.py`), the two edited paragraphs reflowed at 100 characters with "Are you feeling stuck?" kept on one line; `pytest` passes with clean output; `backend/PORT-STATUS.md`, ADR-018 (a stuck person is offered ABCDE) with its index entry, and a journal entry record the change in the same work.

## Decision

**Chosen option**: Option 1: a `stuck` fact the model reports, kept only after the check, fitting ABCDE below every other fit.

The model judges when someone is stuck and says so through a new fact; code makes the check a hard precondition, places the stuck fit below every full fit, carries ABCDE's offer lines into `[ctx]` on the turn the check is answered, and starts ABCDE at its second step with a plain question.

**Implementation skills**: none installed apply (backend code, framework content and prompt text; no frontend or database change).

## Feature design

**Data model sketch**: none new. No migration. `stuck` and its quoted words are stored in `thread_technique_state.known` at the offer, like every other fact (migration `012`); that is what the start turn reads.

**State transitions**: none new. Offered, accepted, declined, the cooldown, stage tracking and holds are as today (spec 0003, ADR-015).

**API surface**: none. No endpoint changes; replies keep their shape (`Reply.facts` already carries any fact id the router defines).

**Value sourcing**:
| Action | Value produced / displayed | Source |
|---|---|---|
| Understanding turn | Whether to ask "Are you feeling stuck?" | the model, under the base prompt's stuck check line (spec 0008, AC-5 here) |
| Understanding turn | The `stuck` fact and its words | the model's `Reply.facts`, its meaning from `router.FACTS["stuck"]` (AC-1) |
| Fact check | Whether the check has been asked | Mani's messages in `messages_db.recent_for_context` (20 messages), passed to `kept_facts`, searched for "Are you feeling stuck" after `safety.normalize` (AC-2) |
| Fit | The pick and `stuck_route` | `router.choose` from the kept facts and each framework's `fits_when`: sets without `STUCK_FACT` first, sets with it only when none fits (AC-3) |
| Prompt | How the stuck set is described | `composer.py` "What makes each fit", with "(only when no other set fits)" after a set containing `stuck` (AC-3) |
| Offer turn after the check | ABCDE as the offer candidate | Mani's last message contains the check (normalized), no framework running or a declined one past its cooldown, no safety concern, `context.cooldown_passed`, `context.earliest_offer_ok`, ABCDE not in `_not_offerable_now` (AC-4) |
| Offer | Mani's part of the offer on this route | the offering stage's `stuck` branch in `abcde.md`, seeded, shown as `offer_when_stuck` on the candidate turn and used by `redraft._offer_guidance` when `fit.stuck_route` is true and `event` is not among the facts (AC-4) |
| Offer | Description and permission question | `framework.summary` and `repairs.PERMISSION_QUESTIONS`, unchanged |
| Due offer with pain mentioned | Whether the pain hold applies | `fit.stuck_route`: false holds as today, true does not; pain read as whole words by `pain_mentioned` (AC-6) |
| ABCDE start turn, tapped or typed | Whether this is the stuck route, and which stages are passed over | `technique.known` holds `stuck` and not `event`; the passed over helper in `techniques.py`, used by `context._running_lines` and the orchestrator's `skipped_stages` (AC-7) |
| ABCDE start turn | The first question | `belief.stuck.ask` in `abcde.md`, seeded: "What goes through your mind when you feel this?", with `stage_if_earlier_missing` left out (AC-7) |
| Eval scoring | Whether the first offer was ABCDE | the framework part of `eval_replies._first_offer`, compared with the scenario's `expect_offer` (AC-9) |

**Key invariants**:
- `stuck` never survives the fact check unless "Are you feeling stuck?" is in Mani's messages the turn reads.
- A fit through `stuck` alone never beats a full fit of any other framework, and never bypasses the earliest offer, cooldown, safety, veto or contraindication rules.
- The pain hold is lifted only for a fit whose `stuck_route` is true.
- When `event` is known, the ABCDE offer wording and start turn are unchanged; the stuck wording and the pass over need `stuck` known and `event` absent.
- A passed over stage never produces an `already_told` line or a say back.
- No new model call: the candidate lines go into the one call, and a redraft happens only for the reasons that exist today.

**Security model**: unchanged. No new data is stored beyond the fact words `known` already holds, which are the person's own message text inside their own thread (RLS as today). The safety screen runs before any of this. Eval transcripts are health data and stay in the gitignored `backend/.eval/`; the paid run uses the existing zero data retention route.

**Configuration required**: none.

**Edge cases**:
- The model reports `stuck` before the check was ever asked: dropped with its note, no offer (AC-2).
- The check has scrolled out of the 20 messages the turn reads: `stuck` is dropped from then on. Accepted; a conversation that long has other facts to fit on.
- They say yes to the check at their second message: no candidate lines that turn (ABCDE's earliest is their third message), and Mani asks one concrete question; the due offer comes on a later turn.
- They say no to the check: the candidate lines carry "only if they answered yes"; Mani asks one concrete question.
- Their only stuck answers were one word ("idk", "yes"): no valid quote, `stuck` is dropped, no offer. Accepted limitation (AC-1).
- They named an event but no meaning, then say yes to the check: ABCDE fits through `stuck` and the pain hold lifts, but the offer uses the normal offering lines and the start turn says back the event and asks the normal `belief` question.
- They type "Let's try it" instead of tapping: the same pass over applies, and the first question is the stuck line (AC-7).
- They say yes but declined an offer recently: the cooldown holds, no offer, one concrete question (AC-5).
- They say yes and have also named a painful thought: Thought Reframe is the pick (AC-3).
- They say yes and an action is about to happen, or they are panicked now: DBT STOP (AC-3).
- They say no, then say "I don't know" twice more: `stuck` reported, ABCDE offered through the due offer redraft, no second check (AC-5).
- They describe abuse, threats or danger: ABCDE's contraindication in "Never offer one when" holds, no offer.
- Pain in the body plus stuck: ABCDE may be offered (AC-6); chest pain or "cannot breathe" is a medical emergency for the safety screen first.
- Inside ABCDE they keep saying "I don't know": each step moves on (spec 0003), and the steps with an earlier answer question use it; they reach the short summary and the body check.
- They tap Keep chatting: declined, cooldown as today; after it `stuck` can make the offer again.

**Critical test scenarios**:
- Happy path: check asked, "yes", `stuck` reported, ABCDE offered with the stuck line, "Try it", first question "What goes through your mind when you feel this?", verifies **AC-1**, **AC-2**, **AC-4**, **AC-7**.
- Precedence: `{stuck, painful_thought}` picks Thought Reframe and `{stuck, about_to_act}` picks DBT STOP, verifies **AC-3**.
- Failure case: `stuck` reported with no check in history is dropped and nothing is offered, verifies **AC-2**.
- Pain: a due ABCDE offer on the stuck route is asked for with "my back hurts" in the conversation; a due Structured Problem Solving offer is not, verifies **AC-6**.
- Event known: the start turn with `known` `{event, stuck}` says back the event and asks the normal belief question, verifies **AC-7**.
- Real model: the nine conversations of AC-10, verifies **AC-4** to **AC-7**, **AC-10**.

## Build plan

Ordered as a thin thread first (Tracer Bullet): the fact, the fit and the start turn work end to end on unit and integration tests before the prompt is tuned and the paid run is asked for.

1. `router.py`: `stuck` in `FACTS` and `STUCK_FACT`; `kept_facts` takes Mani's messages (default empty) and gates `stuck` on the normalized check; `choose` looks at sets with `STUCK_FACT` only when no other set fits, sets `Fit.stuck_route`, and keeps `leading` and `missing` blind to them; `composer.py` writes "(only when no other set fits)"; unit tests. Satisfies **AC-1**, **AC-2**, **AC-3**.
2. `abcde.md`: `fits_when` gains `[stuck]`; the offering stage gains its `stuck` branch; `belief` gains its `stuck` branch with the one line; a comment beside `not_when` noting the stuck route. Seed. Satisfies **AC-3**, **AC-4**, **AC-7**.
3. `techniques.py`: the passed over helper. `context.py`: the `stuck` branch in `_stage_lines` (`offer_when_stuck`, and `stuck.ask` in place of `ask` with no `if_earlier_missing` on a passed over start), the start turn and the typed yes path using the helper. `orchestrator.py`: Mani's messages into `kept_facts`, ABCDE as the gated candidate on the turn after the check, `skipped_stages` from the helper. `redraft.py`: `_offer_guidance` uses the stuck branch, the pain hold skips a `stuck_route` fit, `pain_mentioned` matches whole words. Unit tests and the integration test. Satisfies **AC-4**, **AC-6**, **AC-7**, **AC-8**.
4. `mani_base.md`: the stuck check line and the pain sentence exactly as AC-5 and AC-6 give them, the two paragraphs reflowed, body at 118 lines or fewer; extend `test_base_prompt.py`; seed again. Satisfies **AC-5**, **AC-6**, **AC-11**.
5. `eval_conversations.yaml`: `stuck_body_pain`, `expect_offer` on it and on `depressed_alone`; `eval_replies._score` checks `expect_offer` on the framework part of `_first_offer`; ADR-018 and its index entry, `PORT-STATUS.md`, the journal; full `pytest`. Satisfies **AC-9**, **AC-11**.
6. After muhammad says yes and credit is checked: the nine conversation run shared with spec 0008 AC-9, the read, the figures in the journal. Satisfies **AC-10**.

## Consequences

**Positive**:
- Someone who cannot put their pain into words gets a guided set of questions instead of more open ones, as the client asked.
- The check makes the offer something the person confirmed, and code guarantees the order (check, then offer).
- No new model call, no migration, and the fact machinery of spec 0005 is reused unchanged.

**Negative / tradeoffs**:
- It goes against the client's written overview ("stuck" is listed under Behavioral Activation) and ABCDE's own "when not to use" list (an unclear issue, a person who cannot answer reflective questions). It rests on the meeting, which nobody has written down.
- ABCDE's steps ask what they told themselves and what supports it. A person who cannot think may answer "I don't know" at each step and reach the body check with little; spec 0003 moves on regardless.
- The model's fact marking is not reliable on the current model (row 35's finding); a missed `stuck` means no offer, an over marked one is still held by the check.
- Lifting the body pain hold for this route means ABCDE can be offered to someone with a physical problem; the safety screen covers emergencies only, not every medical case.
- The ABCDE description the code adds ("look at what happened, what you took it to mean...") assumes an event the stuck person may not have named; row 6 owns that text.
- One more `[ctx]` candidate path beside DBT STOP's, one more branch shape (`stuck`) beside `panic`, and a second way a stage can be skipped (passed over with no words, beside credited with words).
- A person whose only stuck answers were one word cannot reach the stuck route, because the words check needs two words; the check would then be asked and answered with nothing offered.

**Neutral**:
- Spec 0005's rule that only a full fit is offered still holds: `[stuck]` is a full fit of a new set.
- Spec 0008 AC-4's "nothing is offered because of the check" no longer holds; its other rules (asked once, never under a safety concern, never an either/or) stay.

## Follow-up

- [ ] Ask the client to confirm the stuck route in writing, since it differs from their overview (Behavioral Activation for "stuck") and from ABCDE's "when not to use" list.
- [ ] Row 6: ABCDE's description and its offering stage wording for a person who named no event.
- [ ] Records this makes stale, for `/sync` to flag: spec 0008 AC-4 ("nothing is offered because of the check"), ADR-014's list of fit sets, and ABCDE's `not_when` documentation.
- [ ] Tell the client the body pain hold no longer applies on this route.

## Rationale

Reasoning and options: see [rationale.md](rationale.md).
