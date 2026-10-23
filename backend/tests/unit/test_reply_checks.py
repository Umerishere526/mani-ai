# ABOUTME: Checks on the model's reply that cost no model call: what it missed that code cannot fix.
# ABOUTME: Each check is a rule about the person or the cadence, so each is a plain test.

from mani.chat import reply_checks
from mani.llm.schema import Reply


def test_a_clean_question_stands():
    draft = Reply(text="What is the hardest part of the evenings?")
    assert reply_checks.misses(
        draft, offered=None, offer_dropped=None, needs_question=True, last_mani_text=None
    ) == []


def test_a_check_missing_one_of_its_parts_is_counted():
    """Spec 0006, AC-3: it is not stored and costs no second call."""
    assert reply_checks.misses(
        Reply(text="Do I have that right?"), offered=None, offer_dropped=None, needs_question=False,
        last_mani_text=None, check_unusable=True,
    ) == ["check unusable"]


def test_a_check_sent_before_their_feeling_was_answered_is_counted():
    """Spec 0006, AC-18: it opens nothing, so their yes to it brings no offer; how often is measured."""
    assert reply_checks.misses(
        Reply(text="So that is it. Do I have that right?"), offered=None, offer_dropped=None,
        needs_question=False, last_mani_text=None, check_too_early=True,
    ) == ["check before the three steps"]


def test_no_check_by_the_expected_message_is_counted_never_asked_for():
    """Spec 0006, AC-11: logged only, so the live runs measure it."""
    assert reply_checks.misses(
        Reply(text="What happened next?"), offered=None, offer_dropped=None, needs_question=True,
        last_mani_text=None, no_check_by=5,
    ) == ["no check by message 5"]


def test_a_comfort_with_no_question_is_missed_before_an_offer():
    comfort = Reply(text="It is okay to feel that way. I am here with you.")
    assert reply_checks.misses(
        comfort, offered=None, offer_dropped=None, needs_question=True, last_mani_text=None
    ) == ["asks no question"]


def test_no_question_is_fine_when_it_is_not_needed():
    """While the questions run, on a safety concern, or when they asked only to be heard."""
    comfort = Reply(text="It is okay to feel that way. I am here with you.")
    assert reply_checks.misses(
        comfort, offered=None, offer_dropped=None, needs_question=False, last_mani_text=None
    ) == []


def test_an_offer_carries_its_own_permission_question():
    """The sent reply is the client's offer, whatever the model wrote in text."""
    draft = Reply(text="It sounds heavy.")
    assert reply_checks.misses(
        draft, offered="abcde", offer_dropped=None, needs_question=True, last_mani_text=None
    ) == []


def test_an_offer_that_could_not_be_made_is_counted_by_its_reason():
    draft = Reply(text="What happened next?")
    assert reply_checks.misses(
        draft, offered=None, offer_dropped="no going_through", needs_question=True,
        last_mani_text=None,
    ) == ["offer unusable: no going_through"]


FIRST = (
    "It can be hard to choose when everything feels like a big step. Would picking one of these small "
    "actions, opening your laptop to look at one travel destination, browsing a site for one new "
    "learning opportunity, or simply sitting near a window for a few minutes, feel most manageable "
    "to you today?"
)
SAME_AGAIN = (
    "It is okay that you are not sure. Between opening your laptop to look at one travel destination, "
    "browsing for one learning opportunity, or sitting by a window for a few minutes, which one "
    "feels like the most manageable one to start with today?"
)


def test_the_same_choices_asked_again_are_missed():
    """Observed: someone who asked Mani to pick got the same three options back, reworded, twice."""
    assert reply_checks.misses(
        Reply(text=SAME_AGAIN), offered=None, offer_dropped=None, needs_question=False, last_mani_text=FIRST
    ) == ["repeats the last question"]


def test_a_different_question_after_an_answer_is_not_a_repeat():
    moved_on = Reply(text="Opening your laptop to look at one place sounds like a start. When will you do it?")
    assert reply_checks.misses(
        moved_on, offered=None, offer_dropped=None, needs_question=False, last_mani_text=FIRST
    ) == []


def test_a_draft_that_chose_a_shape_asking_nothing_is_not_missing_a_question():
    """Whether someone only wants to be listened to is the model's reading, shown by its shape."""
    from mani.llm.schema import Style

    holding = Reply(text="That has been hard for you.", style=Style(shape="mirror and hold"))
    asking = Reply(text="That has been hard for you.", style=Style(shape="mirror and ask"))
    none = Reply(text="That has been hard for you.")
    for draft, expected in ((holding, []), (asking, ["asks no question"]), (none, ["asks no question"])):
        assert reply_checks.misses(
            draft, offered=None, offer_dropped=None, needs_question=True, last_mani_text=None
        ) == expected


def test_a_question_that_leaves_the_stack_out_is_counted_and_one_that_carries_any_of_it_is_not():
    """Lolly, 2026-10-22: D asked only about her belief and dropped the hurt and the missing. Logged, never re-asked."""
    stack = "sad hurt you miss her; her silence means you don't matter; you want an apology"
    bare = Reply(text="Is there anything that makes you question that?")
    carried = Reply(text="You miss her and you want an apology. What makes you question that?")
    assert reply_checks.misses(
        bare, offered=None, offer_dropped=None, needs_question=True, last_mani_text=None, stack=stack,
    ) == ["stack missing"]
    assert reply_checks.misses(
        carried, offered=None, offer_dropped=None, needs_question=True, last_mani_text=None, stack=stack,
    ) == []
    assert reply_checks.misses(
        bare, offered=None, offer_dropped=None, needs_question=True, last_mani_text=None, stack="",
    ) == []


def test_a_figure_of_speech_in_a_reply_is_counted_with_the_phrase_that_was_used():
    """Lolly, 2026-10-22: "what would you want to hold onto" and "hold you" read as artificial."""
    reply = Reply(text="What would you want to hold onto as you think about this?")
    assert reply_checks.misses(
        reply, offered=None, offer_dropped=None, needs_question=True, last_mani_text=None,
    ) == ["figure of speech: hold onto"]
    plain = Reply(text="What seems more realistic to you now?")
    assert reply_checks.misses(
        plain, offered=None, offer_dropped=None, needs_question=True, last_mani_text=None,
    ) == []
