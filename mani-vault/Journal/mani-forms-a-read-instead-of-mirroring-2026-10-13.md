---
type: journal
date: 2026-10-13
tags: [journal, prompts, context, decisions, measured]
---

# Mani forms a read instead of mirroring (2026-10-13)

muhammad's Direct chat: six turns, every reply a mirror of his words plus a question. "i'm
frustrated" got "I hear the frustration. What's been frustrating you?"; "everything" got "It
sounds like it isn't just one thing"; turn 6 asked "What would you like us to focus on today?"
as if it were turn 1. Against the same opening, ChatGPT answered "When everything feels
frustrating, sometimes it's because several things have been building up for a while. I don't
want to assume that's what's happening to you", then an either/or built from candidate
explanations, then said why the distinction mattered.

## Two causes, both verified

**The prompt forbade the raw material.** `before_an_offer` already invited the behaviour ("Listen
for the pattern under what they say", "You may give two or three possibilities"), and four rules
in the same file forbade it: "Nothing they did not tell you. No assumed people, places, motives
or feelings"; "Never join two things they said into a cause or a link they did not make"; "Never
label or define"; "Never make it bigger than they did". The `[ctx]` `understanding` meaning, the
most-read block on exactly the failing turns, said "built from their words" and "two or three
possibilities from what they said". On "everything" and "idk" there are no words to build from,
so mirroring was the only move satisfying every rule at once. **Prohibitions beat invitations:
the contradiction resolved toward the prohibitions every time.**

**Mani had no memory of its own thinking.** `Reply.reasoning` is produced every turn, first in
schema order, and discarded unless `AI_DEBUG_MODE` is on. Before an offer `[ctx]` carried style,
phase, question focus, cooldown and recent openers - nothing about what Mani knew or suspected.

## What the measurement showed, in two steps

Step 1, the prompt narrowings alone, run live on muhammad's exact transcript: mirroring stopped
and hypotheses appeared. Two new failures appeared with it. "I don't want to assume" landed in
all six replies - a tic, not care - and **the same either/or was put to him at turns 2, 3 and 5**,
because nothing carried forward what had already been tried. That second failure is the proof
that the prompt alone could not fix this, and that the carried read was load-bearing rather than
speculative.

Step 2 added `working_read`. Turn 6 then produced a real pattern statement: "The problem may be
less any one broken promise and more that you can't rely on people to take responsibility. Do I
have this right?" All three styles kept their own voice.

## What is in place

- `Reply.working_read`, declared after `understanding_said` and before `next_move`, so the read
  is formed before the move is chosen (schema order is generation order).
- `thread_summaries.working_read` (migration 012), written **every turn** inside the turn's own
  transaction from `ThreadUpdates`, unlike `summary` and `current_issue`, which the background
  summarization writes only past twenty messages. The two writers share the row and name only
  their own columns in `do update set`, so neither blanks the other. **If summarization is ever
  changed to upsert the whole row, it blanks this column.**
- It arrives back free: `_TURN_CONTEXT_SQL` already fetches the row whole with `to_jsonb(sm)`.
- `[ctx]` line plus meaning, suppressed on a safety-concern turn.
- Three new rules: mark a possibility as yours once and vary the wording; never put the same
  pairing twice; keep the read the size they gave it.

## Costs and watch-items

No extra model call: the model already reasoned every turn, it needed somewhere to put the
result. `__bool__` on `ThreadUpdates` had to learn the new field or the write silently dropped
whenever nothing else changed - the trap that dataclass's own comment warns about. A bullet with
a colon in it became a YAML mapping again, caught by
`test_every_rule_in_a_prompt_file_is_a_sentence_not_a_yaml_mapping`; write "so" instead of ":".

Not yet measured: the full scenario suite. Several scenarios are only three or four scripted
lines and Mani now spends turns building the read, so some end before an offer - a harness
artifact, not a regression. The scripts need lengthening before those numbers mean anything.

Open for muhammad: Direct now offers a possibility on message 1, before the person has said much.
That may be too forward for the client; it is a one-line change either way.

See [[direct-questions-have-no-target-2026-10-09]] for the earlier version of the same lesson -
removing a behaviour by prohibition swings it to the opposite failure, so say what to do instead.
