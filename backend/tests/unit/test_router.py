# ABOUTME: Routing accuracy as a test rather than a bill - the router makes no model call.
# ABOUTME: Driven by the shipped framework content, so drift in a phrase list fails here.

import pytest

from mani.chat.router import Signal, is_confident, shortlist
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


@pytest.mark.parametrize(
    "message",
    [
        "She did not answer because she is angry",
        "They excluded me because they do not like me",
        "I did not get this job, which proves I will never get hired",
        "My friend has not answered all day, so I know I do not matter to her",
    ],
)
def test_the_thought_reframe_examples_are_not_taken_by_the_deeper_framework(message):
    """Both specifications claim an unanswered message or an exclusion; without a wish for depth
    it is the quick reframe: ABCDE is never the confident pick, and Thought Reframe stays on
    the shortlist for the model to choose."""
    ranked = shortlist([message], ACTIVATIONS)
    assert "thought_reframe" in [s.framework_id for s in ranked]
    assert not (ranked[0].framework_id == "abcde" and is_confident(ranked))


def test_asking_to_understand_why_an_event_hit_so_hard_prefers_the_deeper_framework():
    messages = ["nobody cares about me", "I want to understand why one comment affected me so strongly"]
    ranked = [s.framework_id for s in shortlist(messages, ACTIVATIONS)]
    assert ranked.index("abcde") < ranked.index("thought_reframe")


@pytest.mark.parametrize(
    "message",
    [
        "I am anxious, and I cannot stop thinking that I will fail",
        "I cannot make my family understand",
        "I cannot make my family approve of my decision",
        "I cannot control what they decide",
        "I may never receive an apology",
    ],
)
def test_the_act_choice_point_examples_route_to_it(message):
    """The headline example and the family examples matched nothing until the phrases covered
    them; none of them may be taken by a framework that argues with the thought."""
    assert top([message]) == "act_choice_point"


def test_asking_to_understand_why_is_enough_to_offer_the_deeper_framework():
    """The depth cue stands alone, as a suggestion: nothing else need have scored, and one cue
    is never confident."""
    ranked = shortlist(["I want to understand why that comment affected me so much"], ACTIVATIONS)
    assert [s.framework_id for s in ranked] == ["abcde"]
    assert not is_confident(ranked)


def test_a_loose_event_phrase_does_not_put_the_deeper_framework_on_the_shortlist():
    """Only rules with a specific phrase may offer a framework nothing else scored."""
    assert top(["The meeting was fine, and after that I went home"]) is None


def test_cannot_stop_thinking_alone_is_never_a_confident_choice_point():
    """It is also how a person says they are stuck on a thought that evidence could examine."""
    ranked = shortlist(["I cannot stop thinking I am incompetent"], ACTIVATIONS)
    assert not is_confident(ranked)


def _redirects():
    cases = []
    for framework_id, activation in ACTIVATIONS.items():
        for redirect in activation.get("redirects", []):
            cases.append(pytest.param(
                framework_id, redirect["instead"], redirect["signal"],
                id=f"{framework_id}-to-{redirect['instead']}-{len(redirect['signal'])}",
            ))
    return cases


@pytest.mark.parametrize(("framework_id", "instead", "signal"), _redirects())
def test_each_redirect_example_routes_to_the_framework_it_names(framework_id, instead, signal):
    """The specification's "may fit another framework" statements, as authored in each file."""
    ids = [s.framework_id for s in shortlist([signal], ACTIVATIONS)]
    assert instead in ids
    assert framework_id not in ids or ids.index(instead) < ids.index(framework_id)


@pytest.mark.parametrize(
    "message",
    [
        "I am furious. I am about to send a message I will regret",
        "I already wrote the email",
        "I want to call her right now",
        "I am about to post everything publicly",
        "I keep typing and deleting",
        "I am about to lose it",
        "I need to confront her right now",
        "I am quitting today",
        "I am ending the relationship right now",
        "I am about to make this purchase even though I know I should wait",
        "I need help stopping myself",
    ],
)
def test_the_imminent_action_examples_are_a_confident_stop(message):
    """The specification's own imminent actions: time critical, so one mention is enough."""
    ranked = shortlist([message], ACTIVATIONS)
    assert ranked[0].framework_id == "dbt_stop"
    assert is_confident(ranked)


@pytest.mark.parametrize(
    "message",
    [
        "I want to tell him exactly what I think",
        "I want to say something that will hurt him",
        "I know I will regret it",
    ],
)
def test_an_urge_with_no_sign_the_action_is_imminent_is_only_a_suggestion(message):
    """Planning to say something is not about to say it; the model asks before offering a pause."""
    ranked = shortlist([message], ACTIVATIONS)
    assert ranked[0].framework_id == "dbt_stop"
    assert not is_confident(ranked)


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


# ---------------------------------------------------------------------------
# Matching is on whole words
# ---------------------------------------------------------------------------


def test_a_phrase_inside_a_longer_word_does_not_match():
    """"she hates me" is not in "she hates meetings", and the idiom "I cannot begin to tell
    you" is not someone unable to start anything."""
    assert top(["she hates meetings on mondays"]) != "thought_reframe"
    assert top(["I cannot begin to tell you how good the trip was"]) != "behavioral_activation"


def test_an_idiom_does_not_read_as_an_imminent_action():
    assert top(["that is what I was about to say"]) != "dbt_stop"


# ---------------------------------------------------------------------------
# Corroboration counts a phrase said again
# ---------------------------------------------------------------------------


def test_the_same_phrase_in_two_messages_is_corroboration():
    """The corroboration rule's own comment: "either it recurs across more than one of their
    recent messages". The same words twice is exactly that."""
    ranked = shortlist(
        ["I cannot make myself start anything", "honestly I cannot make myself start anything"],
        ACTIVATIONS,
    )
    assert ranked[0].framework_id == "behavioral_activation"
    assert ranked[0].spread == 2
    assert is_confident(ranked)


# ---------------------------------------------------------------------------
# A rule-based pick can still be confident
# ---------------------------------------------------------------------------


def test_an_imminent_action_is_confident_even_when_its_own_phrases_did_not_match():
    """The rule's phrase is the evidence. STOP promoted with no match of its own used to sit
    at the promotion floor, below the confident score, so the urgent offer never went out."""
    urgent = shortlist(["I am about to quit my job over this"], ACTIVATIONS)
    assert urgent[0].framework_id == "dbt_stop"
    assert is_confident(urgent)


def test_a_promoted_framework_is_not_refused_for_the_margin_its_promotion_created():
    """A distinction rule decides between the leaders; measuring the margin afterwards
    against the framework it just outranked made every such pick unconfident. Its own
    evidence still has to clear the score and corroboration bars."""
    promoted = Signal("act_choice_point", 2.4, ["cannot control", "keeps directing"],
                      promoted_by="the outcome cannot be controlled", spread=2)
    outranked = Signal("thought_reframe", 3.0, ["nobody cares about me"], spread=1)
    assert is_confident([promoted, outranked])

    thin = Signal("act_choice_point", 1.2, ["cannot control"],
                  promoted_by="the outcome cannot be controlled", spread=1)
    assert not is_confident([thin, outranked])


# ---------------------------------------------------------------------------
# Mentioning a person is not an activating event
# ---------------------------------------------------------------------------


def test_mentioning_a_person_does_not_promote_abcde_over_a_thought():
    ranked = shortlist(["my boss keeps ignoring me, nobody cares about me"], ACTIVATIONS)
    assert ranked[0].framework_id == "thought_reframe"


def test_a_framework_lists_what_said_anywhere_rules_it_out():
    from mani.chat.router import vetoes

    activation = ACTIVATIONS["behavioral_activation"]
    assert vetoes(activation, ["I'm sad that my dog died", "it feels empty"]) == ["died"]
    assert vetoes(activation, ["I have been in bed all day"]) == []
    # whole words: a phrase is not found inside a longer word
    assert vetoes({"never_offer_when_said": ["grief"]}, ["a grievance at work"]) == []
