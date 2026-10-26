# ABOUTME: The admin's screen: every person's conversations grouped under them, each readable in full with its timing.
# ABOUTME: Read-only - there is no composer and no button that sends anything to a conversation.

from __future__ import annotations

import datetime as dt
from typing import Any

import streamlit as st

import client as mani
from login import render_account


def gap(seconds: float) -> str:
    """How long after the message before it this one came, at a glance: +40s, +3m, +2h 5m, +1d 4h."""
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"+{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"+{minutes}m"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"+{hours}h {minutes}m" if minutes else f"+{hours}h"
    days, hours = divmod(hours, 24)
    return f"+{days}d {hours}h" if hours else f"+{days}d"


def _when(value: str) -> dt.datetime:
    # The backend writes UTC as a trailing Z, which fromisoformat reads only from Python 3.11.
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def _stamp(value: str) -> str:
    return _when(value).strftime("%b %d, %H:%M:%S UTC")


def _title(thread: dict[str, Any]) -> str:
    """The conversation's title with the style Mani spoke in, e.g. "Feeling stuck (Directive)"."""
    title = thread.get("title") or "Untitled"
    style = thread.get("conversation_style")
    return f"{title} ({style.capitalize()})" if style else title


def _owner(thread: dict[str, Any]) -> str:
    who = thread.get("user_email") or thread["user_id"]
    return f"{thread['user_nickname']} · {who}" if thread.get("user_nickname") else who


def by_person(threads: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """The threads grouped under the person they belong to, each person placed by their most
    recent conversation, and each person's conversations newest first - the order they arrive in."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for thread in threads:
        groups.setdefault(thread["user_id"], []).append(thread)
    return list(groups.values())


def _render_thread_button(thread: dict[str, Any], is_open: bool) -> None:
    crisis = "🚨 " if thread.get("crisis_detected") else ""
    if st.button(
        ("▶ " if is_open else "") + crisis + _title(thread),
        key=f"admin_thread_{thread['id']}",
        disabled=is_open,
        use_container_width=True,
        help=f"{thread['message_count']} messages  ·  started {_stamp(thread['created_at'])}  ·  "
             f"last active {_stamp(thread['last_message_at'])}",
    ):
        st.session_state.admin_thread = thread["id"]
        st.rerun()


def _render_list(client: mani.ManiClient) -> None:
    st.subheader("Conversations")
    search = st.text_input("Search by email or user id", key="admin_search")
    try:
        page = client.admin_threads(search)
    except mani.ApiError as exc:
        st.caption(f"Could not list conversations: {exc}")
        return
    threads = page["threads"]
    open_id = st.session_state.get("admin_thread")
    for person in by_person(threads):
        crisis = "🚨 " if any(t.get("crisis_detected") for t in person) else ""
        count = f"{len(person)} conversation" + ("" if len(person) == 1 else "s")
        holds_open = any(t["id"] == open_id for t in person)
        with st.expander(f"{crisis}{_owner(person[0])} · {count}", expanded=holds_open):
            for thread in person:
                _render_thread_button(thread, thread["id"] == open_id)
    if not threads:
        st.caption("No conversations match." if search else "No conversations yet.")
    elif page.get("next_cursor"):
        st.caption(
            f"Showing the {len(threads)} most recently active conversations; a person may have older ones. "
            "Search their email to see them all."
        )


def _render_transcript(client: mani.ManiClient, thread_id: str) -> None:
    try:
        found = client.admin_transcript(thread_id)
    except mani.ApiError as exc:
        st.error(str(exc))
        return
    thread, messages = found["thread"], found["messages"]

    st.title(_title(thread))
    st.caption(
        f"{_owner(thread)}  ·  {thread['message_count']} messages  ·  "
        f"started {_stamp(thread['created_at'])}  ·  last active {_stamp(thread['last_message_at'])}"
    )
    if thread.get("crisis_detected"):
        st.error("🚨 This conversation was flagged by the crisis screen.")
    if len(messages) > 1:
        span = _when(messages[-1]["created_at"]) - _when(messages[0]["created_at"])
        st.caption(f"First to last message: {gap(span.total_seconds()).lstrip('+')}")

    previous = None
    for message in messages:
        is_mani = message["role"] == "mani"
        with st.chat_message("assistant" if is_mani else "user", avatar="🧠" if is_mani else "🧑"):
            st.write(message["content"])
            timing = _stamp(message["created_at"])
            if previous is not None:
                waited = _when(message["created_at"]) - _when(previous)
                timing += f"  ·  {gap(waited.total_seconds())}"
            if message.get("selected_prompt"):
                timing += f"  ·  tapped “{message['selected_prompt']}”"
            st.caption(timing)
        previous = message["created_at"]
    if not messages:
        st.caption("This conversation has no messages.")
    st.info("Read-only. Admin accounts can read conversations but cannot reply in them.")


def render_admin(client: mani.ManiClient) -> None:
    with st.sidebar:
        render_account("admin, read-only")
        st.divider()
        _render_list(client)

    thread_id = st.session_state.get("admin_thread")
    if thread_id:
        _render_transcript(client, thread_id)
    else:
        st.title("🧠 Beta conversations")
        st.caption("Pick a conversation in the sidebar to read it in full, with the time between messages.")
