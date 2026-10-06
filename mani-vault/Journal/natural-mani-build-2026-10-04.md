---
type: journal
date: 2026-10-04
tags: [journal, evals, conversation, prompts, baseline]
---

# Building "Mani speaks naturally": the numbers and what they taught

Scope row 33, spec [0002](../../docs/specs/0002-mani-speaks-naturally/index.md). Follows
[[client-style-check-baseline-2026-10-04]], [[measure-before-tuning-prompts]] and
[[overfit-prompt-and-natural-mani-direction]]. Every figure is from `scripts/eval_client_style.py`, three runs of
the client's four conversations in all three styles (36 conversations), model `google/gemini-3.1-flash-lite`.
Saved under `backend/.eval/client_style/` (gitignored): `baseline`, `code-change-alone`, `new-prompt-1`, `-2`, `-3`.

## The baseline, recounted with the extended check

The saved baseline had no tap marks and no text for the new counts, so it was parsed once from
`baseline/transcripts.md` and run through the same functions as every later run.

| Figure | Baseline |
|---|---|
| Questions per reply, Mani's own words (offer description and permission question stripped, replies from the accepting tap on left out) | 0.59 (105 replies, 141 in all) |
| Questions per reply, every reply | 1.00 |
| Replies with two questions | 0 |
| Stock phrases per conversation, Direct / Reflective / Supportive | 0.08 / 0.42 / 0.58 |
| Stock phrases said twice in one conversation | 5 |
| Repeated openers per conversation, Direct / Reflective / Supportive | 0.17 / 0.42 / 0.75 |
| Feelings never used, in Mani's own words | 0 |
| Offers reached / at exchange 2 to 4 | 36 of 36 / 33 |
| Dashes | 2 |
| Replies over three sentences, own words | 1 |
| Replies after a message of three words or fewer | 43 with taps, 12 without; all 12 are the client's scripted lines |

## Where this differs from the spec's figures

- **AC-6's bar is already met by the baseline.** Counting on Mani's own words gives 0.59, under the bar of 0.7.
  The bar was set when the baseline was read as 1.0 (every reply). It needs tightening or restating as a gap.
- **Long replies: 1, not 9.** The reviewer's 9 did not strip the composed offer text. Offers whose buttons were
  dropped (the bug in [[safety-buttons-dropped-after-offer-text-composed]]) still carry that text, so the check
  strips the description and permission question wherever they appear, not only when `offered` is set. The first
  version of the check keyed on `offered` and counted offer paragraphs as Mani's sentences.
- **Baseline feelings were 9 only before stripping.** With the description stripped, 0.
- **The filler line never triggers `short`.** "I don't really know." is four words. Only the client's "Yes." and
  "I'm upset." reach `their_last: short`, so AC-5's list is the client's scripted turns, which answer the client's
  Mani, not the model's.

## The effect of the code change alone

Old prompt, only the redrafts retired and `short` plus `answering` in. Replies still ask a question almost every
time because the old prompt demands it.

| Figure | Baseline | Code change alone |
|---|---|---|
| Questions per reply, own words | 0.59 | 0.60 |
| Stock phrases, Direct / Reflective / Supportive | 0.08 / 0.42 / 0.58 | 0.33 / 0.25 / 0.42 |
| Feelings never used | 0 | 10 |
| Offers reached / at 2 to 4 | 36 / 33 | 35 / 34 |

The ten feelings are the cost of retiring ADR-006's redraft and trim: "stressful", "overwhelming" and the like now
reach the person. One conversation never offered (panic Supportive: grounding questions, five non answers).

## After the rewrite (`mani_base.md` 120 lines, `response_format.md` shortened)

| Figure | Baseline | new-prompt-1 | -2 | -3 (seeded now) |
|---|---|---|---|---|
| Questions per reply, own words | 0.59 | 0.40 | 0.48 | 0.48 |
| Stock phrases, D / R / S | 0.08 / 0.42 / 0.58 | 0.33 / 0.33 / 0.25 | 0.08 / 0.00 / 0.08 | 0.00 / 0.00 / 0.00 |
| Repeated openers, D / R / S | 0.17 / 0.42 / 0.75 | 0.17 / 0.33 / 0.25 | 0.25 / 0.08 / 0.25 | 0.17 / 0.25 / 0.25 |
| Feelings never used | 0 | 0 | 2 | 2 |
| Offers reached / at 2 to 4 | 36 / 33 | 36 / 33 | 36 / 35 | 36 / 35 |
| Dashes | 2 | 0 | 0 | 0 |
| Replies over three sentences | 1 | 0 | 0 | 0 |

Changes between runs, one at a time: run 1 to 2 named "I hear you", "I am here with you" and "that makes sense"
in the base (the presence line had been prompting "I am here with you" in the first reply); run 2 to 3 added
"worried" and "scared" count as feelings.

## Settled after reading the transcripts (2026-10-04)

- **AC-6's bar: under 0.5** own words, mean of three runs (baseline 0.59, the rewrite 0.47 to 0.48). The spec's 0.7 was
  already met by the baseline. Not lower: fewer questions means Mani learns less per reply and the offer comes later.
- **AC-8: restored a feeling and size words redraft** (muhammad's choice). One call only when a draft uses a word from
  `repairs.FEELING_WORDS` or `repairs.SIZE_PHRASES` that they never used; no question pushed, no trimming. Check
  `with-feeling-redraft`: feelings never used 0 of 36, offers 36 of 36 all at exchange 2 to 4, own questions 0.47,
  stock phrases 0 / 0 / 0.08, openers 0 / 0 / 0.17, dashes 0, long replies 0.
- **Still reaching people:** "a lot" in 5 of 90 final replies, all stress before a deadline, and meanings stated as fact
  that no list catches ("stuck in a loop", "this thought is pulling at you", "a hard pattern to break"), plus
  "It sounds like" in 23 of 90. Ask the client whether "a lot" may stay; their own lines use it.
- **AC-5:** 12 qualifying replies, 9 of them the opening "I'm upset.", 3 the panic Direct "Yes." to "Would you like to
  pause for a moment?", which Mani takes and offers on. Right, but three real cases.
- **AC-9:** no style reads more emotional. Direct leads (a pause offered, "What has been happening?"). Supportive and
  Reflective barely differ in what they do. Half met.
- Panic's first stage question after Try it, "Can you stop the action before it happens?", fits panic badly: framework
  content for rows 6 and 18.

## Task 4a: size phrases and the files for the human reads (2026-10-04, check `read-files`)

Baseline size phrases never used, parsed from `baseline/transcripts.md` with the same functions (offer taken as
accepted at the first message equal to a button of the offer before it; the parse reproduces the recorded 105 own
replies, 0.59, 2 dashes, 1 long reply, 33 offers at 2 to 4): **5 without "a lot"** ("weighing on you" twice, "so much"
three times), **16 "a lot"**. Nothing committed parses that file; the one off script lived in the scratchpad.

Final check, current prompt and redraft: size phrases without "a lot" **0** (bar: no more than 5, met), "a lot" **4**
(reported only), feelings never used 0, own questions per reply 0.49, stock phrases 0 / 0 / 0.08, openers
0.08 / 0.17 / 0.25, offers 36 of 36 with 35 at exchange 2 to 4, dashes 0, replies over three sentences 0.

Files for muhammad, under `backend/.eval/client_style/read-files/`: `style_read.md` (18 panic replies, style hidden, key at
the end, AC-9) and `meaning_read.md` (24 conversations, run 1 of the baseline and of this check mixed, source hidden,
key at the end, AC-8). Both still need marking. Task 4b waits on the AC-9 marks.

Bug the test caught while building the shuffle: the first version printed the whole `(label, text)` pair, which would have
shown the reader the source. The unit test asserts the word "source" never appears above the key.

## What the first human read found that the check could not (2026-10-04)

muhammad marked two habits in `meaning_read.md`: "It sounds like", and a sentence that says their words back before the
question ("You find yourself unable to stop scrolling."). Counted afterwards on the saved transcripts: "it sounds like"
49 of 105 replies in the baseline (32 of 36 conversations), 25 of 88 after the rewrite (19 of 36, six saying it twice).
The check said 0 stock phrases because its list held three phrases and the base banned the same three: a measure and a
rule that share a blind spot pass each other. Lesson: when the people reading disagree with the numbers, add what they
heard to the list before trusting the numbers again.

A cause sat in the base itself: line 23 said "say back no more than is there". A rule written to stop over interpreting
also asked for restating. Spec 0002 was amended (AC-7 widened, AC-14 added, tasks 4c and 4d) with the fix kept in the
instructions. The cross check on another model found that the stock phrase count ran on full replies, not Mani's own
words, so a sample reply after acceptance could have broken the zero bar. Its other gaps are in the spec's rationale.

## Before the redraft was restored: what was not met

- **AC-8 (zero feelings never used) is not met.** 0, 2, 2 across the three checks. Run 2: "worried" for "I feel like
  I might have a panic attack", twice. Run 3: "worried" and "frustrating", different conversations. The base rule
  was tightened once and the slips moved rather than stopped. This is the cost ADR-008's and ADR-006's code checks
  were paying for. Options for muhammad: accept the rate and read for it, restore a feelings only redraft, or tighten
  the model in row 35.
- **The human reads (AC-5, AC-8 meaning, AC-9) have not been done.** They need muhammad.

## Things noticed in the transcripts

- Panic Reflective repeats the offer on three replies in a row after non answers. The offer returns whenever
  `cooldown_passed` allows and the person typed past it.
- Reflective still states a meaning past their words once: "which sounds like things are moving very fast for you".
- The person's name appears twice in some Reflective panic replies ("I am here with you, Sam", later "Sam, can you
  stop..."), against the once rule.
- A provider timeout kills a whole check run; the script has no retry. One run was lost to it and repeated.

## Choices forced by the 120 line limit

Dropped from the base: the generic client line for "I don't know" (each stage carries its own `if_unclear`), the
clarification wording (`response_format.md` has it), the three worked conversations, the shapes table, the
question-focus paragraphs. Kept in their old words: "never ask twice for the same thing the same way",
"say it simply, in any style", the client's three "yes" lines.

## Task 4c: ban "It sounds like", two rounds (2026-10-04)

The check now counts stock phrases on Mani's own words before acceptance (`own_phrases`), keeps the all replies
figure beside it, and has two new patterns ("sounds like", "seems like"). The baseline and the last check were
recounted the same way with a one off script (not committed; it parses `baseline/transcripts.md`, takes the offer
as accepted at the first message equal to a button of the offer before it, and reproduces the recorded 105 own
replies, 0.59 questions, 2 dashes, 1 long reply, 33 offers at 2 to 4).

| Figure | Baseline | Last check (`read-files`) | Round 1 (base only) | Round 2 (base and response_format) |
|---|---|---|---|---|
| "sounds like" or "seems like", own words | 49 in 32 of 36 conversations | 26 in 19 | 10 | 3 |
| Stock phrases per conversation, D / R / S, own words | 1.08 / 1.92 / 2.17 | 0.42 / 0.83 / 1.00 | 0.50 / 0.25 / 0.50 | 0.00 / 0.08 / 0.42 |
| Stock phrases said twice | 20 | 6 | 0 | 0 |
| Repeated openers, D / R / S | 0.17 / 0.42 / 0.75 | 0.08 / 0.17 / 0.25 | 0.08 / 0.25 / 0.00 | 0.33 / 0.00 / 0.00 |
| Own questions per reply | 0.59 | 0.49 | 0.49 | 0.49 |
| Feelings never used / size phrases / "a lot" | 0 / 5 / 16 | 0 / 0 / 4 | 0 / 0 / 4 | 0 / 0 / 0 |
| Offers reached / at exchange 2 to 4 | 36 / 33 | 36 / 35 | 36 / 35 | 36 / 35 |
| Dashes / replies over three sentences | 2 / 1 | 0 / 0 | 0 / 0 | 0 / 0 |

Round 1 changed one line of `mani_base.md` (named both phrases, dropped "Plain words." to stay at 120 lines; line 15
still says plain). Round 2 changed one line of `response_format.md` (the tone rule repeats the five phrases).
Saved under `backend/.eval/client_style/ban-sounds-like-1` and `-2`.

What is left after round 2: three "sounds like" openers (supportive 2, one in compulsive scrolling, one in stress)
and three "I am here with you" in panic, supportive and reflective, first reply. Not met: AC-7 asks zero for the two
new phrases, under 0.3 stock phrases per conversation in each style (Supportive 0.42), styles within 0.2, and
repeated openers no worse than the baseline (Direct 0.33 against 0.17; it was 0.08 in round 1, so it is probably
noise at temperature 1, but one check cannot say). The spec allows two rounds, so this stops here and goes back to
muhammad: restore a redraft for the phrases (as was done for the feeling word), or accept the rate.

Noticed: `response_format.md` line 37 shows `recent_openers: "your manager", "that sounds"` in the `[ctx]`
example, which may prime the phrase. Spec 4d's round 2 already allows rewording it; not touched here.

### Decision on the fork (2026-10-04)

muhammad accepted the rate: no redraft for "It sounds like" or "It seems like". After two rounds the instructions
alone left 3 uses in 36 conversations (baseline 49, before the ban 26). AC-7's bars (zero for the two phrases,
stock phrases under 0.3 per conversation in every style, styles within 0.2) are therefore met only in part; round 2
gave Direct 0.00, Reflective 0.08, Supportive 0.42. The spec is `/architect`'s to amend. The client has still not been
asked whether the phrase may stay (spec follow up).

Noticed while building 4d's file: `_accepted_at` treats any button tap that follows an offer as the acceptance, so
a tap on "Keep chatting" would end "Mani's own words" early in the count. The check only ever sends accepting taps,
so no number is wrong today. A decline tap in a scenario would need a label on the turn.

## Task 4d: ban restating (2026-10-04)

Built: `restating_read` and the `--restating-read CHECK_DIR...` entry point on `eval_client_style.py`, which writes
`restating_read.md` (definition at the top, run 1 of each folder, `[offer]` and `[after tap]` tags, shuffled, key at
the end) without calling the model; unit tests for the tags, the hiding and the run filter. The baseline had only a
markdown transcript, so it was converted once to `baseline/transcripts.json` (taps inferred as in the recount,
`scripted` set false since nothing reads it here). The "say back" bullet in `mani_base.md` is replaced by the AC-14
rule in the same three lines; the base is still 120 lines. `response_format.md` and `schema.py` are untouched, for
round 1. `tests/evals/test_base_prompt.py` asserts the five stock phrases are named together and "say back" is gone.

### 4d round 1: figures, and a rise in "sounds like" (2026-10-04)

Checks `no-restating-1` and `no-restating-2` (the same seeded prompt run twice, to see the noise). The bullet that said
"say back no more than is there" is replaced by the AC-14 rule; nothing else changed from 4c round 2.

| Figure | 4c round 2 | 4d check 1 | 4d check 2 |
|---|---|---|---|
| "sounds like" or "seems like", own words | 3 | 12 | 15 |
| Stock phrases per conversation, D / R / S | 0.00 / 0.08 / 0.42 | 0.67 / 0.08 / 0.67 | 0.50 / 0.25 / 0.75 |
| Repeated openers, D / R / S | 0.33 / 0.00 / 0.00 | 0.00 / 0.08 / 0.00 | 0.00 / 0.00 / 0.00 |
| Own questions per reply | 0.49 | 0.51 | 0.52 |
| Feelings never used / size phrases / "a lot" | 0 / 0 / 0 | 0 / 0 / 5 | 0 / 0 / 4 |
| Offers reached / at exchange 2 to 4 | 36 / 35 | 36 / 35 | 36 / 35 |
| Dashes / replies over three sentences | 0 / 0 | 0 / 0 | 0 / 0 |

Two checks on one prompt differ by 3 (12 and 15), so the rise from 3 is not noise. The new bullet ends "Ask about a
meaning of your own, never state it", and the model seems to turn that into "It sounds like X" followed by a question.
Round 1 of 4c (older prompt, no response_format rule) gave 10, so the 3 of 4c round 2 was partly luck.
`read-files-4d/restating_read.md` (baseline, 4c round 2, 4d check 1, run 1 each) waits for muhammad's marks; the restating
share is what says whether the rule works.

## Blind reads by a model, and task 4b (2026-10-04)

muhammad chose that a fresh model marks the three reads blind (key stripped, source hidden) and that he checks only
the flagged cases, instead of marking 36 conversations and 18 replies himself. This departs from the spec, which says
muhammad judges AC-8 meaning, AC-9 and AC-14; recorded here as his decision. Reader noise is real: the same baseline
conversations scored 13 of 30 restating in one read and 18 of 30 in the next, while an identical 4d file got 8 of 18
both times. Only compare inside one file.

| Read | Intended style matched (D / R / S) | Restating, eligible replies | Meaning as fact |
|---|---|---|---|
| AC-14 read 1: baseline / before 4d / after 4d | | 13 of 30 / 15 of 17 / 8 of 18 | 7 / 0 / 2 |
| AC-9, 4d prompt | 1 / 1 / 3 = 5 of 18 | | |
| AC-9, style lines round 1 | 2 / 3 / 5 = 10 of 18 | | |
| AC-14 read 2: baseline / 4d / style lines 1 | | 18 of 30 / 8 of 18 / 8 of 19 | 4 / 2 / 0 |
| AC-9, style lines round 2 | 3 / 3 / 4 = 10 of 18 | | |

Style lines, round 1 and 2: the second round did not move the score. The misses are structural: the first reply is often
the offer sentence, and the offer section of the base says the questions are ones "you could go through together" in
every style, so every offer reads Supportive; the style lines cannot change a line they do not own.

## Close out of the build (2026-10-04)

Fork answers from muhammad: revert the style lines to round 1 and leave the offer wording to row 6; accept the
"sounds like" rate and ask the client. The prompt in force is the one of check `style-lines-1` (same database digest).

Round 2 of the style lines (`style-lines-2`) told Supportive and Reflective to "receive" and to "ask about one detail
and never state it back": AC-9 stayed at 10 of 18 and restating went from 42% back to 58%, so it was reverted. A rule
that says "receive what they said in plain words" invites a restatement; the style lines and the restating rule
pull against each other.

Final read, one file with the three sources hidden: restating baseline 14 of 30, before (4c round 2) 15 of 17, after
8 of 19; meaning as fact 5, 0, 0. AC-14 met (42% is under half of 88%), AC-8 met. The reader marked the identical
"before" file 15 of 17 both times, and the baseline 13, 18, 17 and 14 of 30 across four files.

Not met, for `/architect` to amend or the client to settle: AC-9 (10 of 18, structural: "together" in every offer),
AC-7 (zero for the two phrases; Direct and Supportive over 0.3). AC-6's bar is under 0.5 in the journal, 0.7 in the
spec. ADR-012 stays `proposed` until muhammad accepts it.

### Correction: the reader's marks stand without muhammad's check (2026-10-04)

Above, and in ADR-012 (accepted), the blind reads are described as "muhammad checks the flagged cases". When the amended
spec was cross checked, muhammad chose to treat the reader's marks as final, with no check of the flagged cases. The spec
(AC-8, AC-9, AC-14), PORT-STATUS and `verify.md` say so. ADR-012 is accepted and is not edited; read its line about
checking flagged cases as superseded by this note.

Also changed in that pass: the amended criteria name the final check (`style-lines-1`), the read of record
(`read-files-final/restating_read.md`, `style-lines-1/style_read.md`), the printed figures and how the blind marks are tallied; the
check script's labels print the amended bars; the opener baselines are 0.17 / 0.42 / 0.75.
