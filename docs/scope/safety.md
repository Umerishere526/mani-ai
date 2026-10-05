# Scope epic: Safety and privacy

Noticing when someone is in danger, answering with real help, and keeping health conversations private. These carry the most risk in the product, so every feature here runs the GA workflow. The evidence is in the backend audit and the team summary from October 2026. Back to [the index](index.md).

## Slice 6: Safety first

### 9. Crisis help a person can use · needs a decision · GA

When Mani detects a crisis today it gives no phone number or service, says "I'm not going anywhere", and then refuses every later message in that chat. The approved safety question, the reply for each kind of risk and the crisis services per country are all empty, because they must come from the client or a clinician (see the index).
**Done when:** every kind of risk the client lists gets its approved reply, the person sees checked crisis services for their country, the wording matches what then happens in the chat, and a clinician has signed it off.

- [ ] Design it (spec): `/architect crisis help a person can use`

### 10. Danger detection catches real phrasing · needs a decision · GA

The screen matches a short list of exact phrases. It misses "I am suicidal", "I'm going to hang myself", "I took 30 tablets", "I have a knife" and anything not in English, and it locks the chat on "I want to diet before summer" or "I would never kill myself". DBT STOP can be fast tracked for messages that need the safety response, and for protective actions like "I'm about to call the police".
**Done when:** a clinician labelled set of at least 300 messages meets the agreed catch rate and false alarm rate, runs on every change, and no message on that set that needs the safety response is routed to DBT STOP.

- [ ] Design it (spec): `/architect danger detection catches real phrasing`

### 11. Safety mode follows the person · needs a decision · GA

The crisis lock lives on one chat, so "New chat" gets around it, and a false alarm can never be undone. A worry flagged by the model is forgotten after one message, can be lost when the reply is rewritten, and leaves no record. Messages typed into a locked chat are not saved or checked.
**Done when:** a confirmed concern puts the person (not the chat) into a safety mode that holds across new chats until it is resolved, every message in that mode is saved, checked and recorded, a named owner can review and resolve it, and the choice between lock and safety mode follows the team's decision.

- [ ] Design it (spec): `/architect safety mode follows the person`

### 36. A short answer to Mani's safety question is checked · needs a decision · GA

When Mani asks whether someone is safe and they reply "yes" or "no", the safety screen reads only that reply, finds nothing, and the answer is treated as an ordinary message. This is true today. From spec 0002 (Mani speaks naturally), whose cross check found it.
**Done when:** a short reply to a safety type question from Mani is read against that question, an answer that confirms danger puts the person into the safety response, and the set of messages row 10 builds includes such replies.

- [ ] Design it (spec): `/architect a short answer to Mani's safety question is checked`

### 37. The model's safety flag does not stall DBT STOP · done · GA

When the model reports a safety concern, the running framework is paused for that turn: nothing is recorded, so the stage lags and the person can be asked the same question twice or miss the body check. In DBT STOP the model reports one often, because the person is describing an urge to act ("potentially volatile situation"), which is what the framework is for. From spec 0003 (a framework stage moves on after one answer): in 54 real conversations two did not reach the body check, and a trace showed the pause on those turns. It overlaps row 11, which decides what a flag from the model means.
**Done when:** a person in DBT STOP whom the model flags as in a volatile situation, but not at risk of harm, keeps moving through the stages and reaches the body check, a real risk still stops the framework and gets the safety response, and a test over the client's STOP conversations shows both.

Spec: [0004](../specs/0004-safety-flag-kind-decides-pause/index.md) · code in backend/mani/chat/, backend/mani/llm/schema.py, backend/scripts/

- [x] Design it (spec): `/architect the model's safety flag does not stall DBT STOP`
- [x] Build it: `/develop the model's safety flag does not stall DBT STOP`
  - [x] The authored risk set and the baseline on today's code (AC-9)
  - [x] The kind on the flag, the rule, the orchestrator, notes and log (AC-1 to AC-5, AC-7)
  - [x] The instruction on the flag, in the prompt and the description, with its test (AC-6)
  - [x] Measure, client sign off, record it (AC-8, AC-9, AC-10)
- [x] Verify it: `/check verify the model's safety flag does not stall DBT STOP`
- [x] Test it: `/test the model's safety flag does not stall DBT STOP`
- [x] Review it (fresh model): `/check review the model's safety flag does not stall DBT STOP`
- [x] Document it: `/document the model's safety flag does not stall DBT STOP`

## Slice 7: Ready for a limited beta

### 13. Private conversations stay private · needs a decision · GA

Parts of people's conversations can reach the error reporting service, stored error text, and the AI provider for voice messages without the "do not store or train" setting. Some of that text survives account deletion.
**Done when:** no conversation text reaches error reports, logs or stored error records, voice messages use the same privacy setting as chat, deleting an account removes every record tied to it, and a test checks each of these.

- [ ] Design it (spec): `/architect private conversations stay private`

### 14. Database permissions match what users should do · needs a decision · GA

Signed in users can still delete chats, change a chat's last message time, undelete chats and add rows the app writes, directly through the database's public interface. Deleting a crisis chat that way can also erase its crisis record.
**Done when:** users hold only the permissions the app needs them to have, crisis records cannot be erased by a user, and the database permission tests assert it.

- [ ] Design it (spec): `/architect database permissions match what users should do`

## Slice 9: Robust for open launch

### 21. Hard safety rules enforced in code · needs a decision · GA

The client's "never" rules for danger (never reinterpret abuse, never use Behavioral Activation for a medical problem or intoxication, never use ACT acceptance on abuse, never delay someone leaving danger) reach Mani only as instructions. Code should block a framework when these signals appear in the conversation.
**Done when:** each rule has a code check over the recent conversation, and a test shows the matching framework is never offered or continued when its signal is present.

- [ ] Design it (spec): `/architect hard safety rules enforced in code`

### 24. Memory and notes kept apart from instructions · needs a decision · GA

What Mani remembers about a person is written by the model from their own messages, then placed among Mani's instructions in every later chat. Someone can plant an instruction that comes back forever. The app's own notes to the model sit inside the person's message instead of beside it.
**Done when:** remembered text and summaries are clearly marked as the person's data, are checked before they are stored, and a test shows a planted instruction does not change Mani's behaviour in a later chat.

- [ ] Design it (spec): `/architect memory kept apart from instructions`

### 25. Admin access guarded and recorded · needs a decision · GA

An admin login can read every person's memory and crisis records, with no second sign in step and no record of what was read.
**Done when:** admin access needs a second sign in factor, and every admin read of a person's data is recorded with who, whose and when.

- [ ] Design it (spec): `/architect admin access guarded and recorded`
