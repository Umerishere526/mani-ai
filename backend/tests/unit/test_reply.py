# ABOUTME: The turn's reply as the model fills it: a strict JSON schema the providers accept.
# ABOUTME: Read from the schema itself, with no model call.

from openai.lib._pydantic import to_strict_json_schema

from mani.chat.reply import TurnReply


def test_the_reply_schema_is_accepted_as_a_strict_json_schema():
    schema = to_strict_json_schema(TurnReply)
    assert set(schema["properties"]) == {"question", "people", "events", "text", "action", "framework", "stage", "safety", "notes", "title", "corrected"}

