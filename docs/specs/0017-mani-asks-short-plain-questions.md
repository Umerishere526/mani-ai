# 0017. Mani asks short plain questions, in plain words

**Date**: 2026-10-09
**Status**: In Progress

## Summary

Mani's replies come out long and fancy ("how does the possibility of losing your job sit with you now?", "notice the support beneath them"), and most questions start by saying the person's story back to them. The cause is a handful of prompt sentences that tell the model to pack the person's story into every question, restate before asking, and never word anything the same way twice. This spec cuts or rewords those sentences, and rewords the existing plain words rule so it bans dramatic, poetic and fancy phrases. The client's ABCDE questions are the bar ("How did that thought affect how you felt or what you did?"). Nothing is added to the prompts, no code changes, and muhammad judges the result by eye in three real runs.

## Context

Scope feature 23 asks for one short plain question about one thing, the way the client's ABCDE questions read. On 2026-10-09 muhammad widened it to every reply the model writes: questions, comfort lines, mirrors and body check steps. In his words: no dramatic, fancy, poetic or mouthful phrases. The work is backend seeded content only: `backend/content/prompts/mani_base.md`, `backend/content/prompts/response_format.md` and the Stages lines in `backend/content/frameworks/`, seeded into `admin.prompts` and `admin.frameworks` by `scripts/seed.py`.

The local thread `cbc5c13d` (a Directive ABCDE chat about being left out of meetings, analysed in `mani-vault/Journal/stage-skip-and-short-questions-scope-2026-10-09.md`) shows the problem in Mani's own replies:

- "Okay. With that distinction in mind, how does the possibility of losing your job sit with you now?"
- "You're right, you'd already said these were meetings you were integral to. You've also said no one has told you your role is changing. Given both, what feels like a fair way to describe what you know right now?"
- "You're saying losing your job is a real possibility, not something you can simply set aside. Would it fit to say …"
- "Being left out of important meetings can leave a lot unclear. Has anyone said something that points to your role changing, or is it the meetings themselves that have you wondering?"
- "Press both feet gently into the floor and notice the support beneath them."

Four kinds of prompt sentence ask for this. First, sentences that pack their story into the question: "in your style and their words, about their situation, never bare" (`in_a_framework` line 1), "built from what they have told you, in their words, … never bare" (`ctx.stage_lines`), "built on what they already told you" (`ctx.framework_starting`), "specific to what they just said" (`reasoning` step 3), and "in their words" on four Stages lines. Second, one that puts a restatement first: "say what you now understand, name what is still missing in fresh words" (`in_a_framework` line 2). Third, variety rules that push the model to reach for synonyms ("sit with you", "a fair way to describe"): "or the same thing the same way twice" (`questions` line 2) and "do not reuse your own phrasing from earlier replies" (`reply` line 3). Fourth, a framing that invites counsellor phrasing: "Ask as a perceptive friend would, … about what happened or what it is like for them" (`questions` line 2).

The constraints in force: prompt changes cut and clarify, never add (muhammad, 2026-10-08), and the scope's Done when says `mani_base.md` plus `response_format.md` end with no more lines than they started with. Spec 0010 already handed three of these sentences to this feature in its *Not in this spec*. Every real model run spends the client's credit and needs muhammad's yes first.

## Requirements

**User stories**:
- As a person talking to Mani on a phone, I want every reply in plain everyday words, so I can read it at a glance and answer without working out what it means.
- As a person answering a set of questions, I want each question to ask one thing, without my story said back first, so I know exactly what to answer.
- As muhammad, I want the fix made by cutting the sentences that cause it, so the prompts get shorter rather than gaining another rule.

**The bar**, from the client's ABCDE document and muhammad (2026-10-09):
- A question with an "or" between two sides of one thing passes ("How did that thought affect how you felt or what you did?"). Two different questions joined by "or" fail ("Has anyone said something about your role, or is it the meetings that have you wondering?").
- A few words of acknowledgment may come before the question ("Okay." "That sounds hard."), like the client's Supportive lead ins. Their story said back before the question fails.

**Acceptance criteria**:

- **AC-1**: `mani_base.md` `in_a_framework` line 1 reads exactly "The stage you are on is named in [ctx]. Ask what that stage asks on its Stages line, in your style, as one short plain question, never bringing in anything they did not give." (E1)
- **AC-2**: In `mani_base.md` `in_a_framework` line 2, the sentence "Staying is not repeating, so say what you now understand, name what is still missing in fresh words, and after two tries come at it from a different angle." is replaced by exactly "Staying is not repeating, so ask only for what is still missing, and after two tries come at it from a different angle." Every other sentence of the line is byte for byte unchanged. (E2)
- **AC-3**: `mani_base.md` `questions` line 2 reads exactly "Ask in plain words about what happened or what makes it hard. Never ask for what they made clear. Until you know what the issue is, ask what it is, plainly, before asking about any part of it." No line of `mani_base.md` contains "never bare", "fresh words", "perceptive friend", "same way twice" or "what it is like for them". (E3)
- **AC-4**: `response_format.md` `reply` line 1 reads exactly "Write the way a person texts a friend. Short, everyday words. No dramatic, poetic or fancy phrases, no clinical words or jargon. One to three short sentences, longer only to explain what the questions involve when they ask." and `reply` line 3 reads exactly "English only, and no dashes of any kind." (E4, E5)
- **AC-5**: `response_format.md` `ctx.stage_lines` reads exactly "stage_lines: stage is the first stage on stage_ledger not known or passed, by id, and what each asks is on the Stages line in the Framework Index. While stage is offering, your offer is still open and offer_waiting says how to take what they typed. On the last stage of the questions, and on somatic_checkin and somatic_practice, the ending section says what to do." (E6)
- **AC-6**: `response_format.md` `ctx.framework_starting` reads exactly "framework_starting: they just said yes. Judge every stage on stage_ledger against all they told you before, in state.stages, and ask the first one not known. Never say it back or ask them to confirm it." No line of `response_format.md` contains "never bare", "built from what they have told you", "built on what they already told you" or "reuse your own phrasing". (E7)
- **AC-6a**: `response_format.md` `reasoning` step 3 reads exactly "The question, as questions says. Is it new and not already answered? Then offer or not, as cooldown_passed, ruled_out and offers say, and start differently from recent_openers." (E9)
- **AC-7**: The Stages lines lose ", in their words" and nothing else: `thought_reframe.md` has "thought (the one thought, tied to a moment)", `structured_problem_solving.md` "problem (one problem)", `act_choice_point.md` "present (the thought, feeling or urge)", `dbt_stop.md` "observe (what is happening now, not why)". `abcde.md` and `behavioral_activation.md` are unchanged, and so is the `Starts when` line of `thought_reframe.md`. `python scripts/seed.py` accepts all six files. (E8)
- **AC-8**: `mani_base.md` plus `response_format.md` have no more lines than before and fewer words, as `wc -lw` reports, measured on the working tree right before the edits and right after (145 lines and 3360 words on 2026-10-09, with spec 0010's amendment in the tree). Both numbers go in the journal note.
- **AC-9**: After `python scripts/seed.py` and a server restart, the whole `pytest` passes with pristine output. The builder records the passed and skipped counts and checks the integration tests ran rather than skipped.
- **AC-10**: After muhammad's yes, with `get-credits` checked first, `python scripts/eval_replies.py --scenario journey_abcde --style <style> --verbose` runs once each for `direct`, `supportive` and `reflective`. Before reading a run, the builder confirms its thread has the style set, with `select conversation_style from public.threads where id = <the run's thread id>` against the local database; a null means the run did not test that style and is reported as such. muhammad reads every model written reply by eye against *The bar* above: plain everyday words, no dramatic, poetic or fancy phrase, each question asking one thing, and nothing before a question but a few words of acknowledgment. The body check starts after the closing stage, at the scenario's turn 12 ("My shoulders feel a bit looser…"), and its replies count. A run fails if any one model written reply breaks the bar; the seeded lines (the offer, Tell Me More, the after framework questions) are not judged. There is no word limit and no automated check. Each run is recorded as measured, pass or fail with the replies that failed quoted, in the journal note and under the measurements in `backend/PORT-STATUS.md`. A failing run is reported, never rerun until it passes.
- **AC-11**: In the same change, `backend/PORT-STATUS.md` gets one line under "Decisions in force": every reply the model writes uses plain everyday words with no dramatic, poetic or fancy phrases, questions ask one thing with the client's ABCDE questions as the bar, and the fix cut the sentences that packed their story into the question. No PORT-STATUS line quotes an edited sentence today, so no other line changes. PORT-STATUS has uncommitted edits from spec 0010, so only this spec's lines are touched.

**Not in this spec**:
- Seeded lines Mani sends word for word: the offer, Tell Me More, the greeting, the style openers and the after framework questions (`replies.md`). They are the client's wording.
- The persona line "You listen with the skill of someone with forty years of experience …" (`identity` line 2). Kept on purpose. It is the next lever if AC-10 fails (see *Follow-up*).
- Letter names such as "C is for Consequences" (feature 20).
- The stage ledger, `fields.state` and the `|` cut (spec 0010).
- When the offer comes and restating at the first message (feature 22, spec 0016). Spec 0016 wrote `questions` line 2 and `ctx.framework_starting` (its E4 and E7). E3 and E7 here reword parts of both and keep the rest, including "Until you know what the issue is…" and "Never say it back or ask them to confirm it.", which carry 0016's intent.
- The `Starts when` line of `thought_reframe.md`, which also says "in their words". It decides when to offer, not how a question is worded.

## Options considered

### Option 1: Cut and reword the sentences that cause it, and reword the plain rule in place

Delete or shorten the nine sentences above, and reword the existing `reply` line 1 so it names what is banned. No new line, no code.

**Pros**:
- Fixes the cause. The sentences that ask for packing and synonyms are gone, so the plain rule no longer fights them.
- The prompts get shorter, which keeps muhammad's cut, never add rule and the scope's line count check.
- Seeded content only: reverting is a file revert and a reseed.

**Cons**:
- With the variety rules gone, the model may repeat a phrase from one reply to the next.
- Less instruction to tie a question to their situation, so a question may come out too bare.

### Option 2: Add a plain words rule and leave the causes in place

A new line in `reply` or `questions` listing banned phrasing, with the current sentences kept.

**Pros**:
- The smallest edit to read, and it keeps the current tie to their situation.

**Cons**:
- Adds a line, against the cut, never add rule and the scope's Done when.
- Two instructions pull in opposite directions ("never bare, in their words" and "short and plain"). The model ends up choosing between them each turn, which is how the long questions came about.

### Option 3: Put the client's exact question for each stage on the Stages lines

For example "consequences (C is for Consequences: How did that thought affect how you felt or what you did?)", so the model copies the client's plain question.

**Pros**:
- The plainest anchor there is, in the client's own words.

**Cons**:
- Client wording exists only for ABCDE; the other five frameworks have none yet.
- The ABCDE Stages line is 417 of its 420 character cap.
- It changes framework content the client owns, and still does not cover replies that are not questions (body check steps, comfort).

### Option 4: A code check or an eval word limit

Flag or redraft replies over a word count, or containing listed phrases.

**Pros**:
- Measurable and repeatable.

**Cons**:
- Spec 0006 removed reply repairs, and the reply goes out as the model wrote it.
- muhammad chose to judge by eye with no word limit (2026-10-09). A phrase list misses the next fancy phrase it has not seen.

## Decision

**Chosen option**: Option 1: cut and reword the sentences that cause the long, fancy wording, and reword the plain rule in place.

Nine sentences in two prompt files and four Stages lines lose the words that pack the person's story into a question, put a restatement first, or push for synonyms; `reply` line 1 is reworded to "texts a friend" with dramatic, poetic and fancy phrases banned.

**Implementation skills**: none (backend seeded content only).

## Rationale

The replies in `cbc5c13d` are not the model ignoring the plain words rule. They are the model obeying the sentences around it. "Never bare", "in their words, about their situation" and "built from what they have told you" each ask for the story inside the question, which makes it long. "Say what you now understand" asks for a restatement in front of it. "Never … the same thing the same way twice" and "do not reuse your own phrasing" make the model reach for a new phrase each time, and the new phrases are where "sit with you", "with that distinction in mind" and "a fair way to describe" come from. A rule added on top (Option 2) would leave all of that in place and add a contradiction, which is why removing the causes beats adding a counterweight.

Muhammad's constraints point the same way. Prompt changes cut and never add, the scope requires the two files to end no longer than they started, and judging is by eye rather than by a word limit or phrase list (which rules out Option 4). Option 3 would give the plainest questions for ABCDE, but only for ABCDE, and only for questions; muhammad widened this to every reply, so the fix has to live in the rules that govern every reply.

Two smaller calls. "Ask only for what is still missing" moves out of `in_a_framework` line 1 and lives only in line 2, so the instruction appears once. The persona line about forty years of experience stays: it carries warmth and the "never claim it" rule, and nothing in the runs shows it is the cause. If AC-10 fails on counsellor style phrasing after these cuts, it is the next thing to look at.

## Feature design

**Data model**: no schema change and no migration. The `admin.prompts` rows `mani_base` and `response_format`, and the `admin.frameworks` rows `thought_reframe`, `structured_problem_solving`, `act_choice_point` and `dbt_stop`, change on reseed.

**State transitions**: none. Offers, the stage ledger, stage choice and the ending work as today.

**Interface changes**: no HTTP shape change, no `[ctx]` key added or removed.

**The edits** (exact text; the ACs quote the results):

| # | Where | Before | After |
|---|---|---|---|
| E1 | `mani_base.md` `in_a_framework` line 1 | The stage you are on is named in [ctx]. Ask what that stage asks on its Stages line, in your style and their words, about their situation, never bare and never bringing in anything they did not give. If it is partial, ask only for what is still missing. | The stage you are on is named in [ctx]. Ask what that stage asks on its Stages line, in your style, as one short plain question, never bringing in anything they did not give. |
| E2 | `mani_base.md` `in_a_framework` line 2, its fourth sentence | Staying is not repeating, so say what you now understand, name what is still missing in fresh words, and after two tries come at it from a different angle. | Staying is not repeating, so ask only for what is still missing, and after two tries come at it from a different angle. |
| E3 | `mani_base.md` `questions` line 2, its first two sentences | Ask as a perceptive friend would, in plain words, about what happened or what it is like for them. Never ask for what they made clear or the same thing the same way twice. | Ask in plain words about what happened or what makes it hard. Never ask for what they made clear. |
| E4 | `response_format.md` `reply` line 1, its first two sentences | Write the way a person talks. Short, everyday words, no clinical words or jargon. | Write the way a person texts a friend. Short, everyday words. No dramatic, poetic or fancy phrases, no clinical words or jargon. |
| E5 | `response_format.md` `reply` line 3 | English only, no dashes of any kind, and do not reuse your own phrasing from earlier replies. | English only, and no dashes of any kind. |
| E6 | `response_format.md` `ctx.stage_lines`, its second sentence | Ask its question in your own words and the conversation style, built from what they have told you, in their words, as its words on the Stages line describe it, never bare. | (deleted) |
| E7 | `response_format.md` `ctx.framework_starting` | … and ask the first one not known, built on what they already told you. … | … and ask the first one not known. … |
| E8 | Stages lines of `thought_reframe`, `structured_problem_solving`, `act_choice_point`, `dbt_stop` | … , in their words … | the phrase ", in their words" removed, nothing else |
| E9 | `response_format.md` `reasoning` step 3, its second sentence | Is it new, specific to what they just said and not already answered? | Is it new and not already answered? |

**Value sourcing**:

| Action | Value | Source |
|---|---|---|
| Any model turn | how a reply is worded | `admin.prompts` `response_format` row, `reply` lines (E4, E5), seeded from `content/prompts/response_format.md` |
| Question before an offer | what it asks about | `admin.prompts` `mani_base` row, `questions` line 2 (E3) |
| Stage question | what the stage asks | that framework's Stages line in `admin.frameworks.body`, seeded from `content/frameworks/*.md` (E8) |
| Stage question | which stage | `[ctx]` `stage`, from `Registry.stage_from_ledger` (spec 0010, unchanged) |
| Stage question | the style it is asked in | `[ctx]` `conversation_style`, from `threads.conversation_style` (unchanged) |
| First question after a yes | which stage, and that nothing is said back | `ctx.framework_starting` (E7) |
| Any question | what the model checks before asking | `reasoning` step 3 (E9) |
| A stage still partial | what is asked | `in_a_framework` line 2 (E2) |
| AC-8 | line and word counts | `wc -lw content/prompts/mani_base.md content/prompts/response_format.md`, before and after |
| AC-10 | the replies muhammad reads | `eval_replies.py --verbose` output for `journey_abcde`, one run per style |

**Key invariants**:
- No line is added to `mani_base.md` or `response_format.md`.
- No sentence outside E1 to E9 changes, including the sentences spec 0010 and spec 0016 own on the same lines.
- No Stages line gains anything. Each stays within `seed.py`'s `MAX_STAGES_LINE` (420).

**Security model**: no change. Seeded admin content only; no new data, grant or route.

**Critical test scenarios**:
- The edited files hold exactly the after text, and none of the cut phrases remain (a search of both prompt files), verifies **AC-1** to **AC-6a**.
- `python scripts/seed.py` accepts all six frameworks and both prompts, verifies **AC-7**.
- `wc -lw` before and after, verifies **AC-8**.
- The whole `pytest`, integration tests not skipped, verifies **AC-9**.
- `journey_abcde` in Directive reaches C, and the C question reads like the client's ("How did that affect how you felt or what you did?"), not "how does X sit with you", verifies **AC-10**.
- `journey_abcde` in Supportive reaches the body check, and each step is plain ("Press your feet into the floor."), not "notice the support beneath them", verifies **AC-10**.
- `journey_abcde` in Reflective: no stage question opens with their story said back, verifies **AC-10**.

## Build plan

Tracer Bullet: all of this is seeded text, so it is one slice, proven on ABCDE in all three styles. Build it on top of spec 0010's amendment, still uncommitted in the same working tree (muhammad, 2026-10-09); none of its sentences overlap.

1. Measure `wc -lw` of `mani_base.md` and `response_format.md` before any edit, satisfies **AC-8**.
2. E1, E2 and E3 in `mani_base.md`, satisfies **AC-1**, **AC-2**, **AC-3**.
3. E4 to E7 and E9 in `response_format.md`, satisfies **AC-4**, **AC-5**, **AC-6**, **AC-6a**.
4. E8 in the four framework files, satisfies **AC-7**.
5. Measure `wc -lw` again; `python scripts/seed.py`; restart the server; run the whole `pytest` and record the counts, satisfies **AC-7**, **AC-8**, **AC-9**.
6. Ask muhammad for his yes, check `get-credits`, run `journey_abcde` once per style with `--verbose`, and hand him the replies to read, satisfies **AC-10**.
7. Record the results in a journal note (`mani-vault/Journal/short-plain-questions-build-2026-10-09.md`, with the counts) and in PORT-STATUS measurements; add the decision line to PORT-STATUS "Decisions in force", satisfies **AC-10**, **AC-11**.

## Consequences

**Positive**:
- Replies and questions read like the client's: one plain thing at a time.
- Both prompt files get shorter, and the plain rule no longer fights the sentences around it.
- Seeded content only: no code, no schema. Reverting means reverting the files and running the seed again.

**Negative / tradeoffs**:
- Without the variety rules, the model may reuse a phrase across replies. `ctx.recent_openers` still keeps openers varied, and "after two tries come at it from a different angle" still stops a stage from stalling. Watch for it in the AC-10 runs.
- With less instruction to tie each question to their situation, a question may come out too bare or generic. The client's Directive questions are bare by design, so this is accepted.
- Judged by eye in three runs, so it is a sample, not a guarantee. A fancy phrase can still appear in a run no one reads.

**Neutral**:
- This changes two decisions in specs still in progress, and both are edited in place in the same change as this spec: spec 0010 line 163 said the "in their words" in four Stages descriptions stays, and E8 removes it; spec 0016 AC-2 and AC-5 pinned `questions` line 2 and `ctx.framework_starting` exactly as its E4 and E7, which E3 and E7 here reword, so feature 22's verify checks them as reworded by 0017. Spec 0016 AC-6's 3424 words already differ from the tree (3360), so its count is stale independently of this spec.
- Specs 0006, 0007, 0012 and 0013 quote some of these lines as they were. They are decision records and stay as written; `/sync` flags any that go stale.
- No migration plan is needed: one reseed, rolled back by reverting the files and reseeding.

## Follow-up

- [ ] If AC-10 fails, these are the next levers, in order of likely effect, each decided with muhammad: on a story said back, the `mirror and ask` shape and the `mirroring` move (spec 0016 owns them); on counsellor style phrasing, the persona line in `identity` ("forty years of experience … read what is said and what is left out") and the Reflective style's "reflects the meaning behind what they say"; on a poetic body check, "gentle attention to where they feel it" in `ending` line 3; on story packing before the offer, "Hold on to what they came with" (`goal`) and "ask one question from what they said" (`ctx.conversation_phase`).
- [ ] Watch in AC-10 that a stage left partial is asked again only for its missing part, now that the instruction lives only in `in_a_framework` line 2.
- [ ] When the client sends wording for the other five frameworks, compare their questions with these Stages lines (feature 15's documents).
