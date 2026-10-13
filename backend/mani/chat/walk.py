# ABOUTME: The walk through a framework's stages: what they said per stage, merged and stepped by code.
# ABOUTME: Pure functions over the stored stage store and one reply; the orchestrator writes what they return.

from __future__ import annotations

import re
import uuid
import zlib
from dataclasses import dataclass, field

from mani.chat import repairs
from mani.chat.techniques import OFFERING
from mani.llm.schema import StageUpdate
from mani.models.rows import ENDING_STAGES, Framework

# Lowest first. A stage with no status is missing, below all of them.
STATUSES = ("partial", "possible", "known", "done")
# What a reply may report for a stage. done is set only by code, when the walk leaves the stage.
_REPORTED = frozenset({"partial", "possible", "known"})
# A stage stored with one of these is said back and confirmed once, never asked.
CONFIRMED = frozenset({"known", "possible"})
# How their message may answer the stage in force and move the walk on.
MOVES = frozenset({"agreed", "answered", "corrected", "let_go"})
SAID_LIMIT = 200
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


def start(framework: Framework, updates: list[StageUpdate] | None) -> Walked:
    """The turn they say yes: what they already said seeds a cleared store, and the walk opens on
    the first stage."""
    merged = merge({}, updates, framework, in_force=None)
    first = content_stages(framework)[0]
    return Walked(merged.entries, first, first, merged.notes)


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
    body_answered: bool = False,
) -> Walked:
    """A turn on the stage in force: merge, then move at most one phase. A second not_yet in a row
    moves on as let_go. `body_answered` is a body route answer at the closing, which wins over the
    stage answer."""
    before = entries.get(in_force) or {}
    merged = merge(entries, updates, framework, in_force=in_force)
    notes = list(merged.notes)
    tries = before.get("tries", 0)
    if body_answered:
        if answer is not None:
            notes.append(f"stage answer {answer} ignored for a body answer")
        moved = True
    else:
        if answer is not None and not _counts(answer, before, in_force in merged.updated):
            notes.append(f"stage answer invalid: {answer}")
            answer = None
        moved = answer in MOVES
        if not moved and tries >= 1:
            notes.append(f"{in_force} let go after a second not_yet")
            moved = True
    stored = merged.entries
    if not moved:
        stored[in_force] = {**stored.get(in_force, {}), "tries": tries + 1}
        return Walked(stored, in_force, None, notes)
    stored[in_force] = {"said": stored.get(in_force, {}).get("said", ""), "status": "done", "tries": 0}
    following = framework.phases[framework.phase_index(in_force) + 1]
    return Walked(stored, following, following if following in content_stages(framework) else None, notes)


def confirm_phrase(framework: Framework, stage: str, thread_id: uuid.UUID | str) -> str:
    """The phrase that closes a stage said back to them: the same per thread, and never the same on
    two neighbouring stages."""
    pool = framework.confirm_phrases
    if not pool:
        return ""
    return pool[(zlib.crc32(str(thread_id).encode()) + framework.phase_index(stage)) % len(pool)]


def reply_text(
    framework: Framework,
    walked: Walked,
    before: dict[str, dict],
    *,
    text: str,
    style: str,
    thread_id: uuid.UUID | str,
    feeling: str | None,
) -> tuple[str, list[str]]:
    """The reply and the fallbacks it took. A stage just reached opens with its letter line, then
    what its stored status calls for; otherwise it is the model's text. `before` is the store [ctx]
    showed, so the model's text is used only for the branch it was written for. A letter line the
    model wrote is dropped either way."""
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
    written_for = (before.get(reached) or {}).get("status")
    ask = _client_line(framework, reached, "ask", style) or ""
    confirm = _client_line(framework, reached, "confirm", style)
    if status in CONFIRMED and confirm:
        body = repairs.render_template(confirm, lead_line=None, slot=_mid_sentence(said))
        if body is None:
            notes.append("slot empty")
            body = ask
    elif status == "known":
        if written_for != "known":
            notes.append("branch changed")
            own = ""
        naming = repairs.without_sentences(own, lambda s: s.rstrip().endswith("?")).strip()
        if naming != own:
            notes.append("naming asks")
        naming = naming or f"You mentioned {_mid_sentence(said).rstrip('.,;:!? ')}."
        body = f"{naming} {confirm_phrase(framework, reached, thread_id)}".strip()
    elif status == "partial":
        body = own if written_for == "partial" and "?" in own else ""
        if not body:
            notes.append("gap asks nothing" if written_for == "partial" else "branch changed")
            body = ask
    else:
        missing = _client_line(framework, reached, "missing", style)
        body = repairs.render_template(missing, lead_line=None, slot=_mid_sentence(feeling)) if missing else None
        if missing and body is None:
            notes.append("slot empty")
        body = body or ask
    intro = ((framework.stages or {}).get(reached) or {}).get("intro")
    # One paragraph, as the client's document writes it: "A is for Activating Event. You've mentioned..."
    return " ".join(part for part in (intro, body) if part), notes


def next_line(framework: Framework, entries: dict[str, dict], phase: str) -> str:
    """What the reply's text is for, in each way their message can answer the stage in force, from
    the store before this turn. On the second try both ways move on."""
    following = framework.phases[framework.phase_index(phase) + 1]
    status = (entries.get(following) or {}).get("status")
    if following in ENDING_STAGES:
        moved = "the questions end, and the body check-in is sent after your text: write one short sentence, no question."
    elif status in CONFIRMED and (framework.stages.get(following) or {}).get("confirm"):
        moved = f"the next stage is {following}, which they already answered. Its check is sent for you, so your text is not sent."
    elif status == "known":
        moved = f"the next stage is {following}, which they already answered: write one sentence naming their words for it, no question."
    elif status == "partial":
        moved = f"the next stage is {following}, which is partly answered: write only the question for what next_stage still needs."
    else:
        moved = f"the next stage is {following}. Its question is sent for you, so your text is not sent."
    if (entries.get(phase) or {}).get("tries", 0) >= 1:
        return f"Whatever they answer, {moved}"
    return f"If you answer agreed, answered, corrected or let_go, {moved} If not_yet, write the follow up for this stage."


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
    missing up to the one the walk is on, and not reached after it."""
    at = framework.phase_index(phase)
    rows = []
    for stage in content_stages(framework):
        entry = entries.get(stage) or {}
        status = entry.get("status") or ("missing" if framework.phase_index(stage) <= at else "not_reached")
        rows.append({
            "stage": stage,
            "title": ((framework.stages or {}).get(stage) or {}).get("title"),
            "status": status,
            "known": entry.get("said") or None,
            "action": _ACTIONS[status],
            "asking": stage == phase,
        })
    return rows
