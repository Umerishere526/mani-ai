# ABOUTME: Checks the crisis resource list carries the reference US numbers the pause messages name, each with its
# ABOUTME: kind, the helpline directory for every country, and a pause message that fits whose danger it is.

import re

from mani.chat import crisis, enforce


def test_crisis_resources_list_the_reference_numbers():
    us = {r.name: r for r in crisis.resources_for("us")}

    assert len(us) == 5
    assert us["Emergency services"].phone == "911"
    assert us["988 Suicide & Crisis Lifeline"].phone == "988"
    assert us["988 Suicide & Crisis Lifeline"].sms == "988"
    assert us["988 Suicide & Crisis Lifeline"].url == "https://988lifeline.org"
    assert us["Crisis Text Line"].sms == "741741"
    assert us["Find a helpline in your country"].url == "https://findahelpline.com"
    assert us["National Domestic Violence Hotline"].phone == "1-800-799-7233"
    assert us["National Domestic Violence Hotline"].sms == "88788"


def test_each_resource_says_what_kind_of_help_it_is():
    kinds = {r.name: r.kind for r in crisis.RESOURCES}

    assert kinds == {
        "Emergency services": "emergency",
        "988 Suicide & Crisis Lifeline": "support",
        "Crisis Text Line": "support",
        "National Domestic Violence Hotline": "support",
        "Find a helpline in your country": "directory",
    }


def test_the_helpline_directory_is_listed_for_every_country():
    assert [r.url for r in crisis.resources_for("fr")] == ["https://findahelpline.com"]
    assert [r.kind for r in crisis.resources_for("fr")] == ["directory"]
    assert len(crisis.resources_for()) == 5


def test_every_number_the_pause_reply_names_is_a_listed_resource():
    listed = {number for r in crisis.RESOURCES for number in (r.phone, r.sms) if number}
    for about in ("themselves", "someone_else", "from_someone", "body", None):
        named = set(re.findall(r"\d[\d-]+\d", crisis.pause_reply(about, 30)))
        assert "911" in named and named <= listed, about


def test_the_pause_reply_fits_whose_danger_it_is():
    """The live replays of 2026-11-13: one reply went out for chest pain, a bee sting, a stroke and a friend's overdose,
    saying "your safety" and offering suicide lines for a body emergency."""
    themselves = crisis.pause_reply("themselves", 900)
    assert "your safety" in themselves and "988" in themselves and "15 minutes" in themselves
    assert "pausing our chat for 30 seconds." in crisis.pause_reply("themselves", 30)
    assert "everyone's safety" in crisis.pause_reply("someone_else", 900)
    assert "your safety" in crisis.pause_reply("from_someone", 900), "the danger is to them"
    for other in ("someone_else", "from_someone"):
        assert "988" not in crisis.pause_reply(other, 900)
    body = crisis.pause_reply("body", 900)
    assert "your health" in body and "911" in body and "988" not in body
    assert crisis.pause_reply(None, 900) == themselves, "an unknown danger keeps the suicide line"
    for about in ("themselves", "someone_else", "from_someone", "body"):
        assert crisis.pause_reply(about, 900).endswith("We can talk again when you come back."), about


def test_the_pause_reply_leads_with_where_to_get_help_and_the_length_comes_after():
    """S6 (PROVISIONAL: clinician sign-off required before deploy): the pause is a safety screen, not a countdown
    (Lolly, 2026-11-18: a timer must never be the primary intervention). Its first words are the help, 911 first, so an
    overdose leads with 911 (R90); the length is said once, after it."""
    for about in ("themselves", "someone_else", "from_someone", "body", None):
        reply = crisis.pause_reply(about, 900)
        first_line = reply.split("\n\n")[0]
        assert "911" in first_line and "15 minutes" not in first_line, about
        assert first_line.index("911") < first_line.index("988") if "988" in first_line else True, about
        assert reply.count("15 minutes") == 1, about


def test_every_resources_text_gives_the_us_numbers_and_the_directory_for_everywhere_else():
    """S11 and S9 (PROVISIONAL: clinician sign-off required before deploy): no country detection, so every text that
    says where to get help names 911, and findahelpline.com for anyone outside the US. The outage reply while a worry
    is held named no number at all ("contact your local emergency number")."""
    texts = {
        "IN_DANGER": crisis.IN_DANGER, "CRISIS_REPLY": crisis.CRISIS_REPLY, "TROUBLE_REPLY": crisis.TROUBLE_REPLY,
        **{f"resources_line({about})": crisis.resources_line(about)
           for about in ("themselves", "someone_else", "from_someone", "body", None)},
        "RETURN_CHECK_REPLY": crisis.RETURN_CHECK_REPLY,
        "RETURN_DANGER_REPLY": crisis.RETURN_DANGER_REPLY,
        **{f"pause_reply({about})": crisis.pause_reply(about, 900)
           for about in ("themselves", "someone_else", "from_someone", "body", None)},
    }
    for name, text in texts.items():
        assert "911" in text and "findahelpline.com" in text, name
    for name in ("IN_DANGER", "CRISIS_REPLY", "TROUBLE_REPLY", "RETURN_CHECK_REPLY", "RETURN_DANGER_REPLY"):
        assert "988" in texts[name], name


def test_danger_from_someone_names_the_domestic_violence_hotline():
    """S14 (PROVISIONAL: clinician sign-off required before deploy): threats, coercion or abuse with fear for their
    safety are danger from someone, and its help adds the National Domestic Violence Hotline (R152)."""
    for text in (crisis.pause_reply("from_someone", 900), crisis.resources_line("from_someone")):
        assert "1-800-799-7233" in text and "START to 88788" in text and "911" in text
    for about in ("themselves", "someone_else", "body", None):
        assert "799-7233" not in crisis.resources_line(about), about


def test_the_body_line_says_call_911_if_it_is_happening_now_without_judging_the_symptom():
    """S13 (PROVISIONAL: clinician sign-off required before deploy): Safety Guardrails section 2 allows no interpreting
    of a physical symptom or comment on its severity, so the line never calls it an emergency."""
    for text in (crisis.resources_line("body"), crisis.pause_reply("body", 900)):
        assert "If this is happening now, call 911." in text
        assert "emergency" not in text.lower() and "988" not in text


def test_no_fixed_safety_text_says_a_banned_line_or_a_forbidden_word():
    """CR-6: code's own safety words are sent untouched, so they must hold the rules themselves; the old pause line said
    "I'll be here when you come back". PROVISIONAL: clinician sign-off required before deploy."""
    fixed = [crisis.IN_DANGER, crisis.CRISIS_REPLY, crisis.TROUBLE_REPLY, crisis.END_CHECK, crisis.RETURN_CHECK_REPLY,
             crisis.RETURN_DANGER_REPLY, crisis.AFTER_PAUSE_FOLLOW_UP]
    fixed += [crisis.pause_reply(about, 900) for about in ("themselves", "someone_else", "from_someone", "body", None)]
    fixed += [crisis.resources_line(about) for about in ("themselves", "someone_else", "from_someone", "body")]
    for text in fixed:
        assert not enforce.banned_phrases(text) and not enforce.forbidden_words(text), text


def test_a_reply_that_names_the_numbers_but_not_the_outside_us_line_gets_only_that_line():
    """muhammad's local test of "honestly I wish I were dead" (2026-11-25): the reply named 988 and 911 but not
    findahelpline.com, so code added nothing and someone outside the US had no line (S9 to S11); the next test of TC-S3
    then said 911 and 988 twice when the whole line was added for the directory alone. PROVISIONAL: clinician
    sign-off required before deploy."""
    reply = ("That's a lot to be carrying, and I'm glad you said it to me.\n\nI take that seriously. Please call or text "
             "988 right now, it's free and open any time. If you feel like you might act on this, call 911.\n\nYou don't "
             "have to sit with this on your own tonight.\n\nIs there someone who could be with you right now?")
    assert not crisis.names_help(reply, "themselves")
    assert crisis.help_missing(reply, "themselves") == crisis.OUTSIDE_US
    assert crisis.help_missing("Please call 911.", "themselves") == crisis.resources_line("themselves")
    for about in ("themselves", "someone_else", "from_someone", "body", None):
        assert crisis.names_help(crisis.resources_line(about), about), about


def test_the_first_message_back_asks_about_immediate_danger_with_the_help():
    """CR-5 (PROVISIONAL: clinician sign-off required before deploy): the danger a pause rested on is still open when
    they come back, so code's question is the question of immediate danger, with the numbers."""
    for about in ("themselves", None):
        text = crisis.return_check_reply(about)
        assert crisis.IMMEDIACY_QUESTION in text and crisis.names_help(text, "themselves"), about
    assert crisis.IMMEDIACY_QUESTION not in crisis.return_check_reply("body")
    assert crisis.names_help(crisis.return_check_reply("body"), "body")
