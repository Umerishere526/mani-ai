# ABOUTME: Checks the one rule that moves a conversation's safety each turn (worry.step): the sequences below were run
# ABOUTME: through the rules as they stood before it, and differ only where a comment says muhammad ruled otherwise.

import datetime as dt
import uuid

import pytest

from mani.chat import record as rec
from mani.chat import worry
from mani.chat.pause import ReturnCheck
from mani.chat.reply import Safety
from mani.chat.safety import State
from mani.chat.worry import Phase
from mani.db.threads import TurnContext
from mani.models.rows import Thread


def D(**read) -> Safety:
    return _read("danger", read)


def U(**read) -> Safety:
    return _read("unsure", read)


def _read(level: str, read: dict) -> Safety:
    """A worry with no kind fails the reply's own check, so the model never sends one; worry.step must still hold it
    to the right rule, so such a read is built without that check."""
    if read.get("about") is None:
        return Safety.model_construct(level=level, **read)
    return Safety(level=level, **read)


def N(**read) -> Safety:
    return Safety(level="none", **read)


ORD, ASK, ANS = Phase.ORDINARY, Phase.ASKING, Phase.ANSWERING
# What each turn must come to: state after, pauses, a worry settled, where to get help due, and whose danger is open.
# S2 and S7 (PROVISIONAL: clinician sign-off required before deploy): the first danger of a kind that does not pause is
# due the help line, even with someone with them; before, only a body worry code raised got it.
# CR-3 (PROVISIONAL: clinician sign-off required before deploy): while danger about a person is held, every reply that
# does not pause is due it, unless their message says someone is with them (S7); manasa's test (2026-11-25) heard
# "you do not have to tell anyone you know" after emergency guidance. A body symptom keeps its line once per rise.
DANGER, UNSURE, CLEAR = "danger", "unsure", "clear"
T, F = True, False

# (turns as (phase, the model's read), what each turn must come to)
SEQUENCES = {
    "danger goes on after Mani answered it, so it pauses": (
        [(ORD, D(about="themselves")), (ORD, D(about="themselves"))],
        [(DANGER, F, F, T, "themselves"), (DANGER, T, F, F, "themselves")]),
    "help in place stops the pause": (
        [(ORD, D(about="themselves")), (ORD, D(about="themselves", help_in_place=True))],
        [(DANGER, F, F, T, "themselves"), (DANGER, F, F, F, "themselves")]),
    "asked what they meant and they say it again, the screen comes at once (2026-11-16)": (
        [(ORD, U(about="themselves")), (ORD, D(about="themselves"))],
        [(UNSURE, F, F, F, "themselves"), (DANGER, T, F, F, "themselves")]),
    # muhammad, 2026-11-20: only the model raises a worry to danger. Before, a second unsure after Mani asked was held as
    # danger, and production paused someone lonely and crying after "unsafe with my family" whom the model judged unsure
    # every turn ("no self-harm or immediate danger is stated").
    "a worry the model only ever judged unsure never pauses (production, 2026-11-20)": (
        [(ORD, U(about="from_someone")), (ORD, U(about="from_someone")), (ORD, U(about="themselves"))],
        [(UNSURE, F, F, F, "from_someone"), (UNSURE, F, F, F, "from_someone"), (UNSURE, F, F, F, "themselves")]),
    "asked and still unsure stays unsure, and danger said after it pauses at once": (
        [(ORD, U(about="themselves")), (ORD, U(about="themselves")), (ORD, D(about="themselves"))],
        [(UNSURE, F, F, F, "themselves"), (UNSURE, F, F, F, "themselves"), (DANGER, T, F, F, "themselves")]),
    # muhammad, 2026-11-20: an unsure worry they never answer closes on the second message in a row read as no concern.
    # Before, the first one closed it, and the prompt kept it open for good by reading a changed subject as unsure.
    "an unsure worry they never answer closes on the second calm message": (
        [(ORD, U(about="themselves")), (ORD, N()), (ORD, N())],
        [(UNSURE, F, F, F, "themselves"), (UNSURE, F, F, F, "themselves"), (CLEAR, F, T, F, None)]),
    "the worry said again between two calm messages starts the count over": (
        [(ORD, U(about="themselves")), (ORD, N()), (ORD, U(about="themselves")), (ORD, N())],
        [(UNSURE, F, F, F, "themselves")] * 4),
    # S1 (PROVISIONAL: clinician sign-off required before deploy): danger cleared on one message read as no concern, so
    # "I took pills" then "can we talk about work" ended it. A change of subject is not safety: danger clears on their
    # word that they are safe or someone is with them, or on the second calm message after Mani's reply asked.
    "a change of subject never clears danger, and the second calm message does (S1)": (
        [(ORD, D(about="themselves")), (ORD, N()), (ORD, N())],
        [(DANGER, F, F, T, "themselves"), (DANGER, F, F, T, "themselves"), (CLEAR, F, T, F, None)]),
    "their word that they are safe clears danger at once (S1)": (
        [(ORD, D(about="themselves")), (ORD, N(says_safe=True))],
        [(DANGER, F, F, T, "themselves"), (CLEAR, F, T, F, None)]),
    "someone with them clears danger at once (S1)": (
        [(ORD, D(about="themselves")), (ORD, N(help_in_place=True))],
        [(DANGER, F, F, T, "themselves"), (CLEAR, F, T, F, None)]),
    "a calm message held as danger never pauses, and danger said after it does (S1)": (
        [(ORD, D(about="themselves")), (ORD, N()), (ORD, D(about="themselves"))],
        [(DANGER, F, F, T, "themselves"), (DANGER, F, F, T, "themselves"), (DANGER, T, F, F, "themselves")]),
    "danger of one kind never holds an unsure read of another (the review of 2026-11-20)": (
        [(ORD, U(about="body", symptom_now="unsaid")), (ORD, U(about="themselves"))],
        [(DANGER, F, F, T, "body"), (UNSURE, F, F, F, "themselves")]),
    "asked about one kind is not asked about another (the held-back run, 2026-11-16)": (
        [(ORD, U(about="from_someone")), (ORD, D(about="themselves")), (ORD, D(about="themselves"))],
        [(UNSURE, F, F, F, "from_someone"), (DANGER, F, F, T, "themselves"), (DANGER, T, F, F, "themselves")]),
    "a body worry the model held lower is raised, with the call-now line once": (
        [(ORD, U(about="body", symptom_now="unsaid")), (ORD, U(about="body", symptom_now="unsaid"))],
        [(DANGER, F, F, T, "body"), (DANGER, F, F, F, "body")]),
    "a body danger pauses only on a refusal of the help for a symptom happening now": (
        [(ORD, U(about="body", symptom_now="unsaid")), (ORD, D(about="body", symptom_now="yes")),
         (ORD, D(about="body", symptom_now="yes", declined=True))],
        [(DANGER, F, F, T, "body"), (DANGER, F, F, F, "body"), (DANGER, T, F, F, "body")]),
    "their word that the symptom stopped holds it at unsure": (
        [(ORD, U(about="body", symptom_now="unsaid")), (ORD, U(about="body", symptom_now="no"))],
        [(DANGER, F, F, T, "body"), (UNSURE, F, F, F, "body")]),
    "the kind changes inside one open worry and the call-now line comes once (2026-11-18)": (
        [(ORD, D(about="themselves")), (ORD, U(about="body", symptom_now="unsaid"))],
        [(DANGER, F, F, T, "themselves"), (DANGER, F, F, T, "body")]),
    "a settled symptom reopens only on their newest word that it is happening (2026-11-11; S1 settles it on two)": (
        [(ORD, U(about="body", symptom_now="unsaid")), (ORD, N()), (ORD, N()), (ORD, U(about="body", symptom_now="unsaid")),
         (ORD, D(about="body", symptom_now="yes"))],
        [(DANGER, F, F, T, "body"), (DANGER, F, F, F, "body"), (CLEAR, F, T, F, None), (CLEAR, F, F, F, None),
         (DANGER, F, F, T, "body")]),
    "a refusal never settles a concern": (
        [(ORD, D(about="themselves")), (ORD, N(declined=True))],
        [(DANGER, F, F, T, "themselves"), (DANGER, T, F, F, "themselves")]),
    "danger lowered to unsure is still danger once asked": (
        [(ORD, D(about="themselves")), (ORD, U(about="themselves")), (ORD, D(about="themselves"))],
        [(DANGER, F, F, T, "themselves"), (DANGER, T, F, F, "themselves"), (DANGER, T, F, F, "themselves")]),
    "a worry that settled and a new one starts over: the first danger message gets Mani's reply": (
        [(ORD, D(about="themselves")), (ORD, N(says_safe=True)), (ORD, D(about="themselves")),
         (ORD, D(about="themselves"))],
        [(DANGER, F, F, T, "themselves"), (CLEAR, F, T, F, None), (DANGER, F, F, T, "themselves"),
         (DANGER, T, F, F, "themselves")]),
    # After a settled worry its kind is forgotten. Before, a later danger the model gave no kind inherited the old one:
    # after a body worry it could not pause with a refusal, and after a worry about themselves it paused with none.
    "a danger of no known kind after a settled body worry pauses on a refusal": (
        [(ORD, U(about="body", symptom_now="unsaid")), (ORD, N(says_safe=True)), (ORD, D(declined=True)),
         (ORD, D(declined=True))],
        [(DANGER, F, F, T, "body"), (CLEAR, F, T, F, None), (DANGER, F, F, T, None), (DANGER, T, F, F, None)]),
    # muhammad, 2026-11-24: during an open body worry a danger of no known kind took the body's kind, so its refusal
    # never paused; the body's rule holds only a read about the body.
    "a refused danger of no known kind during an open body worry pauses (2026-11-24)": (
        [(ORD, U(about="body", symptom_now="unsaid")), (ORD, D(declined=True)), (ORD, D(declined=True))],
        [(DANGER, F, F, T, "body"), (DANGER, T, F, F, "body"), (DANGER, T, F, F, "body")]),
    "a danger of no known kind after a settled worry needs a refusal like any other": (
        [(ORD, D(about="themselves")), (ORD, N(says_safe=True)), (ORD, D()), (ORD, D())],
        [(DANGER, F, F, T, "themselves"), (CLEAR, F, T, F, None), (DANGER, F, F, T, None),
         (DANGER, F, F, T, None)]),
    "the first message back after a pause never pauses, whatever the read reports": (
        [(ASK, D(about="themselves", still_there=True))],
        [(DANGER, F, F, T, "themselves")]),
    "their answer to how things are pauses only when it says the danger is still there": (
        [(ASK, D(about="themselves")), (ANS, D(about="themselves", still_there=True))],
        [(DANGER, F, F, T, "themselves"), (DANGER, T, F, F, "themselves")]),
    "an answer that is fine settles it": (
        [(ASK, D(about="themselves")), (ANS, N())],
        [(DANGER, F, F, T, "themselves"), (CLEAR, F, T, F, None)]),
    # muhammad, 2026-11-23: "I took more pills" in answer to how things are used to wait one more message for the
    # pause when the model did not also mark it still there.
    "an answer read as danger pauses even when the read does not say it is still there": (
        [(ASK, N()), (ANS, D(about="themselves"))],
        [(CLEAR, F, F, F, None), (DANGER, T, F, F, "themselves")]),
    "an answer read as danger with someone with them does not pause": (
        [(ASK, N()), (ANS, D(about="themselves", help_in_place=True))],
        [(CLEAR, F, F, F, None), (DANGER, F, F, T, "themselves")]),
    "a first message back that is read as no worry and a refusal keeps the question open": (
        [(ASK, N(declined=True))],
        [(UNSURE, F, F, F, None)]),
}


@pytest.mark.parametrize("name", SEQUENCES)
def test_each_turn_of_a_sequence_comes_to_what_the_rules_gave_it(name):
    turns, expected = SEQUENCES[name]
    standing = worry.Standing(state=State.CLEAR, about=None, phase=turns[0][0])
    for (phase, read), want in zip(turns, expected, strict=True):
        standing = standing.model_copy(update={"phase": phase})
        outcome = worry.step(standing, read)
        got = (outcome.state.value, outcome.pausing, outcome.settled_now, outcome.resources_due, outcome.about)
        assert got == want, (name, read)
        standing = worry.Standing(
            state=outcome.state, about=outcome.about, phase=phase, settled=standing.settled or outcome.settled_now,
            calm=outcome.calm)


def test_an_answer_to_the_safety_question_after_a_set_settles_it_at_once():
    """Mani asked directly, so a calm answer closes the worry and the set can close on the same turn."""
    asked = worry.Standing(state=State.UNSURE, about=None, phase=ORD, end_check=True)
    assert worry.step(asked, N()).state is State.CLEAR


USER = uuid.UUID("a0000000-0000-4000-8000-0000000000f1")
THREAD = uuid.UUID("b0000000-0000-4000-8000-0000000000f1")
SAID = dt.datetime(2026, 11, 13, 12, 0, tzinfo=dt.UTC)
CHECK = ReturnCheck(pause_id=uuid.UUID("c0000000-0000-4000-8000-0000000000f1"), reason="pills")


def _ctx(*, safety: str) -> TurnContext:
    thread = Thread(id=THREAD, user_id=USER, created_at=SAID, last_message_at=SAID, safety=safety,
                    understanding={rec.ABOUT: "themselves"})
    return TurnContext(thread=thread, profile=None, technique=None)


def test_the_phase_is_the_owed_check_then_the_question_it_asked_then_neither():
    ctx = _ctx(safety="clear")
    assert worry.standing(ctx, CHECK, None).phase is Phase.ASKING
    assert worry.standing(ctx, None, str(CHECK.pause_id)).phase is Phase.ANSWERING
    assert worry.standing(ctx, None, None).phase is Phase.ORDINARY


def test_the_record_keeps_one_kind_while_a_worry_is_open_and_forgets_it_when_it_settles():
    opened = worry.step(worry.Standing(state=State.CLEAR, about=None, phase=ORD), D(about="themselves"))
    record = worry.record_after({}, opened, check=None, answering=None)
    assert record == {rec.ABOUT: "themselves", rec.DANGER_REACHED: True, rec.IMMEDIACY: rec.IMMEDIACY_OPEN}
    settled = worry.step(worry.Standing(state=State.DANGER, about="themselves", phase=ORD), N(says_safe=True))
    after = worry.record_after(record, settled, check=None, answering=None)
    assert after == {rec.DANGER_REACHED: True, rec.SAFETY_SETTLED: True}


def test_the_record_counts_calm_messages_only_while_the_worry_waits():
    waiting = worry.step(worry.Standing(state=State.UNSURE, about="themselves", phase=ORD), N())
    record = worry.record_after({rec.ABOUT: "themselves"}, waiting, check=None, answering=None)
    assert record == {rec.ABOUT: "themselves", rec.CALM: 1}
    closed = worry.step(worry.Standing(state=State.UNSURE, about="themselves", phase=ORD, calm=1), N())
    assert worry.record_after(record, closed, check=None, answering=None) == {rec.SAFETY_SETTLED: True}


def test_the_record_keeps_where_the_return_check_stands():
    out = worry.step(worry.Standing(state=State.CLEAR, about=None, phase=ASK), N())
    asked = worry.record_after({}, out, check=CHECK, answering=None)
    assert asked == {rec.RETURN_CHECK: {"pause": str(CHECK.pause_id), "state": "asked"}}
    answered = worry.record_after(asked, out, check=None, answering=str(CHECK.pause_id))
    assert answered[rec.RETURN_CHECK] == {"pause": str(CHECK.pause_id), "state": "answered"}


@pytest.mark.parametrize(("about", "read", "pauses"), [
    ("themselves", D(about="themselves"), True),
    ("someone_else", D(about="someone_else"), True),
    ("from_someone", D(about="from_someone"), True),
    ("someone_else", D(about="someone_else", declined=True), True),
    ("themselves", D(about="themselves", help_in_place=True), False),
    ("themselves", D(about="themselves", declined=True, help_in_place=True), False),
    (None, D(), False),
    (None, D(declined=True), True),
    ("body", D(about="body", symptom_now="yes"), False),
    ("body", D(about="body", symptom_now="yes", declined=True), True),
    ("body", U(about="body", symptom_now="yes", declined=True), True),
    ("body", D(about="body", symptom_now="unsaid", declined=True), False),
    ("body", N(declined=True), False),
    ("body", D(), False),
    ("body", D(declined=True), True),
], ids=["themselves", "someone else", "from someone", "someone else, refused", "someone is with them",
        "someone is with them and they refuse", "no known kind", "no known kind, refused", "a doubt about a symptom",
        "refusing help for a symptom now (2026-11-13)",
        "refusing help for a symptom now the model judged unsure (2026-11-23)", "a symptom not said to be happening", "declined and nothing else",
        "no known kind in a body worry", "no known kind in a body worry, refused (2026-11-24)"])
def test_danger_that_goes_on_pauses_for_these_kinds_and_reads(about, read, pauses):
    """muhammad, 2026-11-14: a person about to act, alone, who answered every question honestly never paused, so danger to
    themselves, to someone else or from someone pauses without a refusal; a body symptom needs one for a symptom
    happening now (2026-11-13), and so does a danger of no known kind."""
    assert worry.step(worry.Standing(state=State.DANGER, about=about, phase=ORD), read).pausing is pauses


@pytest.mark.parametrize("message", [
    "I want to die", "i don't want to live anymore", "Sometimes I wish I were dead", "I want to hurt myself",
    "I feel like ending it", "honestly I might kill myself", "This is my last message",
    "everyone is better off without me", "I DON’T WANT TO LIVE",
])
def test_a_high_risk_phrase_the_model_read_lower_is_raised_to_danger_with_help_and_no_pause(message):
    """S3 and S4 (PROVISIONAL: clinician sign-off required before deploy): the client's Risk Classification makes each
    of these HIGH, and "I wish I were dead" was read as unsure. Code raises a read below danger to danger about
    themselves, so the help line is due, and never pauses on that message, even with danger already open."""
    for stood, read in ((worry.Standing(state=State.CLEAR, about=None, phase=ORD), N()),
                        (worry.Standing(state=State.CLEAR, about=None, phase=ORD), U(about="themselves")),
                        (worry.Standing(state=State.DANGER, about="themselves", phase=ORD), U(about="themselves"))):
        outcome = worry.step(stood, read, message)
        assert outcome.state is State.DANGER and outcome.about == "themselves" and not outcome.pausing, (stood, read)
    first = worry.step(worry.Standing(state=State.CLEAR, about=None, phase=ORD), N(), message)
    assert first.resources_due


@pytest.mark.parametrize("message", [
    "I have a plan for the weekend", "I wrote letters to my grandma", "I gave my things away to charity",
    "I want to diet before the wedding",
])
def test_everyday_words_near_a_high_risk_phrase_are_left_to_the_model(message):
    """S4 kept narrow (2026-11-25): out-of-context phrases and a longer word ("diet") never raise a read; a false alarm
    is the lockout the client objected to (2026-11-20). PROVISIONAL: clinician sign-off required before deploy."""
    outcome = worry.step(worry.Standing(state=State.CLEAR, about=None, phase=ORD), N(), message)
    assert outcome.state is State.CLEAR and not outcome.resources_due


def test_the_phrase_floor_only_raises_and_ignores_messages_without_a_listed_phrase():
    """S4: the floor never lowers a read, and words near a phrase are not it."""
    clear = worry.Standing(state=State.CLEAR, about=None, phase=ORD)
    assert worry.step(clear, N(), "I'm dying to see that film").state is State.CLEAR
    assert worry.step(clear, N(), "my grandfather died and I miss him").state is State.CLEAR
    held = worry.step(worry.Standing(state=State.DANGER, about="themselves", phase=ORD), D(about="themselves"),
                      "I want to die")
    assert held.pausing, "a danger the model read itself goes on and pauses as before"


def test_a_pause_after_an_overdose_is_for_an_overdose_whatever_the_pausing_message_says():
    """S6 and R90 (PROVISIONAL: clinician sign-off required before deploy): after an overdose emergency services lead
    and 911 is the most prominent action. The model marks the overdose (safety.overdose); the worry keeps it until it
    closes, so the pause on a later message ("alone, I don't want help") is still for an overdose."""
    clear = worry.Standing(state=State.CLEAR, about=None, phase=ORD)
    took = worry.step(clear, D(about="themselves", overdose=True))
    record = worry.record_after({}, took, check=None, answering=None)
    assert record[rec.OVERDOSE] is True
    held = worry.Standing(state=took.state, about=took.about, phase=ORD, overdose=True)
    paused = worry.step(held, D(about="themselves"))
    assert paused.pausing and paused.paused_for == "overdose"
    other = worry.step(worry.Standing(state=State.DANGER, about="from_someone", phase=ORD), D(about="from_someone"))
    assert other.pausing and other.paused_for == "from_someone"
    settled = worry.step(held, N(says_safe=True))
    assert rec.OVERDOSE not in worry.record_after(record, settled, check=None, answering=None)


def _walk(turns: list[tuple[Phase, Safety]], message: str = "") -> list[worry.Outcome]:
    """Each turn's outcome, the standing carried from one to the next as the record would carry it."""
    standing, outcomes = worry.Standing(state=State.CLEAR, about=None, phase=ORD), []
    for phase, read in turns:
        standing = standing.model_copy(update={"phase": phase})
        outcome = worry.step(standing, read, message)
        outcomes.append(outcome)
        standing = worry.Standing(state=outcome.state, about=outcome.about, phase=phase, calm=outcome.calm,
                                  immediacy=outcome.immediacy)
    return outcomes


def test_confirmed_thoughts_of_not_being_here_open_the_question_of_immediate_danger_until_answered():
    """CR-1 (PROVISIONAL: clinician sign-off required before deploy): manasa's crisis test (2026-11-25) confirmed
    suicidal thoughts, and Mani never asked whether she was in immediate danger; it went back to reflective questions
    until she said she was alone and afraid of acting tonight. Once thoughts about themselves are confirmed (asked and
    still unsure, or danger), immediacy is open, and only their answer closes it."""
    asked, confirmed, deflected, answered = _walk([
        (ORD, U(about="themselves")), (ORD, U(about="themselves")), (ORD, U(about="themselves")),
        (ORD, D(about="themselves", immediacy_said=True))])
    assert asked.immediacy is None, "the first unsure read gets the clarifying question (S5), not this one"
    assert confirmed.immediacy == "open" and deflected.immediacy == "open"
    assert answered.immediacy == "answered"
    first_danger = _walk([(ORD, D(about="themselves"))])[0]
    assert first_danger.immediacy == "open"
    floored = _walk([(ORD, N())], "I want to die")[0]
    assert floored.immediacy == "open"
    assert _walk([(ORD, D(about="someone_else"))])[0].immediacy is None, "the question is about danger to themselves"


def test_the_record_keeps_where_immediacy_stands_only_while_the_worry_is_open():
    opened = worry.step(worry.Standing(state=State.CLEAR, about=None, phase=ORD), D(about="themselves"))
    record = worry.record_after({}, opened, check=None, answering=None)
    assert record[rec.IMMEDIACY] == "open"
    settled = worry.step(worry.Standing(state=State.DANGER, about="themselves", phase=ORD, immediacy="open"),
                         N(says_safe=True))
    assert rec.IMMEDIACY not in worry.record_after(record, settled, check=None, answering=None)


def test_danger_a_pause_left_unresolved_closes_only_on_their_word_and_pauses_again_only_if_it_goes_on():
    """CR-5 (PROVISIONAL: clinician sign-off required before deploy): manasa's crisis test (2026-11-25) asked what
    happens when someone keeps coming back after a pause without doing anything about their safety. A worry that paused
    the chat stays danger until they say they are safe or someone is with them: a message back that says nothing of it,
    an answer that does not say it, and any number of calm messages after keep it open, never pause, and keep the
    question of immediate danger open. A second pause comes only on danger said again (S12)."""
    paused = worry.step(worry.Standing(state=State.UNSURE, about="themselves", phase=ORD), D(about="themselves"))
    assert paused.pausing
    record = worry.record_after({}, paused, check=None, answering=None)
    assert record[rec.PAUSED] is True
    held = worry.Standing(state=State.DANGER, about="themselves", phase=ASK, paused=True,
                          immediacy=rec.IMMEDIACY_ANSWERED)
    back = worry.step(held, N())
    assert back.state is State.DANGER and not back.pausing and back.immediacy == rec.IMMEDIACY_OPEN
    for phase in (ANS, ORD, ORD, ORD):
        quiet = worry.step(held.model_copy(update={"phase": phase, "immediacy": rec.IMMEDIACY_OPEN}), N())
        assert quiet.state is State.DANGER and not quiet.pausing and quiet.resources_due, phase
    assert worry.step(held.model_copy(update={"phase": ANS}), D(about="themselves")).pausing
    for safe in (N(says_safe=True), N(help_in_place=True)):
        settled = worry.step(held.model_copy(update={"phase": ANS}), safe)
        assert settled.state is State.CLEAR and settled.settled_now
        assert rec.PAUSED not in worry.record_after(record, settled, check=None, answering=None)
