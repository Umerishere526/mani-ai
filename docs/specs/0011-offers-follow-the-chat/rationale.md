# 0011. Rationale: offers follow the chat, not a phrase list

## Context

> ⚠️ Premise note: this spec removes a safeguard without measuring what replaces it. Spec 0007 made the router's shortlist the set Mani may offer from, so the model could not offer a set the router saw no sign of. This spec takes that gate away, and muhammad chose scripted tests only, so nothing here shows how often the model, left alone, offers a set that does not fit. The guards that remain are the framework's own Starts when, Skip when and Never lines, the grief veto, the cooldown and the safety line. The right framing is to ship it and measure offers under feature 11 with muhammad's yes, because the alternative (keeping a gate that cannot see plain phrasing) is a known cost today. It also reverses two things in force: spec 0007's offer gate and the urgent DBT STOP rule (0007 AC-10). Both are named as changed in `index.md`.

Mani decides what to offer in two steps. A router written in Python scores each framework against what the person said, using phrase lists in the framework files (`strong_signals`, `signals`), reorders the result with six distinction rules, and sends the ranked ids to the model as `framework_shortlist`. The model may offer only a set on that list, and an empty list means no offer. Spec 0007 made it a gate on purpose, after removing the closest fit that used to offer something on a timer.

The phrases are short fragments matched as whole words, so a sentence that says the same thing in other words matches nothing. The scope's own example, "I've been avoiding my friends because I've been overwhelmed, and I feel guilty about ignoring them", gets an empty shortlist, and so does almost any ordinary phrasing (probe below). With no closest fit, an empty shortlist means the person is never offered a set, however well it would fit. Growing the lists helps only the sentences someone thought of.

The model already sees the whole Framework Index every turn, with each framework's Starts when, Sounds like, Skip when, stages and Never lines, and it writes a `heading_toward` field of its own. The client's own selection table reads "what MANI has identified", not "what phrase appeared". The router is a second judge that can only say no by saying nothing.

This is the backend of `mani/` (Python 3.14, FastAPI, asyncpg), no frontend. The change touches the offer rule in the prompts, `mani/chat/router.py`, `context.py`, `orchestrator.py`, `techniques.py`, `scripts/seed.py`, the `tuning` row and the six framework files. Spec 0010 (stage ledger) is in progress and edits several of the same files.

## Options considered

### Option 1: Fix in place, widen the phrase lists

Keep spec 0007 whole. Add many more plain phrasings to each framework's `signals`, and add a test per client example.

**Pros**:
- Content only, no code change, and 0007's gate and tests stay as they are.
- Deterministic and free per turn.

**Cons**:
- The ways people describe the same trouble never run out, and each added fragment buys recall at the cost of precision (the files already say so). The probe below shows 10 of 12 plain lines missed, and a longer list shifts which ones.
- It keeps a router that only says yes to what it was told about in advance.

### Option 2: Add a second signal source to the gate

Keep the shortlist as the gate and add a second way onto it: the model's own last turn guess (`heading_toward`, stored in a new column and added to the shortlist next turn), or a vector similarity between the message and each framework's description.

**Pros**:
- Keeps a gate, so an offer still needs a sign from somewhere.
- Plain phrasing can reach the list.

**Cons**:
- The stored guess costs a migration, a column and a one turn lag. Spec 0007 weighed it and dropped it. A vector match adds a new model call and dependency to a router that has none, and a third judge that can disagree with the model.
- Either way the model that makes the offer is the one whose guess adds the framework, so the gate no longer gates anything the model did not already choose.

### Option 3: The model judges, the router stays as a ranked hint

Drop the gate. Any set not ruled out may be offered when the model judges it fits. Keep the router's scoring and distinction rules and send the ranked ids as a hint, logging when the offer was off the hint.

**Pros**:
- Smallest change and nothing deleted. The client's tie breakers keep working and the hint is free per turn.
- The log would show how often the model beat the router.

**Cons**:
- Two judges that can disagree, which spec 0007 removed once already when it dropped the router's `offer:` line.
- All the phrase maintenance and the router tuning stay for a hint nobody has measured.
- This was the recommended option. muhammad chose Option 4 instead.

### Option 4: The model judges, the router is cut to the grief veto (chosen)

Drop the gate, the ranked hint, the distinction rules, the phrase lists, the urgent case and the router tuning. Keep one coded stop, `never_offer_when_said`, and the cooldown.

**Pros**:
- One judge, reading what the client wrote. Every pair in the client's tie breaker table is already named on both sides of its Skip when lines.
- Nearly all of `router.py`, the router tuning, the seed's distinction checks and most of `test_router.py` go, and no phrase list is left to grow.
- The first offer is on the same timing for every set.

**Cons**:
- The deepest cut, and the least measured: the decision rests on the model's reading of the Framework Index, with the veto and the cooldown the only code between it and a bad offer.
- Drops the DBT STOP urgency, a case where code, not the model, had decided an offer should come early.
- Needs muhammad's explicit yes to delete, which he gave.

## Rationale

Option 4. The forces in Context point one way: the router can only block by silence, and silence is what plain phrasing produces. A gate should refuse the bad, not demand proof of the good. The model reads the full Framework Index every turn and the client's own selection table is about what Mani has understood, so the fit judgment already lives in the prompt. A phrase router in front of it makes the prompt's work conditional on a list. Options 1 and 2 keep a gate whose signal still comes from code or from the model's own guess, so they add parts without adding judgment. Option 3 is the safe path, and I recommended it because it deletes nothing and a hint costs nothing per turn, but the hint adds a second opinion that only matters if someone measures it, and under spec 0006's rule that a turn is one call and the reply goes out as the model wrote it, a second opinion that is never enforced earns its place only by being measured.

muhammad's calls, with my objections where I had them:

- **Cut the router to the veto (Option 4 over my pick, Option 3).** My objection was that the hint is free and deleting it throws away working code and the client's tie breakers. His answer, in effect, was that a hint nobody measures is maintenance, and git holds the code. The tie breaker point turned out weaker than I feared: every pair in the client's table is already named on both sides by the Skip when lines, so the table is carried in the content the model reads. (A cross check found three lines that miss a neighbour the deleted `redirects` listed, but those are not client tie breakers, nothing read them, and the lines are at the 220 character cap.)
- **Drop the urgent DBT STOP case (over my pick, keep it).** My objection was that a person about to send a regretted message in their first message gets no offer until their second, and the client's text puts DBT STOP before analysis. The client's overview also says DBT STOP does not replace the established cadence, and the first reply still asks one question and the second may offer. Dropping it removes the last scoring code and the one special path, at the cost named in `index.md`.
- **Told, plus the existing word veto, for Skip when.** Consistent with decisions in force: the reply is not edited and offers are told, not enforced. More word vetoes would put code back to reading words, the thing 0006 and 0007 removed.
- **Scripted tests only.** The cheap proof. It cannot show a model choosing well, so the spec says so in its premise note and leaves measuring to feature 11, as 0007 left it.
- **The line rename (`framework_signs`) became moot.** muhammad accepted the rename in the same round as the cut. With no ranked hint there is no line to name.

Details decided here (RECOMMEND items):
- **`router.py` becomes `vetoes.py`.** A module called router that routes nothing would mislead the next reader. Runner up: keep the file and delete what it no longer needs, which leaves a misleading name.
- **`ruled_out(phrases_by_framework, messages)` returns ids.** The orchestrator currently builds the list from a per framework call. One function over a map from `Registry` is simpler and tests directly.
- **`Registry` checks the veto once per load and ignores a malformed list, logging one error naming the id.** A string would iterate as single letters, and "a" or "i" as a whole word would rule out a framework silently. The seed refuses it too. muhammad chose this over checking in `ruled_out` every turn, which would log an error per turn.
- **The log keeps `cooldown_passed` and drops the shortlist fields.** An offer before the cooldown is still the one event that shows a told rule was broken. Off the shortlist has no meaning now.
- **Slice order.** Tracer first (behavior changes, nothing deleted, revertable alone), then deletion, then docs.

## Probe of the router on plain phrasing

Run 2026-10-08 against the seeded framework files and tuning, calling `router.shortlist` on each line alone, no model and no database. The lines are mine, written to sound like ordinary phrasing for each framework, not the client's examples (the client's six examples all route, which `test_router.py` holds). It is a probe, not a measurement.

| Framework it is about | Line | Shortlist |
|---|---|---|
| behavioral_activation | I've been avoiding my friends because I've been overwhelmed, and I feel guilty about ignoring them | none |
| behavioral_activation | I haven't left the house in days and I just lie on the couch scrolling | none |
| abcde | My boss barely looked at me in the meeting and now I think she's decided I'm useless | none |
| abcde | My sister snapped at me at dinner and I've been spiralling about what I did wrong | none |
| thought_reframe | I keep telling myself I'm going to fail the exam | thought_reframe |
| thought_reframe | I feel like I'm just not good enough for anyone | none |
| structured_problem_solving | I have rent due, a visa renewal, and my laptop broke, I don't know what to sort out first | none |
| structured_problem_solving | There's so much going on at work I can't figure out what to do about it | none |
| act_choice_point | My dad's illness is something I can't fix but it's eating me up every day | none |
| act_choice_point | I can't change that she left, but I still don't know how to move forward | none |
| dbt_stop | I'm so angry at him I want to text him everything right now | none |
| dbt_stop | I'm about to quit my job on the spot after that meeting | dbt_stop |

Two of twelve reached a shortlist. The probe says nothing about whether the model would offer the right set for these lines; that is the part left unmeasured.
