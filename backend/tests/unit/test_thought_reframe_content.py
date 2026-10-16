# ABOUTME: Checks the seeded Thought Reframe framework carries what the client's Thought Reframe document asks for.
# ABOUTME: Read from the framework file itself, the same structure that is seeded, so no database is needed.

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
        confirm_phrases=parsed["confirm_phrases"],
    )


def test_it_can_be_seeded_active_and_runs_five_steps_then_the_body_check_in(reframe):
    assert missing_for_activation(reframe) == []
    assert reframe["phases"] == ["offering", "thought", "painful", "feels_true", "interpretation", "replacement"]
    framework = as_framework(reframe)
    assert framework.closing == "replacement"
    assert framework.check_in_required, "the document: the body check-in must not be omitted"


def test_each_step_opens_with_its_number_and_the_clients_name(reframe):
    intros = {stage: reframe["stages"][stage]["intro"] for stage in reframe["phases"][1:]}
    assert intros == {
        "thought": "Step 1 is Identify the Thought.",
        "painful": "Step 2 is Name What Makes It Painful.",
        "feels_true": "Step 3 is Explore What Makes the Thought Feel True.",
        "interpretation": "Step 4 is Consider Another Interpretation.",
        "replacement": "Step 5 is Create a Believable Replacement Thought.",
    }


# The document's Try It questions, word for word. Step 1's are the generic ones: its client lines with
# their feeling word are the missing lines, below.
CLIENT_QUESTIONS = {
    "painful": {
        "directive": "What's most upsetting about that thought?",
        "supportive": "What's the hardest part of thinking that might be true?",
        "reflective": "When you think about that possibility, what feels most upsetting about what it might mean?",
    },
    "feels_true": {
        style: "What makes that thought feel true to you? Is there anything that makes you see it differently?"
        for style in STYLES
    },
    "interpretation": {
        "directive": "Is there another way to understand what's happening that could also make sense?",
        "supportive": "Is there another way of looking at what's happening that might also make sense to you?",
        "reflective": "As you think about what's happened, is there another explanation that could also make sense?",
    },
    "replacement": {
        "directive": "Given what you've considered, what's a more balanced way to think about this that you can believe?",
        "supportive": "After looking at this together, what's a more balanced way of thinking about it that feels true to you?",
        "reflective": "After talking this through, is there another way you might look at the situation that feels more realistic to you?",
    },
}


def test_every_step_asks_the_clients_own_question_in_each_style(reframe):
    for stage, asks in CLIENT_QUESTIONS.items():
        assert reframe["stages"][stage]["ask"] == asks, stage


def test_step_one_carries_the_documents_confirm_and_missing_lines(reframe):
    thought = reframe["stages"]["thought"]
    assert thought["missing"]["supportive"] == (
        "When you're feeling <their word for it>, what's the thought that's been bothering you most?"
    )
    assert thought["missing"]["directive"] == "What's the thought that's been bothering you most?"
    for key in ("confirm", "missing"):
        assert set(thought[key]) == set(STYLES)
        assert all(line.endswith("?") for line in thought[key].values())


def test_try_it_begins_with_the_documents_line_in_every_style(reframe):
    assert set(reframe["stages"]["offering"]["begin"].values()) == {
        "Let's begin Thought Reframe. We'll start with what you've already told me."
    }


def test_tell_me_more_is_the_five_steps_in_the_selected_style(reframe):
    framework = as_framework(reframe)
    for style in STYLES:
        text = repairs.explanation(framework, style)
        assert text.startswith("Thought Reframe has five steps")
        assert text.count("\n- ") == 5 and "Create a Believable Replacement Thought:" in text
        assert text.endswith("Would you like to try it?")


@pytest.mark.parametrize(("style", "opening"), [
    ("directive", "When you say you are not handling things well, Thought Reframe can help us understand"),
    ("supportive", "You said you are not handling things well. Thought Reframe can help us understand what you mean"),
    ("reflective", "When you say you are not handling things well, I would like to understand what is behind"),
])
def test_the_offer_is_the_clients_line_with_their_thought_in_its_one_slot(reframe, style, opening):
    template = reframe["stages"]["offering"]["offer"][style]
    assert "?" not in template, "the permission question is added by code"
    rendered = repairs.render_template(template, lead_line=None, slot="you are not handling things well")
    assert rendered.startswith(opening)


def test_keep_chatting_is_the_clients_question_with_their_words(reframe):
    framework = as_framework(reframe)
    assert repairs.keep_chatting(framework, "reflective", "you're not handling things well") == (
        "When you say you're not handling things well, what experiences have led you to think that about yourself?"
    )


def test_the_framework_index_tells_it_apart_from_abcde_once_with_abcde_first(reframe):
    from mani.prompts import composer

    abcde = parse_framework(FRAMEWORKS_DIR / "abcde.md")
    index = composer.framework_index(Registry([as_framework(abcde), as_framework(reframe)]))
    assert index.count("**Thought Reframe or ABCDE**") == 1
    assert "a troubling thought alone does not make it ABCDE" in index
    assert index.index("| ABCDE |") < index.index("| Thought Reframe |")
    assert "act choice point" not in index.lower(), "no set that cannot be offered"


def test_after_step_five_the_body_check_in_never_offers_to_skip_for_an_action(reframe):
    from mani.chat import context
    from scripts.seed import load_somatic_stages

    somatic = load_somatic_stages()
    abcde = parse_framework(FRAMEWORKS_DIR / "abcde.md")
    for parsed, offers_skip in ((reframe, False), (abcde, True)):
        framework = as_framework({**parsed, "phases": parsed["phases"] + list(somatic),
                                  "stages": {**parsed["stages"], **somatic}})
        lines = "\n".join(context._stage_lines("next_stage", framework, "somatic_checkin", "directive"))
        assert ("acting:" in lines) is offers_skip, parsed["id"]


def test_a_line_the_walk_finds_by_its_id_must_be_one_string_with_a_when(reframe):
    stages = {**reframe["stages"], "feels_true": {
        **reframe["stages"]["feels_true"],
        "if_unclear": [{"id": "differently", "when": "w", "reply": {"directive": "Anything else?"}}],
    }}
    assert missing_for_activation({**reframe, "stages": stages}) == [
        "stages.feels_true.if_unclear.differently with a when and one reply"
    ]
