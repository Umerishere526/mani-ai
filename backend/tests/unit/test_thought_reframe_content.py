# ABOUTME: Checks the seeded Thought Reframe framework carries what the client's cadence document asks for.
# ABOUTME: Read from the framework file itself, the same structure that is seeded, so no database is needed.

import copy
import re

import pytest

from mani.chat import repairs
from mani.chat.techniques import Registry
from mani.models.rows import Framework
from scripts.seed import FRAMEWORKS_DIR, missing_for_activation, parse_framework

STYLES = ("directive", "supportive", "reflective")


@pytest.fixture(scope="module")
def reframe() -> dict:
    return parse_framework(FRAMEWORKS_DIR / "thought_reframe.md")


def as_framework(parsed: dict) -> Framework:
    return Framework(
        id=parsed["id"], name=parsed["name"], summary=parsed["summary"], body="b",
        phases=parsed["phases"], activation=parsed["activation"], stages=parsed["stages"],
        confirm_phrases=parsed["confirm_phrases"], display_order=parsed.get("display_order", 0),
    )


def test_thought_reframe_runs_five_steps_and_the_body_check_in_follows(reframe):
    assert reframe["phases"] == ["offering", "thought", "significance", "facts", "alternative", "reframe"]
    framework = as_framework(reframe)
    assert framework.closing == "reframe", "the last step is asked, never skipped; no separate closing stage"


def test_it_passes_the_seed_activation_gate(reframe):
    assert missing_for_activation(reframe) == []


def test_each_step_has_its_line_said_once_and_the_confirm_phrases_are_the_four(reframe):
    """The PDF: each step is named as it opens ('Step 1 is Identify the Thought.'); the first intro folds
    in the Try-It opener once. Reframe's confirm phrases match ABCDE's so the fallback phrase is not new."""
    intros = {stage: reframe["stages"][stage]["intro"] for stage in reframe["phases"][1:]}
    assert intros == {
        "thought": "Let's begin Thought Reframe. We'll start with what you've already told me. Step 1 is Identify the Thought.",
        "significance": "Step 2 is Name What Makes It Painful.",
        "facts": "Step 3 is Explore What Makes the Thought Feel True.",
        "alternative": "Step 4 is Consider Another Interpretation.",
        "reframe": "Step 5 is Create a Believable Replacement Thought.",
    }
    assert reframe["confirm_phrases"] == [
        "Is that right?", "Do we have this right?", "Did I get that right?", "Does that sound right?",
    ]


def test_every_step_declares_the_parts_it_needs_and_when_to_stop_asking_for_each(reframe):
    needs = {stage: {p["id"]: p.get("required", True) for p in reframe["stages"][stage]["parts"]}
             for stage in reframe["phases"][1:]}
    assert needs == {
        "thought": {"thought": True},
        "significance": {"painful": True},
        "facts": {"supports": True, "against": True, "fact": False},
        "alternative": {"alternative": True},
        "reframe": {"new_thought": True, "next_step": False},
    }
    every = [p for stage in reframe["phases"][1:] for p in reframe["stages"][stage]["parts"]]
    assert len({p["id"] for p in every}) == len(every)
    assert all(p.get("stop_pushing") for p in every if p.get("required", True))


def test_only_the_last_step_reflects_so_reframe_stays_lighter_than_abcde(reframe):
    """The document: Reframe stays shorter, one reflection at the end only, never a second ABCDE."""
    assert [stage for stage in reframe["phases"][1:] if reframe["stages"][stage].get("reflect")] == ["reframe"]
    assert reframe["stages"]["reframe"]["reflect"] == "what changes when they see it this way"


def test_facts_asks_what_supports_the_thought_before_what_challenges_it(reframe):
    """The paused file's rule, kept: leading with counter-evidence reads as debate before the person has
    finished laying out their own case."""
    parts = [p["id"] for p in reframe["stages"]["facts"]["parts"]]
    assert parts.index("supports") < parts.index("against")


def test_a_believable_replacement_is_never_required(reframe):
    new_thought = next(p for p in reframe["stages"]["reframe"]["parts"] if p["id"] == "new_thought")
    assert "never a requirement" in new_thought["stop_pushing"] or "accept that" in new_thought["stop_pushing"]
    assert reframe["stages"]["reframe"]["boundaries"]
    assert any("possible outcome" in b for b in reframe["stages"]["reframe"]["boundaries"])


def test_the_clients_offer_wording_reaches_the_person_but_never_the_framework_index(reframe):
    from mani.prompts import composer

    index = composer.framework_index(Registry([as_framework(reframe)]))
    for key in ("offer", "keep_chatting", "explain"):
        for text in reframe["stages"]["offering"][key].values():
            fixed = max(re.split(r"<[^>]*>", text), key=len).strip()
            assert fixed[:40] not in index, key


def test_tell_me_more_is_the_five_steps_in_the_selected_style(reframe):
    registry = Registry([as_framework(reframe)])
    for style in STYLES:
        text = repairs.explanation(registry.get("thought_reframe"), style)
        assert text.count("\n") >= 6 and "Identify the Thought" in text and "Believable Replacement" in text
        assert text.endswith("Would you like to try it?")


CLIENT_QUESTIONS = {
    "thought": {
        "directive": "What's the thought that's troubling you?",
        "supportive": "When you're feeling overwhelmed, what's the thought that's been bothering you most?",
        "reflective": "When you think about feeling that way, what thought about yourself or the situation keeps coming back to you?",
    },
    "significance": {
        "directive": "What's most upsetting about that thought?",
        "supportive": "What's the hardest part of thinking that might be true?",
        "reflective": "When you think about that possibility, what feels most upsetting about what it might mean?",
    },
    "facts": {
        "directive": "What supports that thought?",
        "supportive": "What makes that thought feel true to you?",
        "reflective": "What have you seen that seems to support it?",
    },
    "alternative": {
        "directive": "Is there another way to understand what's happening that could also make sense?",
        "supportive": "Is there another way of looking at what's happening that might also make sense to you?",
        "reflective": "As you think about what's happened, is there another explanation that could also make sense?",
    },
    "reframe": {
        "directive": "What's a more balanced way to think about this that you can believe?",
        "supportive": "After looking at this together, what's a more balanced way of thinking about it that feels true to you?",
        "reflective": "After talking this through, is there another way you might look at the situation that feels more realistic to you?",
    },
}


def test_every_step_asks_the_clients_own_question_in_each_style(reframe):
    for stage, asks in CLIENT_QUESTIONS.items():
        assert reframe["stages"][stage]["ask"] == asks, stage


def test_offer_templates_share_abcdes_slot_shape(reframe):
    """slots_for builds the Offer schema from the first active framework's template (ABCDE, display_order 1);
    Reframe's templates must fit the same shape (going_through inline, a lead_line on supportive/reflective)."""
    from mani.chat.repairs import template_slots

    offer = reframe["stages"]["offering"]["offer"]
    whole, inline = template_slots(offer["directive"])
    assert whole is None and inline is not None, "directive: inline slot only, like ABCDE"
    for style in ("supportive", "reflective"):
        whole, inline = template_slots(offer[style])
        assert whole is not None and inline is not None, f"{style}: a lead line and an inline slot, like ABCDE"


def test_a_framework_whose_parts_the_walk_cannot_read_is_refused_at_seed_with_the_path_named(reframe):
    broken = copy.deepcopy(reframe)
    del broken["stages"]["alternative"]["parts"]
    broken["stages"]["significance"]["parts"][0]["id"] = "thought"
    assert missing_for_activation(broken) == [
        "stages.alternative.parts",
        "parts.thought listed twice",
    ]
