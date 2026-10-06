# 0007. A framework ends with a conclusion and the body check, not a question

**Date**: 2026-10-05
**Status**: In Progress

## Summary

Today every framework ends by asking one more question ("Is that something you could realistically do?", "How does that sit with you?", or, when an earlier stage got no answer, "Is there anything you would add?") and only then asks about the body. muhammad found this abrupt and generic: the person has just said something real and gets a form question back. This spec removes that last question. The reply to the person's answer at the last real stage is one message: a short conclusion in their own words that says what they decided or said and that what they feel is okay, followed by the client's fixed body check question. It applies to all six frameworks, and the body check is now always asked. The spec also changes one earlier rule: at the two stages that ask for a balanced thought, a first "I don't know" gets one gentler question before the framework moves on.

## Requirements

Linked scope feature: row 19 in [docs/scope/conversation.md](../../scope/conversation.md), "Body check in follows every framework". muhammad's answer to that row's open question is "always ask it", given on 2026-10-05, so its "needs a decision" state is resolved by this spec. Everything below is checked on the two chats muhammad marked up on 2026-10-05: an ACT Choice Point chat that ended on "Is that something you could realistically do today?" and an ABCDE chat that ended on "Is there anything you would add before we finish looking at this?" after the person said "i don't know myself. i've lost my confidence".

**User stories**:
- As a person finishing a framework, I want Mani to close with a short, warm message that reflects what I decided or said, so that I do not feel quizzed at the end.
- As a person who could not find a balanced thought, I want Mani to say that not knowing yet is okay, so that I am not left with a form question or a conclusion I did not reach.
- As the client reviewing transcripts, I want every framework to reach the body check, as in every one of my worked examples.

**Acceptance criteria**:
- **AC-1** (no closing question): none of the six framework files has a `closing` stage. Each `phases` list ends on its last real stage, and the seed appends the two body stages after it. The six lists are ABCDE `offering, activate, belief, consequence, evidence_for, evidence_against, balanced`; Thought Reframe `offering, thought, significance, facts_for, facts_against, alternative, reframe`; Behavioral Activation `offering, stopped, matters, choose, manageable, begin, barrier`; ACT Choice Point `offering, situation, present, pull, matters, toward, action`; Structured Problem Solving `offering, problem, facts, control, outcome, options, compare, select, first_action`; DBT STOP `offering, stop, pause, observe, proceed`. The `closing` stage's `if_earlier_missing` ("Is there anything you would add before we finish?") and DBT STOP's closing `panic` branch are gone with it, and no framework text asks that question. A content test asserts all of this.
- **AC-2** (one message): on the turn that answers a framework's last real stage, `[ctx]` shows `somatic_checkin` as the stage to ask, with the conclusion note under *Feature design*. The reply the person sees is the model's concluding text followed by the body check question for the style, word for word (the existing `repairs.with_the_check_in`), and the stage recorded is `somatic_checkin`. Every sentence of the model's text that ends in a question mark is dropped before the check in is appended, so the check in is the only question in the message. The check in is appended only when the recorded stage is `somatic_checkin`: a hold at the last real stage (a rephrase, or the counted branch of AC-5) gets no check in, a turn paused by `safety: concern` records no stage and gets no conclusion or check in, and "stop" uses the client's own line with no conclusion. The turn after the conclusion is the body route, unchanged.
- **AC-3** (what the conclusion says): the `somatic_checkin` stage's `purpose` and `boundaries` carry the rules, so they live in one place for all six frameworks. The conclusion is one or two short sentences in the person's own words: it says back what they last decided or said, and may say that what they feel is okay without naming a feeling they did not name. That line is optional and is not in every conclusion, so it does not become a formula. It asks no question of its own, so the check in is the only question in the message. It does not summarize the framework or name its steps. It may say back up to two things the person told Mani they know, in their words, but never what those things mean about them or what they should conclude from them. When the last stage got no usable answer it may also say they do not have to settle it today. It does not give advice, choose an action or a value, or add to their plan; say the framework worked, or that a thought, feeling or situation changed, or that they have calmed down, or that a thought is fairer or a plan manageable or realistic, unless they used those words; require them to feel differently or to act; open with the words Mani opened its last two messages with (the existing `recent_openers` hint already reaches the model, and the eval's `repeated_openers` check measures it); or start with "It sounds like". The existing redraft for a feeling or size word the person never used (spec 0002, AC-8) applies to it unchanged, and it runs on the model's draft before the check in is appended, so the fixed text is never redrafted. These rules cannot be fully proved with a fake model: AC-3 counts as unverified until the AC-8 read has run.
- **AC-4** (the body check is always asked): the `somatic_checkin` branch "their closing answer already names an action they are going to take", and the words "or were skipped for action readiness" in its `ready_when`, are removed. After a conclusion the check in is asked in every framework. A person who declines it, or who answers it by saying what they will do, is handled by the body route as today (`repairs.declines_or_acts`).
- **AC-5** (a gentler question for "I don't know" at the balanced stages): ABCDE `balanced` and Thought Reframe `reframe` each carry one `if_unclear` branch marked `counted: true`: when they say they do not know what would be fair, or cannot put it into words, the reply is "That is fine. What is one thing about this that you do know is true?", one text used in all three styles. It uses the stage's one extra turn (spec 0003, AC-12). A second "I don't know", or any other answer, ends the framework with the conclusion, and when no balanced thought was given the conclusion says it is okay not to have one yet and does not write one for them. Every other "I don't know" at every other stage still moves on, as spec 0003 AC-5 says; this amends that rule for these two stages only.
- **AC-6** (the base prompt): the "Ending gently" paragraph of `content/prompts/mani_base.md` no longer tells the model to ask the closing stage's question. It says the last answer is followed by a short conclusion, then the body check as `[ctx]` gives it. The edit adds no lines and the file stays within the limit tests/evals/test_base_prompt.py enforces.
- **AC-7** (tests follow the new shape): the tests and scripts that name `closing` against the real frameworks use the last real stage instead (see the Build plan). The count of stages with an `if_earlier_missing` is 21 (27 less the six `closing` stages), and the two new balanced branches are in the content test's list of later branches. `pytest` passes with its output clean.
- **AC-9** (the balanced thought is asked for in plain words): ABCDE and Thought Reframe no longer ask for "a fairer way to say it". The questions are, in all three styles: ABCDE `evidence_against` and Thought Reframe `facts_against` "Is there anything you know that doesn't match that thought?"; ABCDE `balanced` and Thought Reframe `reframe` "Putting those together, what would you say is true about this?", with `ask_simpler` "From all of that, what do you know is true about this?" and the missing answer question "From what you know so far, what would you say is true about this?" (Thought Reframe `reframe`: "What would you say is true about this?"). A content test asserts no word "fair" in those stages' questions. Added on 2026-10-05 after muhammad's third chat, where a person asked what "fairer" meant.
- **AC-8** (the endings read well, with the real model): muhammad has to say before any real model run, since each run spends the client's tokens. Once he does: the two marked up chats are replayed in each style, three runs each (18 conversations), and the ABCDE chat with "I don't know" answered twice at `balanced`, in each style, three runs each (9 conversations), 27 in all. Every ending is read against AC-3. The check counts, per ending, question marks (must be one), feeling or size words the person never used (`repairs.introduced_feelings` and `repairs.introduced_size`, the lists spec 0002 AC-8 uses; must be zero), "It sounds like" (must be zero), and repeated openers (`validators.repeated_openers`, none). The result and muhammad's read are recorded in the journal.

## Decision

**Chosen option**: Option 1: remove the `closing` stage and let the body check stage write the conclusion.

The last real stage is followed straight by `somatic_checkin`; the model writes a short conclusion under rules held once in that stage, and code appends the client's fixed check in.

**Implementation skills**: none installed apply (backend conversation code and framework content, no frontend or database change).

## Feature design

**Data model sketch**: none. No migration and no new column. `thread_technique_state.phase` keeps its meaning, the stage whose question Mani last asked; the stored value after a conclusion is `somatic_checkin`.

**State transitions** (a running framework, stored stage `P`, last real stage `L`):
- `L` answered: an ordinary move on turn (spec 0003) to `somatic_checkin`, the move `closing` to `somatic_checkin` was before. `L` may still take its one counted hold (a rephrase, or a counted branch such as the two in AC-5); after a hold the next turn moves on whatever was said.
- Every other turn is as today: the first stage on acceptance, one stage per move, a stored somatic stage owned by the body route, `safety: concern` pausing the framework.
- A thread stored at `closing` when this ships has a stage the framework no longer has, and falls back as spec 0003 says a stored stage outside the list does. Mani is not open to real people yet, so this affects local test threads only.

**The conclusion note.** `context._move_on_lines` uses this note, word for word, when the stage to ask is `somatic_checkin` and `holds` is 0, in place of the move on note:

> stage_note: they have replied to the last stage, so the framework is done. Write the short concluding message that stage_purpose describes, in their words, and ask no question of your own: the body check in is added after it exactly as written. Report stage as your step. Stay on the answered stage, reporting answered as your step, only in these cases: they did not understand the question, so say it again once in simpler everyday words; or a branch in answered_if_unclear applies (a branch marked uses your extra turn uses it up) or you use one of the client's lines, so use its reply as written

When `holds` is 1 it is the same note with its first sentence "you have already stayed on the answered stage once, so the framework is done whatever they said", and without the first exception and without the words "a branch marked uses your extra turn uses it up", since no counted branch may keep the stage a second time. The rephrase note and the redirect handling are unchanged.

**The `somatic_checkin` stage** (in `content/prompts/somatic.md`, merged into every framework by `seed.py`):
- `purpose`: "Conclude the framework in one short message, then check in with the body. The conclusion is one or two short sentences in the person's own words: it says back what they last decided or said, and may say that what they feel is okay. The check in question is added after it exactly as written, once. Do not summarize the framework."
- `boundaries`: the three it has now, with the first reworded to "must not summarize the framework or name its steps; it may say back up to two things they told you they know, in their words", plus one per rule in AC-3 (including "must not tell them what those things mean about them or their ability, or what they should conclude from them"): no question of its own; no advice, no action or value chosen for them, nothing added to their plan; no feeling they did not name (what they feel may be called okay without naming one); no claim that it worked, changed, calmed, or is fairer, manageable or realistic unless they used those words; no requirement to feel differently or act; when the last stage got no usable answer, say it is okay not to have it yet and do not write it for them; no opening with the words of Mani's last two messages, and no "It sounds like". The purpose also says the line that what they feel is okay is optional and is left out of most conclusions.
- `if_unclear`: the branch "their closing answer already names an action they are going to take" is removed. "they agree to notice but have not said what they notice" and "the user declines the check in" stay. `ask` stays, the client's per style wording.

**Illustrations** (to show the intended shape, not fixed text):
- The ACT chat, Direct style: "Taking the half day to be with her is your choice, and what you feel about being away is okay. What do you notice in your body now?"
- The ABCDE chat after a second "I don't know": "It is completely okay not to know right now. You told me you have never missed a deadline and that you bring ideas to meetings, and that stays true even while you feel lost. You do not have to settle it today. Would you like to notice what is happening in your body?"

**Value sourcing**:

| Action | Value | Source |
|---|---|---|
| Build `[ctx]` | whether the turn concludes | the stage to ask, `framework.phases[index(answered) + 1]`, is `somatic_checkin`; `answered` is the stored stage |
| Build `[ctx]` | the conclusion's rules | `stages.somatic_checkin.purpose` and `boundaries`, seeded from `somatic.md` |
| Write the reply | what they last decided or said | the person's last message, in their words |
| Write the reply | a feeling they named | the conversation so far; none named means none is mentioned (spec 0002, AC-8) |
| Write the reply | the words Mani opened its last two messages with | `recent_openers`, already sent to the model by `context.build` |
| Compose the reply | the conclusion text kept | the model's text with every sentence ending in a question mark dropped, in `repairs` before `with_the_check_in` |
| Write the reply | whether the last stage got a usable answer | the model's reading of the conversation, as spec 0003 AC-7 does for `if_earlier_missing` (decided: no stored flag) |
| Record the reply | the stage recorded | `reply.state.step` limited by `clamp` to the answered stage or the next, so `somatic_checkin` |
| Compose the reply | the check in question | `stages.somatic_checkin.ask[style]` through `repairs.with_the_check_in`; the style from `context.resolve_style` |
| Build `[ctx]` | whether a counted branch is available | the answered stage's `if_unclear` branch with `counted: true`, and `thread_technique_state.holds` is 0 |

**Key invariants**:
- No framework has a stage after its last real stage except the two body stages.
- The reply that ends the real stages carries exactly one question, the check in, word for word. Code drops every question sentence from the model's text before appending it, and the eval counts question marks as a second check.
- The check in is appended only when the recorded stage is `somatic_checkin`. A hold, a safety pause and a stop never carry it.
- A panic answer at DBT STOP's `proceed` reaches the body route like any other framework's last stage; the DBT STOP closing `panic` branch is gone and `proceed` keeps its own.
- A stage still takes at most two replies from the person (spec 0003). The two new branches use the one counted hold, so "I don't know" twice at `balanced` ends the framework.
- The conclusion never writes the balanced thought, the plan or the value for the person.
- `mani_base.md` stays within the limit the test enforces.

**Security model**: no change. Replies remain special category health content and nothing new reaches logs or Sentry. The conclusion adds no storage.

**Configuration required**: none. Re-seed after editing `content/` (`python scripts/seed.py`); the running app picks the change up when its prompt cache expires or the server restarts.

**Critical test scenarios**:
- Content: no `closing` stage in the six files and the six phase lists exactly as AC-1 gives them; no framework text contains "anything you would add"; the 21 stages with an `if_earlier_missing`; the two `balanced` and `reframe` branches carry `counted: true` and a reply that passes the negative set; `somatic_checkin` has no branch about an action already named. Verifies **AC-1**, **AC-4**, **AC-5**, **AC-7**.
- Context: stored last real stage of a framework with a fake model, `[ctx]` shows `stage: somatic_checkin` with the conclusion note and the stage's purpose and boundaries, not the move on note; the same with `holds` 1 shows the used variant. Verifies **AC-2**, **AC-3**.
- Record and compose: a fake reply "That works for you." plus a question of its own, from the last real stage, comes out as the conclusion text then the style's check in, recorded `somatic_checkin`; a fake reply with a question in its first sentence has that sentence dropped; a reply that already contains the check in is not doubled. Verifies **AC-2**.
- No check in where none belongs: a hold at the last real stage (rephrase, and the AC-5 branch) records that stage and has no check in; a turn with `safety: concern` records no stage and has no conclusion or check in; "stop" gets the client's line and no conclusion. Verifies **AC-2**.
- DBT STOP: `panic_somatic_once` starts at `proceed` and still reaches the body question once, then where, then the exercise. Verifies **AC-1**, **AC-2**.
- Walk per framework: the six walks from spec 0003 AC-8 reach `somatic_checkin` through the last real stage, with no `closing` turn. Verifies **AC-1**, **AC-2**.
- The balanced stages: at `balanced` and at `reframe`, a fake reply that uses the branch records the stored stage with `holds` 1; a second records `somatic_checkin` with the note `hold limit`. At any other stage "I don't know" still moves on. Verifies **AC-5**.
- Integration (database, scripted model): a thread stored at the last real stage of ABCDE, the person answers, the reply ends with the check in and the stored phase is `somatic_checkin`; the person then answers "yes, that fits" and the body route handles it. Verifies **AC-2**, **AC-4**.
- Real model: AC-8, after muhammad says to run it.

## Build plan

Approach: Tracer Bullet. One framework goes through every layer first, then the other five repeat it.

1. [x] Shared stage and note (the thread through every layer): rewrite `somatic_checkin` in `somatic.md` (purpose, boundaries, remove the action branch and the `ready_when` words); add the conclusion note and its used variant to `context._move_on_lines`; add the drop of question sentences before `with_the_check_in`; unit tests for the context block, for record and compose, and for the hold, safety and stop cases. Satisfies **AC-2**, **AC-3**, **AC-4**.
2. [x] ACT Choice Point end to end: remove its `closing` stage from `act_choice_point.md`, update its phase list, run the seed, and walk it in the unit and integration tests. Satisfies **AC-1**, **AC-2**.
3. [x] The other five frameworks: remove each `closing` stage (including DBT STOP's closing `panic` branch), update `test_framework_content.py` (the six phase sets, the 21 count, the panic test's phase list), and the unit walks from spec 0003 AC-8. Satisfies **AC-1**, **AC-7**.
4. [x] The two balanced branches: add the counted branch to ABCDE `balanced` and Thought Reframe `reframe`, add both to `LATER_BRANCHES`, and add the hold and limit tests. Satisfies **AC-5**.
5. [x] The base prompt: reword the "Ending gently" paragraph in `mani_base.md` with no added line. Satisfies **AC-6**.
6. [x] Tests and scripts that name `closing` against the real frameworks: `tests/integration/test_turn.py` (`_land_on` and the four `phase="closing"` setups use each framework's last real stage), `scripts/eval_conversations.yaml` (`start_in` for `panic_somatic_once` becomes `proceed`), `scripts/eval_replies.py` (drop `"closing"` from the phase test), and the closing case in `tests/evals/test_style_findings.py` and `validators.py` if they depend on it. Satisfies **AC-7**.
7. [x] The record, in the same change: ADR-016 (amends ADR-013, whose 27 stages become 21 and whose "I don't know always moves on" has the two exceptions), `_Index.md`, `backend/PORT-STATUS.md`, scope row 19, and a journal note on the two chats. Satisfies **AC-7** and the project rule that PORT-STATUS changes with the work.
8. The real model read, after muhammad says to run it. Satisfies **AC-8**.

## Consequences

**Positive**:
- No framework ends on a form question, and the "anything you would add" fallback cannot appear.
- The client's body check follows every framework again, as scope row 19 asked, without a new rule: removing the skip is the whole change.
- The conclusion rules sit in one stage, not six copies, so they cannot drift apart.
- Fewer stages to walk and to test.

**Negative / tradeoffs**:
- The conclusion is written by the model, so its quality depends on the rules and cannot be fully tested. The check counts the measurable parts (one question, no invented feelings, no "It sounds like") and a person reads the rest.
- The six per framework closing boundaries (for example DBT STOP's "must not tell the user they have calmed down or made the correct decision") become one shared list. The general wording covers them, but a framework specific nuance is lost, and DBT STOP's panic closing is now just the general rules.
- It departs from the client's document (spec section 21 gives a completion question in all three tones). The client has to be told, and the change goes on the sign off list (scope row 29).
- The conclusion mirrors the last answer, which spec 0002 AC-14 treats as restating elsewhere. It is exempt on purpose, like the opening after a tap, and a person reads it in AC-8.

**Neutral**:
- A local thread stored at `closing` loses its stage on this change. Nothing real depends on it.
- Spec 0003's count of 27 stages with an `if_earlier_missing` becomes 21, and its AC-5 gets two exceptions; ADR-016 records both.

## Follow-up

- [ ] Tell the client the closing question is gone and what replaces it, and add it to row 29's list of our changes to their wording. muhammad decided the wording is his to change (2026-10-05), but this removes a question the client wrote.
- [ ] In the ABCDE chat, "From what you know so far, what seems fairest to say about your work?" was the `if_earlier_missing` question at `balanced`. It fired after the person answered "yes" at `evidence_for`, although `evidence_against` held real evidence, and muhammad marked it bad. Decide separately whether `needs: evidence_for` is the right test and how that question should read.
- [ ] In the ACT chat, the person's answer to "what matters" already named a response (the half day), so `toward` was skipped, and "what is the next small thing" was asked as a second action question. Neither is part of this spec; decide whether they need a rule.
- [ ] Spec 0002 AC-14 (no restating) does not cover the conclusion. Decide after the AC-8 read whether it should.

## Rationale

Reasoning and options: see [rationale.md](rationale.md).
