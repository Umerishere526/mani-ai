# ABOUTME: Checks the one seeded framework, ABCDE, carries what the client's ABCDE document asks for.
# ABOUTME: Read from the framework file itself, the same structure that is seeded, so no database is needed.

import pytest

from mani.chat import context, repairs
from mani.chat.techniques import Registry
from mani.models.rows import Framework
from scripts.seed import FRAMEWORKS_DIR, parse_framework

STYLES = ("direct", "supportive", "reflective")


@pytest.fixture(scope="module")
def abcde() -> dict:
    return parse_framework(FRAMEWORKS_DIR / "abcde.md")


def as_framework(parsed: dict) -> Framework:
    return Framework(
        id=parsed["id"], name=parsed["name"], summary=parsed["summary"], body="b",
        phases=parsed["phases"], activation=parsed["activation"], stages=parsed["stages"],
    )


def test_only_abcde_is_seeded():
    assert [p.stem for p in FRAMEWORKS_DIR.glob("*.md")] == ["abcde"]


def test_abcde_runs_a_to_e_and_the_body_check_in_follows(abcde):
    assert abcde["phases"] == ["offering", "activate", "belief", "consequence", "dispute", "effective"]
    framework = as_framework(abcde)
    assert framework.closing == "effective", "the last letter is asked, never skipped"


def test_every_letter_has_a_title_for_the_ledger_and_asks_in_all_three_styles(abcde):
    titles = {"activate": "A: Activating Event", "belief": "B: Belief", "consequence": "C: Consequences",
              "dispute": "D: Dispute", "effective": "E: Effective New Belief"}
    for stage, title in titles.items():
        assert abcde["stages"][stage]["title"] == title
        assert set(abcde["stages"][stage]["ask"]) == set(STYLES)


def test_tell_me_more_is_the_five_steps_in_the_selected_style(abcde):
    registry = Registry([as_framework(abcde)])
    for style in STYLES:
        text = repairs._compose_offer("part", registry, "abcde", style, None, describe=True)
        assert text.count("\n") >= 6 and "A: Activating Event" in text and "E: Effective New Belief" in text
        assert "part" not in text.split("\n\n")[0], "Mani's own part is not added to the explanation"
        assert text.endswith("Would you like to try it?")


def test_the_event_stage_confirms_only_a_possible_event_in_each_style(abcde):
    branch = abcde["stages"]["activate"]["if_unclear"][0]
    assert set(branch["reply"]) == set(STYLES)
    assert all(reply.endswith("?") for reply in branch["reply"].values())


def test_no_stage_letter_or_name_is_sent_for_the_chat_to_repeat(abcde):
    framework = as_framework(abcde)
    block = "\n".join(
        context._stage_lines("stage", framework, "activate", "direct")
        + context._later_stage_lines(framework, "dispute", "direct", explain=True)
    )
    assert "title" not in block and "label" not in block and "Activating Event" not in block
    note = context._stage_note(framework, "direct", starting=True)
    assert "Never say a stage's letter or name" in note and "skipped without a word" in note


def test_the_offer_follows_the_clients_pattern_with_a_slot_for_their_situation(abcde):
    offer = abcde["stages"]["offering"]["offer"]
    assert set(offer) == set(STYLES)
    for text in offer.values():
        assert "There's a framework called ABCDE" in text
        assert "<" in text and ">" in text and "?" not in text, "a slot to fill, and no question of its own"
    assert "helps you identify the thoughts behind <" in offer["direct"]
    assert "question whether they're true, and replace them with more realistic ones." in offer["direct"]


def test_the_offer_pattern_reaches_the_prompt_through_the_framework_index(abcde):
    from mani.prompts import composer

    index = composer.framework_index(Registry([as_framework(abcde)]))
    assert "## How to word an offer" in index
    assert "- direct: There's a framework called ABCDE that helps you identify the thoughts behind <" in index


CLIENT_QUESTIONS = {
    "belief": {
        "direct": "What did you start telling yourself about what was happening?",
        "supportive": "Sometimes when things are difficult, we start drawing conclusions about ourselves or what's happening. What were you telling yourself about the situation?",
        "reflective": "When that happened, what did you begin believing about yourself or the situation?",
    },
    "consequence": {
        "direct": "How did that thought affect how you felt or what you did?",
        "supportive": "Our thoughts can affect how we feel and respond. How did that belief affect how you felt or what you did?",
        "reflective": "When you believed that thought, how did it influence your feelings or the way you responded?",
    },
    "dispute": {
        "direct": "What makes you believe this is true, and what makes you question it?",
        "supportive": "Let's look at that belief together. What makes you think it's true? Is there anything that suggests otherwise?",
        "reflective": "As you think about that belief, what seems to support it, and what might suggest a different explanation?",
    },
    "effective": {
        "direct": "What's a more realistic and helpful way to think about what's happening?",
        "supportive": "Now that you've looked at both sides, what's a more realistic and helpful way to think about what's happening?",
        "reflective": "After considering both sides, what do you think would be a more accurate and helpful way to understand what happened?",
    },
}


def test_every_stage_asks_the_clients_own_question_in_each_style(abcde):
    for stage, asks in CLIENT_QUESTIONS.items():
        assert abcde["stages"][stage]["ask"] == asks, stage
