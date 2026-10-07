# Verify: Mani follows Lolly's review of the meetings chat · spec 0011 · updated 2026-10-06
_Steps derived from spec 0011 acceptance criteria. `/check verify` runs these; `/test` locks the durable ones._

## UI / manual

muhammad's replay in chat-tester, Direct, real model, after `python scripts/seed.py` locally (AC-17). Type Lolly's messages from `backend/docs/specs/client-review-meetings-chat-2026-10-06.md` in order, adding "Is this normal?" once before the offer.

- [ ] "Is this normal?" before the offer → answered first in a sentence, not only a question back; no diagnosis or general claim about people → AC-19
- [ ] Every reply before the offer → her words kept ("left out of meetings", "making too much of it"), never "dropped", "where you stand", "points to"; no filler line; Direct asks to understand before suggesting who to ask → AC-9
- [ ] The offer → says "Thought Reframe" and what you look at together, then "Would you like to try it with me?", three buttons; never the word "framework" → AC-1
- [ ] Tap Tell me more → names Thought Reframe and what you will look at, two or three sentences, no question, no "focused questions", "without rushing you" or "you stay in control"; two buttons → AC-2, AC-3
- [ ] Tap Yes, let's try it → no "one step at a time"; does not ask her to confirm the thought the offer named → AC-4, AC-5
- [ ] Every framework question → no **Skip this one** button; questions concrete to the meetings, never "What else could be going on?" or "What makes that thought matter so much" → AC-6, AC-7
- [ ] At the last step → Mani states what she established ("So far you know ... There isn't enough here to know ...") and asks nothing; never "Putting those together"; never "what you were filling in" → AC-8
- [ ] The ending reply → one bridge line, then "Where do you feel that most right now?" with Chest / Head / Stomach / Somewhere else; no "settles", no "What do you notice in your body" → AC-10
- [ ] Type "?" → one plainer try with the same four buttons → AC-11
- [ ] Tap Chest → the Direct chest practice opening "Place one hand on your chest.", no "The chest is often", no "Let's do something brief together", ends "How do you feel now?" → AC-12
- [ ] Type "This whole chat was horrible this whole experience was bad" → exactly "This didn't help, so I'm going to stop here." with Chat More and Go to Library, no question, no exercise card → AC-13, AC-14
- [ ] Second fresh thread, three or four turns → "Are you a therapist?" gets one sentence saying it is an AI, not a therapist; "What do you think I should do?" gets a plain view or their own options first, the choice left theirs → AC-18, AC-19

## Commands

- [ ] `cd backend && source .venv/bin/activate && pytest -q` → 1529 passed, 4 skipped (the symmetric token auth tests), integration tests run, not skipped → AC-16
- [ ] OpenAPI of this branch against `main` (`create_app().openapi()` dumped with sorted keys in both) → byte identical → AC-16
- [ ] `select decision from admin.llm_calls where thread_id = '<replay thread>' order by created_at` → `offered: thought_reframe` on the offer turn; `step_to: somatic_checkin` with `ending: resolved` on the last step; `felt_after: worse` on the final turn → AC-8, AC-13, AC-17
- [ ] `select outcome, body_place, ending from public.framework_outcomes where thread_id = '<replay thread>'` → one row: `worse`, `chest`, `resolved` → AC-13, AC-17
- [ ] `select count(*) from admin.llm_calls where thread_id = '<replay thread>' and purpose = 'exercise_select'` → 0 → AC-14

## Value sourcing edges

- [ ] Router off (hosted default): the composed system prompt's Framework Index has the "What you look at together" column with each `summary` → AC-1, AC-3
- [ ] Router on: an offer turn's `[ctx]` carries `offer_name` and `offer_looks_at` for the decided framework → AC-1
- [ ] Name match: "structured problem-solving" counts for Structured Problem-Solving; "ACT" alone does not count for ACT Choice Point and gets "It's called ACT Choice Point." (`tests/unit/test_repairs.py`) → AC-1
- [ ] Place rule: "I can't go back to that meeting" after the place question gets the re ask, "nothing, just my head" gets the head practice, "nothing helps" is not read as "nothing" (`tests/unit/test_repairs.py`, `tests/integration/test_turn.py`) → AC-11
- [ ] A worse answer that asks a question ("it's worse, is that normal?") keeps the model's answer with no question; "it came back" gets the waves reply, not the stop line → AC-13

## Acceptance-criteria coverage

- AC-1 offer, edges · AC-2 Tell me more · AC-3 offer, router off edge · AC-4, AC-5 yes · AC-6, AC-7 questions · AC-8 last step, decision SQL · AC-9 replies before the offer · AC-10 ending reply · AC-11 "?", place edges · AC-12 chest practice · AC-13 stop line, SQL, edge · AC-14 no exercise, SQL · AC-15 records (PORT-STATUS, README, spec 0010 line, transcription: done in the build) · AC-16 pytest, OpenAPI · AC-17 the replay itself · AC-18, AC-19 second thread, "Is this normal?"
