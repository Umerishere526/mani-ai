# ABOUTME: Checks the system prompt's layer order, that every turn starts with the same voice, and that
# ABOUTME: a missing layer is not silent. Order is fixed so the static prefix stays cacheable.

import time
import uuid
from contextlib import asynccontextmanager

import pytest

from mani.chat.techniques import Registry
from mani.errors import ServiceError
from mani.llm.schema import Memory
from mani.models.rows import Framework, Profile, TechniqueTried, ThreadSummary
from mani.prompts import cache, composer
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
        prompt("voice", "VOICE"),
        prompt("conversation", "CONVERSATION"),
        prompt("framework", "FRAMEWORK"),
        prompt("moments", "MOMENTS"),
        prompt("title_generation", "TITLE"),
    ]
    return Config(
        prompts={p.name: p for p in named},
        registry=Registry([]),
        loaded_at=time.monotonic(),
    )


def test_the_layers_come_in_a_fixed_order(config):
    built = composer.compose_moment(
        config,
        Profile(user_id=USER, nickname="Al", topics=["anxiety"], support_style="reflective"),
        should_generate_title=True,
        offered=["abcde"],
        summary=ThreadSummary(
            thread_id=THREAD, user_id=USER, summary="Talked about work.",
            techniques_tried=[TechniqueTried(name="abcde", helpful=True)],
        ),
    )
    assert [name for name, _ in built.layers] == [
        "voice", "moments", "user_context", "title_generation", "techniques_used", "summary",
    ]


def test_optional_layers_are_simply_absent(config):
    built = composer.compose_moment(config, None)
    assert [name for name, _ in built.layers] == ["voice", "moments"]


@pytest.mark.parametrize("compose", [composer.compose_conversation, composer.compose_framework, composer.compose_moment])
def test_every_turn_starts_with_the_same_voice_so_it_caches_once(config, compose):
    """muhammad, 2026-10-27: the chat, a framework's stages and the moments between them all speak in voice.md,
    which carries the three styles, so no turn is composed from a style file of its own."""
    built = compose(config, None)
    assert built.text.startswith("VOICE\n\n")
    assert not any(name in ("mani_base", "response_format", "style") for name, _ in built.layers)
    assert composer.model_settings(config)[0] == "google/gemini-3-flash-preview"


async def test_a_missing_prompt_row_is_refused_when_the_prompts_load(config, monkeypatch):
    """A deactivated part would otherwise surface mid-conversation, as a turn that fails in that moment only."""
    import mani.db.pool as pool_module

    @asynccontextmanager
    async def fake_as_admin():
        yield object()

    async def active_prompts(conn):
        return [p for name, p in config.prompts.items() if name != "moments"]

    async def active_frameworks(conn):
        return []

    monkeypatch.setattr(pool_module, "as_admin", fake_as_admin)
    monkeypatch.setattr(cache.config_tables, "list_active_prompts", active_prompts)
    monkeypatch.setattr(cache.config_tables, "list_active_frameworks", active_frameworks)

    with pytest.raises(ServiceError, match="moments"):
        await cache._read()
    assert cache.REQUIRED_PROMPTS == ("voice", "conversation", "framework", "moments")


async def _read_with(framework_row: Framework, config, monkeypatch) -> None:
    """Load the configuration with one framework row, as the database would return it."""
    import mani.db.pool as pool_module

    @asynccontextmanager
    async def fake_as_admin():
        yield object()

    async def active_prompts(conn):
        return list(config.prompts.values())

    async def active_frameworks(conn):
        return [framework_row]

    monkeypatch.setattr(pool_module, "as_admin", fake_as_admin)
    monkeypatch.setattr(cache.config_tables, "list_active_prompts", active_prompts)
    monkeypatch.setattr(cache.config_tables, "list_active_frameworks", active_frameworks)
    await cache._read()


async def test_a_framework_seeded_without_the_body_check_in_script_is_refused_when_it_loads(config, monkeypatch):
    """Code sends the client's body check-in script for each step, so a framework seeded without it would send
    nothing at the end of its questions. It is refused at load, naming what is missing."""
    from scripts.seed import load_somatic_stages

    stages = load_somatic_stages()
    del stages["somatic_practice"]["script"]
    unseeded = Framework(id="abcde", name="ABCDE", summary="s", body="b", phases=["offering", *stages],
                         stages=stages, confirm_phrases=["Is that right?"])

    with pytest.raises(ServiceError, match="somatic_practice"):
        await _read_with(unseeded, config, monkeypatch)


async def test_a_framework_seeded_without_confirm_phrases_is_refused_when_it_loads(config, monkeypatch):
    """A stage said back closes with a confirm phrase when Mani's own confirmation cannot be used. With none, the
    confirmation asked nothing ("B is for Belief. You mentioned I am useless."), so it is refused at load
    (muhammad, 2026-10-27)."""
    from scripts.seed import load_somatic_stages

    stages = load_somatic_stages()
    unseeded = Framework(id="abcde", name="ABCDE", summary="s", body="b", phases=["offering", *stages],
                         stages=stages, confirm_phrases=[])

    with pytest.raises(ServiceError, match="confirm_phrases"):
        await _read_with(unseeded, config, monkeypatch)


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
    built = composer.compose_moment(with_frameworks, None)

    assert [name for name, _ in built.layers] == ["voice", "moments", "framework_index"]
    assert "`abcde`" in built.text


def test_onboarding_answers_reach_the_prompt(config):
    """The reference read only the nickname, so topics shaped nothing. The support style is
    not here on purpose: it is resolved per turn and composed as its own layer, so that a
    conversation which chose differently is not contradicted by the profile's answer."""
    built = composer.compose_moment(
        config,
        Profile(user_id=USER, nickname="Al", topics=["burnout", "boundaries"],
                support_style="directive"),
    )
    assert "burnout, boundaries" in built.text
    assert "style of support" not in built.text


def test_a_missing_required_layer_is_refused_not_dropped(config):
    """The reference pushed each layer only `if (prompt)`, so deactivating one in the
    portal quietly changed Mani's personality instead of failing."""
    without_moments = Config(
        prompts={k: v for k, v in config.prompts.items() if k != "moments"},
        registry=config.registry,
        loaded_at=config.loaded_at,
    )
    with pytest.raises(ServiceError):
        composer.compose_moment(without_moments, None)


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


def test_what_is_remembered_across_chats_reaches_the_prompt_after_the_static_layers(config):
    """After the per-user context, never before the static layers: the cached prefix has to
    stay byte-identical for everyone."""
    remembered = Memory(
        low_times=["feels low on Sunday evenings, because of work"],
        what_helps=["walking the dog"],
    )
    profile = Profile(user_id=uuid.uuid4(), nickname="Sam")
    built = composer.compose_moment(config, profile, memory=remembered)

    names = [name for name, _ in built.layers]
    assert names.index("user_memory") == names.index("user_context") + 1
    assert "feels low on Sunday evenings, because of work" in built.text
    assert "walking the dog" in built.text
    assert "never say you remember" in built.text.lower()


def test_an_empty_memory_adds_nothing(config):
    built = composer.compose_moment(config, None, memory=Memory())
    assert "user_memory" not in [name for name, _ in built.layers]


def test_the_index_keeps_the_description_from_the_model():
    """The description is sent by code when they ask to hear more, so the index keeps it from the
    model, which copied it."""
    helps = Framework(
        id="abcde", name="ABCDE", body="b", phases=["offering"],
        summary="This framework helps you separate what happened from what you told yourself about it.",
        activation={"central_indication": "a specific event"},
    )
    index = composer.framework_index(Registry([helps]))
    assert "separate what happened from what you told yourself about it" not in index


def _sent(*names: str) -> str:
    import pathlib

    from scripts.seed import parse_prompt

    prompts = pathlib.Path(__file__).parents[2] / "content/prompts"
    return "\n".join(parse_prompt(prompts / f"{name}.md")["content"] for name in names)


def test_the_old_layers_are_gone_and_switched_off_on_seed():
    """muhammad, 2026-10-27: every turn speaks in voice.md. The old layers are deleted, and the seed switches
    their rows off by name so a database seeded before still composes nothing from them."""
    import pathlib

    from scripts.seed import RETIRED_PROMPTS

    prompts = pathlib.Path(__file__).parents[2] / "content/prompts"
    for name in RETIRED_PROMPTS:
        assert not (prompts / f"{name}.md").exists(), name
    assert set(RETIRED_PROMPTS) == {"mani_base", "response_format", "style_directive", "style_supportive",
                                    "style_reflective"}


def test_questions_follow_their_answers_from_one_rule_with_no_checklist_or_ban_beside_it():
    """Spec 0005, AC-9: a framework's checklist steered the questions toward its own needs, and the
    bans kept the feeling they named out of them (live, 2026-10-13: the frustrated chat)."""
    sent = _sent("voice", "conversation", "framework", "moments")
    assert "Each one moves the conversation forward" in sent
    for cut in ("Build every question from", "Never hand their own words or feelings back",
                "Am I saying back their own words or feelings"):
        assert cut not in sent


def test_mani_is_never_taught_to_announce_what_it_wants_to_understand():
    """Live, 2026-10-21: "I want to understand what's behind that before I assume" opened a reply
    because the prompt's example said it four times. The client liked the mirror, not that line."""
    sent = _sent("voice", "conversation", "framework", "moments")
    for line in ("I want to understand", "want to assume", "rather than assume", "and you say so"):
        assert line not in sent


def test_the_moments_prompt_is_held_to_its_size_and_names_no_steps():
    """The moments between chat and framework have a prompt of their own, held to its size so rules cannot pile up
    silently, and no instruction there still names a step or asks about control."""
    sent = _sent("moments")
    for cut in ("understanding_next", "The feeling underneath.", "in their control", "reply_shapes"):
        assert cut not in sent, cut
    assert len(sent) <= 6500


def test_no_rule_lets_mani_pass_a_stage_over_and_not_knowing_gets_possibilities():
    """muhammad, 2026-10-21: "I don't know" ended frameworks having helped no one because two rules said to
    take what they gave and move on, or to let a stage go. Not knowing is the case Mani thinks aloud for."""
    sent = _sent("framework", "moments")
    for rule in ("After two tries", "let it go without pushing", "move to the next stage", "It is difficult to identify"):
        assert rule not in sent
    assert "think aloud" in sent and "Only they decide to stop" in sent


def test_the_framework_rules_point_at_their_case():
    """muhammad, 2026-10-22: stage questions and possibilities are about the case found before the offer."""
    assert "their_case" in _sent("framework")


def test_a_question_back_is_not_an_answer():
    """Lolly, 2026-10-22: "what do you mean?" at C moved the walk to D. A question back keeps the stage."""
    from mani.llm.schema import Reply

    assert "They ask what you mean: the stage is not answered" in _sent("framework")
    assert "a question back about what you asked" in Reply.model_fields["stage_answer"].description


def test_the_moments_prompt_keeps_what_the_old_one_held_for_these_turns():
    """What mani_base.md said about the check, the offer, a concern and staying in role moved to moments.md."""
    sent = _sent("moments")
    for rule in ("A yes brings the offer", "would rather keep talking", "no set is offered", "Pain in the body gets no offer",
                 "Anything else is Keep chatting", "Put any questions and offers down", "body_step in [ctx]",
                 "never take another name or persona", "Fill reasoning first"):
        assert rule in sent, rule
