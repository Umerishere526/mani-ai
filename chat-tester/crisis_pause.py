# ABOUTME: The pause on a person's chat while their danger continues: reads when it began and ends from a turn, a
# ABOUTME: profile or a refusal, and shows the centred pop-up with the help numbers and a live countdown.

from __future__ import annotations

import html
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import streamlit as st

import client as mani

# The pop-up's wording is ours until the client supplies hers; the numbers come from GET /v1/crisis/resources.
TITLE = "Let's make sure everyone is safe"
BODY = (
    "It sounds like someone could be at risk. Whether you're thinking about hurting yourself, worried you might hurt "
    "someone else, or you're in a dangerous situation right now, you can reach a real person immediately."
)
FOOTER = "I'm an AI and can't contact anyone for you, but I'll be here when you come back."

# The pop-up in the middle of the window (auto margins keep a tall one scrollable from its top), and its help cards.
# Icons are ligatures of the Material Symbols font Streamlit already loads for its own icons.
STYLE = """<style>
[data-testid="stDialog"] > div { margin-block: auto; }
[data-testid="stDialogIcon"] { background: #E7F0EE; color: #2C5F57; border-radius: 50%; padding: .55rem; }
.pause-icon { font-family: "Material Symbols Rounded"; font-size: 1.35rem; line-height: 1; font-feature-settings: "liga"; }
.pause-call, .pause-text, .pause-emergency { display: flex; align-items: center; gap: .75rem; padding: .85rem 1.1rem;
    border-radius: .65rem; text-decoration: none !important; }
.pause-call { background: #2C5F57; color: #FFFFFF !important; }
.pause-call b { display: block; font-size: 1.05rem; }
.pause-call small { display: block; opacity: .9; }
.pause-call .pause-chevron { margin-left: auto; }
.pause-row { display: grid; grid-template-columns: 1fr 1fr; gap: .65rem; margin: .65rem 0 1rem; }
.pause-text { border: 1px solid #C9DAD6; color: #2C5F57 !important; font-weight: 600; }
.pause-emergency { border: 1px solid #E5C3AE; background: #FBF1EC; color: #9A3A12 !important; font-weight: 600; }
.pause-outside a { color: #2C5F57 !important; }
.pause-timer { display: flex; align-items: center; gap: .5rem; }
.pause-timer b { margin-left: auto; font-size: 1.35rem; }
</style>"""


@dataclass(frozen=True)
class Pause:
    """When the pause on their chat began and when it ends."""

    began: datetime
    ends: datetime


@dataclass(frozen=True)
class Help:
    """What the pop-up offers, each None when the resources hold none: a line to call (and to text, when it takes
    texts), emergency services, and the directory of helplines in other countries."""

    call: dict[str, Any] | None
    emergency: dict[str, Any] | None
    directory: dict[str, Any] | None


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
    length = (pause.ends - pause.began).total_seconds()
    if length <= 0:
        return 1.0
    return min(1.0, max(0.0, (now - pause.began).total_seconds() / length))


def pick(resources: list[dict[str, Any]]) -> Help:
    """The first resource of each kind the pop-up shows that has the number or link it needs."""

    def first(kind: str, field: str) -> dict[str, Any] | None:
        return next((r for r in resources if r.get("kind") == kind and r.get(field) is not None), None)

    return Help(call=first("support", "phone"), emergency=first("emergency", "phone"), directory=first("directory", "url"))


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
        st.session_state.pause = pause_in(client.get_profile())
    pause = st.session_state.pause
    return pause if pause is not None and pause.ends > now else None


def _link(kind: str, href: str, icon: str, label: str, end: str = "") -> str:
    """A help card: its icon, its label, then `end`."""
    return (f'<a class="pause-{kind}" href="{html.escape(href)}"><span class="pause-icon">{icon}</span>'
            f"<span>{label}</span>{end}</a>")


def _cards(found: Help) -> str:
    """The help as HTML; a part whose resource is missing is left out."""
    e = html.escape
    parts, row = [], []
    if found.call is not None:
        about = " · ".join(e(v) for v in (found.call["name"], found.call.get("hours")) if v is not None)
        label = f"<b>Call {e(found.call['phone'])}</b><small>{about}</small>"
        chevron = '<span class="pause-icon pause-chevron">chevron_right</span>'
        parts.append(_link("call", f"tel:{found.call['phone']}", "call", label, end=chevron))
        if found.call.get("sms") is not None:
            row.append(_link("text", f"sms:{found.call['sms']}", "chat_bubble", f"Text {e(found.call['sms'])}"))
    if found.emergency is not None:
        phone = e(found.emergency["phone"])
        row.append(_link("emergency", f"tel:{found.emergency['phone']}", "warning", f"Emergency: {phone}"))
    if row:
        parts.append(f'<div class="pause-row">{"".join(row)}</div>')
    if found.emergency is not None:
        parts.append(f"<p><b>Someone in immediate danger?</b> Call {phone} or get to a safe place first.</p>")
    if found.directory is not None:
        url, name = e(found.directory["url"]), e(found.directory["name"])
        parts.append(f'<p class="pause-outside">Outside the US? <a href="{url}" target="_blank">{name}</a></p>')
    return "".join(parts)


@st.fragment(run_every=1)
def _countdown(pause: Pause) -> None:
    """Ticks every second while the pop-up is open; at 0:00 the whole page runs again, which closes it."""
    now = datetime.now(timezone.utc)
    if now >= pause.ends:
        st.rerun()
    st.markdown(
        f'<div class="pause-timer"><span class="pause-icon">schedule</span>'
        f"<span>Chat is paused while you reach out. Resumes in</span><b>{countdown(pause.ends, now)}</b></div>",
        unsafe_allow_html=True,
    )
    st.progress(elapsed(pause, now))


def _show_library() -> None:
    st.session_state.view = "library"


@st.dialog(TITLE, icon=":material/shield:", on_dismiss=_show_library)
def render(client: mani.ManiClient, pause: Pause) -> None:
    st.html(STYLE)
    st.write(BODY)
    try:
        resources = client.crisis_resources()
    except mani.ApiError as exc:
        resources = []
        st.caption(f"Could not load the help numbers: {exc}")
    cards = _cards(pick(resources))
    if cards:
        st.markdown(cards, unsafe_allow_html=True)
    st.divider()
    _countdown(pause)
    st.caption(FOOTER)
