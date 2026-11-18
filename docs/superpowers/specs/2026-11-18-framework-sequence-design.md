# The framework runs the way the client's sequence document shows

Branch: `feat/one-call-turn` (muhammad tests on the branch, then opens the PR and merges himself).
Source: the client's "Framework Sequences - Example Conversations", recorded in
`docs/client/messages/2026-11-18-framework-sequences.md`. Scope and choices: muhammad, 2026-11-18.

## Intent

The client wrote down how a framework is meant to run, three times over for one scenario, once per style: a lead-in
that questions the belief, the five steps shown as a list, a choice to start, one letter per reply, a check on how they
feel, then the close. Today Mani offers in its own words with Try it / Tell me more / Keep chatting, may answer two
letters in one reply when the chat already covered one, and closes straight after E. muhammad's latest Directive chat
showed the rest: A and B in one reply, long replies, and stock phrases ("I want to highlight something" three times).

## Goals

1. The offer follows the document: a lead-in, the five steps, then a choice to start, see an example, or talk more.
2. Every letter is its own reply, with its line ("A is for Activating Event.") and its question, even when the chat
   already touched it.
3. After E, Mani asks how they feel now, with Stronger / More focused / Still a bit tired; then the closing buttons
   Keep Chatting / Go to Library / Finish for Now.
4. Directive is short: short replies everywhere, and a short acknowledgment on each stage. Supportive and Reflective
   keep their current length and warmth.
5. Suggestion buttons in all three styles: when Mani's question has a few natural answers, it offers them as buttons,
   like "Work / Family / Everything at once".

## Non-goals

- The chat before the set: unchanged in voice and pace (muhammad). The document's chat lines ("these thoughts are
  beliefs, not facts" on the first message) are not adopted.
- The greeting: unchanged, it still asks for the style. The document's greeting skips that question.
- The document's closing buttons (Save chat / Finish chat / Practice another one): not adopted; ours stay (muhammad).

## Anti-goals

- A questionnaire: code never writes a stage's text; the model writes every stage, the acknowledgment and the question.
- Suggestion buttons on a safety turn, or beside code's own buttons.
- The feelings check standing in for the safety question after a framework: when the conversation reached danger,
  that question still comes first.

## Constraints

- One model call per turn; fixed client pieces are sent by code with no model call, as Tell me more is today.
- A prompt change passes the side-by-side gate: the two prompts run one after the other (OpenRouter's in-flight
  budget refused two at once on 2026-11-18), every rule passing, and `evals/check_suite.py` exits 0. **Judged by
  style** (muhammad, 2026-11-18): the 0.15 mark applies to the Supportive and Reflective quality cases; the Directive
  cases are judged for quality with length set aside, since short is now the aim and their references run 150 to 190
  words. New rule cases check the sequence, and both prompts run them: the lead-in does not name the set and ends on a
  question about testing the belief; a stage reply asks about one stage only; E answered sets `action: finish`; the
  reply after the feelings check asks nothing; suggestions come with a question that has a few natural answers and
  never on a safety turn.
- CLAUDE.md: tests first, no orphans (the replaced labels and helpers are deleted), decisions edited in place.

## Approaches

- **Chosen: code sends the client's fixed pieces, the model writes the rest.** The lead-in, every stage and the reply
  around the feelings check are the model's; the button rows, the five-step text and the example are code's. It is
  how Tell me more and the closing buttons already work.
- Rejected: the model writes every step. The client's step list and button labels would change from run to run.
- Rejected: code runs the stages as a script. That is the stage walk deleted on 2026-11-17, the questionnaire feel
  muhammad named.

## The design

### The offer (three steps)

1. **Lead-in.** When the model offers (`action: offer`, `framework`), its text is the lead-in in the person's style:
   what they just said, that a belief can feel true without being a fact, and a question about how they could test it.
   It does not name the set. Code adds **Not sure / Show me how / Give me a tool** and records the offer (`offered`,
   phase `offering`), as today.
2. **The steps.** A tap on any of the three sends, with no model call, the framework's step text for their style:
   the intro sentence, the five steps as a list, and the ready question, word for word from the document for ABCDE
   (Directive: "The ABCDE technique can really help. It breaks down thoughts into five steps:" ... "Ready to dive into
   a real life situation?"; Reflective and Supportive as in the document; the openers that answer Not sure, "No
   worries" and "It's okay to be unsure", are dropped because only Not sure earns them, and a typed reply or another
   button can lead here too). Buttons: **Start ABCDE / I need an example / Talk more first**. The label is
   `Start <framework name>`.
3. **The example.** I need an example sends, with no model call, the framework's worked example, then **Start ABCDE /
   Talk more first**. ABCDE's example is the document's own deadline-and-sick-child answers, A to E, in a few lines;
   Thought Reframe's is ours. Both are marked ours until the client supplies hers.

Start starts the set (as Try it does). **Talk more first lets the offer lapse, for now only**: Mani may offer the set
again later in the conversation when it fits; it is not declined (muhammad, 2026-11-18).

**A typed reply to the lead-in** (muhammad, 2026-11-18): the model replies to what they typed, and code adds the step
text and its three buttons underneath, as a paragraph of its own; the offer stays open, now at the steps. Only a clear
no declines the set: the model reports it as `action: stop` while the offer is open. A typed reply after the steps or
the example goes to the model as today: a clear yes starts the set, anything else lets the offer lapse. The offer row
keeps which step it is on (the lead-in, or the steps shown), so code knows which applies.

### Inside the set

- Every stage is its own reply: its line, then its question. A stage the chat already touched gets its line, what Mani
  understood in a sentence, and its question to confirm or complete it. The starting turn opens the first stage only
  (code today lets it reach the second; that is removed, with the Try it fact that says so).
- Directive opens each stage with one short acknowledgment ("That is a clear activating event."); Supportive and
  Reflective keep their current warmth.

### The end of E

E ends on the new belief in their own words, as the document does (muhammad, 2026-11-18). The "one clear thing they'll
do" that E asks for today goes: from `ready_when`, `purpose` and `if_unclear` of ABCDE's `effective` and Thought
Reframe's `replacement`, and from `mani.md` ("Don't finish until ... what they want to do with it"). After a finished
set, what was understood stands; if they ask what to do, Mani helps in practical terms, as today.

### The feelings check

- When E is answered, the model sets `action: finish` as today. Code no longer finishes on that turn: the framework row
  moves to a check-in phase, and code adds **Stronger / More focused / Still a bit tired**. The model's reply
  acknowledges the new belief and asks how they feel now.
- The next turn, tapped or typed, finishes the set: the model replies briefly with no question (Directive in a sentence
  or two), and code adds Keep Chatting / Go to Library / Finish for Now, as today's finish does.
- When the conversation reached danger, the safety question after the framework comes first, as today; its settled
  answer leads to the feelings check instead of straight to the close.
- A turn held for safety while the check is open moves nothing, as everywhere else.

### Suggestion buttons

- The reply gains a field for up to three short suggested answers, in the person's own terms, filled only when the
  question has a few natural answers. Code shows them as buttons when the reply has no buttons of code's own, no set
  is running, no offer is open, and the turn is not held or guarded for safety.
- A tapped suggestion is their answer, read like typed text.

### The prompt (`mani.md`)

- Offering: the lead-in replaces the offer sentence; examples per style from the document.
- Inside the set: one stage per reply always; Directive's short acknowledgment; the finish asks how they feel; the
  turn after it closes with no question.
- Your style: Directive replies are short, in the chat as well as the set (three or four short sentences at most).
- Suggestions: when to fill them and when to leave them empty.
- How you sound: a stock phrase is never used twice in a conversation ("I want to highlight something", "There is a
  distinction worth exploring").

### Content and records

- Framework files: each framework's offering gains the step text per style and one worked example; seeding refuses
  an active framework without them. The client's Tell me more text for ABCDE is replaced by the document's step text.
- The labels Try it, Tell me more and Keep chatting, the permission question and the code that used them are removed.
- `docs/client/requirements.md`: R107 to R113 from the document. R107 the lead-in that questions the belief, with
  Not sure / Show me how / Give me a tool; R108 the five steps in the person's style, then Start / I need an example /
  Talk more first; R109 a worked example on request; R110 every letter its own reply, asked even when the chat touched
  it; R111 E ends on the new belief, then how they feel now, with Stronger / More focused / Still a bit tired; R112
  suggested answers as buttons; R113 Directive's short acknowledgment on each stage and short replies. Conflict rows: the document's offer replaces
  the earlier Try it / Tell me more / Keep chatting (client, 2026-10-08) and Tell me more's explanation; its closing
  buttons and its greeting are not adopted (muhammad, 2026-11-18).
- `backend/PORT-STATUS.md` Decisions in force: the offer, buttons, stage and finish entries edited in place; the
  journal notes that argued for them get the superseded line.

## Verification

- Unit: the offer buttons; a lead-in tap, an example tap, Start and Talk more first; the starting turn held to the
  first stage; finish on the last stage moving to the check-in and the next turn closing; the end check before the
  check-in; suggestions shown only where allowed.
- Integration, scripted model: the whole sequence in one conversation, offer to close, with the step text word for
  word for each style, and a typed yes at the steps starting the set.
- The gate and the suite, as in Constraints. The suite's checks move to the new labels.

## Left to the builder

The names of the new phase, labels, fields and helpers; where the step texts live in the framework files; the exact
facts lines; Thought Reframe's step text (from its current explanation plus the ready question) and its example.
