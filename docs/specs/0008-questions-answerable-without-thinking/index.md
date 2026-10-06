# 0008. Mani's questions can be answered without stopping to think

**Date**: 2026-10-05
**Status**: In Progress

## Summary

The team lead wants Mani's questions to sound like the earlier Mani's best ones: plain, neutral, down to earth, and answerable straight away ("What does being alone feel like for you today?"). The framework step questions were already rewritten in plain words today, but the model still wraps them in a restating clause ("Since you've mentioned that you find yourself losing an hour to scrolling, what makes...") and asks abstract or ranking questions of its own ("What gives it that meaning?", "Which part is pulling the most on you?"). This spec changes the instructions so every question is short, about one thing the person said, with nothing in front of it. It also adds one plain check ("Are you feeling stuck?") for someone who says they are stuck, and rewords two body check lines. Enforcement is by the prompt alone, measured by free counts and tests, then one small paid run of two chats once muhammad says yes.

## Requirements

Linked scope feature: row 40 in [docs/scope/conversation.md](../../scope/conversation.md), "Mani's questions can be answered without stopping to think". Source material: the old Mani chat and the team lead's four picked questions (journal `questions-easy-to-answer-old-mani-chat-2026-10-05`), the client's "Good, Acceptable, Bad Conversations" document ("Mani Standard" rewrites), the client's style document, and the questions in the 4 October run (`backend/.eval/client_style/style-lines-2/transcripts.md`). muhammad allowed rewriting client wording for comprehension on 2026-10-05.

**User stories**:
- As a person talking to Mani, I want each question to ask one plain thing about what I said, so that I can answer without working out what is being asked.
- As a person who is stuck or confused, I want Mani to check that simply and then ask me something easy, so that I am not handed choices I cannot make.
- As the team lead reviewing transcripts, I want the questions to read like the earlier Mani's best ones, in all three styles.

**Acceptance criteria**:
- **AC-1** (a step question is asked plainly): every instruction that tells the model to restate before a stage question, or to put it in their words and never send it bare, says instead to "ask it plainly": as written, or with one of their words in place of a general one, with no clause in front of it. That covers, in `backend/mani/chat/context.py`, `_TOLD_NOTE`, `_TOLD_IF_YES_NOTE`, `_MOVE_ON_NOTE`, `_PICKS_NOTE`, `_HOLD_USED_NOTE` (near line 597), the `framework_starting` note (lines 472 to 476, "say it back in a clause ... in the same reply") and the plain stage note (lines 480 to 481, "never send it bare"); the "They say yes" line in `backend/content/prompts/mani_base.md` (line 88); and the `framework_starting` line in `backend/content/prompts/response_format.md` (line 92). On a turn where what they told before accepting is credited (ADR-015, and the `framework_starting` case where it meets `stage_ready_when`), the say back stays, as its own short sentence before the question, never a clause leading into it. The client's opening line on that turn ("Okay. I'll guide you through it one step at a time.") does not count toward the "one or two short sentences" rule. A unit test asserts every stage note contains "ask it plainly" and none contains "never bare" or "never send it"; the existing assertion on the plain note text (`tests/unit/test_chat_context.py` near line 952) follows the new text.
- **AC-2** (what a question looks like, before and inside a framework): the "How you talk" section of `mani_base.md` says a question asks one thing they can answer straight away, about something they said, in fewer than 16 words, and never opens with a clause ("Since you...", "Given...", "Now that..."). It never asks them to rank or judge their own state ("what is loudest", "what is most present for you", "what is pulling on you most"), and never asks what would help or feel supportive before they have named something. The list of words Mani never uses gains "conclusion" and "meaning". Existing lines that contradict this are rewritten, and these are where the room comes from: line 32's "Ask about a meaning of your own, never state it" (dropped; checking an understanding as a question stays covered by the client's "do not label" line elsewhere), line 37's "which part bothers them most" (becomes "what happened, how it went, what they did next"), Reflective's "what is strongest, what sits under it" (becomes "ask about it plainly"), and "give a short conclusion" in "Ending gently" (becomes "a short summary", since "conclusion" is now a banned word in questions and the instructions should not use it either). The base prompt body stays within the 115 lines `tests/evals/test_base_prompt.py` enforces (113 today) with no other behavior line removed, and `test_the_hard_rules_are_still_said` gains the new question rule.
- **AC-3** (Supportive stays gentle and concrete): the Supportive line in "The three styles" reads that any question is gentle and about something they said, in place of "about what would help". Direct is unchanged; Reflective changes only as AC-2 says.
- **AC-4** (a person who is stuck, before any offer): when, before any offer, they say they cannot think, cannot decide or are confused, or answer "I don't know" twice running, Mani may ask exactly "Are you feeling stuck?", the same words in every style, so it is countable and never trips the feeling word redraft ("confused" is on `repairs.FEELING_WORDS`, "stuck" is not). It is the one allowed exception to "name no feeling they have not named", because it is a check, never a statement; the base prompt says so. It is asked at most once in a conversation, and never under `safety: concern`, while a framework is running, or when their last message is `heard`. It goes in the `short` bullet of "Their last message" and takes precedence over "read it as the answer and go on" for that case only. After their answer, yes or no, Mani asks one concrete question about something they already said. A stuck person is never given an either/or question, before or after the check. Which framework is offered, and when, still follows spec 0005: the facts must fully fit, and nothing is offered because of the check. Inside a framework, "I don't know" still moves on as spec 0003 says; the check is for the understanding phase only.
- **AC-5** (two body check lines): in `backend/content/prompts/somatic.md`, Supportive's check in becomes "What are you noticing in your body right now?" and the `somatic_practice` Reflective `ask` (line 88) becomes "Where do you feel that in your body?". The other styles' lines are unchanged, and so is the `if_unclear` reply sent with the place buttons (line 57, "Where do you feel that most right now?"). Supportive's check in is no longer a yes or no question, so its "agree to notice" branch (lines 37 to 38) is no longer reached in Supportive; it stays for the other styles' wording and is left in place. Tests that assert the old Supportive line (`tests/integration/test_turn.py` near lines 1585, 1596 and 1787) assert the new one.
- **AC-6** (every authored question passes, free): a unit test reads, through the same parser `scripts/seed.py` uses, every question the model is given: each stage's `ask` in all styles, `ask_simpler`, `if_earlier_missing`, branch asks (such as DBT STOP's `panic`), `if_unclear` replies, and the body check and "where" lines in `somatic.md`. The offering stage of each framework, including its `panic` branch, is left out (its wording is row 6). Fields that are not said to the person (`when`, `needs`, `prompts`, `purpose`, `ready_when`) are not read; a reply may be a string or a per style mapping. Only sentences ending in "?" are checked, cut by the same splitter AC-7 uses, so statements in a reply (the "returns in waves" reply says "pattern" outside a question) are left alone. Each question has fewer than 16 words, opens with no lead clause, and uses none of the flagged words (AC-7). Today one fails and is reworded: DBT STOP `observe` `panic`, Reflective, "What is present for you right now, inside you or around you?" becomes "What do you notice right now, inside you or around you?".
- **AC-7** (counts on real replies, free): `backend/tests/evals/validators.py` gains `question_findings(reply, their_message, *, in_framework=False) -> list[Finding]`. `their_message` is the person's message of that one exchange, never the conversation's text so far. Curly apostrophes are turned straight first. Questions are cut with the existing `_QUESTION` pattern (`[^.!?\n]*\?`) and words counted with a plain whitespace split. It returns one `Finding` per fault, under four rule names:
  - `long question`: 16 words or more.
  - `lead clause`: the question's first words are "since", "given", "now that", "looking at", "knowing" or "considering". The list is deliberately narrow: "when", "with" and "as" often open a fine question ("When you try to stop, what happens?").
  - `flagged word`: whole words "belief", "process", "reflect", "pattern", "example", "conclusion", "meaning" (so "reflective" and "meaningful" are not caught), any word starting "explor" ("explore", "exploring"), and the phrases "present for you", "pulling on you", "pulling the most".
  - `either/or`: only when `in_framework` is false and `their_message` is a stuck message, a question containing " or " that opens "would you", "do you", "should we", "shall we", "is it" or "are you", or contains "would you rather". The client's fixed lines (`repairs.CLIENT_LINES`) and the body route's "keep chatting or go to the Library" reply are exempt. A stuck message matches "i don't know", "dont know", "idk", "not sure", "can't think", "cant think", "can't decide", "cant decide" or "confused".
  `scripts/eval_replies.py` calls it per reply in `_score`, with `in_framework` true once a framework is accepted, and prints the findings. `scripts/client_style_counts.py` adds one integer field per rule to `ConversationCounts`, one key per rule to `figures()`, and prints them in `summary.txt`. Unit tests feed concrete replies from the 4 October run and the old chat: "Since you've mentioned that you find yourself losing an hour to scrolling, what makes returning to the time you spent doing other things matter to you?" is caught for length and lead; "What was in that message?" is not; "Would you like to try an exercise, or would you prefer to keep talking?" after "i cant decide" is an either/or, and the same after "I went to a concert" is not.
  The existing `names_their_situation` check (a framework question that shares no content word with what they said) stays and is still printed: it now shows whether the one swapped word of AC-1 happens. It is reported, not part of the AC-9 bar, because a step question asked as written is allowed.
- **AC-8** (the old chat is a scenario): `backend/scripts/eval_conversations.yaml` gains a `depressed_alone` scenario with the user turns of the old chat, in order, up to "Different way", with "Let's try it" typed rather than tapped. It has no expected framework: under spec 0005 an offer may not come, and later turns may then read oddly, so the read in AC-9 judges only the questions Mani asks. The concert scenario `idiot_concert_direct` already exists and is used as it is.
- **AC-9** (the real model, after muhammad says yes): muhammad has to say yes before any real model run, since it spends the client's tokens, and checks credit first. Once he does: `idiot_concert_direct` and `depressed_alone`, each style, one run each (6 conversations). The bar, counted from the AC-7 findings over each whole transcript (offer descriptions and the client's fixed lines are not Mani's questions): no `lead clause`, no `flagged word`, no `either/or`; at most one `long question` per conversation; in `depressed_alone`, "Are you feeling stuck?" appears at most once (a plain text count). The check can repeat if it has scrolled out of the history the model is given; that is accepted, and the count will show it. muhammad and the team lead read the six transcripts and agree the questions read like the old examples. The figures and their read go in the journal. Until this run, AC-2 to AC-4 count as built but unverified.
- **AC-11** (what the model is told to find out, in plain words): the Framework Index text built from each framework's `to_find_out` (`backend/mani/prompts/composer.py` near line 124) steers the model's own questions, and three lines in it invite the abstract ones ("What gives it that meaning?"). They become plain: ABCDE "what they took it to mean about themselves or the other person" becomes "what they told themselves about it, about them or the other person"; ABCDE "how believing that has affected what they felt, did or avoided" becomes "how thinking that changed what they felt or did"; Thought Reframe "why that thought hurts" becomes "what makes that thought hard for them". No other `to_find_out` line uses a flagged word; a unit test asserts none does.
- **AC-10** (records and a clean suite): `python scripts/seed.py` is run after the content edits; `pytest` passes with clean output; `backend/PORT-STATUS.md`, a new ADR (ADR-017, questions are asked plainly) and its index entry, and a journal entry record the change in the same work.

## Decision

**Chosen option**: Option 1: fix in place, in the prompt and content, measured by free checks and one small paid run.

The base prompt and the `[ctx]` stage notes are rewritten so questions are plain and short with nothing in front, Supportive's question rule and two body lines change, a stuck person gets one check, and new deterministic checks measure all of it without adding any runtime redraft.

**Implementation skills**: none installed apply (backend prompt, content and test code; no frontend or database change).

## Feature design

**Data model sketch**: none. No migration, no new column, no new `[ctx]` field. The stuck check's "at most once" is held by the model reading the conversation, and measured by the eval (AC-9).

**State transitions**: none new. Stage tracking, holds and moving on are unchanged (spec 0003).

**API surface**: none. No endpoint changes; replies keep their shape.

**Value sourcing**:
| Action | Value produced / displayed | Source |
|---|---|---|
| Framework turn | The step question text | the stage's `ask` for the style, from the seeded framework (`admin.frameworks`), given as `stage_ask` in `[ctx]`; the model may swap in one of their words (AC-1) |
| First framework turn after credited stages | The say back sentence | `already_told` in `[ctx]` (ADR-015), as its own sentence (AC-1) |
| Understanding phase turn | The model's own question | the model, under the "How you talk" rules (AC-2, AC-3) |
| Understanding phase turn after a stuck message | Whether to ask the check | the model, from the conversation it is given and the rule in AC-4 |
| Understanding phase turn after a stuck message | The check's wording | fixed in `mani_base.md`: "Are you feeling stuck?" (AC-4) |
| Understanding phase turn | What the model looks for | the Framework Index from `to_find_out`, reworded (AC-11) |
| Eval scoring | Whether a reply is inside a framework | `eval_replies.py`, true from the accepted offer on (AC-7) |
| Body check turn | The check in and "where" lines | `somatic.md` per style, seeded, appended by `repairs.with_the_check_in` (AC-5) |
| Eval scoring | Question findings per reply | `validators.py`, from the reply text and the person's previous message (AC-7) |
| Eval scoring | Whether a message is stuck | the phrase list in AC-7, in `validators.py`, applied to that exchange's message only, used by the eval only, never at runtime |
| Per conversation counts | Totals of each finding | `client_style_counts.py`, summing AC-7 findings over saved transcripts |

**Key invariants**:
- No runtime code rejects, trims or redrafts a reply because of its question. The redrafts that exist today (a feeling or size word they never gave, offer timing and fit) are unchanged.
- No question the model is given from content (AC-6 list) has 16 words or more, a lead clause, or a flagged word; the content test fails otherwise.
- The stuck check never states a feeling; it is always a question, and it never forces an offer.
- The base prompt body stays within 115 lines.

**Security model**: unchanged. No new data is stored. Eval transcripts are health data and stay in the gitignored `backend/.eval/`; the paid run uses the existing zero data retention route (spec 0006). The safety screen runs before everything here, so "depressed" in the old chat is handled by it exactly as today.

**Configuration required**: none.

**Edge cases**:
- They answer "no" to the stuck check: one concrete question about something they said, never the check again.
- Still stuck after the check: one concrete question again, never the check again, never an either/or.
- A credited first framework turn: say back sentence, then the plain step question (AC-1).
- They did not understand a step question: the existing rephrase hold (`ask_simpler`, spec 0003) is unchanged, and its wording is covered by AC-6.
- A stage that asks them to choose among options they named (`answered_picks_options`): that hold still offers one of their options and asks whether it suits them. It is not counted as an either/or, because AC-7 counts either/or only outside a framework.
- A decline at the body route ("not sure" to the check in) followed by the client's "keep chatting or go to the Library" reply: exempt under AC-7.
- `safety: concern`, a running framework, or `heard`: no stuck check (AC-4).

**Critical test scenarios**:
- Happy path: the content test passes on every authored question after the DBT STOP rewording, verifies **AC-5**, **AC-6**.
- Failure case: a fake reply "Since you are focused on finishing that presentation by Friday, what do you know for certain about that deadline?" is caught for its lead clause; "Would it help to name a few of them, or would you rather sit with the restlessness?" after "i cant decide" is caught as an either/or; the same question after "I went to a concert", inside a framework, or the client's "keep chatting or go to the Library" line, is not, verifies **AC-7**.
- The framework index: no `to_find_out` line uses a flagged word, verifies **AC-11**.
- The notes: no `[ctx]` stage note says "never bare", verifies **AC-1**.
- The prompt: the base prompt fits in 115 lines and says the new question rule and the Supportive line, verifies **AC-2**, **AC-3**.
- Real model: the six conversations of AC-9, verifies **AC-2**, **AC-3**, **AC-4**, **AC-9**.

## Build plan

Ordered so the measurement exists before the prompt changes (the repo's lesson: measure before tuning prompts), then the thinnest end to end change, then the paid check.

1. The free checks: `question_findings` in `validators.py` with unit tests on real lines from the 4 October run and the old chat, including the exemptions; the per conversation fields, `figures()` keys and summary lines in `client_style_counts.py`; `eval_replies.py` passing that exchange's message and `in_framework`, and printing the findings beside `names_their_situation`. Satisfies **AC-7**.
2. The content test over every authored question through the seed parser; it fails on the DBT STOP panic line. Reword that line; change Supportive's check in and the `somatic_practice` Reflective line in `somatic.md`; update `tests/integration/test_turn.py` near lines 1585, 1596 and 1787; reword the three `to_find_out` lines with their test; run `scripts/seed.py`. Satisfies **AC-5**, **AC-6**, **AC-11**.
3. The stage notes in `context.py` (all seven named in AC-1), the "They say yes" line in `mani_base.md` and the `framework_starting` line in `response_format.md`: plain step questions, the say back as its own sentence; the notes test and `tests/unit/test_chat_context.py` near line 952. Satisfies **AC-1**.
4. The base prompt: the question rule and flagged words in "How you talk", the named lines rewritten for room, the Supportive line, the stuck check and its exception in the `short` bullet, "a short summary" in "Ending gently", all within 115 lines; extend `test_base_prompt.py`; seed again. Satisfies **AC-2**, **AC-3**, **AC-4**.
5. The `depressed_alone` scenario; ADR-017 and its index entry, `PORT-STATUS.md`, the journal; full `pytest`. Satisfies **AC-8**, **AC-10**.
6. After muhammad says yes and credit is checked: the six conversation run, the read with the team lead, the figures in the journal. Satisfies **AC-9**.

## Consequences

**Positive**:
- The questions the person sees get shorter and plainer in every style, with no new model calls and no new code path at runtime.
- The new counts make question quality visible on every later eval run, including row 35's model comparison, at no cost.
- Authored questions can no longer drift back into long or abstract wording without a failing test.

**Negative / tradeoffs**:
- Prompt only enforcement is not a guarantee: the lite model already let "It sounds like" survive a redraft (journal of the concert chat). Some long or wrapped questions will get through until a stronger model is chosen (row 35).
- Dropping the clause in front of a step question makes some replies feel less connected to what the person just said. The one swapped word and the say back sentence on credited turns carry that, and the read in AC-9 judges whether it is enough.
- The flagged words and the stuck phrases are a short list, the kind of phrase list the project is moving away from. They live only in the eval, never at runtime, so they measure but cannot misroute a conversation.
- The 115 line limit forces existing prompt lines to be tightened to make room, which can change behavior the earlier specs measured (spec 0002). The AC-9 run is the only real check of that.
- The stuck check is one more model judgment; "at most once" is not enforced in code, and the check can repeat once it has scrolled out of the history the model sees.
- Supportive's body check in becomes an open question, so its "agree to notice" branch goes unused in that style.

**Neutral**:
- Spec 0003's notes change wording but not behavior: the stage still moves on after one answer.
- Two client lines in `somatic.md` change, under muhammad's 2026-10-05 permission; the client has not been told.

## Follow-up

- [ ] Row 17's Done when ("every stage's question is the client's own question for that stage") conflicts with this spec where a client question fails AC-6; reword row 17 when it is designed.
- [ ] Row 6 owns the offering stage wording, which AC-6 leaves out ("This one event has come to mean something much larger about you" has 16 or more words and "mean"). Apply AC-6's checks to it when row 6 is built.
- [ ] Tell the client about the two changed body check lines and the stuck check.
- [ ] Records this makes stale, for `/sync` to flag: ADR-015's "say back in one short clause" (the say back is now its own sentence), spec 0003 AC-16 (the notes quoted word for word), and the "never bare" lesson in `validators.names_their_situation`'s docstring.
- [ ] Row 27 (client rules the app never reads): the worked examples and "responses to avoid" tables still hold old questions ("What did that come to mean for you?"); nothing reads them, so they are left alone here.

## Rationale

Reasoning and options: see [rationale.md](rationale.md).
