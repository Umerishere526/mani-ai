# ABOUTME: A minimal chat UI against the real Mani backend - for trying frameworks and
# ABOUTME: exercise offers directly, not a product interface. Talks over HTTP like any client.

from __future__ import annotations

import asyncio
import json
import os

import streamlit as st

import client as mani
from library import render_library
import session_store
from login import render_login

# Off wherever this flag is unset - a deployed, client-facing instance - so there is no
# control on screen that could show a framework id, a stage name, or a database read.
# Muhammad's own local .env sets it; nothing else needs to.
DEV_MODE = os.environ.get("CHAT_TESTER_DEV_MODE", "") == "1"

st.set_page_config(page_title="Mani chat tester", page_icon="🧠", layout="centered")

# The greeting's style buttons, by the label the person taps - used only to show which
# style the conversation is in.
STYLES = {"direct": "Directive", "supportive": "Supportive", "reflective": "Reflective"}

# Where Mani's reply will appear, while it is on its way: three dots pulsing in a pill.
# Colours are .streamlit/config.toml's secondaryBackgroundColor, borderColor and primaryColor.
THINKING_PILL = """
<style>
/* Streamlit pushes message content down so one line of text centres on the avatar. The
   pill is as tall as the avatar instead (2rem), so it starts level with it. */
[data-testid="stChatMessageContent"]:has(.thinking-pill) {
    margin-top: 0;
}
.thinking-pill {
    box-sizing: border-box;
    display: inline-flex;
    gap: 0.3rem;
    align-items: center;
    height: 2rem;
    padding: 0 0.9rem;
    border-radius: 999px;
    background: #EEF3F0;
    border: 1px solid #D5E0DA;
}
.thinking-pill span {
    width: 0.45rem;
    height: 0.45rem;
    border-radius: 50%;
    background: #1F7A5A;
    animation: thinking-pulse 1.2s infinite ease-in-out;
}
.thinking-pill span:nth-child(2) { animation-delay: 0.15s; }
.thinking-pill span:nth-child(3) { animation-delay: 0.3s; }
@keyframes thinking-pulse {
    0%, 60%, 100% { transform: translateY(0); opacity: 0.35; }
    30% { transform: translateY(-0.25rem); opacity: 1; }
}
</style>
<div class="thinking-pill" aria-label="Mani is thinking"><span></span><span></span><span></span></div>
"""


def run(coro):
    return asyncio.run(coro)


def reset_thread_state(thread: dict, messages: list[dict]) -> None:
    st.session_state.thread = thread
    st.session_state.messages = messages
    st.session_state.style = thread.get("conversation_style")
    st.session_state.locked = thread.get("crisis_detected") and thread.get("crisis_blocks_chat")
    st.session_state.last_turn = None
    # A message still waiting to go belongs to the conversation it was typed in.
    st.session_state.pending = None


# ---------------------------------------------------------------------------
# Session - each person signs in or signs up with their own email and password,
# and the backend scopes every thread to the signed-in account. Keyed on the email
# because sign-in sets it alongside the client; a tab without one has no account to show.
# ---------------------------------------------------------------------------

if "email" not in st.session_state:
    # A reload opens a new connection, so st.session_state is empty even though the person
    # signed in a moment ago. Put their session back before showing a login screen they
    # have already been through - losing a conversation to a stray refresh is the worst
    # moment for it, because the reason people refresh is that a reply is taking too long.
    if not session_store.restore():
        render_login()
        st.stop()

# A browser tab keeps its session across edits to client.py, so it can hold an instance of the
# class as it was before the edit, without the methods added since. Same sign-in, current class.
if not isinstance(st.session_state.client, mani.ManiClient):
    st.session_state.client = mani.ManiClient(session=st.session_state.client.session)

with st.sidebar:
    st.header("Session")
    st.caption(f"backend: {mani.API_BASE_URL}")
    st.caption(f"signed in: {st.session_state.email}")
    if st.button("Sign out", use_container_width=True):
        session_store.end()
        st.session_state.clear()
        st.rerun()

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
        st.session_state.view = "chat"
        st.rerun()
    if st.button("📚 Library", use_container_width=True):
        st.session_state.view = "library"
        st.rerun()

client: mani.ManiClient = st.session_state.client

# Which screen is showing. The library replaces the chat rather than sitting beside it,
# as it does in the apps; the conversation is untouched and comes back as it was.
if st.session_state.get("view") == "library":
    render_library(client)
    st.stop()

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
    st.caption(f"user: {st.session_state.email}  ·  thread: {thread['id'][:8]}…")

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

# A message that has been sent and not yet answered: the person's own bubble straight away,
# and the thinking pill where Mani's reply will appear. The backend call itself runs at the
# very end of the script, once everything else on the page is drawn.
pending = st.session_state.get("pending")
if pending:
    with st.chat_message("user", avatar="🧑"):
        st.write(pending)
    with st.chat_message("assistant", avatar="🧠"):
        st.markdown(THINKING_PILL, unsafe_allow_html=True)


def send(content: str) -> None:
    # Only queues it. The rerun every caller makes shows it as pending, and that run
    # delivers it.
    st.session_state.pending = content


def deliver(content: str) -> None:
    # Cleared before the call, so a rerun that interrupts it cannot send the message twice.
    st.session_state.pending = None
    try:
        turn = client.send_message(thread["id"], content)
    except mani.ApiError as exc:
        # Kept in session state rather than shown here: the rerun that follows would wipe
        # an st.error before anyone could read it, and a failed send would look like nothing.
        st.session_state.send_error = str(exc)
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


# A voice transcript waiting to be put into the composer. The composer's own key can't be
# written once it has rendered this run (Streamlit raises), so the transcript is held here
# and written into `composer` on the next run, before the field is drawn.
if "voice_draft" not in st.session_state:
    st.session_state.voice_draft = None

if st.session_state.locked:
    st.warning("This conversation is paused after a crisis flag. Start a new conversation to continue.")
else:
    send_error = st.session_state.pop("send_error", None)
    if send_error:
        st.error(send_error)

    # Mani's newest message is the only one whose buttons are live, exactly as in the apps.
    # A tap sends the label as the person's message; the backend matches it to the button.
    # A button carrying a library section opens the library instead, as the apps navigate
    # there rather than sending anything.
    # type="secondary" (the default) on purpose: a suggested reply is a shortcut, not the
    # composer's Send action, and the two must not look like the same control.
    latest = next((m for m in reversed(st.session_state.messages) if m["role"] == "mani"), None)
    # Hidden while a message is on its way: they answer the reply before it.
    buttons = (latest or {}).get("prompts") or []
    if buttons and not pending:
        cols = st.columns(len(buttons))
        for index, (col, button) in enumerate(zip(cols, buttons)):
            if col.button(button["label"], use_container_width=True, key=f"tap_{index}_{len(st.session_state.messages)}"):
                if button.get("library"):
                    st.session_state.view = "library"
                else:
                    send(button["label"])
                st.rerun()

    # -----------------------------------------------------------------------
    # Composer: Streamlit's own chat input, pinned to the bottom of the page, with its
    # built-in mic. Enter sends, Shift+Enter adds a line.
    #
    # Voice never reaches the backend on its own. A recording comes back here, goes to the
    # transcription endpoint only, and the result lands in the field as editable text,
    # same as if it had been typed. Only sending text calls send() - one trigger, same as a
    # typed message, no parallel path.
    # -----------------------------------------------------------------------
    if st.session_state.voice_draft is not None:
        st.session_state.composer = st.session_state.voice_draft
        st.session_state.voice_draft = None

    # Disabled while a message is on its way: a second submit would rerun the script and
    # stop the one waiting on the reply.
    submitted = st.chat_input(
        "Type, or tap the mic and edit before sending…",
        key="composer",
        accept_audio=True,
        disabled=bool(pending),
    )

    if submitted and submitted.audio:
        with st.spinner("Transcribing…"):
            try:
                transcript = client.transcribe_audio(
                    submitted.audio.getvalue(), submitted.audio.name or "recording.wav"
                )
            except mani.ApiError as exc:
                st.error(str(exc))
                transcript = None
        # Only ever fills the field - nothing here calls send().
        if transcript:
            st.session_state.voice_draft = transcript
            st.rerun()
    elif submitted and submitted.text.strip():
        send(submitted.text.strip())
        st.rerun()

# ---------------------------------------------------------------------------
# Dev inspector - direct reads, not API calls. This is the point of the tool: seeing the
# framework state and what a turn cost, not just the reply text.
# ---------------------------------------------------------------------------

with st.sidebar:
    st.divider()
    # The person's conversations, newest activity first. Tapping one opens it to continue; the
    # open one is marked and cannot be tapped. "New conversation" above starts another.
    st.subheader("Conversations")
    try:
        conversations = client.list_threads()
    except mani.ApiError as exc:
        conversations = []
        st.caption(f"Could not list conversations: {exc}")
    for item in conversations:
        is_open = item["id"] == thread["id"]
        when = item["last_message_at"][:16].replace("T", " ")
        if st.button(
            ("▶ " if is_open else "") + (item.get("title") or "Untitled"),
            key=f"thread_{item['id']}",
            disabled=is_open,
            use_container_width=True,
            help=f"{item['message_count']} messages  ·  last active {when} UTC",
        ):
            try:
                opened = client.open_thread(item["id"])
            except mani.ApiError as exc:
                st.error(str(exc))
                st.stop()
            reset_thread_state(opened["thread"], opened["messages"])
            st.rerun()
    if not conversations:
        st.caption("No conversations yet.")

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

# The message send() queued goes to the backend last, so the person's message and the
# thinking pill are already on screen while Mani's reply is on its way.
if pending:
    deliver(pending)
    st.rerun()
