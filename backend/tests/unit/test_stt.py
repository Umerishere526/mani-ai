# ABOUTME: Checks the voice translation call is routed and configured like every chat call.
# ABOUTME: A transcript is what the person said, so it must reach only the providers chat may.

from types import SimpleNamespace

import pytest

from mani import stt
from mani.config import Settings
from mani.errors import ErrorCategory, ServiceError


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
    assert provider["only"] == settings().openrouter_providers
    assert provider["data_collection"] == "deny"
    assert provider["zdr"] is True


class FakeTranscriptions:
    """The OpenAI SDK's audio.transcriptions, keeping what it was asked to send."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def create(self, **request):
        self.sent.append(request)
        return SimpleNamespace(text="Hi, I'm tired.")


async def test_a_recording_goes_only_to_endpoints_that_keep_no_data(monkeypatch):
    """The recording is what they said, sent before any translation, so it carries the same data policy."""
    transcriptions = FakeTranscriptions()
    monkeypatch.setattr(stt, "_http", lambda _: SimpleNamespace(
        audio=SimpleNamespace(transcriptions=transcriptions), chat=SimpleNamespace(completions=FakeCompletions()),
    ))
    assert await stt.transcribe(b"audio", "clip.webm", settings=settings()) == "Hi, I'm tired."
    assert transcriptions.sent[0]["extra_body"]["provider"] == {"data_collection": "deny", "zdr": True}


async def test_the_translation_says_how_hard_to_think(monkeypatch):
    request = await translate(monkeypatch)
    assert request["extra_body"]["reasoning"] == {"effort": settings().reasoning_effort}
    assert "temperature" not in request


async def test_a_recording_vercel_would_refuse_is_refused_in_our_own_shape_before_the_provider(monkeypatch):
    """Vercel turns away a request body past 4.5 MB with a 413 of its own; the backend's ceiling sits below that, so
    the client gets the one error shape it branches on, and nothing reaches the provider."""
    transcriptions = FakeTranscriptions()
    monkeypatch.setattr(stt, "_http", lambda _: SimpleNamespace(audio=SimpleNamespace(transcriptions=transcriptions)))
    assert stt.MAX_AUDIO_BYTES < 4.5 * 1000 * 1000

    with pytest.raises(ServiceError) as refused:
        await stt.transcribe(b"a" * (stt.MAX_AUDIO_BYTES + 1), "clip.m4a", settings=settings())
    assert refused.value.category is ErrorCategory.INVALID_REQUEST and transcriptions.sent == []
