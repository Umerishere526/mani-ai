# ABOUTME: Checks the crisis pause pop-up: where the pause is read from, that it leads with help (911 first after an
# ABOUTME: overdose) and the time left only after it, and that the chat page shows only the pop-up. Fake backend.

from __future__ import annotations

import base64
import pathlib
import re
from datetime import datetime, timedelta, timezone

import pytest
from streamlit.testing.v1 import AppTest

import client as mani
import crisis_pause

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)
# As GET /v1/crisis/resources lists them.
EMERGENCY = {"country": "US", "kind": "emergency", "name": "Emergency services", "phone": "911", "sms": None,
             "url": None, "hours": None, "description": "For immediate danger to you or someone else."}
LIFELINE = {"country": "US", "kind": "support", "name": "988 Suicide & Crisis Lifeline", "phone": "988", "sms": "988",
            "url": "https://988lifeline.org", "hours": "24/7", "description": "Call, text or chat."}
TEXT_LINE = {"country": "US", "kind": "support", "name": "Crisis Text Line", "phone": None, "sms": "741741",
             "url": None, "hours": "24/7", "description": "Text HOME."}
DIRECTORY = {"country": "US", "kind": "directory", "name": "Find a helpline in your country", "phone": None,
             "sms": None, "url": "https://findahelpline.com", "hours": None, "description": "175+ countries."}
RESOURCES = [EMERGENCY, LIFELINE, TEXT_LINE, DIRECTORY]


def test_a_pause_is_read_from_a_turn_a_profile_and_an_error():
    began, ends = "2026-11-13T12:00:00+00:00", "2026-11-13T12:15:00+00:00"
    expected = crisis_pause.Pause(NOW, NOW + timedelta(minutes=15))
    assert crisis_pause.pause_in({"content": "hi", "paused_from": began, "paused_until": ends}) == expected
    assert crisis_pause.pause_in({"nickname": "L", "chat_paused_from": began, "chat_paused_until": ends}) == expected
    refusal = {"error": {"code": "chat_paused", "details": {"paused_from": began, "paused_until": ends}}}
    assert crisis_pause.pause_in(refusal) == expected
    assert crisis_pause.pause_in({"paused_from": None, "paused_until": None}) is None
    assert crisis_pause.pause_in({"chat_paused_from": None, "chat_paused_until": None}) is None
    assert crisis_pause.pause_in({"error": {"code": "validation"}}) is None
    assert crisis_pause.pause_in({}) is None


def test_a_pause_carries_the_kind_of_danger_the_backend_names():
    began, ends = "2026-11-13T12:00:00+00:00", "2026-11-13T12:15:00+00:00"
    assert crisis_pause.pause_in({"paused_from": began, "paused_until": ends, "paused_for": "overdose"}).emergency_first
    profile = {"chat_paused_from": began, "chat_paused_until": ends, "chat_paused_for": "overdose"}
    assert crisis_pause.pause_in(profile).emergency_first
    refusal = {"error": {"details": {"paused_from": began, "paused_until": ends, "paused_for": "overdose"}}}
    assert crisis_pause.pause_in(refusal).emergency_first
    assert not crisis_pause.pause_in({"paused_from": began, "paused_until": ends}).emergency_first


def test_the_time_left_is_whole_minutes_rounded_up_and_never_below_one():
    assert crisis_pause.opens_again(NOW + timedelta(minutes=15), NOW) == "Chat opens again in about 15 minutes."
    assert crisis_pause.opens_again(NOW + timedelta(minutes=14, seconds=1), NOW) == "Chat opens again in about 15 minutes."
    assert crisis_pause.opens_again(NOW + timedelta(seconds=30), NOW) == "Chat opens again in about 1 minute."
    assert crisis_pause.opens_again(NOW - timedelta(minutes=5), NOW) == "Chat opens again in about 1 minute."


def test_the_pop_up_says_how_long_the_pause_itself_runs():
    """muhammad, 2026-11-16: the drawing says 24 hours and the pause is 15 minutes, so the words follow the pause."""
    assert crisis_pause.length(crisis_pause.Pause(NOW, NOW + timedelta(seconds=30))) == "30 seconds"
    assert crisis_pause.length(crisis_pause.Pause(NOW, NOW + timedelta(minutes=15))) == "15 minutes"
    assert crisis_pause.length(crisis_pause.Pause(NOW, NOW + timedelta(hours=24))) == "24 hours"
    assert crisis_pause.length(crisis_pause.Pause(NOW, NOW + timedelta(hours=1))) == "1 hour"
    assert crisis_pause.length(crisis_pause.Pause(NOW, NOW + timedelta(minutes=1))) == "1 minute"
    assert crisis_pause.length(crisis_pause.Pause(NOW, NOW + timedelta(minutes=90))) == "90 minutes"


def test_the_help_is_picked_by_kind_and_a_missing_kind_is_none():
    found = crisis_pause.pick(RESOURCES)
    assert (found.call, found.emergency, found.directory) == (LIFELINE, EMERGENCY, DIRECTORY)

    # A support line with no phone number is not a line to call.
    assert crisis_pause.pick([TEXT_LINE]) == crisis_pause.Help(call=None, emergency=None)
    assert crisis_pause.pick([]) == crisis_pause.Help(call=None, emergency=None)


def test_after_an_overdose_911_leads_and_get_help_now_calls_it():
    """R90: emergency medical services lead after an overdose, and 988 is not a substitute."""
    found = crisis_pause.pick(RESOURCES)
    overdose = crisis_pause.Pause(NOW, NOW + timedelta(minutes=15), "overdose")
    other = crisis_pause.Pause(NOW, NOW + timedelta(minutes=15))

    assert "tel:911" in crisis_pause.help_lines(overdose, found)[0]
    assert "tel:988" in crisis_pause.help_lines(overdose, found)[1]
    assert crisis_pause.call_first(overdose, found) == EMERGENCY
    assert "tel:988" in crisis_pause.help_lines(other, found)[0]
    assert crisis_pause.call_first(other, found) == LIFELINE
    # With no emergency line to call, the call line is still offered rather than nothing.
    assert crisis_pause.call_first(overdose, crisis_pause.pick([LIFELINE])) == LIFELINE


class PausedBackend(mani.ManiClient):
    """Answers the routes the page opens with; the profile says the chat is paused for 30 seconds from now,
    and the one conversation is T, with a message Mani sent."""

    def __init__(self, resources: list[dict] = RESOURCES) -> None:
        token = "h." + base64.urlsafe_b64encode(b'{"role":"authenticated"}').decode().rstrip("=") + ".s"
        super().__init__(session=mani.Session("00000000-0000-0000-0000-000000000001", token, "refresh"))
        now = datetime.now(timezone.utc)
        self.began, self.until = now.isoformat(), (now + timedelta(seconds=30)).isoformat()
        self.resources = resources
        self.kind: str | None = None
        self.calls: list[tuple] = []

    def _call(self, method, path, **kwargs):
        self.calls.append((method, path))
        if path == "/v1/profile":
            return {"nickname": None, "chat_paused_from": self.began, "chat_paused_until": self.until,
                    "chat_paused_for": self.kind}
        if path == "/v1/crisis/resources":
            return self.resources
        if path == "/v1/threads":
            return {"threads": []}
        if path == "/v1/threads/current":
            return {"thread": {"id": "T", "title": None, "message_count": 3, "crisis_detected": True,
                               "conversation_style": "supportive"},
                    "messages": [{"id": "g", "role": "mani", "content": "I hear you", "prompts": [{"label": "Tap me"}]}]}
        if path == "/v1/threads/T/messages" and method == "GET":
            return {"messages": [{"id": "g", "role": "mani", "content": "I hear you", "prompts": [{"label": "Tap me"}]}],
                    "next_cursor": None}
        if path == "/v1/exercises":
            return []
        raise AssertionError(f"unexpected {method} {path}")


class OpenThreadBackend(PausedBackend):
    """Not paused, with conversation T open; sending a message in it returns `answer`, or raises it."""

    def __init__(self, answer: dict | Exception) -> None:
        super().__init__()
        self.began = self.until = None
        self.answer = answer

    def _call(self, method, path, **kwargs):
        thread = {"id": "T", "title": None, "message_count": 3, "crisis_detected": False,
                  "conversation_style": "supportive"}
        if path == "/v1/threads/current":
            return {"thread": thread, "messages": []}
        if (method, path) == ("POST", "/v1/threads/T/messages"):
            if isinstance(self.answer, Exception):
                raise self.answer
            return self.answer
        return super()._call(method, path, **kwargs)


@pytest.fixture(autouse=True)
def no_database(monkeypatch):
    monkeypatch.setattr(mani, "DATABASE_URL", "")


def _open(backend: PausedBackend) -> AppTest:
    app = AppTest.from_file(str(pathlib.Path(__file__).with_name("app.py")), default_timeout=20)
    app.session_state["email"], app.session_state["client"] = "a@b.c", backend
    app.session_state["user_id"] = backend.session.user_id
    app.run()
    assert not app.exception
    return app


def _shown(app: AppTest) -> str:
    return " ".join(m.value for m in app.markdown)


def _opens_again_in_minutes(app: AppTest) -> int:
    """The minutes the page says the chat opens again in."""
    shown = " ".join(c.value for c in app.caption)
    return int(re.search(r"Chat opens again in about (\d+) minute", shown).group(1))


def test_a_paused_chat_leads_with_help_and_says_the_time_left_only_after_it():
    """S6: the pop-up leads with 988, 911 and findahelpline.com; that the chat is paused and for how long follow as
    secondary text, with no ticking clock. No list of situations and no "while you reach out" (the client's safety
    test, points 35 to 47). The Library still opens."""
    backend = PausedBackend()
    app = _open(backend)

    shown = _shown(app)
    lead = ('<p class="pause-lead">If you are thinking about suicide or you need immediate support call or text '
            '<a href="tel:988">988</a> to connect with a trained crisis counselor</p>')
    assert lead in shown
    assert 'If you are in immediate danger, call <a href="tel:911">911</a>.' in shown
    assert 'Outside the US: <a href="https://findahelpline.com" target="_blank">findahelpline.com</a>' in shown
    secondary = "Chat is temporary unavailable. For your safety, chat is paused for 30 seconds."
    assert shown.index(lead) < shown.index(secondary)
    assert "You can still access our Library resources." in shown
    assert "741741" not in shown and "while you reach out" not in shown and "everyone is safe" not in shown
    assert _opens_again_in_minutes(app) == 1
    assert not app.get("progress"), "no bar running down"
    assert [b.url for b in app.get("link_button")] == ["tel:988"]
    assert [b.label for b in app.button if b.label == "Visit library"] == ["Visit library"]
    assert app.chat_input[0].disabled
    assert [b for b in app.sidebar.button if "New conversation" in b.label][0].disabled
    assert ("GET", "/v1/threads/opening") not in backend.calls

    next(b for b in app.button if b.label == "Visit library").click().run()
    assert not app.exception
    assert app.title[0].value == "📚 Library"


def test_a_pause_after_an_overdose_leads_with_911():
    backend = PausedBackend()
    backend.kind = "overdose"
    app = _open(backend)

    shown = _shown(app)
    assert '<p class="pause-lead">If you are in immediate danger, call <a href="tel:911">911</a>.</p>' in shown
    assert 'call or text <a href="tel:988">988</a>' in shown
    assert [b.url for b in app.get("link_button")] == ["tel:911"]


def test_closing_the_pop_up_leaves_the_conversation_to_read_with_no_way_to_write():
    """The cross closes the pop-up (what its on_dismiss records); the conversation shows, read-only, until the pause ends."""
    app = _open(PausedBackend())
    app.session_state["pause_dismissed"] = app.session_state["pause"].ends
    app.run()
    assert not app.exception

    shown = _shown(app)
    assert "I hear you" in shown and "Chat is paused. You can read your conversation until it resumes." in "".join(
        i.value for i in app.info)
    assert "Chat is temporary unavailable" not in shown and _opens_again_in_minutes(app) == 1
    assert app.chat_input[0].disabled
    assert not [b for b in app.button if b.label == "Tap me"], "a suggested reply would send a message"
    assert not [b for b in app.button if b.key == "edit_last"]


def _closed(backend: PausedBackend) -> AppTest:
    app = _open(backend)
    app.session_state["pause_dismissed"] = app.session_state["pause"].ends
    app.run()
    assert not app.exception
    return app


def test_closing_the_pop_up_keeps_the_help_lines_on_the_page():
    """R90: what closing does is clear, and the instructions stay reachable after it."""
    shown = _shown(_closed(PausedBackend()))
    assert 'call or text <a href="tel:988">988</a>' in shown
    assert 'If you are in immediate danger, call <a href="tel:911">911</a>.' in shown
    assert 'Outside the US: <a href="https://findahelpline.com" target="_blank">findahelpline.com</a>' in shown

    overdose = PausedBackend()
    overdose.kind = "overdose"
    assert '<p class="pause-lead">If you are in immediate danger, call <a href="tel:911">911</a>.</p>' in _shown(
        _closed(overdose))

    unreachable = _shown(_closed(UnreachableBackend("/v1/crisis/resources")))
    assert 'call or text <a href="tel:988">988</a>' in unreachable and 'call <a href="tel:911">911</a>' in unreachable


def test_the_pop_up_leaves_out_the_help_it_was_not_given():
    app = _open(PausedBackend(resources=[DIRECTORY]))

    shown = _shown(app)
    assert "call or text" not in shown and "immediate danger" not in shown and "findahelpline.com" in shown
    assert "For your safety, chat is paused for 30 seconds." in shown and "Library resources" in shown


def test_the_chat_opens_once_the_pause_has_run_out():
    backend = OpenThreadBackend({})
    backend.began, backend.until = NOW.isoformat(), (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    app = _open(backend)
    assert app.chat_input[0].disabled

    # What the rerun once the pause is over finds: the stored pause has run out and the backend no longer has one.
    backend.began = backend.until = None
    app.session_state["pause"] = crisis_pause.Pause(NOW, datetime.now(timezone.utc) - timedelta(seconds=1))
    app.run()

    assert not app.exception
    assert not app.chat_input[0].disabled
    assert "chat is paused" not in _shown(app) and not [c for c in app.caption if "Chat opens again" in c.value]


def test_a_turn_that_pauses_the_chat_shows_the_pop_up_on_the_next_run():
    now = datetime.now(timezone.utc)
    turn = {"id": "m", "content": "I'm pausing our chat.", "prompts": [], "trace": None, "title": None,
            "crisis_detected": True, "paused_from": now.isoformat(),
            "paused_until": (now + timedelta(minutes=10)).isoformat(), "follow_up_pending": False}
    app = _open(OpenThreadBackend(turn))
    app.chat_input[0].set_value("I don't want help").run()

    assert not app.exception
    assert app.chat_input[0].disabled
    assert "For your safety, chat is paused for 10 minutes." in _shown(app)
    assert _opens_again_in_minutes(app) == 10


def test_a_send_refused_because_the_chat_is_paused_shows_the_pop_up_and_queues_no_error():
    now = datetime.now(timezone.utc)
    details = {"paused_from": now.isoformat(), "paused_until": (now + timedelta(minutes=20)).isoformat()}
    refusal = mani.ApiError(423, {"error": {"code": "chat_paused", "category": "chat_paused",
                                            "message": "paused", "details": details}})
    app = _open(OpenThreadBackend(refusal))
    app.chat_input[0].set_value("hello").run()

    assert not app.exception
    assert app.chat_input[0].disabled
    assert "For your safety, chat is paused for 20 minutes." in _shown(app)
    assert "send_error" not in app.session_state
    assert "notice" not in app.session_state
    assert app.session_state.composer_draft == "hello"


class UnreachableBackend(PausedBackend):
    """PausedBackend, except that the routes in `unreachable` go over the network to an address where nothing
    listens, as when the backend is down."""

    def __init__(self, *unreachable: str) -> None:
        super().__init__()
        self.base_url = "http://127.0.0.1:9"
        self.unreachable = unreachable

    def _call(self, method, path, **kwargs):
        if path in self.unreachable:
            return mani.ManiClient._call(self, method, path, **kwargs)
        return super()._call(method, path, **kwargs)


def test_a_backend_that_does_not_answer_is_a_handled_error():
    with pytest.raises(mani.BackendUnreachable):
        UnreachableBackend("/v1/crisis/resources").crisis_resources()


def test_the_pop_up_names_the_us_lines_when_the_help_numbers_cannot_be_loaded():
    """A pop-up with no number to call is the worst thing it could show someone in danger."""
    app = _open(UnreachableBackend("/v1/crisis/resources"))

    shown = _shown(app)
    assert "For your safety, chat is paused for 30 seconds." in shown
    assert ('If you are thinking about suicide or you need immediate support call or text <a href="tel:988">988</a> '
            "to connect with a trained crisis counselor") in shown
    assert 'If you are in immediate danger, call <a href="tel:911">911</a>.' in shown
    assert 'Outside the US: <a href="https://findahelpline.com" target="_blank">findahelpline.com</a>' in shown
    assert [b.url for b in app.get("link_button")] == ["tel:988"]
    assert any(c.value.startswith("Could not load the help numbers, so these are the reference lines:")
               for c in app.caption)


def test_the_page_opens_when_the_pause_cannot_be_checked_and_asks_again_on_the_next_run():
    backend = UnreachableBackend("/v1/profile")
    app = _open(backend)

    assert any(c.value.startswith("Could not check whether the chat is paused:") for c in app.sidebar.caption)
    assert "Chat is temporary unavailable" not in _shown(app)

    backend.unreachable = ()
    app.run()
    assert not app.exception
    assert "Chat is temporary unavailable" in _shown(app)
