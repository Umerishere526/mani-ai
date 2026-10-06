# 0005. A framework is chosen from facts the model states

**Date**: 2026-10-05
**Status**: In Progress

## Summary

Mani chooses which framework (a set of guided questions, such as ABCDE or DBT STOP) to offer by matching the person's words against hand written phrase lists. Anything said another way matches nothing, and at the fourth message Mani must offer something anyway, so it guesses. Two chats on 5 October 2026 show it: stress about work, parents and society got Structured Problem Solving before anything specific was said, and "I might have a panic attack" got ACT. With this change the model writes a short checklist each turn of what the person has actually told it (an event, what they took it to mean, one painful thought, panic right now, and so on), quoting their own words. Code then applies the client's selection table to that checklist. When the checklist points to a framework the model did not offer, the model is asked once more. Mani offers only a framework the checklist fully fits; until then it keeps talking and asks about what is missing. There is no "closest fit" offer any more: the first real runs showed that a forced nearest offer at the fourth message made the model read general stress as a fact. The phrase lists go, except the two deterministic rules (an action about to happen, and words that rule a framework out). DBT STOP gains a version for panic, as the client's overview describes.

## Requirements

**User stories**:
- As a person who says something no phrase list predicted, I want Mani to understand what I described and offer the framework that fits it, so that I am not handed the wrong one.
- As a person who has not yet said anything specific, I want Mani to ask about what happened or what I am telling myself, so that I am not offered a plan for a problem I never named.
- As a person close to panic, I want Mani to offer to pause with me (DBT STOP), so that I get help in the moment rather than reflective questions.
- As muhammad, I want the choice to be checkable from a list of facts without a model call, so that routing rules can be tested for free.

**Vocabulary.** A **fact** is one of the ten ids in the table below, reported by the model with the person's own words. A framework **fits** when every fact in one of its `fits_when` sets is present. A framework **points somewhere** when at least one fact from any of its sets is present. The **pick** is the fitting framework the tie rules put first. The **leading** framework is, when nothing fits, the one that points somewhere with the most facts present. It is never offered; it is read only by reason 5's redraft text (AC-7) and the log line, so it reaches the model only when a wrong offer is redrafted, and the prompt does the everyday steering. A framework is **allowed now** when it is not vetoed (`router.vetoes`), `context.cooldown_passed` is true, `context.earliest_offer_ok` is true for it, and the reply is not the one that takes a no; nothing else (a pain hold, a safety concern) gates an offer in the redraft or in repairs. A **fact turn** is a turn with no framework running, no button tapped, no offer accepted on this turn, and no `safety: concern`; facts are read only on fact turns.

| Fact id | Plain meaning (also what the model is told) | Belongs to |
|---|---|---|
| `event` | a specific thing happened (something someone said or did, a moment, a result) | ABCDE |
| `meaning` | what they took that event to mean about themselves or someone else | ABCDE |
| `painful_thought` | one specific painful thought, in their words ("nobody cares about me") | Thought Reframe |
| `low_mood` | low mood, and they have stopped doing things that matter or pulled away from people | Behavioral Activation |
| `cannot_begin` | they know what they could do but cannot get themselves to begin | Behavioral Activation |
| `practical_problem` | a specific practical problem that a decision or an action could change (not a general pressure) | Structured Problem Solving |
| `unsure_what_to_do` | they do not know what to do about a situation, or have a decision to make. A bare "I don't know" in answer to Mani's question is not this | Structured Problem Solving |
| `cannot_control` | a specific thing they said they cannot change or control (a loss, someone else's choice, an outcome still uncertain), and it keeps pulling at them. Pressure from work, family or life in general is not this | ACT Choice Point |
| `overwhelmed_now` | right now, in this moment, they are panicked, flooded or too activated to think. Stress about work or life in general is not this | DBT STOP |
| `about_to_act` | they are about to do something they may regret: send, post, call, confront, quit | DBT STOP |

**Acceptance criteria**:

- **AC-1** (the checklist in the reply): `Reply` in `mani/llm/schema.py` gains `facts: list[Fact] | None`, declared after `reasoning` and before `style` and `text`, where `Fact` has `fact: str` and `words: str`. Its description lists the ten ids with their plain meanings from one table in `router.py`, the same table the redraft and the prompt use, and says to leave it null while a framework is running. A `mode="before"` validator drops any entry that is not an object with two strings, so a malformed checklist never fails the turn (the pattern of `_decline_written_as_a_word`). `heading_toward` and `offer_fit` are removed from `Reply`. Unit tests: field order (`facts` before `text`), neither removed field exists, and a malformed entry is dropped while the rest of the reply parses.
- **AC-2** (only facts in their words count): on a fact turn a fact is kept only when its id is one of the ten, its `words` hold at least two words, and those words, after `safety.normalize`, occur as whole words within one of the person's own messages in this conversation (never Mani's, never across two messages). `overwhelmed_now` and `about_to_act` count only when the words are in one of the person's two most recent messages. Anything else is dropped and noted in the repair notes (`dropped a fact not in their words: <id>`, `dropped an unknown fact: <id>`). A quote the model corrected (a fixed typo) is dropped; that is an accepted miss. A null or empty `facts` counts as no facts. On any other turn facts are ignored. Unit tests cover: a quote found, a quote only in Mani's text, a quote spanning two messages, a one word quote, an unknown id, `facts: null`, and an `overwhelmed_now` quote from the person's third most recent message.
- **AC-3** (fit sets are content): each framework file carries `activation.fits_when`, a list of fact sets: ABCDE `[[event, meaning]]`, Thought Reframe `[[painful_thought]]`, Behavioral Activation `[[cannot_begin], [low_mood]]`, Structured Problem Solving `[[practical_problem, unsure_what_to_do]]`, ACT Choice Point `[[cannot_control]]`, DBT STOP `[[about_to_act], [overwhelmed_now]]`. `test_framework_content.py` asserts every framework has `fits_when` and uses only the ten ids.
- **AC-4** (the tie rules, in code, in order): fitting frameworks are first ordered by `display_order`. Then these rules apply in this order. A rule only reorders frameworks that already fit, never adds one. A rule whose `over` list holds a framework an earlier rule already settled is skipped (today's `settled` behaviour).
  1. `about_to_act` present: DBT STOP first, over everything. (Client: overview selection table and DBT STOP's purpose.)
  2. `overwhelmed_now` present: DBT STOP over Behavioral Activation, ACT Choice Point, ABCDE and Thought Reframe, but not over Structured Problem Solving. (Client overview: STOP comes before reflection when the person is too activated to reason. Not over Structured Problem Solving is ours, from ADR 010's lost wallet chat, where the overview says "before problem solving"; it goes on the sign off list.)
  3. `cannot_begin` present: Behavioral Activation over Structured Problem Solving and ACT Choice Point. (Client: overview distinction, and ACT's own "not when they know what to do but cannot begin".)
  4. `cannot_control` present: ACT Choice Point over Structured Problem Solving, ABCDE and Thought Reframe. (Client: overview distinction, and the "cannot be controlled" not when lines of ABCDE and Structured Problem Solving.)
  5. `unsure_what_to_do` present: Structured Problem Solving over Behavioral Activation, ABCDE and Thought Reframe. (Client: overview distinction, and the "practical plan" not when lines of ABCDE and Thought Reframe.)
  6. `event` present: ABCDE over Thought Reframe. (Client: overview distinction; muhammad chose ABCDE when an event is named.)

  Unit tests from fake fact lists, no model: one per rule; `cannot_begin` with `unsure_what_to_do` and `practical_problem` (Behavioral Activation); `low_mood` with `unsure_what_to_do` and `practical_problem` (Structured Problem Solving); `event`, `meaning` with `painful_thought` (ABCDE); `event` with `painful_thought` and no `meaning` (Thought Reframe, the rule does not promote ABCDE, which does not fit); the lost wallet facts `overwhelmed_now`, `practical_problem`, `unsure_what_to_do` (Structured Problem Solving).
- **AC-5** (leading, missing fact, exclusions): when no framework fits, the leading framework is the one with the most of its facts present; ties go through the same rules, then `display_order`. With no fact present there is no leading framework. A framework's **missing fact** is the first fact, in set order, of its set with the most facts present that is not yet present. Before the pick and the leading framework are chosen, two kinds of framework are removed: one whose `never_offer_when_said` phrase the person used (`router.vetoes`), and one they have finished in this thread (repairs already refuses it). A declined framework is not removed: `cooldown_passed` covers the whole thread, so no framework at all may be offered while a decline cools down, and after it the declined one may come back if it still fits (muhammad, 2026-09-24). Unit tests: `event` alone leads to ABCDE with `meaning` missing; no facts leads to none; an excluded framework is never picked.
- **AC-6** (urgency stays deterministic): `router.urgent` (the imminent action phrases, its one absolute rule) still lets DBT STOP skip the message wait, and when it fires `[ctx]` still carries DBT STOP's `offering` lines for the action branch, the one case where offer guidance is sent before the call. `test_an_imminent_action_reaches_the_offer_on_the_first_message` changes to assert the `offer_*` lines without `framework_shortlist`.
- **AC-7** (one ordered chain of offer reasons): `redraft.reasons` keeps its feeling and size reasons, and its offer reasons become one ordered chain. The first that applies is the one sent. The pick and the leading framework are computed from the **first** draft and kept for the redraft and its check.
  1. The draft shows again the offer that is already waiting (`deferred`, same framework): no fit check.
  2. The draft offers a framework that is not allowed now (vocabulary): today's "offer nothing" reason, or the veto reason when its words rule it out. This is checked before reasons 3 and 5, whether or not a pick exists, so an offer during a cooldown is never told to ask what is happening.
  3. The draft offers, a pick exists, and the pick is not what it offered: `the facts you listed point to <pick name>: offer that instead`. This applies only when the pick itself is allowed now; otherwise it is reason 2's text.
  4. (Removed by AC-16: the nearest is never offered.)
  5. The draft offers and no pick exists: `nothing they have said fits a set of questions yet: offer nothing, and ask about <missing fact of the leading framework, in plain words>` (with no leading framework, `ask what is happening for them`).
  6. The draft does not offer, it is the person's fourth message or later with nothing offered yet (today's `closest_fit_due`, renamed `offer_due` by AC-16), no pain is mentioned, and a pick exists and is allowed now: `you have talked for several replies and not offered: offer <pick name>`. A leading framework alone never triggers it.

  Reasons 3 and 6 carry that framework's `offering` purpose, boundaries and style `ask`. For DBT STOP the `panic` branch's (AC-11) is used when `overwhelmed_now` is present without `about_to_act`, and the action branch's otherwise. This is the one redraft ADR 006 allows. Unit tests in `test_redraft.py` cover each of the six, including the manager chat at message 2 (reason 2, not 3, because ABCDE waits for message 3).
- **AC-8** (still wrong after the redraft): if the second draft still breaks the chain (reasons 2, 3 or 5 would apply to it, judged against the pick from the first draft), the offer, its buttons and its words are removed through the existing `cooldown_passed=False` path in `repairs.apply`, and the reply is kept as a reply. The waiting offer of reason 1 is never removed this way. An integration test with a scripted model that offers the wrong framework twice asserts no technique is stored and no offer button is sent.
- **AC-9** (an offer is the pick or nothing): replaced by AC-16. An offer stands only when the offered framework is the pick and it is allowed now; `repairs.apply` receives `cooldown_passed` from that, and every other offer is removed after the redraft (AC-8).
- **AC-10** (prompt and steering): every prompt text that names `heading_toward`, `offer_fit` or `framework_shortlist`, or tells the model to offer when `closest_fit` is `due`, is rewritten. That covers `mani_base.md` "Understanding, then offering" (lines 61 to 68), `response_format.md`'s `closest_fit` and `framework_shortlist`/`offer_*` descriptions and step 3 of "The reasoning field", and the reason texts in `redraft.py`. The new wording says:
  - Fill `facts` first, quoting their words.
  - Offer only a set your facts fully fit; one they only point to is never offered (AC-16).
  - When nothing fits yet, the question goes after the missing fact of the framework with the most facts, in the person's own terms, never naming the fact or the framework.
  - With no fact at all, ask what is happening for them.

  The Framework Index lists each framework's facts in plain words alongside its use. A composer test asserts every framework's fact meanings appear in the Framework Index, and a test asserts no prompt file mentions `heading_toward`, `offer_fit` or `framework_shortlist`.
- **AC-11** (panic is DBT STOP): `dbt_stop.md`'s `central_indication` uses the client's overview wording ("emotionally overwhelmed, highly reactive, panicked, or close to acting impulsively"). Its `offering`, `stop`, `pause`, `observe`, `proceed` and `closing` stages each gain a `panic` key for a person who is overwhelmed with no action named. The key holds `purpose` and an `ask` per style, and `offering`'s also holds its boundaries. Its words never mention an action, a message, sending, posting or calling. The panic `offering` boundary says it must not be offered before Mani has asked what is happening for them. The existing "must not offer before the specific action is named" boundary applies to the action branch only. All protective contraindications (safety protocol first, never delay leaving danger or getting help, medical emergency) apply to both. While STOP runs, `[ctx]` sends both branches labelled ("when they are about to act" and "when they are panicked with no action named"), and the model follows the one that matches. `panic` is not an `if_unclear` branch, so it never counts as a redirect or holds a stage. `test_framework_content.py` asserts each of those six stages has a `panic` key with all three style asks and no action words, and its pinned counts are updated. The new wording goes on the client sign off list (scope row 29).
- **AC-12** (phrase scoring is gone): removed are `router.shortlist`, `router.is_confident`, `_score_one`, `_promote`, the non absolute `DISCRIMINATORS`, `ROUTER_MIN_EXCHANGES`, the `[ctx]` line `framework_shortlist`, and the router candidate's `offer_*` lines (except AC-6). `strong_signals`, `signals` and `redirects` are removed from the six framework files. `router.urgent` and `router.vetoes` stay. The orchestrator's `heading toward` log line becomes one line with fact ids, the pick and the leading framework, ids only, never `words`.
- **AC-13** (what does not change, and the tests that do): the safety screen, a safety concern blocking offers, the pain hold, each file's `earliest_offer_message`, `CLEAR_OFFER_AFTER`, the number 4 in `CLOSEST_FIT_AFTER` (renamed `OFFER_DUE_AFTER` by AC-16, and it now asks only for a pick, never a nearest offer), the clear offer cooldowns, contraindications, and every running framework turn behave as today, and their tests stay green. These tests assert removed behaviour and are rewritten to the new rules, not deleted without replacement:
  - in `test_turn.py`: the closest fit test at line 273 (now driven by facts), and the tests near lines 1034 and 1088 (AC-6);
  - in `test_chat_context.py`: the shortlist and candidate tests near lines 241 and 489;
  - in `test_redraft.py`: the closest fit test near line 51;
  - `test_router.py`'s scoring tests, which give way to the fit and rule tests of AC-4 and AC-5.

  The whole `pytest` runs, and the integration count is checked not to be all skipped.
- **AC-14** (the reported chats, scripted): integration tests in `test_turn.py` replay three chats with a scripted model that returns facts.
  - **Chat 1** ("i feel emotionally stressed", "work pressure, parents pressure, society pressure", "yes", "i suggest at all of them", no facts): at the fourth message there is no reason 6 redraft, and no offer is stored.
  - **Chat 2** ("I feel like I might have a panic attack.", then "yea i see my laptop in front of me", with `overwhelmed_now` quoting "might have a panic attack"): at the second message a draft offering ACT is redrafted to DBT STOP with the `panic` offering ask.
  - **The manager chat** ("I'm very upset. My manager embarrassed me today because he wants me to fail.", "EVERYTHING WENT WRONG", "I felt really embarrassed.", with `event` "my manager embarrassed me today" and `meaning` "he wants me to fail"): at the third message a draft offering Structured Problem Solving is redrafted to ABCDE.
- **AC-15** (one small real check, asked first): the three chats and their Supportive style turns are added as scenarios to `scripts/eval_conversations.yaml`. After the build, and only once muhammad says yes at that moment, `scripts/eval_replies.py` runs them and `grief_dog_steering` once each. Expected:
  - chat 1 asks about what happened or a thought and makes no offer by its fourth message;
  - chat 2 offers DBT STOP;
  - the manager chat offers ABCDE;
  - the grief chat reaches an offer (ACT Choice Point as the pick, or the nearest), with Behavioral Activation never offered.

  The transcripts and counts are recorded in a journal note whatever the outcome. Measured 2026-10-05 (journal `framework-fit-from-facts-first-runs-2026-10-05`): chat 2, the manager chat and grief as expected; chat 1 offered at message 4 in 2 of 3 runs, once ACT as a full fit (general pressure marked `cannot_control`) and once Structured Problem Solving as the nearest. AC-16 and AC-17 follow from it.
- **AC-16** (full fits only, added 2026-10-05): Mani offers only the pick, a framework the facts fully fit; the leading framework only steers the question and is never offered. In code:
  - `redraft.offer_kind` is replaced by a true or false check, `offers_the_pick(technique, fit)`: true when `fit` is None (a turn whose facts are not read) or the offered framework is the pick. The `cooldown_passed=` expression passed to `repairs.apply` becomes: it offers the pick, the pick is allowed now, and it is not ruled out.
  - Removed: AC-7's reason 4; `context.closest_fit_ok`; the `[ctx]` line `closest_fit`; `repairs.CLOSEST_FIT_LABEL` ("Try the closest fit") and the `closest_fit` parameter of `repairs.apply`; `context.cooldown_for` and `COOLDOWN_AFTER_DECLINE`, which only the closest fit reads in code; the declined exclusion in `orchestrator._not_offerable_now` (AC-5); the closest fit marker in `scripts/eval_replies.py`. Removing `COOLDOWN_AFTER_DECLINE` is a decision, not tidying: muhammad's 2026-09-24 rule of three replies after Keep chatting has applied only to the closest fit since ADR 007 gave clear offers `CLEAR_COOLDOWN_AFTER_DECLINE`, which stays.
  - Renamed to say what they do now: `closest_fit_due` becomes `offer_due` and `CLOSEST_FIT_AFTER` becomes `OFFER_DUE_AFTER` (still 4). `offer_due` never goes into `[ctx]`: reason 6 runs in code on the first draft's facts. It is false whenever `ctx.technique` is set, so reason 6 never fires after a decline or a finished framework.
  - The prompt and generated text drop every "nearest" and every "an offer is due" push: in `mani_base.md` "Understanding, then offering"; in `response_format.md` the `closest_fit` line in the block listing and its description, "Is an offer due?" in step 3 of the reasoning field, and "a confident offer" in the `cooldown_passed` description; in `composer.py` the "What makes each fit" intro ("point to it" becomes "pointing to a set is never an offer; ask about what is missing") and the "Finding the fit" intro ("heading toward"). The model is told to offer only a set its facts fully fit. `mani_base.md` keeps its 120 line cap and the exact phrase "Never offer under `safety: concern`" that the hard rules test reads.
  - After Keep chatting, a framework may come back only as a clear offer, after the clear cooldown, as today.

  Tests rewritten, not deleted without replacement:
  - `test_turn.py`: `test_the_closest_fit_is_owed_by_the_fourth_message_and_says_so` becomes "an event alone is never offered" (a draft offering ABCDE on `event` alone at the fourth message is redrafted to ask about `meaning`, and a second such draft is removed); chat 1's test asserts no `closest_fit` line instead of `closest_fit: due`; the test near line 1158 uses `CLEAR_COOLDOWN_AFTER_DECLINE`.
  - `test_redraft.py`: the reason 4 tests and the leading half of the reason 6 tests go, the `closest_ok` argument goes, a test asserts reason 6 never names a leading framework, a test asserts an offer with no pick during a cooldown gets reason 2's text, and the pain test moves to `ABCDE_FITS` so it tests the hold; `offer_kind` tests become `offers_the_pick` tests.
  - `test_chat_context.py`: the tests near lines 99, 692 and 711 to 734 that read `COOLDOWN_AFTER_DECLINE`, `closest_fit_ok` or `closest_fit_due` move to `CLEAR_COOLDOWN_AFTER_DECLINE` and `offer_due`.
  - `test_repairs.py` near line 639 (`CLOSEST_FIT_LABEL`) goes.
  - `test_framework_fit.py`: the declined exclusion test becomes the finished exclusion.
  - `test_composer.py` asserts no prompt file, and no generated Framework Index text, mentions `closest_fit`, "closest fit", "nearest" or "an offer is due". The whole `pytest` runs.
- **AC-17** (the re-check, asked first): after AC-16 is built, and only once muhammad says yes at that moment, `scripts/eval_replies.py --style supportive` runs `stress_nothing_named_yet` three times and `grief_dog_steering` and `deadlines_steering` once each. Expected: the stress chat makes no offer by its fourth message in each of the three runs; grief reaches an offer and never Behavioral Activation; deadlines reaches Structured Problem Solving. Recorded in the journal whatever the outcome. The stress chat may still fail: in the first measurement it got ACT at message 3, before any `due` line existed, so removing the push may not stop the model marking general pressure as a fact. The runs must say which: `scripts/eval_replies.py --verbose` prints, per reply, the kept fact ids, the pick and leading framework, and any redraft reason (ids and reason text only, never the person's words). A stress offer from a fact the model marked goes back to muhammad as that problem; one from a reason 6 redraft is a fault in this build. Three runs means three separate invocations.

## Decision

**Chosen option**: Option 1: the model states the facts, code applies the client's table.

Each reply carries a checklist of what the person has said, quoted in their words and checked against them. Code picks the framework from it with the client's tie rules, asks the model once more when its offer disagrees, and removes the offer if it still does. Only a framework the facts fully fit is ever offered; there is no nearest offer (AC-16, an update after the first real runs). Phrase scoring is removed; the imminent action check and the never offer vetoes stay. Reasoning and the options weighed: [rationale.md](rationale.md).

**Implementation skills**: none (backend Python and content; no community skill governs this layer).

### What changes, what stays

| Part | Today | After |
|---|---|---|
| Who reads meaning | phrase lists, then the model chooses freely | the model states facts; code chooses |
| `Reply` | `heading_toward`, `offer_fit` | `facts` (ids with their words) |
| `router.py` | scoring, shortlist, confidence, six rules on phrases | fit, pick and leading from facts, six tie rules on facts, `urgent`, `vetoes` |
| Framework files | `strong_signals`, `signals`, `redirects` | `fits_when`; DBT STOP widened with a `panic` key per stage |
| `[ctx]` | `framework_shortlist`, candidate `offer_*` lines | neither, except STOP's offer lines when `urgent` fires |
| Closest fit at message four | always owed | gone: only a full fit is offered; from message four a pick not yet offered is asked for (AC-16) |
| A wrong offer | stands | asked again once, then removed |

## Feature design

**Data model sketch**: no database change. `admin.frameworks.activation` (jsonb, already seeded from the framework files) gains `fits_when` and loses `strong_signals`, `signals` and `redirects`. The DBT STOP stages gain `panic` keys. `scripts/seed.py` carries both as it carries the rest. The checklist is never stored: it is read from the reply, used in the turn, and logged as ids only. `admin.llm_calls` keeps tokens and timing, not reply content, and because a malformed fact is dropped by a validator instead of failing validation, no validation error text carrying quoted words reaches `error_message`.

**Interface surface**: no HTTP route changes. The changed interface is the model's reply shape and the hidden context block.

| Surface | Change |
|---|---|
| `Reply.facts` | new, `list[Fact]`, optional, before `text`, malformed entries dropped |
| `Reply.heading_toward`, `Reply.offer_fit` | removed |
| `[ctx]` `framework_shortlist`, router candidate `offer_*` | removed, except STOP's offer lines when `urgent` fires |
| `[ctx]` inside a running DBT STOP | both branches of each stage, labelled |
| System prompt Framework Index | each framework's facts in plain words |
| Redraft reasons | one ordered chain of six offer reasons (AC-7) |
| Log line per turn | `thread <id> facts [ids] pick <id or none> leading <id or none>` |

**Value sourcing**:

| Action | Value produced | Source |
|---|---|---|
| read the reply | kept facts | `Reply.facts`, filtered by the ten ids (table in `router.py`), two word minimum, and `safety.normalize` whole word match inside one of the person's messages (`user_texts` in the orchestrator); the two STOP facts against `user_texts[-2:]` |
| decide a fact turn | fact turn or not | `technique` (running or not), `tapped`, `accepted_this_turn`, `assessment.blocks_framework`, all already in the orchestrator |
| choose | pick | kept facts + each framework's `activation.fits_when` + the six tie rules in `router.py` + `display_order` from `admin.frameworks`, minus frameworks vetoed by `router.vetoes(user_texts)` and one they have finished (AC-5) |
| choose | leading framework, missing fact | kept facts + `fits_when` (AC-5) |
| know what a draft offers | offered framework | `redraft.offered(draft, registry)`, unchanged |
| redraft text | framework name, offering purpose, boundaries, style `ask` | `Framework.name`; that framework's `offering` stage (its `panic` key for STOP when `overwhelmed_now` is present without `about_to_act`); style from `context.resolve_style(ctx)` |
| redraft text | missing fact in plain words | the plain meaning column of the fact table in `router.py` |
| offer timing | clear allowed, offer due | `context.cooldown_passed`, `context.earliest_offer_ok`, `context.offer_due` (renamed from `closest_fit_due`, AC-16), plus "a pick exists" for reason 6 |
| repairs | `cooldown_passed` | true only for the pick when allowed now (AC-8, AC-16), instead of from `Reply.offer_fit` |
| urgency | STOP skips the wait, STOP offer lines in `[ctx]` | `router.urgent(user_texts)`, unchanged |

**Key invariants**:
- A fact counts only when its words are words the person typed in one message. This proves the words exist, not that they mean the fact. The plain meanings and the tie rules carry the rest, and a real run measures it.
- A framework is started only from an offer the code agrees with. A mismatch that survives the redraft is never stored.
- With no fact present, no offer is owed and none is forced.
- `about_to_act` always puts DBT STOP first. Neither DBT STOP branch ever runs in place of the safety protocol, since its contraindications apply to both.
- The quoted words are never logged, stored or sent to Sentry; only fact ids are.

**Security model**: no change to who can read or write what; no route, table or grant changes. The quoted words are special category health data already present in the person's messages. This design adds no new copy of them at rest and keeps them out of logs and error records (AC-1, AC-12).

**Critical test scenarios**:
- Happy path: the manager chat reaches ABCDE and chat 2 reaches DBT STOP's panic offer from scripted facts, verifies **AC-14**, **AC-4**, **AC-7**, **AC-11**.
- No fit: chat 1 at the fourth message owes nothing and offers nothing, verifies **AC-9**, **AC-14**.
- Invented or stale fact: a fact quoting words only Mani said is dropped, and an old panic quote no longer puts STOP first, verifies **AC-2**.
- Still wrong: two drafts offering the wrong framework end with no offer stored, verifies **AC-8**.
- Rule conflicts: the combinations in AC-4, including the lost wallet facts going to Structured Problem Solving, verifies **AC-4**.
- Keep chatting: an offer during a decline's cooldown gets reason 2, never reason 5, verifies **AC-7**.
- An event alone: the leading framework is never offered, at the fourth message or after, verifies **AC-16**.
- Urgent first message: STOP's offer lines still reach `[ctx]`, verifies **AC-6**.

## Build plan

Tracer Bullet: the first four tasks carry one chat (chat 2, panic to DBT STOP) through the reply, the choice, the redraft and the stored offer with scripted facts. The rest widens it to every framework and removes the phrase scoring.

1. Add the fact table and `Fact` to `router.py` and `mani/llm/schema.py`, the `facts` field before `text` with its dropping validator, and the reading of facts on fact turns with the words check; remove `heading_toward` and `offer_fit`. Satisfies **AC-1**, **AC-2**.
2. Add `fits_when` to all six framework files; add fit, pick, leading and missing fact with the six tie rules to `router.py`, removing vetoed and declined frameworks first. Satisfies **AC-3**, **AC-4**, **AC-5**.
3. DBT STOP content: the overview wording, the `panic` key on its six stages, the boundary scoped to the action branch, both branches in `[ctx]` while it runs, the content test; reseed with `python scripts/seed.py`. Satisfies **AC-11**.
4. Wire the orchestrator and redraft: compute pick and leading from the first draft, the ordered chain of six reasons, computed `clear` and `closest`, the conditional closest fit, a still wrong offer dropped through `cooldown_passed=False`, STOP's offer lines kept when `urgent` fires, the new log line. Scripted integration test for chat 2. Satisfies **AC-6**, **AC-7**, **AC-8**, **AC-9**, **AC-14** (chat 2).
5. Scripted integration tests for chat 1 and the manager chat. Satisfies **AC-14**.
6. Prompt: the Framework Index lists each framework's facts; rewrite every text named in AC-10; the test that no prompt file names the removed fields. Satisfies **AC-10**.
7. Remove phrase scoring: `shortlist`, `is_confident`, `_score_one`, `_promote`, the non absolute rules, `ROUTER_MIN_EXCHANGES`, the `[ctx]` lines, and `strong_signals`, `signals`, `redirects` from the files; rewrite the tests named in AC-13; run the whole `pytest` and check the integration count. Satisfies **AC-12**, **AC-13**.
8. Records: write ADR 014 (amends ADR 007: the closest fit needs a framework that fits or points somewhere, and clear or closest is computed), mark spec 0001 `Superseded by [0005](0005-framework-fit-from-stated-facts/index.md)`, update the ADR index row about phrase matching, `backend/docs/database-schema-reference.md` (the activation keys, near line 190) and `backend/PORT-STATUS.md`, and add the DBT STOP panic wording and the "not over Structured Problem Solving" rule to scope row 29's list. Satisfies **AC-4**, **AC-11**, **AC-12**.
9. Add the three chats to `eval_conversations.yaml`, ask muhammad, then run the small real check and write the journal note. Satisfies **AC-15**.

Update of 2026-10-05, full fits only (AC-16, AC-17), built after tasks 1 to 9:

10. Offers are the pick or nothing: `offers_the_pick` in place of `offer_kind`; reason 2 checked first; reason 4 removed; reason 5 for an allowed offer with no pick; reason 6 only for a pick; rename `closest_fit_due` and `CLOSEST_FIT_AFTER`; remove `closest_fit_ok`, the `[ctx]` `closest_fit` line, `CLOSEST_FIT_LABEL` and the `closest_fit` parameter of `repairs.apply`, `cooldown_for`, `COOLDOWN_AFTER_DECLINE` and the declined exclusion. Rewrite every test AC-16 names. Satisfies **AC-5**, **AC-7**, **AC-16**.
11. Prompt and generated text: drop the nearest and "offer is due" wording AC-16 lists from `mani_base.md`, `response_format.md` and `composer.py`, within the 120 line cap; the composer test; reseed. Satisfies **AC-16**.
12. Records and the runner:
    - `scripts/eval_replies.py --verbose` also prints the facts log line (ids, pick, leading) and the redraft reasons, and the closest fit marker goes;
    - ADR 014 (still proposed): new title, says it supersedes ADR 007's owed closest fit, its consequence line about the nearest fit, and acceptance now waits for AC-17 as well; the ADR index rows 007 and 014;
    - `backend/PORT-STATUS.md` (the turn steps, the frameworks paragraph, the decisions list);
    - `chat-tester/README.md` where it mentions the closest fit button;
    - this spec's `verify.md` (closest steps out, AC-16 and AC-17 steps in);
    - the comments in `redraft.py` and `context.py` that describe the closest fit;
    - scope row 5's mention of the closest fit in `docs/scope/conversation.md`, through `/scope`.
    Satisfies **AC-16**, **AC-17**.
13. Ask muhammad, run the re-check, read it with the printed ids and reasons, write it in the journal. Satisfies **AC-17**.

## Migration plan

**Strategy**: no data migration; a direct replace in one change. Nobody outside the team uses Mani yet (the limited beta waits on slices 6 and 7), so running old and new routers side by side buys nothing a scripted test does not.
**Phases**:
1. Code and content land together, then `python scripts/seed.py` loads the new `activation` and DBT STOP stages.
**Rollback**: revert the commit and run `python scripts/seed.py` again; there is no stored state to undo.
**Risks**: a running server keeps old prompts until its prompt cache expires or it restarts, so restart after seeding.

## Consequences

**Positive**:
- Any wording that means an event, a thought or panic can reach the right framework; nothing waits on someone adding a phrase.
- A conversation with nothing specific in it keeps talking and asks, instead of being handed the nearest guess.
- The client's selection table and tie breakers become code that runs on facts, tested without spending on the model.
- An offer that disagrees with what the person said is corrected or withheld, never started.

**Negative / tradeoffs**:
- The choice now depends on the model filling the checklist well. A model that reads "work pressure" as a `practical_problem` still leans toward Structured Problem Solving. The plain meanings are the main defence, and only a real run measures it.
- Only a full fit is ever offered (AC-16). A conversation whose facts never fully fit gets no offer however long it runs, which is the cost of not guessing. The chats ADR 007's owed nearest offer was written for now depend on the model marking facts: grief on `cannot_control`, the exam and deadlines chats on `practical_problem` with `unsure_what_to_do`. AC-17 checks grief and deadlines.
- A model can still mark a fact loosely without any push (run 1 of the first measurement offered ACT as a full fit for general pressure). The plain meanings are the only defence; AC-17 shows whether removing the push was enough.
- A strict words check drops a fact the model paraphrased or typo corrected, so a real fit can be missed for a turn.
- A mismatch costs a second model call for that turn, and a vague chat past its fourth message can cost one on several turns if the model keeps offering.
- First drafts no longer see the offering stage's boundaries the router candidate used to carry (except the urgent STOP case); they arrive only with a redraft.
- Removing the phrase lists gives up exact, free recall on the client's own example sentences; those sentences now need a real run to check.
- The DBT STOP panic wording and the "STOP not over Structured Problem Solving" rule are ours until the client signs them off.
- A few more output tokens on every reply for the checklist.

**Neutral**:
- Spec 0001's router changes (ABCDE phrases, the fourth weight, the closest fit candidate wording) are replaced; its goal, ABCDE for the manager chat, is kept as AC-14.
- ADR 007 is amended by ADR 014; ADR 002 is unchanged (the redraft is the one ADR 006 already allows); ADR 010's lost wallet behaviour is kept by rule 2.

## Follow-up

- [ ] Ask the client to confirm the DBT STOP panic wording and the STOP versus Structured Problem Solving rule (through scope row 29).
- [ ] After AC-15, decide whether a wider paid run (the client style eval) is worth the remaining budget.
- [x] If the real run shows a fact marked for general stress, tighten its plain meaning: done for `cannot_control`, and the `facts` description now says general pressure, stress or worry on its own is none of the facts. Not enough alone, which led to AC-16.

## Rationale

Reasoning and the options weighed: see [rationale.md](rationale.md).
