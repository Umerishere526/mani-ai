# ABOUTME: The pause on a person's chat while their danger continues: reads when it began and ends from a turn, a
# ABOUTME: profile or a refusal, and shows the client's blocker pop-up with where to get help and a live countdown.

from __future__ import annotations

import html
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import streamlit as st

import client as mani

# The pop-up is the client's drawing of 2026-11-16, word for word ("Blocker." above the title and "temporary" as she
# wrote them: muhammad, 2026-11-16), with the emergency line he asked to keep. How long it says the chat is paused is
# the pause's own length, and the numbers come from GET /v1/crisis/resources.
LABEL = "Blocker."
TITLE = "Chat is temporary unavailable"
PAUSED_FOR = "For your safety, chat is paused for {length}."
LIBRARY = "You can still access our Library resources."
SUPPORT = (
    "If you are thinking about suicide or you need immediate support call or text {number} to connect with a trained "
    "crisis counselor"
)
EMERGENCY = "If you are in immediate danger, call {number}."
GET_HELP = "Get help now"
GO_TO_LIBRARY = "Go to library"
# The help the pop-up names when GET /v1/crisis/resources cannot be read, so it never shows no number at all: the
# backend's US reference lines (RESOURCES in backend/mani/chat/crisis.py), as that route lists them.
FALLBACK_RESOURCES = [
    {"country": "US", "kind": "emergency", "name": "Emergency services",
     "description": "For immediate danger to you or someone else.", "phone": "911", "sms": None, "url": None,
     "hours": None},
    {"country": "US", "kind": "support", "name": "988 Suicide & Crisis Lifeline",
     "description": "Call, text or chat with a trained counselor.", "phone": "988", "sms": "988",
     "url": "https://988lifeline.org", "hours": "24/7"},
]
# Beside the live timer at the bottom, which the drawing does not show and muhammad kept (2026-11-16). It says only
# when the chat opens again: "while you reach out" assumed they had (the client's safety test, point 43).
RESUMES_IN = "Chat resumes in"
# Above the conversation they can still read after closing the pop-up.
WHILE_READING = "Chat is paused. You can read your conversation until it resumes."

# The pop-up in the middle of the window (auto margins keep a tall one scrollable from its top), its words centred as
# drawn.
STYLE = """<style>
[data-testid="stDialog"] > div { margin-block: auto; }
.pause-body { text-align: center; }
.pause-body h2 { font-size: 1.6rem; font-weight: 700; margin: 0 0 1.25rem; padding: 0; }
.pause-body p { margin: 0 0 1.1rem; }
.pause-body a { color: inherit !important; text-decoration: underline !important; }
.pause-icon { font-family: "Material Symbols Rounded"; font-size: 1.35rem; line-height: 1; font-feature-settings: "liga"; }
.pause-timer { display: flex; align-items: center; gap: .5rem; margin-top: .75rem; }
.pause-timer b { margin-left: auto; font-size: 1.35rem; }
</style>"""


@dataclass(frozen=True)
class Pause:
    """When the pause on their chat began and when it ends."""

    began: datetime
    ends: datetime


@dataclass(frozen=True)
class Help:
    """What the pop-up names, each None when the resources hold none: a line to call or text, and emergency
    services."""

    call: dict[str, Any] | None
    emergency: dict[str, Any] | None


def _stamp(source: dict[str, Any], end: str) -> datetime | None:
    """`paused_<end>` of a turn or of a refusal's error details, or `chat_paused_<end>` of a profile or opening."""
    details = source.get("error", {}).get("details", {})
    stamps = (source.get(f"paused_{end}"), source.get(f"chat_paused_{end}"), details.get(f"paused_{end}"))
    stamp = next((s for s in stamps if s is not None), None)
    return None if stamp is None else datetime.fromisoformat(stamp)


def pause_in(source: dict[str, Any]) -> Pause | None:
    """The pause a turn, a profile or opening, or a refusal's error body carries; None when it carries none."""
    began, ends = _stamp(source, "from"), _stamp(source, "until")
    return None if began is None or ends is None else Pause(began, ends)


def countdown(until: datetime, now: datetime) -> str:
    """The time left as m:ss, rounded up to the second, so 0:00 shows only once the pause is over."""
    seconds = max(0, math.ceil((until - now).total_seconds()))
    return f"{seconds // 60}:{seconds % 60:02d}"


def elapsed(pause: Pause, now: datetime) -> float:
    """How much of the pause has run, from 0 to 1."""
    total = (pause.ends - pause.began).total_seconds()
    if total <= 0:
        return 1.0
    return min(1.0, max(0.0, (now - pause.began).total_seconds() / total))


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

    return Help(call=first("support", "phone"), emergency=first("emergency", "phone"))


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


def words(pause: Pause, found: Help) -> str:
    """The pop-up's words as HTML, in the drawing's order; a line whose number is missing is left out."""
    e = html.escape
    lines = [e(PAUSED_FOR.format(length=length(pause))), e(LIBRARY)]
    if found.call is not None:
        lines.append(e(SUPPORT).format(number=_number(found.call)))
    if found.emergency is not None:
        lines.append(e(EMERGENCY).format(number=_number(found.emergency)))
    return f'<div class="pause-body"><h2>{e(TITLE)}</h2>{"".join(f"<p>{line}</p>" for line in lines)}</div>'


@st.fragment(run_every=1)
def _countdown(pause: Pause) -> None:
    """Ticks every second while the pop-up is open; at 0:00 the whole page runs again, which closes it."""
    now = datetime.now(timezone.utc)
    if now >= pause.ends:
        st.rerun()
    st.markdown(
        f'<div class="pause-timer"><span class="pause-icon">schedule</span>'
        f"<span>{html.escape(RESUMES_IN)}</span><b>{countdown(pause.ends, now)}</b></div>",
        unsafe_allow_html=True,
    )
    st.progress(elapsed(pause, now))


def _show_library() -> None:
    st.session_state.view = "library"


def _dismiss() -> None:
    st.session_state.pause_dismissed = st.session_state.pause.ends


def dismissed(pause: Pause) -> bool:
    """Whether the person closed this pause's pop-up with its cross; a later pause shows it again."""
    return st.session_state.get("pause_dismissed") == pause.ends


def banner(pause: Pause) -> None:
    """What the page shows beside the readable conversation once the pop-up is closed: only when the chat resumes."""
    st.info(WHILE_READING)
    _countdown(pause)


@st.dialog(LABEL, on_dismiss=_dismiss)
def render(client: mani.ManiClient, pause: Pause) -> None:
    # Closing it with the cross leaves the conversation to read, with no way to write in it until the pause ends.
    st.html(STYLE)
    try:
        found = pick(client.crisis_resources())
    except mani.ApiError as exc:
        found = pick(FALLBACK_RESOURCES)
        st.caption(f"Could not load the help numbers, so these are the US lines: {exc}")
    st.markdown(words(pause, found), unsafe_allow_html=True)
    help_line = found.call or found.emergency
    get_help, library = st.columns(2)
    if help_line is not None:
        get_help.link_button(GET_HELP, f"tel:{help_line['phone']}", use_container_width=True)
    if library.button(GO_TO_LIBRARY, use_container_width=True):
        _show_library()
        st.rerun()
    _countdown(pause)
