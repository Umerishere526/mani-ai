# Scope: Mani somatic check

Mani is a mental health companion. This scope covers one thing: the body check at the end of a framework, built to match the client's wording and flow for the Direct, Supportive and Reflective styles.

**Build approach:** Tracer Bullet (get one style through the whole flow end to end, then repeat for the others).
**Workflow:** Beta (check verify, then test). The reply text is health content the client signed off on, so it needs a real conversation run, not only unit tests.

_These are recommendations to keep your build orderly, not requirements. Skip anything that does not fit._

## At a glance

| # | Feature | Phase | Status |
|---|---------|-------|--------|
| 1 | Somatic check asked once, then moves on | Slice 1 | done |
| 2 | Where in the body, with buttons, then the exercise | Slice 1 | done |
| 3 | Per style wording from the client | Slice 2 | done |
| 4 | Returns in waves, then the library offer | Slice 2 | done |

## Slice 1: The flow works

### 1. Somatic check asked once, then moves on · needs a decision
The body question is asked one time. When the person says yes or describes their body, Mani acknowledges it and moves to asking where. Today the fixed question is added to every reply while the stage is still the check in, so "yes" gets the same question again.
**Done when:** in a replay of the panic chat, "yes" is followed by "where", never by the body question a second time, and a person who already named a place skips the "where" question.
- [ ] Design it (spec): `/architect somatic check asked once`

### 2. Where in the body, with buttons, then the exercise · needs a decision
After the check in, Mani asks where, with the four buttons (Chest, Head, Stomach, Somewhere else). "idk" or an unclear answer gets the buttons again, not a plain text guess. The matching exercise is always given before any Chat More or Go to Library choice appears.
**Done when:** the chat can never reach Chat More or Go to Library from the somatic stages without an exercise having been given, unless the person declines, skips for action, or mentions pain, trouble breathing or feeling faint.
- [ ] Design it (spec): `/architect somatic location and exercise`

## Slice 2: Client wording

### 3. Per style wording from the client · needs a decision
Chest, head, stomach and somewhere else exercises in the client's exact words for each style. Direct and Supportive add a line after the exercise (for example "Just notice"), and Reflective sets the steps one per line. Each ends with "How do you feel now?". Today there is one shared text for all three styles.
**Done when:** every style and place pairing matches the client's document word for word, and the evals check it.
- [ ] Design it (spec): `/architect somatic per style wording`

### 4. Returns in waves, then the library offer
After "calmer, then it comes back", Mani says it is common and comes in waves, that the same exercise helps, and offers the library. Buttons are "take me to the library" and "want to keep chatting" (shorter label "Library Tools" if too long). Choosing the library gets the client's handoff line.
**Done when:** that exact path works in all three styles, and the buttons appear only here and after the exercise, never earlier.
- [ ] Build it: `/develop somatic waves and library offer`

## Open questions for the client
- The client's example ends "How do you feel now?" and then goes straight to the "comes back" reply. What should happen when the person answers "better" or "still tense"? The current buttons "I tried it / Still tense / Feeling better" are not in the new flow.
- Panic conversation: the earlier framework asks about the body once already ("What are you noticing in your body right now compared with when we started?"). Does that count as the one body question, so the somatic check should go straight to "where"?

## Legend

**The decision box.** Every feature carries one sub task ending in `(spec)`. Skills find it by that suffix.
- **Next step** is the first unticked box.
- **needs a decision** means run `/architect` first. The tag drops once the spec is captured.
- **Status** goes `planned`, `in-progress`, `done`.
