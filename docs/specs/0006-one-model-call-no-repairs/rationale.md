# 0006. One model call per turn, with integrity guards and no reply repairs: decision record

The build spec is [index.md](index.md).

## Context

A chat turn today can make up to three model calls. `mani/chat/redraft.py` checks each draft for six faults: a feeling word the person never used, a closing question that repeats the last one, no question at all, an offer before the cooldown allows it, an offer of a framework the person's words rule out (the grief veto on Behavioral Activation), and no offer once the closest fit is due. A failing draft is sent back with `rewrite:` lines added to `[ctx]`, once, and a second time when it still asks no question (`orchestrator.py`, the `_why` loop). On top of that, `client.complete` retries once when a reply does not parse, so a malformed chat reply is a second billed call.

What survives the redraft then passes through `repairs.apply` (634 lines), which edits the reply in code. It strips leaked script markers, removes a repeated clarification question, removes the person's name when overused, cuts any sentence naming a feeling they never named, and polices buttons (duplicates, the one just tapped, explain buttons, feeling or judging labels, labels over five words, more than three, buttons outside an offer). It drops offers made before the cooldown or of a finished framework, cuts the offer's sentence when its button goes, and builds every offer itself: the model's sentence, then the client's framework description word for word, then the client's permission question for the style. Mixed into the same function are checks of a different kind. Those stop an unknown framework id, a stage reported for a framework that is not running, an out of order stage, an unknown library section or an off list style shape from being stored.

The lean prompt scope (`docs/scope/scope.md`, feature 5) sets the goal: fewer tokens and lower latency, and a model that follows short rules instead of being corrected after the fact. Spec 0005 (in progress, uncommitted on the same branch) already removed the earliest offer redraft and rewrote the frameworks as eight lines. The base prompt (`content/prompts/mani_base.md`) and `response_format.md` already state the rules the repairs enforce: no feeling they have not named, their name at most once and never first, never the same question twice, one question per reply, buttons only under an offer or at the end, labels of one to five words. `[ctx]` already reports `cooldown_passed`, `closest_fit` and `this_thread`.

Three boundaries hold. The body check in code (the word for word check in, the practice by place, the returning reply, the Chat More and Go to Library buttons) belongs to feature 7. The safety screen and the safety concern pause belong to feature 10. muhammad chose not to run real model conversations for this feature, so it is proven by the scripted test suite alone.

## Options considered

### Option 1: Remove the redraft loop, keep the repairs

One model call per turn, but `repairs.apply` keeps editing the reply: feeling sentences cut, offers composed, buttons policed, early offers dropped.

**Pros**:
- One call per turn, so the cost and latency win lands with the smallest code change.
- The client's description and permission questions stay word for word.

**Cons**:
- The person still reads replies with sentences cut out and offers stitched together by code.
- Behaviour stays split between the prompt and 600 lines of regular expressions, which the scope sets out to end, and a prompt improvement is masked by code that corrects it anyway.

### Option 2: Remove the redraft and every reply edit, keep integrity guards

One call, the reply as written, and code after the call only stops bad ids and values reaching the database or the app. Offer timing and the grief veto become facts in `[ctx]`.

**Pros**:
- Matches the scope's goal: one call, short rules, nothing rewritten.
- Stored state stays safe, because a model supplied id is still checked before it is written.
- About 700 lines of code and their tests go.

**Cons**:
- No backstop: an early offer, a named feeling or a repeated question reaches the person when the model slips.
- A guard that drops a `technique` button (unknown id, running framework, safety concern) can leave offer words with no button under them.

### Option 3: Remove everything after the call

Trust the schema alone: no guards, every id and value stored as the model sent it, or closed sets typed as enums.

**Pros**:
- The least code of all.

**Cons**:
- An unknown framework id or an out of order stage reaches `thread_technique_state`, and a wrong library section sends the app nowhere.
- Typing the closed sets as enums turns a small slip into a `ValidationError`, which with no retry loses the person's turn (the reason `schema.py` keeps them as plain strings).

## Rationale

The scope's premise is that a short rule the model reasons from beats code that corrects it afterwards, and that the cost of a turn should be one call. Option 1 gets the call count but keeps the half of the problem the person actually sees: replies with sentences removed and text added. Option 3 goes past the goal and gives up safety of stored state, which no prompt can provide. Option 2 draws the line where it belongs. Anything that changes what the person reads is the model's job. Anything that protects a row or a navigation target is code's.

The prompts already carry every rule the repairs enforced (see Context), and `[ctx]` already reports the offer timing, so most of this change is deletion. The two gaps are filled where the model reads them. The grief veto becomes a `ruled_out:` fact, and the client's description moves into the cached index so the model can still tell the person what the questions would help with (muhammad's 2026-09-24 wish) in its own words. muhammad has standing permission to reword the client's lines (2026-10-05), which covers the permission questions no longer being verbatim.

Recommended calls settled here:
- **The schema retry is switched off by a keyword on `client.complete`, `retry_malformed: bool = True`, and the chat turn passes `False`** (runner up: decide by `purpose` inside the client). The call site then shows the choice, and the retry loop keeps one shape for both failure kinds.
- **A vetoed framework is filtered in the orchestrator, before the offer candidate is picked** (runner up: filter inside `router.shortlist`, or inside `context.build`). Spec 0005 requires `test_router.py` to pass untouched, which rules out the router. Filtering in `context.build` would be too late: the candidate and its confidence are decided before `build` is called, so a vetoed top item would block or skew the offer.
- **The orchestrator computes `ruled_out` from `router.vetoes` over `registry.activations`** and passes the ids to `context.build` (runner up: `context.build` calls the router itself). The orchestrator already holds `user_texts` and the registry, and `context.build` stays a pure function of what it is handed.
- **Three state guards are added where repairs used to cover them by accident**: no offer button on a decline or retiring turn, an offer's companion buttons go with it, and only the handoff sets `library_offered`. The cooldown and already offered drops happened to stop a model button from overwriting the stored decline or retirement, and the "buttons outside an offer" drop happened to keep a stray library button from silencing `library_pending`. With those drops gone, the state needs its own guards. They change no text.
- **`ruled_out` is not shown while a framework runs**. No offer is possible then (the running framework guard), so the line would be noise.
- **The description is its own `Description:` line outside the eight lines** (runner up: a ninth line in the body). The seed check from spec 0005 stays exactly eight lines, and the summary already lives in its own column.
- **Guard notes are logged as `checked reply on thread <id>: …`, and `eval_replies.py` captures them as `guard_notes`** (runner up: drop the log). How often a guard fires is the one measure left of the model slipping on structure.
- **Old tests are deleted, not rewritten** (muhammad's choice). The new tests cover only the new behaviour and the one call contract.
