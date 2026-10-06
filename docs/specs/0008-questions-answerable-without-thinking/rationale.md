# 0008. Rationale and options

## Context

The team lead pointed to four questions from Mani as it was before the current work (journal `questions-easy-to-answer-old-mani-chat-2026-10-05`) as the target: easy to understand, neutral, down to earth, and answerable without thinking first. The same chat shows the limit of that target. "What would feel most supportive for you right now?" and "Is there something specific that is feeling loudest for you right now?" both got "i dont know"; the two questions about something the person had already said got real answers; and two either/or questions to a person who said they were confused got "i cant decide". The client's "Good, Acceptable, Bad Conversations" document points the same way: its "Mani Standard" rewrites are one short line, then one concrete question about something specific the person named ("What time are you aiming for right now?").

The framework step questions in `backend/content/frameworks/` were rewritten in plain words earlier on 2026-10-05 (commit `c4e3d1e`), after the concert chat where the person said "what?" three times. They now read "What happened?", "What did you tell yourself about it?", "What makes you think that is true?". What still goes wrong is what the model does around them and on its own. In the 4 October run (`backend/.eval/client_style/style-lines-2`), the model wrapped step questions in restating clauses, 20 to 30 words long ("Since the presentation deadline on Friday is the problem you want to resolve, what do you know for certain about it?"), because every stage note says "ask stage_ask in their words, never bare". In the understanding phase it asked abstract questions ("What gives it that meaning?", "What is that conclusion based on?") and questions that make the person rank their own state ("Which of these parts is pulling the most on you right now?", "What part of the balance is most present for you right now?"). The good questions in the same run are short and concrete: "What was in that message?", "What keeps you there when you want to stop?".

Forces: ADR-012 retired the redrafts that enforced tone, because they pushed every reply into one shape and added model calls; the project's direction (rows 32 to 35) is short instructions and judgment, not rules in code. The base prompt body is at 113 of the 115 lines its test allows. The client's credit is low (about 3.7 dollars on 2026-10-05) and every real model run needs muhammad's yes. The client's "do not label" rule allows a check phrased as a question but not a stated feeling. Spec 0005 says a framework is offered only on a full fit of stated facts, and the client's overview maps "stuck" and "withdrawn" to Behavioral Activation and lists "the issue has not been clearly identified" and "the user cannot participate in reflective questions" among the times not to use ABCDE.

Not deciding leaves people saying "what?" and "i dont know" to questions they could have answered if asked plainly, which is the complaint the team lead and the client both raised.

## Options considered

### Option 1: Fix in place in the prompt and content, measured for free

Rewrite the stage notes and the base prompt's question rules, change Supportive's question rule and two body check lines, add the stuck check, and add deterministic checks that measure questions on content and on eval transcripts. No runtime change beyond the instructions.

**Pros**:
- No added model calls or latency; consistent with ADR-012.
- Small, reviewable diff: a few prompt lines, five notes, two content lines, plus tests.
- The checks keep measuring on every later run, including the model comparison in row 35.

**Cons**:
- Not a guarantee; the lite model does not always follow prompt rules.
- Needs a paid run to know whether it worked.

### Option 2: Option 1 plus a code trim of lead clauses

After the model replies, code removes a leading "Since ...," or "Given ...," clause from any question before saving.

**Pros**:
- The lead clause can never reach the person.
- Free and deterministic.

**Cons**:
- The trimmed question can lose its referent ("what do you know for certain about it?" with nothing for "it" to point to).
- Fixes one shape only; abstract and ranking questions pass untouched.
- Another text repair after the model, which the project has been removing.

### Option 3: Option 1 plus a redraft on question faults

When a question is long, has a lead clause or a flagged word, ask the model for a new draft.

**Pros**:
- The most reliable way to keep faulty questions out on the current model.

**Cons**:
- An extra model call on every faulty turn, slower and costlier.
- Brings back the tone redraft ADR-012 retired, and with it the pull toward one reply shape.
- A word list deciding runtime behavior is the phrase list pattern spec 0005 removed.

### Option 4: Authored questions only in the understanding phase

Give the model a bank of plain authored questions for the understanding phase, the way stage questions work, and have it pick one.

**Pros**:
- Every question is reviewed text, as plain as the team lead wants.

**Cons**:
- Mani stops following what the person said and reads like a form, the opposite of the Natural Mani direction.
- A large authoring job with the client, and the bank would never cover every situation.

## Rationale

Option 1 because the failures are in what the instructions ask for, not in a lack of enforcement. "Ask stage_ask in their words, never bare" literally requests the restating clause, and "Any question is gentle and about what would help" literally requests "What would feel most supportive?". Changing those words removes the cause; Options 2 and 3 would police a symptom the instructions keep producing. Option 1 also respects ADR-012 and the credit limit: no extra calls, and the measurement is free on content and on whatever transcripts later runs save.

The engineer's choices shaped the details. Plain step questions with one swapped word won over a short lead sentence because the model grows any allowed lead. The stuck check ("Are you feeling stuck?") is muhammad's: easy to answer, and a check is what the client's "do not label" rule asks for. muhammad first wanted ABCDE offered after it; he chose to keep spec 0005's fit rule once the client's documents were set beside it (stuck maps to Behavioral Activation, and ABCDE's "when not to use" list describes a stuck, confused person). The body check lines follow the client's own body question in the style document. Prompt only enforcement, the four flagged words, the 16 word bar and the small paid run were muhammad's picks of the recommended options.

Settled here without asking, as implementation detail: the stuck check is understanding phase only, since spec 0003 already moves a framework on after "I don't know" (runner up: also inside frameworks, rejected because it would hold a stage spec 0003 releases); the say back on a credited turn stays as its own sentence (runner up: drop it, rejected because ADR-015 needs the person to see they were heard); the counts live in `validators.py` so `eval_replies.py` scores them and `client_style_counts.py` reuses them (runner up: only in `client_style_counts.py`, rejected because the two chats run through `eval_replies.py`); the content test reads questions through the seed parser rather than by searching the files' text, so worked examples and "responses to avoid" tables, which the model never reads, are not checked.

Settled after the cross check (another model read the draft and found ten decisions left to the build; muhammad chose the recommended fixes): the stuck check uses fixed words, "Are you feeling stuck?", rather than the model's own, so it can be counted and cannot trip the feeling word redraft on "confused" (runner up: model's own words, rejected as unmeasurable); `names_their_situation` is kept as a reported signal of the one swapped word rather than retired (runner up: retire it for framework turns, rejected because it is the only measure of whether plain questions still connect to what was said); either/or is counted only outside a framework, with the client's fixed lines exempt, because inside a framework the picks options hold and the body route's closing choice are legitimate; and three `to_find_out` lines were reworded, because the Framework Index text steers the model's own questions and was a likely source of "What gives it that meaning?".
