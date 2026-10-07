# ABOUTME: Checks the voice translation call is routed and configured like every chat call.
# ABOUTME: A transcript is what the person said, so it must reach only the providers chat may.

from types import SimpleNamespace

from mani import stt
from mani.config import Settings


def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql://localhost/none",
        supabase_url="https://example.supabase.co",
        supabase_jwt_secret="secret",
        supabase_service_role_key="service-role-not-a-real-key",
        openrouter_api_key="sk-test-not-a-real-key",
    )


class FakeCompletions:
    """The OpenAI SDK's chat.completions, keeping what it was asked to send."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def create(self, **request):
        self.sent.append(request)
        message = SimpleNamespace(content="Hi, I'm tired.")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


async def translate(monkeypatch) -> dict:
    completions = FakeCompletions()
    monkeypatch.setattr(stt, "_http", lambda _: SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    ))
    assert await stt._translate_to_english("Hola, estoy cansado.", settings()) == "Hi, I'm tired."
    return completions.sent[0]


async def test_a_transcript_goes_only_to_the_providers_chat_may_use(monkeypatch):
    """Unrouted, OpenRouter may send it to any provider serving the model, under that
    provider's own terms - which is exactly what the chat path refuses."""
    provider = (await translate(monkeypatch))["extra_body"]["provider"]
    assert provider["order"] == settings().openrouter_provider_order
    assert provider["data_collection"] == "deny"


async def test_the_translation_says_how_hard_to_think(monkeypatch):
    request = await translate(monkeypatch)
    assert request["extra_body"]["reasoning"] == {"effort": settings().reasoning_effort}
    assert "temperature" not in request
