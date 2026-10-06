# 0005. Rationale: a framework is chosen from facts the model states

The decision record behind [index.md](index.md).

## Context

Mani offers one of six frameworks (ABCDE, Thought Reframe, Behavioral Activation, Structured Problem Solving, ACT Choice Point, DBT STOP) once it understands what is going on. The client's documents say how to choose: a selection table ("what MANI has identified" against "what the user wants") and a short list of tie breakers between pairs ([six-frameworks-overview.md](../../../backend/docs/specs/six-frameworks-overview.md)).

The backend reads the person's meaning in two places today. `backend/mani/chat/router.py` matches hand written phrases from each framework file (whole words, the last four messages weighted 1.0, 0.6, 0.3, 0.15) and six rules on phrases, and puts a ranked shortlist in the hidden context block. The model reads a one line description of each framework and chooses freely, reporting its choice in `heading_toward` and whether it is a clear or closest fit in `offer_fit`. No code checks that choice against the conversation. At the person's fourth message the closest fit is owed (ADR 007), and a redraft forces an offer if the model holds back.

Two chats on 5 October 2026 show where this breaks. In the first ("i feel emotionally stressed", "work pressure, parents pressure, society pressure", "yes", "i suggest at all of them") no phrase matched, nothing specific had been said, and the closest fit at message four produced Structured Problem Solving. muhammad expected ABCDE or Thought Reframe; by the client's own rules neither fits yet either (no event, no single thought), so the right move was a question about what happened. In the second ("I feel like I might have a panic attack" and three grounding replies) no phrase matched and the closest fit produced ACT. The client's overview lists "panicked" under DBT STOP, but our DBT STOP file, and the client's detailed DBT STOP specification, describe only pausing before an action, so DBT STOP had no way to be chosen and no wording for panic.

The cost of not deciding is the one row 8 of the scope names: every missed wording becomes another phrase, and the lists can never cover what people actually say. Constraints: one model call per turn with at most one redraft (ADR 002, ADR 006); OpenRouter as the only provider; conversation content is special category health data and must not reach logs or error reports; about 2 dollars of model budget left, so real runs are rare and asked for.

## Options considered

### Option 1: The model states the facts, code applies the client's table

The model, in the same reply, writes a checklist of ten facts drawn from the selection table, each with the person's words. Code drops any fact whose words the person never typed, finds which frameworks fit, and orders them with the client's tie breakers. A disagreeing offer is redrafted once and then removed. The imminent action phrases and the never offer vetoes stay as deterministic code.

**Pros**:
- Reads meaning, including negation ("I know what to do but can't start") and the absence of anything specific.
- No new provider, storage or per turn call; a few output tokens.
- The choosing rules are pure functions of a fact list, so every rule and conflict is unit tested for free.
- The quote check stops an invented fact from steering.

**Cons**:
- Correctness rests on how well the model fills the checklist, which only a paid run measures.
- A mismatch costs a second call for that turn.
- Loses the free, exact recall the phrase lists gave on the client's own example sentences.

### Option 2: An embedding router

Embed each framework's routing profile (examples, plus negative examples) with an embedding model, store the vectors (pgvector in Supabase, or in memory at this size), embed the recent conversation each turn, and rank frameworks by cosine similarity over the top k matches, with a minimum score and margin. Researched by muhammad as a hybrid: hard rules, then semantic candidates, then a decision layer.

**Pros**:
- Matches paraphrases the phrase lists miss.
- Deterministic once the vectors exist; scores are inspectable.

**Cons**:
- Similarity measures topic, not the structure the client's table turns on (an event named or not; knows what to do or not); weak on negation.
- Always returns a nearest neighbour; "nothing specific yet" needs a cutoff that is unreliable on short messages like "yes" and "all of them".
- Panic would match only if panic examples were written for DBT STOP, so example lists are maintained again.
- Needs an embedding provider (possibly a second one receiving health data), an ingestion step, one more network call each turn, and a cutoff tuned on labelled chats we do not have.

### Option 3: Widen the phrase router

Add panic and overwhelm phrases to DBT STOP and make the closest fit conditional on something having scored.

**Pros**:
- Smallest change; deterministic and free.

**Cons**:
- Fixes today's two wordings and none of tomorrow's; it is the pattern row 8 exists to end.

### Option 4: A separate classification call

A small model call before each reply labels the situation against the selection table; the reply call then offers what it was told.

**Pros**:
- Semantic, and isolated enough to evaluate on its own.

**Cons**:
- Breaks ADR 002 on every turn, not only on a mismatch; adds cost and delay to every message.

## Rationale

The failure in both chats was not a missing phrase, it was that nothing in the system could say what the person had actually described, so the fourth message forced a guess. Option 3 adds phrases and leaves that intact. Options 1, 2 and 4 all add a semantic reading; they differ in what produces it and what it costs. The chat model already reads the whole conversation on every turn, and asking it to name ten facts with quotes costs a handful of tokens, where embeddings need a provider, storage, ingestion and a tuned cutoff, and a classifier call doubles the calls on every turn. More importantly, the client's table is structural: ABCDE needs an event and its meaning, Structured Problem Solving needs a problem and not knowing what to do, Behavioral Activation is knowing and not starting. Facts express that structure directly, where a similarity score blurs it. And facts can be absent, which is exactly what chat 1 needed: with no fact, nothing is owed and Mani asks.

Putting the judgement in the model raises the question of trust, which is why the design keeps the decision in code. The words check means a fact must be anchored in what the person typed; the pick is computed, not reported; a disagreeing offer gets the one redraft ADR 006 already allows and is removed if it persists, using the repair path that already removes disallowed offers. The two rules where a phrase is the right tool stay as phrases: an imminent action, where waiting is the failure, and the grief vetoes, where a single word rules a framework out.

Several smaller calls were made with muhammad during the design. The closest fit stays at message four but only when a framework points somewhere (ADR 007 is amended, not dropped, so grief and exam chats still reach an offer). `overwhelmed_now` is defined as being flooded in the moment, because a literal reading of "overwhelmed" would send ordinary stress, chat 1 included, to DBT STOP. ABCDE wins over Thought Reframe when an event is named, following the client's distinction. The "what the user wants" column is left out of the checklist because people rarely say it. Steering happens from the model's own checklist in the same reply, because a stored checklist would be one message behind and would ask again about what the person just said. DBT STOP gets panic wording now rather than waiting for the client, because the client's overview already lists panic under it and the alternative leaves panicking people with no fitting framework; the wording goes on the sign off list.

A cross check by a second model added several calls. `overwhelmed_now` puts DBT STOP above the reflective frameworks but not above a full Structured Problem Solving fit, because ADR 010's lost wallet chat ("I am panicking" with a practical problem) was accepted as Structured Problem Solving; the client's overview says STOP comes before problem solving, so this rule goes on the sign off list. Both STOP facts must be quoted from the person's last two messages, because a panic from eight messages ago is not the state they are in now. A bare "I don't know" in answer to Mani's question is not `unsure_what_to_do`, or every hesitant reply would lead toward Structured Problem Solving and bring chat 1 back. A declined framework is left out of the pick during its cooldown, so Keep chatting can lead somewhere else.

The cross check also proposed a smaller alternative: keep the model's own `heading_toward`, require one quoted and checked reason for it, force the closest fit only when that quote checks, and add the DBT STOP panic content. It is a fraction of the change. It was not chosen because the model still chooses freely: in chat 1 the quote "work pressure" checks out, so Structured Problem Solving would be forced again, and nothing applies the client's tie breakers in code.

muhammad's research proposed embeddings as the semantic layer of a three layer router. The three layers are kept (hard rules, a semantic reading, a decision layer); the semantic reading is the model's stated facts rather than similarity scores, for the reasons above. Its suggestion of routing profiles with negative examples lives on in the fit sets and tie rules, and in the plain meanings the model is given.

## Update, 2026-10-05: full fits only

**What the first real runs showed.** With facts in place, the stress chat ("work pressure, parents pressure, society pressure") still got an offer at the fourth message in 2 of 3 runs: once ACT as a full fit, the model marking general pressure as `cannot_control`, and once Structured Problem Solving as the nearest fit, from facts that only pointed to it. Tightening the meaning of `cannot_control` moved the offer later; it did not stop it. The reading: at the fourth message `[ctx]` said `closest_fit: due` for anyone with nothing running, since it is built before the facts exist, and the model marked facts loosely to justify the offer it was told was owed. The words check cannot catch that, because the words were theirs. The evidence for this reading is thin: in an earlier run the same chat got ACT at message 3, before any `due` line existed, so the push explains the nearest offer but not all of the loose marking.

**Options weighed.**

- *Full fits only (chosen).* No nearest offer at all; the leading framework only steers the question. Removes the push and fixes the nearest offer outright. Con: a chat whose facts never fully fit gets no offer, and the chats ADR 007's owed offer was written for (grief, an exam) now depend on the model marking facts; grief did reach ACT as a full fit in every run, but that is three runs.
- *Keep the closest fit, never owed.* Smaller, but nothing stops the model choosing the nearest on its own, which is what the second run did.
- *Accept the nearest for named pressures.* Structured Problem Solving for several named pressures matches the client's "several problems need separating", but leaves ACT for general pressure unexplained.
- *Stricter facts in code.* Refusing quotes that are only a list of general areas reads meaning from wording again, the phrase list problem this spec removed.

**Why.** The failure was an offer the person had not earned, and a nearest offer is that by definition. The full fit offer keeps one push the cross check asked for: from the fourth message a pick the model has not offered is asked for, because a clear fit left unoffered makes a chat circle; it cannot push a nearest offer, though it can push a full fit the model marked loosely, which the plain meanings alone guard against. Whether removing the push is enough to stop the model marking facts loosely is measured, not assumed (AC-17), and if it is not, that goes back to muhammad as a separate problem.
