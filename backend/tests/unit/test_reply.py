# ABOUTME: The turn's reply as the model fills it: a strict JSON schema the providers accept, and the fixed
# ABOUTME: reply that stands in when every host fails.

from openai.lib._pydantic import to_strict_json_schema

from mani.chat.reply import TurnReply


def test_the_reply_schema_is_accepted_as_a_strict_json_schema():
    schema = to_strict_json_schema(TurnReply)
    assert set(schema["properties"]) == {"text", "action", "framework", "stage", "safety", "notes", "title"}


def test_a_fallback_reply_judges_nothing_and_keeps_no_notes():
    reply = TurnReply.fallback("I'm having trouble replying right now.")
    assert reply.text == "I'm having trouble replying right now."
    assert reply.safety.level == "none"
    assert reply.notes == ""
    assert reply.action == "none"
