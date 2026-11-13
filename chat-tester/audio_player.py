# ABOUTME: An exercise's audio player: seek bar, 10 s back and forward, play, mute, time and, when asked, a 0.5x to 2x
# ABOUTME: speed choice, which st.audio has no setting for. The browser runs it (audio_player.js); no tap reruns the page.

from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import quote

import streamlit as st

SPEEDS = ("0.5", "1", "1.5", "2")
SKIP_SECONDS = 10

_HERE = Path(__file__).parent


def _icon(shapes: str) -> str:
    """A 24-unit SVG as a CSS url(). st.html strips inline SVG, so icons are painted through a CSS mask."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{shapes}</svg>'
    )
    return f'url("data:image/svg+xml,{quote(svg)}")'


_SKIP = (
    '<text x="12" y="15.4" text-anchor="middle" font-size="8" font-weight="700" '
    f'font-family="system-ui,sans-serif" fill="black" stroke="none">{SKIP_SECONDS}</text>'
)
_SPEAKER = '<path d="M4 9.5h3l4.5-4v13l-4.5-4H4a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1z" fill="black"/>'
_ICONS = {
    "back": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>' + _SKIP,
    "forward": '<path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/>' + _SKIP,
    "play": '<path d="M7 4.8v14.4a1 1 0 0 0 1.5.86l11.6-7.2a1 1 0 0 0 0-1.72L8.5 3.94A1 1 0 0 0 7 4.8z" fill="black"/>',
    "pause": (
        '<rect x="6" y="4.5" width="4" height="15" rx="1.2" fill="black" stroke="none"/>'
        '<rect x="14" y="4.5" width="4" height="15" rx="1.2" fill="black" stroke="none"/>'
    ),
    "sound": _SPEAKER + '<path d="M15.5 9a4 4 0 0 1 0 6"/><path d="M18.5 6a8 8 0 0 1 0 12"/>',
    "muted": _SPEAKER + '<path d="M16 9.5l5 5M21 9.5l-5 5"/>',
}

# The link rides on the audio element as an escaped attribute, never inside the script, so it can never run as code.
_ASSETS = (
    "<style>.mani-player {" + "".join(f" --icon-{name}: {_icon(shapes)};" for name, shapes in _ICONS.items()) + " }\n"
    + (_HERE / "audio_player.css").read_text()
    + "</style><script>"
    + (_HERE / "audio_player.js").read_text()
    + "</script>"
)


def _button(action: str, icon: str, label: str, by: int | None = None) -> str:
    skip = f' data-by="{by}"' if by is not None else ""
    return (
        f'<button class="mani-btn" type="button" data-act="{action}"{skip} aria-label="{label}">'
        f'<span class="mani-icon" data-icon="{icon}"></span></button>'
    )


def audio_player(url: str, speed_choice: bool) -> None:
    """A player for `url`, paused at the start at 1x, with the speed menu only when `speed_choice` is set."""
    options = "".join(
        f'<option value="{speed}"{" selected" if speed == "1" else ""}>{speed}×</option>' for speed in SPEEDS
    )
    speed_menu = f'<select class="mani-speed" aria-label="Playback speed">{options}</select>' if speed_choice else ""
    st.html(
        '<div class="mani-player">'
        f'<audio preload="metadata" src="{html.escape(url, quote=True)}"></audio>'
        '<input class="mani-seek" type="range" min="0" max="1000" value="0" aria-label="Seek">'
        '<div class="mani-row">'
        + _button("skip", "back", f"Back {SKIP_SECONDS} seconds", -SKIP_SECONDS)
        + _button("play", "play", "Play")
        + _button("skip", "forward", f"Forward {SKIP_SECONDS} seconds", SKIP_SECONDS)
        + _button("mute", "sound", "Mute")
        + '<span class="mani-time">0:00 / 0:00</span>'
        + speed_menu
        + "</div></div>"
        + _ASSETS,
        unsafe_allow_javascript=True,
    )
