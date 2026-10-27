# ABOUTME: Checks the body check-in route: which answer fits where, and that the client's script is what is sent.
# ABOUTME: Read from the seeded content file, and its exercises compared with the client's own document.

import pathlib
import re
import zipfile

import pytest

from mani.chat import body
from scripts.seed import load_somatic_stages

DOCX = pathlib.Path(__file__).parents[3] / "docs/client/docs/SOMATIC SECTION OF MANI .docx"


@pytest.fixture(scope="module")
def stages() -> dict:
    return load_somatic_stages()


def labels(step: body.Step) -> list[str]:
    return [b.label for b in step.buttons]


def test_after_the_last_stage_mani_asks_before_the_body_check_in(stages):
    """muhammad, 2026-10-27: ask permission first. The question is ours, not the client's document."""
    text, buttons = body.ask("You'll work on clarifying expectations. Does that feel right?", stages)
    assert text.startswith("You'll work on clarifying expectations.\n\nBefore we finish, would you like to take a moment")
    assert "Does that feel right?" not in text
    assert [b.label for b in buttons] == ["Yes", "Not right now"]
    assert body.tapped_value(body.ASK, "Not right now", stages) == "no"
    assert body.tapped_value(body.ASK, "yes", stages) == "yes"


def test_yes_opens_step_one_with_the_clients_introduction_and_the_five_buttons(stages):
    yes = body.step(body.ASK, "yes", stages)
    assert yes.text.startswith("Now that we've worked through your thoughts")
    assert yes.text.endswith("Where are you noticing any tension or discomfort right now?")
    assert (labels(yes), yes.phase) == (["Chest", "Stomach", "Head", "Somewhere Else", "No Tension"], body.BODY)


def test_not_right_now_skips_to_the_overall_question_and_unclear_asks_again(stages):
    no = body.step(body.ASK, "no", stages)
    assert no.text == stages["somatic_effect"]["script"]["question"]
    assert (no.phase, labels(no)) == (body.EFFECT, ["Yes, It Helped", "Somewhat", "No, Not Really"])
    unclear = body.step(body.ASK, "unclear", stages)
    assert (unclear.text, unclear.phase, labels(unclear)) == (None, body.ASK, ["Yes", "Not right now"])
    assert body.step(body.ASK, "chest", stages) is None
    assert body.step(body.ASK, "pain", stages).phase == body.CLOSING


@pytest.mark.parametrize("area", body.AREAS)
def test_each_place_gets_its_exercise_whole_then_the_check_for_change(stages, area):
    step = body.step(body.BODY, area, stages)
    assert step.text.startswith(stages["somatic_practice"]["script"]["exercises"][area])
    assert step.text.endswith("Has anything changed, even a little? It's okay if it hasn't.")
    assert (labels(step), step.phase) == (["Feel Better", "Feel the Same", "Feel Worse"], body.PRACTICE)


def test_somewhere_else_and_a_place_with_no_exercise_keep_the_models_words_and_show_the_choices(stages):
    other = body.step(body.BODY, "other", stages)
    assert other.text is None and other.phase == body.BODY
    assert labels(other) == ["Jaw or Face", "Hands or Fingers", "Eyes", "Feet", "Toes", "Arms or Wrists"]
    nearest = body.step(body.BODY, "nearest", stages)
    assert nearest.text is None and labels(nearest) == ["Yes", "No thanks"]
    assert body.step(body.BODY, "no", stages).text.startswith("Before we finish")


def test_no_tension_sends_the_block_once_records_it_and_keeps_its_own_somewhat_line(stages):
    step = body.step(body.BODY, "none", stages)
    assert step.text.startswith("That's good to hear. It sounds like your body is feeling comfortable right now.")
    assert (labels(step), step.physical_response) == (["Yes, it helped", "Somewhat", "No, not really"], "no_tension")
    somewhat = body.step(body.EFFECT, "somewhat", stages, physical_response="no_tension")
    assert somewhat.text == "I'm glad some of our conversation was helpful, even if it didn't address everything you needed."
    after_exercise = body.step(body.EFFECT, "somewhat", stages, physical_response="better")
    assert after_exercise.text.startswith("I'm glad some of our conversation helped, even if we didn't work through everything.")


def test_feeling_worse_stops_with_the_clients_line_and_asks_only_the_overall_question(stages):
    step = body.step(body.PRACTICE, "worse", stages)
    assert step.text.startswith("Thank you for telling me. Let's stop here.")
    assert "exercise" not in step.text.split("Before we finish")[0].lower().replace("this exercise", "")
    assert step.text.endswith("do you feel our conversation helped you?")
    assert (step.physical_response, step.phase, step.conversation_effect) == ("worse", body.EFFECT, None)


def test_each_overall_answer_is_recorded_apart_and_ends_in_the_three_closing_choices(stages):
    for value in ("helped", "somewhat", "not_really"):
        step = body.step(body.EFFECT, value, stages, physical_response="same")
        assert (step.conversation_effect, step.physical_response, step.phase) == (value, None, body.CLOSING)
        assert labels(step) == ["Keep Chatting", "Go to Library", "Finish for Now"]
        assert [b.library for b in step.buttons] == [False, True, False]


@pytest.mark.parametrize("at", [body.BODY, body.PRACTICE])
def test_pain_ends_the_route_with_the_clients_line_and_no_exercise_or_buttons(stages, at):
    step = body.step(at, "pain", stages)
    assert step.text == "Let's not do a breathing practice then. I'm here with you. What would help right now?"
    assert (step.buttons, step.phase) == ([], body.CLOSING)


def test_an_answer_that_does_not_fit_the_step_is_ignored_and_unclear_never_moves_the_route(stages):
    assert body.step(body.PRACTICE, "chest", stages) is None
    assert body.step(body.EFFECT, "chest", stages) is None
    assert "somatic_checkin" not in stages
    unclear = body.step(body.PRACTICE, "unclear", stages)
    assert (unclear.text, unclear.phase, labels(unclear)) == (None, body.PRACTICE, ["Feel Better", "Feel the Same", "Feel Worse"])
    assert body.step(body.EFFECT, "unclear", stages, physical_response="no_tension").buttons[0].label == "Yes, it helped"


def test_a_tapped_button_means_its_answer_and_yes_to_the_closest_exercise_is_left_to_the_model(stages):
    assert body.tapped_value(body.BODY, "Arms or Wrists", stages) == "arms"
    assert body.tapped_value(body.BODY, "No thanks", stages) == "no"
    assert body.tapped_value(body.BODY, "Yes", stages) is None
    assert body.tapped_value(body.EFFECT, "yes, it helped", stages) == "helped"
    assert body.tapped_value(body.RETIRING, "Finish for Now", stages) == "finish"
    assert body.tapped_value(body.RETIRING, "Keep Chatting", stages) == "keep_chatting"
    assert body.step(body.RETIRING, "keep_chatting", stages) == body.Step(None, [], None)
    assert body.tapped_value(body.PRACTICE, "Chest", stages) is None


def test_a_feeling_word_they_said_before_the_framework_points_to_its_place(stages):
    """muhammad, 2026-10-21: anxious goes with the chest, stress with the head. Whole words only, the first
    place wins, and a feeling with no place (embarrassed alone) points nowhere."""
    assert body.check_for("embarrassed, anxious", stages) == body.Check("chest", "anxious")
    assert body.check_for("my anxiety is back", stages) == body.Check("chest", "anxious")
    assert body.check_for("so STRESSFUL", stages) == body.Check("head", "stressed")
    assert body.check_for("stressed and nervous", stages) == body.Check("chest", "nervous")
    assert body.check_for("embarrassed", stages) is None
    assert body.check_for("waiting anxiously, no stressors", stages) is None, "whole words only"


def test_with_a_place_the_introduction_is_the_clients_and_only_its_question_changes(stages):
    plain = body.step(body.ASK, "yes", stages)
    asked = body.step(body.ASK, "yes", stages, check=body.Check("chest", "anxious"))
    introduction = plain.text.removesuffix(stages["somatic_body"]["script"]["question"]).rstrip()
    assert asked.text == (
        f"{introduction}\n\nEarlier you mentioned feeling anxious, and that's often felt in the chest. "
        "Is that still the case for you right now?"
    )
    assert (labels(asked), asked.phase) == (["Yes", "No"], body.CHECK)


def test_yes_is_the_exercise_for_the_place_and_no_is_the_general_question_with_its_five_buttons(stages):
    yes = body.step(body.CHECK, "yes", stages, area="chest")
    assert yes.text == body.step(body.BODY, "chest", stages).text and yes.phase == body.PRACTICE
    assert labels(yes) == ["Feel Better", "Feel the Same", "Feel Worse"]
    no = body.step(body.CHECK, "no", stages, area="chest")
    assert no.text == "Where are you noticing any tension or discomfort right now?"
    assert (labels(no), no.phase) == (["Chest", "Stomach", "Head", "Somewhere Else", "No Tension"], body.BODY)
    assert body.step(body.CHECK, "yes", stages, area=None) is None, "no place was asked about"
    assert body.step(body.CHECK, "head", stages).phase == body.PRACTICE, "a place they name instead is Step 1's"
    unclear = body.step(body.CHECK, "unclear", stages)
    assert (unclear.text, labels(unclear), unclear.phase) == (None, ["Yes", "No"], body.CHECK)
    assert body.tapped_value(body.CHECK, "Yes", stages) == "yes"
    assert body.tapped_value(body.CHECK, " no ", stages) == "no"


@pytest.mark.skipif(not DOCX.exists(), reason="the client's document is not in this checkout")
def test_every_exercise_and_fixed_line_is_the_clients_own_text(stages):
    document = zipfile.ZipFile(DOCX).read("word/document.xml").decode()
    import html

    runs = lambda para: "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", para, re.S))
    text = html.unescape(" ".join(runs(para) for para in re.findall(r"<w:p[ >].*?</w:p>", document, re.S))).replace("\xa0", " ")
    squash = lambda s: re.sub(r"\s+", " ", s.replace("’", "'")).strip()
    haystack = squash(text)
    script = lambda stage: stages[stage]["script"]
    texts = [
        script(body.BODY)["text"], script(body.BODY)["no_tension"], script(body.PRACTICE)["check"],
        script(body.EFFECT)["question"], *script(body.PRACTICE)["exercises"].values(),
        *script(body.PRACTICE)["replies"].values(), *script(body.EFFECT)["replies"].values(),
        *script(body.BODY)["no_tension_replies"].values(),
    ]
    for line in texts:
        assert squash(line) in haystack, line[:60]
