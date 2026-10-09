# ABOUTME: Checks which words an offer turn and a Tell me more send: the seeded offer for every set,
# ABOUTME: and a framework's own Tell me more where the client wrote one. Built on the shipped files.

from __future__ import annotations

import pytest

from mani.chat import offer as offers
from mani.models.rows import Framework
from scripts.seed import FRAMEWORKS_DIR, load_replies, parse_framework

REPLIES = load_replies()
ANSWER = "We'd look at what happened and what you told yourself about it."


def _framework(framework_id: str) -> Framework:
    return Framework.model_validate(parse_framework(FRAMEWORKS_DIR / f"{framework_id}.md"))


def _seeded(template: str, framework: Framework) -> str:
    return template.format(name=framework.name, description=framework.description)


@pytest.mark.parametrize("framework_id", ["abcde", "structured_problem_solving"])
def test_every_set_is_offered_in_the_seeded_words_alone(framework_id):
    framework = _framework(framework_id)

    text, buttons = offers.offer(REPLIES, framework, "Want to try?", answering=False)

    assert text == _seeded(REPLIES.offer.text, framework)
    assert text.startswith("We'll go through a few focused questions.")
    assert f"Framework: {framework.name}\n\n{framework.description}" in text
    assert [b["label"] for b in buttons] == ["Try It", "Tell Me More", "Keep Chatting"]


def test_an_answer_to_a_typed_question_goes_before_the_offer():
    abcde = _framework("abcde")

    text, _ = offers.offer(REPLIES, abcde, ANSWER, answering=True)

    assert text == f"{ANSWER}\n\n{_seeded(REPLIES.offer.text, abcde)}"


@pytest.mark.parametrize("style", ["direct", "supportive", "reflective"])
def test_tell_me_more_is_the_clients_own_wording_where_it_exists(style):
    text, _ = offers.told_more(REPLIES, _framework("abcde"), style)

    assert text == REPLIES.offer.by_framework["abcde"][style].more_text


def test_tell_me_more_is_the_name_and_description_for_the_rest():
    solving = _framework("structured_problem_solving")

    text, buttons = offers.told_more(REPLIES, solving, "direct")

    assert text == f"Framework: {solving.name}\n\n{solving.description}"
    assert [b["label"] for b in buttons] == ["Try It", "Keep Chatting"]
