# 0001. ABCDE offered when an event and a belief about it are named

**Date**: 2026-10-02
**Status**: In Progress

## Summary

When someone says a person did something to them and they believe that person meant it ("my manager embarrassed me because he wants me to fail"), Mani should offer ABCDE. Today the phrase router finds nothing in that sentence, so at the fourth message Mani picks a framework from its general table and chose structured problem solving. The fix has three small parts: add the client's "assumed motive" phrases to ABCDE's signals, let the router look back four messages so the first message still counts when the closest fit is due, and give the closest fit the top framework's authored offer wording even when the router is not fully confident.

## Context

Backend: `backend/mani/chat/router.py` ranks frameworks from phrase signals in `backend/content/frameworks/*.md`, over the person's last three messages with weights 1.0, 0.6 and 0.3. The model chooses from that shortlist. When the shortlist is empty it sees only the framework table with each framework's central indication. The router only runs in production from the person's second exchange (`orchestrator.py`, `ROUTER_MIN_EXCHANGES`).

In the reported chat (Supportive style) the router returned an empty shortlist at every point. ABCDE's signals are belief sentences such as "so i must be", and "he wants me to fail" is not one. The client's own document uses this sentence as a stage A example, answered inside ABCDE, so ABCDE is the intended framework. The offer arrived at the fourth message, when `closest_fit: due` fires with nothing to guide the model, and the model chose from the table.

Replaying the chat with the new signals showed more gaps. ABCDE scores about 3.0 at message 1, 1.8 at message 2 (below the 2.0 confidence bar), 0.9 at message 3 and 0.45 at message 4. The offer may not come before message 3 (`earliest_offer_message: 3`), by which time the score has faded. At message 4 the first message weighs only 0.15, and without a fourth weight it is outside the window and the shortlist is empty. Even with a faint shortlist entry, a candidate only carries its authored offer lines when the router is confident, so the model would still be guessing at the wording.

## Requirements

**User stories**:
- As a person describing an event and the motive I believe lay behind it, I want Mani to offer the deeper reflection framework, so that I am helped to look at the belief and not handed a plan.

**Acceptance criteria**:
- **AC-1**: For the reported chat ("I'm very upset. My manager embarrassed me today because he wants me to fail." then "EVERYTHING WENT WRONG" then "I felt really embarrassed."), `shortlist` ranks `abcde` first after message 1, 2 and 3. Production runs the router from the second exchange, so the check at message 1 is for the function only.
- **AC-2**: With the reported chat's fourth user message appended, `shortlist` is not empty and `abcde` is first. When the fourth message carries a neighbouring framework's own phrase, that framework may rank above ABCDE, and a test states this so the behaviour is a decision, not a surprise.
- **AC-3**: When the closest fit is due and nothing is running, the top shortlist entry becomes the candidate even if the router is not confident, so the model receives that framework's authored offer lines. A test shows this for the reported chat at message 4, and shows a lone weak match is also carried (the accepted risk).
- **AC-4**: Each client example for the neighbouring frameworks still ranks its own framework first. These examples are already the `redirects` in the framework files and are covered by `test_each_redirect_example_routes_to_the_framework_it_names`, which must stay green.
- **AC-5**: Offer timing is unchanged: `earliest_offer_message` for ABCDE stays 3 and `CLEAR_OFFER_AFTER` and `CLOSEST_FIT_AFTER` stay as they are.
- **AC-6**: The window cannot silently fall behind the closest fit: a test asserts `len(RECENCY_WEIGHTS) >= CLOSEST_FIT_AFTER`.
- **AC-7**: Two intended effects of the fourth weight each have a test: a phrase at message 1 repeated at message 4 counts as corroboration, and a runner up gaining the fourth weight can lower the leader's margin. The tests state the expected result.

## Options considered

### Option 1: Signals, a four message window, and offer wording at the closest fit

Content change for the phrases, one constant in the router, and a small change so the closest fit uses the top shortlist entry as its candidate.

**Pros**:
- Fixes both what the model sees (a ranked hint) and what it says (authored wording), which is where this chat went wrong.
- Does not touch the client's offer cadence.

**Cons**:
- A weak or stale top pick also carries its wording at the closest fit.
- Every framework's signals persist one message longer at a weight of 0.15.

### Option 2: Signals and the four message window only

**Pros**:
- Content plus one constant.

**Cons**:
- The model gets a faint number (0.45) and no offer wording at message 4, nearly the situation that produced the wrong pick.

### Option 3: Offer wording at the closest fit only

**Pros**:
- Small change in context code.

**Cons**:
- The shortlist is empty at message 4 without the window and signals, so there is no candidate to pass.

### Option 4: Lower ABCDE `earliest_offer_message` to 2, or a new discriminator rule

**Pros**:
- Content only, or precise.

**Cons**:
- Offers after one vague reply against the client's "clearly identified" rule, or adds code for something a phrase list says.

## Decision

**Chosen option**: Option 1: Signals, a four message window, and offer wording at the closest fit

Add assumed motive phrases to ABCDE's plain signals, add a fourth recency weight, and make the closest fit use the top shortlist entry as its candidate.

**Implementation skills**: none used (backend Python and content, no community skill applies).

## Rationale

The router was designed so a framework is a content change, and the first miss is a missing phrase list. The window change follows from a number already in the code: the closest fit fires at the person's fourth message while the router only saw three. The third change is there because a hint alone is not enough: the model chose from the table when it had no authored wording to follow, and the offer lines are what make the pick match the client's text.

The phrases are plain signals, not strong ones. The router's comment says strong signals come from a framework's central indication, and a motive sentence on its own is closer to one painful thought (Thought Reframe) than to a specific event. The strong weight would not help here anyway, since message 2 is under the bar either way. Three earlier candidates were dropped: "no respect for me" and "because nobody likes me" are already in abcde.md, and "did not answer because" is Thought Reframe's own strong signal.

Ruled out: lowering `earliest_offer_message` (trades the client's rule for a better score) and a new discriminator rule (a phrase list says it).

## Feature design

**Signal changes in `backend/content/frameworks/abcde.md`**, plain `signals` only (matched as whole words after normalising, with no stemming, so each variant is listed):
- "wants me to fail", "want me to fail", "wanted me to fail", "embarrassed me", "embarassed me", "humiliated me"

The stale comment in that file's activation block that says signals match as "plain substrings" is corrected to whole words in the same change.

**Router change in `backend/mani/chat/router.py`**: `RECENCY_WEIGHTS` becomes `(1.0, 0.6, 0.3, 0.15)`, with the comment saying the window is the last four of their messages, matching the closest fit moment in `context.py`.

**Closest fit change** (`context.py` and `orchestrator.py`): when `closest_fit_due` is true and no framework is running, the candidate is `shortlist[0]` even if `is_confident` is false, so the offer lines are included. Confident behaviour in other cases is unchanged.

**Value sourcing**:
| Action | Value produced | Source |
|---|---|---|
| shortlist | ABCDE score for a message | `strong_signals` and `signals` in `admin.frameworks.activation`, seeded from `content/frameworks/abcde.md`, weighted by `RECENCY_WEIGHTS` |
| closest fit | the candidate whose offer lines are shown | `shortlist[0]` from `router.shortlist`, when `closest_fit_due` |

**Key invariants**:
- Router stays pure: no model call and no database access.
- `repairs.apply` still validates the model's chosen identifier against the registry.
- Safety paths, crisis handling and cooldowns are not touched.

**Security model**: no change. ABCDE's contraindications (abuse, threats, harassment and so on) are read by the prompt and still apply. A phrase like "wants me to fail" can appear in a bullying situation, and that handling is the prompt's job. Because the signals are plain, one sentence alone never makes the router confident.

**Critical test scenarios**:
- Happy path: the reported chat ranks `abcde` first at messages 1 to 4, and the closest fit at message 4 carries ABCDE's offer lines, verifies **AC-1**, **AC-2**, **AC-3**.
- Neighbour cases: existing redirect example tests stay green, verifies **AC-4**.
- Neighbour phrase at message 4: the neighbour may rank above ABCDE, and the test says so, verifies **AC-2**.
- Timing and window: existing context timing tests untouched, plus the window length test, verifies **AC-5**, **AC-6**.
- Fourth weight effects: corroboration across messages 1 and 4, and the margin effect, verifies **AC-7**.

## Build plan

1. [x] Add the six signals to `backend/content/frameworks/abcde.md`, correct the stale comment, and re-seed with `python scripts/seed.py`, satisfies **AC-1**
2. [x] Widen `RECENCY_WEIGHTS` to four entries and update the comment above it, satisfies **AC-2**, **AC-6**
3. [x] Make the closest fit use `shortlist[0]` as its candidate when due and nothing is running, satisfies **AC-3**
4. [x] Add tests to `tests/unit/test_router.py` (reported chat at messages 1 to 4, neighbour phrase at message 4, window length, fourth weight effects), reusing its `ACTIVATIONS` built from the real files, satisfies **AC-1**, **AC-2**, **AC-6**, **AC-7**
5. [x] Add a context test for the closest fit candidate, satisfies **AC-3**
6. [x] Run the whole `pytest` (including `tests/evals`) and confirm the existing timing and redirect tests pass unedited, satisfies **AC-4**, **AC-5**
7. [x] Update `backend/PORT-STATUS.md` in the same change, as BACKEND.md requires, satisfies **AC-1**

## Consequences

**Positive**:
- The reported chat gets a ranked hint and the client's authored ABCDE offer wording at the moment the offer is due.

**Negative / tradeoffs**:
- A fourth, low weight message of memory applies to all frameworks, so a stale framework can appear in the hint at message 4.
- A weak top pick now carries its authored wording at the closest fit. Message 5 can still have an empty shortlist if the offer did not happen at 4.
- The model still makes the final choice, so this raises the odds, it does not guarantee the pick.

**Neutral**:
- Needs a re-seed after the content edit.

## Follow-up

- [ ] Run `scripts/eval_replies.py` on this chat as a real model check; kept out of this spec at the engineer's choice of router tests.
- [ ] Check that the Supportive offer wording in `abcde.md` matches the client's ("This one event has come to mean something much larger about you. Would it help to look at it together?").
