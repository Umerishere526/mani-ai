# ABOUTME: Checks the voice translation call is routed and configured like every chat call.
# ABOUTME: A transcript is what the person said, so it must reach only the providers chat may.

import logging
import time
import uuid
from types import SimpleNamespace

from mani import stt
from mani.chat.techniques import Registry
from mani.config import Settings
from mani.llm import chain
from mani.models.rows import Prompt
from mani.prompts.cache import Config
from scripts.seed import PROMPTS_DIR, parse_prompt

SAID = "Hola, estoy cansado."


def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql://localhost/none",
        supabase_url="https://example.supabase.co",
        supabase_jwt_secret="secret",
        supabase_service_role_key="service-role-not-a-real-key",
        openrouter_api_key="sk-test-not-a-real-key",
    )


def seeded_row(**changes) -> Prompt:
    """The voice_translation row as the seed writes it from the authored file."""
    authored = parse_prompt(PROMPTS_DIR / "voice_translation.md")
    row = Prompt(
        id=uuid.UUID(authored["id"]), name=authored["name"], content=authored["content"],
        model_id=authored["model_id"], model_parameters=authored["model_parameters"],
    )
    return row.model_copy(update=changes)


class FakeCompletions:
    """The OpenAI SDK's chat.completions, keeping what it was asked to send."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def create(self, **request):
        self.sent.append(request)
        message = SimpleNamespace(content="Hi, I'm tired.")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def install(monkeypatch, *rows: Prompt) -> FakeCompletions:
    completions = FakeCompletions()
    monkeypatch.setattr(stt, "_http", lambda _: SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    ))
    config = Config(
        prompts={row.name: row for row in rows}, registry=Registry([]),
        loaded_at=time.monotonic(),
    )

    async def load() -> Config:
        return config

    monkeypatch.setattr(stt.cache, "load", load)
    return completions


async def translate(monkeypatch) -> dict:
    completions = install(monkeypatch, seeded_row())
    assert await stt._translate_to_english(SAID, settings()) == "Hi, I'm tired."
    return completions.sent[0]


async def test_a_transcript_goes_only_to_the_providers_chat_may_use(monkeypatch):
    """Unrouted, OpenRouter may send it to any provider serving the model, under that
    provider's own terms - which is exactly what the chat path refuses."""
    provider = (await translate(monkeypatch))["extra_body"]["provider"]
    assert provider["order"] == settings().openrouter_provider_order
    assert provider["data_collection"] == "deny"


async def test_the_translation_is_the_one_its_row_describes(monkeypatch):
    """Instruction, thinking level and reply budget all come from the voice_translation row,
    and the seeded row asks for exactly what the call sent before it had one."""
    request = await translate(monkeypatch)
    assert request["messages"][0] == {"role": "system", "content": seeded_row().content}
    assert request["messages"][1] == {"role": "user", "content": SAID}
    assert request["model"] == "openai/gpt-6-luna"
    assert request["extra_body"]["reasoning"] == {"effort": "high"}
    assert request["max_completion_tokens"] == 500 + chain.REASONING_ALLOWANCE_TOKENS
    assert "temperature" not in request


async def test_a_row_with_no_level_costs_the_translation_not_the_voice_input(
    monkeypatch, caplog
):
    """Nothing is sent at a level nobody chose; the person still gets their own words back,
    and the warning names the row without repeating what they said."""
    completions = install(monkeypatch, seeded_row(model_parameters={"maxTokens": 500}))

    with caplog.at_level(logging.WARNING, logger="mani.stt"):
        assert await stt._translate_to_english(SAID, settings()) == SAID

    assert completions.sent == []
    assert "voice_translation" in caplog.text
    assert SAID not in caplog.text
