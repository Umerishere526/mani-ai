# ABOUTME: The turn's reply as the model fills it: a strict JSON schema the providers accept.
# ABOUTME: Read from the schema itself, with no model call.

from openai.lib._pydantic import to_strict_json_schema

from mani.chat.reply import TurnReply, shaped


def test_the_reply_schema_is_accepted_as_a_strict_json_schema():
    schema = to_strict_json_schema(TurnReply)
    assert set(schema["properties"]) == {"question", "people", "events", "text", "said", "action", "framework", "stage",
                                         "safety", "notes", "library", "title", "corrected"}



def test_a_turn_that_may_not_offer_is_never_shown_offer_or_a_set_to_name():
    schema = to_strict_json_schema(shaped(()))
    assert schema["properties"]["action"]["enum"] == ["none", "finish", "stop", "library"]
    assert "framework" not in schema["properties"] and "framework" not in schema["required"]


def test_a_turn_that_may_offer_is_shown_only_the_sets_code_would_show():
    framework = to_strict_json_schema(shaped(("thought_reframe",)))["properties"]["framework"]
    assert framework["anyOf"][0]["enum"] == ["thought_reframe"]
    assert "offer" in to_strict_json_schema(shaped(("thought_reframe",)))["properties"]["action"]["enum"]


def test_an_offer_the_schema_did_not_show_still_reads_so_code_can_refuse_it():
    """A host that does not hold the model to the schema must not turn a refused offer into a failed reply."""
    reply = shaped(()).model_validate({"text": "Lead-in.", "action": "offer", "framework": "abcde",
                                       "safety": {"level": "none"}, "notes": ""})
    assert (reply.action, reply.framework) == ("offer", "abcde")


def test_each_distinct_set_of_offers_is_one_schema_from_turn_to_turn():
    assert shaped(("abcde",)) is shaped(("abcde",)) and shaped(()) is not shaped(("abcde",))
    assert shaped(()).__name__ == TurnReply.__name__, "the schema's name is sent with it and stays the same"
