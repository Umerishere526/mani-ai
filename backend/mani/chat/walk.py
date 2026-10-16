# ABOUTME: The walk through a framework's stages: what they said per stage, merged and stepped by code.
# ABOUTME: Pure functions over the stored stage store and one reply; the orchestrator writes what they return.

from __future__ import annotations

import re
import uuid
import zlib
from dataclasses import dataclass, field

from mani.chat import repairs
from mani.chat.techniques import OFFERING
from mani.llm.schema import NextStage, StageUpdate
from mani.models.rows import ENDING_STAGES, Framework

# Lowest first. A stage with no status is missing, below all of them.
STATUSES = ("partial", "possible", "known", "done")
# What a reply may report for a stage. done is set only by code, when the walk leaves the stage.
_REPORTED = frozenset({"partial", "possible", "known"})
# A stage stored with one of these is said back and confirmed once, never asked.
CONFIRMED = frozenset({"known", "possible"})
# How their message may answer the stage in force and move the walk on.
MOVES = frozenset({"agreed", "answered", "corrected", "let_go"})
# How many questions or push-backs hold a stage without counting as a try; past that, an
# answer of asked counts as not_yet, so no stage is held for ever.
HELD_FOR_QUESTIONS = 2
SAID_LIMIT = 200
# How Mani confirms a stage the person already answered, in its own words (muhammad's team lead, 2026-10-13).
CONFIRM_ASK = (
    "Say back only what they said for this stage, never another stage's part, to them as you, and ask in "
    "your own words whether that is right, in one or two sentences, asked differently from the stage before."
)
_LETTER_LINE = re.compile(r"^\s*[A-E] is for\b")
# "I" and its contractions keep their capital inside a sentence; nothing else that starts their words does.
_FIRST_PERSON = re.compile(r"^I\b")


def content_stages(framework: Framework) -> list[str]:
    """The stages the person answers: after the offer and before the body route."""
    return [p for p in framework.phases if p != OFFERING and p not in ENDING_STAGES]


def _rank(entry: dict | None) -> int:
    status = (entry or {}).get("status")
    return STATUSES.index(status) if status in STATUSES else -1


def _short(said: str) -> str:
    """Their words on one line, at most SAID_LIMIT characters, cut at a word boundary."""
    said = " ".join(said.split())
    if len(said) <= SAID_LIMIT:
        return said
    head = said[: SAID_LIMIT + 1]
    return head.rsplit(" ", 1)[0] if " " in head else said[:SAID_LIMIT]


def _mid_sentence(words: str | None) -> str | None:
    """Their words as they read inside one of Mani's sentences: the first letter lowercase, unless it
    is "I". The model stores them as said, often as a sentence of their own."""
    words = (words or "").strip()
    if not words or _FIRST_PERSON.match(words):
        return words or None
    return words[0].lower() + words[1:]


def _client_line(framework: Framework, stage: str, key: str, style: str) -> str | None:
    return (((framework.stages or {}).get(stage) or {}).get(key) or {}).get(style)


@dataclass(frozen=True)
class Merged:
    entries: dict[str, dict]
    # The stages an update was applied to.
    updated: frozenset[str]
    notes: list[str]


def merge(
    entries: dict[str, dict],
    updates: list[StageUpdate] | None,
    framework: Framework,
    *,
    in_force: str | None,
) -> Merged:
    """This turn's updates merged into one framework's stored entries. On the stage in force the
    latest words win and the status never drops; elsewhere only a higher status replaces what is
    stored, or a correction, which replaces the words and keeps the higher status. Logged by stage
    id and status only, never their words."""
    stages = content_stages(framework)
    merged = {stage: dict(entry) for stage, entry in entries.items()}
    updated: set[str] = set()
    notes: list[str] = []
    for update in updates or []:
        stage, status, said = update.stage, update.status, _short(update.said or "")
        stored = merged.get(stage)
        if stage not in stages:
            notes.append("ignored update for a stage outside the framework")
            continue
        if status not in _REPORTED or (
            status == "possible" and not (framework.stages.get(stage) or {}).get("confirm")
        ):
            notes.append(f"ignored update for {stage}: status {status if status in STATUSES else 'off-list'}")
            continue
        if not said:
            notes.append(f"ignored update for {stage}: nothing said")
            continue
        if stage == in_force:
            kept = status if STATUSES.index(status) >= _rank(stored) else stored["status"]
            merged[stage] = {**(stored or {}), "said": said, "status": kept}
        elif STATUSES.index(status) > _rank(stored):
            merged[stage] = {**(stored or {}), "said": said, "status": status}
        elif update.corrected:
            merged[stage] = {**stored, "said": said}
        else:
            notes.append(f"ignored update for {stage}: {status} is not above {stored['status']}")
            continue
        merged[stage].pop("gap", None)
        updated.add(stage)
    return Merged(merged, frozenset(updated), notes)


@dataclass(frozen=True)
class Walked:
    # This framework's entries after the merge and the step.
    entries: dict[str, dict]
    # The phase to write.
    phase: str
    # The content stage this reply opens: the first on the start turn, or the next after a move.
    reached: str | None
    notes: list[str] = field(default_factory=list)
    # A stage was reached and the reply did not judge it, so its text was not written for it and the
    # client's question is sent: logged apart from a stage judged missing, which Mani asks itself.
    unjudged: bool = False


def _reach(
    framework: Framework, entries: dict[str, dict], reached: str | None, report: NextStage | None,
) -> tuple[dict[str, dict], list[str], bool]:
    """The stage reached, merged from this turn's judgement of it, made when it is reached from the
    whole conversation rather than guessed ahead (2026-10-13). Missing stores nothing, so its question
    is asked; no judgement at all is reported as unjudged."""
    if reached is None:
        return entries, [], False
    if report is None:
        return entries, [], True
    if report.status == "missing":
        return entries, [], False
    update = StageUpdate(stage=reached, said=report.said or "", status=report.status)
    merged = merge(entries, [update], framework, in_force=reached)
    entries = merged.entries
    if report.gap and reached in merged.updated and entries[reached].get("status") == "partial":
        entries[reached]["gap"] = report.gap
    return entries, merged.notes, False


def start(
    framework: Framework, updates: list[StageUpdate] | None, report: NextStage | None,
) -> Walked:
    """The turn they say yes: the walk opens on the first stage, judged from what they have said, on
    a cleared store. Nothing is stored for a later stage until the walk reaches it."""
    first = content_stages(framework)[0]
    entries, notes, unjudged = _reach(framework, {}, first, report)
    dropped = [f"dropped update for {u.stage}" for u in updates or []]
    return Walked(entries, first, first, dropped + notes, unjudged=unjudged)


def _counts(answer: str, before: dict, updated: bool) -> bool:
    """Whether the stage answer can be true of the stage in force. agreed answers a check of their
    words, so only a stage reached as one; answered and corrected bring words for it."""
    if answer == "agreed":
        return before.get("status") in CONFIRMED
    if answer in ("answered", "corrected"):
        return updated
    return True


def advance(
    framework: Framework,
    entries: dict[str, dict],
    updates: list[StageUpdate] | None,
    answer: str | None,
    *,
    in_force: str,
    report: NextStage | None = None,
    body_answered: bool = False,
) -> Walked:
    """A turn on the stage in force: merge what they said for it and any correction to an earlier
    stage, move at most one phase, then merge the stage reached from this turn's `report` of it,
    which is ignored when the walk stays. A second not_yet in a row moves on as let_go. A question or
    push-back (asked) holds the stage without a try, up to HELD_FOR_QUESTIONS times.
    `body_answered` is a body route answer at the closing, which wins over the stage answer. Nothing
    is stored for a stage before it is reached, and an entry stored ahead by an earlier version is
    ignored, so no stale words are said back."""
    stages = content_stages(framework)
    at = stages.index(in_force) if in_force in stages else len(stages)
    notes: list[str] = []
    ahead = [stage for stage in stages[at + 1:] if stage in entries and entries[stage].get("status") != "done"]
    if ahead:
        notes.append(f"ignored stored ahead: {', '.join(ahead)}")
    base = {stage: entry for stage, entry in entries.items() if stage not in ahead}
    now = [u for u in updates or [] if u.stage == in_force
           or (u.stage in stages and stages.index(u.stage) < at and u.corrected)]
    notes += [f"dropped update for {u.stage}" for u in updates or [] if u not in now]
    before = base.get(in_force) or {}
    if answer == "answered" and before.get("status") in CONFIRMED and not any(u.stage == in_force for u in now):
        # "Yes, and more": an answer to their words said back that brings no new words for the stage.
        notes.append("answered with no update read as agreed")
        answer = "agreed"
    merged = merge(base, now, framework, in_force=in_force)
    notes += merged.notes
    tries = before.get("tries", 0)
    if body_answered:
        if answer is not None:
            notes.append(f"stage answer {answer} ignored for a body answer")
        moved = True
    else:
        if answer is not None and not _counts(answer, before, in_force in merged.updated):
            notes.append(f"stage answer invalid: {answer}")
            answer = None
        held = before.get("asked", 0)
        if answer == "asked" and held < HELD_FOR_QUESTIONS:
            stored = merged.entries
            stored[in_force] = {**stored.get(in_force, {}), "asked": held + 1}
            return Walked(stored, in_force, None, notes)
        moved = answer in MOVES
        if not moved and tries >= 1:
            notes.append(f"{in_force} let go after a second not_yet")
            moved = True
    stored = merged.entries
    if not moved:
        stored[in_force] = {**stored.get(in_force, {}), "tries": tries + 1}
        return Walked(stored, in_force, None, notes)
    # A confirmation they did not agree to and gave no words for is let go with no words, so words they
    # rejected never stand as done.
    rejected = (
        not body_answered and before.get("status") in CONFIRMED and answer != "agreed"
        and in_force not in merged.updated
    )
    said = "" if rejected else stored.get(in_force, {}).get("said", "")
    stored[in_force] = {"said": said, "status": "done", "tries": 0}
    following = framework.phases[framework.phase_index(in_force) + 1]
    reached = following if following in stages else None
    stored, reach_notes, unjudged = _reach(framework, stored, reached, report)
    return Walked(stored, following, reached, notes + reach_notes, unjudged=unjudged)


def confirm_phrase(framework: Framework, stage: str, thread_id: uuid.UUID | str) -> str:
    """The phrase that closes a stage said back to them when Mani's own confirmation cannot be used:
    the same per thread, and never the same on two neighbouring stages."""
    pool = framework.confirm_phrases
    if not pool:
        return ""
    return pool[(zlib.crc32(str(thread_id).encode()) + framework.phase_index(stage)) % len(pool)]


def reply_text(
    framework: Framework,
    walked: Walked,
    *,
    text: str,
    style: str,
    thread_id: uuid.UUID | str,
    feeling: str | None,
) -> tuple[str, list[str]]:
    """The reply and the fallbacks it took. A stage just reached opens with its letter line, then
    what its stored status calls for; otherwise it is the model's text. Every stage reached is one
    [ctx] told the reply about, so once the reply judged it, the model's text is used for it when it
    asks something: a confirmation, the gap, or its question about their situation. A stage missing
    keeps the client's own line where it has one with their feeling word (A), and a stage left
    unjudged gets the client's line. A letter line the model wrote is dropped either way."""
    notes: list[str] = []
    own = repairs.without_sentences(text, lambda s: bool(_LETTER_LINE.match(s))).strip()
    if own != text.strip():
        notes.append("dropped a letter line")
    reached = walked.reached
    if reached is None:
        if not own and walked.phase in content_stages(framework):
            notes.append("stay text empty")
            own = _client_line(framework, walked.phase, "ask", style) or ""
        return own, notes

    entry = walked.entries.get(reached) or {}
    status, said = entry.get("status"), entry.get("said") or ""
    own_asks = "?" in own
    ask = _client_line(framework, reached, "ask", style) or ""
    if status in CONFIRMED:
        # Mani's own confirmation, what it understands for the stage and its own question (muhammad's
        # team lead, 2026-10-13). The client's line or a fixed phrase only when it cannot be used.
        if own_asks:
            body = own
        else:
            notes.append("confirm text unusable")
            body = _confirm_fallback(framework, reached, said, style, thread_id) or ask
    elif status == "partial":
        if own_asks:
            body = own
        else:
            notes.append("gap asks nothing")
            body = _gap_line(framework, walked.entries, reached, entry.get("gap")) or ask
    else:
        missing = _client_line(framework, reached, "missing", style)
        body = repairs.render_template(missing, lead_line=None, slot=_mid_sentence(feeling)) if missing else None
        if missing and body is None:
            notes.append("slot empty")
        if body is None and own_asks and not walked.unjudged:
            # Mani's own question for the stage, about their situation in their words, as the client's
            # document adapts it ("What makes you believe your manager is planning to replace you…"):
            # muhammad, 2026-10-14.
            body = own
        elif body is None:
            if not walked.unjudged:
                notes.append("missing asks nothing")
            body = ask
    intro = ((framework.stages or {}).get(reached) or {}).get("intro")
    # One paragraph, as the client's document writes it: "A is for Activating Event. You've mentioned..."
    return " ".join(part for part in (intro, body) if part), notes


def _gap_line(framework: Framework, entries: dict[str, dict], stage: str, gap: str | None) -> str | None:
    """The client's line for the part of a stage still missing, by its id in the stage's if_unclear,
    with the words of the stage the line names in its slot (D's "What might make you question the
    belief that <their belief>?"). None when the stage has no line for that part."""
    branch = next(
        (b for b in ((framework.stages or {}).get(stage) or {}).get("if_unclear") or []
         if gap and b.get("id") == gap),
        None,
    )
    if branch is None:
        return None
    words = _mid_sentence((entries.get(branch.get("slot")) or {}).get("said"))
    return repairs.render_template(branch["reply"], lead_line=None, slot=words.rstrip(".") if words else None)


def _confirm_fallback(
    framework: Framework, stage: str, said: str, style: str, thread_id: uuid.UUID | str,
) -> str | None:
    """A stage said back when Mani's own confirmation cannot be used: the client's confirm line where
    the stage has one, otherwise their words and a confirm phrase."""
    words = _mid_sentence(said)
    if not words:
        return None
    confirm = _client_line(framework, stage, "confirm", style)
    if confirm:
        return repairs.render_template(confirm, lead_line=None, slot=words)
    return f"You mentioned {words.rstrip('.,;:!? ')}. {confirm_phrase(framework, stage, thread_id)}".strip()


def reach_line(stage: str) -> str:
    """What the reply's text does for a stage the walk reaches, by what next_stage reports for it.
    How the stage is judged lives in the next_stage field and the stage's own lines in [ctx]."""
    return (
        f"your text follows what you report for {stage} in next_stage. Known or possible: your text is "
        f"its confirmation. {CONFIRM_ASK} Partial: your text asks only for what is missing, built on "
        f"what they said. Missing: your text is only the question, since its letter line is sent for you; "
        f"ask next_stage_ask as written, with what it refers to in their words."
    )


def next_line(framework: Framework, entries: dict[str, dict], phase: str) -> str:
    """What the reply's text is for, in each way their message can answer the stage in force, from
    the store before this turn. On the second try both ways move on; a question holds the stage until
    it has held it HELD_FOR_QUESTIONS times."""
    following = framework.phases[framework.phase_index(phase) + 1]
    if following in ENDING_STAGES:
        moved = "the questions end, and the body check-in is sent after your text: write one short sentence, no question."
    else:
        moved = f"the walk reaches {following}: {reach_line(following)}"
    entry = entries.get(phase) or {}
    asked = (
        " If asked, answer them plainly, then ask this stage's question again."
        if entry.get("asked", 0) < HELD_FOR_QUESTIONS else ""
    )
    if entry.get("tries", 0) >= 1:
        return f"Whatever else they answer, {moved}{asked}"
    return (
        f"If you answer agreed, answered, corrected or let_go, {moved} If not_yet, write the follow up for "
        f"this stage.{asked}"
    )


# What the walk does with a stage, for a person watching the conversation.
_ACTIONS = {
    "known": "said back and confirmed once",
    "possible": "a possible event, confirmed once",
    "partial": "partly known, ask only the gap",
    "done": "done",
    "missing": "missing, ask it",
    "not_reached": "not reached yet",
}


def ledger_view(framework: Framework, entries: dict[str, dict], phase: str) -> list[dict]:
    """Every content stage as the store holds it after this turn. A stage with nothing stored is
    missing up to the one the walk is on, and not reached after it, as is anything stored after it
    that is not done, which the walk ignores until it reaches the stage."""
    at = framework.phase_index(phase)
    rows = []
    for stage in content_stages(framework):
        entry = entries.get(stage) or {}
        ahead = framework.phase_index(stage) > at
        if ahead and entry.get("status") != "done":
            entry = {}
        status = entry.get("status") or ("not_reached" if ahead else "missing")
        rows.append({
            "stage": stage,
            "title": ((framework.stages or {}).get(stage) or {}).get("title"),
            "status": status,
            "known": entry.get("said") or None,
            "action": _ACTIONS[status],
            "asking": stage == phase,
        })
    return rows
