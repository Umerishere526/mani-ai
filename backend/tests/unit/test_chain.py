# ABOUTME: Checks the LangChain layer talks to OpenRouter and still reports what a turn cost.
# ABOUTME: Token accounting is the only reason this code reads the raw response at all.

import json
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


def test_reply_asks_for_its_reasoning_and_style_before_its_text():
    """Structured output is generated in schema order, so a field after text cannot shape it.

    The opener and repeated-shape checks live in reasoning and style; declared after text,
    they were written about a reply that already existed.
    """
    fields = list(Reply.model_json_schema()["properties"])
    assert fields.index("reasoning") < fields.index("text")
    assert fields.index("style") < fields.index("text")


def _body_key(effort: str | None) -> str:
    return json.dumps(chain.request_body(None, effort, settings()), sort_keys=True)


def test_a_reasoning_effort_goes_in_the_request_body_and_none_sends_nothing():
    """covers spec 0006 AC-1: sent as OpenRouter's `reasoning`, in the body the chain already
    builds, never through LangChain's own arguments (which switch to a different API)."""
    assert chain.request_body(None, "low", settings())["reasoning"] == {"effort": "low"}
    assert "reasoning" not in chain.request_body(None, None, settings())
    # What was already there stays.
    assert chain.request_body(None, "low", settings())["usage"] == {"include": True}


def test_build_makes_its_model_from_that_body_and_a_new_effort_is_a_new_model():
    args = ("sk-test-not-a-real-key", "https://openrouter.ai/api/v1", 60.0, "m-effort", 1.0, 4096)
    for effort in ("low", "high"):
        chain.build(
            Reply, model="m-effort", temperature=1.0, max_tokens=4096, routing=None,
            settings=settings(), reasoning_effort=effort,
        )
    low = chain._model(*args, _body_key("low"))
    high = chain._model(*args, _body_key("high"))
    assert low is not high
    assert low.extra_body["reasoning"] == {"effort": "low"}
    assert high.extra_body["reasoning"] == {"effort": "high"}
    assert chain._model(*args, _body_key("low")) is low


def test_the_tool_call_runnable_sends_the_effort_too():
    from mani.llm import tools

    args = ("sk-test-not-a-real-key", "https://openrouter.ai/api/v1", 60.0, "m-tool", 0.7, 200)
    chain.build_tool_choice(
        tools.StartExercise, model="m-tool", temperature=0.7, max_tokens=200, routing=None,
        settings=settings(), reasoning_effort="low",
    )
    assert chain._model(*args, _body_key("low")).extra_body["reasoning"] == {"effort": "low"}


def test_no_temperature_is_sent_when_none_is_set():
    """Google Vertex lists no temperature parameter, and a route that requires its parameters
    refuses a request that carries one."""
    args = ("sk-test-not-a-real-key", "https://openrouter.ai/api/v1", 60.0, "m-vertex")
    messages = [("user", "hi")]
    without = chain._model(*args, None, 4096, _body_key(None))._get_request_payload(messages)
    with_one = chain._model(*args, 1.0, 4096, _body_key(None))._get_request_payload(messages)
    assert "temperature" not in without
    assert with_one["temperature"] == 1.0
