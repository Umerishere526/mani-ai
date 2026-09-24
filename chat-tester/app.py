# ABOUTME: A minimal chat UI against the real Mani backend - for trying frameworks and
# ABOUTME: exercise offers directly, not a product interface. Talks over HTTP like any client.

from __future__ import annotations

import asyncio
import json

import streamlit as st

import client as mani

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
# Sidebar - the test user and the session controls
# ---------------------------------------------------------------------------

def start_session(sign_in, label: str, nickname: str, base_url: str) -> None:
    """Sign in one way or another, then start from a clean slate as that person."""
    try:
        session = sign_in()
        client = mani.ManiClient(session=session, base_url=base_url)
        if nickname.strip():
            # Before any chat starts, so the very first greeting already uses it.
            client.set_profile(nickname.strip())
    except (RuntimeError, mani.ApiError) as exc:
        st.error(str(exc))
        return
    st.session_state.clear()
    st.session_state.name = label
    st.session_state.user_id = session.user_id
    st.session_state.client = client
    st.rerun()


with st.sidebar:
    st.header("Test session")
    base_url = st.text_input("API base URL", value=mani.API_BASE_URL)
    quick, returning, new = st.tabs(["Quick user", "Sign in", "Sign up"])

    with quick:
        name = st.text_input("Test user name", value="tester-1", key="quick_name")
        nickname = st.text_input("Nickname (greeting)", key="quick_nickname")
        if st.button("Start / switch user", use_container_width=True):
            start_session(lambda: mani.sign_in(name), name, nickname, base_url)

    with returning, st.form("sign_in"):
        email = st.text_input("Email", key="sign_in_email")
        password = st.text_input("Password", type="password", key="sign_in_password")
        if st.form_submit_button("Sign in", use_container_width=True):
            start_session(lambda: mani.sign_in_with_password(email, password), email, "", base_url)

    with new, st.form("sign_up"):
        email = st.text_input("Email", key="sign_up_email")
        password = st.text_input("Password", type="password", key="sign_up_password")
        nickname = st.text_input("Nickname (greeting)", key="sign_up_nickname")
        if st.form_submit_button("Create account", use_container_width=True):
            start_session(lambda: mani.sign_up(email, password), email, nickname, base_url)

    if "client" in st.session_state:
        st.divider()
        if st.button("🆕 New conversation", use_container_width=True):
            try:
                started = st.session_state.client.start_new_thread()
            except mani.ApiError as exc:
                st.error(str(exc))
                st.stop()
            reset_thread_state(started["thread"], started["messages"])
            st.rerun()

if "client" not in st.session_state:
    st.title("🧠 Mani chat tester")
    st.write(
        "A dev interface for trying real conversations against the running backend - "
        "how a framework gets offered, when the somatic hand-off appears, when an "
        "exercise follows it. In the sidebar, sign up, sign in, or start a quick test user by "
        "name."
    )
    st.caption(
        "Needs the backend running (`fastapi dev main.py`) and `chat-tester/.env` filled "
        "in from `.env.example` - the DATABASE_URL and Supabase keys `supabase status -o env` "
        "prints."
    )
    st.stop()

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
st.caption(f"user: {st.session_state.name}  ·  thread: {thread['id'][:8]}…")

# The style is chosen the way a person chooses it in the apps: by tapping one of the
# greeting's three buttons, which the backend turns into the style and its opener.
framework_state = run(mani.framework_debug_state(thread["id"]))
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
    if technique_prompts:
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
    with st.expander("🔍 Framework state (direct DB read)"):
        st.json(framework_state or {"active": False})

    with st.expander("🧠 What Mani remembers (direct DB read)"):
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
