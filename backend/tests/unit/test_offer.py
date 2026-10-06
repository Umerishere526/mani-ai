# ABOUTME: What each turn decides to do, given routing and the state of the conversation.
# ABOUTME: The priority order is the point: the person comes before the framework.

import pytest

from mani.chat import semantic_router as sr
from mani.chat.offer import Action, cadence_for, decide


def routing(status=sr.RouteStatus.MATCH, framework_id="abcde", margin=0.2, **kw):
    candidates = ()
    if framework_id is not None:
        candidates = (sr.Candidate(framework_id, 0.6, margin, **kw),)
    return sr.Routing(status, candidates)


def ambiguous(first="abcde", second="thought_reframe"):
    return sr.Routing(
        sr.RouteStatus.AMBIGUOUS,
        (sr.Candidate(first, 0.6, 0.0), sr.Candidate(second, 0.58, 0.02)),
    )


def test_a_clear_fit_inside_the_window_is_offered():
    decision = decide(routing(), style="direct", their_messages=3, cooldown_passed=True)
    assert decision.action is Action.OFFER_FRAMEWORK
    assert decision.framework_id == "abcde"


def test_a_clear_fit_before_the_style_is_ready_asks_instead():
    """Direct offers soonest at 3; Supportive earns the room to explore first."""
    early = decide(routing(), style="supportive", their_messages=3, cooldown_passed=True)
    assert early.action is Action.ASK
    ready = decide(routing(), style="supportive", their_messages=5, cooldown_passed=True)
    assert ready.action is Action.OFFER_FRAMEWORK


@pytest.mark.parametrize("style, soonest", [("direct", 3), ("supportive", 5), ("reflective", 6)])
def test_each_style_offers_no_earlier_than_its_cadence(style, soonest):
    assert decide(routing(), style=style, their_messages=soonest - 1, cooldown_passed=True).action is Action.ASK
    assert decide(routing(), style=style, their_messages=soonest, cooldown_passed=True).action is Action.OFFER_FRAMEWORK


def test_an_unknown_style_falls_back_rather_than_crashing():
    assert cadence_for(None) == cadence_for("supportive")
    assert decide(routing(), style="shouty", their_messages=9, cooldown_passed=True).action is Action.OFFER_FRAMEWORK


def test_safety_outranks_everything():
    decision = decide(
        routing(), style="direct", their_messages=9, cooldown_passed=True, safety_concern=True,
    )
    assert decision.action is Action.CONTINUE
    assert not decision.offers


def test_safety_outranks_even_an_imminent_action():
    decision = decide(
        routing(framework_id="dbt_stop", time_critical=True),
        style="direct", their_messages=9, cooldown_passed=True, safety_concern=True,
    )
    assert decision.action is Action.CONTINUE


def test_a_running_framework_outranks_a_clear_fit_for_another():
    decision = decide(
        routing(), style="direct", their_messages=9, cooldown_passed=True, framework_running=True,
    )
    assert decision.action is Action.CONTINUE_STAGE
    assert not decision.offers


def test_the_final_stage_closes():
    decision = decide(
        routing(), style="direct", their_messages=9, cooldown_passed=True,
        framework_running=True, finishing=True,
    )
    assert decision.action is Action.CLOSE


def test_asking_only_to_be_heard_outranks_a_clear_fit():
    decision = decide(
        routing(), style="direct", their_messages=9, cooldown_passed=True, their_last="heard",
    )
    assert decision.action is Action.CONTINUE
    assert not decision.offers


@pytest.mark.parametrize("their_last", ["correction", "about_mani"])
def test_a_correction_is_answered_before_any_offer(their_last):
    decision = decide(
        routing(), style="direct", their_messages=9, cooldown_passed=True, their_last=their_last,
    )
    assert decision.action is Action.ASK
    assert not decision.offers


def test_an_imminent_action_does_not_wait_for_the_cadence():
    """About to send the message they will regret, on their first message."""
    decision = decide(
        routing(framework_id="dbt_stop", time_critical=True),
        style="supportive", their_messages=1, cooldown_passed=False,
    )
    assert decision.action is Action.OFFER_FRAMEWORK
    assert decision.framework_id == "dbt_stop"


def test_a_framework_their_words_rule_out_is_never_offered():
    """Behavioral Activation after a loss, for instance - demoted here, not caught later."""
    decision = decide(
        routing(framework_id="behavioral_activation"),
        style="direct", their_messages=9, cooldown_passed=True,
        vetoed=("behavioral_activation",),
    )
    assert decision.action is Action.ASK
    assert not decision.offers


def test_the_cooldown_still_holds_a_clear_fit():
    decision = decide(routing(), style="direct", their_messages=9, cooldown_passed=False)
    assert decision.action is Action.ASK


def test_a_changed_topic_follows_them_rather_than_offering():
    changed = sr.Routing(sr.RouteStatus.MATCH, (sr.Candidate("abcde", 0.6, 0.2),), topic_changed=True)
    decision = decide(changed, style="direct", their_messages=9, cooldown_passed=True)
    assert decision.action is Action.ASK
    assert decision.why == "topic changed"


def test_two_plausible_fits_ask_what_separates_them():
    decision = decide(ambiguous(), style="direct", their_messages=3, cooldown_passed=True)
    assert decision.action is Action.CLARIFY
    assert decision.separates == ("abcde", "thought_reframe")


def test_nothing_fitting_follows_them_and_offers_nothing():
    decision = decide(
        sr.Routing(sr.RouteStatus.NO_MATCH, ()), style="direct", their_messages=9, cooldown_passed=True,
    )
    assert decision.action is Action.ASK
    assert decision.framework_id is None
    assert not decision.offers


def test_a_weak_fit_asks_rather_than_offering_inside_the_window():
    decision = decide(
        routing(sr.RouteStatus.WEAK_MATCH), style="direct", their_messages=3, cooldown_passed=True,
    )
    assert decision.action is Action.ASK


@pytest.mark.parametrize("status", [sr.RouteStatus.WEAK_MATCH, sr.RouteStatus.AMBIGUOUS])
def test_a_fit_that_is_only_the_closest_is_never_offered_however_long_they_talk(status):
    """Nobody is handed a framework because the conversation has gone on (muhammad,
    2026-10-06). Only a clear fit is ever offered; everything else keeps talking."""
    route = ambiguous() if status is sr.RouteStatus.AMBIGUOUS else routing(status)
    decision = decide(route, style="direct", their_messages=12, cooldown_passed=True)
    assert not decision.offers


def test_nothing_fitting_is_never_rounded_up_to_the_nearest_framework():
    """No match past the window is still no offer: a nearest neighbour is not a fit."""
    decision = decide(
        sr.Routing(sr.RouteStatus.NO_MATCH, ()), style="direct", their_messages=12, cooldown_passed=True,
    )
    assert not decision.offers


def test_accepting_starts_the_framework():
    decision = decide(
        routing(), style="direct", their_messages=3, cooldown_passed=True, accepted_this_turn=True,
    )
    assert decision.action is Action.START_FRAMEWORK


def test_the_same_inputs_always_give_the_same_decision():
    kwargs = dict(style="direct", their_messages=3, cooldown_passed=True)
    assert decide(routing(), **kwargs) == decide(routing(), **kwargs)


def test_the_question_that_separates_two_sets_is_asked_once_not_every_turn():
    """Their answer says which set fits, not what happened, so it rarely moves the vectors:
    without this the same clarify question is asked every turn forever."""
    first = decide(ambiguous(), style="direct", their_messages=3, cooldown_passed=True)
    assert first.action is Action.CLARIFY

    # Their answer is the evidence: the nearest of the two is offered rather than asked about
    # again, once the style's cadence has given them the room it gives.
    answered = decide(
        ambiguous(), style="direct", their_messages=4, cooldown_passed=True,
        clarified_already=True,
    )
    assert answered.action is Action.OFFER_FRAMEWORK

    # Still inside the cadence, it waits rather than offering early.
    early = decide(
        ambiguous(), style="direct", their_messages=1, cooldown_passed=True,
        clarified_already=True,
    )
    assert early.action is Action.ASK
    assert not early.offers


def weak_with_shortlist(*ids):
    """What "I am in pain" produces: nothing clear enough to act on, but a ranked few behind
    it. Mirrors the real router, which carries `nearest` whatever the status."""
    near = tuple(sr.Candidate(f, 0.38 - i * 0.02, 0.0) for i, f in enumerate(ids))
    return sr.Routing(sr.RouteStatus.NO_MATCH, (), nearest=near)


def test_something_real_that_points_nowhere_is_assessed_never_offered():
    """"I am in pain" names no framework. The shortlist says what it might be about, which is
    what to ask about, and an offer on a shortlist would be guessing (muhammad, 2026-10-06)."""
    decision = decide(
        weak_with_shortlist("act_choice_point", "behavioral_activation", "abcde"),
        style="direct", their_messages=1, cooldown_passed=True,
    )
    assert decision.action is Action.ASSESS
    assert not decision.offers
    assert decision.framework_id is None, "nothing is chosen on an assessment turn"
    assert decision.shortlist == ("act_choice_point", "behavioral_activation", "abcde")


def test_a_conversation_that_never_names_a_framework_goes_to_the_fallback():
    """Assessed to the top of the window and still nothing: these lead to ABCDE rather than
    the closest of a shortlist that never separated (muhammad, 2026-10-06)."""
    route = weak_with_shortlist("act_choice_point", "behavioral_activation")
    for n in (1, 3, 4):
        early = decide(route, style="direct", their_messages=n, cooldown_passed=True, fallback="abcde")
        assert early.action is Action.ASSESS, f"at {n} messages"
    landed = decide(route, style="direct", their_messages=5, cooldown_passed=True, fallback="abcde")
    assert landed.action is Action.OFFER_FRAMEWORK
    assert landed.framework_id == "abcde"


def test_the_fallback_is_refused_when_their_words_rule_it_out():
    """The grief veto outranks it: a fallback is still an offer."""
    decision = decide(
        weak_with_shortlist("abcde"), style="direct", their_messages=9,
        cooldown_passed=True, fallback="abcde", vetoed=frozenset({"abcde"}),
    )
    assert not decision.offers


def test_two_real_fits_are_told_apart_rather_than_sent_to_the_fallback():
    """Ambiguous means two frameworks genuinely fit, so the question that separates them is
    the answer - not ABCDE, which is only for a conversation that names nothing."""
    decision = decide(
        ambiguous("thought_reframe", "abcde"), style="direct", their_messages=12,
        cooldown_passed=True, fallback="abcde",
    )
    assert decision.action is Action.CLARIFY


def test_being_heard_still_comes_before_assessing():
    """Someone who asked only to be listened to is not assessed at them."""
    decision = decide(
        weak_with_shortlist("abcde"), style="direct", their_messages=3,
        cooldown_passed=True, their_last="heard",
    )
    assert decision.action is Action.CONTINUE


def test_nothing_at_all_to_go_on_just_follows_them():
    decision = decide(
        sr.Routing(sr.RouteStatus.NO_MATCH, ()), style="direct", their_messages=3,
        cooldown_passed=True,
    )
    assert decision.action is Action.ASK
    assert not decision.offers


@pytest.mark.parametrize("style, soonest", [("direct", 3), ("supportive", 5), ("reflective", 6)])
def test_the_styles_reach_a_framework_at_muhammads_cadence(style, soonest):
    """Direct 3-5, Supportive 5-7, Reflective 6-8 (muhammad, 2026-10-06). A deviation from the
    client's styles document, which gives every style two to four."""
    assert cadence_for(style)[0] == soonest
