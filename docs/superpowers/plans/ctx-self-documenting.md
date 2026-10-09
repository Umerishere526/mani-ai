# Plan: make `[ctx]` explain itself

Move the `[ctx]` key dictionary out of `response_format.md` and into `context.py`, so a key's
explanation is sent only on the turns the key is actually sent.

**Spec:** `backend/docs/specs/` for the client's rules. `backend/PORT-STATUS.md` for decisions in force.

## The measurement that justifies this

Taken 2026-10-08 against the live files.

| | chars |
|---|---|
| `response_format.ctx` — the dictionary, sent on every turn | 3,970 |
| `response_format.their_last` — the follow-on block | 964 |
| **paid every turn** | **4,934** |

What a turn actually emits, measured with the real `context.build()`:

| Turn | keys emitted | the block itself |
|---|---|---|
| Understanding, their 2nd message | 5 | 154 chars |
| Closest fit due, their 4th message | 6 | 171 chars |

So a plain turn pays **4,934 characters of dictionary to explain 154 characters of block.**
Roughly 1,250 tokens, on every call, to define 17 keys that are not present.

The largest entries are the ones that fire least:

| chars | key | fires when |
|---|---|---|
| 442 | stage lines | only inside a framework |
| 324 | offer lines | only when a candidate is confident |
| 317 | this_thread | only after something was offered |
| 292 | clarification_available | common |
| 280 | offer_waiting | only when an offer is typed past |
| 255 | conversation_phase | always |
| 254 | their_last (ctx entry) | rare |

## The change

`context.py` already owns every key. It gains the sentence that explains each one, and emits
the explanation beside the value — so the model reads a key and its meaning together, in the
one place it matters, and never reads the other 17.

Before, in two places:

```
# response_format.md, every turn
their_last: present when their message said almost nothing, said you missed something, ...

# [ctx], only on the turns it fires
their_last: vague
```

After, in one:

```
# [ctx], only on the turns it fires
their_last: vague — they gave you almost nothing. Do not treat it as an answer, do not mirror
  it, do not ask again. Take the last real thing they told you and ask a short question ...
```

## Global constraints

- **Key names do not change.** The names are the contract between `context.py` and the model.
- **No behaviour change.** Same keys, same values, same order. Only where the explanation lives.
- **`response_format.md` keeps `about`.** The model must still be told what `[ctx]` is and that
  it is never mentioned, quoted or answered — that is true before any key is read.
- **The explanations are the client's rules in places.** `clarification_available` carries two
  verbatim client questions; `safety` and `their_last` carry clinical handling. Moving text is
  allowed, rewording it is not.
- **`stage_note` is already self-documenting** — `context.py` writes the whole sentence today.
  It is the model for this change, not a thing to change.
- Each task: edit, `pytest`, seed, confirm the database matches, read one built block.

## Task 1: carry the explanations in `context.py`

**Produces:** a `_MEANING` mapping in `context.py`, key → the sentence that explains it.
**Consumes:** the text of `response_format.ctx`, moved verbatim.

1. Add `_MEANING: dict[str, str]` to `context.py`, one entry per key, text moved from
   `response_format.ctx` unchanged.
2. Add a helper that appends `key: value — meaning` for the keys that have one, leaving the
   others as they are.
3. Route every `lines.append` through it.
4. `tests/unit/test_chat_context.py` asserts `"closest_fit: due" in block` and similar — those
   still pass, since the key and value are unchanged and the meaning follows.
5. Add a test: a built block for a plain turn contains no `stage` or `offer` meaning.

**Expected:** a plain turn's block grows from ~154 to ~700 chars; the system prompt loses ~4,900.
Net saving ~4,350 chars per turn, and the uncached part of the turn grows slightly — which is the
trade, because the block is the part the model reads closest.

**To judge it:** print a built block for an ordinary turn and read it as the model would.

## Task 2: cut `ctx` down in `response_format.md`

1. Reduce `ctx` to `about` only — what the block is, that it is for the model, that it is never
   mentioned, quoted or answered, and that each line carries its own meaning.
2. Delete the `their_last` block; its three branches move into the `their_last` meaning in Task 1.
3. Parse-check, `pytest`, seed, confirm lengths.

**Expected:** `response_format.md` drops from ~8,400 to ~3,500 chars.

**Risk:** a key whose meaning was dropped rather than moved. Task 3 is the guard.

## Task 3: a test that binds the two

The files and `context.py` have drifted before — four offer keys were undocumented until this
week, and `their_last` described a signal the code withholds. Nothing caught either.

1. Add `tests/unit/test_ctx_meanings.py`: every key `context.py` can emit has an entry in
   `_MEANING`, and every `_MEANING` entry is a key that can be emitted.
2. Derive the emitted set from the module, not a hand-written list, or the test rots with the file.

**Expected:** the drift that caused C1 and C2 becomes a failing test.

## Task 4: documentation

1. `PORT-STATUS.md` — one line under "Decisions in force": the `[ctx]` dictionary lives in
   `context.py` beside the values, not in the prompt.
2. Journal note recording the measurement above, so the next person does not re-derive it.

## Not in this plan

- **Compressing prose to keyword lists** (`tone: [warm, friendly]`). Verified against the files:
  roughly 80% of both prompts is conditionals ("when X, do Y") and prohibitions ("never say X,
  never call it therapy"). A keyword list cannot carry either. `consent_lines`, `reply_shapes`
  and `moves` are already at minimum. The saving is small and the risk is dropping a client
  requirement silently.
- **The 8,192-token reasoning allowance** dwarfs every prompt saving discussed here. If cost is
  the goal rather than clarity, that is the lever, and it is a different decision.

## Review focus

- No key renamed, no client wording reworded.
- No meaning lost between the file and `_MEANING`.
- The block still reads as instructions to the model, not as a data dump.
