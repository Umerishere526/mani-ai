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


def test_the_model_is_never_asked_for_a_mirroring_voice():
    """muhammad, 2026-09-24: mirroring is there but never forced. Asking for a voice every
    turn, never the same twice, forced the rotation the prompt no longer asks for."""
    style = Reply.model_json_schema()["$defs"]["Style"]
    assert set(style["properties"]) == {"shape"}
    assert "voice" not in Reply.model_fields["style"].description
