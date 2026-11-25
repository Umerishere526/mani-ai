# ABOUTME: Checks the crisis resource list carries the reference US numbers the pause messages name, each with its
# ABOUTME: kind, the helpline directory for every country, and a pause message that fits whose danger it is.

import re

from mani.chat import crisis


def test_crisis_resources_list_the_reference_numbers():
    us = {r.name: r for r in crisis.resources_for("us")}

    assert len(us) == 4
    assert us["Emergency services"].phone == "911"
    assert us["988 Suicide & Crisis Lifeline"].phone == "988"
    assert us["988 Suicide & Crisis Lifeline"].sms == "988"
    assert us["988 Suicide & Crisis Lifeline"].url == "https://988lifeline.org"
    assert us["Crisis Text Line"].sms == "741741"
    assert us["Find a helpline in your country"].url == "https://findahelpline.com"


def test_each_resource_says_what_kind_of_help_it_is():
    kinds = {r.name: r.kind for r in crisis.RESOURCES}

    assert kinds == {
        "Emergency services": "emergency",
        "988 Suicide & Crisis Lifeline": "support",
        "Crisis Text Line": "support",
        "Find a helpline in your country": "directory",
    }


def test_the_helpline_directory_is_listed_for_every_country():
    assert [r.url for r in crisis.resources_for("fr")] == ["https://findahelpline.com"]
    assert [r.kind for r in crisis.resources_for("fr")] == ["directory"]
    assert len(crisis.resources_for()) == 4


def test_every_number_the_pause_reply_names_is_a_listed_resource():
    listed = {number for r in crisis.RESOURCES for number in (r.phone, r.sms) if number}
    for about in ("themselves", "someone_else", "from_someone", "body", None):
        named = set(re.findall(r"\d{3,}", crisis.pause_reply(about, 30)))
        assert "911" in named and named <= listed, about


def test_the_pause_reply_fits_whose_danger_it_is():
    """The live replays of 2026-11-13: one reply went out for chest pain, a bee sting, a stroke and a friend's overdose,
    saying "your safety" and offering suicide lines for a body emergency."""
    themselves = crisis.pause_reply("themselves", 30)
    assert "your safety" in themselves and "988" in themselves and "30 seconds" in themselves
    assert "pausing our chat for 15 minutes." in crisis.pause_reply("themselves", 900)
    assert "everyone's safety" in crisis.pause_reply("someone_else", 30)
    assert "your safety" in crisis.pause_reply("from_someone", 30), "the danger is to them"
    for other in ("someone_else", "from_someone"):
        assert "988" not in crisis.pause_reply(other, 30)
    body = crisis.pause_reply("body", 30)
    assert "your health" in body and "911" in body and "988" not in body
    assert crisis.pause_reply(None, 30) == themselves, "an unknown danger keeps the suicide line"
    for about in ("themselves", "someone_else", "from_someone", "body"):
        assert crisis.pause_reply(about, 30).endswith("We can talk again when you come back."), about


def test_every_resources_text_gives_the_us_numbers_and_the_directory_for_everywhere_else():
    """S11 and S9 (PROVISIONAL: clinician sign-off required before deploy): no country detection, so every text that
    says where to get help names 911, and findahelpline.com for anyone outside the US. The outage reply while a worry
    is held named no number at all ("contact your local emergency number")."""
    texts = {
        "IN_DANGER": crisis.IN_DANGER, "CRISIS_REPLY": crisis.CRISIS_REPLY, "TROUBLE_REPLY": crisis.TROUBLE_REPLY,
        "BODY_EMERGENCY": crisis.BODY_EMERGENCY, "RETURN_CHECK_REPLY": crisis.RETURN_CHECK_REPLY,
        "RETURN_DANGER_REPLY": crisis.RETURN_DANGER_REPLY,
        **{f"pause_reply({about})": crisis.pause_reply(about, 900)
           for about in ("themselves", "someone_else", "from_someone", "body", None)},
    }
    for name, text in texts.items():
        assert "911" in text and "findahelpline.com" in text, name
    for name in ("IN_DANGER", "CRISIS_REPLY", "TROUBLE_REPLY", "RETURN_CHECK_REPLY", "RETURN_DANGER_REPLY"):
        assert "988" in texts[name], name
