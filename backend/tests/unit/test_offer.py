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
    ready = decide(routing(), style="supportive", their_messages=7, cooldown_passed=True)
    assert ready.action is Action.OFFER_FRAMEWORK


@pytest.mark.parametrize("style, soonest", [("direct", 3), ("supportive", 7), ("reflective", 7)])
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
def test_past_the_window_the_closest_fit_is_offered_rather_than_another_question(status):
    """The cadence exists so the conversation arrives somewhere: past Direct's fifth message,
    another question is the worse answer."""
    route = ambiguous() if status is sr.RouteStatus.AMBIGUOUS else routing(status)
    assert decide(route, style="direct", their_messages=5, cooldown_passed=True).action is Action.OFFER_FRAMEWORK


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
