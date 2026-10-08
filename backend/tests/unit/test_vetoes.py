# ABOUTME: Checks what the person said rules a framework out, driven by the shipped veto phrases.
# ABOUTME: In process with no database, so the grief veto stays a test that always runs.

from mani.chat import vetoes
from scripts.seed import FRAMEWORKS_DIR, parse_framework

# The shipped phrases, parsed by the seeder itself, so drift in a phrase list fails here.
PHRASES: dict[str, list[str]] = {
    f["id"]: f["activation"]["never_offer_when_said"]
    for f in (parse_framework(path) for path in sorted(FRAMEWORKS_DIR.glob("*.md")))
    if "never_offer_when_said" in f["activation"]
}


def test_only_behavioral_activation_is_ruled_out_by_what_the_person_said_anywhere():
    assert list(PHRASES) == ["behavioral_activation"]
    said = ["I'm sad that my dog died", "it feels empty"]
    assert vetoes.ruled_out(PHRASES, said) == ["behavioral_activation"]
    assert vetoes.ruled_out(PHRASES, ["I have been in bed all day"]) == []


def test_a_phrase_is_found_as_whole_words_in_any_message_and_never_inside_a_longer_word():
    phrases = {"abcde": ["grief"], "dbt_stop": ["passed away"], "thought_reframe": ["funeral"]}
    messages = ["a grievance at work", "my gran passed away, it was a funeralhome"]

    assert vetoes.ruled_out(phrases, messages) == ["dbt_stop"]
    assert vetoes.ruled_out(phrases, ["Grief!", "x"]) == ["abcde"]
    assert vetoes.ruled_out(phrases, []) == []
