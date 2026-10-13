# 0005. Rationale: questions follow what they said

## Context

> ⚠️ Premise note: before an offer the whole conversation fits inside the 20 message window (the offer is due by their fifth message), so the stored record adds no memory there. What it adds before the offer is a named place for their feeling that every turn rereads, and a value code can place. The live failure below is most likely the checklist and the feeling bans in the prompt. The live run should tell which part fixed it. The record earns its place either way: R6 needs it past the window, and A's slot needs a feeling that code holds.

The client asks that Mani understand the person's actual issue (R4) and keep what they said in view across the conversation (R6). Live on 2026-10-13, in muhammad's Directive tester runs (threads 4ec47e15 and ca968cbd), a chat opened "i am frustrated". The word never came back. By the third question Mani asked "What goes through your mind when the client asks to return to an earlier version?", which is ABCDE's `to_find_out` item "what they began telling themselves about it". The offer in 4ec47e15 then read "the thoughts behind your client deciding what they want before asking you to go back again": their judgment of the client in the slot meant for their feeling.

How it works today. Nothing holds the feeling. The model rebuilds everything each turn from the last 20 messages. `thread_summaries.current_issue` exists, but the background summary writes it only after 20 messages, so it is empty for the whole conversation before an offer. The yes turn's `feeling` field (spec 0004) is read once, for A's line, and thrown away. The system prompt carries a static "Finding the fit" list of what each framework needs, and a cheap model at effort `low` reads a list like that as a script. Three prompt lines push the model away from their feeling: `reflecting` forbids handing their feelings back, and the reasoning step tells it to leave out any of their words or feelings it would say back. Those lines were written against restating (R3, 2026-10-12). Their side effect is that the feeling is also kept out of questions and out of the offer slot.

Forces: a turn is one call at effort `low` (Decision in force, R2). No phrase lists may judge the conversation. Prompt fixes cut rules, they don't add them (muhammad, 2026-10-08). Conversation content is special category health data. OpenRouter is the only provider.

## Options considered

### Option 1: Prompt rewrite alone

Cut "Finding the fit" and the feeling bans, add the one question rule, store nothing.

**Pros**:
- The smallest change: no migration, no new field, no new tokens per turn.
- It may fix the frustrated chat on its own, since that conversation fits in the window.

**Cons**:
- Nothing holds the feeling past the 20 message window, so R6 stays open for long conversations and after Keep chatting.
- A's slot still depends on the model naming the feeling on the yes turn, a one off read.
- muhammad rejected it on 2026-10-13 as not enough on its own.

### Option 2: Provider conversation state

Let the provider keep the conversation (the OpenAI conversation or `previous_response_id` style API) instead of resending history.

**Pros**:
- No history to resend and no window to fall out of.

**Cons**:
- OpenRouter rejects stored state, and OpenRouter is our only provider.
- It changes what the model remembers, not what it is told to ask, so the checklist would still steer the questions.
- The state would sit with a third party, outside our RLS and deletion.

### Option 3: A running understanding reported by the model, merged and stored by code (chosen)

The reply carries what this message names or changes (their feeling, their issue). Code merges it into `threads.understanding` and sends it back in `[ctx]` every turn. The prompt cuts the checklist and the bans and gains one positive rule.

**Pros**:
- Still one call: the update rides on the reply the model already writes.
- Code owns the record, so the low effort model cannot silently drop the feeling (null keeps), and code can place it in A.
- The same pattern as the stage store (spec 0004), which the team already maintains.

**Cons**:
- About 15 to 30 more output tokens per turn.
- A wrong feeling or issue, once stored, steers later turns until corrected.

### Option 4: A background summary call every turn

Run the summary call after every reply instead of every 20 messages, and read `current_issue` from it.

**Pros**:
- The reply schema does not change; the summary prompt already exists.

**Cons**:
- A second model call per turn, which the one call decision forbids (cost, and R2).
- It runs after the reply, so it is always a turn behind: question 2 could not build on answer 1.

## Rationale

Option 3 is the only one that fixes both the behaviour (questions drift to the checklist, the feeling vanishes) and the memory gap (nothing holds the feeling or the issue past the window) without a second call. Option 1 fixes the behaviour but leaves R6 and A's slot resting on a one off model read. Option 4 holds memory but breaks the one call decision and lags a turn, which defeats the point of question 2 building on answer 1. Option 2 is not available on OpenRouter, and it would not change what the model is asked to do.

Inside Option 3, the record is typed (feeling, issue) rather than a prose paragraph, because code reads the feeling for A's slot and prose would need parsing. A third part, a list of what each answer added, was chosen first and then dropped after the cross check (muhammad, 2026-10-13). Before an offer every answer is still in the 20 message window. Inside a framework `stages_known` already holds them. Past the window the summary prose carries them. The list would also have handed the model ready paraphrase to restate (R3) and cost about 400 tokens on every turn. Nothing is stored from a concern turn, as spec 0003 AC-12 holds for every reply field, so a sentence about risk is never resent in later turns. The model reports changes and code merges them, rather than the model rewriting the whole record each turn, because a careless turn at low effort would otherwise lose the feeling. This is the same lesson that made code own the stage store. `feeling` is limited to their own word because Mani never tells people what they feel (`mani_base` `rules`). The offer slot stays the model's to fill, because turning "frustrated" into "your frustration" needs a word form that code could only get from a word list.

The record replaces `current_issue` instead of sitting beside it. Two homes for "their issue", one 20 messages stale, would disagree. `current_issue`'s only readers (Conversation Context and the exercise pick) are better served by a value that is fresh every turn. It lives on `threads`, not `thread_summaries`, because that row exists only after 20 messages and is written by the background fold. It lives in `[ctx]`, not Conversation Context, because `[ctx]` is the per turn channel the model is already taught to read.

The prompt change is net cut, as muhammad's standing rule asks. One rule replaces "Build every question from what they actually said", and four things go: the "Finding the fit" section, `to_find_out`, the reflecting ban on feelings, and the reasoning step that left their feelings out. The rule keeps R3's limit (never as a statement about them) without quoting a banned shape. A quoted bad example became a template for a low effort model on 2026-10-12 (journal, restating is not reflecting).
