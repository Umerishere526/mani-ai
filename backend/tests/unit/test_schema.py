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


def test_the_facts_come_before_the_reply_text():
    """Structured output is written in field order, so facts written after text could not shape it."""
    fields = list(Reply.model_fields)
    assert fields.index("facts") < fields.index("text")
    assert "heading_toward" not in fields and "offer_fit" not in fields


def test_a_malformed_fact_is_dropped_and_the_reply_still_reads():
    reply = Reply.model_validate({
        "text": "t",
        "facts": [{"fact": "event", "words": "my manager shouted"}, {"fact": "meaning"}, "panic", 3],
    })
    assert [(f.fact, f.words) for f in reply.facts] == [("event", "my manager shouted")]


@pytest.mark.parametrize("written", [None, "event", {"fact": "event"}])
def test_facts_that_are_not_a_list_read_as_none(written):
    assert Reply.model_validate({"text": "t", "facts": written}).facts is None
