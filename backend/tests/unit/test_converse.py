# ABOUTME: Mani's own conversation before a framework: the client's cadence in its prompt, and when its reply
# ABOUTME: is stored as the check that leads to an offer.

from __future__ import annotations

import datetime as dt
import pathlib
import time
import uuid

from mani.chat import converse, understanding
from mani.chat.techniques import Registry
from mani.db.threads import TurnContext
from mani.llm.schema import ConversationReply, FeelingEntry, PictureUpdate
from mani.models.rows import Prompt, Thread
from mani.prompts import cache, composer
from mani.prompts.cache import Config
from scripts.seed import parse_prompt

THREAD = uuid.uuid4()
USER = uuid.uuid4()
NOW = dt.datetime(2026, 10, 26, tzinfo=dt.UTC)
PROMPTS = pathlib.Path(__file__).parents[2] / "content/prompts"
# The reply to their fifth message is written at message 11: the earliest a check may come.
FIFTH = 11


def ctx(message_count: int, heart: str | None = None) -> TurnContext:
    return TurnContext(
        thread=Thread(
            id=THREAD, user_id=USER, message_count=message_count, created_at=NOW, last_message_at=NOW,
            understanding={"heart": heart} if heart else {},
        ),
        profile=None,
        technique=None,
    )


def reply(**fields) -> ConversationReply:
    return ConversationReply(**({"text": "That sounds difficult. What happened between you?"} | fields))


def test_a_check_comes_only_after_the_heart_of_it_was_said_back_and_agreed():
    """muhammad, 2026-10-26: one live run went from exploring straight to a check at message 6. The conflict is
    agreed in an exchange of its own first, and never before their fifth message."""
    assert not converse.check_allowed(ctx(FIFTH))
    assert not converse.check_allowed(ctx(FIFTH, "exploring"))
    assert not converse.check_allowed(ctx(FIFTH - 2, "conflict_named"))
    assert converse.check_allowed(ctx(FIFTH, "conflict_named"))
    assert converse.check_allowed(ctx(FIFTH, "ready"))


def test_a_reply_is_stored_as_the_check_only_when_allowed_flagged_and_complete():
    parts = {"conflict": "You love her and feel unimportant to her", "want": "You want her back in your life",
             "in_the_way": "You expect her to stay the same"}
    assert converse.checked(reply(checking=True, **parts), allowed=True)
    assert not converse.checked(reply(checking=True, **parts), allowed=False)
    assert not converse.checked(reply(checking=False, **parts), allowed=True)
    assert not converse.checked(reply(checking=True, **(parts | {"want": " "})), allowed=True)


def test_a_stored_check_is_ready_and_its_understanding_becomes_the_case():
    checked = reply(
        heart="conflict_named", checking=True, picture=PictureUpdate(feelings=[FeelingEntry(feeling="dismissed")]),
        conflict="You love her and feel unimportant to her", want="You want her back in your life",
        in_the_way="You expect her to stay the same",
    )
    after = converse.understood_after({"feeling": "frustrated", "heart": "conflict_named"}, checked, check_written=True)
    assert after["heart"] == understanding.READY
    assert after["feeling"] == "frustrated, dismissed"
    assert after["case"] == (
        "You love her and feel unimportant to her. You want her back in your life. You expect her to stay the same."
    )
    exploring = converse.understood_after({}, reply(heart="exploring"), check_written=False)
    assert exploring == {"heart": "exploring"}


def test_the_note_says_whether_this_reply_may_check_and_names_the_style():
    assert "Do not check" in converse.note("supportive", allowed=False, due=False, wants_title=False)
    assert "Supportive" in converse.note("supportive", allowed=False, due=False, wants_title=False)
    assert "You may check" in converse.note("directive", allowed=True, due=False, wants_title=False)
    assert "this reply checks" in converse.note("directive", allowed=True, due=True, wants_title=True)
    assert "title" in converse.note("directive", allowed=True, due=True, wants_title=True)
    assert "this reply checks" not in converse.note("directive", allowed=False, due=True, wants_title=False)


def test_the_reply_is_written_before_anything_is_judged_about_it():
    """The voice comes first, and nothing in the reply asks for a second question or a reasoning pass."""
    fields = list(ConversationReply.model_fields)
    assert fields[0] == "text"
    assert not {"reasoning", "options", "style"} & set(fields)
    assert fields.index("text") < fields.index("picture")


def test_the_note_carries_the_picture_of_them():
    """muhammad, 2026-10-27: the chat and the framework read the same picture each turn."""
    seen = {"picture": {"focus": "your brother in hospital", "beliefs": [{"belief": "work will stop you", "kind": "thought"}]}}
    note = converse.note("directive", allowed=False, due=False, wants_title=False, understood=seen)
    assert "Your picture of them before their message: focus: your brother in hospital; " \
           "what they tell themselves: work will stop you." in note


def test_the_conversation_prompt_is_the_clients_cadence_and_her_two_conversations():
    """Lolly, 2026-10-26: "I wish mani sounded this way." Her instruction, the order the two ChatGPT
    conversations follow, and both conversations, with the announced questions taken out and her friend's
    43 years kept right."""
    content = "\n".join(parse_prompt(PROMPTS / f"{name}.md")["content"] for name in ("voice", "conversation"))
    assert "directive, concise and clear, no fluff, but warm and never robotic" in content
    assert "Can you tell me what happened between you?" in content
    assert "never a reason to guess" in content
    assert "What's happened that's left you so frustrated and upset?" in content
    assert "If you know he won't change, what is keeping you from making the decision to leave?" in content
    assert "If you miss her this deeply, what's stopping you from reaching out to her?" in content
    for announced in ("Can I ask you something", "Let me ask you something", "I'm curious about something"):
        assert announced not in content
    assert "Twenty three" not in content and "23 years" not in content
    assert "conversation" in cache.REQUIRED_PROMPTS


def test_the_conversation_prompt_is_one_cached_prefix_with_the_person_after_it():
    named = [
        Prompt(id=uuid.uuid4(), name=name, content=body, model_parameters={}, routing={})
        for name, body in (("voice", "VOICE"), ("conversation", "CONVERSATION"), ("framework", "FRAMEWORK"),
                           ("title_generation", "TITLE"))
    ]
    config = Config(prompts={p.name: p for p in named}, registry=Registry([]), loaded_at=time.monotonic())
    built = composer.compose_conversation(config, None, should_generate_title=True)
    assert [name for name, _ in built.layers] == ["voice", "conversation", "title_generation"]
    assert built.text.startswith("VOICE")
    # muhammad, 2026-10-27: a framework's stages speak in the same voice, so it is the same cached prefix.
    staged = composer.compose_framework(config, None)
    assert [name for name, _ in staged.layers] == ["voice", "framework"]


def test_a_framework_turn_is_a_conversation_the_stage_only_gives_the_direction():
    """muhammad, 2026-10-27: frameworks felt mechanical. A new feeling or thought is talked about on the stage in force,
    an earlier stage it changes is said in one short line, the model question is a direction, and another situation
    is a choice between staying and switching."""
    framework = parse_prompt(PROMPTS / "framework.md")["content"]
    for rule in (
        "The stage waits for as many turns as that takes",
        "Say so in one short line",
        "The model question is a direction, never a line to read out",
        "Do you want to stay with the one we selected?",
        "What they say is really happening is never a thought to question",
        "Options only when they are unsure",
    ):
        assert rule in framework, rule
