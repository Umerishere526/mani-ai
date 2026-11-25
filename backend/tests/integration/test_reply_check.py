# ABOUTME: Checks the reply check end to end: a reading said as fact is rewritten before the reply is stored and sent,
# ABOUTME: a safety turn is never sent through it, and a rewrite that does more than it may is not used.
from __future__ import annotations

import uuid

import pytest

from mani.chat import check
from mani.config import get_settings
from mani.db import llm_calls
from mani.llm import client
from tests.integration.fixtures import ScriptedModel, said, send, start



class CheckingModel(ScriptedModel):
    """The scripted chat model, with the reply check answered by `checked` (its text and what it changed)."""

    def __init__(self, reply, checked: tuple[str, list[str]]) -> None:
        super().__init__(reply)
        self.checked = checked
        self.checks = 0

    async def __call__(self, messages, schema, **kwargs):
        if schema is check.Checked:
            self.checks += 1
            text, changed = self.checked
            return client.Call(value=check.Checked(text=text, changed=changed), model="test/model",
                               usage=llm_calls.Usage(), latency_ms=1, call_id=uuid.uuid4())
        return await super().__call__(messages, schema, **kwargs)


@pytest.fixture
def checking(monkeypatch):
    monkeypatch.setattr(get_settings(), "reply_check_enabled", True)

    def install(reply, checked) -> CheckingModel:
        model = CheckingModel(reply, checked)
        monkeypatch.setattr(client, "complete", model)
        return model

    return install


async def test_a_reading_said_as_fact_is_rewritten_before_it_is_sent(alice, checking):
    """muhammad's tester (2026-11-25): "That's not much to ask of a friend" took the person's side as fact."""
    model = checking(said("You wanted her to say sorry. That's not much to ask of a friend.", question={
        "latest": "answer", "ask": "What would you need to hear from her?"}),
        ("You wanted her to say sorry.", ["That's not much to ask of a friend."]))
    thread = await start(alice)
    turn = await send(alice, thread.id, "i want her to say sorry")
    assert model.checks == 1
    assert turn.content.startswith("You wanted her to say sorry.") and "much to ask" not in turn.content
    assert turn.trace["reply_checked"] == ["That's not much to ask of a friend."]


async def test_a_safety_turn_is_never_checked(alice, checking):
    model = checking(said("I'm worried about you. Please call 988 now.", level="danger", safety={
        "level": "danger", "about": "themselves"}), ("Please call now.", ["x"]))
    thread = await start(alice)
    await send(alice, thread.id, "i want to die")
    assert model.checks == 0


async def test_a_rewrite_that_adds_a_question_is_not_used(alice, checking):
    checking(said("That stings, being left out."), ("What hurt most about being left out?", ["That stings."]))
    thread = await start(alice)
    turn = await send(alice, thread.id, "they went without me")
    assert turn.content.startswith("That stings, being left out.") and "reply_checked" not in turn.trace
