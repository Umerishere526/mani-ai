# Verify: Mani speaks naturally · spec 0002 · updated 2026-10-04
_Steps derived from spec 0002 acceptance criteria. `/check verify` runs these; `/test` locks the durable ones._

## UI / manual
- [x] Read `short_replies.md` from three runs of the check; each Mani reply acts on what the person was answering → AC-5 (12 replies, 3 real cases, all acted on; journal 2026-10-04)
- [x] The AC-8 meaning count is taken from the AC-14 file of record (`read-files-final/restating_read.md`), final against baseline in the same file, by a blind model reader whose marks stand as final → AC-8 (meaning) (0 against 5, met)
- [x] Read `style-lines-1/style_read.md` (18 panic replies, style hidden): the reader labels each Direct, Supportive, Reflective or none, "own style" when the label equals the key; at least 10 of 18 and no style under 2 of its 6 → AC-9 (10 of 18, Direct 2, Reflective 3, Supportive 5; met under the amended bar, the full 15 of 18 moves to row 6)
- [x] Record the counts, marks and verdict in the journal → AC-8, AC-9, AC-13 (sections "Blind reads by a model" and "Close out of the build")

## Commands
- [x] `cd backend && source .venv/bin/activate && python scripts/seed.py && python scripts/eval_client_style.py` three times, means of the three → AC-6 to AC-12
  - questions per reply, own words, lower than the baseline's 0.59 (last measured 0.54 on `style-lines-1`) → AC-6
  - no reply with two questions → AC-6
  - stock phrases per conversation below the recounted baseline 1.08 / 1.92 / 2.17 (final 0.83 / 0.00 / 0.67); `sounds_or_seems_like` at most 16 (final 14); `phrases_said_twice` 0 → AC-7
  - repeated openers no worse than the baseline (Direct 0.17, Reflective 0.42, Supportive 0.75; counted on all replies, as the baseline was) → AC-7
  - feelings never used: zero, with the feeling and size redraft restored (last measured 0 of 36; prompt only was 0, 2, 2) → AC-8
  - all 36 offered, at least 33 at exchange 2 to 4; dashes no more than 2 → AC-10
  - replies over three sentences no more than 1 → AC-12
- [x] The check prints size phrases never used beside the feeling figure, no higher than the baseline's count (0 against 5, "a lot" 4 against 16, reported only); and writes `style_read.md` (own words only, shuffled, style hidden); the shuffled meaning read file is built by hand from the baseline and run 1 (`meaning_read.md`) → AC-8, AC-9 (task 4a)
- [x] `cd backend && source .venv/bin/activate && pytest` → green with no new warnings, integration tests not skipped → AC-2, AC-3, AC-4, AC-11
- [x] `pytest tests/evals/test_base_prompt.py` → `mani_base.md` at most 120 lines, no dash punctuation, no example conversation, hard rules present → AC-1, AC-11
- [x] Send "yes" after a Mani message ending in a question, then check the model input holds `their_last: short` and `answering` with that question; send a tap and check it holds neither → AC-4 (Value sourcing: `their_last`, `answering`)
- [x] Send a four word reply ("I don't really know"), a reply while an offer is waiting and a reply on a safety concern; none of them carries `answering` → AC-4
- [x] A repeated question and a reply with no question each cost one provider call and arrive unchanged; a feeling or size never given is redrafted once, never trimmed → AC-2, AC-8
- [x] Offer too early is redrafted once and the note says nothing about asking a question → AC-2, AC-3

## /check verify 2026-10-04
Real stack run (database, orchestrator, model) through the eval harness: typed "yes" carries `their_last: short` and the quoted question; a tap, a four word reply, an offer waiting and a safety concern carry no `answering`; vetoed turn made 2 calls, others 1. Full suite 834 passed, 4 skipped. Check `with-feeling-redraft`, three runs. AC-9 not met: Supportive and Reflective do not differ in what they do.

## Acceptance-criteria coverage
- AC-1 … `test_base_prompt.py` · AC-2 … `test_redraft.py`, `test_turn.py` · AC-3 … existing veto, safety and repair tests · AC-4 … `test_chat_context.py`, `test_turn.py`
- AC-5 … read, met · AC-8 (meaning), AC-9 … blind model reads of record, met under the amended bars · AC-6, AC-7, AC-10, AC-12 … the check, final measured in `style-lines-1` · AC-11 … `test_base_prompt.py`, `tests/evals`
- AC-13 … ADR-012 accepted 2026-10-04; index, PORT-STATUS and journal updated

## Tasks 4b, 4c and 4d · added 2026-10-04
_Steps for the style lines, the stock phrase ban and the restating rule. Results of the 2026-10-04 build are beside each._

### UI / manual
- [x] Mark the panic replies in `style-lines-1/style_read.md` blind against the AC-9 rubric → AC-9 (a fresh model read it, 10 of 18, met under the amended bar of at least 10 and no style under 2; the full 15 of 18 with 4 of 6 moves to row 6)
- [x] Mark `restating_read.md` (baseline, last 4c check, final check, run 1 each, source hidden) for restating replies and meanings stated as fact → AC-14 (88% before, 42% after, met), AC-8 meaning (0 against 5 at baseline, met)
- [x] muhammad accepted the reader's marks as final on 2026-10-04, with no check of the flagged cases → AC-8, AC-9, AC-14

### Commands
- [x] `cd backend && source .venv/bin/activate && python scripts/seed.py && python scripts/eval_client_style.py` three times → AC-7 ("sounds like" or "seems like" in Mani's own words: 14 in 36, bar was zero, accepted by muhammad), AC-6 (0.54), AC-10 (36 of 36 offered, 36 at exchange 2 to 4), AC-12 (0 long replies)
- [x] `python scripts/eval_client_style.py --restating-read <baseline dir> <before dir> <after dir> --out <dir>` writes `restating_read.md` with the source hidden and the key at the end, no model call → AC-14
- [x] `pytest tests/evals/test_base_prompt.py tests/unit/test_client_style_counts.py` → `mani_base.md` names the five stock phrases and no longer says "say back"; stock phrases are counted on Mani's own words before acceptance; the restating read tags `[offer]` and `[after tap]` → AC-1, AC-7, AC-14
- [x] `pytest` → 847 passed, 4 skipped → AC-1 to AC-4, AC-11

### Acceptance-criteria coverage
- AC-7 … `client_style_counts.py` tests and the check (amended bars met) · AC-9 … blind read (met under the amended bar) · AC-14 … the restating read (met) · AC-8 meaning … the same read (met)
