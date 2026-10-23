# ABOUTME: A streaming chat demo against the local Mani backend - the whole point is
# ABOUTME: watching Mani's reply arrive token by token, plus the raw SSE frames it rode in on.

from __future__ import annotations

import json

import streamlit as st

import client as mani
from login import render_login

st.set_page_config(page_title="Mani streaming demo", page_icon="🧠", layout="centered")

# The model's hidden reasoning streams before any visible text, so from send until the
# first delta there is nothing to show yet - this stands in for it.
THINKING = "_Mani is thinking…_"


def reset_thread_state(thread: dict, messages: list[dict]) -> None:
    st.session_state.thread = thread
    st.session_state.messages = messages
    st.session_state.last_turn = None
    st.session_state.debug_events = []
    st.session_state.locked = bool(
        thread.get("crisis_detected") and thread.get("crisis_blocks_chat")
    )


# ---------------------------------------------------------------------------
# Session - each person signs in or signs up with their own email and password,
# and the backend scopes every thread to the signed-in account.
# ---------------------------------------------------------------------------

if "email" not in st.session_state:
    render_login()
    st.stop()
# A browser tab keeps its session across edits to client.py, so it can hold an instance of the
# class as it was before the edit. Same sign-in, current class.
if not isinstance(st.session_state.client, mani.ManiClient):
    st.session_state.client = mani.ManiClient(session=st.session_state.client.session)

with st.sidebar:
    st.header("Session")
    st.caption(f"backend: {mani.API_BASE_URL}")
    st.caption(f"signed in: {st.session_state.email}")
    if st.button("Sign out", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    st.divider()
    if st.button("🆕 New conversation", use_container_width=True):
        try:
            started = st.session_state.client.start_new_thread()
        except (mani.ApiError, RuntimeError) as exc:
            st.error(str(exc))
            st.stop()
        reset_thread_state(started["thread"], started["messages"])
        st.rerun()

client: mani.ManiClient = st.session_state.client

# First load: continue the most recent conversation, or start the first one.
if "thread" not in st.session_state:
    try:
        conversations = client.list_threads()
        if conversations:
            reset_thread_state(conversations[0], client.list_messages(conversations[0]["id"]))
        else:
            started = client.start_new_thread()
            reset_thread_state(started["thread"], started["messages"])
    except (mani.ApiError, RuntimeError) as exc:
        st.error(f"Could not reach the backend at {client.base_url}: {exc}")
        st.stop()

thread = st.session_state.thread

if st.session_state.get("view") == "library":
    if st.button("← Back to chat"):
        st.session_state.view = "chat"
        st.rerun()
    st.header("Library")
    try:
        exercises = client.list_exercises()
    except (mani.ApiError, RuntimeError) as exc:
        st.error(str(exc))
        st.stop()
    for exercise in exercises:
        st.subheader(exercise.get("title") or "Exercise")
        if exercise.get("subtitle"):
            st.caption(exercise["subtitle"])
        if exercise.get("audio_url"):
            st.audio(exercise["audio_url"])
    st.stop()

st.title("Mani")

# ---------------------------------------------------------------------------
# The conversation itself
# ---------------------------------------------------------------------------

for message in st.session_state.messages:
    avatar = "🧠" if message["role"] == "mani" else "🧑"
    with st.chat_message("assistant" if message["role"] == "mani" else "user", avatar=avatar):
        st.write(message["content"])

last_turn = st.session_state.get("last_turn")
if last_turn and last_turn.get("crisis_detected"):
    st.error("🚨 **Crisis detected.** " + (last_turn.get("content") or ""))


def send(content: str) -> bool:
    """Stream one turn. The user's message shows at once; Mani's reply fills a
    placeholder as `delta` frames arrive. Returns True when the turn finished cleanly."""
    with st.chat_message("user", avatar="🧑"):
        st.write(content)
    events: list[tuple[str, str]] = []
    streamed = ""
    turn: dict | None = None
    failure: str | None = None
    with st.chat_message("assistant", avatar="🧠"):
        placeholder = st.empty()
        placeholder.markdown(THINKING)
        try:
            for event, data in client.stream_message(thread["id"], content):
                events.append((event, data))
                try:
                    parsed = json.loads(data) if data else {}
                except ValueError:
                    parsed = {}
                if event == "delta":
                    streamed += parsed.get("text", "")
                    placeholder.markdown(streamed)
                elif event == "reset":
                    # A retry streams a fresh attempt from scratch.
                    streamed = ""
                    placeholder.markdown(THINKING)
                elif event == "replace":
                    # The committed reply was revised after streaming.
                    streamed = parsed.get("text", "")
                    placeholder.markdown(streamed)
                elif event == "done":
                    turn = parsed
                elif event == "error":
                    failure = parsed.get("message") or "The turn failed."
        except mani.ApiError as exc:
            if exc.status == 404:
                # This backend commits the reply in one response. Show it whole,
                # the way the screen does once generation has finished.
                try:
                    turn = client.send_message(thread["id"], content)
                    streamed = turn.get("content") or ""
                    placeholder.markdown(streamed)
                    events.append(("reply", streamed))
                except (mani.ApiError, RuntimeError) as again:
                    failure = str(again)
            else:
                failure = str(exc)
        except RuntimeError as exc:
            failure = str(exc)
        if failure is None and turn is None:
            failure = "The stream ended without a done event."
        if failure is not None:
            placeholder.markdown(streamed or "*(no reply)*")
            st.error(failure)
    st.session_state.debug_events = events
    if failure is not None:
        return False

    # done's content is authoritative: where it differs from the streamed text, it wins.
    final = turn["content"] if turn.get("content") is not None else streamed
    if final != streamed:
        placeholder.markdown(final)
    st.session_state.messages.append({"role": "user", "content": content, "prompts": []})
    st.session_state.messages.append(
        {"role": "mani", "content": final, "prompts": turn.get("prompts") or []}
    )
    st.session_state.last_turn = turn
    if turn.get("title"):
        st.session_state.thread["title"] = turn["title"]
    if turn.get("crisis_detected") and turn.get("crisis_blocks_chat"):
        st.session_state.locked = True
    return True


if st.session_state.locked:
    st.warning("This conversation is paused after a crisis flag. Start a new conversation to continue.")
else:
    # Mani's newest message is the only one whose buttons are live, exactly as in the apps.
    # A tap sends the label as the person's message; the backend matches it to the button.
    latest = next((m for m in reversed(st.session_state.messages) if m["role"] == "mani"), None)
    buttons = (latest or {}).get("prompts") or []
    if buttons:
        cols = st.columns(len(buttons))
        for index, (col, button) in enumerate(zip(cols, buttons)):
            if col.button(
                button["label"],
                use_container_width=True,
                key=f"tap_{index}_{len(st.session_state.messages)}",
            ):
                if button.get("library"):
                    st.session_state.view = "library"
                    st.rerun()
                if send(button["label"]):
                    st.rerun()

# What the wire looked like on the last turn - the point of the demo, but collapsed
# so the chat itself stays in view.
with st.expander("Framework cadence (last turn)", expanded=False):
    ledger = (st.session_state.get("last_turn") or {}).get("ledger") or []
    if ledger:
        for row in ledger:
            mark = " ←" if row.get("asking") else ""
            st.text(f"{row.get('stage')}: {row.get('status')}{mark}")
    else:
        st.caption("No stage ledger on the last turn.")

# The in-flight exchange renders into this slot, which sits above the pinned chat input.
live = st.container()

if not st.session_state.locked:
    prompt = st.chat_input("Message Mani…")
    if prompt and prompt.strip():
        with live:
            if send(prompt.strip()):
                st.rerun()

# ---------------------------------------------------------------------------
# Sidebar: the person's conversations, newest activity first. Tapping one opens it
# to continue; the open one is marked and cannot be tapped.
# ---------------------------------------------------------------------------

with st.sidebar:
    st.divider()
    st.subheader("Conversations")
    try:
        conversations = client.list_threads()
    except (mani.ApiError, RuntimeError) as exc:
        conversations = []
        st.caption(f"Could not list conversations: {exc}")
    for item in conversations:
        is_open = item["id"] == thread["id"]
        when = (item.get("last_message_at") or "")[:16].replace("T", " ")
        if st.button(
            ("▶ " if is_open else "") + (item.get("title") or "Untitled"),
            key=f"thread_{item['id']}",
            disabled=is_open,
            use_container_width=True,
            help=f"{item.get('message_count', '?')} messages  ·  last active {when} UTC",
        ):
            try:
                messages = client.list_messages(item["id"])
            except (mani.ApiError, RuntimeError) as exc:
                st.error(str(exc))
                st.stop()
            reset_thread_state(item, messages)
            st.rerun()
    if not conversations:
        st.caption("No conversations yet.")
