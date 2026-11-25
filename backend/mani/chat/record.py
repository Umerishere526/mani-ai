# ABOUTME: The thread record a turn keeps in threads.understanding: Mani's notes, the people and events they spoke of,
# ABOUTME: what each reply asked and gave, the frameworks declined or finished, and the safety keys. Pure helpers.

from __future__ import annotations

NOTES = "notes"
# Who they spoke of and what happened, as the model rewrites them each turn, cut to these bounds so the facts stay
# short.
PEOPLE = "people"
PEOPLE_KEPT = 8
EVENTS = "events"
EVENTS_KEPT = 10
# The longest a name or relation, and a line of what they said, may be (in characters).
NAME_CHARS = 60
LINE_CHARS = 200
WHEN = ("past", "now", "upcoming", "unsaid")
# Each reply, oldest first: the question it asked ("" for none) and what that question was for, whether it was in the
# open chat, its move and the gist of what it gave, its opening words, and once their next message answers its
# question, the gist of that answer.
REPLIES = "replies"
REPLIES_KEPT = 12
# What a reply mainly does (TurnReply.said.move); anything else is kept as "other".
MOVES = ("acknowledge", "reflect", "reassure", "highlight", "summarize", "help")
GIST_CHARS = 80
OPENING_WORDS = 4
DECLINED = "declined"
FINISHED = "finished"
# The library section the conversation is closest to, as the latest reply that named a valid one said.
LIBRARY = "library"
# The safety keys: where the question owed after a pause stands, whether a worry settled and whether danger was reached
# (each lasts the conversation), and whose danger the open worry is about (only while it is open).
RETURN_CHECK = "return_check"
SAFETY_SETTLED = "safety_settled"
DANGER_REACHED = "danger_reached"
ABOUT = "worry_about"
# Whether the open worry is about an overdose or a poisoning, kept only while it is open, so its pause leads with 911.
OVERDOSE = "worry_overdose"
# How many messages in a row were read as no concern while an unsure worry stayed open (worry.CALM_TO_CLEAR).
CALM = "worry_calm"
# Whether Mani knows if a worry about themselves is immediate (alone, a plan or the means, acting tonight): open once
# they confirm the thoughts, answered once they say; kept only while the worry is open (CR-1).
IMMEDIACY = "worry_immediacy"
IMMEDIACY_OPEN = "open"
IMMEDIACY_ANSWERED = "answered"
SAFETY_END_CHECK = "safety_end_check"
# Where the safety question after a framework's last stage stands.
END_CHECK_ASKED = "asked"
END_CHECK_DONE = "done"


def declined(record: dict) -> list[str]:
    """The frameworks declined in this conversation, never offered again."""
    return list(record.get(DECLINED) or [])


def finished(record: dict) -> list[str]:
    """The frameworks finished in this conversation, after which no framework is offered."""
    return list(record.get(FINISHED) or [])


def library(record: dict) -> str | None:
    """The library section the conversation is closest to, or None while no reply has named one."""
    return record.get(LIBRARY)


def replies(record: dict) -> list[dict]:
    """The replies kept, oldest first, each as {"q": the question or "", "intent": what it was for, "open_chat": whether
    it was in the open chat, "move", "gist", "opens": its first words}, with "answer" once their next message answered
    the question."""
    return list(record.get(REPLIES) or [])


def opening(text: str) -> str:
    """A reply's first OPENING_WORDS words, without the punctuation that ends them."""
    return " ".join(text.split()[:OPENING_WORDS]).rstrip(".,!?;:")


def with_answer(record: dict, answer: str) -> dict:
    """The record with the gist of their answer set on the last reply's question, when it asked one not yet answered;
    otherwise the record as it was."""
    kept = replies(record)
    answer = _clip(answer, GIST_CHARS)
    if not answer or not kept or not kept[-1].get("q") or kept[-1].get("answer"):
        return record
    return {**record, REPLIES: [*kept[:-1], {**kept[-1], "answer": answer}]}


def with_reply(record: dict, *, question: str, intent: str, open_chat: bool, move: str, gist: str, text: str) -> dict:
    """The record with this reply added, keeping the latest REPLIES_KEPT."""
    move = move.strip().lower()
    entry = {"q": question, "intent": intent, "open_chat": open_chat, "move": move if move in MOVES else "other",
             "gist": _clip(gist, GIST_CHARS), "opens": opening(text)}
    return {**record, REPLIES: [*replies(record), entry][-REPLIES_KEPT:]}


def return_check(record: dict, pause_id: str, state: str) -> dict:
    """The record with the question about pause `pause_id` at `state`: asked, or answered."""
    return {**record, RETURN_CHECK: {"pause": pause_id, "state": state}}


def return_check_pause(record: dict, *, state: str | None = None) -> str | None:
    """The pause the record's return check is about, or None; with `state`, only while it stands at that state."""
    check = record.get(RETURN_CHECK) or {}
    return check.get("pause") if state is None or check.get("state") == state else None


def end_check(record: dict) -> str | None:
    """Where the safety question after a framework's last stage stands: asked, done, or None."""
    return record.get(SAFETY_END_CHECK)


def people(record: dict) -> list[dict]:
    """The people kept, each as {"called": how they name them, "relation": who they are to them, "told": what they
    said about them}."""
    return list(record.get(PEOPLE) or [])


def events(record: dict) -> list[dict]:
    """The events kept, each as {"what": what happened or will, "when": past, now, upcoming or unsaid}."""
    return list(record.get(EVENTS) or [])


def _clip(text: str, limit: int) -> str:
    folded = " ".join((text or "").split())
    return folded if len(folded) <= limit else folded[:limit - 1].rstrip() + "…"


def bounded_people(given: list[dict]) -> list[dict]:
    """The people as the reply gave them, the latest PEOPLE_KEPT with a name, each cut to its bounds."""
    kept = [{"called": _clip(p.get("called", ""), NAME_CHARS), "relation": _clip(p.get("relation", ""), NAME_CHARS),
             "told": _clip(p.get("told", ""), LINE_CHARS)} for p in given]
    return [p for p in kept if p["called"]][-PEOPLE_KEPT:]


def bounded_events(given: list[dict]) -> list[dict]:
    """The events as the reply gave them, the latest EVENTS_KEPT that say something, each cut to its bounds, with a
    when outside the four read as unsaid."""
    kept = [{"what": _clip(e.get("what", ""), LINE_CHARS),
             "when": e.get("when") if e.get("when") in WHEN else "unsaid"} for e in given]
    return [e for e in kept if e["what"]][-EVENTS_KEPT:]


def with_outcomes(record: dict, *, notes: str | None, people: list[dict], events: list[dict], declined: list[str],
                  finished: list[str], library: str | None = None) -> dict:
    """The record with this turn's outcomes. The reply rewrites its people and events whole each turn, so they replace
    what is stored; `notes=None` and `library=None` keep what is already stored."""
    after = {**record, PEOPLE: bounded_people(people), EVENTS: bounded_events(events), DECLINED: declined,
             FINISHED: finished}
    if notes is not None:
        after[NOTES] = notes
    if library is not None:
        after[LIBRARY] = library
    return after
