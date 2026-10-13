---
type: journal
date: 2026-10-13
tags: [journal, frameworks, stages, memory, gotchas]
---

# The ABCDE walk is owned by code (2026-10-13)

Built spec 0004 (scope feature 18, R6 and R12). The model no longer walks the stages or rebuilds a
ledger every turn. It reports what changed (`stage_updates`), how their message answers the stage in
force (`stage_answer`) and, on the yes, their word for the feeling. `mani/chat/walk.py` merges that
into `thread_technique_state.stages_known`, moves at most one stage, and renders the letter line and
the client's lines. Why the store was needed: [[version-b-remembered-by-model-work-not-storage-2026-10-13]].
What it replaces: [[stages-are-skipped-not-confirmed-2026-10-09]].

## Gotchas found while building

- **The pool's jsonb codec already calls `json.dumps`.** Passing `json.dumps(value)` to a `$1::jsonb`
  parameter stores a JSON *string*, not an object. Pass the dict. The new check constraint
  (`jsonb_typeof(stages_known) = 'object'`) would refuse the string, which is one reason it is there.
- **`seed.py` drops frontmatter keys it does not know, silently.** A framework level key in
  `abcde.md` (`confirm_phrases`) reached nothing until it had a column (migration 021) and a line in
  `parse_framework`. Putting it inside `stages` would have worked too, but `stages` would then hold
  something that is not a stage.
- **The model's text is written for the branch `[ctx]` named, from the store before this turn.** If
  this turn's updates change the status of the stage being reached (they say the belief while answering
  A), the text was written for another branch. Using it as the naming sentence would send a stray
  acknowledgement; the walk uses the fixed fallback instead and logs `branch changed`.
- **Code sending the first stage left the style consent lines nowhere to go.** The client's ABCDE
  document goes from Try It straight to "A is for Activating Event.", so the consent lines were removed
  and the conflict with `conversational-styles.md` recorded in `docs/client/requirements.md`.
- **"The turn they say yes" is ambiguous once the walk has checks.** The field descriptions said
  `stage_answer`: "Null on the turn they say yes" and `feeling`: "Only on the turn they say yes", meaning
  the yes to the offer. A person typing "yes" to A's check got `stage_answer: null` (and a `feeling`) in
  3 of 3 live replays, so the walk stayed on A while the text named B's belief. Named as "the turn they
  accept the offer", it was `agreed` in 3 of 3. Field descriptions are prompt: a word that means two
  things in the conversation will be read the other way. `test_no_stage_field_reads_a_yes_to_a_check_as_the_start_turn`.

## Weak spots to watch in transcripts

- The naming sentence is checked only for questions. A sentence with no "?" that does not name their
  words ("Thank you.") passes as the naming sentence. Only a live run shows how often.
- A correction to an earlier stage usually comes with `not_yet` for the stage in force, which counts as
  a try there; the next `not_yet` then lets that stage go. That follows the spec (tries count every
  `not_yet` in a row), but it may move a stage on sooner than a person expects.
- Seeding five stages in one low effort call can over report (five confirms in a row) or under report
  (a stage asked again). Owed: a live seeded run, see [[one-call-turns-at-low-effort-2026-10-12]].
