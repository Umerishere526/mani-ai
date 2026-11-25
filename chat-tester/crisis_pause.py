# ABOUTME: The pause on a person's chat while their danger continues: reads when it began and ends from a turn, a
# ABOUTME: profile or a refusal, and shows a pop-up that leads with where to get help, the time left only beneath it.

from __future__ import annotations

import html
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import streamlit as st

import client as mani

# The pop-up leads with where to get help; that the chat is paused, and for how long, comes after it as secondary text
# with no ticking countdown (S6, R90: a timer must never be the primary intervention). The words are the client's drawing
# of 2026-11-16 ("Blocker." above it and "temporary" as she wrote them: muhammad, 2026-11-16), and the numbers come from
# GET /v1/crisis/resources.
# PROVISIONAL: clinician sign-off required before deploy.
LABEL = "Blocker."
SUPPORT = (
    "If you are thinking about suicide or you need immediate support call or text {number} to connect with a trained "
    "crisis counselor"
)
EMERGENCY = "If you are in immediate danger, call {number}."
# Every resources text names help outside the US (S11).
DIRECTORY = "Outside the US: {link}"
TITLE = "Chat is temporary unavailable"
PAUSED_FOR = "For your safety, chat is paused for {length}."
LIBRARY = "You can still access our Library resources."
# When the chat opens again, in whole minutes rounded up, so it reads as a time rather than a clock running down.
OPENS_AGAIN = "Chat opens again in about {minutes}."
GET_HELP = "Get help now"
VISIT_LIBRARY = "Visit library"
# The kinds of danger after which emergency services lead and 911 is the most prominent action, 988 no substitute
# (R90). The backend names the kind in `paused_for`.
# PROVISIONAL: clinician sign-off required before deploy.
EMERGENCY_FIRST = ("overdose",)
# The help the pop-up names when GET /v1/crisis/resources cannot be read, so it never shows no number at all: the
# backend's US reference lines and the directory for everyone else (RESOURCES in backend/mani/chat/crisis.py), as that
# route lists them.
FALLBACK_RESOURCES = [
    {"country": "US", "kind": "emergency", "name": "Emergency services",
     "description": "For immediate danger to you or someone else.", "phone": "911", "sms": None, "url": None,
     "hours": None},
    {"country": "US", "kind": "support", "name": "988 Suicide & Crisis Lifeline",
     "description": "Call, text or chat with a trained counselor.", "phone": "988", "sms": "988",
     "url": "https://988lifeline.org", "hours": "24/7"},
    {"country": "US", "kind": "directory", "name": "Find a helpline in your country",
     "description": "Free, confidential helplines in more than 175 countries.", "phone": None, "sms": None,
     "url": "https://findahelpline.com", "hours": None},
]
# Above the conversation they can still read after closing the pop-up.
WHILE_READING = "Chat is paused. You can read your conversation until it resumes."

# The pop-up in the middle of the window (auto margins keep a tall one scrollable from its top), its words centred as
# drawn, the help first and largest.
STYLE = """<style>
[data-testid="stDialog"] > div { margin-block: auto; }
.pause-body { text-align: center; }
.pause-body p { margin: 0 0 1.1rem; }
.pause-body .pause-lead { font-size: 1.2rem; font-weight: 700; }
.pause-body a { color: inherit !important; text-decoration: underline !important; }
.pause-after { text-align: center; opacity: .75; font-size: .9rem; margin-top: 1rem; }
.pause-after p { margin: 0 0 .4rem; }
</style>"""


@dataclass(frozen=True)
class Pause:
    """When the pause on their chat began and when it ends, and the kind of danger it was for when the backend named
    it."""

    began: datetime
    ends: datetime
    kind: str | None = None

    @property
    def emergency_first(self) -> bool:
        return self.kind in EMERGENCY_FIRST


@dataclass(frozen=True)
class Help:
    """What the pop-up names, each None when the resources hold none: a line to call or text, emergency services, and
    a directory of helplines outside the US."""

    call: dict[str, Any] | None
    emergency: dict[str, Any] | None
    directory: dict[str, Any] | None = None


def _field(source: dict[str, Any], name: str) -> Any:
    """`paused_<name>` of a turn or of a refusal's error details, or `chat_paused_<name>` of a profile or opening."""
    details = source.get("error", {}).get("details", {})
    values = (source.get(f"paused_{name}"), source.get(f"chat_paused_{name}"), details.get(f"paused_{name}"))
    return next((v for v in values if v is not None), None)


def pause_in(source: dict[str, Any]) -> Pause | None:
    """The pause a turn, a profile or opening, or a refusal's error body carries; None when it carries none."""
    began, ends = _field(source, "from"), _field(source, "until")
    if began is None or ends is None:
        return None
    return Pause(datetime.fromisoformat(began), datetime.fromisoformat(ends), _field(source, "for"))


def opens_again(until: datetime, now: datetime) -> str:
    """The time left in whole minutes, rounded up, so it says "1 minute" until the pause is over."""
    minutes = max(1, math.ceil((until - now).total_seconds() / 60))
    return OPENS_AGAIN.format(minutes="1 minute" if minutes == 1 else f"{minutes} minutes")


def length(pause: Pause) -> str:
    """How long the pause runs, in the largest whole unit that holds it: "30 seconds", "15 minutes", "24 hours"."""
    seconds = max(1, round((pause.ends - pause.began).total_seconds()))
    unit_seconds, unit = next(((n, name) for n, name in ((3600, "hour"), (60, "minute")) if seconds % n == 0), (1, "second"))
    count = seconds // unit_seconds
    return f"{count} {unit}" if count == 1 else f"{count} {unit}s"


def pick(resources: list[dict[str, Any]]) -> Help:
    """The first resource of each kind the pop-up shows that has the number or link it needs."""

    def first(kind: str, field: str) -> dict[str, Any] | None:
        return next((r for r in resources if r.get("kind") == kind and r.get(field) is not None), None)

    return Help(call=first("support", "phone"), emergency=first("emergency", "phone"),
                directory=first("directory", "url"))


def note(source: dict[str, Any]) -> bool:
    """Keeps the pause a response carries, so the next run shows the pop-up; says whether it carried one."""
    pause = pause_in(source)
    if pause is not None:
        st.session_state.pause = pause
    return pause is not None


def active(client: mani.ManiClient) -> Pause | None:
    """The pause that is running, or None. Asked of the backend on sign-in, on reload and once the stored pause has
    run out; every other run reads the stored one."""
    now = datetime.now(timezone.utc)
    stored = st.session_state.get("pause", "unread")
    if stored == "unread" or (stored is not None and stored.ends <= now):
        try:
            st.session_state.pause = pause_in(client.get_profile())
        except mani.ApiError as exc:
            # Asked again on the next run. Meanwhile the backend still refuses a message while the chat is paused,
            # and that refusal shows the pop-up.
            st.caption(f"Could not check whether the chat is paused: {exc}")
            return None
    pause = st.session_state.pause
    return pause if pause is not None and pause.ends > now else None


def _number(resource: dict[str, Any]) -> str:
    """A resource's phone number as a link that calls it."""
    phone = html.escape(resource["phone"])
    return f'<a href="tel:{phone}">{phone}</a>'


def _link(resource: dict[str, Any]) -> str:
    """A resource's web address as a link, shown without its scheme."""
    url = resource["url"]
    shown = url.removeprefix("https://").removeprefix("http://").rstrip("/")
    return f'<a href="{html.escape(url)}" target="_blank">{html.escape(shown)}</a>'


def help_lines(pause: Pause, found: Help) -> list[str]:
    """Where to get help as HTML lines, most prominent first: 988 then 911, or 911 first after an overdose; a line
    whose number or link is missing is left out."""
    e = html.escape
    call = None if found.call is None else e(SUPPORT).format(number=_number(found.call))
    emergency = None if found.emergency is None else e(EMERGENCY).format(number=_number(found.emergency))
    directory = None if found.directory is None else e(DIRECTORY).format(link=_link(found.directory))
    ordered = (emergency, call) if pause.emergency_first else (call, emergency)
    return [line for line in (*ordered, directory) if line is not None]


def words(pause: Pause, found: Help) -> str:
    """The pop-up's help as HTML, the first line the lead."""
    lines = help_lines(pause, found)
    body = "".join(f'<p class="pause-lead">{line}</p>' if i == 0 else f"<p>{line}</p>" for i, line in enumerate(lines))
    return f'<div class="pause-body">{body}</div>'


def call_first(pause: Pause, found: Help) -> dict[str, Any] | None:
    """The line Get help now calls: the one the pop-up leads with."""
    return (found.emergency or found.call) if pause.emergency_first else (found.call or found.emergency)


def after_help(pause: Pause) -> str:
    """What comes after the help, smaller: that the chat is paused, for how long, and that the Library stays open."""
    e = html.escape
    lines = (f"{e(TITLE)}. {e(PAUSED_FOR.format(length=length(pause)))}", e(LIBRARY))
    return f'<div class="pause-after">{"".join(f"<p>{line}</p>" for line in lines)}</div>'


@st.fragment(run_every=5)
def _time_left(pause: Pause) -> None:
    """When the chat opens again, in whole minutes; once the pause is over the whole page runs again, which closes the
    pop-up."""
    now = datetime.now(timezone.utc)
    if now >= pause.ends:
        st.rerun()
    st.caption(opens_again(pause.ends, now))


def _show_library() -> None:
    st.session_state.view = "library"


def _dismiss() -> None:
    st.session_state.pause_dismissed = st.session_state.pause.ends


def dismissed(pause: Pause) -> bool:
    """Whether the person closed this pause's pop-up with its cross; a later pause shows it again."""
    return st.session_state.get("pause_dismissed") == pause.ends


def _help(client: mani.ManiClient) -> Help:
    """The help to name, from the backend, or the fallback lines with a note when it cannot be read."""
    try:
        return pick(client.crisis_resources())
    except mani.ApiError as exc:
        st.caption(f"Could not load the help numbers, so these are the reference lines: {exc}")
        return pick(FALLBACK_RESOURCES)


def banner(client: mani.ManiClient, pause: Pause) -> None:
    """What the page shows beside the readable conversation once the pop-up is closed: the help lines stay reachable
    (R90), then when the chat resumes."""
    st.html(STYLE)
    st.info(WHILE_READING)
    st.markdown(words(pause, _help(client)), unsafe_allow_html=True)
    _time_left(pause)


@st.dialog(LABEL, on_dismiss=_dismiss)
def render(client: mani.ManiClient, pause: Pause) -> None:
    # Closing it with the cross leaves the conversation to read, with no way to write in it until the pause ends.
    st.html(STYLE)
    found = _help(client)
    st.markdown(words(pause, found), unsafe_allow_html=True)
    line = call_first(pause, found)
    get_help, library = st.columns(2)
    if line is not None:
        get_help.link_button(GET_HELP, f"tel:{line['phone']}", type="primary", use_container_width=True)
    if library.button(VISIT_LIBRARY, use_container_width=True):
        _show_library()
        st.rerun()
    st.markdown(after_help(pause), unsafe_allow_html=True)
    _time_left(pause)
