# 0002 rationale: Mani speaks naturally

Build spec: [index.md](index.md). This file is the decision record; a build does not read it.

## Context

> ⚠️ Premise note: the replies sound robotic, but the tone may not be the model's only fault; part of it is code that rewrites replies into one shape. A prompt rewrite alone would leave that code pushing every reply back toward a question, so the spec changes both. A second concern: a short prompt tuned on the lite model may not carry over to the model chosen in row 35, so the check is re run there.

The client meeting of 2026-10-02 reported that Mani is robotic, too complicated, full of questions, and repeats "I hear you", so people do not feel heard. muhammad set the direction on 2026-10-04: natural, neutral, humble, down to earth, with "I'm in pain" answered by "Can you tell me more about it?". Workspace: `backend/` (API), a repo wide behaviour of the product, no frontend change.

How it works today. `content/prompts/mani_base.md` is 499 lines and `response_format.md` is 171. Both are seeded into the database and read by the model on every turn. The base carries a long list of rules, a table of six reply shapes, three full example conversations (about 100 lines) and a "never" list. Code then checks the draft: `redraft.reasons` asks the model again when the draft names a feeling the person never used (ADR-006), repeats the last question (ADR-011) or asks no question while Mani is still understanding (ADR-008), up to two extra calls. `repairs.apply` then drops any sentence that still names such a feeling. The result is that every reply carries exactly one question: 36 of 36 conversations on the baseline, questions equal replies in every conversation and style row. Not all of that is the redraft: code adds a permission question to every offer and the first stage question follows acceptance, so roughly two of the nearly four replies per conversation carry a question the prompt does not control. The check therefore counts questions on Mani's own words (AC-6), and task 3 measures the code change alone first.

The client's own style document breaks several of Mani's rules. Its Supportive example says "It sounds like a lot is happening at once" (the base bans "a lot") and "I'm here with you". The document also says the three styles are not three voices ("MANI always remains MANI"), that wording must not signal a style, that replies must not lean on stock phrases, and that Mani checks an understanding that goes beyond the person's words instead of stating it. It asks for two to four exchanges before a framework and says Mani should not keep asking questions to reach a number.

Short replies are read badly. `context.py` holds a fixed phrase list (`_VAGUE_REPLIES`: "yeah", "ok", "idk", "not sure" and so on). A match tells the model not to treat the reply as an answer and to ask a two way question. "Yes" and "no" are not on the list, so they get no hint, and the model sometimes answers a "yes" as if nothing had been asked. muhammad's requirement is that Mani must look at the previous conversation and understand what a bare "yes", "no" or "I don't know" means.

Baseline (2026-10-04, `scripts/eval_client_style.py`, three runs, 36 conversations, model `google/gemini-3.1-flash-lite`, `mani_base` md5 `84627c5f`, commit `476edf0`): one question in every reply; offers at exchange 2 to 6, three of 36 later than the client's two to four; stock phrases per conversation Supportive 0.6, Reflective 0.4, Direct 0.1; two dashes in 36 conversations. The scripted "Yes." lines answer the client's Mani questions, not the model's, so some of those turns are non sequiturs in the baseline; the noise is the same each run.

## Options considered

### Option 1: Rewrite the prompts only

Shorten `mani_base.md` and `response_format.md`, leave the redrafts and repairs as they are.

**Pros**:
- No code change, no test churn.
- Safety and offer rules untouched.

**Cons**:
- The forced question redraft survives, so every reply still ends in a question regardless of what the prompt says. The prompt and the code would disagree.
- The feeling and repeat redrafts keep nudging the model toward the old caution.
- Does nothing for the bare "yes" problem.

### Option 2: Rewrite the prompts, retire the tone enforcement, read short replies in context (chosen)

Short prompts; retire the tone redrafts and the sentence drop (as first proposed; the feeling and size redraft was restored after measuring, see the choices below); replace the `vague` hint with `short` plus the quoted last question; keep safety, offer vetoes, stage tracking and the label checks.

**Pros**:
- Prompt and code say the same thing, so the measured change can be attributed.
- Cuts up to two extra model calls per turn on today's redrafted turns.
- The short reply fix is built from data the code already has (the last Mani message).

**Cons**:
- The guarantees that ADR-008 added (a question every reply) and ADR-011 added (no repeated question) become measured and read, not enforced; ADR-006's feeling guarantee came back as one redraft after the first measurement.
- The tests and eval validators for the retired behaviour are deleted.

### Option 3: Put the reply's parts in the answer format

Make "mirror", "question" and "stage evidence" separate fields of the structured reply, so the shape is enforced by the schema (scope row 22).

**Pros**:
- Hard to break; no regex checks.

**Cons**:
- Fixes the shape of every reply, the opposite of the direction. Row 22 was dropped for that reason.
- A schema and storage change much larger than this decision needs.

### Option 4: Keep the checks but run a model judge on naturalness

A second model call grades each draft for naturalness and triggers a redraft.

**Pros**:
- Targets "sounds like a person" directly.

**Cons**:
- Adds a second unmeasured model to a path that is already too slow, and a judge's taste is no better evidence than the transcripts the team reads.
- Another redraft loop, which is what causes the uniform shape.

## Rationale

Option 2, because the forces in Context point at both the prompt and the code. The baseline shows the code's effect (36 of 36 conversations, exactly one question per reply) more directly than any sentence in the prompt could. Option 1 leaves that in place. Option 3 and 4 add machinery where the evidence says remove it. The client's own document is the reference for what natural means here, and it describes a model that checks its understanding as a question, varies its wording, and does not ask questions to reach a count.

Retiring enforcement is a real loss and the spec says so. ADR-006 exists because "That sounds incredibly stressful" reached a person who had not said stressed, and ADR-008 because a Supportive reply once only comforted. Those stay watched through counts on the check (AC-6, AC-8) and a human read (AC-5, AC-8, AC-9), and the feeling word list stays in use as a measurement. muhammad decided this on 2026-10-04 knowing the cost; the safety screen, which protects a person in danger, is not touched.

Order of work: measure, then change code alone, then change the prompt, so a regression can be traced to one change. This follows `mani-vault/Journal/measure-before-tuning-prompts.md`: one run is noise, so every comparison uses the mean of three.

Choices made by the architect, with the runner up:
- **The feeling and size redraft stayed (2026-10-04, after the build).** The prompt alone left feelings never used at 0, 2 and 2; with one redraft it is 0 of 36 and offers stayed 36 of 36. muhammad chose it over accepting the rate and over tightening the model in row 35. Runner up: accept 2 of 36 and read for it. The redraft is one extra call only on a turn that needs it, its note asks for no question, and nothing is trimmed, so it does not bring back the one shape the baseline showed.
- **AC-8 size and meaning parts.** The feeling count alone left "a lot" (5 of 90 in the stress conversation) and meanings stated as fact unmeasured, and AC-11 bans both kinds. Size gets a count with the baseline as its bar, because zero waits on the client's answer about "a lot". Meaning stated as fact gets a human count against the baseline on the same sample, not zero, because the baseline code never caught it and a prompt rule against it behaves like a word list. Runner up for both: record only, which gives the read no bar.
- **AC-9 is judged by a person against a rubric, not by a model or a word count.** The client's document says the styles differ in behaviour and not in words, so a phrase count is the wrong instrument, and a judge model was rejected earlier as a second unmeasured model. The rubric comes from the client's own lists and from the one line "Direct leads. Supportive accompanies. Reflective mirrors and explores." The reading points are the first reply and the reply that leads into the offer, because that is where the model's own words differ; code writes the offer description, permission question, consent line and stage asks, and those barely differ by style. The bar of 15 of 18 is a recommendation, not a measurement. Runner up: a model judge giving a confusion matrix. (Superseded by the amendment below: a fresh model reads blind and muhammad accepted its marks as final.)
- **Short replies get a code hint, not only a prompt rule.** The journal found prose rules did not hold on this model, while structure in the context block did. Runner up: prompt rule only, smaller but weaker. muhammad chose the hint.
- **The `reasoning` field stays, with three short steps.** Schema field order was the strongest lever in the earlier work; removing the field loses it. Runner up: remove the field, which needs a schema change.
- **The offer veto redraft notes stop saying "ask one question".** Left in, they would bring the forced question back through the offer path.
- **`response_format.md` shrinks to about 70 lines.** Most of it documents `[ctx]` lines and a reasoning checklist the new base no longer needs. Runner up: leave it, which keeps the old rules alive.
- **The sentence drop is retired as muhammad decided.** The cross check noted it saves no model calls, and only its keep the question rule forced a question, so keeping it without that rule was an option that held ADR-006's guarantee at zero cost. I recommended retiring because it has trimmed a correct reply before (ADR-008: a misspelled feeling word) and a cut sentence can read worse than the original; muhammad confirmed. The bar for AC-8's feeling count is zero on Mani's own words. The prompt alone did not hold it (0, 2 and 2 of 36 over three checks), so one redraft for a feeling or size word came back, with no trimming; see the first bullet above.
- **The `question_focus` line is retired.** It said every turn that Mani's question is about feelings. That is a style behaviour the style paragraphs now carry, and a per turn rule is one more thing pushing a question.
- **A bare "yes" to a safety question is a separate feature.** It is a hole in the screen today, not a tone issue, and `answering` is only a possible place to close it.
- **The log note for a draft that names an unspoken feeling stays.** It edits nothing and shows live traffic what the check shows offline.
- **The model and temperature stay as they are.** Row 35 changes the model on the same check; changing two things at once would hide which one helped.
- **Stock phrase and "comfort phrase" are one list.** The existing list covers both; a second list would drift.
- **"It sounds like" and restating (2026-10-04, after the first read).** muhammad read run 1 of the baseline and of the rewrite, blind, and marked two habits the check could not see: "It sounds like" and a sentence that says the person's words back before the question. Counts on the saved transcripts: "it sounds like" 49 of 105 replies in the baseline (32 of 36 conversations), 25 of 88 after the rewrite (19 of 36, six saying it twice). The rewrite halved the phrase but the base banned only three phrases, so the check reported 0 stock phrases while the client's eyes saw a repeat in half the conversations. A cause sits in the base itself: line 23 says "say back no more than is there". muhammad's call, over the client's own document, which uses "It sounds like". Runner up for the phrase: a redraft when the phrase appears, as for the feeling word. Not chosen first because ADR-012's direction is that tone is the instructions' job and a redraft is a second model call and a second guard to keep in step; kept as the fallback after two rounds if the prompt alone does not reach zero, and the choice is muhammad's.
- **The phrase list gets the near neighbour "It seems like" too.** A banned phrase is usually replaced by the closest one, and the cost of listing it is one more regex. "It feels like" and "You find yourself" are not listed: the first is a different, rarer shape and the second is restating, which a list cannot define.
- **Restating is read, not counted.** "You find yourself unable to stop scrolling" shares two words of five with "I cannot stop scrolling", and "Jumping from task to task makes it hard to gain any real traction" shares one with "I keep jumping from one thing to another". A word overlap count would pass both, and a list is the same overfitting the journal warns about. The read already exists for AC-8's meaning count, so AC-14 reuses its file. Runner up: a model judge, rejected earlier for the same reason as in AC-9. (The judge model was later used, see the amendment below.)
- **The restating rule covers understanding replies only.** The client designed the offer's first sentence, the stage asks and the opening after a correction to mirror (the framework files say a standalone mirror must be followed by a question, and "I just told you" must begin with what was told). Rows 6 and 18 rewrite those, so this change leaves them. Runner up: ban restating everywhere, which would contradict the client's framework content.
- **Reflective keeps mirroring, inside the question.** The rubric says Reflective mirrors one detail and asks about it. That stays true if the detail is in the question ("What is strongest about the racing thoughts?") and not in a statement before it. Runner up: loosen the ban for Reflective, which would let the habit back through the style that already restates most.
- **The bar for restating is "under half", as a share.** The only baseline is muhammad's own count, so the bar is relative: the share of eligible replies that restate after the change is under half the share before, both counted in one blind file. A share, not a raw count, because an earlier offer leaves fewer understanding replies. If the count before is under 4 the ratio is meaningless and the choice returns to muhammad. Runner up: zero, which a read of 12 conversations by one person cannot hold steady. (Counted by a blind model reader in one file, see the amendment below.)
- **The phrase change and the restating change are measured one at a time (4c, then 4d).** Banning "It sounds like" can push the model toward restating, and doing both at once would hide which one moved what, the lesson in `measure-before-tuning-prompts`.
- **Cross check (another model, 2026-10-04) changed the amendment.** Its main finding: the stock phrase count ran on full replies, so a sample reply after acceptance, or text the code adds, could break the zero bar; the count now runs on Mani's own words before acceptance, like AC-6 and AC-8, and the baseline is recounted that way. Also applied: one regex per phrase with "that sounds like", "as though" and a bare "Sounds like"; the recount recorded only, since the 0.3 and 0.2 bars are fixed numbers; "restate" defined as a sentence that is not a question and adds nothing; the "before" run taken after 4c, because the earlier read's "before" still carries the phrase and would give the source away; one three source file serving AC-8 and AC-14; AC-9 marking no longer carries a restating clause, and all 18 panic replies are re read blind after 4c and 4d. Not taken: its simpler option of one read, final against baseline, which loses the credit for 4d alone. A model that wrote the spec had missed that the count and the check disagreed about what "Mani's own words" means. (The 0.3 and 0.2 bars named here were replaced in the amendment below.)
- **Thresholds apply to the mean of three runs.** One run is noise (panic Reflective offered at exchange 6, 4 and 2 on the same script).
- **The check has no automatic gate.** There is no CI and the check costs real model calls; it runs by hand before the row closes.
- **The prompt keeps the banned size words.** I recommended replacing the list with one line ("do not make it bigger than they did"), because the client's own example says "a lot" and the list is the kind of rule the journal calls overfitting. muhammad kept it. The tradeoff is recorded in Consequences and revisited in Follow-up after the check.

## Superseded decisions (for ADR-012)

ADR-012 will state, without editing the old ADRs (ADR-012 itself is still proposed and takes the "It sounds like" and restating decision as part of its Decision):
- ADR-008 (every reply before an offer asks a question): superseded in full.
- ADR-006 (a turn may be redrafted once): stays in force for the offer vetoes and for the feeling or size redraft (one extra call, no trimming, no question asked); superseded only for the sentence trim.
- ADR-011: superseded for the repeated question redraft; the draft step for a request to pick and the first stage test stay (row 18 may revisit them).
- ADR-010 and ADR-007 are not changed here. Rows 18 and 6 revisit them.
- ADR-002 (one model call per turn) is closer to true again: the extra call is only for an offer veto or a feeling or size word never used.

## Amendment of AC-6, AC-7 and AC-9, 2026-10-04

The build finished with the final check (three runs, 36 conversations) short of three bars. muhammad chose, from options with a recommendation each, to set the bars to what the build can show and to say so in the spec, so `/check verify` judges the spec as written.

| Criterion | Bar before | Measured | Bar now |
|---|---|---|---|
| AC-6 questions per reply, own words | under 0.7, then under 0.5 | 0.54 final, 0.47 to 0.54 across checks, baseline 0.59 | lower than the baseline's 0.59 |
| AC-7 stock phrases per conversation | under 0.3 in each style, within 0.2 of each other; zero for "sounds like" and "seems like" | 0.83 / 0.00 / 0.67 (Direct, Reflective, Supportive); 14 uses of the two phrases, baseline 49 | below the recounted baseline 1.08 / 1.92 / 2.17; at most 16 uses of the two phrases; none said twice; openers no worse than baseline |
| AC-9 styles read as their own | 15 of 18, at least 4 of 6 per style | 10 of 18 (2 / 3 / 5), 5 of 18 on the first rewrite, 10 of 18 again after a second round of style lines | 10 of 18, no style under 2; the full bar moves to scope row 6 |

Why the bars were loosened and not the build changed further:
- AC-7. Two rounds of instruction change took the two phrases from 26 to between 3 and 15 and never to zero. A redraft would reach zero but is the kind of tone enforcement ADR-012 retires. The 0.3 bars were set against a baseline counted with three phrases; the same list with the two new patterns gives a baseline several times higher, so the old bars compared different things.
- AC-9. Every offer's wording says its questions are ones "you could go through together", so offers read Supportive in all styles. That sentence belongs to the offer rewrite (row 6), and task 4b may only change the three style lines. A second round of style lines gave the same score and raised restating from 42% to 58%, so it was reverted.
- AC-6. The earlier bar of 0.5 was settled on 0.47 and was not met by the later checks. A comparison with the baseline says what the client asked for, fewer questions, and is met by every check since the rewrite.

The model reader is a noisy instrument: it marked the same baseline conversations 13, 18, 17 and 14 of 30 restating across four files, and the identical "before" file 15 of 17 both times. Reads are compared inside one file only. The reads for AC-8, AC-9 and AC-14 were done by a fresh model, and muhammad chose to accept its marks as final without checking the flagged cases, a departure from the first text of those criteria, which had muhammad read. A cross check on another model (2026-10-04) then found the wording of the amended criteria left a verifier guessing; the criteria now name the final check (`style-lines-1`), the read of record, the printed figures and how the blind marks are tallied. Its note that AC-6's bar sits inside run to run noise and that AC-9's per style floor equals chance for one style is written into those criteria.
