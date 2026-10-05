# 0003 rationale: A framework stage moves on after one answer

The decision record for [index.md](index.md). `/develop` builds from `index.md`; this file is the why.

## Context

Inside a framework, Mani works through stages in order. Each stage has a question (`ask`), a test for when it is done (`ready_when`), and branches for unclear answers (`if_unclear`). Today the model decides when a stage is done. It reports the stage it is on in `state.step`, and the code only stops it skipping ahead: holding a stage, or stepping back, is always allowed (`techniques.Registry.validate_transition`). `ready_when` is sent in `[ctx]` and checked by nothing in code, but the base prompt says "staying on a stage until what it needs is clear", and 87 `if_unclear` branches across six frameworks, most of them asking the same stage again in other words, push the model the same way.

The result is the quizzing the client objected to in October 2026. "I don't know" gets the question again, reworded, or a list of options. ADR-010 added options and drafts for a person in panic; ADR-011 added a draft when asked to choose, and a redraft for a repeated question that spec 0002 has since retired. Scope row 18 asks for the opposite: any reply moves the stage on, within one reply.

Three forces shape it. First, prose does not hold this model: the panic journal note records that a note in `[ctx]` lost to a question sitting in `[ctx]`, and that the only fix was to withhold the text not wanted. Second, stages are not independent. Some stage questions name what an earlier stage produced ("What supports that belief?", "When will you do it?"); after "I don't know" they point at nothing. Third, the content mirrors the client's specifications, which are written as stages that hold until ready, and two stages (ABCDE `examine`, Thought Reframe `facts`) deliberately take two turns.

Not deciding leaves the frameworks feeling like a form to fill in, which is the main finding against the natural Mani work (rows 32, 33, 34, 18 in order), and keeps the client's open question about suggestions unanswered.

## Options considered

### Option 1: Code moves the stage before the call; authored questions for missing answers (chosen)

Each turn after the start turn, the code shows only the stage after the stored one, sends the stored one as `answered` without its question, and accepts a recorded step of that stage or a hold. Content loses `ready_when` after the first stage and the branches that ask again. Stages whose question depends on an earlier answer get an authored `if_earlier_missing` question, and the model chooses it from the history.

**Pros**:
- The old question is not in `[ctx]`, which is the one fix the journal shows working.
- The record follows what was really asked, so a hold for a client line does not skip a stage.
- No schema change; the content field rides the existing JSON column.

**Cons**:
- The model can still report a hold while asking the next stage, which then repeats it; only the eval sees that.
- 27 questions to author and keep matched to the client's specifications.

### Option 2: Code forces the record forward after the call

The model keeps choosing; whatever it reports, `clamp` records the next stage.

**Pros**:
- Smallest code change; the prompt and `[ctx]` stay as they are.

**Cons**:
- The text can ask the old question while the record says the stage moved, so the next turn skips a stage that was never asked.
- The current stage's question is still in `[ctx]`, so the repeat remains likely.

### Option 3: Prompt only

Rewrite the base rules to "move on after any answer" and leave the code.

**Pros**:
- No code; easy to reverse.

**Cons**:
- The model has held stages against prose before (ADR-010's measurements, the panic journal note).
- `ready_when` and the branches that ask again would still be in `[ctx]`, contradicting the rule.

### Option 4: Code tracks unanswered stages

As Option 1, but the model reports `answered: yes/no` each turn, a new column stores the unanswered stages, and the code sends the alternative question only when its dependency is missing.

**Pros**:
- Exact: the alternative question is sent only when it applies, and the gaps are visible in the data.

**Cons**:
- A new reply field, a column, a migration and a grant on `thread_technique_state` for a judgement the model already makes when it reads the history.
- One more field the model can fill wrongly, failing the turn as boolean fields have before (`SmartPrompt.decline`).

### Amendment 2026-10-04: the bounded holds

The first real runs (54 conversations, see the amendment below) showed two things muhammad wanted changed. A person who asks what a question means should get it said again once, and a person who cannot choose among options they named should be offered one with a reason, but neither may loop. That needs a limit on a stage's extra turns. These are the options for the limit and for how the two holds relate.

#### Where the count lives

**Option A: a column on `thread_technique_state` (chosen).** `holds smallint not null default 0 check (holds between 0 and 1)`, written by the same upsert as the stage.

**Pros**:
- The limit does not depend on the model remembering what it did last turn, which is the thing the journal says prose does not hold.
- `mani_service` already holds table wide insert and update, so no grant changes; `to_jsonb(s)` already carries every column into the turn snapshot.
- Reset on every move, so it can never go stale.

**Cons**:
- A migration, and one more field in the state row and the upsert.

**Option B: derive the count from the history.** Read Mani's last message and decide whether it was a hold.

**Pros**: no schema change.

**Cons**: nothing in the history says a reply was a hold; it would be a text guess, which is the kind of check the project has been removing.

**Option C: the model counts, from its own previous reply.**

**Pros**: no code, no schema.

**Cons**: exactly what failed before. A rule the model has to remember is the rule it dropped in the panic runs.

#### One rule or two

**Option A: one rule, one counter, named reasons (chosen).** Rephrase once, offer one option, and DBT STOP's acting hold all share the extra turn.

**Option B: a counter per reason.** A person could then be rephrased to once and offered an option on the same stage, two extra turns.

**Cons of B**: more state, a longer stage, and the loop muhammad does not want. One extra turn per stage is easier to explain and to measure.

#### Which holds count

**Option A: count every hold that is not marked a redirect (chosen).** The model sets `state.redirect` on a safety branch, a "does not fit" branch, the protective step, or one of the client's lines. A missed mark counts, which limits the conversation.

**Option B: count every hold.** Simplest, but a second reply after a safety branch would be moved on to the next stage, so someone who had described abuse could be asked what a belief means.

**Option C: count only holds the model labels as rephrase or offer.** A missed label means no count, so the limit fails open.

**Chosen because** A fails closed, and B is unsafe for exactly the replies the framework files go out of their way to protect.

## Rationale

Option 1 is the only one that removes the cause rather than adding a rule against it. The repeat happens because the stage the person has just answered is still in front of the model, with a `ready_when` that tells it to wait and branches that tell it how to ask again. Withholding that text and limiting the record to two values makes moving on the easy path. Option 2 keeps the text and makes the record lie. Option 3 is what ADR-010 and the panic note already showed failing.

The holds are kept to the cases where Mani did not ask a stage question at all (the client's three lines), where safety outranks the flow (a kept safety branch, and DBT STOP while the person is acting on the urge), and the existing `safety: concern` pause. Letting the model hold for "an unrelated reply" would give back the judgement that produced the problem. The model reports a hold by reporting the answered stage; the code records it without needing to know the reason, which keeps the reply schema unchanged.

For missing answers, an authored question per dependent stage keeps the clinical wording in content that people review, rather than letting the model improvise questions the client never saw (a general prompt rule), and costs no schema (Option 4). The model already reads the history to word every question, so judging whether the earlier answer exists is the same reading. muhammad writes the 26 questions; the stage list was judged per stage by whether its own question still makes sense without the earlier answer, so stages such as Structured Problem Solving's `facts` ("What do you know for certain?") need none.

The first stage keeps `ready_when` and all its branches because ADR-011's start turn still uses them: what the person said before accepting is judged against the first stage, and the branches shape how that first question is asked (an event too broad, an assumed motive). That decision was measured (the confirmation question went from 9 of 9 to 0) and row 18 does not touch the start turn. The first stage branches that ask the same stage again are marked `start_only` so they shape only that start turn and never invite a hold afterwards. Every turn that is not a move on turn (a waiting offer, a typed or tapped yes, a stored `offering`, the somatic stages) keeps today's block and rules, so the change touches only the turns row 18 is about.

Splitting the two part stages keeps the rule simple (one question, one answer, move on) and follows the client's own order, supporting evidence then challenging evidence. Both second halves already exist as branches, so their questions are not new text.

"Pick for me" stays a single stated step because ADR-011 measured that a list given to someone who has said they cannot choose does not help, and stating it rather than asking keeps the reply to one question with the next stage's question.

### The bounded holds

The loop risk muhammad named is real and the code can end it: with a stored count, a stage takes at most two replies from the person, whatever the model does. The model is told when its extra turn is used (`hold_used`), so the usual case is the model obeying, and the code's forced move is a backstop that costs one skipped question at worst. Only an explicit hold keeps a stage: a reply with no state, an unknown stage or an earlier one records the next stage, because the review of this amendment showed that any other rule lets a lost state keep the same stage on screen for ever. DBT STOP's acting holds are counted, with a flag on the five branches so the model can tell them from the redirects; a person still acting on the urge after one extra turn goes on to `observe`, whose question works either way. Offering one option with a reason, and asking whether it suits them or another is easier, keeps the person deciding: that is what the client's Structured Problem Solving boundary ("never choose for them", "must not disguise a recommendation as the user's decision") allows, and it is why the earlier "state one step" wording of AC-5 was wrong for that framework. It is limited to stages that pick among options already named, because offering one where nothing was named means inventing it, which is closer to choosing for them.

## Branch inventory

Every `if_unclear` branch in the six framework files, as of 2026-10-04, and what the build does with it. *Unchanged (offering stage)* means the offering stage, which this spec does not touch. *Keep (first stage, start only)* means a first stage branch that asks the same stage again: it is used on the start turn and marked `start_only: true`, so it is never sent after. *Keep (first stage; a hold after the start turn)* and *Keep* mean the branch leaves or redirects the framework, or protects someone; it is sent as `answered_if_unclear`, and when it fires it is a hold. *Becomes ask* means it is the question of a new split stage. *Drop* means it asks the same stage again; after this change the next stage is asked instead.

### ABCDE

| Stage | Branch (`when`) | Treatment |
|---|---|---|
| offering | the user declines | Unchanged (offering stage) |
| activate | assumed motive | Keep (first stage, start only) |
| activate | event too broad | Keep (first stage, start only) |
| activate | abuse, threats, coercion, harassment, discrimination | Keep (first stage; a hold after the start turn) |
| belief | a feeling instead of a belief | Drop |
| belief | several beliefs at once | Drop |
| consequence | consequence unclear | Drop |
| examine | part of the belief is accurate | Drop |
| examine | no contrary evidence comes to mind | Drop |
| examine | what supports the belief has been said, and what challenges it has not | Becomes ask of `evidence_against` |
| examine | the user has named evidence that challenges the belief | Drop (`balanced` asks next) |
| balanced | falsely positive | Drop |
| balanced | cannot form a balanced belief | Drop (`closing` uses `if_earlier_missing`) |

### Thought Reframe

| Stage | Branch | Treatment |
|---|---|---|
| offering | the user declines | Unchanged (offering stage) |
| thought | several thoughts appear | Keep (first stage, start only) |
| thought | no clear thought | Keep (first stage, start only) |
| thought | identity level rather than moment level | Keep (first stage, start only) |
| thought | abuse, threats, coercion, harassment, discrimination | Keep (first stage; a hold after the start turn) |
| significance | a feeling word instead | Drop |
| facts | no contrary information | Drop |
| facts | the thought is supported by an established fact | Keep on `facts_for` (the framework does not fit; redirects) |
| facts | what supports the thought has been said, and what does not has not | Becomes ask of `facts_against` |
| alternative | no alternative offered | Drop |
| reframe | falsely positive | Drop |
| reframe | it does not feel true yet | Drop |

### Behavioral Activation

| Stage | Branch | Treatment |
|---|---|---|
| offering | the user declines | Unchanged (offering stage) |
| stopped | "Everything." | Keep (first stage, start only) |
| stopped | several activities named | Keep (first stage, start only) |
| stopped | a wish but no activity | Keep (first stage, start only) |
| stopped | injury, severe or sudden physical symptoms, intoxication | Keep (first stage; a hold after the start turn) |
| matters | it does not matter | Drop |
| choose | wants to address everything | Drop |
| choose | asks Mani to pick | Drop (the base prompt's pick for me rule) |
| manageable | still too large | Drop |
| manageable | cannot identify an action | Drop |
| begin | cannot choose a time | Drop |
| barrier | cannot identify a barrier | Drop |
| barrier | the action depends on someone else | Drop |
| barrier | the action is unsafe | Keep (safety) |

### Structured Problem Solving

| Stage | Branch | Treatment |
|---|---|---|
| offering | the user declines | Unchanged (offering stage) |
| problem | too broad | Keep (first stage, start only) |
| problem | several combined | Keep (first stage, start only) |
| problem | framed as unsolvable | Keep (first stage, start only) |
| problem | abuse, a threat, or emergency danger | Keep (first stage; a hold after the start turn) |
| problem | a medical, legal or financial decision that needs a qualified person | Keep (first stage; a hold after the start turn) |
| problem | already described before the stage began | Keep (first stage, start only) |
| facts | prediction stated as fact | Drop |
| facts | not enough information | Drop |
| facts | a time critical risk is still open | Keep (protective step, ADR-010) |
| control | focuses on another person | Drop |
| control | cannot say what is theirs to do | Drop |
| outcome | outcome too broad | Drop |
| outcome | cannot say what they want | Drop |
| options | only one option | Drop |
| options | asks Mani to decide, or cannot name any option | Drop (the base prompt's pick for me rule) |
| compare | only benefits named | Drop |
| compare | only risks named | Drop |
| select | cannot choose | Drop |
| first_action | action too large | Drop |
| first_action | cannot name a first action | Drop |

### ACT Choice Point

| Stage | Branch | Treatment |
|---|---|---|
| offering | the user declines | Unchanged (offering stage) |
| situation | focuses on controlling another | Keep (first stage, start only) |
| situation | the situation is actually controllable | Keep (first stage; a hold after the start turn) |
| situation | abuse, threats, coercion, harassment, danger | Keep (first stage; a hold after the start turn) |
| present | "I don't know." | Drop |
| present | several experiences at once | Drop |
| pull | cannot identify the pull | Drop |
| matters | names what another person should do | Drop |
| matters | cannot identify what matters | Drop |
| matters | answers with how it feels instead of what matters | Drop |
| toward | response depends on another person | Drop |
| toward | response creates danger | Keep (safety) |
| toward | framed as removing the feeling | Drop |
| action | action too broad | Drop |
| action | wants the thought removed before acting | Drop |

### DBT STOP

| Stage | Branch | Treatment |
|---|---|---|
| offering | the user declines | Unchanged (offering stage) |
| stop | "I cannot stop myself." | Keep (first stage; DBT hold) |
| stop | already acted | Keep (first stage; DBT hold) |
| pause | returns to the action | Keep (DBT hold) |
| pause | wants to leave | Keep (DBT hold) |
| pause | the pause needs an anchor | Keep (DBT hold) |
| observe | "I don't know." | Drop |
| observe | assumed motive | Drop |
| observe | several urges at once | Drop |
| proceed | still wants the original action | Drop (watched; see Follow-up in index.md) |
| proceed | cannot identify a response | Drop |
| proceed | chooses retaliation | Keep (safety, harm to another) |

**Totals**: 87 branches. 6 on offering stages, unchanged. 22 on first stages, all kept: 13 start only, 9 holds after the start turn (including DBT STOP's two). 8 kept on later stages, all holds. 2 become the questions of the split stages. 49 dropped.

## Superseded decisions (for ADR-013)

- ADR-010, "Cannot say": up to three options or a draft at the first "I don't know" → "I don't know" moves on with no options. The protective step for a time critical risk and the start turn's "no confirmation" stay.
- ADR-011, "A request to pick gets one draft step ... and asks whether it works" → at a stage that picks among options they named (Behavioral Activation `choose`, Structured Problem Solving `select`), one of their options with a short reason and a question whether it suits them or another is easier, held once; at every other stage "suggest something" moves on with "that one is yours to say". "The first stage, by its own test" stays. The repeated question redraft was already retired by spec 0002.
- Spec 0002, "Stage validation and `ready_when` in `[ctx]`: Keep" → kept for the start turn only.
- `mani_base.md`, "staying on a stage until what it needs is clear" and "after two tries, try a different angle" → removed.

## Amendment 2026-10-04: what the first real runs showed

Run with `scripts/eval_replies.py`, one scenario per framework started inside it, three runs, every style: 54 conversations. One stage per reply and no repeated question in all 54; 50 reached the body check, and the four misses each followed a hold. Four holds fell outside the first closed list: three Behavioral Activation replies to "what do you mean?" at `barrier`, and one Structured Problem Solving reply that gave the hand off text but reported `closing`. "What do you mean?" was answered in a clause and moved on in 51 of 54. "Pick one for me" at Behavioral Activation `choose` gave one step in 9 of 9; "Tell me what to do" at Structured Problem Solving `options` got "that is yours to decide" in 8 of 9, because that framework's boundaries say never to choose for the person. Changing the base prompt's wording did not move it.

muhammad's decisions (2026-10-04): offer one of the options they have with a reason and a check, at the stages that pick among named options only; say a question again once, in plain natural English that leaves the person feeling heard, and move on if they still do not understand; one extra turn at most, so a conversation never loops; he left the single rule, the storage and the redirect exemption to this spec.

Transcripts: the scratchpad runs are summarised in `mani-vault/Journal/stage-moves-on-first-real-runs-2026-10-04.md`.

## Amendment 2026-10-04 (2): what 54 real conversations showed about the redirect mark and the pick offer

Evidence: `mani-vault/Journal/stage-moves-on-holds-measured-2026-10-04.md`. All six frameworks passed muhammad's read (2026-10-04) and every conversation reached the body check with no hold limit, but two things did not work as designed.

**The redirect mark was wrong 24 of 24 times.** The model set `state.redirect` on every hold of the redirect kind and none was one. Where it did it:

| Where | Marks | What the code could see |
|---|---|---|
| Stages with no safety, fit or protective branch (`choose`, `matters`, `select`, `balanced`, `pull`) | 9 | No branch exists to cite |
| DBT STOP `pause`, whose three branches are all counted | 9 | Only counted branches exist |
| `barrier` and `proceed`, which do have a safety branch; the replies were rephrases | 6 | A branch exists, its words are absent from the reply |

For the DBT STOP marks the note is a probable cause: it said "or, with redirect set to true, another branch in answered_if_unclear applies", and the counted branch sits in that same line.

*Option A: the code decides from the reply and the model marks nothing (chosen).* A hold is a redirect when the reply, or Mani's message just before it, carries the opening words of the fixed part of a redirect branch of the answered stage, or one of the client's three lines. Pros: 18 of the 24 false marks are caught by structure alone, the other six by the text test; keeps the redirect exemption, which is the reason the first design rejected counting every hold; removes a schema field the model has just been shown to misuse; it also records a hold when the model quotes a safety branch but reports the next stage, which today moves two stages on after a safety reply; the repository already finds a branch in a reply by its opening words (`practice_in`). Cons: a real redirect the model paraphrases is counted; a branch that is only a placeholder, or only scenario wording, cannot be matched.

*Option A2: keep the mark, and check it against the reply.* The first form of this amendment. Pros: smaller change. Cons: a branch quoted but not marked is counted, so the marks add nothing except the cases where the model quoted a branch and forgot to mark it, which are the real redirects. The independent review pointed this out and muhammad chose A over A2.

*Option B: count every hold and drop the mark.* Pros: the simplest, an absolute bound of one extra turn. Cons: the case the first design rejected it for, a person who described abuse and replies again is moved to the next question, with only the safety screen between them and it.

*Option C: reword only and measure again.* Pros: no code. Cons: the bound would still depend on a mark the model has just been shown to get wrong, and the real redirect cases were not in the measurement, so a good re run would prove little.

muhammad chose A (2026-10-04). The independent review (a second model, read only) also found that after a safety branch has been quoted once the base forbids saying the phrase again, so the next reply paraphrases and would be counted; muhammad chose to honour the previous Mani message too (one more uncounted turn, no new state), and to leave ending or pausing the framework on a safety branch as follow up work. It also found that abuse described at a stage after the first has no branch to quote and that the safety screen is a weak backstop (about ten explicit phrases, current message only); both are recorded in Consequences and Follow-up, not solved here.

**"Suggest something" was folded, not held.** At Behavioral Activation `choose` the model held in 1 of 9 conversations; Structured Problem Solving `select` held in 5 of 9. The rest named one option inside the next stage's question and reported the next stage ("What is the smallest version of cooking you could manage?"), which chooses cooking for the person without asking. Two causes in the note: it said "cannot choose", which "suggest something" is not, and the exception came after "Ask stage_ask now". The note is fixed word for word in the spec, so the fix is a spec change.

*Option A: a note of its own on a flagged stage, leading with the offer (chosen).* The exception comes first and names a request to suggest or pick; other stages keep the shared note, so nothing else moves. Cons: a third note to keep in step.

*Option B: widen the shared note.* Smaller, but the exception stays behind "ask stage_ask now".

*Option C: accept the folding.* Drops the hold from AC-13. Rejected: the client's Structured Problem Solving says never choose for them, and the folded reply does.

The bar for the re run (muhammad, 2026-10-04): no redirect that is not real, no stage with two holds, the pick held in at least 7 of 9 at each of the two stages, and one transcript per framework read again.

## Amendment 2026-10-04 (3): AC-14 was not met on the real model

Found by `/check verify`: the first "I don't get it" was held in 25 of 54 conversations (ABCDE 3, ACT Choice Point 4, Behavioral Activation 2, DBT STOP 7, Structured Problem Solving 5, Thought Reframe 4), and in the live check at ABCDE `evidence_against` it was not held. The rest moved on with a clause, which is the safe default but not what AC-14 says.

Two causes in how the turn is built. The shared note puts the exception after "Ask stage_ask now", the same shape that made "suggest something" fold into the next question (AC-16). And a message of three words or fewer ("I don't understand", "I'm confused") has `their_last: short` and an `answering` line, which the base reads as "an answer, not a gap, go on from it", the opposite of what was asked. A four word message such as "I don't get it" carries neither, so that second cause only affects the shortest requests.

*Option 1: soften the AC to "may stay, at the model's reading".* Pros: nothing to build. Cons: weakens what muhammad asked for, and ABCDE and Thought Reframe would rarely hold.

*Option 2: recognise the request in code and lead the note with the rephrase (chosen first).* The phrase check sends `asked_again: yes` and a note that leads with saying the same question again. Pros: the trigger does not depend on the model noticing; the same shape took the pick offer from 1 of 9 to 7 of 9; the second request still moves on, so the bound holds. Cons: a phrase list misses paraphrases and can fire on a request that is really about the situation; the model can still fold the request into the next stage's question, because that question is on the page.

*Option 2b: the same recognition, and the next stage is withheld (chosen after the independent review).* On a rephrase turn the model sees only the stored stage's own question as `answered_ask`, so there is nothing to fold the request into, and the code records the counted hold itself, as AC-15 already lets the code decide redirects. Pros: the hold is deterministic, the model has the real question to simplify instead of digging it out of the history, which also repairs the case where the last message was a redirect, and the bar measures wording and recognition, not whether the model complied. Cons: one stated exception to AC-1 (the answered stage's ask is sent on that turn), and a false positive costs one turn with the model shown the wrong frame.

*Option 3: reword the shared note only.* Cons: the same approach did not move the pick request until the note got its own variant, and it still depends on the model deciding it was asked.

muhammad chose Option 2 (2026-10-04) and, after the independent review, the stronger form 2b. The bar: the first request held in at least 7 of 9 conversations of every framework, the second never held when the first was.

The review (a second model, read only) also found, and the spec now fixes: "I still don't get it" was not recognised because of the word "still" (filler words are removed before matching); statements about the situation such as "I don't understand why he left" passed a six word cap (a list of blocked words); a rephrase that used the client's "I misunderstood" line is a redirect and so never counted, which let it repeat forever (client lines are not evidence on a rephrase turn, and the previous message rule uses branch words only); where the conditions are checked, which the spec had left open (`build` and `apply` each combine the raw phrase match with their own test); `answered_picks_options` competing with the rephrase note (not sent on a rephrase turn); and the walk test's "what do you mean?" reply, which is now a recognised request.

Choices made in the design, not asked: the cap is eight words with a list of blocked words, because longer messages that contain a phrase are mostly statements about the situation; the request wins over the pick note, because someone who did not understand a question has not yet chosen anything; the line is sent only when `holds` is 0, because the used note already says to move on after a second request; a tap is never read.

## Amendment 2026-10-04 (4): the rephrase asked two questions

The first run of the request recognition (AC-17) met the hold bar, but 20 of the 54 rephrase replies asked two questions, and several brought a new idea (journal: `stage-moves-on-holds-measured-2026-10-04`). Cause: the rephrase note said to say again what they may not have followed and "end with the question in answered_ask". The model wrote its own reworded question and then added the stage question as a second one. The base allows one question per reply.

*Option A: the note asks for ONE question, with answered_ask as its model and nothing after it (chosen, muhammad's wording).* The reworded question is the question; nothing is appended. Pros: removes the two question shape at its source, and a single question has less room for a new idea. Cons: a model that still adds a second question is not caught in code; the bar counts it.

*Option B: trim a second question in code.* On a rephrase turn keep the reply through its first sentence ending in a question mark and drop whole sentences after it, which cuts no sentence in half, like the repairs that remove an offer sentence. Pros: a guarantee. Cons: a first question that is only a check ("Does that make sense?") would be the one kept, and it hides what the model wrote. Specified as build task 14 and built only if the re run still shows the shape (muhammad, 2026-10-04).

The independent review (a second model, read only) found, and the spec now fixes: two sources for "the question to say again" (the history or `answered_ask`), which differ after an earlier answer question, a redirect, or a question of their own, so the note and the table now use one precedence and a clause for a last message with no question or two; a branch reply on a rephrase turn needing "with nothing added"; the eval finding counting more than one `?` but not zero, so the bar says exactly one; findings in `eval_replies.py` that carry no turn, so a finding per request is added; and the second request being answered under the used note, which this change does not touch, so the bar covers rephrase turns only. Recorded as deliberate: the lead-in "what in your last message they may not have followed" is gone from the note, so a person who did not follow a reflection and not the question gets the question only. A near copy of `answered_ask` instead of simpler words is not measured; muhammad's read covers it.

The bar in AC-9b gains: every rephrase turn reply has exactly one `?`, and any finding triggers task 14.

## Amendment 2026-10-04 (5): more ways to say "I did not understand"

Scope row 38. A check of 40 typings against the list showed that apostrophe-less typing mostly works already, because the shared word cleanup expands "dont", "im" and the like. The real gaps were "whats that mean" (the cleanup has no entry for "what's" or "whats", and the spec does not touch that table), the past tense ("I didn't understand"), "say that again" and "repeat that", the texting forms "what do u mean" and "wdym", and "that doesn't make sense".

*Option A: add typings and close forms (chosen, muhammad 2026-10-04), with the risky ones anchored after the independent review.* The review (a second model, read only) found that the past tense and "say that again" and "repeat that" read as a story or an objection inside a longer sentence ("I applied and didn't get it", "No, you didn't understand", "I don't want to repeat that", "please don't say that again"), and that a false match is worse than a lost turn: the old question is reworded at someone who was not asking. So those phrases are an *anchored* set that counts only when the message is the phrase, with at most "i", "can you" or "could you" before it and a short list of words after it. Safe forms (whats that mean, what do u mean, wdym, wym, what did you mean) stay free. "what that means" is replaced by the forms that start "do not know", "not sure" or "no idea". "mean for", "means for" and "not want" join the blocked words. The count is six free phrases and fourteen anchored ones added. The review also noted that a recognised request overrides AC-5's reading of "I don't know" as stuck, now said in AC-17, and that the earlier negative test case was over the word cap, so the typed negatives are listed.

*Option B: only "whats that mean".* The smallest change. *Option C: also the bare words "huh", "what", "confused", "unclear", "explain".* Rejected: "what?" can be surprise and "explain" can be a request about the situation, and each false hold costs a turn.

Not added on purpose: bare "huh", "what?", "confused", "unclear" and "explain". They fall to the model, as before.

