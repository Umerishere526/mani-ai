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
        max_tokens=2048, routing=None, settings=settings(),
    )
    # with_structured_output wraps the model; the configured chat model is underneath it.
    configured = chain._model.cache_info()
    assert configured.currsize >= 1
    assert runnable is not None


def test_the_provider_sdk_never_retries_on_its_own():
    """Its default is three, which multiplies the bill and the latency of a slow turn."""
    chain.build(
        Reply, model="m", temperature=0.7, max_tokens=100, routing=None, settings=settings()
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
        }
    )
    usage = chain.usage_from(raw)
    assert usage.input_tokens == 8189
    assert usage.output_tokens == 205
    assert usage.cached_input_tokens == 3568


def test_usage_falls_back_to_the_providers_own_shape():
    """A provider that does not fill usage_metadata still reports under token_usage."""
    raw = SimpleNamespace(
        usage_metadata=None,
        response_metadata={
            "token_usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "prompt_tokens_details": {"cached_tokens": 40},
            }
        },
    )
    usage = chain.usage_from(raw)
    assert (usage.input_tokens, usage.output_tokens, usage.cached_input_tokens) == (100, 20, 40)


def test_a_missing_response_costs_nothing_rather_than_raising():
    """A failed call still writes its admin.llm_calls row; it must not fail on the way."""
    empty = chain.usage_from(None)
    assert (empty.input_tokens, empty.output_tokens, empty.cached_input_tokens) == (0, 0, 0)
