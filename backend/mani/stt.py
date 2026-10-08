# ABOUTME: Speech-to-text - one call to OpenRouter's /audio/transcriptions endpoint.
# ABOUTME: Same key, same base_url as chat - OpenRouter's own endpoint, not a second provider.

from __future__ import annotations

import logging

import openai

from mani.config import Settings, get_settings
from mani.errors import ErrorCategory, ServiceError
from mani.llm import chain
from mani.prompts import cache, calls

logger = logging.getLogger(__name__)

# Keeps a silent recording, a dropped connection, or a stuck mic from hanging the request
# or costing nothing-but-time on a provider that is briefly slow.
TIMEOUT_SECONDS = 30.0

# Matches FastAPI's own default request body ceiling for this endpoint - rejected here,
# before the bytes are ever handed to the provider, with our own error shape rather than
# a platform-level 413 the client cannot branch on.
MAX_AUDIO_BYTES = 25 * 1024 * 1024

_client: openai.AsyncOpenAI | None = None


def _http(settings: Settings) -> openai.AsyncOpenAI:
    global _client
    if _client is None:
        # The OpenAI SDK is the client because OpenRouter speaks that protocol - same as
        # the chat path in mani/llm/chain.py. base_url pointed at OpenRouter, not OpenAI.
        _client = openai.AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            timeout=TIMEOUT_SECONDS,
        )
    return _client


async def close() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


# Whisper itself has a "translate" task that always outputs English, but it's only
# reachable through OpenAI's separate /v1/audio/translations endpoint - OpenRouter's
# documented /audio/transcriptions takes a `language` hint for transcription accuracy
# only, not a task switch, and returns text in whatever language was spoken (confirmed
# against OpenRouter's own API reference, which lists no translate/task parameter).
# So English-only output is a second, explicit step: one plain chat completion, same
# key and base_url as everything else here, translating whatever Whisper returned. Its
# instruction, model, budget and thinking level are the `voice_translation` prompt row.
TRANSLATION_PROMPT = "voice_translation"


async def _translate_to_english(text: str, settings: Settings) -> str:
    """Best-effort. Falls back to the original transcript rather than failing voice
    input entirely over a translation hiccup - a non-English reply beats none."""
    if not text:
        return text
    try:
        # Inside the try, so a cold cache that cannot reach the database, or a row that is
        # missing or names no level, costs the translation and not the voice input.
        prompt = (await cache.load()).require(TRANSLATION_PROMPT)
        effort = calls.effort_for(prompt, TRANSLATION_PROMPT)
        model = prompt.model_id or settings.default_chat_model
        parameters = prompt.model_parameters
        response = await _http(settings).chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt.content},
                {"role": "user", "content": text},
            ],
            # What they said is health data: the same providers and data policy as every
            # chat call, not whatever OpenRouter would pick for an unrouted request.
            extra_body=chain.request_body(model, settings, prompt.routing, effort=effort),
            **chain.sampling(
                model, parameters.get("temperature", 0), parameters.get("maxTokens", 500)
            ),
        )
        translated = response.choices[0].message.content
        return translated.strip() if translated else text
    except Exception:
        logger.warning("translation to English failed, returning original transcript", exc_info=True)
        return text


async def transcribe(
    audio_bytes: bytes, filename: str, *, settings: Settings | None = None
) -> str:
    """One recording in, its English text out. Raises ServiceError on anything that
    stops the transcription itself; translation failure degrades, it doesn't raise."""
    settings = settings or get_settings()
    if not settings.openrouter_api_key:
        raise ServiceError(
            "OPENROUTER_API_KEY is not set",
            ErrorCategory.CONFIG_ERROR,
            user_message="Voice input is not available right now.",
        )
    if not audio_bytes:
        raise ServiceError(
            "empty audio upload",
            ErrorCategory.INVALID_REQUEST,
            user_message="That recording was empty. Please try again.",
        )
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise ServiceError(
            f"audio upload too large: {len(audio_bytes)} bytes",
            ErrorCategory.INVALID_REQUEST,
            user_message="That recording is too long. Please keep it under a minute.",
        )

    client = _http(settings)
    try:
        result = await client.audio.transcriptions.create(
            model=settings.whisper_model,
            file=(filename, audio_bytes),
        )
    except openai.RateLimitError as exc:
        raise ServiceError(
            f"transcription provider rate limited: {exc}",
            ErrorCategory.RATE_LIMITED,
            retryable=True,
            user_message="Voice input is busy right now. Please try again in a moment.",
        ) from exc
    except openai.APITimeoutError as exc:
        raise ServiceError(
            f"transcription provider timed out: {exc}",
            ErrorCategory.LLM_TIMEOUT,
            retryable=True,
            user_message="That took too long to transcribe. Please try again.",
        ) from exc
    except Exception as exc:
        raise ServiceError(
            f"transcription call failed: {exc}",
            ErrorCategory.LLM_UNAVAILABLE,
            retryable=True,
            user_message="Could not transcribe that. Please try again or type instead.",
        ) from exc

    transcript = result.text.strip()
    return await _translate_to_english(transcript, settings)
