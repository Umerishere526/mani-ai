# ABOUTME: What a tapped button means for the turn: which framework starts, which offer is declined, when the fixed
# ABOUTME: explanation is due, and what the reply is told; a tap on a stale button means nothing.

from mani.chat.taps import tap_event
from mani.chat.techniques import stages_of
from mani.llm.schema import SmartPrompt
from tests.unit.frameworks import REGISTRY, offered


def test_try_it_starts_only_the_framework_on_the_offer_that_is_still_open():
    tap = SmartPrompt(label="Try it", technique="abcde")
    assert tap_event(tap, REGISTRY, offered("abcde")).starting.id == "abcde"
    assert tap_event(tap, REGISTRY, None).starting is None
    assert tap_event(tap, REGISTRY, offered("thought_reframe")).starting is None


def test_try_it_tells_the_reply_the_first_stage_and_its_line():
    fact = tap_event(SmartPrompt(label="Try it", technique="abcde"), REGISTRY, offered("abcde")).fact
    assert '"A is for Activating Event."' in fact and "Never further." in fact


def test_keep_chatting_on_an_open_offer_declines_it():
    event = tap_event(SmartPrompt(label="Keep chatting", decline=True), REGISTRY, offered("abcde"))
    assert event.declined == "abcde" and event.starting is None


def test_tell_me_more_asks_for_the_fixed_explanation():
    assert tap_event(SmartPrompt(label="Tell me more"), REGISTRY, offered("abcde")).explain.id == "abcde"
    assert tap_event(SmartPrompt(label="Tell me more"), REGISTRY, None).explain is None


def test_finish_for_now_after_the_questions_asks_for_a_goodbye():
    event = tap_event(SmartPrompt(label="Finish for Now"), REGISTRY, None)
    assert event.closing == "finish" and "ask nothing" in event.fact


def test_no_tap_means_nothing():
    event = tap_event(None, REGISTRY, offered("abcde"))
    assert (event.fact, event.starting, event.declined, event.explain, event.closing) == (None, None, None, None, None)


def test_a_frameworks_stages_are_its_phases_after_the_offer():
    assert stages_of(REGISTRY.get("abcde")) == ["activate", "belief", "consequence", "dispute", "effective"]
