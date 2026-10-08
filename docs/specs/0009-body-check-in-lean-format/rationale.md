# 0009 rationale. The body ending as short rules, ended by a reply field

## Context

> ⚠️ Premise note: the scope row asked for the client's ending (completion question, body check in, a practice per place, Chat More / Go to Library) restated as short rules. muhammad redesigned the flow during this design instead: the body check is offered rather than always run, with an apology when they feel worse, its steps are chosen by the model and paced one per turn, and a person who still feels bad is kept talking rather than given the two choices. This departs from the client's documents (`six-frameworks-overview.md`, "Completion, somatic, and the hand-off"; `conversational-styles.md`, "Somatic check-in"), which also disagree with each other on the check in wording. It rests on muhammad's standing permission to change the client's wording without sign off (2026-10-05). It should still be told to the client (Follow-up).

The ending is the last place the code still writes the reply. `orchestrator._body_route_step` and `mani/chat/ending.py` insert the check in word for word, find the place in the person's message by regex (`_PLACE_WORDS`), swap in one of twelve scripted practices, swap in the returning reply on "it comes back" (`_COMES_BACK`), and read the reply's own wording (`_ASKS_WHAT_NEXT`) and the last message's buttons (`_awaiting_place`) to decide buttons and retirement. Spec 0006 left all of it to this feature (its AC-3 exception).

The content behind it, `content/prompts/somatic.md`, is merged by the seed into every framework's `stages`, and `context._stage_lines` renders the two blocks in full into `[ctx]` on the last own stage and both ending stages. `[ctx]` is not cached, so each of those turns pays for the purposes, boundaries, `if_unclear` branches and scripts again.

Retirement today is positional: an accepted framework whose stored phase is the last one retires on the next turn, unless the last reply carried place buttons. Once the practice spans several turns, position alone can no longer say when the ending is over, and nothing in the database says when the ending began.

## Options considered

### How the code learns the ending is over

- **A closed reply field (chosen).** `ending: choice | keep_talking`, validated by a guard. Pros: no words are read, the labels stay exact, and the model reports the one judgement only it can make (how they feel). Cons: one more schema field, and the model can forget it, which needs a backstop.
- **The model sends the buttons.** Labels named in the prompt, the handoff found by label. Pros: no new field. Cons: spec 0006 saw these come back mislabeled or missing, and it still leaves no signal for keep talking, which has no buttons.
- **One phase per step.** Each step its own phase, buttons hung off phases. Pros: the state is explicit. Cons: the step count is the model's choice, so a fixed phase list cannot describe it, and skipping inside the ending would need the clamp loosened.

### Where the rules live

- **`mani_base.md`'s `ending` section (chosen).** Pros: it already holds the ending's two rules, sits in the cached prefix, and needs no new row or composer layer. Cons: the base prompt grows by about six lines on every turn.
- **A new seeded row added by the composer.** Pros: kept apart from the general rules. Cons: a new layer, a new required row and its checks, for six lines.
- **Short blocks in `[ctx]` on ending turns only.** Pros: nothing added to other turns. Cons: uncached on exactly the turns that use it, and it keeps `_stage_lines` and the block keys alive.

### Who words the check in and the practice

- **The model, from rules and an allowed step list (chosen).** Pros: matches the scope's "short rules, not verbatim text", fits the style, and removes every script. Cons: wording and step order drift, and only real runs show it.
- **The client's text, copied by the model.** Pros: the client's exact words. Cons: twelve practices plus three check ins in the prompt, and copying is still not guaranteed without the code this feature removes.
- **Keep code inserting it.** Pros: exact. Cons: it is the code this feature exists to remove.

### How the backstop counts the ending's turns

- **A new nullable column, `ending_from` (chosen).** Pros: exact, and it changes nothing else. Cons: a migration on a hosted database that already differs from the code.
- **Reset `at_message_count` when the ending starts.** Pros: no migration. Cons: the post framework cooldown and `since_last` would silently count from the ending instead of from the yes.
- **Count from the yes.** Pros: no migration. Cons: framework lengths vary, so any cap is either too tight for a long framework or too loose for a short one.

## Rationale

The forces are the scope's bar (no code edits the reply or matches words) and muhammad's flow, where the practice length and the outcome are the model's judgement. A closed field is the smallest signal that carries that judgement to the code without reading text, and it keeps the two buttons exact, which spec 0006 showed the model does not. Every other choice follows from keeping one home per fact: the rules join the ending section that already exists, and the phase ids stay as the code's closed set (`ENDING_PHASES`), unchanged so open threads carry on.

The cap exists because a field the model can forget would otherwise pin a thread in its ending and block every later offer. The column was chosen over reusing `at_message_count` because that reuse would quietly change offer timing, which is spec 0008's territory. The cap is a Python constant only because this is built before spec 0008's `tuning` row exists. muhammad chose to build in that order, and 0008 moves it.

Two smaller calls were made in writing:
- **Setting `library_offered_since` on `keep_talking` and the cap** (runner up: a new flag). The existing flag already turns `library_pending` off. A second flag would need another column for the same effect, at the cost of the column's name being slightly broader than what it holds.
- **Dropping the model's buttons on every ending turn** (runner up: allow its own, minus library and handoff). Every step is typed, by muhammad's choice, so any button there could only be one the flow does not want.
