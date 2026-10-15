# MANI Conversation Flow — Audit and Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. muhammad answered D-1 to D-7 on 2026-10-13; the answers are in Part 2, "Decisions", and Part 2 is written to them.

**Goal:** Separate "do I understand them", "does a framework fit", "is now the moment to offer" and "is this stage's purpose met" in MANI's backend, so a framework that fits no longer ends open chat by itself, turn counts stop forcing offers, and a reply may move forward without a question when that is the right move.

**Architecture:** Keep the existing one-call turn (`orchestrator.send` → `context.build` → `client.complete(Reply)` → `redraft.reasons` → `repairs.apply` → writes). Add one schema field chosen before `text` (`next_move`) so readiness becomes an explicit, checkable decision rather than a consequence of fit plus a turn count; move the deterministic gates (`redraft`, `repairs`) to check that field instead of guessing from `?` and button presence. No new model call, no new table, no embeddings.

**Tech Stack:** FastAPI on Python 3.14, asyncpg on Supabase Postgres, LangChain structured output over OpenRouter (`openai/gpt-6-luna`), pytest (`filterwarnings = error`), `scripts/scenario_check.py` for live evaluation.

**Spec:** the audit brief pasted in the 2026-10-13 session (sections 1–17), plus the reference conversation muhammad attached (a ChatGPT exchange on workplace frustration that ends with "INTRODUCE FRAMEWORK"). Decisions in force: `backend/PORT-STATUS.md` → "Decisions in force".

## Global Constraints

- No framework is offered on the strength of a turn count alone (brief §3, §17).
- No question is asked only to fill a field (brief §4.8, §17).
- Fit does not imply an immediate offer; more exploration is not assumed useful (brief §3, §17).
- No count floor and no forced offer: the model decides readiness through `next_move` (muhammad, 2026-10-13). The only count left is the cooldown after Keep chatting (no offer in that reply or the two after it) and after a finished framework.
- No AI attribution lines (`Co-Authored-By` or similar) in commit messages, ever (muhammad's standing rule).
- Framework start requires consent: Try it, or a typed yes read as `state.accepted: true` (existing).
- Safety screen behaviour, phrases, thresholds and crisis handling are not changed by this plan (brief §12).
- The chat never names a stage or its letter (muhammad, 2026-10-09).
- No phrase lists that judge meaning (muhammad, 2026-10-09). Code may check structure, ids, counts.
- Every prompt bullet is a sentence with no colon-as-mapping (`test_every_rule_in_a_prompt_file_is_a_sentence_not_a_yaml_mapping`).
- Content edits change nothing until `python scripts/seed.py` is run; prod reseeds only on muhammad's approval.
- Every code file starts with two `ABOUTME:` lines. Decisions go in `PORT-STATUS.md` "Decisions in force", edited in place.
- Measure before and after: three runs of `scripts/scenario_check.py` before, three after ([[measure-before-tuning-prompts]]).

## Review Focus

1. **A detailed first message.** Person gives event, belief and feeling in message 1. Expect: no question for anything already given; the offer may still wait for message 3 (earliest gate) but the replies in between must ask something new or move forward without asking. Pinned in Task 4 scenario `detailed_first_message`.
2. **An explicit "can we just work out what to do?" while an offer is open.** Expect: treated as a request, not as a question about ABCDE; the offer is not re-attached. Pinned in Task 2.
3. **Third ask of a stage.** Expect: the text that reaches the person does not ask the same stage a third time. Pinned in Task 3.
4. **A correction ("that's not what I meant") right after an offer.** Expect: no re-offer in that reply; the correction is taken. Pinned in Task 4 scenario `correction_after_offer`.
5. **Supportive person past message 6 with nothing that fits.** Expect: no forced ABCDE offer (once D-2 is decided). Pinned in Task 6.

---

# Part 1 — Audit

## A. Executive summary

**How the flow works today (verified by reading the code).** A message reaches `POST /v1/threads/{id}/messages`, and `orchestrator.send` runs it inside one transaction: idempotency and per-thread advisory locks, crisis lock check, style-button tap (no model call), framework retirement, button-tap resolution, the deterministic safety screen, the imminent-action check (inert while DBT STOP is paused), system-prompt composition (`mani_base` + generated Framework Index + `response_format` + profile + memory + summary), a per-turn `[ctx]` block, **one** structured model call returning `Reply`, up to two redrafts, deterministic repairs, then writes. Only **ABCDE** is active; the other five frameworks sit in `content/frameworks/paused/` and are seeded inactive. **No product frontend calls this API**: mobile runs `useChatSimulation` and web has no chat; the only real client is `chat-tester/`.

**The central problem (verified).** Framework suitability and readiness to offer are the **same decision** in the prompt, and the only brakes on it are **turn counts**:
- `[ctx]` tells the model in the understanding phase "As soon as one fits, offer it" (`backend/mani/chat/context.py:235-236`); `mani_base.md` says "Once a set fits, offer it rather than asking more" (`:94`), "do not keep talking once the fit is clear" (`:99`), "Do not hold a confident offer back for one more question" (`:107`), and Direct "as soon as a set fits, offer it" (`:68`).
- ABCDE's `central_indication` says it is "offered whenever one is appropriate" (`backend/content/frameworks/abcde.md:12-13`), and with one framework nearly anything fits.
- What holds the offer back is `earliest_offer_message: 3` (`abcde.md:16`, uncommitted) and what pushes it forward is `closest_fit_due` at the person's 4th (Direct) or 6th (Supportive, Reflective) message (`context.py:24-25,164-171`), enforced by a redraft (`redraft.py:200-205`).

So "fits but more exploration would help" cannot be represented, and "nothing fits" turns into a forced ABCDE offer once the count is reached. Those two facts drive most of the reported behaviour (offers at message 2, offers that feel abrupt, a person interviewed until the count arrives).

**Other main gaps.**
- Every reply before an offer must end in a question, redrafted up to twice if not (`orchestrator.py:504,545`; `redraft.py:177-184`). The two shapes that may ask nothing are restricted to venting or after a framework (`mani_base.md:59-60`). Acknowledging without a question while still exploring is not allowed.
- The understanding of the situation is not stored anywhere. It is re-derived each turn from a 20-message window (`messages.py:20`) and, after 20 messages, a 2–4 sentence summary. Known, uncertain and unknown are not told apart before an offer. Inside a framework the model writes a per-turn stage ledger (`stages_known`) that is used for one check and then discarded.
- Stage completion is entirely the model's judgement. Code checks only that `state.step` agrees with the ledger the model wrote itself, and caps asks at two. The cap moves the **recorded** stage but leaves the **text** asking the same stage a third time (`repairs.py:505-513`).
- With an offer open, **any** typed message containing `?` counts as asking about the offer, and code re-attaches the Try it button (`orchestrator.py:508-510,591-596`). A person who types "can we just work out what to do?" is offered ABCDE again.
- Engagement, difficulty answering, corrections, boundaries and diminishing value are all prompt-only, by an explicit decision ("no phrase lists"). That decision is sound. The trouble is that the prompt rules conflict with each other and with the turn gates (§C).

**Separation of the decisions (verified):**

| Decision | Where it lives | Separate? |
|---|---|---|
| Do I understand enough to respond? | model reasoning, prompt only | No state, no output field |
| Does a framework fit? | `heading_toward`, `offer_fit` (`schema.py:178-194`) | Partly: written down, but implies an offer |
| Is now the moment to offer? | "offer as soon as it fits" + earliest gate + closest-fit-due count | **No.** It is fit + count |
| Is this stage's purpose met? | `stages_known` per turn, model-judged; `MAX_STAGE_ASKS` | Partly: judged, not persisted |

**Biggest risks and open decisions.** (1) Whether the closest-fit forced offer stays (D-2). (2) Whether a pre-offer reply may skip the question (D-3). (3) The client's reference conversation contradicts two rules in force: it **summarises the pattern** before the offer, which `mani_base.md:23` forbids, and it **asks either/or questions**, which `mani_base.md:92,96` forbid (D-1). (4) Production: crisis resources are empty and no product client calls the API yet (both already in `PORT-STATUS.md`).

**Verified vs hypothesis.** Everything in the table above and in findings marked *Verified* comes from reading the code at the working tree of 2026-10-13, including uncommitted changes. User-facing **frequencies** (how often the model offers early, asks a third time and so on) are **not** measured here; no live model calls were made.

## Evidence base and what was run

- Branch `feat/abcde-framework-revamp`, HEAD `c2470fd`. 18 files have uncommitted changes, plus untracked `backend/supabase/migrations/011_technique_stage_asks.sql` and one journal note. The working tree was not touched.
- `pytest tests/unit -q -p no:cacheprovider` → **354 passed, 4 skipped** in 2.7 s.
- **Not run:** `tests/integration/` (writes users and turns to the shared local Supabase), `scripts/scenario_check.py` (paid model calls, creates and deletes users), `scripts/test_db.sh`. All three mutate local state, so they need muhammad's go-ahead (the brief, §13).
- **Not verified:** which content the local or hosted database actually holds. The uncommitted `abcde.md` (`earliest_offer_message: 3`) and `mani_base.md` (`reasoning_effort: low`) only take effect after `seed.py`. `PORT-STATUS.md` still says `mani_base` is on `high`.
- No black-box model comparison was run (§10). The reproducible experiment for it is in Part 2, Task 4.

## B. Execution flow (verified components)

```
mobile/ (useChatSimulation: canned replies, NO backend)   web/ (no chat)   chat-tester/ (Streamlit, real HTTP)
                                                                                   │
                         POST /v1/threads/{id}/messages  (mani/routers/threads.py) │
                                                                                   ▼
orchestrator.send  (mani/chat/orchestrator.py:276)
 ├─ advisory locks: client_message_id (:292), thread (:331)
 ├─ threads.load_turn_context: thread, technique row, offered list, recent styles,
 │     summary, recent_crisis, admin.user_memory  (one query, mani/db/threads.py)
 ├─ crisis lock? → 403                                                   (:343)
 ├─ messages.recent_for_context: last 20 messages                        (:351, messages.py:20)
 ├─ chosen_style(tap on greeting) → _open_in_style: fixed opener, NO model call  (:354, :943)
 ├─ retire a finished framework (final phase, not awaiting a body place) (:364-375)
 ├─ find_tapped_prompt / pending_offer → accepted | declined | deferred  (:388-409)
 ├─ safety.screen(content)  ── CRISIS → _handle_crisis: lock, fixed text, no model (:414-422)
 │                          └─ CONCERN → blocks_framework for this turn
 ├─ eligibility.urgent(last 2 user msgs) → DBT STOP candidate (inert: dbt_stop paused) (:433-437)
 ├─ composer.compose: mani_base | Framework Index | response_format | profile | memory
 │                    | title? | techniques offered | debug? | summary   (prompts/composer.py:248)
 ├─ context.build → [ctx]: style, phase (understanding|framework|talking), question_focus,
 │     cooldown_passed (= cooldown AND earliest_offer_message), closest_fit due|ok,
 │     this_thread, stage + next_stage + later_stage, stage_asked, said_before_yes   (context.py:371)
 ├─ client.complete([system, history…, "[ctx]…" + message], Reply)        (:482)
 │     Reply order: reasoning → style → heading_toward → offer_fit → stages_known → text → prompts → state
 ├─ redraft.reasons → up to 2 more calls: ledger mismatch, repeated question,
 │     no question, offered too early, offer not allowed, closest fit due, ruled out  (:519-564)
 ├─ deferred offer resolution: accepted | Keep chatting | asked about it  (:598-638)
 ├─ repairs.apply: strip leakage/internal words, button rules, cooldown drop,
 │     offer composition + client's buttons, phase clamp, stage-exhausted move (repairs.py:305)
 ├─ concern → strip technique & phase                                    (:684-697)
 ├─ body route (somatic check-in → place → practice), hand-off buttons   (:698-750)
 ├─ messages.create_pair (security definer)                               (:761)
 ├─ threads.apply: technique row upsert (stage_asks++ when phase unchanged), offered list,
 │     style shape, title                                                 (:776-819, threads.py:308-318)
 └─ framework retired → exercise pick (2nd small model call)              (:821-827)
Background: summarize.update when count − summarized ≥ 20 (needs_summary, :842); memory fold by cron.
```

Uncertain paths, marked rather than invented: what the hosted database holds; whether `needs_summary` background tasks finish before the next turn under load.

## C. Findings matrix

Priority: **P1** shapes most conversations, **P2** specific situations, **P3** quality or hygiene.

| ID | Requirement | Current behaviour and evidence | Scenario | Gap and impact | Confidence | Pri | Depends |
|---|---|---|---|---|---|---|---|
| F-01 | Fit ≠ readiness (§3, §7) | Understanding-phase `[ctx]` meaning ends "As soon as one fits, offer it" (`context.py:235-236`); `mani_base.md:68,94,99,107` say the same; ABCDE "offered whenever one is appropriate" (`abcde.md:12-13`). Readiness has no field, no state, no check. | Coworker frustration, message 3: fits ABCDE, so it is offered whether or not the person has said what they want. | No way to keep exploring once a framework fits. The offer arrives as soon as the earliest gate opens, which reads as abrupt. | Verified (code); live frequency unmeasured | P1 | D-1 |
| F-02 | No offer driven only by turn count (§3, §17) | `closest_fit_due` at the person's 4th (Direct) or 6th message (`context.py:24-25,164-171`); `[ctx]` "offer the set that fits best now" (`:282-286`); redraft forces it when `heading_toward` is set (`redraft.py:200-205`). With ABCDE alone, `heading_toward` is nearly always `abcde`. | Supportive person venting about a breakup, message 6: ABCDE offered because the count is reached. | A count triggers the offer, which the brief forbids. Undoes the "nothing fits, keep chatting" path. | Verified | P1 | D-2 |
| F-03 | Earliest offer by count (§3) | `earliest_offer_message: 3` (`abcde.md:16`), `earliest_offer_ok` (`context.py:145-151`), "too early" redraft (`redraft.py:185-192`). Uncommitted, added 2026-10-12 after offers at message 2. | Detailed first message with event, belief and feeling: no offer before message 3. | A count as a brake. It is the right stopgap while F-01 stands; with F-01 fixed it can become a floor rather than the only control. | Verified | P2 | D-2 |
| F-04 | A reply need not end in a question (§5) | `needs_question` before any offer (`orchestrator.py:504`); redraft up to twice (`:545`, `redraft.py:177-184`); `mani_base.md:22` "Every reflection is followed by one question"; question-free shapes "Only after the questions ended, or when they only want to be listened to" (`:59-60`). | Person gives a painful detail; the best reply is a short acknowledgement. The draft is redrafted to add a question. | Interview feel: a question on every turn is enforced in code. | Verified | P1 | D-3 |
| F-05 | Prompt rules contradict each other (§5) | `mani_base.md:98` "no question is aimed at a set" vs the generated Framework Index "let your questions reach for what is still missing for it" (`composer.py:111-116`). `:22` "every reflection is followed by one question" vs reply shapes that ask nothing. `:99` "Ask until you understand… then stop asking and offer". | Any pre-offer turn. | The model receives conflicting targets. Journal [[direct-questions-have-no-target-2026-10-09]] shows prohibitions swinging between two failures. | Verified (text); effect unmeasured | P2 | D-1 |
| F-06 | Known / uncertain / unknown, provenance (§4) | No stored understanding before an offer. Model `reasoning` is discarded (returned only with `AI_DEBUG_MODE`). Summary exists only after 20 messages (`orchestrator.py:61,842`) and is 2–4 sentences of model prose (`summarization.md`). | A correction at message 2 is held only by the raw history. | Corrections and provenance depend on the model re-reading history each turn. Within 20 messages that usually works; the risk is model judgement, not lost data. | Verified (absence); harm Suspected | P3 | none |
| F-07 | Context reuse at framework start (§9) | `said_before_yes`: the last **6** user messages, on the accept turn only (`context.py:587-597`); `_WALK_THE_STAGES` and `stages_known` walk them (`context.py:535-549`). Later turns rely on the 20-message window plus summary. | 8 user messages before the yes, with the belief stated in message 1: it is not in `said_before_yes`, though still in the 20-message window. | Mostly covered. The edge is long pre-offer chats; the summary's 2–4 sentences may lose the exact belief wording later in the framework. | Partially verified | P3 | none |
| F-08 | Stage completion by purpose (§9) | Completion is the model's ledger (`schema.py:119-153`); code checks only that `state.step` matches the first non-met stage of the model's own ledger (`redraft.py:65-79`), and does nothing when the ledger is missing (`:69`). The ledger is not persisted. | The model marks `dispute` known after "yes"; nothing in code can tell. | Purpose satisfaction is unverifiable in code. That is inherent: it is a semantic judgement. Only evaluation can catch it. | Verified | P2 | none |
| F-09 | Never ask a stage a third time (decision 2026-10-12) | At `stage_asks ≥ 2`, if the redrafted reply still stays, `repairs.apply` changes the recorded `phase` only (`repairs.py:505-513`); `text` still asks the old stage. | Dispute stage, "idk" twice: the third reply still asks dispute; the next turn starts at effective. | The person reads the third ask the decision forbids. The state jumps ahead of what was asked, so their next answer is filed under the wrong stage. | Verified (code path) | P1 | none |
| F-10 | Explicit request for practical help with an offer open (§6C, §8) | `asked_about_offer = offer and (deferred and "?" in content)` (`orchestrator.py:508-510`); the reply is then forced to carry Try it (`:591-596`) and the outcome stays OFFERED (`:606-610`). It also bypasses `offer_not_allowed` (`:527`). | Offer shown; they type "can we just work out what to do?". Mani answers and re-attaches the ABCDE offer. | Pressure to accept; the request is not honoured. Any question ("why do I feel like this?") behaves the same. The schema already lets the model say "asked about the offer" (`state.accepted: null`, `schema.py:92-101`). | Verified (code); live unverified | P1 | none |
| F-11 | Decline does not loop (§8) | Typed non-yes = Keep chatting (`orchestrator.py:604-610`, decision 2026-09-24). Same framework may return after 4 messages (`context.py:28,134-142`); the model is told a declined one "may come back once the cooldown has passed, if it still fits" (`context.py:289-294`). With one framework, "fits" stays true. | Decline at message 4, re-offer at message 6, again at 8 or 10. | Repeated-offer loop risk; no record of why they declined. | Suspected (frequency unmeasured) | P2 | D-4 |
| F-12 | No match → continue open chat (§7) | Only ABCDE is active. `offer_fit: closest` plus `closest_fit_due` force the nearest, which is always ABCDE. Contraindication covers abuse and danger only (`abcde.md:32-33`). | Grief, a practical scheduling problem, loneliness: all get ABCDE by message 4 or 6. | "No framework fits" exists only until the count. | Verified | P1 | D-2 |
| F-13 | Boundaries before an offer (§6C) | `any_stage` handles unease and skip inside a framework (`mani_base.md:138`). Before an offer there is no rule for "I don't want to talk about that"; memory records skipped questions only across chats (`schema.py:324-330`). | "I don't want to talk about my dad" at message 2: nothing tells the model to keep away from it at message 4. | Prompt gap; depends on the model reading history. | Verified (absence) | P2 | none |
| F-14 | Practical-help request while no practical framework exists (§6C, §7) | Structured Problem-Solving is paused. Direct names "the one thing worth doing next only when they ask" (`mani_base.md:69`); no other mode answers "what should I do?" before an offer. | "Can we just work out what to do?" at message 2: Mani asks a feeling question or offers ABCDE. | Product gap: ABCDE examines beliefs; it is not a plan. | Verified | P2 | D-5 |
| F-15 | Style is not readiness (§2) | Style propagation is sound: `resolve_style` (thread > profile > supportive, `context.py:183-193`) is used in `[ctx]`, the stage note (`:562-573`), the offer pattern, consent line and body route. But style also sets the forced-offer count (4 vs 6, `context.py:169-171`) and Direct is told it "reaches the offer soonest" (`mani_base.md:68`). A thread whose person types instead of tapping a style silently gets Supportive. | Direct conversation: forced offer at message 4. | Style changes when an offer happens, which the brief says not to assume. | Verified | P2 | D-2 |
| F-16 | Safety precedence (§12) | The screen runs on every turn before the model (`orchestrator.py:414`); crisis short-circuits; concern removes offers and stage changes (`:684-697`); a model-reported crisis is a non-locking concern. Redrafts reuse the same assessment. Tested in `tests/unit/test_safety.py` and `tests/integration/test_turn.py:656-915` (not run here). | Concern mid-framework: stage held, no offer. | No gap found in precedence. Production gap already recorded: `crisis.py`, `PROTOCOLS` and `CLARIFICATION` are empty. | Verified (code); integration not run | P2 | none (no change) |
| F-17 | Clients consistent with the API (§8, §11) | Mobile uses `mobile/src/hooks/useChatSimulation.ts` (canned replies, own crisis words); web has no chat. | Any product user. | Offer, consent and stage state are unverifiable in the product clients. | Verified | P3 | out of scope |
| F-18 | Runtime vs repo content (§11) | Runtime reads `admin.prompts` and `admin.frameworks`. Uncommitted `mani_base.md` sets `reasoning_effort: low` while `PORT-STATUS.md` says high. The `abcde.md` footer (`:205-210`) says each letter is named, against the decision that the chat never names a stage (the footer is documentation; whether it reaches the model is unverified). | — | Drift; the behaviour seen depends on the last reseed. | Partially verified | P3 | none |
| F-19 | Engagement signals (§6A, §6B, §6D) | All prompt-only by decision. `threads.vague_streak` exists and is written by nothing. "I don't know" before an offer: an easier question about one small part (`mani_base.md:96`). Diminishing value: only "Ask until you understand… then stop and offer" (`:99`), which is F-01 again. | Repeated "idk": the prompt says ask easier; nothing measures the run. | Acceptable by the 2026-10-09 decision; untested. Diminishing value is not represented except as "offer". | Verified (absence) | P2 | D-3 |

## D. Current vs intended, as traces

None of these were run against the model. "Current" is what the code and prompt **require or allow**, traced through the files cited; it is not a recorded output.

**Trace 1, the reference conversation (muhammad's attachment).** Person: "I am frustrated" → "everything" → "my boss, my coworkers, our vendors…" → "people over promise and under deliver…" → "I cannot do the work unless they do their work" → "yes I need help".
- *Current, as gated:* message 3 is the earliest an ABCDE offer may come (`earliest_offer_message: 3`), and the prompt says offer as soon as it fits, so an offer is likely at message 3 or 4. In Direct, message 4 makes it **due** (F-02). Before that, every reply must end in one short question with no either/or (`mani_base.md:92,96`).
- *Reference:* five exchanges; asks discriminating either/or questions; offers nothing until the person says "yes I need help"; then reflects the **pattern** in four sentences and introduces the framework.
- *Why it matters:* the reference uses the person's explicit readiness as the trigger, not a count, and does two things current rules forbid: summarising (`mani_base.md:23`) and either/or questions (`:92,96`). D-1 has to settle which of these the product wants.

**Trace 2, explicit request with an offer open (F-10).** Offer shown → "Honestly can we just work out what to do?" → `deferred` true, `"?" in content` true → `asked_about_offer` true → the reply is forced to carry Try it → `repairs.apply` composes the offer again if the reply has no other `?`. *Intended:* treat it as a request; answer it; no re-offer in that reply.

**Trace 3, third ask (F-09).** In dispute: "idk" → reply 2 asks again → "idk" → `stage_asked: twice` in `[ctx]`; the model stays anyway → redraft (ledger) → still stays → `repairs.apply` records `effective`, **text unchanged**. *Intended:* the text reaching the person moves on (asks `effective`) or holds the question back.

**Trace 4, nothing fits, Supportive (F-02, F-12).** Message 6 of a grief conversation with no belief stated: `closest_fit: due` → if `heading_toward` is `abcde`, the redraft says "offer the set that fits best now". *Intended:* keep talking; offer only if fit and readiness are both there.

## E. Unresolved product decisions

| ID | Question | Why it matters | Alternatives and consequences | Recommendation | Blocks |
|---|---|---|---|---|---|
| **D-1** | What makes MANI ready to offer, once ABCDE fits? | F-01, F-05, Trace 1 | (a) Fit + earliest gate, as today: fast, abrupt. (b) Fit + the model's explicit judgement that one more question would not change what happens next, recorded in `next_move`: needs evaluation. (c) Fit + the person signals readiness ("I need help", asks what to do): natural, may never come for some people. | **(b), with (c) as a strong signal the model weighs.** Keep `earliest_offer_message` as a floor. | Tasks 5, 6 |
| **D-2** | Keep the forced closest-fit offer at message 4 or 6? | F-02, F-12, F-15 | (a) Keep: every conversation reaches a framework; violates the brief. (b) Remove: some conversations never offer; needs an alternative for "nothing fits". (c) Keep `closest_fit: ok` (may offer) but drop `due` (must offer). | **(c).** The model may still offer the nearest; nothing forces it. | Task 6 |
| **D-3** | May a reply before an offer end without a question? | F-04, F-19 | (a) No, as today. (b) Yes, when `next_move` is `acknowledge`; code still redrafts a reply that asks nothing without having chosen that. (c) Yes, but never twice in a row. | **(c)**: it keeps the conversation moving and is checkable in code. | Task 5 |
| **D-4** | After Keep chatting, when may ABCDE come back? | F-11 | (a) 4 messages, as today. (b) Only after the person brings something new or asks. (c) Once per conversation unless they ask. | No evidence yet; measure the re-offer rate in Task 4 first. | Deferred |
| **D-5** | What does MANI do with "just tell me what to do" while SPS is paused? | F-14 | (a) ABCDE anyway. (b) Answer directly within the existing advice exceptions (one small draft step). (c) Un-pause SPS. | Client decision. Until then, (b) keeps the request honoured. | Deferred |
| **D-6** | Should the client's reference conversation become a scenario in `scenarios.json`? | Gives D-1 a measurable target | yes / no | **Yes.** | Task 4 |
| **D-7** | May integration tests and `scenario_check.py` run against the local database for this work? | They write data and cost money | yes / no | Required for any measurement. | Tasks 1–6 verification |

## F. Readiness assessment

- **Ready to implement now (no product decision):** Task 1 (baseline), Task 2 (F-10), Task 3 (F-09).
- **Needs a decision first:** Task 5 (D-1, D-3), Task 6 (D-2).
- **Needs more evidence before any change:** F-06/F-07 (persisted understanding: do **not** build until the Task 4 scenarios show forgotten context inside the 20-message window), F-11 (D-4).
- **Sequence:** Task 1 → 2 → 3 → 4 → muhammad answers D-1..D-3 → 5 → 6 → Task 7 (measure and record).
- **Before production:** crisis resources (F-16, already open); a product client on the real API (F-17); reseed and check that the database matches the repo (F-18).

---

# Part 2 — Implementation plan

## Decisions (muhammad, 2026-10-13)

- **D-1:** readiness is a `next_move` field the model fills before `text`. The trigger is the model's judgement that the conditions are met, never the word "help".
- **D-2:** no forced offer. `closest_fit` due/ok and `offer_fit` go.
- **First offer:** no floor. `earliest_offer_message` goes.
- **D-3:** a reply before an offer asks one question, except when any question would be unreasonable.
- **Questions:** dig for the core issue so the person thinks "yes, that is it". Either/or questions are allowed freely. Never call it therapy.
- **Offer:** opens with two or three sentences naming the pattern Mani sees, then the client's ABCDE line.
- **D-4:** after Keep chatting, come at the same context from another angle; may offer again by judgement, never in that reply or the two after it.
- **D-5:** Structured Problem-Solving stays paused. "Just tell me what to do" gets: Mani cannot hand over a solution, but can help them work it out, plus the question that leads there.
- **D-7:** live runs approved.
- Target: chat the way Lolly experienced ChatGPT in her workplace-frustration conversation, in general, not only that scenario.

## Execution order

Task 1 (baseline, controller, done in scratch) → Task 2 → Task 3 → Task 4 → Task 5 → controller measures → Task 6 → controller measures → Task 7. Tasks 5 and 6 are measured separately because muhammad wants a behaviour change attributable to one step.

## Task 1: Baseline measurement (controller)

Done by the controller before Task 2: `seed.py`, full `pytest` (451 passed, 4 skipped), and three runs of the scenarios plus `reference_frustration`, `detailed_first_message`, `practical_request`, saved as JSON transcripts in the session scratchpad.

## Task 2: A typed question with an offer open is not automatically about the offer (F-10)

**Files:**
- Modify: `backend/mani/chat/orchestrator.py` (`asked_about_offer` at about lines 506-511, its use in `_why`, the Try it re-attachment at about 591-596, `asked_about_it` at about 604-610, `offer_asked_about=` in the `repairs.apply` call)
- Test: `backend/tests/integration/test_turn.py`

**Interfaces:**
- Consumes: `Reply.state.accepted`. `True` means yes, `False` means Keep chatting, `None` with `state.technique` naming the open offer means they asked about the offer (`backend/mani/llm/schema.py`, `TechniqueState.accepted`).
- Produces: inside `send`, a local `_asked_about(draft: Reply) -> bool` that is true only for a tap whose label is in `EXPLAIN_LABELS`, or a typed reply (`deferred`) whose draft reports `state.technique == offer.technique` and `state.accepted is None`.

- [ ] **Step 1: Write the failing test** in `backend/tests/integration/test_turn.py`, next to `test_asking_about_an_offer_leaves_it_open`:

```python
async def test_a_typed_request_with_an_offer_open_is_not_offered_again(alice, model):
    """A question that is not about the offer, typed while it is open, is Keep chatting: the
    reply answers them and the offer is not put back (audit F-10, 2026-10-13)."""
    model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Try it", technique="abcde")],
            state=TechniqueState(technique="abcde", step="offering"),
        ),
        Reply(text="I can't hand you a plan, but we can work it out. What is due first?"),
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep spiralling about work")
    turn = await send(alice, thread.id, "Honestly can we just work out what to do?")

    assert not any(p.technique for p in turn.prompts)
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.technique.outcome is TechniqueOutcome.DECLINED
```

- [ ] **Step 2:** `cd backend && source .venv/bin/activate && pytest tests/integration/test_turn.py -k typed_request -v`. Expected: FAIL. Today code re-attaches Try it and the outcome stays `offered`.
- [ ] **Step 3: Implement.** Replace the `asked_about_offer` boolean with:

```python
    def _asked_about(draft: Reply) -> bool:
        """They asked about the open offer: Tell me more, or a typed question the draft itself
        reports as about the offer (state names it, accepted left null)."""
        if offer is None:
            return False
        if tapped is not None and tapped.label.strip().lower() in EXPLAIN_LABELS:
            return True
        return bool(
            deferred and draft.state is not None
            and draft.state.technique == offer.technique and draft.state.accepted is None
        )
```

In `_why`, use `not _asked_about(draft)` where `not asked_about_offer` was. After the redraft loop set `asked_about_offer = _asked_about(reply)` and keep the existing uses (Try it re-attachment, `offer_asked_about=`). In the `deferred` branch, replace `asked_about_it = "?" in content and any(p.technique for p in reply.prompts or [])` with `asked_about_it = asked_about_offer`. Keep the existing comments that are still true, and fix any that describe the `?` rule.
- [ ] **Step 4:** Run the new test, then the whole of `tests/integration/test_turn.py`. Expected: PASS. If an existing test scripted a typed question about the offer with `state=None`, it relied on the `?` rule. Update its script to report `state=TechniqueState(technique=..., step="offering")` and name the test in the commit message.
- [ ] **Step 5:** In `backend/PORT-STATUS.md`, edit the decision line "An open offer is read from the database, not from the buttons on screen" in place to add: a typed message counts as asking about the offer only when the reply reports the offer with `accepted` left null; any other typed message is Keep chatting. Commit: `fix: a typed question with an offer open is not taken as asking about the offer`.

## Task 3: The third ask never reaches the person (F-09)

**Files:**
- Modify: `backend/mani/chat/redraft.py` (`reasons`), `backend/mani/chat/repairs.py` (`apply`, the `stage_exhausted` branch)
- Test: `backend/tests/unit/test_redraft.py`, `backend/tests/unit/test_repairs.py`, `backend/tests/integration/test_turn.py::test_a_stage_they_cannot_answer_is_left_after_two_asks`

**Interfaces:**
- Consumes: `redraft.StageInForce(framework_id, stage, asked, asks)`, `context.MAX_STAGE_ASKS` (2), `framework.may_skip(phase)`, `repairs.with_the_check_in(text, script)` (keeps the reflection, replaces the closing question with `script`), `repairs.reply_for`, the framework's `stages[phase]["ask"][style]`.
- Produces: `reasons` adds a note when the draft stays on a stage already asked twice. `apply`, when `stage_exhausted` moves `phase` forward, also replaces the reply's closing question with the new stage's `ask` for `conversation_style`, and adds the note `replaced a third ask of '<old>' with '<new>'`.

- [ ] **Step 1: Failing unit tests.** Use the fixtures and helpers the two files already have for a registry with ABCDE and for calling `apply` on a running framework; read them first.

```python
def test_a_draft_staying_on_a_stage_asked_twice_is_redrafted(registry):
    draft = Reply(text="What makes you believe it?",
                  state=TechniqueState(technique="abcde", step="dispute"))
    notes = reasons(draft, [], registry, offer_not_allowed=False,
                    stage_in_force=StageInForce("abcde", "dispute", True, 2))
    assert any("asked twice" in n for n in notes)


def test_a_stage_asked_once_is_not_redrafted_for_staying(registry):
    draft = Reply(text="What makes you believe it?",
                  state=TechniqueState(technique="abcde", step="dispute"))
    notes = reasons(draft, [], registry, offer_not_allowed=False,
                    stage_in_force=StageInForce("abcde", "dispute", True, 1))
    assert not any("asked twice" in n for n in notes)
```

```python
def test_an_exhausted_stage_reaches_the_person_as_the_next_stage_question(registry):
    draft = Reply(text="That's hard to know.\n\nWhat makes you believe it?",
                  state=TechniqueState(technique="abcde", step="dispute"))
    fixed = apply(draft, registry, already_offered=[], current_framework_id="abcde",
                  current_phase="dispute", selected_label=None, accepted_this_turn=False,
                  framework_running=True, cooldown_passed=False, conversation_style="direct",
                  wants_title=False, stage_exhausted=True)
    assert fixed.phase == "effective"
    assert "What makes you believe it?" not in fixed.text
    assert fixed.text.startswith("That's hard to know.")
    assert fixed.text.endswith(registry.get("abcde").stages["effective"]["ask"]["direct"])
```

- [ ] **Step 2:** `pytest tests/unit/test_redraft.py tests/unit/test_repairs.py -v`. Expected: the "asked twice" and "exhausted" tests FAIL.
- [ ] **Step 3: Implement.** In `redraft.reasons`, after the ledger check (`framework` is already looked up from `stage_in_force`):

```python
    if (
        stage_in_force and framework and stage_in_force.asks >= MAX_STAGE_ASKS
        and framework.may_skip(stage_in_force.stage)
        and reply.state and reply.state.technique == framework.id
        and reply.state.step == stage_in_force.stage
    ):
        notes.append(
            f"you have asked {stage_in_force.stage} twice already; take what they gave you, even "
            "partial or I don't know, and ask the next stage now, in your own tone"
        )
```

Do not duplicate a note when the ledger check already named a different expected stage. If both fire, keep both: they say the same thing in different words, and the model handles that. In `repairs.apply`, inside the existing `stage_exhausted` branch right after `phase` is moved:

```python
                ask = ((framework.stages.get(phase) or {}).get("ask") or {}).get(conversation_style)
                if ask:
                    text = with_the_check_in(text, ask)
                    notes.append(f"replaced a third ask of {current_phase!r} with {phase!r}")
```

`with_the_check_in` is defined later in the same module. It is a plain module function, so calling it from `apply` is fine. If the new phase is in `ENDING_STAGES` (`somatic_checkin`), do not replace the text. The body route sets that text itself.
- [ ] **Step 4:** In `test_a_stage_they_cannot_answer_is_left_after_two_asks`, add after the last `send` that the returned turn's content does not end with `"What did you make of it?"` and does end with the `consequence` stage's Supportive ask (the thread's default style). Use `context.resolve_style` semantics: no style set means `supportive`. Run `pytest tests/unit tests/integration/test_turn.py`. Expected: PASS.
- [ ] **Step 5:** Edit the decision line containing "**No stage is asked a third time**" in `PORT-STATUS.md` in place: the reply that would ask it a third time asks the next stage's question instead, and a draft that stays is redrafted once first. Commit: `fix: a stage asked twice is not asked a third time in the reply`.

## Task 4: Scenarios for the conversation matrix (data only)

**Files:** Modify `backend/scripts/scenarios.json`. Read `backend/scripts/scenario_check.py` first. Each scenario is `{"source": str, "lines": [str, ...]}`, and the runner sends the lines in order and stops after the first offer and its Tell me more.

- [ ] **Step 1:** Add these entries verbatim (keys and lines), keeping the existing six:

```json
 "reference_frustration": {
  "source": "Lolly's ChatGPT conversation, attached by muhammad 2026-10-13: the target behaviour",
  "lines": [
   "I am frustrated",
   "everything",
   "my boss, my coworkers, our vendors, our consultants, our customers everything",
   "people over promise and under deliver, do not take responsibility or accountability and it makes my job harder",
   "I cannot do the work unless they do their work",
   "yes I need help"
  ]
 },
 "detailed_first_message": {
  "source": "audit matrix 1, 2026-10-13: everything in the first message",
  "lines": [
   "My sister stopped replying to my messages two weeks ago after I missed her birthday dinner, and I keep thinking she's decided I'm a terrible person. I've been avoiding calling her because I'm scared she'll confirm it. I just want things to be okay between us again.",
   "Yeah, that's pretty much it.",
   "I don't know, I guess I just feel stuck."
  ]
 },
 "practical_request": {
  "source": "audit matrix 9, 2026-10-13: asks what to do",
  "lines": [
   "My landlord says I have to move out in 30 days and I have nowhere lined up.",
   "I've looked at a few places but they're all too expensive.",
   "Can we just work out what to do?"
  ]
 },
 "correction": {
  "source": "audit matrix 7, 2026-10-13: corrects Mani",
  "lines": [
   "My best friend didn't invite me to her wedding.",
   "No, I'm not angry. That's not it at all.",
   "I just keep wondering what I did wrong.",
   "Maybe she thinks I'm not really her friend anymore."
  ]
 },
 "boundary": {
  "source": "audit matrix 8, 2026-10-13: a topic they will not discuss",
  "lines": [
   "Things at home have been really tense and I can't focus at work.",
   "I don't want to talk about my dad.",
   "I just feel like I'm failing at everything lately.",
   "My manager said my work has slipped and I think he's going to let me go."
  ]
 },
 "minimal_replies": {
  "source": "audit matrix 4 and 5, 2026-10-13: short and unsure answers",
  "lines": [
   "I feel off today.",
   "idk",
   "work I guess",
   "my team lead keeps redoing my work and I think he thinks I'm useless"
  ]
 }
```

- [ ] **Step 2:** `python -c "import json;print(len(json.load(open('backend/scripts/scenarios.json'))))"` prints 12. Commit: `eval: conversation-matrix scenarios and the reference conversation`.

## Task 5: Readiness is the model's explicit choice; no count floor, no forced offer (D-1, D-2; F-01, F-02, F-03, F-12, F-15)

**Files:**
- Modify: `backend/mani/llm/schema.py`, `backend/mani/chat/context.py`, `backend/mani/chat/redraft.py`, `backend/mani/chat/orchestrator.py`, `backend/mani/chat/repairs.py` (only if it references a removed name), `backend/scripts/scenario_check.py` (only if it references a removed name), `backend/content/frameworks/abcde.md`, `backend/content/prompts/mani_base.md`, `backend/content/prompts/response_format.md`, `backend/PORT-STATUS.md`
- Test: `backend/tests/unit/test_redraft.py`, `backend/tests/unit/test_chat_context.py`, `backend/tests/unit/test_chain.py` or the test file that pins `Reply` field order (find it with `grep -rn "model_fields" backend/tests`), `backend/tests/unit/test_composer.py`, `backend/tests/integration/test_turn.py`

**Interfaces:**
- Produces: `Reply.next_move: Literal["ask", "acknowledge", "offer", "answer_request"] | None`, declared directly after `heading_toward` and before `stages_known` and `text`. `Reply.offer_fit` is removed. `redraft.reasons(..., may_offer: bool = False)` with `earliest_wait` and `closest_fit_due` parameters removed. `context.build(...)` without `first_offer_ok`; `urgent` goes too if nothing else in `build` reads it. `context.COOLDOWN_AFTER_DECLINE = 4`; `context.cooldown_for(outcome)` returns `COOLDOWN_AFTER_COMPLETE` (45) for accepted, else `COOLDOWN_AFTER_DECLINE`.
- Removed (every definition, use, test and `[ctx]` meaning): `earliest_offer_ok`, `closest_fit_ok`, `closest_fit_due`, `_closest_fit_after`, `CLOSEST_FIT_AFTER`, `CLOSEST_FIT_AFTER_GENTLE`, `CLEAR_COOLDOWN_AFTER_DECLINE`, `clear_cooldown_for`, the old 6-message `COOLDOWN_AFTER_DECLINE`, `_FIT_PLAINLY`, the `closest_fit` `[ctx]` line, `earliest_offer_message` in `abcde.md`, `offer_fit`.

- [ ] **Step 1: Failing tests.**

```python
# field order (put beside the existing field-order test)
def test_next_move_is_chosen_before_text():
    fields = list(Reply.model_fields)
    assert fields.index("heading_toward") < fields.index("next_move") < fields.index("text")
    assert "offer_fit" not in fields
```

```python
# test_redraft.py
def test_an_offer_the_draft_did_not_choose_is_redrafted(registry):
    draft = Reply(text="There's a framework called ABCDE.", next_move="ask",
                  prompts=[SmartPrompt(label="Try it", technique="abcde")])
    notes = reasons(draft, [], registry, offer_not_allowed=False)
    assert any("next_move" in n for n in notes)


def test_choosing_to_offer_without_the_button_is_redrafted(registry):
    draft = Reply(text="There's a framework called ABCDE that could help.", next_move="offer")
    notes = reasons(draft, [], registry, offer_not_allowed=False, may_offer=True)
    assert any("Try it" in n for n in notes)


def test_choosing_to_offer_is_not_pressed_when_no_offer_may_be_made(registry):
    draft = Reply(text="What has stayed with you since?", next_move="offer")
    assert reasons(draft, [], registry, offer_not_allowed=False, may_offer=False) == []


def test_an_acknowledgement_chosen_as_the_move_is_not_asked_for_a_question(registry):
    draft = Reply(text="That landed hard.", next_move="acknowledge")
    assert reasons(draft, [], registry, offer_not_allowed=False, needs_question=True) == []


def test_a_draft_with_no_move_and_no_question_still_asks_for_one(registry):
    draft = Reply(text="That landed hard.")
    notes = reasons(draft, [], registry, offer_not_allowed=False, needs_question=True)
    assert any("asks no question" in n for n in notes)
```

```python
# test_chat_context.py, using that file's own helper for a TurnContext at a given message count
def test_no_count_holds_back_or_forces_a_first_offer(...):
    block = context.build(ctx_at_their_first_message)
    assert "cooldown_passed: yes" in block
    assert "closest_fit" not in block


def test_after_keep_chatting_no_offer_for_that_reply_and_the_two_after(...):
    # technique declined at message_count C: cooldown_passed is no at C and C+2, yes at C+4
    ...
```

Write the last two with that file's existing `TurnContext` builders. Assert `context.cooldown_passed(ctx)` at `message_count` equal to `at_message_count`, `+2` and `+4`, expecting False, False, True.

```python
# test_turn.py: replace test_an_offer_on_their_first_message_waits_for_the_meaning
async def test_an_offer_the_model_is_ready_to_make_is_made_on_their_first_message(alice, model):
    """No count holds a first offer back: the model decides readiness (muhammad, 2026-10-13)."""
    scripted = model(Reply(
        text="It sounds like the waiting is what gets to you. There's a framework called ABCDE.",
        prompts=[SmartPrompt(label="Try it", technique="abcde")],
        state=TechniqueState(technique="abcde", step="offering"),
        next_move="offer",
    ))
    thread = await start(alice)
    turn = await send(alice, thread.id, "i have an exam tomorrow and i keep thinking i will fail it")

    assert scripted.calls == 1
    assert [p.technique for p in turn.prompts if p.technique] == ["abcde"]
```

Delete `test_the_closest_fit_is_owed_by_the_fourth_message_and_offers_plainly`. In `test_a_motive_they_believe_in_reaches_the_closest_fit_with_the_deeper_framework_offer`, rename it to `test_four_messages_without_an_offer_force_none` and assert `"closest_fit" not in final_prompt` and `scripted.calls == 4` (no redraft forced an offer). Remove or rewrite every unit test of the removed functions so it asserts the new behaviour. List removed tests in the commit message.
- [ ] **Step 2:** `pytest tests/unit tests/integration/test_turn.py`. Expected: the new tests FAIL.
- [ ] **Step 3: Implement the code.**
  - `schema.py`: remove `offer_fit`. Add after `heading_toward`:

```python
    next_move: Literal["ask", "acknowledge", "offer", "answer_request"] | None = Field(
        default=None,
        description=(
            "Choose before writing text, after heading_toward. ask: one question that would change "
            "what you understand of their concern. acknowledge: no question, only when any question "
            "here would be unreasonable. offer: a set fits and another question would not change "
            "what you understand, so you offer it in this reply. answer_request: they asked you "
            "for something, so you answer it and ask what leads toward it. Never decided by how "
            "many messages have passed. Not shown to the user."
        ),
    )
```

  - `redraft.reasons`: drop `earliest_wait` and `closest_fit_due` and their branches. Add `may_offer: bool = False`. Add these checks:

```python
    if technique and reply.next_move not in (None, "offer"):
        notes.append(
            f"your draft offers a set of questions but next_move is {reply.next_move}; offer only "
            "when you chose to, otherwise offer nothing and do what next_move says"
        )
    if may_offer and not technique and reply.next_move == "offer":
        notes.append(
            "you chose next_move offer but sent no Try it button; offer it with the Try it button "
            "and the framework id, or choose another move"
        )
```

  and widen `chose_to_ask_nothing` to `... in NO_QUESTION_SHAPES or reply.next_move == "acknowledge"`. The `offer_not_allowed` note drops its "set offer_fit to clear" clause: "your draft offered a set of questions, which may not be offered in this reply; offer nothing and ask one short, plain question about what they just said, in their words".
  - `orchestrator.send`: `clear_ok = context.cooldown_passed(ctx)`; delete `closest_ok`, `_earliest_ok` and the `first_offer_ok=` argument. `offer_not_allowed = not _asked_about(draft) and not clear_ok`. Pass `may_offer = clear_ok and not assessment.blocks_framework and not framework_going and not deferred`. The `repairs.apply` argument becomes `cooldown_passed=(clear_ok and outcome is not TechniqueOutcome.DECLINED and not redraft.ruled_out(reply, user_texts, config.registry))`. Keep the existing comments that are still true; delete the ones about closest fit, earliest offer or offer_fit.
  - `context.py`: remove the names listed under "Removed" and every `[ctx]` line and meaning for them. `cooldown_passed` uses `cooldown_for`. Keep its docstring true: "Whether an offer may be made yet: the first never waits; after Keep chatting none comes in that reply or the two after it." Change the `cooldown_passed` meanings to `"yes": "an offer may be made in this reply, when one fits and another question would not change what you understand."` and `"no": "offer nothing in this reply."`. In `_MEANING["conversation_phase"]["understanding"]`, replace the final two sentences `"What they say about how it is for them shows which set fits. As soon as one fits, offer it."` with `"What they say shows which set fits. A set that fits is offered only when another question would not change what you understand, and that is your next_move, never a count of messages."`. The comment block above `CLOSEST_FIT_AFTER` goes with it. Rewrite the comment above the cooldowns to say what is left.
  - Fix `scenario_check.py`'s `INTERNAL` regex only if it no longer compiles or reads a removed name. It may keep `offer_fit` as a leak guard. Leave `repairs._INTERNAL_WORDS` as it is.
- [ ] **Step 4: Content, the readiness lines only** (Task 6 changes how Mani talks; do not touch anything else in these files):
  - `abcde.md`: delete the `earliest_offer_message: 3` line and the two comment lines above it. In `central_indication`, replace `ABCDE is the framework offered whenever one is appropriate, and the only one offered right now.` with `ABCDE is the only framework offered right now.`
  - `mani_base.md` `styles.direct`: replace the line `- Of the three, Direct reaches the offer soonest: as soon as a set fits, offer it.` with `- Each question goes straight to what matters, with no detours.`
  - `mani_base.md` `before_an_offer`: replace `- Never ask what is at stake. Once a set fits, offer it rather than asking more.` with `- Never ask what is at stake.` Replace the bullet starting `- There is no fixed number of questions.` with `- There is no fixed number of questions. A set that fits is not yet a reason to offer it. Offer once you understand the core of their concern well enough that another question would not change it, the way a good therapist would know. Never keep asking to reach a number, and never hold an offer back once another question would add nothing.`
  - `mani_base.md` `offers`: replace the bullet starting `- ABCDE is the only set offered.` with `- ABCDE is the only set offered. It fits once they have described a situation, and what they began believing it means or how they are feeling or coping, such as overwhelmed, anxious or not handling things well. It does not need every detail of the event, since step A asks for that. Offer it by its Use it when, never by whether something could be done. Most situations have a practical side, and that alone is no reason to hold it back.` Replace the two bullets starting `- offer_fit clear means` and `- offer_fit closest means` with one bullet: `- Offer when next_move is offer, that is when it fits by its Use it when and you understand their concern well enough that another question would not change it. Never because of how many messages have passed.`
  - `response_format.md` `reasoning.steps`: replace the bullet starting `- Offer or not.` with `- Next move. Choose next_move. If cooldown_passed is no or safety is concern, it is not offer, and if pain is not yet placed in the body or in how they feel, it is not offer. Offer when a set fits by its Use it when and Telling them apart and another question would not change what I understand of their concern. Ask when a question would. Acknowledge only when any question here would be unreasonable. Answer_request when they asked me for something.`
  - No bullet may contain `: ` (colon then space). `test_every_rule_in_a_prompt_file_is_a_sentence_not_a_yaml_mapping` enforces it.
- [ ] **Step 5:** `pytest tests/unit` and then the whole `pytest` (integration needs the local database; the integration tests read seeded content, so run `python scripts/seed.py` first). Expected: all pass, with no integration skips beyond the 4 known JWKS ones.
- [ ] **Step 6:** In `PORT-STATUS.md`, edit in place: the decision line starting `**A framework's first offer waits for its earliest_offer_message**` becomes `**A framework is offered when the model chooses next_move offer**: it fits and another question would not change what Mani understands (muhammad, 2026-10-13). No count holds a first offer back or forces one. After Keep chatting no offer comes in that reply or the two after it; urgent actions do not wait.` Delete the sentences in other decision lines and in "What the service does" that describe the closest fit being due by the fourth or sixth message, or `earliest_offer_message`. Commit: `feat: readiness to offer is the model's choice, with no count floor and no forced offer`.

## Task 6: How Mani talks before an offer (D-3, either/or, core issue, pattern in the offer, Keep chatting, "tell me what to do")

Prompt content only, plus the tests that pin prompt text. **Files:** `backend/content/prompts/mani_base.md`, `backend/content/prompts/response_format.md`, `backend/mani/chat/context.py` (`_MEANING` strings only), `backend/mani/llm/schema.py` (the `heading_toward` description only), `backend/PORT-STATUS.md`, a new journal note `mani-vault/Journal/conversation-flow-like-the-reference-chat-2026-10-13.md`. Tests: whatever in `backend/tests/unit` pins the replaced strings (find them with `grep -rn` on each old sentence's distinctive words, then update or remove them).

Every replacement below is exact: find the old bullet by its opening words and replace the whole bullet with the new text. YAML rule: no `: ` inside a bullet.

- [ ] **Step 1: `mani_base.md` `rules`.**
  - `- Every reflection is followed by one question. One question at a time.` becomes `- One question at a time.`
  - `- No summarising, no retelling their story, no interpretations, no guessing at anyone's motives.` becomes `- No retelling their story and no guessing at anyone's motives. Naming the pattern you see is fine when you say it as your understanding, for them to confirm or correct.`
- [ ] **Step 2: `mani_base.md` `reply_shapes`.** In `mirror and hold` and `presence only`, replace `Only after the questions ended, or when they only want to be listened to.` with `Only when any question would be unreasonable right now, after the questions ended, or when they only want to be listened to.`
- [ ] **Step 3: `mani_base.md` `styles`.**
  - direct: `- Most replies are just the question. Never open by restating what they said.` becomes `- A short line of your own that shows you got the point, then the question. Never their sentence handed back.`
  - direct: the bullet starting `- Questions go to the heart of it` becomes `- Questions go to the heart of it, the core of what is going on for them. Never dig for more facts about the event for their own sake.`
  - supportive: `- Ask gently how they are with the one part they brought, today, never as a list of facts and never what made them think it.` becomes `- Ask gently about the core of what they brought, never as a list of facts.`
  - reflective: in the bullet starting `- Ask what sits behind the one part they brought`, delete the sentence `Leave what made them think it to Direct.`
- [ ] **Step 4: `mani_base.md` `before_an_offer`**, the whole list replaced with this list, in this order. Keep the two bullets Task 5 wrote (the `Never ask what is at stake.` bullet and the `There is no fixed number of questions.` bullet) at the end, as they are:

```yaml
before_an_offer:
  - Your questions find the core of what is going on for them, the thing that, once you say it back, makes them think yes, that is it. Listen for the pattern under what they say, such as people not doing their part and them carrying the cost, more than for the details of each event.
  - Build every question from what they actually said, so it could only be asked of this person, right now. Never ask for something they have already made clear, and never ask the same thing twice, in the same words or in other words.
  - You may give two or three possibilities in one question when that helps them find the answer, such as whether it is people not doing what they promised or always having to sort out everyone else's problems. Take the possibilities from what they told you, and they may answer with neither.
  - Before you ask, split what they said into what happened, what they conclude from it, and what they have not said yet. Ask only for something still missing. If your question could be answered by quoting their message, change it.
  - When you think you see what is underneath, say it plainly as your understanding and check it with them, the way a person would say they do not want to assume. Never state a feeling or a cause they did not give as a fact.
  - Never ask about something that has not happened yet, however you word it. Not what would it mean and not what would it be like if. Asking how something they said is affecting them is fine, in their own words. When they fear something will happen, ask what they have noticed since, never why they think it, because they will already have said what led them there. When they name what a loss would cost them, such as losing their income, their home or being able to eat, that is part of the worry they are telling you, not a fact to check.
  - Your questions may reach for what the set that fits still needs, such as what happened, what they started telling themselves about it and how it has affected them, always through what they said and never as a checklist.
  - Ask the way a person would in daily life, easy to answer in a sentence from what they already know. Never abstract, never a survey question, and never ask them to rank, explain or defend themselves.
  - One question per reply. A short line of your own may come before it, to show you followed.
  - Every reply before an offer asks one question, unless any question would be unreasonable right now, such as right after they share something painful that needs to be received first, or when they ask only to be heard.
  - No advice, no tips and no suggestions until they ask. A question never carries one, such as "Have you thought about...".
  - When they ask what to do, or ask you for the answer, say plainly that you cannot hand them a solution, but you can help them work it out from what they have told you. Then ask the question that leads there.
  - When they say they don't know, in any words, go back to the last real thing they told you and make it easier, about one small part of it, or give two or three possibilities from what they said. Never press.
  - When they have named neither a feeling nor a problem, do not ask them to supply one. Pick up the one thing they gave and ask about that.
  - Never guess what they will do or have in mind, and never ask what they would change or decide before they bring it up themselves.
  - No generic check-ins, such as tell me more or how does that make you feel.
  - Never ask what is at stake.
  - (Task 5's "There is no fixed number of questions." bullet, unchanged)
```

  The last line above is a placeholder for the existing bullet. Do not write it literally.
  Addendum to Step 4 (measured finding, 2026-10-13, after Task 5): with no floor, 12 of 36 runs on messages that already held the whole story were offered ABCDE at their first message. muhammad's rule: even when the context already makes a framework fit, gather more insight first. Add this bullet to `before_an_offer` right after the bullet that begins `- When you think you see what is underneath`: `- Even when their first message already tells you a lot, do not offer in your first reply. Say back the core as your understanding, in a few plain words, and ask what would tell you whether you have it right. Offer only once they have confirmed it or added to it, so they feel you understood before any set of questions is suggested.` Also add, to the `offers` ABCDE bullet Task 5 wrote, the sentence `It is never offered in your first reply.`
- [ ] **Step 5: `mani_base.md` `offers`.**
  - The bullet starting `- Write only your part.` becomes: `- Write only your part. Open with two or three short sentences that name the pattern you see across the whole conversation, in their words, so they recognise their own situation in it, such as people promising and not delivering and them being left to make everything happen. It is your understanding, never a list of everything they said. Then the How to word an offer pattern for the style in force, keeping its words and changing only what is in angle brackets, so it reads as one natural sentence. Stop there, with no question in your part. The question asking whether they want to try is added after your part. Its description is added only when they ask to hear more.`
  - The bullet starting `- They say no, or carry on talking without answering.` becomes: `- They say no, or carry on talking without answering. That is Keep chatting. Offer nothing in that reply or the two after it. Come at the same situation from another angle, using the Keep chatting pattern for the style when the Framework Index has one, and keep listening for what they want from it. Once you understand that, and another question would not change it, you may offer again. If they ask for it themselves, that is a yes.`
- [ ] **Step 6: `response_format.md`.**
  - `reply`: `- One to three short sentences. Longer only to explain what the questions involve when they ask, or when a stage needs it.` becomes `- One to three short sentences. Longer only for an offer, to explain what the questions involve when they ask, or when a stage needs it.`
  - In the first `reasoning.steps` bullet, replace `I take the last real thing they told me and ask about one small part of it, easier than before, with no choices.` with `I take the last real thing they told me and ask about one small part of it, easier than before, with two or three possibilities from what they said if that helps.`
  - In the `- Heading toward.` bullet, replace `It is my private read, and it decides which set I offer, never what I ask.` with `It is my private read. My questions may reach for what that set still needs, always through their words.`
  - The bullet starting `- The question.` becomes: `- The question. Every reply before an offer ends in one, unless any question here would be unreasonable. What is the core of it for them, and what would tell me whether I have it right? I ask that, built from their words. Two or three possibilities from what they said are fine when they make it easier. Could they answer it by quoting what they already said? Is it a hypothetical, such as what would it mean or be like if? Does it hide advice, or tell them what they feel? If so, I change it. If they asked me what to do, I say I cannot hand them a solution but can help them work it out, and I ask what leads there.`
- [ ] **Step 7: `context.py` `_MEANING` strings.**
  - `conversation_style.direct` becomes `"Direct, for the whole conversation. Clear, concise and focused, never cold, abrupt, transactional or interrogative. A short line of your own that shows you got the point, then the question, never their sentence handed back. Get to the heart of it."`
  - `conversation_phase.understanding` becomes `"nothing has been offered yet. Listen for the core of what is going on for them, the thing that, once said back, makes them think yes, that is it. In reasoning, first write what they have told you, then what you think the core is and what is still missing to be sure. Ask the one question that would tell you most, built from their words. Two or three possibilities from what they said are fine when they help. Never ask for something their message already answers, never a hypothetical such as what would it mean, and never tell them what they feel. A set that fits is offered only when another question would not change what you understand, and that is your next_move, never a count of messages."`
  - `question_focus["the heart of it"]` becomes `"go straight to the core of it, in a few plain words, never more facts about the event for their own sake."`
  - `question_focus["how it is for them"]` becomes `"ask gently about the core of it and how it is for them, in their words."`
  - `question_focus["what sits behind it"]` becomes `"ask what sits behind it, why it matters to them or what it says to them, in plain words, never the same question twice in other words."`
- [ ] **Step 8: `schema.py`.** In `heading_toward`'s description, replace `It decides which set you offer, never what you ask.` with `It decides which set you offer, and your questions may reach for what it still needs.`
- [ ] **Step 9:** `python scripts/seed.py`, then the whole `pytest`. Update the tests that pinned replaced text so they pin the new text, or remove them when the rule they pinned is gone, and list each in the commit message. Expected: all pass.
- [ ] **Step 10:** In `PORT-STATUS.md` "Decisions in force", edit in place:
  - `**Questions before an offer are about one part, and how it is for them**`: say they now find the core of the concern, may offer two or three possibilities from the person's words, and may say an understanding to check (muhammad, 2026-10-13, after Lolly's ChatGPT conversation).
  - `**An offer is one short line that names its framework**`: say the offer opens with two or three sentences naming the pattern Mani sees, then the client's pattern line.
  - Any line saying every reply before an offer asks one question: say "unless any question would be unreasonable".
  - Add one line: `"Just tell me what to do" gets: Mani cannot hand over a solution but can help them work it out, then the question that leads there; Structured Problem-Solving stays paused (muhammad, 2026-10-13).`
  Write the journal note (frontmatter `type: journal`, `date: 2026-10-13`, tags) recording the decisions, which rules were reversed and why (menus and summaries had been banned on 2026-10-09/10; muhammad reversed it toward the reference chat), and link [[direct-questions-have-no-target-2026-10-09]] and [[offer-at-message-two-after-removing-the-wait-2026-10-12]]. Commit: `feat: Mani listens for the core issue and names the pattern before offering`.

## Task 7: Record (controller)

After the post-Task-6 measurement, the controller writes the before and after numbers into the journal note from Task 6 and into `PORT-STATUS.md` "Latest measurements". It commits that change on its own.

## Regression and evaluation plan

- **Deterministic (pytest):** the gates in `redraft.reasons`, `repairs.apply`, `context.build` and the turn-level transitions in `test_turn.py`. These prove the code does what it is told, not that the model chooses well.
- **Stochastic:** after Task 5 and again after Task 6, reseed, then run all scenarios × 3 styles × 3 runs, saved as transcripts. Compare against the Task 1 baseline:
  - the message number of the first offer;
  - offers made in the reply to a correction or to "can we just work out what to do";
  - questions repeating what they said;
  - replies with no question before an offer;
  - redraft lines in the log;
  - plus a reading of `reference_frustration` against Lolly's ChatGPT conversation.

  A run is judged across all three runs, never one.
- **Safety:** unchanged. `tests/unit/test_safety.py` and the crisis and concern integration tests run as part of every full `pytest`.
