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
        named = set(re.findall(r"\d{3,}", crisis.pause_reply(about, 15)))
        assert "911" in named and named <= listed, about


def test_the_pause_reply_fits_whose_danger_it_is():
    """The live replays of 2026-11-13: one reply went out for chest pain, a bee sting, a stroke and a friend's overdose,
    saying "your safety" and offering suicide lines for a body emergency."""
    themselves = crisis.pause_reply("themselves", 15)
    assert "your safety" in themselves and "988" in themselves and "15 minutes" in themselves
    assert "everyone's safety" in crisis.pause_reply("someone_else", 15)
    assert "your safety" in crisis.pause_reply("from_someone", 15), "the danger is to them"
    for other in ("someone_else", "from_someone"):
        assert "988" not in crisis.pause_reply(other, 15)
    body = crisis.pause_reply("body", 15)
    assert "your health" in body and "911" in body and "988" not in body
    assert crisis.pause_reply(None, 15) == themselves, "an unknown danger keeps the suicide line"
    for about in ("themselves", "someone_else", "from_someone", "body"):
        assert crisis.pause_reply(about, 15).endswith("I'll be here when you come back."), about
