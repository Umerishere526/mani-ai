# ABOUTME: Checks the model's reply is read the way it is meant when it fills a field loosely.
# ABOUTME: A reply that fails validation fails the whole turn, so leniency here is user facing.

import pytest

from mani.llm.schema import Reply


@pytest.mark.parametrize("written", ["decline", "Keep chatting", "true", True])
def test_a_word_in_the_decline_field_still_declines(written):
    reply = Reply.model_validate({"text": "t", "prompts": [{"label": "Keep chatting", "decline": written}]})
    assert reply.prompts[0].decline is True


@pytest.mark.parametrize("written", ["false", "no", False])
def test_an_explicit_no_in_the_decline_field_does_not_decline(written):
    reply = Reply.model_validate({"text": "t", "prompts": [{"label": "Try it", "decline": written}]})
    assert reply.prompts[0].decline is False


def test_the_reply_carries_no_facts_and_its_shape_comes_before_the_text():
    """The model judges the offer itself (spec 0010), so the reply lists no facts; structured
    output is written in field order, so the shape it chooses must come before the text."""
    fields = list(Reply.model_fields)
    assert "facts" not in fields
    assert fields.index("style") < fields.index("text")
    assert "heading_toward" not in fields and "offer_fit" not in fields


@pytest.mark.parametrize("field", ["ending", "felt_after"])
def test_a_reported_ending_or_outcome_is_a_plain_string_so_an_odd_value_never_fails_the_turn(field):
    assert getattr(Reply.model_validate({"text": "t", field: "kind of okay"}), field) == "kind of okay"
