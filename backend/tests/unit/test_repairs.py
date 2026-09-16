# ABOUTME: Checks the deterministic corrections that replaced six regeneration calls.
# ABOUTME: Each case here cost an entire extra model call in the implementation ported from.

import pytest

from mani.chat import repairs
from mani.chat.techniques import Registry
from mani.llm.schema import Reply, SmartPrompt, Style, TechniqueState
from mani.models.rows import Framework

REFRAMING = Framework(
    id="thought_reframing", name="Thought Reframing", summary="s", body="b",
    phases=["offering", "surface", "externalize", "explore", "land", "ground"],
)
ABCDE = Framework(
    id="abcde", name="ABCDE", summary="s", body="b",
    phases=["offering", "activate", "belief", "consequence", "dispute", "effect", "ground"],
)


@pytest.fixture
def registry() -> Registry:
    return Registry([REFRAMING, ABCDE])


def reply(**overrides) -> Reply:
    return Reply(**({"text": "That sounds heavy to carry."} | overrides))


def fix(registry, model_reply, **overrides):
    defaults = {
        "already_offered": [],
        "current_framework_id": None,
        "current_phase": None,
        "selected_label": None,
        "accepted_this_turn": False,
        "wants_title": False,
    }
    return repairs.apply(model_reply, registry, **(defaults | overrides))


def test_mirroring_the_users_own_word_is_not_censored(registry):
    """The reference refused "heavy" anywhere, while instructing Mani to mirror."""
    assert fix(registry, reply()).text == "That sounds heavy to carry."


def test_leaked_script_metadata_is_stripped(registry):
    leaked = reply(
        text="Let's try something.\n\n**Mani:** Take a breath.\n\n(Include prompts: yes/no)"
    )
    fixed = fix(registry, leaked)
    assert "**Mani:**" not in fixed.text
    assert "Include prompts" not in fixed.text
    assert "Let's try something." in fixed.text
    assert fixed.notes


def test_an_already_offered_technique_is_dropped(registry):
    offered_again = reply(
        prompts=[
            SmartPrompt(label="Yes, let's try it", technique="abcde"),
            SmartPrompt(label="Not right now"),
        ]
    )
    fixed = fix(registry, offered_again, already_offered=["abcde"])
    assert [p.label for p in fixed.prompts] == ["Not right now"]


def test_the_technique_being_offered_is_not_a_duplicate_of_itself(registry):
    still_offering = reply(
        prompts=[SmartPrompt(label="Yes, let's try it", technique="abcde")]
    )
    fixed = fix(
        registry, still_offering, already_offered=["abcde"], current_framework_id="abcde"
    )
    assert len(fixed.prompts) == 1


def test_an_invented_technique_id_is_refused(registry):
    """A model-supplied identifier is untrusted until the registry recognises it."""
    invented = reply(prompts=[SmartPrompt(label="Try box breathing", technique="box_breathing")])
    assert fix(registry, invented).prompts == []


def test_the_button_the_user_just_tapped_is_not_offered_back(registry):
    echoed = reply(
        prompts=[SmartPrompt(label="Yes, let's try it"), SmartPrompt(label="Tell me more")]
    )
    fixed = fix(registry, echoed, selected_label="  yes, let's try it ")
    assert [p.label for p in fixed.prompts] == ["Tell me more"]


def test_more_than_three_buttons_are_trimmed(registry):
    many = reply(prompts=[SmartPrompt(label=f"Option {n}") for n in range(6)])
    assert len(fix(registry, many).prompts) == repairs.MAX_PROMPTS


def test_a_skipped_phase_is_corrected_rather_than_regenerated(registry):
    jumped = reply(state=TechniqueState(technique="thought_reframing", step="land"))
    fixed = fix(registry, jumped, current_framework_id="thought_reframing",
                current_phase="offering")
    assert fixed.phase == "surface"
    assert fixed.notes


def test_a_technique_appearing_mid_flow_is_pulled_back_to_offering(registry):
    straight_in = reply(state=TechniqueState(technique="abcde", step="belief"))
    assert fix(registry, straight_in).phase == "offering"


def test_state_for_an_unknown_technique_is_ignored(registry):
    nonsense = reply(state=TechniqueState(technique="somatic_release", step="offering"))
    fixed = fix(registry, nonsense)
    assert fixed.framework_id is None and fixed.phase is None


def test_a_long_title_is_trimmed_not_rejected(registry):
    """The schema capped this at 50 and failed the whole generation over it."""
    long = reply(title='  "Talking through a really long and rambling worry about work."  ')
    fixed = fix(registry, long, wants_title=True)
    assert fixed.title.startswith("Talking through")
    assert not fixed.title.endswith(".")
    assert len(fixed.title) <= repairs.MAX_TITLE_LENGTH


def test_a_title_is_ignored_when_none_was_asked_for(registry):
    assert fix(registry, reply(title="Unasked for")).title is None


def test_a_clean_reply_is_left_alone(registry):
    clean = reply(
        prompts=[SmartPrompt(label="Tell me more")],
        style=Style(shape="mirror and ask", voice="naming"),
    )
    fixed = fix(registry, clean)
    assert fixed.notes == []
    assert [p.label for p in fixed.prompts] == ["Tell me more"]
