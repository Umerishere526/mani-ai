# ABOUTME: A minimal chat UI against the real Mani backend - for trying frameworks and
# ABOUTME: exercise offers directly, not a product interface. Talks over HTTP like any client.

from __future__ import annotations

import asyncio
import json
import os

import streamlit as st
import streamlit.components.v1 as components

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


def run(coro):
    return asyncio.run(coro)


def reset_thread_state(thread: dict, messages: list[dict]) -> None:
    st.session_state.thread = thread
    st.session_state.messages = messages
    st.session_state.style = thread.get("conversation_style")
    st.session_state.locked = thread.get("crisis_detected") and thread.get("crisis_blocks_chat")
    st.session_state.last_turn = None


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


# Composer state. `draft` seeds the text field's initial value; the field's own widget
# key is `draft_{composer_cycle}`, deliberately a different name. Streamlit refuses to
# touch a widget's own key once it has rendered this run (confirmed by testing - it
# raises StreamlitWidgetAlreadyInstantiatedError), so both "fill it with a transcript"
# and "clear it after Send" work by bumping composer_cycle and reseeding `draft`, which
# mints a fresh widget next render instead of mutating the live one.
# `mic_cycle` mints a fresh key for the recorder after each use so the consumed clip
# disappears rather than sitting there re-triggering transcription on every rerun.
if "draft" not in st.session_state:
    st.session_state.draft = ""
if "composer_cycle" not in st.session_state:
    st.session_state.composer_cycle = 0
if "mic_cycle" not in st.session_state:
    st.session_state.mic_cycle = 0
# Whether the voice recorder panel is open. WhatsApp-style: tapping the mic icon pops
# it open above the composer row; it closes itself the moment a recording is stopped
# and handled, leaving just the (now-filled) text field - never left sitting open.
if "show_recorder" not in st.session_state:
    st.session_state.show_recorder = False

# Floats the composer above the bottom of the viewport as one rounded card, rather
# than a bar flush with the screen edge. `st-key-composer_bar` is the CSS class
# Streamlit derives from the container's key, so this only ever targets that one
# container - and everything inside it (including the recorder pop-up, when open)
# inherits the same rounded shape via overflow: hidden, rather than needing its own
# matching radius set separately.
st.markdown(
    """
    <style>
    .st-key-composer_bar {
        position: fixed;
        bottom: 1.25rem;
        /* left/width are a fallback for the instant before the JS sync below runs
           once; they are then overridden by the real content column's own
           position, since a fixed max-width guess here drifts out of alignment
           whenever the sidebar is collapsed/expanded or the window is resized -
           confirmed by measuring both live: with the sidebar open, the content
           column sat 150px right of a viewport-centered guess. */
        left: 0;
        right: 0;
        z-index: 999;
        margin-inline: auto;
        width: calc(100% - 2.5rem);
        max-width: 46rem;
        padding: 0.75rem 1rem;
        border-radius: 1.5rem;
        overflow: hidden;
        /* Hardcoded, not var(--...) - Streamlit's theme colors aren't exposed as
           stable named CSS variables in this version (checked: only emotion's
           auto-hashed ones are), so this must match .streamlit/config.toml's
           secondaryBackgroundColor by hand if that value ever changes. */
        background: #EEF3F0;
        border: 1px solid rgba(31, 122, 90, 0.25);
        box-shadow: 0 8px 24px rgba(28, 38, 33, 0.10);
    }
    .st-key-composer_bar div[data-testid="stForm"] {
        border: none;
        padding: 0;
    }
    /* The field sits flush in the card: no outline of its own, focused or not, and no
       "Press ⌘+Enter to submit form" hint, since Enter sends (wired up below). */
    .st-key-composer_bar [data-testid="stTextAreaRootElement"] {
        border: none;
    }
    .st-key-composer_bar [data-testid="InputInstructions"] {
        display: none;
    }
    /* WhatsApp-style: one line tall until the text wraps or Shift+Enter adds a line,
       then it grows up to a cap and scrolls inside. Streamlit renders the field with
       rows=3 and a 68px minimum, which is what made an empty field look like a box;
       field-sizing sizes it to its text instead. A browser without field-sizing keeps
       the three-row box and still works. */
    .st-key-composer_bar textarea {
        field-sizing: content;
        min-height: 0;
        max-height: 10rem;
    }
    /* Room at the bottom of the message feed so the last bubble never sits under
       the floating composer. */
    .block-container {
        padding-bottom: 10rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Keeps the floating composer's left edge and width locked to the real chat content
# column, not a guessed viewport-centered width. Needed because the content column is
# centered in the space *after* the sidebar, while a plain CSS fixed-position guess
# centers against the full viewport - measured live, that mismatch was 150px with the
# sidebar open. Runs in an iframe with documented same-origin access to the app (per
# components.v1.html's own docs), so window.parent.document reaches the real page.
components.html(
    """
    <script>
    function syncComposerBar() {
        const doc = window.parent.document;
        const bar = doc.querySelector(".st-key-composer_bar");
        const content = doc.querySelector(".block-container");
        if (!bar || !content) return;
        const rect = content.getBoundingClientRect();
        bar.style.left = rect.left + "px";
        bar.style.width = rect.width + "px";
        bar.style.right = "auto";
        bar.style.maxWidth = "none";
        bar.style.marginInline = "0";
    }
    syncComposerBar();
    window.parent.addEventListener("resize", syncComposerBar);
    const target = window.parent.document.querySelector(".block-container") || window.parent.document.body;
    new ResizeObserver(syncComposerBar).observe(target);
    // Also catches the sidebar's own collapse/expand animation, which resizes the
    // content column without firing a window resize event.
    setInterval(syncComposerBar, 250);
    </script>
    """,
    height=0,
)

if st.session_state.locked:
    st.warning("This conversation is paused after a crisis flag. Start a new conversation to continue.")
else:
    # Mani's newest message is the only one whose buttons are live, exactly as in the apps.
    # A tap sends the label as the person's message; the backend matches it to the button.
    # A button carrying a library section opens the library instead, as the apps navigate
    # there rather than sending anything.
    # type="secondary" (the default) on purpose: a suggested reply is a shortcut, not the
    # composer's Send action, and the two must not look like the same control.
    latest = next((m for m in reversed(st.session_state.messages) if m["role"] == "mani"), None)
    buttons = (latest or {}).get("prompts") or []
    if buttons:
        cols = st.columns(len(buttons))
        for index, (col, button) in enumerate(zip(cols, buttons)):
            if col.button(button["label"], use_container_width=True, key=f"tap_{index}_{len(st.session_state.messages)}"):
                if button.get("library"):
                    st.session_state.view = "library"
                else:
                    send(button["label"])
                st.rerun()

    # -----------------------------------------------------------------------
    # Composer: pinned to the bottom of the screen, flat rather than boxed. The mic
    # is a toggle button beside the field, WhatsApp-style - tapping it pops the
    # recorder open above the row; stopping a recording closes it again immediately,
    # so it's never left open once used.
    #
    # Voice never reaches the backend on its own. Recording stops -> Streamlit's own
    # player lets the person listen back -> this sends the clip to the transcription
    # endpoint only -> the result lands as editable draft text, same as if they'd typed
    # it. Only the Send button (or Enter in the field) calls send() - one trigger, same
    # as a typed message, no parallel path.
    # -----------------------------------------------------------------------
    # An open offer is answered with its buttons, as the apps will be: the field, Send and the mic
    # come back after any reply without one. An open recorder is closed too, so it does not
    # reappear on the next render.
    if any(button.get("technique") for button in buttons):
        st.session_state.show_recorder = False
    else:
        with st.container(key="composer_bar"):
            if st.session_state.show_recorder:
                st.caption("🎤 Recording - tap again to cancel")
                recording = st.audio_input(
                    "Voice message",
                    key=f"mic_{st.session_state.mic_cycle}",
                    label_visibility="collapsed",
                )

                if recording is not None:
                    with st.spinner("Transcribing…"):
                        try:
                            transcript = client.transcribe_audio(
                                recording.getvalue(), recording.name or "recording.wav"
                            )
                        except mani.ApiError as exc:
                            st.error(str(exc))
                            transcript = None
                    # Reset the recorder and close the panel regardless of outcome, so a
                    # failed or already-used clip never re-submits itself on the next
                    # rerun, and the panel vanishes the moment a recording is handled -
                    # it never sits open after stopping.
                    st.session_state.mic_cycle += 1
                    st.session_state.show_recorder = False
                    if transcript:
                        # Only ever fills the draft - nothing here calls send(). A fresh
                        # field key next render means this is a clean reseed, not a live
                        # mutation of an already-rendered widget.
                        st.session_state.draft = transcript
                        st.session_state.composer_cycle += 1
                    st.rerun()

            mic_col, composer_col = st.columns([1, 9])
            with mic_col:
                mic_icon = "✕" if st.session_state.show_recorder else "🎤"
                if st.button(mic_icon, key="mic_toggle", use_container_width=True):
                    st.session_state.show_recorder = not st.session_state.show_recorder
                    st.rerun()

            field_key = f"draft_{st.session_state.composer_cycle}"
            with composer_col:
                with st.form("composer", border=False, enter_to_submit=False):
                    field_col, button_col = st.columns([5, 1])
                    with field_col:
                        # A text area so a long message wraps and the field grows, instead of
                        # scrolling sideways. height="content" (Streamlit >=1.64) grows it with
                        # the text rather than fixing it at one size.
                        st.text_area(
                            "Message",
                            value=st.session_state.draft,
                            key=field_key,
                            placeholder="Type, or tap 🎤 and edit before sending…",
                            label_visibility="collapsed",
                            height="content",
                        )
                    with button_col:
                        submitted = st.form_submit_button(
                            "Send ➤", use_container_width=True, type="primary"
                        )

            if submitted:
                content = st.session_state[field_key].strip()
                if content:
                    send(content)
                # A new cycle means a new field key next render, seeded empty - the clean
                # way to clear it without touching the widget that just rendered.
                st.session_state.draft = ""
                st.session_state.composer_cycle += 1
                st.rerun()

    # A text_area takes plain Enter as a new line, so sending on Enter (Shift+Enter for a
    # real line break) is wired up by hand: this intercepts Enter in the composer's textarea
    # and clicks Send, rather than switching to st.chat_input, which has no way to seed the
    # field from a voice transcript the way this one does.
    components.html(
        """
        <script>
        function wireComposerEnter() {
            const doc = window.parent.document;
            const bar = doc.querySelector(".st-key-composer_bar");
            if (!bar) return;
            const textarea = bar.querySelector("textarea");
            const button = [...bar.querySelectorAll("button")]
                .find(b => b.innerText.includes("Send"));
            if (!textarea || !button || textarea.dataset.enterWired) return;
            textarea.dataset.enterWired = "1";
            textarea.addEventListener("keydown", (event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    button.click();
                }
            });
        }
        wireComposerEnter();
        new MutationObserver(wireComposerEnter)
            .observe(window.parent.document.body, {childList: true, subtree: true});
        </script>
        """,
        height=0,
    )

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
