---
type: journal
date: 2026-10-04
tags: [journal, frameworks, stages, evals, holds]
---

# The two holds, built and measured on the real model

Spec: `docs/specs/0003-stage-moves-on-one-answer/`. Earlier notes: [[stage-moves-on-design-2026-10-04]], [[stage-moves-on-first-real-runs-2026-10-04]]. Decision: [[ADR-013-a-framework-stage-moves-on-after-one-answer]]. What the service does now is in `backend/PORT-STATUS.md`.

Built: migration 011 (`holds`), the redirect mark on the reply's state, the recording rules in `repairs.apply`, the new `[ctx]` lines, the base prompt and content changes, the six scenarios with a rephrase asked twice and "suggest something", and `held` and `hold limit` findings in `eval_replies.py`.

## The numbers (54 conversations: six frameworks, three runs, three styles)

- Reached the body check: **54 of 54**. One run hit a provider timeout and was run again.
- A `hold limit` note (a hold after the extra turn was used): **0**. No stage got a second counted hold.
- Holds: 27 counted, 24 marked redirect. Three conversations held twice at one stage (DBT STOP `pause` in two runs, ACT `pull` in one), each because one of the two was marked a redirect.
- "I don't get it" held in about four cases in ten. ABCDE and Thought Reframe nearly always moved on instead (8 of 9 each).
- "Suggest something" at the choosing stage: Structured Problem Solving held in 5 of 9 (3 counted, 2 marked redirect); Behavioral Activation in 1 of 9.

## What I read, and what it says

- **The redirect mark is wrong every time I could check.** I read all 24. None was a safety branch, a framework that does not fit or one of the client's lines. Nine were DBT STOP `pause` with "I started typing again", which the file marks as a counted branch. The rest were rephrases and pick offers. The model reads `redirect` as "I am holding". Because a redirect is not counted, the limit under reads, and a stage can take two holds. The code did what the spec says. The weakness is the design: the bound depends on a mark the model gets wrong. Options for `/architect`: count every hold unless the reply names a safety branch in another way, or drop the mark and let `answered_if_unclear` branches that are not `counted` set the exception in code.
- **A pick request is often answered inside the next question.** At Behavioral Activation `choose` the model says "for cooking, could you chop one vegetable? Which feels smaller?", reports the next stage and moves on. That is one option with a reason, but it is not a hold and it asks the next stage's question. The note says "they cannot choose". "Suggest something" is not "cannot choose". The spec fixes the note word for word, so widening it is a spec change.
- **Rephrases are uneven.** Good: Behavioral Activation `barrier` ("What might make it hard to do that task after you finish work?"), Structured Problem Solving `outcome` ("What is the result you are looking for by Friday?"). Weaker: ACT `pull` often brings a new idea ("does it push you to try and change their mind?"), ABCDE `balanced` asks a new question, and DBT STOP `proceed` explains the method. These are for muhammad to judge.
- **A model that asks the wrong stage.** In one Behavioral Activation run the model asked the `barrier` question while the record said `begin`, so the next "I don't get it" was answered about a question the record did not hold. The code corrected the phase and could not know the text.

## muhammad's read (2026-10-04)

One transcript per framework, styles rotated (ABCDE supportive, Thought Reframe reflective, Behavioral Activation direct, Structured Problem Solving supportive, ACT Choice Point reflective, DBT STOP direct), each from the run with the most holds in that style. Verdict: **pass for all six**, with no wording notes. The things I flagged while reading stand as things to watch, not as failures: Mani writing its own reframe at ABCDE `balanced`, "a new thought" at Thought Reframe that nobody stated, a rephrase at ACT `pull` that brings options of its own, and a method explanation at DBT STOP `proceed`.

muhammad chose to fix the redirect mark and the `stage_note` wording through `/architect` before ADR-013 is accepted, so it stays proposed.

## After the redirect fix (same day, 54 conversations again)

Spec amendment: the model's redirect mark is removed and the code decides from the reply (AC-15), a stage that picks among options has a note of its own that leads with the offer (AC-16). Bar from muhammad: no redirect that is not real, no stage with two holds, the pick held in at least 7 of 9 at `choose` and at `select`.

- Reached the body check: **54 of 54**. Hold limit: **0**. Redirect holds: **0** (no scenario has a real one). Stages held twice: **0**.
- Counted holds: 63, up from 27, because a hold is now counted unless the reply quotes a redirect.
- "Suggest something": held **7 of 9** at Behavioral Activation `choose` (was 1) and **8 of 9** at Structured Problem Solving `select` (was 5). The bar was 7.
- The Behavioral Activation pick offer in the transcript I pulled says "The choice is yours to make, Sam. Does picking cooking suit you, or does starting with the gym seem easier?" It offers one option and asks if it suits them, but gives no reason. The note asks for a short reason and the model drops it.
- Other findings are unchanged noise: repeated openers 22, a repeated body check question 9, two replies with two questions, a feeling word ("confusing") the person did not use in two replies, and one "a lot". The `generic` finding is still noise.

## muhammad's read after the redirect fix (2026-10-04)

One transcript per framework, styles rotated as before. Verdict: **pass for all six**, no notes. What I had flagged stays as things to watch: a feeling word ("confusing") and "reached into everything" at ABCDE, a new angle in the Thought Reframe rephrase, a pick offer at Behavioral Activation with no reason, options of its own in the Structured Problem Solving `options` rephrase, and the method explained at DBT STOP `observe`. ADR-013 accepted.

## One question only (fourth round, same day, 54 conversations)

The rephrase note was reworded to ask for ONE question using `answered_ask` as its model and nothing after it, with a clause for a last message that asked none or two, and `eval_replies.py` gained a `rephrase questions` finding.

- Reached the body check **54 of 54** (the DBT STOP safety pause did not bite this run). First "I don't get it" held **9 of 9** for every framework. Second never held after a held first. Picks held 9 of 9 at `choose` and 8 of 9 at `select`. No redirect holds, no hold limits, no stage held twice.
- **`rephrase questions` findings: 0.** Replies with two question marks fell from 20 of 54 rephrases to none; the four left are a DBT STOP acting hold (3) and one pick offer (1), neither a rephrase. So the code trim (build task 14) was not built.
- muhammad read one transcript per framework: **pass for all six**, no notes. Things I noted while reading, not failures: the Behavioral Activation pick offer gives only a thin reason ("might be easier"); DBT STOP once answered "I don't know" at `proceed` with "Is that your next step?", which is not a question about anything they said.

## Things worth remembering

- A prompt rule that depends on the model setting a flag correctly is only as strong as that flag. Measure the flag before counting on it. Better, decide from what the reply says. Removing the flag fixed it, where rewording was only a guess.
- A note that states the exception after the general order gets the general order. Put the exception first on the stages where it can apply, and keep the shared note unchanged elsewhere.
- An eval run that dies on a provider timeout skips its own user cleanup. I removed the leftover `@eval.mani.local` users by hand with the script's own function.
- Applying one migration to the local database: `docker exec -i supabase_db_mani psql -U postgres -v ON_ERROR_STOP=1 -q < file.sql`. `supabase migration list` shows nothing applied here, so `migration up` would try all of them.
- Keeping the base prompt at 120 lines meant measuring each rewrite. The `stage_note` already lists the hold cases each turn, so the base only needed the rules and how to word them.

## Recognising the request in code (third round, same day, 54 conversations)

Spec amendment 3 (AC-17): the code recognises "I don't get it" and its kin, shows the model only the stage's own question as `answered_ask`, and records the counted hold itself.

- The first "I don't get it" was held in **9 of 9** conversations for five frameworks and 7 of 9 for DBT STOP (was 25 of 54 overall). The second was never held after a held first. Picks held 9 of 9 at both stages. No redirect holds, no hold limits, no stage held twice. Bar met.
- **Two conversations did not reach the body check** (both DBT STOP, run 3). Cause, traced with a spy on `repairs.apply` and the technique write: on some DBT STOP turns the model reports a safety concern ("potentially volatile situation"), the existing design pauses the framework for that turn, nothing is written, and the record lags a stage. It also explains the two DBT STOP rephrases that were not held. Not caused by this change; earlier runs reached 54 of 54 by luck. Worth its own look: the model over reports concern in the one framework about an urge to act.
- **A regression: 20 of the 54 rephrase replies ask two questions** (multiple questions findings went from 3 to 22). The note says to "end with the question in answered_ask", so the model writes its own reworded question and then adds the stage question. Many also bring a new idea ("What facts show that you might not be bad at your job?"). The note needs to say: one question only, the stage question said again in simpler words, nothing appended. The notes are fixed word for word in the spec, so this goes through `/architect`.
- The phrase "whats that mean" without an apostrophe is not in the list; `normalize` does not expand "whats".

Things worth remembering: a trace of what `apply` decided against what was written found the cause in minutes where reading transcripts did not. Print both sides of a boundary.
