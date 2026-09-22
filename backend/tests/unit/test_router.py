# ABOUTME: Routing accuracy as a test rather than a bill - the router makes no model call.
# ABOUTME: Driven by the shipped framework content, so drift in a phrase list fails here.

import pytest

from mani.chat.router import is_confident, shortlist
from scripts.seed import FRAMEWORKS_DIR, parse_framework

# The shipped activation data, parsed by the seeder itself - the same structures that reach
# admin.frameworks and then Registry.activations at runtime. A hand-written copy used to
# stand here, and it passed while sharing almost no phrases with the content actually
# deployed, which is the one thing this suite must never do. No database: the markdown is
# the input to both, so routing accuracy stays a test that always runs.
ACTIVATIONS: dict[str, dict] = {
    f["id"]: f["activation"]
    for f in (parse_framework(path) for path in sorted(FRAMEWORKS_DIR.glob("*.md")))
}


def top(messages: list[str]) -> str | None:
    ranked = shortlist(messages, ACTIVATIONS)
    return ranked[0].framework_id if ranked else None


# ---------------------------------------------------------------------------
# The central indication of each framework routes to that framework
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("My manager criticized my work, so I must be incompetent", "abcde"),
        ("Nobody cares about me", "thought_reframe"),
        ("I have been in bed all day. I cannot make myself do anything", "behavioral_activation"),
        ("I am behind on everything and do not know where to begin", "structured_problem_solving"),
        ("I cannot change what happened and it is still directing my choices", "act_choice_point"),
        ("I am furious. I am about to send a message I will regret", "dbt_stop"),
    ],
)
def test_the_specifications_own_examples_route_correctly(message, expected):
    assert top([message]) == expected


# ---------------------------------------------------------------------------
# Discriminators, from "Important Framework Distinctions"
# ---------------------------------------------------------------------------


def test_an_imminent_action_outranks_everything():
    """The specification treats impulsivity as time-critical: STOP comes before analysis."""
    messages = [
        "I keep thinking nobody cares about me",
        "I am about to send a message I may regret",
    ]
    ranked = shortlist(messages, ACTIVATIONS)
    assert ranked[0].framework_id == "dbt_stop"
    assert ranked[0].promoted_by == "an action is imminent"


def test_an_uncontrollable_outcome_prefers_acceptance_over_reframing():
    """"Use ACT Choice Point when debating whether the thought is true would not help."

    Thought Reframe scores higher on the recent message; the discriminator still wins."""
    messages = ["I cannot change what happened", "she hates me"]
    ranked = shortlist(messages, ACTIVATIONS)
    assert [s.framework_id for s in ranked[:2]] == ["act_choice_point", "thought_reframe"]


def test_knowing_what_to_do_prefers_activation_over_problem_solving():
    messages = ["I do not know where to begin", "I know what to do but cannot make myself start"]
    ranked = shortlist(messages, ACTIVATIONS)
    ids = [s.framework_id for s in ranked]
    assert ids.index("behavioral_activation") < ids.index("structured_problem_solving")


def test_not_knowing_what_to_do_prefers_problem_solving_over_activation():
    messages = ["I have stopped answering people", "I do not know what to do next"]
    ranked = shortlist(messages, ACTIVATIONS)
    ids = [s.framework_id for s in ranked]
    assert ids.index("structured_problem_solving") < ids.index("behavioral_activation")


def test_a_specific_event_prefers_the_deeper_framework():
    """"Use ABCDE when the user wants to understand the deeper sequence." Thought Reframe is
    the lighter default, so an event marker is what tips it."""
    messages = ["I am a failure", "my manager criticized me in front of the team"]
    ranked = shortlist(messages, ACTIVATIONS)
    ids = [s.framework_id for s in ranked]
    assert ids.index("abcde") < ids.index("thought_reframe")


# ---------------------------------------------------------------------------
# Shape and cost
# ---------------------------------------------------------------------------


def test_the_most_recent_message_carries_the_most_weight():
    """What someone needs now is what they just said, not what they opened with."""
    recent_wins = shortlist(
        ["nobody cares about me", "I have stopped answering people and stopped cooking"],
        ACTIVATIONS,
    )
    assert recent_wins[0].framework_id == "behavioral_activation"


def test_nothing_recognisable_returns_nothing():
    """Silence is a valid answer. The prompt then carries the index, not a guess."""
    assert shortlist(["I went to the shop and bought some bread"], ACTIVATIONS) == []
    assert shortlist([], ACTIVATIONS) == []
    assert shortlist(["nobody cares about me"], {}) == []


def test_the_shortlist_is_bounded():
    """The whole point is never shipping all six frameworks' content in one prompt."""
    messages = [
        "nobody cares about me and I am a failure, everything is a mess, "
        "I cannot make myself start, I cannot change what happened, "
        "and I am about to send a message"
    ]
    assert len(shortlist(messages, ACTIVATIONS)) <= 3
    assert len(shortlist(messages, ACTIVATIONS, limit=2)) == 2


def test_confidence_decides_how_much_content_the_prompt_carries():
    assert not is_confident([])
    # One incidental phrase is a suggestion, not a finding.
    weak = shortlist(["I keep canceling plans"], ACTIVATIONS)
    assert weak and not is_confident(weak)


def test_a_strong_phrase_said_once_is_not_yet_confident():
    """A central-indication phrase clears the score and margin on its own, but a single mention
    could be a passing line rather than an established situation. Confidence needs it said more
    than once - across messages, or twice within one - before the model gets the full offer."""
    single_mention = shortlist(["I cannot make myself start anything"], ACTIVATIONS)
    assert single_mention[0].score >= 2.0
    assert not is_confident(single_mention)


def test_corroboration_across_two_messages_is_confident():
    corroborated = shortlist(
        ["I keep avoiding the task", "I cannot make myself start anything"], ACTIVATIONS
    )
    assert is_confident(corroborated)


def test_corroboration_within_one_message_is_confident():
    corroborated = shortlist(
        ["I cannot make myself start, and I have stopped cooking too"], ACTIVATIONS
    )
    assert is_confident(corroborated)


def test_an_imminent_action_is_confident_on_one_mention():
    """DBT STOP exists because waiting costs something - the message it would pause may
    already be sent by the time a second mention arrives. Corroboration is right to ask for
    patience everywhere else, but not here."""
    urgent = shortlist(["I am about to send a message I may regret"], ACTIVATIONS)
    assert urgent[0].framework_id == "dbt_stop"
    assert urgent[0].time_critical
    assert is_confident(urgent)


def test_a_framework_absent_from_the_registry_is_never_returned():
    """Model-supplied ids are already checked in repairs; the router must not invent one."""
    ranked = shortlist(["I am about to send a message I may regret"], {"abcde": ACTIVATIONS["abcde"]})
    assert all(s.framework_id == "abcde" for s in ranked)
