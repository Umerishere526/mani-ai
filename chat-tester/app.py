# ABOUTME: A minimal chat UI against the real Mani backend - for trying frameworks and
# ABOUTME: exercise offers directly, not a product interface. Talks over HTTP like any client.

from __future__ import annotations

import asyncio
import json
import os

import streamlit as st

import client as mani

# Off wherever this flag is unset - a deployed, client-facing instance - so there is no
# control on screen that could show a framework id, a stage name, or a database read.
# Muhammad's own local .env sets it; nothing else needs to.
DEV_MODE = os.environ.get("CHAT_TESTER_DEV_MODE", "") == "1"

st.set_page_config(page_title="Mani chat tester", page_icon="🧠", layout="centered")

# The greeting's style buttons, by the label the person taps - used only to show which
# style the conversation is in.
STYLES = {"direct": "Direct", "supportive": "Supportive", "reflective": "Reflective"}


def run(coro):
    return asyncio.run(coro)


def reset_thread_state(thread: dict, messages: list[dict]) -> None:
    st.session_state.thread = thread
    st.session_state.messages = messages
    st.session_state.style = thread.get("conversation_style")
    st.session_state.locked = thread.get("crisis_detected") and thread.get("crisis_blocks_chat")
    st.session_state.last_turn = None


# ---------------------------------------------------------------------------
# Session - one fixed test user, signed in automatically. No sign-up or sign-in
# screen: a public link to this tool must not be able to create or reach any
# account but this one against the real backend.
# ---------------------------------------------------------------------------

FIXED_TEST_USER = os.environ.get("CHAT_TESTER_FIXED_USER", "streamlit-tester")

if "client" not in st.session_state:
    try:
        session = mani.sign_in(FIXED_TEST_USER)
    except (RuntimeError, mani.ApiError) as exc:
        st.error(f"Could not sign in the test user: {exc}")
        st.stop()
    st.session_state.client = mani.ManiClient(session=session)
    st.session_state.user_id = session.user_id

with st.sidebar:
    st.header("Session")
    st.caption(f"backend: {mani.API_BASE_URL}")
    st.caption(f"test user: {FIXED_TEST_USER}")

    # The control itself is gone, not just off, wherever CHAT_TESTER_DEV_MODE is unset - a
    # deployed, client-facing instance - so there is nothing on screen a client could click
    # into and see a framework id, a stage name, or a database read.
    developer = DEV_MODE and st.toggle("Show developer details", key="developer")

    st.divider()
    if st.button("🆕 New conversation", use_container_width=True):
        try:
            started = st.session_state.client.start_new_thread()
        except mani.ApiError as exc:
            st.error(str(exc))
            st.stop()
        reset_thread_state(started["thread"], started["messages"])
        st.rerun()

client: mani.ManiClient = st.session_state.client

if "thread" not in st.session_state:
    try:
        started = client.start_or_resume_thread()
    except mani.ApiError as exc:
        st.error(f"Could not reach the backend at {client.base_url}: {exc}")
        st.stop()
    reset_thread_state(started["thread"], started["messages"])

thread = st.session_state.thread

st.title("🧠 Mani chat tester")
if developer:
    st.caption(f"user: {FIXED_TEST_USER}  ·  thread: {thread['id'][:8]}…")

# The style is chosen the way a person chooses it in the apps: by tapping one of the
# greeting's three buttons, which the backend turns into the style and its opener.
framework_state = run(mani.framework_debug_state(thread["id"])) if developer else None
caption = [f"style: {STYLES[st.session_state.style]}"] if st.session_state.style else []
if framework_state and framework_state.get("phase"):
    caption.append(f"framework: {framework_state['framework_id']} · stage: {framework_state['phase']}")
if caption:
    st.caption("  ·  ".join(caption))

# ---------------------------------------------------------------------------
# The conversation itself
# ---------------------------------------------------------------------------

for message in st.session_state.messages:
    avatar = "🧠" if message["role"] == "mani" else "🧑"
    with st.chat_message("assistant" if message["role"] == "mani" else "user", avatar=avatar):
        st.write(message["content"])

last_turn = st.session_state.get("last_turn")

# The reply that just arrived gets its own callouts - a framework offer, an exercise
# hand-off, or a crisis - which is the whole reason this tool exists.
if last_turn:
    if last_turn.get("crisis_detected"):
        st.error("🚨 **Crisis detected.** " + last_turn["content"])

    technique_prompts = [p for p in last_turn.get("prompts") or [] if p.get("technique")]
    if developer and technique_prompts:
        st.info(
            "🧩 **Framework offered:** "
            + ", ".join(p["technique"] for p in technique_prompts)
        )

    exercise = last_turn.get("exercise")
    if exercise:
        with st.container(border=True):
            st.success(f"🎧 **Exercise offered:** {exercise['title']}")
            if exercise.get("subtitle"):
                st.caption(exercise["subtitle"])
            if exercise.get("audio_url"):
                st.audio(exercise["audio_url"])

def send(content: str) -> None:
    with st.spinner("Mani is responding..."):
        try:
            turn = client.send_message(thread["id"], content)
        except mani.ApiError as exc:
            st.error(str(exc))
            return
    st.session_state.messages.append({"role": "user", "content": content, "prompts": []})
    st.session_state.messages.append(
        {"role": "mani", "content": turn["content"], "prompts": turn.get("prompts") or []}
    )
    st.session_state.last_turn = turn
    style = next((key for key, label in STYLES.items() if label == content.strip()), None)
    if style:
        st.session_state.style = style
    if turn.get("title"):
        st.session_state.thread["title"] = turn["title"]
    if turn.get("crisis_detected") and turn.get("crisis_blocks_chat"):
        st.session_state.locked = True


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
            if col.button(button["label"], use_container_width=True, key=f"tap_{index}_{len(st.session_state.messages)}"):
                send(button["label"])
                st.rerun()
    if typed := st.chat_input("Say something…"):
        send(typed)
        st.rerun()

# ---------------------------------------------------------------------------
# Dev inspector - direct reads, not API calls. This is the point of the tool: seeing the
# framework state and what a turn cost, not just the reply text.
# ---------------------------------------------------------------------------

with st.sidebar:
    st.divider()
    # Shown to a client too: that a returning person's patterns were kept is part of the demo.
    with st.expander("🧠 What Mani remembers"):
        memory = run(mani.remembered(st.session_state.user_id))
        entries = {k: v for k, v in ((memory or {}).get("memory") or {}).items() if v}
        if entries:
            for key, values in entries.items():
                st.markdown(f"**{key.replace('_', ' ').capitalize()}**")
                for value in values:
                    st.markdown(f"- {value}")
            st.caption(f"updated {memory['updated_at']:%H:%M:%S} - folded in when a new chat starts")
        else:
            st.caption("Nothing yet. It's folded in when this person starts a new chat.")

    if developer:
        with st.expander("🔍 Framework state (direct DB read)"):
            st.json(framework_state or {"active": False})

        with st.expander("💰 Recent calls (direct DB read)"):
            calls = run(mani.recent_call_costs(thread["id"]))
            for call in calls:
                st.text(
                    f"{call['purpose']:<15} {call['outcome']:<10} "
                    f"in={call['input_tokens']:<5} cached={call['cached_input_tokens']:<5} "
                    f"{call['latency_ms']}ms"
                )
            if not calls:
                st.caption("No calls recorded yet for this thread.")

        if last_turn:
            with st.expander("📦 Last turn, raw"):
                st.code(json.dumps(last_turn, indent=2, default=str), language="json")
