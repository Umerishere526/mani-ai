# ABOUTME: Mani's picture of the person, shared by the chat and every framework: what is happening, what they feel,
# ABOUTME: what they tell themselves, what they want and what is in the way. Pure merge and render functions.

from __future__ import annotations

import copy

from mani.llm.schema import PictureUpdate

# The key the picture is stored under in the thread's understanding record.
KEY = "picture"
SHIFTS = ("adds", "corrects", "new_issue", "back", "nothing_new")
PROBLEM_TYPES = ("belief", "situation", "both")
BELIEF_KINDS = ("thought", "happening")
RISK_TO = ("self", "others")
# Each list keeps its first entry, what they came with, and the latest ones up to this many.
LIST_LIMIT = 8
ENTRY_LIMIT = 150


def _clean(text: str | None) -> str:
    """An entry on one line, cut at a word boundary to ENTRY_LIMIT characters."""
    text = " ".join((text or "").split())
    if len(text) <= ENTRY_LIMIT:
        return text
    head = text[: ENTRY_LIMIT + 1]
    return head.rsplit(" ", 1)[0] if " " in head else text[:ENTRY_LIMIT]


def _same(a: str, b: str) -> bool:
    return " ".join(a.split()).casefold() == " ".join(b.split()).casefold()


def _capped(entries: list) -> list:
    """The first entry and the latest ones, LIST_LIMIT in all."""
    return entries if len(entries) <= LIST_LIMIT else [entries[0], *entries[-(LIST_LIMIT - 1):]]


def _text(entry) -> str:
    """The words of any entry, for matching a dropped one."""
    if isinstance(entry, str):
        return entry
    return entry.get("feeling") or entry.get("belief") or entry.get("risk") or ""


def _without(entries: list, dropped: list[str]) -> list:
    return [e for e in entries if not any(_same(_text(e), d) for d in dropped)]


def merge(stored: dict | None, update: PictureUpdate | None) -> dict:
    """The picture after their message: what it adds gathered, what it shows wrong dropped, the focus moved when
    they turn to another situation or back to an earlier one. A value off its closed list is ignored. `quiet` is how
    many messages in a row added nothing new."""
    picture = copy.deepcopy(stored or {})
    if update is None:
        return picture
    dropped = [_clean(d) for d in update.drop or [] if _clean(d)]
    for key in ("situations", "feelings", "beliefs", "risks"):
        if dropped and picture.get(key):
            picture[key] = _without(picture[key], dropped)
    for key in ("wants", "in_the_way"):
        if dropped and picture.get(key) and any(_same(picture[key], d) for d in dropped):
            picture.pop(key)

    situations = picture.get("situations") or []
    for situation in update.situations or []:
        if (situation := _clean(situation)) and not any(_same(situation, s) for s in situations):
            situations.append(situation)
    feelings = picture.get("feelings") or []
    for entry in update.feelings or []:
        feeling, about = _clean(entry.feeling), _clean(entry.about)
        if not feeling:
            continue
        known = next((f for f in feelings if _same(f["feeling"], feeling)), None)
        if known is None:
            feelings.append({"feeling": feeling, **({"about": about} if about else {})})
        elif about:
            known["about"] = about
    beliefs = picture.get("beliefs") or []
    for entry in update.beliefs or []:
        belief, kind = _clean(entry.belief), entry.kind.strip().lower()
        if not belief or kind not in BELIEF_KINDS:
            continue
        known = next((b for b in beliefs if _same(b["belief"], belief)), None)
        if known is None:
            beliefs.append({"belief": belief, "kind": kind})
        else:
            known["kind"] = kind
    risks = picture.get("risks") or []
    for entry in update.risks or []:
        risk, to = _clean(entry.risk), entry.to.strip().lower()
        if risk and to in RISK_TO and not any(_same(r["risk"], risk) for r in risks):
            risks.append({"risk": risk, "to": to})
    for key, entries in (("situations", situations), ("feelings", feelings), ("beliefs", beliefs), ("risks", risks)):
        if entries:
            picture[key] = _capped(entries)
        else:
            picture.pop(key, None)
    for key in ("wants", "in_the_way"):
        if value := _clean(getattr(update, key)):
            picture[key] = value

    shift = (update.shift or "").strip().lower()
    shift = shift if shift in SHIFTS else None
    if focus := _clean(update.focus):
        earlier = [e for e in picture.get("earlier") or [] if not _same(e, focus)]
        if picture.get("focus") and not _same(picture["focus"], focus) and shift in ("new_issue", "back"):
            earlier.append(picture["focus"])
        picture["focus"] = focus
        if earlier:
            picture["earlier"] = _capped(earlier)
        else:
            picture.pop("earlier", None)
    if (problem := (update.problem_type or "").strip().lower()) in PROBLEM_TYPES:
        picture["problem_type"] = problem
    if shift:
        picture["shift"] = shift
        picture["quiet"] = picture.get("quiet", 0) + 1 if shift == "nothing_new" else 0
    return picture


def render(picture: dict | None) -> str | None:
    """The picture on one line, as the model reads it each turn, or None when it holds nothing yet."""
    if not picture:
        return None
    feelings = [f["feeling"] + (f" (about {f['about']})" if f.get("about") else "") for f in picture.get("feelings") or []]
    beliefs = picture.get("beliefs") or []
    risks = picture.get("risks") or []
    parts = [
        ("focus", picture.get("focus")),
        ("what is happening", " | ".join(picture.get("situations") or [])),
        ("feelings", " | ".join(feelings)),
        ("what they tell themselves", " | ".join(b["belief"] for b in beliefs if b["kind"] == "thought")),
        ("what they say is really happening", " | ".join(b["belief"] for b in beliefs if b["kind"] == "happening")),
        ("what they want", picture.get("wants")),
        ("what is in the way", picture.get("in_the_way")),
        ("risks to them", " | ".join(r["risk"] for r in risks if r["to"] == "self")),
        ("risks to others", " | ".join(r["risk"] for r in risks if r["to"] == "others")),
        ("kind of problem", picture.get("problem_type")),
        ("earlier situations", " | ".join(picture.get("earlier") or [])),
    ]
    rendered = "; ".join(f"{name}: {value}" for name, value in parts if value)
    return rendered or None


def feeling_words(picture: dict | None) -> list[str]:
    """Every feeling in the picture, in the order they named them."""
    return [f["feeling"] for f in (picture or {}).get("feelings") or []]


def added_beliefs(before: dict | None, after: dict | None, kind: str = "thought") -> list[str]:
    """The beliefs of this kind the turn added, in order."""
    known = [b["belief"] for b in (before or {}).get("beliefs") or []]
    return [
        b["belief"] for b in (after or {}).get("beliefs") or []
        if b["kind"] == kind and not any(_same(b["belief"], k) for k in known)
    ]


def added_feelings(before: dict | None, after: dict | None) -> list[str]:
    """The feelings the turn added, in order, with what each is about when they said."""
    known = feeling_words(before)
    return [
        f["feeling"] + (f" about {f['about']}" if f.get("about") else "")
        for f in (after or {}).get("feelings") or []
        if not any(_same(f["feeling"], k) for k in known)
    ]
