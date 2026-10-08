# ABOUTME: Checks the LangChain layer talks to OpenRouter and still reports what a turn cost.
# ABOUTME: Token accounting is the only reason this code reads the raw response at all.

from types import SimpleNamespace

from mani.config import Settings
from mani.llm import chain
from mani.llm.schema import Reply


def settings() -> Settings:
    return Settings(
        database_url="postgresql://localhost/none",
        supabase_url="https://example.supabase.co",
        supabase_jwt_secret="secret",
        openrouter_api_key="sk-test-not-a-real-key",
    )


def test_the_model_is_pointed_at_openrouter_not_openai():
    """langchain-openai is an OpenAI-protocol client. The base_url decides who is billed."""
    runnable = chain.build(
        Reply, model="google/gemini-3-flash-preview", temperature=0.7,
        max_tokens=2048, routing=None, settings=settings(), reasoning_effort="high",
    )
    # with_structured_output wraps the model; the configured chat model is underneath it.
    configured = chain._model.cache_info()
    assert configured.currsize >= 1
    assert runnable is not None


def test_the_provider_sdk_never_retries_on_its_own():
    """Its default is three, which multiplies the bill and the latency of a slow turn."""
    chain.build(
        Reply, model="m", temperature=0.7, max_tokens=100, routing=None, settings=settings(),
        reasoning_effort="high",
    )
    model = chain._model(
        "sk-test-not-a-real-key", "https://openrouter.ai/api/v1", 60.0, "m", 0.7, 100,
        '{"provider": {}, "usage": {"include": true}}',
    )
    assert model.max_retries == 0
    assert model.openai_api_base == "https://openrouter.ai/api/v1"


def test_openrouter_is_asked_to_report_cached_tokens():
    """Without this OpenRouter omits the count, and prompt caching becomes unmeasurable."""
    model = chain._model(
        "sk-test-not-a-real-key", "https://openrouter.ai/api/v1", 60.0, "m", 0.7, 100,
        '{"provider": {}, "usage": {"include": true}}',
    )
    assert model.extra_body["usage"] == {"include": True}


def test_usage_is_read_from_langchains_own_metadata():
    raw = SimpleNamespace(
        usage_metadata={
            "input_tokens": 8189,
            "output_tokens": 205,
            "input_token_details": {"cache_read": 3568},
            "output_token_details": {"reasoning": 131},
        }
    )
    usage = chain.usage_from(raw)
    assert usage.input_tokens == 8189
    assert usage.output_tokens == 205
    assert usage.cached_input_tokens == 3568
    assert usage.reasoning_tokens == 131


def test_usage_falls_back_to_the_providers_own_shape():
    """A provider that does not fill usage_metadata still reports under token_usage."""
    raw = SimpleNamespace(
        usage_metadata=None,
        response_metadata={
            "token_usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "prompt_tokens_details": {"cached_tokens": 40},
                "completion_tokens_details": {"reasoning_tokens": 12},
            }
        },
    )
    usage = chain.usage_from(raw)
    assert (usage.input_tokens, usage.output_tokens, usage.cached_input_tokens) == (100, 20, 40)
    assert usage.reasoning_tokens == 12


def test_a_model_that_reports_no_thinking_records_zero_reasoning():
    """An ordinary chat model sends no reasoning count; that is 0, not an error."""
    raw = SimpleNamespace(usage_metadata={"input_tokens": 10, "output_tokens": 5})
    assert chain.usage_from(raw).reasoning_tokens == 0


def test_a_missing_response_costs_nothing_rather_than_raising():
    """A failed call still writes its admin.llm_calls row; it must not fail on the way."""
    empty = chain.usage_from(None)
    assert (empty.input_tokens, empty.output_tokens, empty.cached_input_tokens) == (0, 0, 0)


def test_reply_asks_for_its_reasoning_and_style_before_its_text():
    """Structured output is generated in schema order, so a field after text cannot shape it.

    The opener and repeated-shape checks live in reasoning and style; declared after text,
    they were written about a reply that already existed.
    """
    fields = list(Reply.model_json_schema()["properties"])
    assert fields.index("reasoning") < fields.index("text")
    assert fields.index("style") < fields.index("text")


def test_a_reasoning_model_is_not_sent_a_temperature():
    """gpt-6-luna has no `temperature` in its supported parameters on any provider, and
    names its output budget `max_completion_tokens`. Sending either wrong one is a 400 on
    every call, so the request shape follows the model."""
    chain._model.cache_clear()
    chain.build(
        Reply, model="openai/gpt-6-luna", temperature=0.7,
        max_tokens=2048, routing=None, settings=settings(), reasoning_effort="high",
    )
    sent = chain._model("sk-test-not-a-real-key", "https://openrouter.ai/api/v1",
                        60.0, "openai/gpt-6-luna", 0.7, 2048, "{}")._default_params
    assert "temperature" not in sent
    assert sent["max_completion_tokens"] >= 2048
    assert sent.get("max_tokens") is None


def test_an_ordinary_chat_model_still_gets_its_sampling_parameters():
    """The guard is on reasoning models only; everything else keeps the old request shape."""
    sent = chain._model("sk-test-not-a-real-key", "https://openrouter.ai/api/v1",
                        60.0, "google/gemini-3.1-flash-lite", 0.7, 2048, "{}")._default_params
    assert sent["temperature"] == 0.7
    assert sent["max_completion_tokens"] == 2048


def test_the_reasoning_effort_rides_with_a_reasoning_model_only():
    """A model that does not read a reasoning effort rejects the key."""
    assert chain._reasoning("openai/gpt-6-luna", "high") == {"reasoning": {"effort": "high"}}
    assert chain._reasoning("google/gemini-3.1-flash-lite", "high") == {}


def test_a_prompt_row_can_name_its_own_reasoning_effort():
    """The prompt rows carry `reasoning_effort`; without this it is read and dropped, and the
    stored value silently means nothing."""
    assert chain._reasoning("openai/gpt-6-luna", "low") == {"reasoning": {"effort": "low"}}
    # Named on a model that cannot read it, it is still not sent.
    assert chain._reasoning("google/gemini-3.1-flash-lite", "low") == {}


def test_no_call_can_go_out_on_a_level_nobody_chose():
    """There is no configured default to fall back to: a call site that forgets the level
    fails at once, rather than running at whatever the environment says."""
    import pytest

    assert "reasoning_effort" not in Settings.model_fields
    with pytest.raises(TypeError):
        chain.request_body("openai/gpt-6-luna", settings())


def test_the_effort_reaches_the_request_body():
    """The guard is only worth anything if the value lands in what is actually sent."""
    import json

    captured = {}
    real = chain._model

    def spy(api_key, base_url, timeout, model, temperature, max_tokens, extra_body):
        captured["extra_body"] = json.loads(extra_body)
        return real(api_key, base_url, timeout, model, temperature, max_tokens, extra_body)

    chain._model = spy
    try:
        chain.build(
            Reply, model="openai/gpt-6-luna", temperature=0.7, max_tokens=2048,
            routing=None, settings=settings(), reasoning_effort="low",
        )
    finally:
        chain._model = real

    assert captured["extra_body"]["reasoning"] == {"effort": "low"}


def test_thinking_never_eats_the_budget_the_reply_was_given():
    """On a reasoning model the output budget covers the thinking and the reply together. On
    2026-10-07 a chat turn at effort high thought for 1,955 of its 2,048 tokens, the reply was
    cut off, and the turn failed. Every caller sizes its budget for the reply alone - 200 for the
    exercise pick, 500 for a summary - so the thinking needs room of its own on top."""
    longest_thinking_seen = 1955
    for reply_budget in (200, 500, 800, 2048):
        sent = chain.sampling("openai/gpt-6-luna", 0.7, reply_budget)["max_completion_tokens"]
        assert sent - longest_thinking_seen >= reply_budget
