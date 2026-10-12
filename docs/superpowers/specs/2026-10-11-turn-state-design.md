# Turn state for `orchestrator.send()`

Status: draft for muhammad's review. Nothing here is implemented.

## Context

`orchestrator.send()` runs one chat turn. It is 531 lines (`mani/chat/orchestrator.py:316-846`) and has no phase structure: deciding what the person did, asking the model, reading what the model judged, repairing the reply and writing the result are interleaved over about fifteen mutable locals.

The state that matters is reassigned in many places:

| Variable | Reassigned at | Why it matters |
|---|---|---|
| `outcome` | 7 sites | accepted, declined or offered: drives cooldowns and what is written |
| `fixed` | 7 sites | the reply, rewritten by six blocks after `repairs.apply` |
| `accepted_this_turn` | 5 sites | whether the framework starts |
| `offered_now` | 5 sites | which frameworks count as offered |
| `technique` | 4 sites | the live framework |
| `ctx` | 2 sites | the snapshot every later block reads |

The accept or decline decision is made twice, 175 lines apart: once from a tapped button before the model is called, and again from `reply.state` after. They share `deferred` and nothing else.

This blocks the extractions that would make the function readable. A first pass found six candidate extractions, and three are unsafe because each rebinds `ctx` or `technique` (which every later block reads) or returns four to six values. A missed reassignment at a call site is invisible to the type checker and shows up as wrong cooldown arithmetic in production. This is why the work needs a design and not just edits.

## Goals and non-goals

Goals:
- Behaviour is identical: same replies, same stored state, same API, same schema.
- Each place that changes turn state is a named function, and `send()` reads as a sequence.
- Every step is independently revertable, and the suite proves it.

Non-goals: changing prompts or wording, the `Turn` response, the database, `repairs.apply` (227 lines, a separate question) or `context.build`.

## What the tests already pin (measured)

Branch coverage of `send()` by `tests/integration/test_turn.py` alone (60 tests, all executing against the local database): **156 of 164 lines**. The unexecuted lines are all in state-changing branches:

| Lines | Branch | Note |
|---|---|---|
| 352 | thread not found | error path |
| 419 | a tapped decline button moves `outcome` to declined | the pre-model half of the decision |
| 452 | the imminent-action candidate | dormant by design while DBT STOP is paused |
| 575 | the model reports a safety concern | logging only, but it sets `model_concern` |
| 589-592 | a typed yes to a pending offer, reported by the model | the post-model half of the decision |
| 699-701, 725-727 | the body check-in and returning scripts | need seeded somatic content |
| 760-763 | fall-through when a duplicate cannot be replayed | unreachable by construction |

These are the regions a refactor could change without a test failing, so they are covered first.

## Approaches

1. **Leave it.** Zero risk, and the function stays the largest in the service.
2. **Extract only the three clean regions** (`_apply_body_route`, `_updates_for`, and the replay already done). Small and safe, but the tangle stays: the decision is still split and the state is still loose locals.
3. **A `TurnState` object plus phase functions (recommended).** The loose locals become fields of one mutable object, and each phase is a function that reads and writes it. The three unsafe extractions become safe because there is no rebinding to lose: they mutate a shared object.
4. **A pure pipeline returning new frozen states.** No hidden mutation, but every step copies the state, and the code already uses `dataclasses.replace` heavily for `fixed`. More ceremony for the same result, so rejected.

## Design (approach 3)

```python
@dataclass
class TurnState:
    ctx: TurnContext                    # the snapshot; replaced once, when a finished framework retires
    technique: TechniqueState | None    # the framework live on this turn
    outcome: TechniqueOutcome | None
    accepted_this_turn: bool
    offered_now: list[str]
    retiring_framework_id: str | None
    deferred: bool                      # they typed instead of tapping an open offer
    tapped: SmartPrompt | None
    offer: SmartPrompt | None
    updates: ThreadUpdates
```

Phase functions, in the order `send()` calls them:

| Function | Today | Reads | Writes on the state |
|---|---|---|---|
| `_begin_turn` | 350-411 | history, content, config | `ctx`, `technique`, `retiring_framework_id`, `tapped`, `offer`, `outcome`, `accepted_this_turn`, `offered_now`, `deferred` |
| (unchanged) | 413-565 | safety screen, `[ctx]`, the model call and redrafts | none |
| `_read_model_judgment` | 566-640 | the reply | `outcome`, `accepted_this_turn`, `offered_now`, `technique` |
| `_shape_reply` | 641-740 | the repaired reply | none: returns the final `Repaired` |
| `_updates_for` | 741-800 | state, reply | `updates` |

Rules the code keeps: only these functions write `TurnState`; each lists what it writes in its docstring; none returns more than one value; the `ask` closure, the redraft loop and `repairs.apply` stay in `send()` because they own the cost of a turn.

The post-model decision moves into `_read_model_judgment` beside `_begin_turn`, so the two halves of accept/decline are in adjacent, named functions and can be read together.

## Rollout

Five steps, each its own reviewable diff. Nothing is committed until muhammad has tested; each step is a set of files.

0. **Baseline.** Record the pass/fail/skip counts, confirm `test_turn.py` executes (60 passed, none skipped), and confirm the coverage figures above.
1. **Characterization tests** for the four testable gaps (tapped decline, model concern, typed yes to a pending offer, thread not found). They pass on the current code; they pin behaviour and change none. The somatic scripts and the dormant imminent-action branch are left, for the reasons in the table.
2. **`TurnState` and `_begin_turn`.**
3. **`_read_model_judgment`.**
4. **`_shape_reply` and `_updates_for`.**

After each step: full suite, and a mutation check, meaning deliberately break one reassignment and confirm a test fails. This is the check that found the fold loop earlier (`measure-before-tuning-prompts`).

## Risks

- **Aliasing:** `offered_now` is a list mutated in place. `TurnState` owns it, and it is copied when `ctx.techniques_offered` seeds it, as today.
- **`ctx` is replaced once** (when a finished framework retires). Every later read must go through `state.ctx`; a stale `ctx` local is the failure to watch for, so the old local is removed rather than left beside it.
- **Test fakes hide ordering.** The fake model does not exercise provider retries; steps 2-4 change no call that reaches the provider.
- **Hosted compatibility:** none of this touches the schema or the API.

## Acceptance criteria

- The suite has the same counts as the baseline plus the new tests, and `test_turn.py` executes.
- Coverage of `send()` and the phase functions is at least the baseline, with the four gaps closed.
- `send()` is under about 250 lines and no function is reassigning `ctx` or `technique`.
- A mutation of any single state write fails a test.
- No change to a stored row, a response body or a prompt.

## Open questions for muhammad

- Is a mutable `TurnState` acceptable, or do you want approach 4's immutability despite the ceremony?
- Should the dormant imminent-action branch (452) get a test now, or when DBT STOP resumes?
- Step order: should the characterization tests land first on their own, before any structural change?
