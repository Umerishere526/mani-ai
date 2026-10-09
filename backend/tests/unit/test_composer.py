# ABOUTME: Checks the system prompt's layer order and that a missing layer is not silent.
# ABOUTME: Order is fixed so the large static prefix stays identical and cacheable.

import time
import uuid

import pytest

from mani.chat.techniques import Registry
from mani.config import get_settings
from mani.errors import ServiceError
from mani.llm.schema import Memory
from mani.models.rows import Framework, Profile, TechniqueTried, ThreadSummary
from mani.prompts import composer
from mani.prompts.cache import Config
from tests.seeded import seeded_replies, seeded_tuning

USER = uuid.UUID("a0000000-0000-4000-8000-00000000000a")
THREAD = uuid.UUID("b0000000-0000-4000-8000-00000000000b")


def prompt(name: str, content: str):
    from mani.models.rows import Prompt

    return Prompt(id=uuid.uuid4(), name=name, content=content,
                  model_id="google/gemini-3-flash-preview")


@pytest.fixture
def config() -> Config:
    named = [
        prompt("mani_base", "IDENTITY"),
        prompt("response_format", "FORMAT"),
        prompt("title_generation", "TITLE"),
    ]
    return Config(
        prompts={p.name: p for p in named},
        registry=Registry([]),
        loaded_at=time.monotonic(),
        replies=seeded_replies(),
        tuning=seeded_tuning(),
    )


def test_the_layers_come_in_a_fixed_order(config):
    built = composer.compose(
        config,
        Profile(user_id=USER, nickname="Al", topics=["anxiety"], support_style="reflective"),
        should_generate_title=True,
        offered=["abcde"],
        summary=ThreadSummary(
            thread_id=THREAD, user_id=USER, summary="Talked about work.",
            current_issue="Whether to raise a pattern of missed credit with their manager.",
            techniques_tried=[TechniqueTried(name="abcde", helpful=True)],
        ),
    )
    assert [name for name, _ in built.layers] == [
        "mani_base", "response_format", "user_context", "title_generation",
        "techniques_used", "summary",
    ]
    summary_text = dict(built.layers) and built.text
    assert summary_text.index("Whether to raise a pattern") < summary_text.index("Talked about work.")


def test_optional_layers_are_simply_absent(config):
    built = composer.compose(config, None)
    assert [name for name, _ in built.layers] == ["mani_base", "response_format"]


def framework(id: str, name: str, body: str = "Starts when: x", summary: str = "s") -> Framework:
    return Framework(id=id, name=name, summary=summary, body=body, phases=["offering"])


ABCDE_LINES = (
    "Starts when: you have learned the event and what it came to mean.\n"
    "Sounds like: \"so I must be\".\n"
    "Skip when: one quick thought (thought_reframe).\n"
    "Stages: activate (what happened) > closing (how it sits now)\n"
    "Ends when: they hold a fairer belief.\n"
    "Never: invent evidence.\n"
    "Never: question whether abuse was real."
)


def test_the_framework_index_carries_each_frameworks_description_then_its_seven_lines():
    """The lines are the model's whole view of a framework, written and checked in its file, so
    the index renders them as they are. The client's description stands above them as its own
    line, and a framework with none gets no empty line."""
    registry = Registry([
        framework("abcde", "ABCDE", ABCDE_LINES, summary="These questions help you test a belief."),
        framework("dbt_stop", "DBT STOP", "Starts when: they are about to act.", summary=""),
    ])

    index = composer.framework_index(registry)

    assert (
        "## ABCDE (`abcde`)\nDescription: These questions help you test a belief.\n"
        f"{ABCDE_LINES}\n\n## DBT STOP (`dbt_stop`)\nStarts when: they are about to act."
    ) in index
    assert "Description: \n" not in index
    for removed in ("Use it when", "Telling them apart", "Never offer one when", "Finding the fit"):
        assert removed not in index


def test_a_framework_index_with_nothing_to_list_is_left_out_entirely():
    """An empty registry is already logged as a misconfiguration at load. The prompt should
    not carry an empty table announcing frameworks that do not exist."""
    assert composer.framework_index(Registry([])) is None


def test_the_generated_index_reaches_the_composed_prompt(config):
    with_frameworks = Config(
        prompts=config.prompts,
        registry=Registry([framework("abcde", "ABCDE")]),
        loaded_at=time.monotonic(),
        replies=config.replies,
        tuning=config.tuning,
    )
    built = composer.compose(with_frameworks, None)

    assert [name for name, _ in built.layers] == [
        "mani_base", "framework_index", "response_format"
    ]
    assert "`abcde`" in built.text


def test_onboarding_answers_reach_the_prompt(config):
    """The reference read only the nickname, so topics shaped nothing. The support style is
    not here on purpose: it is resolved per turn and named in [ctx], so that a conversation
    which chose differently is not contradicted by the profile's answer."""
    built = composer.compose(
        config,
        Profile(user_id=USER, nickname="Al", topics=["burnout", "boundaries"],
                support_style="direct"),
    )
    assert "burnout, boundaries" in built.text
    assert "style of support" not in built.text


def test_a_missing_required_layer_is_refused_not_dropped(config):
    """The reference pushed each layer only `if (prompt)`, so deactivating one in the
    portal quietly changed Mani's personality instead of failing."""
    without_format = Config(
        prompts={k: v for k, v in config.prompts.items() if k != "response_format"},
        registry=config.registry,
        loaded_at=config.loaded_at,
        replies=config.replies,
        tuning=config.tuning,
    )
    with pytest.raises(ServiceError):
        composer.compose(without_format, None)


def test_the_reply_commits_to_a_lean_before_it_writes_the_text():
    """Structured output is generated in schema order, so a lean declared after the text could
    only describe a reply already written."""
    from mani.llm.schema import Reply

    fields = list(Reply.model_fields)
    assert fields.index("heading_toward") < fields.index("text")
    assert fields.index("style") < fields.index("heading_toward")


def test_what_is_remembered_across_chats_reaches_the_prompt_after_the_static_layers(config):
    """After the per-user context, never before the static layers: the cached prefix has to
    stay byte-identical for everyone."""
    remembered = Memory(
        low_times=["feels low on Sunday evenings, because of work"],
        what_helps=["walking the dog"],
    )
    profile = Profile(user_id=uuid.uuid4(), nickname="Sam")
    built = composer.compose(config, profile, memory=remembered)

    names = [name for name, _ in built.layers]
    assert names.index("user_memory") == names.index("user_context") + 1
    assert (
        "## Memory\nlow_times: feels low on Sunday evenings, because of work\n"
        "what_helps: walking the dog"
    ) in built.text


def test_an_empty_memory_adds_nothing(config):
    built = composer.compose(config, None, memory=Memory())
    assert "user_memory" not in [name for name, _ in built.layers]


def test_the_index_hands_over_the_description_on_one_line_and_says_nothing_else():
    """The offer's words are the seeded offer's, not the model's, so the index carries only its
    heading, each framework's heading, the description and the seven lines."""
    helps = Framework(
        id="abcde", name="ABCDE", body="b", phases=["offering"],
        summary="This framework helps you separate what happened\nfrom what you told yourself about it.",
    )
    index = composer.framework_index(Registry([helps]))
    assert index == (
        "# Framework Index\n\n## ABCDE (`abcde`)\n"
        "Description: This framework helps you separate what happened "
        "from what you told yourself about it.\nb"
    )


def test_the_current_issue_stays_visible_even_without_a_prose_summary_yet():
    """A thread just long enough for its first fold may have the issue but not much prose
    yet - the issue is what must never go missing."""
    layer = composer.summary_layer(
        ThreadSummary(thread_id=THREAD, user_id=USER, current_issue="Freezing before a talk.")
    )
    assert layer is not None
    assert "Freezing before a talk." in layer


def test_the_per_user_layers_are_headings_and_keyed_data_only(config):
    """Every sentence about what a layer means lives in response_format.md, so the code sends
    only the layer's heading and `key: value` or `- id` lines."""
    built = composer.compose(
        config,
        Profile(user_id=USER, nickname="Al", topics=["burnout", "boundaries"]),
        offered=["abcde", "dbt_stop"],
        summary=ThreadSummary(
            thread_id=THREAD, user_id=USER, summary="Talked about work.",
            current_issue="Missed credit at work.",
            techniques_tried=[
                TechniqueTried(name="abcde", helpful=True),
                TechniqueTried(name="breathing", helpful=False),
            ],
        ),
        memory=Memory(themes=["work", "sleep"], how_they_talk=["prefers short replies"]),
    )
    layers = built.text.split("\n\n")[2:]
    assert layers == [
        "## User Context\nnickname: Al\ntopics: burnout, boundaries",
        "## Memory\nthemes: work; sleep\nhow_they_talk: prefers short replies",
        "## Techniques Already Offered\n- abcde\n- dbt_stop",
        "## Conversation Context\ncurrent_issue: Missed credit at work.\n"
        "summary: Talked about work.\ntechniques_tried: abcde (helpful), breathing (not_helpful)",
    ]
    assert {layer.split("\n")[0] for layer in layers} <= set(composer.LAYER_HEADINGS.values())


def test_a_summary_with_nothing_in_it_adds_no_layer():
    assert composer.summary_layer(ThreadSummary(thread_id=THREAD, user_id=USER)) is None


def test_the_debug_layer_is_its_own_row_and_only_in_debug_mode(config, monkeypatch):
    with_debug = Config(
        prompts=config.prompts | {"debug": prompt("debug", "# Debug\nSAY WHY")},
        registry=config.registry, loaded_at=config.loaded_at,
        replies=config.replies, tuning=config.tuning,
    )
    assert "debug" not in [name for name, _ in composer.compose(with_debug, None).layers]

    monkeypatch.setattr(get_settings(), "ai_debug_mode", True)
    built = composer.compose(with_debug, None)
    assert [name for name, _ in built.layers][-1] == "debug"
    assert built.text.endswith("# Debug\nSAY WHY")


def test_debug_mode_without_its_row_leaves_the_layer_out_and_says_so(config, monkeypatch, caplog):
    monkeypatch.setattr(get_settings(), "ai_debug_mode", True)
    with caplog.at_level("WARNING", logger="mani.prompts.composer"):
        built = composer.compose(config, None)
    assert "debug" not in [name for name, _ in built.layers]
    assert [r.getMessage() for r in caplog.records] == [
        "AI_DEBUG_MODE is on but the debug prompt is missing or inactive"
    ]
