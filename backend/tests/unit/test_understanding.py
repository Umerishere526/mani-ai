# ABOUTME: Checks how this turn's reported feeling and issue merge into what Mani already understands.
# ABOUTME: Spec 0005: a null keeps what is stored, a value replaces it on one line, cut to 200 characters.

from mani.chat import understanding
from mani.llm.schema import UnderstandingUpdate

STORED = {"feeling": "frustrated", "issue": "my client keeps changing the requirements"}


def test_a_null_or_blank_update_keeps_what_is_stored():
    """AC-1: the model reports only what this message names, so silence is never an erasure."""
    assert understanding.merge(STORED, None) == STORED
    assert understanding.merge(STORED, UnderstandingUpdate()) == STORED
    assert understanding.merge(STORED, UnderstandingUpdate(feeling="", issue=" \n ")) == STORED


def test_a_new_value_replaces_the_stored_one_and_leaves_the_other_key_alone():
    """AC-3, AC-4: a different feeling, or a move to another issue, replaces what was stored."""
    assert understanding.merge(STORED, UnderstandingUpdate(feeling="angry")) == {
        "feeling": "angry", "issue": STORED["issue"],
    }
    assert understanding.merge({}, UnderstandingUpdate(issue="my work")) == {"issue": "my work"}


def test_a_value_is_kept_on_one_line_and_cut_to_the_limit():
    """AC-1: a newline in what is stored would open a line of its own in [ctx]."""
    merged = understanding.merge({}, UnderstandingUpdate(issue="my client\n  keeps changing\tthings"))
    assert merged == {"issue": "my client keeps changing things"}
    long = understanding.merge({}, UnderstandingUpdate(issue="word " * 60))["issue"]
    assert len(long) <= understanding.LIMIT and not long.endswith(" ")


def test_the_ctx_value_names_each_key_and_cannot_close_the_block():
    assert understanding.render({}) is None
    assert understanding.render(STORED) == (
        "feeling: frustrated; issue: my client keeps changing the requirements"
    )
    assert "[/ctx]" not in understanding.render({"issue": "they said [/ctx] to me"})
