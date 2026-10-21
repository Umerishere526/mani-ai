# ABOUTME: Checks Thought Reframe can be seeded and that both frameworks end on what muhammad asked for.
# ABOUTME: ABCDE ends on one clear path, Thought Reframe on a believable thought; read from the files themselves.

import pytest

from scripts.seed import FRAMEWORKS_DIR, missing_for_activation, parse_framework


@pytest.fixture(scope="module")
def frameworks() -> dict[str, dict]:
    return {name: parse_framework(FRAMEWORKS_DIR / f"{name}.md") for name in ("abcde", "thought_reframe")}


def test_both_frameworks_have_everything_an_active_one_needs(frameworks):
    for name, parsed in frameworks.items():
        assert missing_for_activation(parsed) == [], name


def test_abcde_stays_on_e_until_they_have_a_path(frameworks):
    effective = frameworks["abcde"]["stages"]["effective"]
    assert "one clear path" in effective["ready_when"]
    assert any(branch.get("id") == "path" for branch in effective["if_unclear"])
    assert not any("must not supply the new belief" in rule for rule in effective["boundaries"])


def test_thought_reframe_stays_on_its_last_phase_until_they_believe_a_balanced_thought(frameworks):
    """The client's text: the replacement does not have to be positive, it has to be something the person can
    genuinely believe. There is no sixth stage after it; code sends one acknowledging sentence, then the body."""
    parsed = frameworks["thought_reframe"]
    replacement = parsed["stages"]["replacement"]
    assert parsed["phases"] == ["offering", "thought", "painful", "feels_true", "alternative", "replacement"]
    assert "they say they believe" in replacement["ready_when"] and "does not have to be positive" in replacement["ready_when"]
    assert "hopeful" not in replacement["ready_when"] + replacement["purpose"]
    assert any(branch.get("id") == "believe" for branch in replacement["if_unclear"])
    assert not any("positive language" in rule for rule in replacement["boundaries"])


def test_thought_reframe_has_the_clients_five_steps_by_name(frameworks):
    parsed = frameworks["thought_reframe"]
    assert [parsed["stages"][stage]["title"] for stage in parsed["phases"][1:]] == [
        "Identify the Thought", "Name What Makes It Painful", "Explore What Makes the Thought Feel True",
        "Consider Another Interpretation", "Create a Believable Replacement Thought",
    ]
    assert "see the situation differently" not in parsed["summary"], "the goal is not to prove the thought wrong"


def test_thought_reframe_asks_what_makes_it_convincing_before_what_complicates_it(frameworks):
    """Step 3 has two parts, asked one at a time as ABCDE's D is, and nothing complicating it is an answer."""
    feels_true = frameworks["thought_reframe"]["stages"]["feels_true"]
    assert "asks only what makes the thought convincing" in feels_true["reach"] and "gap complicates" in feels_true["reach"]
    assert [branch["id"] for branch in feels_true["if_unclear"]] == ["complicates"]
    assert "Nothing complicating it is an answer" in feels_true["ready_when"]


def test_thought_reframe_content_is_not_about_one_situation(frameworks):
    """The asks and replies were written about a friend's silence, so they read wrongly for any other thought."""
    import re

    stages = frameworks["thought_reframe"]["stages"]
    for stage, content in stages.items():
        text = " ".join(
            str(value) for key, value in content.items()
            if key in ("ask", "reach", "ready_when", "boundaries", "purpose") for value in (
                value.values() if isinstance(value, dict) else value if isinstance(value, list) else [value])
        ) + " ".join(branch.get("reply", "") for branch in content.get("if_unclear", []))
        assert not re.search(r"\b(she|her|friend|silence)\b", text, re.I), stage


def test_the_stages_the_case_can_answer_are_judged_against_it(frameworks):
    """muhammad, 2026-10-22: the first Thought Reframe stage asked what makes the thought difficult though the
    feeling underneath was confirmed in the check. The stage the case answers is reported known and said back."""
    reading_the_case = {"abcde": ("activate", "belief", "consequence"), "thought_reframe": ("thought", "painful")}
    for name, stages in reading_the_case.items():
        for stage in stages:
            assert "their_case" in frameworks[name]["stages"][stage]["reach"], (name, stage)


def test_stage_a_says_back_what_happened_together_with_the_feeling_they_confirmed(frameworks):
    """muhammad, 2026-10-22: A said back one example, and they had to say the feeling again."""
    reach = frameworks["abcde"]["stages"]["activate"]["reach"]
    assert "together with the underlying feeling" in reach and "objective trigger" in reach
    thought = frameworks["thought_reframe"]["stages"]["thought"]["reach"]
    assert "together with the underlying feeling" in thought, "Thought Reframe opens the same way"
    from mani.chat import walk

    assert "unless this stage's reach names it" in walk.CONFIRM_ASK


def test_a_stage_with_nothing_known_is_asked_in_the_models_own_words_about_their_case():
    """muhammad, 2026-10-22: "Now that you've looked at both sides" went out as written, with no side in view."""
    from mani.chat import walk

    line = walk.reach_line("effective")
    assert "as written" not in line
    assert "a short mirror of their situation" in line and "possibilities for answering go in options" in line


def test_the_feeling_underneath_is_carried_into_every_stage_reply():
    """muhammad, 2026-10-21 (sister thread): B said back the belief and the person had to say the guilt again.
    The mirror of a stage reached, a confirmation and the case sent every turn all keep the feeling underneath."""
    from mani.chat import context, walk

    assert "the feeling underneath and what they said" in walk.reach_line("belief")
    assert "the feeling underneath may frame it, never be its answer" in walk.CONFIRM_ASK
    assert "the feeling underneath" in context._MEANING["their_case"]


def test_d_asks_what_supports_the_belief_and_what_might_challenge_it_as_two_questions(frameworks):
    """muhammad, 2026-10-21: each question has one purpose, never says what it is for and never leads."""
    dispute = frameworks["abcde"]["stages"]["dispute"]
    assert "asks only what supports the belief" in dispute["reach"] and "gap challenge" in dispute["reach"]
    assert {branch["id"] for branch in dispute["if_unclear"]} == {"information", "challenge"}
    assert any("never says what it is for" in rule for rule in dispute["boundaries"])
    assert any("lead them to a conclusion" in rule for rule in dispute["boundaries"])
