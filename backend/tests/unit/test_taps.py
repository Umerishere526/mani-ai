# ABOUTME: What a tapped button means for the turn: which framework starts, when the five steps or the example are
# ABOUTME: due, when an offer is set aside, and what the reply is told; a tap on a stale button means nothing.

from mani.chat.taps import tap_event
from mani.chat.techniques import stages_of
from mani.llm.schema import SmartPrompt
from tests.unit.frameworks import REGISTRY, offered


def test_start_starts_only_the_framework_on_the_offer_that_is_still_open():
    """An old Try it button from before the client's sequence carries the id too, so it still starts the open offer."""
    for label in ("Start ABCDE", "Try it"):
        tap = SmartPrompt(label=label, technique="abcde")
        assert tap_event(tap, REGISTRY, offered("abcde", "steps")).starting.id == "abcde"
        assert tap_event(tap, REGISTRY, None).starting is None
        assert tap_event(tap, REGISTRY, offered("thought_reframe")).starting is None


def test_start_tells_the_reply_the_first_stage_only():
    fact = tap_event(SmartPrompt(label="Start ABCDE", technique="abcde"), REGISTRY, offered("abcde", "steps")).fact
    assert '"A is for Activating Event."' in fact and "B is for" not in fact and "go on to" not in fact


def test_each_lead_in_button_asks_for_the_five_steps():
    for label in ("Not sure", "Show me how", "Give me a tool"):
        assert tap_event(SmartPrompt(label=label), REGISTRY, offered("abcde")).explain.id == "abcde", label
        assert tap_event(SmartPrompt(label=label), REGISTRY, None).explain is None


def test_i_need_an_example_asks_for_the_worked_example():
    assert tap_event(SmartPrompt(label="I need an example"), REGISTRY, offered("abcde", "steps")).example.id == "abcde"


def test_talk_more_first_sets_the_offer_aside_and_never_declines_it():
    event = tap_event(SmartPrompt(label="Talk more first"), REGISTRY, offered("abcde", "steps"))
    assert event.set_aside is True and event.starting is None and event.fact


def test_finish_for_now_after_the_questions_asks_for_a_goodbye():
    event = tap_event(SmartPrompt(label="Finish for Now"), REGISTRY, None)
    assert "ask nothing" in event.fact


def test_no_tap_means_nothing():
    event = tap_event(None, REGISTRY, offered("abcde"))
    assert (event.fact, event.starting, event.set_aside, event.explain, event.example) == (None, None, False, None, None)


def test_a_frameworks_stages_are_its_phases_after_the_offer():
    assert stages_of(REGISTRY.get("abcde")) == ["activate", "belief", "consequence", "dispute", "effective"]


def test_an_old_keep_chatting_button_sets_the_offer_aside():
    """The final review, 2026-11-18: a decline button stored before the client's sequence read as the closing Keep
    Chatting, and the person who said no got the five steps."""
    event = tap_event(SmartPrompt(label="Keep chatting", decline=True), REGISTRY, offered("abcde"))
    assert event.set_aside is True and event.explain is None
