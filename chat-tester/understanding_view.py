# ABOUTME: The sidebar's "What Mani knows": the thread record the backend sends with each turn while AI_DEBUG_MODE is
# ABOUTME: on - Mani's notes, the people and events, the replies ledger and the frameworks declined or finished.

from __future__ import annotations

from typing import Any

import streamlit as st

TITLE = "🧾 What Mani knows"
NOTHING = "Nothing yet, or AI_DEBUG_MODE is off in the backend."


def _person(person: dict[str, Any]) -> str:
    """Who they spoke of: "Sam (manager): keeps adding tasks"."""
    relation = f" ({person['relation']})" if person.get("relation") else ""
    told = f": {person['told']}" if person.get("told") else ""
    return f"{person.get('called', '')}{relation}{told}"


def _event(event: dict[str, Any]) -> str:
    """What happened or will, with when: "upcoming: review on Friday"."""
    return f"{event.get('when') or 'unsaid'}: {event.get('what', '')}"


def _reply(reply: dict[str, Any]) -> str:
    """One reply in the ledger: its move and gist, then the question it asked and their answer once given."""
    line = f"{reply.get('move', '')} - {reply.get('gist', '')}"
    if reply.get("q"):
        chat = ", open chat" if reply.get("open_chat") else ""
        line += f" · asked ({reply.get('intent', '')}{chat}): {reply['q']}"
        if reply.get("answer"):
            line += f" → {reply['answer']}"
    return line


def _list(label: str, items: list[str]) -> list[str]:
    return [f"**{label}:**", *(f"- {item}" for item in items)] if items else []


def lines(record: dict[str, Any]) -> list[str]:
    """The record as Markdown lines, each part left out when it is empty."""
    shown = [f"**Notes:** {record['notes']}"] if record.get("notes") else []
    shown += _list("People", [_person(p) for p in record.get("people") or []])
    shown += _list("Events", [_event(e) for e in record.get("events") or []])
    shown += _list("Replies, oldest first", [_reply(r) for r in record.get("replies") or []])
    for key, label in (("declined", "Declined"), ("finished", "Finished")):
        if record.get(key):
            shown.append(f"**{label}:** {' | '.join(record[key])}")
    return shown


def render(record: dict[str, Any] | None) -> None:
    st.subheader(TITLE)
    shown = lines(record or {})
    if shown:
        st.markdown("\n".join(shown))
    else:
        st.caption(NOTHING)
