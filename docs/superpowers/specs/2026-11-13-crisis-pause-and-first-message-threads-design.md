# Crisis pause, and threads that start with the first message

Date: 2026-11-13. Branch: `feat/crisis-handling` (cut from `main` at 34fd81d). Owner: muhammad.
Status: design, approved in conversation on 2026-11-13; this document is the written form.

Two pieces of work, built in this order. Part 1 is a prerequisite for Part 2, because "no new conversation during a
pause" is easiest to enforce once a conversation only exists when someone sends a message.

---

## Part 1: a thread exists only once the person has written to Mani

### Intent

Today a thread row and its greeting are written before the person does anything:

- on first page load, `POST /v1/threads/current` creates one when the account has none
  (`backend/mani/routers/threads.py:72-88`);
- on "New conversation", `POST /v1/threads` creates one (`threads.py:44`, `orchestrator.start_thread`
  `orchestrator.py:1683-1699`, `db/threads.create_or_reuse` `db/threads.py:178-216`);
- tapping a style button (Directive / Supportive / Reflective) is stored as a user message plus a fixed opener
  (`orchestrator._open_in_style`, `orchestrator.py:1535-1560`), so a tap alone makes the thread count as one the person
  spoke in (reuse rule, memory folding with a paid model call, the rate limit).

muhammad wants no thread in the database until the person sends their first real message to Mani. Choosing a style is
not a message.

### Goals

- Clicking "New conversation", loading the page, and tapping a style write nothing to the database.
- The first real message creates the thread and gets Mani's reply, as one request.
- The thread's rows after that first message are the same as today: greeting, the style tap and its opener when a style
  was chosen, then the first turn. Message counts, the cadence floors built on them (`context.OPENING_MESSAGES`,
  `their_messages`, `CHECK_FROM`, `TITLE_AFTER_MESSAGES`), rewind's "opening" guard and the tester's opening view keep
  working unchanged.
- The same contract serves the Expo app later (`mobile/` is a placeholder today and calls no API).

### Non-goals

- No change to what the greeting, the style buttons or the openers say.
- No clean-up of greeting-only threads already in a database; they are only hidden from lists (below).

### Approaches considered

| | How | Trade-off | Chosen |
|---|---|---|---|
| A | The client holds a draft. A read-only call returns the greeting, the style options and each style's opener. The first message is sent to "create thread" with the chosen style, and the backend writes the thread, greeting, style rows and the turn. | Rows identical to today, so counters and most tests hold. Needs one new read-only call and a changed create call. | **Yes** |
| B | The backend still writes the thread on click but marks it as a draft until a message arrives. | Still writes on click, which is what muhammad does not want. | No |
| C | Only the style is stored on the thread; greeting, tap and opener are no longer rows. | Cleaner transcript, but every message counter, the rewind guard, the tester's opening view and many tests shift. | No |

### The design

1. **Read-only opening.** A new `GET` (for example `/v1/threads/opening`) returns, without writing:
   the greeting text exactly as `greeting.greeting(nickname, returning)` would write it, the style options
   (`greeting.STYLE_OPTIONS`) and the opener for each style (`greeting.OPENERS`). "Returning" keeps today's rule
   (`_has_earlier_thread`). It also carries the user's pause status from Part 2, so a client can show the pause pop-up
   before the person types.
2. **Create on the first message.** `POST /v1/threads` changes to take the first message: its content, the client
   message id (idempotency, as the send route has today) and the chosen style, if any. In order, it:
   creates the thread; writes the greeting (`create_greeting`); when a style was chosen, writes the tap and its opener
   exactly as `_open_in_style` does and sets `threads.conversation_style`; then runs the person's message as an ordinary
   turn through the same path as `POST /v1/threads/{id}/messages` (`runner.send`). It returns the new thread id and the
   turn. A style typed past the buttons behaves as today (no style rows; `resolve_style` falls back).
3. **The model call stays outside the transaction** (as `chat/runner.py` already does). If the first turn fails after
   the thread was written, the thread must not be left behind as an empty draft visible to the person: either remove it
   in the failure path, or return its id so the client's retry sends to it. The builder picks one and tests it.
4. **Page load.** `POST /v1/threads/current` stops creating. It returns the most recent thread that has a message from
   the person, or nothing, in which case the client shows the draft opening. (A `GET` is the honest verb once it no
   longer writes; renaming is the builder's call, and the tester is the only caller, `chat-tester/client.py:230-239`.)
5. **Lists.** The thread list (`db/threads.list_for_user`), `most_recent` and the admin list show only threads with at
   least one message from the person, so greeting-only threads already in a database disappear from view.
6. **Reuse.** `create_or_reuse`'s rule (reuse the newest thread with no user message) has nothing left to reuse once
   threads are only created with a message; remove it rather than keep a dead path, keeping whatever idempotency the
   first message needs.
7. **Memory fold.** "New conversation" currently starts the memory fold of older threads with the new id as `keep`
   (`chat-tester/client.py:245-249`, `routers/threads.py:62-69`). It stays on the click, so the first reply of the new
   conversation still sees what the earlier ones taught (folding writes the person's memory, not a thread). With no new
   thread yet there is nothing to keep out of the fold; the route takes no thread id, or none. (My call: moving it to the
   first message would make that first reply miss the fold or wait for a paid call.)
8. **Chat-tester.** "New conversation" clears the open thread and shows the draft from the read-only call; a style tap
   is held in `st.session_state` and shown locally with its opener; the first message goes to the create call; the
   sidebar adds the thread once it exists.

### Left to the builder

The route names and shapes beyond what is stated, how the create call reuses the send path, and which of the two
failure behaviours in point 3 to use.

---

## Part 2: when danger continues, Mani pauses the chat for 15 minutes

### Intent and the why

muhammad, 2026-11-13: when a crisis is certain, Mani must stop rather than go round a loop of "please get help". The
person stays signed in. For 15 minutes they cannot chat, in that conversation or any other, and cannot start a new
one; they can use the Library. A pop-up with a close button says how long the pause has left and where to get help;
closing it leaves them on the Library. Each conversation stays separate: nothing from the paused conversation enters
another one. manasa's tests of
2026-11-11 ask the same (R87 on branch `feat/reply-gates-and-agents-map`: "opening a new conversation never bypasses
the crisis pause, and no wording suggests a new chat is an alternative to getting help").

### What happens today (audit, 2026-11-13)

- `threads.safety` is clear, unsure or danger, moved by the model's `SafetyRead` each turn (`chat/safety.py`,
  `orchestrator._judged`). `threads.crisis_detected` and an `admin.crisis_events` row are written on the first move into
  danger, or on an explicit phrase the same turn did not settle; nothing ever clears them.
- Production blocks only one thing: in danger, a reply the model marks `refused_help` makes every later message in that
  thread get `crisis.HELP_REFUSED_REPLY`. "New conversation" works at once.
- `CRISIS_BLOCKS_CHAT` (default off in `config.py:178`, on in muhammad's local `.env`) hard-locks any flagged thread
  with a 403, including threads flagged on a phrase the model judged only unsure. The API models default it to True
  (`models/api.py:22,110`), and `_help_refused` leaves it unset, so the tester showed manasa "paused, start a new
  conversation".
- The "danger" instruction never reaches the model (`context.py:279-288`). A turn's instruction is picked from the state
  before the model judges, so the first danger reply is written under the unsure instruction ("never tell them to call
  anyone while you do not know") or under the chat prompt. The turns after it are told "you already told them what would
  make them safe" whether or not it was said.
- History: until 2026-11-06 (PR #49) an explicit phrase locked the thread with a fixed reply; #49 turned locking off
  because it cut people off mid-conversation and fired on "I'm not going to hurt myself"; #52 (2026-11-12) added the
  refused-help block.

### Decisions muhammad made (2026-11-13)

1. **When it blocks.** Mani gives the help direction once. If the person's next message still shows danger and no
   protection is in place, the chat pauses. Not at the first danger message, and not only on an explicit refusal.
2. **Which danger.** Every kind: to themselves, to someone else, from someone, a symptom in the body. Raised with him:
   this can pause the chat of someone with chest pain who will not call, or someone hiding from an attacker who cannot call.
   He chose it knowing that.
3. **After the pause** (corrected by muhammad the same day: conversations stay separate, memory must not leak between
   them). The paused conversation keeps the reason it was paused. When they continue it, Mani first asks whether they
   are all right now and says that reason. A new conversation carries nothing from the paused one, but its first reply
   also asks whether they are all right right now, with no details. If they are, the chat carries on as usual. If not,
   it pauses again.
4. Pause length **15 minutes** (no 30-minute value existed in the code; the nearest is the 30-*day* "recent crisis"
   window, `db/threads.RECENT_CRISIS_DAYS`). **No sign-out** (muhammad, correcting the first draft). Library usable
   during the pause. A pop-up with a close button and 911, 988 and similar, for the chat-tester now and the mobile app
   later.

### Goals

- A pause is a property of the **user**, enforced by the **backend** on every route that can start or continue a
  conversation. No client can bypass it, including a client still holding a valid access token.
- The Library and everything that is not the chat keep working during a pause.
- The rule is one pure function with tests; the clients only render what the API tells them.
- The first danger reply always carries the help direction, because the pause depends on it having been given.

### Anti-goals

- A pause that fires when protection is already in place. muhammad's chest chat: after "my wife called the
  ambulance" the model still judged danger, because the tightness was still there. A rule of "still danger on the next
  message" would have paused his chat while he waited. This is the reason for the new judgment below.
- A pause the person can end by opening another conversation, reloading, or signing in on another device.
- Wording that suggests a new chat as an alternative to help (R87).

### Approaches considered

| | How | Trade-off | Chosen |
|---|---|---|---|
| 1 | A backend-only table of pauses: who, which thread, start, end, and whether the return check was answered. One backend check guards every chat route; the profile response says "paused until" and "return check due". | Keeps the history of pauses; mobile reuses the same API and draws only the pop-up. One table and one migration. | **Yes** |
| 2 | Two columns on `profiles`. | Simpler, but no history, and it puts safety state into the preferences row. | No |
| 3 | Supabase Auth `ban_duration`. | Blocks sign-in itself, so the Library would be unreachable (Supabase error `user_banned`). | No |

### The design

**The judgment.** `SafetyRead` gains one closed field, judged from the whole conversation as it stands, the same for
every kind of danger: `help_in_place` (boolean): help has been called or is on its way, someone is with them, the means
are away from them, or they have moved away from the danger. It replaces `refused_help`, which is removed with
`understanding.help_refused` and `crisis.HELP_REFUSED_REPLY`. A refusal is no longer a separate case: it is a message
where danger continues and nothing is in place.

**The rule** (one pure function, `chat/pause.pauses_now`, unit-tested on its own): the chat pauses on a turn when
- the state before the turn was danger (so Mani's previous reply was a danger reply), and
- the state after the turn is danger, and
- the read is `declined`: they refused the help, said again they will do it, or pushed the question away, and
- `help_in_place` is false (a second guard).

Changed 2026-11-13 by muhammad after the live replays: the rule without `declined` paused on a doubt ("could it be
stress?", 5 of 6 body chats) and while the wife was making the call (`help_in_place` read false on a short line).
`declined` is broadened to refusing help and restating the intent; a doubt, a question or a step under way is never
declined, nor pushback about a symptom in the body. A danger about the body pauses only when the turn's own read has the
symptom happening now and they refuse the help for it outright ("I'm not calling an ambulance"). `declined` keeps its role in an unsure concern, where a refusal
never settles it and never pauses. Nothing else pauses: not an unsure concern, not the first danger message, and not
the first message back after a pause (the return check below).

**The first danger reply.** Whatever instruction a turn is sent with, a reply that judges danger now says once,
plainly, what would make them safe (the content of today's dead "danger" instruction). The builder fixes where the
instruction is chosen (`context.build`, `orchestrator.py:972`, the chat prompt for a turn that starts clear) so the
first danger reply is told to give the direction, and `danger_said` is only claimed when the previous reply was a
danger reply. A test pins that the first danger turn's instruction asks for the direction.

**The pause record.** Migration `037`: a table in `public` (name is the builder's; for example `chat_pauses`) with
`id`, `user_id` (references `auth.users`, cascade on delete), `thread_id` (the thread it fired in, cascade on thread
delete), `started_at`, `ends_at`, `reason` (below) and `checked_at` (null until they have said they are all right in
any conversation). Indexed on
`user_id`. RLS on; the person may read their own rows; only the backend role writes, following the existing
backend-only state pattern (`034_backend_only_state.sql`, `.claude/SUPABASE.md`). A database test (`tests/sql/`) pins
the grants and RLS.

**The reason.** The model already writes one line on every safety judgment, `SafetyRead.why` ("what in the
conversation your judgment rests on"). The pausing turn's `why` is stored as the pause's `reason`, with no extra model
call. It is read only by turns of the same conversation; no other conversation, the memory fold or the profile ever sees
it. (Flagged threads are already left out of the memory fold, `db/memory.py:23`.)

**The length.** A setting, `CRISIS_PAUSE_MINUTES`, default 15.

**On the pausing turn**, in order:
1. The pause row is written in the same transaction as the turn.
2. The reply is a fixed pause message (`crisis.pause_reply`), not a model reply: that the conversation is paused for
   15 minutes, whom Mani worries for and the help that fits whose danger it is (2026-11-13: no suicide line for a
   body emergency), and nothing about starting a new conversation. Wording is ours until the client
   supplies hers; it goes on the to-tell-the-client list.
3. The turn's response carries the pause (`paused_until`), so the client shows the pop-up at once.
4. Nobody is signed out. The backend gate below is the whole lock, so it holds on every device and after a reload.

**The gate.** One FastAPI dependency checks the pause on every route that creates or continues a conversation: create
thread (Part 1), send, edit, follow-up. While a pause is running it refuses with a structured error the client
recognises by a code (for example `chat_paused`) and that carries `paused_until`. `ServiceError` has no payload today;
the builder extends it or adds a dedicated exception and handler. Reading threads, messages, the profile, the crisis
resources and the Library stay open.

**The status.** `GET /v1/profile` adds `chat_paused_until` (null when not paused). Part 1's read-only opening carries
the same.

**Help numbers.** `crisis.RESOURCES` (served at `GET /v1/crisis/resources`, empty today) gets the reference list
muhammad asked for, for the chat-tester now: 911 for immediate danger; 988 Suicide & Crisis Lifeline, call or text 988
or chat at 988lifeline.org; Crisis Text Line, text HOME to 741741 (US). Marked as reference numbers pending the client's
own list.

**The return check.** Each conversation keeps its own; nothing crosses between them but the fact that a pause ran.

- **In the paused conversation.** Its first message after the pause never pauses, whatever it says. Mani's reply asks
  whether they are all right now and says the stored reason ("earlier you told me ..., so I paused our chat"). It is the
  model's reply under a dedicated instruction, so it can also acknowledge what they wrote; it asks even when that
  message already sounds fine. That the check was asked is kept on the conversation (`threads.understanding`). Their
  answer is judged like any safety turn: settled (none) clears this conversation's safety and the chat carries on;
  danger they refuse help for or stay set on pauses again; unsure is not asked again and follows today's unsure rules.
- **In every other conversation, new or older** (2026-11-13, muhammad: one created before the pause asked nothing
  at first, which let a person bypass the check). It carries nothing from the paused one: no reason, no picture, no
  mention of it. Its first reply asks whether they are all right right now, with no details, under the same kind of
  instruction, and the answer is judged the same way. A settled answer records `checked_at` on the pause, after which
  the other conversations no longer ask. The paused conversation still asks its own question when they go back to it.
- **Only for a recent pause** (2026-11-13, the controller's ruling): a pause owes the check while it ended within
  `RECENT_CRISIS_DAYS` (30, the window `recent_crisis` uses); an older one owes nothing.
- From the answer on, the pause rule applies as in any danger conversation.

**The chat-tester.**
- When a turn's response carries `paused_until`, any route answers `chat_paused`, or the profile says the chat is
  paused (on sign-in or reload): show a pop-up (Streamlit `st.dialog`, which has a close button) with the help numbers
  from `GET /v1/crisis/resources` by kind and a countdown, ticking every second, with a bar of how much of the pause
  has run (from `paused_from` to `paused_until`). Closing it goes to the Library page.
- While paused, the chat page is closed: opening it shows the pop-up again, with no composer, no "New conversation" and
  no way into an earlier conversation. The Library works as usual. When the pause ends, the chat opens again.
- The current per-thread "paused after a crisis flag. Start a new conversation to continue." banner and its
  `crisis_blocks_chat` check (`chat-tester/app.py:109,215,313,405-406`) are removed.
- The pop-up and the gate logic live in one small module, so the same contract maps onto
  `mobile/src/app/chat.tsx` (which already opens a crisis drawer) later.

**Removed, completely** (no second path left beside the pause):
- the `CRISIS_BLOCKS_CHAT` setting and the lock at `orchestrator.py:861-866`, its API fields and defaults
  (`models/api.py`, `serializers.py`, `orchestrator.Turn`, `routers/messages.py`) and the edit roll-back that depends on
  it. muhammad's local `.env` line is then ignored (`extra="ignore"`); he can delete it;
- `refused_help`, `understanding.help_refused`, `_help_refused`, `crisis.HELP_REFUSED_REPLY`;
- the dead comments the audit found (`safety.py:13,59,106` "the screen locks", `Assessment.blocks_framework` with no
  caller).

**Also fixed in this work** (found by the audit, same area):
- The end check after a framework's last stage keys on `crisis_detected`, which a phrase judged only unsure also sets.
  It should fire only for a thread where danger was reached.
- `recent_crisis` measures its 30 days from the flagged thread's last message, not from the crisis
  (`db/threads.py:276-281`). It should measure from the crisis event.

### Records

- `backend/PORT-STATUS.md`, Decisions in force, edited in place: "nothing locks" (2026-11-06) and "help refused is
  the only block" (2026-11-11) become the pause; `CRISIS_BLOCKS_CHAT` removed; the end check; the threads entry for
  Part 1.
- `docs/client/requirements.md`, to-tell-the-client: the pause, its 15 minutes, the return check, the help numbers and
  the fixed pause text (all our wording).
- Journal note for what the audit found.

### Verification

- Unit tests for the rule (every combination of before, after, `declined`, `help_in_place`, whose danger, and for the
  body the read's danger and `symptom_now`), the instruction a first danger turn gets, and the pause gate.
- Integration tests (throwaway database): a pause is written and the reply is the pause text; every chat route refuses
  during a pause, including create-thread; the Library and profile still answer; the profile reports the pause and the
  reason is stored with the paused conversation; after the pause, the paused conversation's first message gets the check
  with its reason and never pauses, even when it reads as danger; every other conversation's first reply, new or older,
  asks with no details, and its prompt contains nothing from the paused one; a settled answer in any conversation stops
  the other ones asking but not the paused one; a pause that ended more than 30 days ago asks nothing; danger again
  pauses again only with a refusal or the intent said again; an unsure answer is not asked again; pushing the question
  away while in danger pauses; a doubt never pauses; a chest chat with help on its way never pauses, and one that refuses
  the ambulance for a symptom happening now pauses with the body text; nobody is signed out.
- Live replays on muhammad's key, twice each: manasa's refusal test (Topic 3), muhammad's chest chat with his wife, the
  ten unseen chats of 2026-11-11. Expected: a pause only where danger continued and they refused or stayed set on it
  with nothing in place; none in the
  chest chat after the ambulance was called; no false pause in the control chats.
- The chat-tester suite, with the pop-up, its close button and the Library left open.

### Left to the builder

The table and route names, how the error carries `paused_until`, where the dependency lives, the exact pause text
(within the rules above), and how the chat-tester's pop-up is laid out.
