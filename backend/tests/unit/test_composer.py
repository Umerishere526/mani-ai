# ABOUTME: Checks the system prompt's layer order and that a missing layer is not silent.
# ABOUTME: Order is fixed so the large static prefix stays identical and cacheable.

import time
import uuid

import pytest

from mani.chat.techniques import Registry
from mani.errors import ServiceError
from mani.llm.schema import Memory
from mani.models.rows import Framework, Profile, TechniqueTried, ThreadSummary
from mani.prompts import composer
from mani.prompts.cache import Config

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


def framework(id: str, name: str, indication: str, distinctions: dict) -> Framework:
    return Framework(
        id=id, name=name, summary="s", body="b", phases=["offering"],
        activation={"central_indication": indication, "distinctions": distinctions},
    )


def test_the_framework_index_is_built_from_the_registry_not_written_by_hand():
    """Every line of it already exists on admin.frameworks. A prose copy beside that is a
    second source of truth, and it drifts the first time somebody edits one and not the
    other - so adding a framework must need no prompt edit at all."""
    registry = Registry([
        framework("abcde", "ABCDE", "A specific event triggered a belief.",
                  {"thought_reframe": "Reframe when one thought is already clear."}),
        framework("dbt_stop", "DBT STOP", "The user is about to act.", {}),
    ])

    index = composer.framework_index(registry)

    assert "| ABCDE | `abcde` | A specific event triggered a belief. |" in index
    assert "| DBT STOP | `dbt_stop` | The user is about to act. |" in index
    # thought_reframe is not in this registry, so it falls back to a readable form of the
    # id rather than a display name it has no way to look up.
    assert "**ABCDE or thought reframe** — Reframe when one thought is already clear." in index


def test_a_distinction_written_from_both_sides_is_emitted_once():
    """Every framework file explains itself against its neighbours, so each pair is written
    twice across the set, and 'continue chatting instead' is written in all six. Correct in
    a file a clinician reads, pure waste in a prompt paid for on every turn."""
    registry = Registry([
        framework("abcde", "ABCDE", "An event and a belief.", {
            "thought_reframe": "ABCDE goes deeper.",
            "continued_conversation": "Keep talking when the issue is unclear.",
        }),
        framework("thought_reframe", "Thought Reframe", "One painful thought.", {
            "abcde": "Reframe is the shorter one.",
            "continued_conversation": "Keep talking when the thought is unclear.",
        }),
    ])

    index = composer.framework_index(registry)

    # The pair appears once, from whichever side was reached first - not twice.
    assert index.count("ABCDE or Thought Reframe") == 1
    assert "Thought Reframe or ABCDE" not in index
    assert index.count("continued conversation") == 1


def test_a_framework_index_with_nothing_to_list_is_left_out_entirely():
    """An empty registry is already logged as a misconfiguration at load. The prompt should
    not carry an empty table announcing frameworks that do not exist."""
    assert composer.framework_index(Registry([])) is None


def test_the_generated_index_reaches_the_composed_prompt(config):
    with_frameworks = Config(
        prompts=config.prompts,
        registry=Registry([framework("abcde", "ABCDE", "A specific event.", {})]),
        loaded_at=time.monotonic(),
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
    )
    with pytest.raises(ServiceError):
        composer.compose(without_format, None)


def test_the_framework_index_carries_each_frameworks_contraindications():
    """The lines that protect the person - abuse, a medical cause, a protective action -
    were authored in every framework file and reached nothing. They are the one part of a
    framework the model must know before it offers, not after."""
    stop = Framework(
        id="dbt_stop", name="DBT STOP", summary="s", body="b", phases=["offering"],
        activation={
            "central_indication": "about to act",
            "contraindications": ["The action itself is protective - leaving, calling for help"],
        },
    )
    index = composer.framework_index(Registry([stop]))
    assert "Never offer one when" in index
    assert "**DBT STOP**: The action itself is protective - leaving, calling for help" in index


def test_the_framework_index_says_what_each_one_needs_to_find_out():
    """Questions can follow the person's feeling and still head somewhere only if the model
    can see what each set of questions needs to learn before it is the right offer."""
    act = Framework(
        id="act_choice_point", name="ACT Choice Point", summary="s", body="b", phases=["offering"],
        activation={
            "central_indication": "cannot change it",
            "to_find_out": ["what they cannot control", "what it pulls them toward"],
        },
    )
    index = composer.framework_index(Registry([act]))
    assert "## Finding the fit" in index
    assert "- **ACT Choice Point**: what they cannot control; what it pulls them toward" in index


def test_every_shipped_framework_says_what_it_needs_to_find_out():
    from scripts.seed import FRAMEWORKS_DIR, parse_framework

    for path in sorted(FRAMEWORKS_DIR.glob("*.md")):
        found = parse_framework(path)["activation"].get("to_find_out") or []
        assert len(found) >= 3, f"{path.name} needs at least three things to find out"


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
    assert "feels low on Sunday evenings, because of work" in built.text
    assert "walking the dog" in built.text
    assert "never say you remember" in built.text.lower()


def test_an_empty_memory_adds_nothing(config):
    built = composer.compose(config, None, memory=Memory())
    assert "user_memory" not in [name for name, _ in built.layers]


def test_the_index_never_names_it_to_the_person_nor_hands_over_its_description():
    """The client: never tell the person the framework's name. Its description reaches the model
    only when they ask to hear more, so the index keeps it out."""
    helps = Framework(
        id="abcde", name="ABCDE", body="b", phases=["offering"],
        summary="This framework helps you separate what happened from what you told yourself about it.",
        activation={"central_indication": "a specific event"},
    )
    index = composer.framework_index(Registry([helps]))
    assert "separate what happened from what you told yourself about it" not in index
    assert 'never say its name, its id, or the word "framework"' in index
    assert "`[ctx]` gives you what it looks at" in index


def test_the_current_issue_stays_visible_even_without_a_prose_summary_yet():
    """A thread just long enough for its first fold may have the issue but not much prose
    yet - the issue is what must never go missing."""
    layer = composer.summary_layer(
        ThreadSummary(thread_id=THREAD, user_id=USER, current_issue="Freezing before a talk.")
    )
    assert layer is not None
    assert "Freezing before a talk." in layer


def test_the_index_lists_what_each_framework_needs_to_know_and_no_offer_message_number():
    """The client's two to four exchanges are a range, not a count (spec 0010, AC-3), so the
    index names what each needs and never a message to wait for."""
    abcde = Framework(
        id="abcde", name="ABCDE", summary="s", body="b", phases=["offering"],
        activation={"central_indication": "x", "to_find_out": ["the event", "what it meant"]},
    )
    index = composer.framework_index(Registry([abcde]))
    assert "- **ABCDE**: the event; what it meant" in index
    assert "offer it only from" not in index and "What makes each fit" not in index


def test_no_prompt_names_a_field_the_reply_no_longer_has():
    from scripts.seed import PROMPTS_DIR

    for path in sorted(PROMPTS_DIR.glob("*.md")):
        text = path.read_text()
        for removed in ("heading_toward", "offer_fit", "framework_shortlist"):
            assert removed not in text, f"{path.name} names {removed}"


def test_nothing_the_model_reads_offers_a_nearest_fit_or_says_an_offer_is_due():
    """covers spec 0005 AC-16: only a full fit is offered, and nothing pushes an offer."""
    from scripts.seed import FRAMEWORKS_DIR, PROMPTS_DIR, parse_framework

    shipped = [Framework.model_validate(parse_framework(p)) for p in sorted(FRAMEWORKS_DIR.glob("*.md"))]
    texts = {p.name: p.read_text() for p in sorted(PROMPTS_DIR.glob("*.md"))}
    texts["framework_index"] = composer.framework_index(Registry(shipped))
    for name, text in texts.items():
        for pushed in ("closest_fit", "closest fit", "nearest", "an offer is due", "offer is due"):
            assert pushed not in text.lower(), f"{name} says {pushed}"
