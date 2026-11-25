# ABOUTME: Checks the reply repair end to end: a closed question or a figure of speech is repaired before the reply is
# ABOUTME: stored and sent, a clean reply and a safety turn make no repair call, and a repair that does more is not used.
from __future__ import annotations

import uuid

import pytest

from mani.chat import check
from mani.config import get_settings
from mani.db import llm_calls
from mani.llm import client
from tests.integration.fixtures import ScriptedModel, said, send, start



class CheckingModel(ScriptedModel):
    """The scripted chat model, with the reply repair answered by `checked` (its text and its question)."""

    def __init__(self, reply, checked: tuple[str, list[str]]) -> None:
        super().__init__(reply)
        self.checked = checked
        self.checks = 0

    async def __call__(self, messages, schema, **kwargs):
        if schema is check.Repaired:
            self.checks += 1
            text, ask = self.checked
            return client.Call(value=check.Repaired(text=text, ask=ask), model="test/model",
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


async def test_an_either_or_question_is_repaired_before_it_is_sent(alice, checking):
    """muhammad's tester (2026-11-25): "that she died, or that the two of you aren't together anymore?"."""
    model = checking(said("Lost her. That can mean more than one thing.", question={
        "latest": "answer", "ask": "Did she die, or are the two of you not together anymore?"}),
        ("Lost her. That can mean more than one thing.", "What happened with her?"))
    thread = await start(alice)
    turn = await send(alice, thread.id, "i lost her")
    assert model.checks == 1 and turn.content.endswith("What happened with her?")
    assert "yes or no" in turn.trace["reply_checked"][0]


async def test_a_clean_reply_makes_no_repair_call(alice, checking):
    model = checking(said("Lost her. That can mean more than one thing.", question={
        "latest": "answer", "ask": "What happened with her?"}), ("x", "y"))
    thread = await start(alice)
    await send(alice, thread.id, "i lost her")
    assert model.checks == 0


async def test_a_safety_turn_is_never_checked(alice, checking):
    model = checking(said("I'm worried about you. Please call 988 now.", level="danger", safety={
        "level": "danger", "about": "themselves"}), ("Please call now.", "Are you safe?"))
    thread = await start(alice)
    await send(alice, thread.id, "i want to die")
    assert model.checks == 0


async def test_a_repair_that_leaves_the_question_closed_is_not_used(alice, checking):
    checking(said("That's hard.", question={"latest": "answer", "ask": "Is she okay?"}), ("That's hard.", "Did she call?"))
    thread = await start(alice)
    turn = await send(alice, thread.id, "my friend is sick")
    assert turn.content.endswith("Is she okay?") and "reply_checked" not in turn.trace
