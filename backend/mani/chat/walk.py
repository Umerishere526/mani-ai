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
# What moves the walk on: their yes to Mani's say-back of a known stage, or their wish to skip it.
# answered and corrected store their words and wait for that yes (spec 0007, decision 6).
MOVES = frozenset({"agreed", "let_go"})
# They want the questions to stop altogether; the walk stays and the orchestrator records a decline.
STOPPED = "stopped"
# Once a stage has held this many replies, the reply offers the choice to keep going, skip or stop.
# No count ever moves a stage by itself (spec 0007, AC-1, AC-2).
STALL_LIMIT = 4
# How many questions or push-backs hold a stage without counting as a try; past that, an
# answer of asked counts as not_yet, so no stage is held for ever.
HELD_FOR_QUESTIONS = 2
SAID_LIMIT = 200
# How Mani confirms a stage the person already answered, in its own words (muhammad's team lead, 2026-10-13).
CONFIRM_ASK = (
    "Say back what they said for this stage, never another stage's part, to them as you, as what you now "
    "understand, and ask in your own words whether that is right, in one or two sentences, asked differently "
    "from the stage before. The stage moves only on their yes."
)
# A letter line the model writes is dropped: the stage is shown beside the chat, never said (spec 0007,
# decision 5).
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
            # The replaced words are kept, so a change is named from what it changed (spec 0007, AC-16).
            merged[stage] = {**stored, "said": said, "was": (stored.get("was") or [])[-2:] + [stored["said"]]}
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
    # They asked for the questions to stop; the store is untouched and the orchestrator records it.
    stopped: bool = False


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
        return before.get("status") in CONFIRMED and not before.get("gap")
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
    which is ignored when the walk stays. Only their yes to the say-back of a known stage (agreed) or
    a skip (let_go) moves the walk; answered and corrected store their words and wait for that yes,
    a correction to an earlier stage holds this one while Mani asks about it, a question or push-back
    (asked) holds it without a try up to HELD_FOR_QUESTIONS times, and stopped leaves everything as
    it was. No count ever moves a stage; the stall is offered as a choice in next_line.
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
        if answer == STOPPED:
            return Walked(merged.entries, in_force, None, notes + [f"{in_force} stopped by them"], stopped=True)
        if any(u.stage != in_force for u in now):
            return Walked(merged.entries, in_force, None,
                          notes + ["earlier stage corrected: clarified before moving"])
        if answer in ("answered", "corrected"):
            return Walked(merged.entries, in_force, None, notes + [f"{in_force} answered: said back for their yes"])
        moved = answer in MOVES
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
    """The reply and the fallbacks it took. A stage just reached is Mani's own text for it, written for
    what [ctx] told the reply the stage is (a say-back, the gap, or its own question about their
    situation), whenever that text asks something; the client's lines are the logged fallback when it
    asks nothing: its confirm line or a phrase for a known stage, its line for the gap, its missing line
    with their feeling word (A) or its ask for a missing one. A stage left unjudged gets the client's
    line. No letter line is sent, and one the model wrote is dropped (spec 0007, decision 5)."""
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
    if own_asks and not walked.unjudged:
        return own, notes
    if status in CONFIRMED:
        notes.append("confirm text unusable")
        body = _confirm_fallback(framework, reached, said, style, thread_id) or ask
    elif status == "partial":
        notes.append("gap asks nothing")
        body = _gap_line(framework, walked.entries, reached, entry.get("gap")) or ask
    else:
        if not walked.unjudged:
            notes.append("missing asks nothing")
        missing = _client_line(framework, reached, "missing", style)
        body = repairs.render_template(missing, lead_line=None, slot=_mid_sentence(feeling)) if missing else None
        if missing and body is None:
            notes.append("slot empty")
        body = body or ask
    return body, notes


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
        f"what they said. Missing: your text is your own question for it, about their situation in their "
        f"words, with next_stage_ask as its model; never name the letter or the stage."
    )


def next_line(framework: Framework, entries: dict[str, dict], phase: str) -> str:
    """What the reply's text is for, in each way their message can answer the stage in force, from
    the store before this turn. A question holds the stage until it has held it HELD_FOR_QUESTIONS
    times; past STALL_LIMIT replies on one stage the text offers the choice to keep going, skip or
    stop, and nothing moves without their answer."""
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
    tries = entry.get("tries", 0)
    prefix = (
        f"They have stayed on {phase} for {tries} replies. Your text offers the choice: keep going with "
        "it, skip it (answer let_go), or stop the questions here (answer stopped). "
        if tries >= STALL_LIMIT else ""
    )
    return (
        f"{prefix}If they give what this stage needs (answered or corrected), report it in stage_updates "
        "and your text says back what you now have for it in their words, as what you understand, and "
        "asks whether that is right; nothing moves until their yes. If agreed to your say-back of a "
        f"known stage, {moved} If agreed while the stage is still partial, ask only the gap. If not_yet, "
        "write the follow up for this stage, helped by stage_when_stuck when they don't know. If they "
        "correct an earlier stage, report it corrected: your text names the change in one sentence from "
        "their words and asks one question to be sure of it, and this stage waits. If let_go, "
        f"{moved} If stopped, say in one sentence that they can stop here; the two choices follow.{asked}"
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
