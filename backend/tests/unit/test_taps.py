# ABOUTME: What a tapped button means for the turn: which framework starts, when the five steps or the walk-through
# ABOUTME: are due, when an offer is set aside, and what the reply is told; a stale button means nothing.

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
    assert "from the whole story to one moment" in fact


def test_the_three_lead_in_buttons_are_three_different_experiences():
    """Lolly, 2026-11-20: Not sure explains, Show me how demonstrates on their situation, Give me a tool begins."""
    not_sure = tap_event(SmartPrompt(label="Not sure"), REGISTRY, offered("abcde"))
    assert not_sure.explain.id == "abcde" and not_sure.starting is None and not_sure.demonstrate is None
    show = tap_event(SmartPrompt(label="Show me how"), REGISTRY, offered("abcde"))
    assert show.demonstrate.id == "abcde" and show.starting is None and show.explain is None
    assert "only what they have told you" in show.fact and "never invent" in show.fact
    assert "theirs to fill in" in show.fact
    tool = tap_event(SmartPrompt(label="Give me a tool"), REGISTRY, offered("abcde"))
    assert tool.starting.id == "abcde" and tool.explain is None
    assert '"A is for Activating Event."' in tool.fact and "B is for" not in tool.fact


def test_a_lead_in_button_with_no_offer_open_means_nothing_to_the_offer():
    for label in ("Not sure", "Show me how", "Give me a tool"):
        event = tap_event(SmartPrompt(label=label), REGISTRY, None)
        assert (event.explain, event.demonstrate, event.starting) == (None, None, None), label


def test_talk_more_first_sets_the_offer_aside_and_never_declines_it():
    event = tap_event(SmartPrompt(label="Talk more first"), REGISTRY, offered("abcde", "steps"))
    assert event.set_aside is True and event.starting is None and event.fact


def test_no_tap_means_nothing():
    event = tap_event(None, REGISTRY, offered("abcde"))
    assert (event.fact, event.starting, event.set_aside, event.explain) == (None, None, False, None)


def test_a_frameworks_stages_are_its_phases_after_the_offer():
    assert stages_of(REGISTRY.get("abcde")) == ["activate", "belief", "consequence", "dispute", "effective"]


def test_an_old_keep_chatting_button_sets_the_offer_aside():
    """The final review, 2026-11-18: a decline button stored before the client's sequence read as the closing Keep
    Chatting, and the person who said no got the five steps."""
    event = tap_event(SmartPrompt(label="Keep chatting", decline=True), REGISTRY, offered("abcde"))
    assert event.set_aside is True and event.explain is None
