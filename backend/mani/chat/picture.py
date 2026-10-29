# ABOUTME: Mani's picture of the person, shared by the chat and every framework: what is happening, what they feel,
# ABOUTME: what they tell themselves, what they want, need and long for, and what is in the way. Pure merge and render.

from __future__ import annotations

import copy

from mani.llm.schema import PictureUpdate, Reading

# The key the picture is stored under in the thread's understanding record.
KEY = "picture"
# answered: a short answer to Mani's last question ("both"), which is not someone pulling away (muhammad, 2026-10-29).
SHIFTS = ("adds", "corrects", "new_issue", "back", "answered", "nothing_new")
PROBLEM_TYPES = ("belief", "situation", "both")
BELIEF_KINDS = ("thought", "happening")
RISK_TO = ("self", "others")
DEPENDENCY_KINDS = ("internal", "external")
CORE_ABOUT = ("self", "others", "situation")
# Each list keeps its first entry, what they came with, and the latest ones up to this many.
LIST_LIMIT = 8
# One line each, replaced whole when their message changes it: what they want in their words, and Mani's reading of
# the need underneath and the life they long for, beside what is in the way.
READINGS = ("wants", "needs", "desire", "in_the_way")
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
    for key in ("situations", "feelings", "underneath", "beliefs", "risks"):
        if dropped and picture.get(key):
            picture[key] = _without(picture[key], dropped)
    for key in READINGS:
        if dropped and picture.get(key) and any(_same(picture[key], d) for d in dropped):
            picture.pop(key)
    if dropped and picture.get("core") and any(_same(picture["core"]["belief"], d) for d in dropped):
        picture.pop("core")

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
    # The feelings under the ones they named, Mani's reading, each with what of theirs it rests on (muhammad,
    # 2026-10-29: the reading the core is built on).
    underneath = picture.get("underneath") or []
    for entry in update.underneath or []:
        feeling, rests_on = _clean(entry.feeling), _clean(entry.rests_on)
        if not feeling:
            continue
        known = next((u for u in underneath if _same(u["feeling"], feeling)), None)
        if known is None:
            underneath.append({"feeling": feeling, **({"rests_on": rests_on} if rests_on else {})})
        elif rests_on:
            known["rests_on"] = rests_on
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
    dependencies = picture.get("dependencies") or []
    for entry in update.dependencies or []:
        what, kind = _clean(entry.what), entry.kind.strip().lower()
        if what and kind in DEPENDENCY_KINDS and not any(_same(d["what"], what) for d in dependencies):
            dependencies.append({"what": what, "kind": kind})
    for key, entries in (
        ("situations", situations), ("feelings", feelings), ("underneath", underneath), ("beliefs", beliefs),
        ("risks", risks), ("dependencies", dependencies),
    ):
        if entries:
            picture[key] = _capped(entries)
        else:
            picture.pop(key, None)
    for key in READINGS:
        if value := _clean(getattr(update, key)):
            picture[key] = value
    if update.core is not None and (belief := _clean(update.core.belief)):
        about = update.core.about.strip().lower()
        if about in CORE_ABOUT:
            # The core is replaced whole: a deeper reading is a new core, not a second one. The feeling underneath
            # is kept from the last reading when this one does not say it.
            was = picture.get("core") or {}
            feeling = _clean(update.core.feeling) or was.get("feeling")
            tension = _clean(update.core.tension) or was.get("tension")
            picture["core"] = {
                "belief": belief, "about": about,
                **({"feeling": feeling} if feeling else {}), **({"tension": tension} if tension else {}),
            }

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


# What a reading field holds when nothing they said points to it. Never written over what the picture holds.
UNCLEAR = frozenset({"", "unclear", "unknown", "none", "n/a", "na", "null", "not yet", "not clear"})


def _known(value: str | None) -> str:
    """The reading's value, cleaned, or "" when it says it cannot tell."""
    value = _clean(value)
    return "" if value.casefold().strip(" .") in UNCLEAR else value


def apply_reading(stored: dict | None, reading: Reading | None) -> dict:
    """The picture with Mani's whole reading of them over it (approach A, 2026-10-29). The reading is re-read from
    the whole conversation every chat turn, so what it says replaces what the picture held; what it cannot tell
    ("unclear") keeps what the picture held. The facts, what is happening and what they named, stay the picture's."""
    picture = copy.deepcopy(stored or {})
    if reading is None:
        return reconcile(picture)
    underneath = []
    for entry in reading.underneath or []:
        feeling, rests_on = _known(entry.feeling), _known(entry.rests_on)
        if feeling and not any(_same(u["feeling"], feeling) for u in underneath):
            underneath.append({"feeling": feeling, **({"rests_on": rests_on} if rests_on else {})})
    if underneath:
        picture["underneath"] = _capped(underneath)
    for key in ("wants", "needs", "desire"):
        if value := _known(getattr(reading, key)):
            picture[key] = value
    if belief := _known(reading.core):
        was = picture.get("core") or {}
        about = reading.core_about.strip().lower()
        about = about if about in CORE_ABOUT else was.get("about", "self")
        core = {"belief": belief, "about": about}
        for key, value in (
            ("feeling", _known(reading.core_feeling) or was.get("feeling")),
            ("tension", _known(reading.tension) or was.get("tension")),
            ("rests_on", _known(reading.core_from) or (was.get("rests_on") if _same(was.get("belief", ""), belief) else "")),
        ):
            if value:
                core[key] = value
        picture["core"] = core
    if (problem := reading.problem_type.strip().lower()) in PROBLEM_TYPES:
        picture["problem_type"] = problem
    return reconcile(picture)


def reconcile(picture: dict) -> dict:
    """The picture made consistent with itself (approach C, 2026-10-29): what they tell themselves is never a
    situation alone. The partner chat held "I may be settling" as a thought and "situation" as the kind of problem,
    so the help offered only ways to make time."""
    thoughts = [b for b in picture.get("beliefs") or [] if b.get("kind") == "thought"]
    if (thoughts or picture.get("core")) and picture.get("problem_type") == "situation":
        picture["problem_type"] = "both"
    return picture


def render(picture: dict | None) -> str | None:
    """The picture on one line, as the model reads it each turn, or None when it holds nothing yet."""
    if not picture:
        return None
    feelings = [f["feeling"] + (f" (about {f['about']})" if f.get("about") else "") for f in picture.get("feelings") or []]
    underneath = [
        u["feeling"] + (f" (from \"{u['rests_on']}\")" if u.get("rests_on") else "") for u in picture.get("underneath") or []
    ]
    beliefs = picture.get("beliefs") or []
    risks = picture.get("risks") or []
    parts = [
        ("focus", picture.get("focus")),
        ("what is happening", " | ".join(picture.get("situations") or [])),
        ("feelings", " | ".join(feelings)),
        ("feelings under the ones they named, your reading", " | ".join(underneath)),
        ("what they tell themselves", " | ".join(b["belief"] for b in beliefs if b["kind"] == "thought")),
        ("what they say is really happening", " | ".join(b["belief"] for b in beliefs if b["kind"] == "happening")),
        ("what they want, in their words", picture.get("wants")),
        ("what they need underneath, your reading", picture.get("needs")),
        ("what they long for, your reading", picture.get("desire")),
        ("the core", (picture.get("core") or {}).get("belief")),
        ("the feeling underneath, your reading", (picture.get("core") or {}).get("feeling")),
        ("the tension", (picture.get("core") or {}).get("tension")),
        ("the core rests on, their words", (picture.get("core") or {}).get("rests_on")),
        ("what is in the way", picture.get("in_the_way")),
        ("risks to them", " | ".join(r["risk"] for r in risks if r["to"] == "self")),
        ("risks to others", " | ".join(r["risk"] for r in risks if r["to"] == "others")),
        ("depends on, inside them", " | ".join(
            d["what"] for d in picture.get("dependencies") or [] if d["kind"] == "internal")),
        ("depends on, outside them", " | ".join(
            d["what"] for d in picture.get("dependencies") or [] if d["kind"] == "external")),
        ("kind of problem", picture.get("problem_type")),
        ("earlier situations", " | ".join(picture.get("earlier") or [])),
    ]
    rendered = "; ".join(f"{name}: {value}" for name, value in parts if value)
    return rendered or None


def core(picture: dict | None) -> dict:
    """The core of it, {belief, about, feeling}, or {} while it is not known."""
    return (picture or {}).get("core") or {}


def new_core(before: dict | None, after: dict | None) -> str | None:
    """The core belief when this turn found it or saw it deeper, or None when it stayed the same."""
    was, now = core(before).get("belief"), core(after).get("belief")
    return now if now and not (was and _same(was, now)) else None


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
