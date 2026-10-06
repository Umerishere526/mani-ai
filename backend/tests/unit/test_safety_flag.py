# ABOUTME: Checks how the kind on a model's safety flag is read and which kinds pause a framework.
# ABOUTME: Only `other` leaves a running framework going; anything missing or unreadable pauses.

import pytest

from mani.chat import safety
from mani.llm.schema import Crisis, Reply

REAL_KINDS = [c.value for c in safety.Category]


@pytest.mark.parametrize("kind", REAL_KINDS)
def test_every_kind_the_screen_uses_pauses_a_framework(kind):
    assert safety.flag_pauses(kind)
    assert safety.flag_kind(kind) == kind


def test_other_is_the_only_kind_that_does_not_pause():
    assert not safety.flag_pauses("other")
    assert [k for k in REAL_KINDS if not safety.flag_pauses(k)] == []


@pytest.mark.parametrize("said", ["OTHER", " other ", "Other.", "other!", "OTHER,"])
def test_other_is_read_ignoring_case_spacing_and_trailing_punctuation(said):
    assert safety.flag_kind(said) == "other"
    assert not safety.flag_pauses(said)


@pytest.mark.parametrize("said,kind", [
    ("Self Harm", "self_harm"), ("self-harm", "self_harm"), ("ABUSE_OR_VIOLENCE", "abuse_or_violence"),
    ("medical emergency.", "medical_emergency"),
])
def test_a_kind_is_read_with_spaces_and_hyphens_as_underscores(said, kind):
    assert safety.flag_kind(said) == kind


@pytest.mark.parametrize("said", [None, "", "   ", "banana", "others", "not other", 3, ["other"], {"kind": "other"}, True])
def test_a_missing_or_unreadable_kind_pauses_and_is_never_logged_as_written(said):
    assert safety.flag_pauses(said)
    assert safety.flag_kind(said) == "unspecified"


def test_a_flag_with_a_kind_and_no_reason_is_read():
    reply = Reply.model_validate({"text": "I am here.", "crisis": {"category": "suicide"}})
    assert reply.crisis.category == "suicide"
    assert reply.crisis.reason == ""


@pytest.mark.parametrize("value", [3, ["other"], {"a": 1}, True])
def test_a_kind_that_is_not_text_reads_as_none_so_the_reply_is_kept(value):
    crisis = Crisis.model_validate({"reason": "x", "category": value})
    assert crisis.category is None
    assert safety.flag_pauses(crisis.category)


def test_the_description_names_all_nine_kinds_in_one_place():
    description = Crisis.model_fields["category"].description
    for kind in REAL_KINDS + ["other"]:
        assert kind in description


def _prompt_section() -> str:
    import pathlib

    text = (pathlib.Path(__file__).parents[2] / "content/prompts/response_format.md").read_text()
    start = text.index("# The safety flag")
    return text[start : text.index("\n# ", start + 1)]


def test_the_system_prompt_and_the_description_each_name_exactly_the_kinds_the_code_reads():
    """Measured 2026-10-04: with the kinds only in the schema description, the model wrote its own
    labels ("safety", "impulsive reaction") and 140 of 150 flags read as no kind. The prompt is what
    it follows, so both texts must name the same set the code reads, and no other word."""
    import re

    in_prompt = set(re.findall(r"`([a-z_]+)`", _prompt_section())) - {"crisis", "category"}
    description = Crisis.model_fields["category"].description
    in_description = set(re.search(r"one of: ([a-z_, ]+)\.", description).group(1).split(", "))
    assert in_prompt == safety.FLAG_KINDS
    assert in_description == safety.FLAG_KINDS


def test_the_prompt_sends_doubt_to_a_danger_kind_and_names_what_not_to_flag():
    section = _prompt_section()
    assert "When it is unclear, use the kind that fits, not `other`" in section
    assert "ordinary sadness, frustration, hopelessness, exhaustion or a physical injury" in section
    assert "a heated moment" in section


def test_the_description_is_never_more_permissive_than_the_prompt_on_doubt():
    description = Crisis.model_fields["category"].description
    assert "choose the kind that fits, not other" in " ".join(
        Reply.model_fields["crisis"].description.split()
    )
    assert "Use other only for something you thought about that is not danger" in description


def test_both_texts_send_a_threat_to_hurt_someone_to_a_danger_kind_not_other():
    """Measured 2026-10-04: without this, "I will make him regret it" came back other in 2 of 5 runs."""
    description = " ".join(Reply.model_fields["crisis"].description.split())
    assert "A threat or a wish to hurt a person is harm_to_other, even when it is angry or vague, never other" in description
    assert "A threat or a wish to hurt a person is `harm_to_other`, even when it is angry or" in _prompt_section()



def test_a_flag_with_a_null_reason_is_read_and_still_pauses():
    reply = Reply.model_validate({"text": "I am here.", "crisis": {"reason": None, "category": "suicide"}})
    assert reply.crisis.reason == ""
    assert safety.flag_pauses(reply.crisis.category)
