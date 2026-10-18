# ABOUTME: The walk through a framework's stages: what they said per part of a stage, and when a stage moves.
# ABOUTME: Pure functions over the stored stage store and one reply; the orchestrator writes what they return.

from __future__ import annotations

import copy
import re
import uuid
import zlib
from dataclasses import dataclass, field, replace

from mani.chat import repairs
from mani.chat.techniques import OFFERING
from mani.llm.schema import NextStage, StageUpdate
from mani.models.rows import ENDING_STAGES, Framework

# Where a stage is, in order: its parts are being collected, Mani's reading of them waits for their yes,
# Mani asked what they take from it, done. The content decides which parts a stage has and which are
# required; code decides the step (spec 0007).
COLLECTING, READ, REFLECT, DONE = "collecting", "read", "reflect", "done"
# They want the questions to stop altogether; the walk stays and the orchestrator records a decline.
STOPPED = "stopped"
# Once a stage has held this many replies without progress, the reply offers the choice to keep going,
# skip or stop. No count ever moves a stage by itself (spec 0007, AC-1, AC-2).
STALL_LIMIT = 4
# How many questions or push-backs hold a stage without counting as a try; past that, an
# answer of asked counts as not_yet, so no stage is held for ever.
HELD_FOR_QUESTIONS = 2
SAID_LIMIT = 200
# How Mani gives its reading of a stage, in its own words (muhammad's team lead, 2026-10-13).
CONFIRM_ASK = (
    "Give your reading of this stage only, as what you now understand, put in a new way, never their words "
    "handed back, and ask in your own words whether it fits. The stage moves only on their yes."
)
# A reference inside a part's question: another part's id, or `understanding.<key>`.
_REF = re.compile(r"<([a-z_.]+)>")
# "I" and its contractions keep their capital inside a sentence; nothing else that starts their words does.
_FIRST_PERSON = re.compile(r"^I\b")


def content_stages(framework: Framework) -> list[str]:
    """The stages the person answers: after the offer and before the body route."""
    return [p for p in framework.phases if p != OFFERING and p not in ENDING_STAGES]


def specs(framework: Framework, stage: str) -> list[dict]:
    """The parts a stage is made of, as its content declares them, in order."""
    return list(((framework.stages or {}).get(stage) or {}).get("parts") or [])


def _owners(framework: Framework) -> dict[str, str]:
    """Which stage each part id belongs to; ids are unique across a framework (checked at seed)."""
    return {p["id"]: stage for stage in content_stages(framework) for p in specs(framework, stage)}


def _required(spec: dict) -> bool:
    return spec.get("required", True)


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


def is_stored(entry: object) -> bool:
    """Whether a stored entry has the shape the walk writes; an earlier shape is ignored."""
    return isinstance(entry, dict) and "step" in entry


def _fresh() -> dict:
    return {"parts": {}, "step": COLLECTING, "tries": 0}


def _filled(entry: dict, part: str) -> bool:
    held = entry["parts"].get(part)
    return bool(held and (held.get("said") or held.get("released")))


def missing_parts(framework: Framework, stage: str, entry: dict) -> list[str]:
    """The required parts of a stage still empty, in the order the content lists them."""
    return [p["id"] for p in specs(framework, stage) if _required(p) and not _filled(entry, p["id"])]


def _snapshot(framework: Framework, stage: str, entry: dict) -> dict[str, str]:
    """What a reading of the stage rests on: the words of its required parts."""
    return {p["id"]: entry["parts"][p["id"]].get("said", "") for p in specs(framework, stage)
            if _required(p) and _filled(entry, p["id"])}


def _apply(entry: dict, updates: list[StageUpdate], parts: list[dict]) -> bool:
    """This turn's updates merged into one stage's entry. A part they rejected is emptied; one released
    keeps the closest thing they said; words of their own are never replaced by an inference; replaced
    words are kept, so a change is named from what it changed. True when anything changed."""
    ids = {p["id"] for p in parts}
    changed = False
    for update in updates:
        if update.part not in ids:
            continue
        old = entry["parts"].get(update.part)
        said = _short(update.said or "")
        if update.rejected:
            if old:
                del entry["parts"][update.part]
                changed = True
            continue
        if update.released:
            new = {"said": said or (old or {}).get("said", ""), "source": "said", "released": True}
        elif said:
            new = {"said": said, "source": "inferred" if update.inferred else "said"}
            if old and old.get("said") == said and old.get("source") == new["source"] and not old.get("released"):
                continue
            if old and old.get("source") == "said" and new["source"] == "inferred" and not old.get("released"):
                continue
        else:
            continue
        if old and old.get("said") and old["said"] != new["said"]:
            new["was"] = (old.get("was") or [])[-2:] + [old["said"]]
        entry["parts"][update.part] = new
        changed = True
    return changed


def _from_known(entry: dict, parts: list[dict], known: dict | None) -> bool:
    """Parts the content binds to the person's running understanding (`from: understanding.<key>`) are
    filled from it as an inference, once per value: a part they rejected stays empty until the
    understanding itself moves, and their own words are never replaced."""
    marks = dict(entry.get("from") or {})
    changed = False
    for spec in parts:
        key = (spec.get("from") or "").removeprefix("understanding.")
        value = _short(str((known or {}).get(key) or "")) if spec.get("from") else ""
        if not value or marks.get(spec["id"]) == value:
            continue
        marks[spec["id"]] = value
        held = entry["parts"].get(spec["id"])
        if held is None or (held.get("source") == "inferred" and held.get("said") != value):
            entry["parts"][spec["id"]] = {"said": value, "source": "inferred"}
            changed = True
    if marks:
        entry["from"] = marks
    return changed


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
    known: dict | None,
) -> tuple[dict[str, dict], list[str], bool]:
    """The stage reached, filled from this turn's judgement of it, made when it is reached from the
    whole conversation rather than guessed ahead (2026-10-13), and from the understanding the content
    binds its parts to. It opens as a reading when every required part is answered, since [ctx] told the
    reply what the understanding holds for its parts and its text was written as the reading; otherwise it
    opens collecting. Nothing stored
    means nothing answers it, so its question is asked; no judgement at all is reported as unjudged."""
    if reached is None:
        return entries, [], False
    if report is None:
        return entries, [], True
    parts = specs(framework, reached)
    entry = _fresh()
    reported = [u.model_copy(update={"rejected": None, "corrected": None, "released": None})
                for u in report.parts or []]
    _apply(entry, reported, parts)
    _from_known(entry, parts, known)
    if not entry["parts"]:
        return entries, [], False
    if not missing_parts(framework, reached, entry):
        entry["step"], entry["read"] = READ, _snapshot(framework, reached, entry)
    return {**entries, reached: entry}, [], False


def start(
    framework: Framework, updates: list[StageUpdate] | None, report: NextStage | None,
    known: dict | None = None,
) -> Walked:
    """The turn they say yes: the walk opens on the first stage, judged from what they have said, on
    a cleared store. Nothing is stored for a later stage until the walk reaches it."""
    first = content_stages(framework)[0]
    entries, notes, unjudged = _reach(framework, {}, first, report, known)
    dropped = [f"dropped update for {u.part}" for u in updates or []]
    return Walked(entries, first, first, dropped + notes, unjudged=unjudged)


def advance(
    framework: Framework,
    entries: dict[str, dict],
    updates: list[StageUpdate] | None,
    answer: str | None,
    *,
    in_force: str,
    report: NextStage | None = None,
    body_answered: bool = False,
    known: dict | None = None,
    hold: bool = False,
) -> Walked:
    """A turn on the stage in force: merge the parts they gave and any correction to an earlier stage,
    then step it. The parts decide: with every required part filled the stage gives Mani's reading
    and waits for their yes (agreed); the yes moves it, or first brings Mani's question about what they
    take from it when the stage has one, and any answer to that question moves it. Words that change
    a part give a new reading, a part they reject is asked again, and a skip (let_go) moves it with
    nothing they did not agree to kept. A question or push-back (asked) holds the stage without a try
    up to HELD_FOR_QUESTIONS times, `hold` holds it while a feeling change or a shift awaits their
    answer, and stopped leaves everything as it was. No count ever moves a stage; the stall is offered
    as a choice in next_line. `body_answered` is a body route answer at the closing, which wins over
    the stage answer. Nothing is stored for a stage before it is reached; entries stored ahead, or in
    an earlier shape, are ignored, so no stale words are said back."""
    stages = content_stages(framework)
    at = stages.index(in_force) if in_force in stages else len(stages)
    notes: list[str] = []
    stale = [s for s, e in entries.items() if s in stages and not is_stored(e)]
    if stale:
        notes.append(f"ignored stored in an earlier shape: {', '.join(stale)}")
    ahead = [s for s in stages[at + 1:] if is_stored(entries.get(s)) and entries[s]["step"] != DONE]
    if ahead:
        notes.append(f"ignored stored ahead: {', '.join(ahead)}")
    base = {s: copy.deepcopy(e) for s, e in entries.items() if s in stages and is_stored(e) and s not in ahead}
    owners = _owners(framework)
    mine: list[StageUpdate] = []
    earlier: dict[str, list[StageUpdate]] = {}
    for update in updates or []:
        stage = owners.get(update.part)
        if stage == in_force:
            mine.append(update)
        elif stage in stages and stages.index(stage) < at and (update.corrected or update.rejected):
            earlier.setdefault(stage, []).append(update)
        else:
            notes.append(f"dropped update for {update.part}")
    entry = base.get(in_force) or _fresh()
    parts = specs(framework, in_force)
    changed = _apply(entry, mine, parts)
    changed = _from_known(entry, parts, known) or changed
    for stage, group in earlier.items():
        other = base.get(stage) or {**_fresh(), "step": DONE}
        _apply(other, group, specs(framework, stage))
        base[stage] = other
    step, tries = entry["step"], entry.get("tries", 0)
    complete = bool(entry["parts"]) and not missing_parts(framework, in_force, entry)
    snapshot = _snapshot(framework, in_force, entry)

    def stay(*, progress: bool = False, counted: bool = True) -> Walked:
        if counted:
            entry["tries"] = 0 if progress else tries + 1
        base[in_force] = entry
        return Walked(base, in_force, None, notes)

    if body_answered:
        if answer is not None:
            notes.append(f"stage answer {answer} ignored for a body answer")
    else:
        if answer == "agreed" and step != READ:
            notes.append("stage answer invalid: agreed")
            answer = None
        held = entry.get("asked", 0)
        if answer == "asked" and held < HELD_FOR_QUESTIONS:
            entry["asked"] = held + 1
            return stay(counted=False)
        if answer == STOPPED:
            base[in_force] = entry
            return Walked(base, in_force, None, notes + [f"{in_force} stopped by them"], stopped=True)
        if hold:
            notes.append(f"{in_force} held while a change awaits their answer")
            return stay(counted=False)
        if earlier:
            notes.append("earlier stage corrected: clarified before moving")
            return stay(counted=False)
        if answer == "let_go":
            if step == READ:
                entry["parts"] = {}
        elif step == REFLECT:
            pass
        elif step == READ:
            if answer == "agreed":
                # Their yes stands even with more added: the words are kept and nothing is read again.
                if (framework.stages.get(in_force) or {}).get("reflect"):
                    entry["step"] = REFLECT
                    notes.append(f"{in_force} agreed: asking what they take from it")
                    return stay(progress=True)
            elif changed:
                if complete:
                    entry["step"], entry["read"] = READ, snapshot
                    notes.append(f"{in_force} changed: read again for their yes")
                else:
                    entry["step"] = COLLECTING
                    notes.append(f"{in_force} part emptied: asked again")
                return stay(progress=True)
            else:
                return stay()
        elif complete:
            entry["step"], entry["read"] = READ, snapshot
            notes.append(f"{in_force} complete: read for their yes")
            return stay(progress=True)
        else:
            return stay(progress=changed)
    entry.update(step=DONE, tries=0)
    entry.pop("asked", None)
    base[in_force] = entry
    following = framework.phases[framework.phase_index(in_force) + 1]
    reached = following if following in stages else None
    stored, reach_notes, unjudged = _reach(framework, base, reached, report, known)
    return Walked(stored, following, reached, notes + reach_notes, unjudged=unjudged)


def with_last_ask(framework: Framework, walked: Walked, text: str) -> Walked:
    """The walk with the question the reply ends on kept on its stage, so that when they don't know the
    next reply can ask it again in fresh words."""
    stage = walked.reached or walked.phase
    match = repairs.last_question(text)
    if walked.stopped or stage not in content_stages(framework) or not match:
        return walked
    entries = {**walked.entries, stage: {**(walked.entries.get(stage) or _fresh()), "last_ask": _short(match)}}
    return replace(walked, entries=entries)


def confirm_phrase(framework: Framework, stage: str, thread_id: uuid.UUID | str) -> str:
    """The phrase that closes a stage said back to them when Mani's own confirmation cannot be used:
    the same per thread, and never the same on two neighbouring stages."""
    pool = framework.confirm_phrases
    if not pool:
        return ""
    return pool[(zlib.crc32(str(thread_id).encode()) + framework.phase_index(stage)) % len(pool)]


def values(framework: Framework, entries: dict[str, dict], known: dict | None) -> dict[str, str]:
    """What a part's question may refer to by name: every part stored so far, and the person's running
    understanding as `understanding.<key>`."""
    held = {pid: _mid_sentence(p.get("said")) or ""
            for e in entries.values() if is_stored(e) for pid, p in e["parts"].items()}
    held.update({f"understanding.{k}": _mid_sentence(v) or "" for k, v in (known or {}).items()
                 if isinstance(v, str)})
    return held


def _fill(template: str, named: dict[str, str]) -> str | None:
    """A question with the words it refers to put in, or None when one it refers to is not there."""
    absent = False

    def put(match: re.Match) -> str:
        nonlocal absent
        value = named.get(match.group(1), "")
        absent = absent or not value
        return value.rstrip(".,;:!? ")

    text = _REF.sub(put, template)
    return None if absent else text


def _part_question(
    framework: Framework, entries: dict[str, dict], stage: str, style: str, known: dict | None,
) -> str | None:
    """The content's question for the first required part still empty, with what it refers to in their
    words; None when the part has none or what it refers to is not known."""
    entry = entries.get(stage) if is_stored(entries.get(stage)) else _fresh()
    absent = missing_parts(framework, stage, entry)
    spec = next((p for p in specs(framework, stage) if absent and p["id"] == absent[0]), None)
    ask = repairs.styled(spec.get("ask"), style) if spec else None
    return _fill(ask, values(framework, entries, known)) if ask else None


def _reading_fallback(
    framework: Framework, stage: str, entry: dict, style: str, thread_id: uuid.UUID | str,
) -> str | None:
    """A stage said back when Mani's own reading cannot be used: the content's confirm line where the
    stage has one, otherwise their words and a confirm phrase."""
    said = "; ".join(entry["parts"][p].get("said", "") for p in _snapshot(framework, stage, entry))
    words = _mid_sentence(said)
    if not words:
        return None
    confirm = repairs.styled(((framework.stages or {}).get(stage) or {}).get("confirm"), style)
    if confirm:
        return repairs.render_template(confirm, lead_line=None, slot=words)
    return f"You mentioned {words.rstrip('.,;:!? ')}. {confirm_phrase(framework, stage, thread_id)}".strip()


def reply_text(
    framework: Framework,
    walked: Walked,
    *,
    text: str,
    style: str,
    thread_id: uuid.UUID | str,
    known: dict | None = None,
) -> tuple[str, list[str]]:
    """The reply and the fallbacks it took. The reply that reaches a stage opens with that stage's letter
    line from the content, then Mani's own text; a reply that stays is Mani's text alone. A stage just reached is Mani's text for
    it, written for what [ctx] told the reply the stage is (a reading, or the part still missing),
    whenever that text asks something; the content's lines are the logged fallback when it asks nothing:
    its confirm line or a phrase for a reading, the question for the first missing part, the stage's
    ask. A stage left unjudged gets the stage's ask. A letter line the model wrote is dropped."""
    notes: list[str] = []
    intros = [i for s in content_stages(framework) if (i := (framework.stages.get(s) or {}).get("intro"))]
    own = repairs.without_sentences(text, lambda s: any(s.strip().startswith(i) for i in intros)).strip()
    if own != text.strip():
        notes.append("dropped a letter line")
    stage = walked.reached or (walked.phase if walked.phase in content_stages(framework) else None)
    # The letter line opens a stage, on the reply that reaches it, never on a reply that stays (muhammad,
    # 2026-10-17).
    letter = (framework.stages.get(walked.reached) or {}).get("intro") if walked.reached else None

    def lettered(body: str) -> str:
        return " ".join(part for part in (letter, body) if part)

    reached = walked.reached
    ask = repairs.styled(((framework.stages or {}).get(stage) or {}).get("ask"), style) or "" if stage else ""
    if reached is None:
        if not own and stage:
            notes.append("stay text empty")
            own = _part_question(framework, walked.entries, stage, style, known) or ask
        return lettered(own), notes
    entry = walked.entries.get(reached)
    if "?" in own and not walked.unjudged:
        return lettered(own), notes
    if is_stored(entry) and entry["step"] == READ:
        notes.append("confirm text unusable")
        body = _reading_fallback(framework, reached, entry, style, thread_id) or ask
    else:
        if not walked.unjudged:
            notes.append("gap asks nothing" if is_stored(entry) and entry["parts"] else "missing asks nothing")
        body = _part_question(framework, walked.entries, reached, style, known) or ask
    return lettered(body), notes


def reach_line(stage: str) -> str:
    """What the reply's text does for a stage the walk reaches, by what next_stage reports for it.
    What the stage is made of lives in the stage's parts in [ctx]."""
    return (
        f"your text follows what you report for {stage} in next_stage. Every required part answered: your "
        f"reading. {CONFIRM_ASK} A required part missing: ask only for the first one, from what they said and "
        f"next_stage_known, with next_stage_ask as its model; never name the letter or the stage."
    )


def next_line(framework: Framework, entries: dict[str, dict], phase: str) -> str:
    """What the reply's text is for, in each way their message can answer the stage in force, from
    the store before this turn. A question holds the stage until it has held it HELD_FOR_QUESTIONS
    times; past STALL_LIMIT replies without progress the text offers the choice to keep going, skip or
    stop, and nothing moves without their answer."""
    following = framework.phases[framework.phase_index(phase) + 1]
    if following in ENDING_STAGES:
        moved = "the questions end, and the body check-in is sent after your text: write one short sentence, no question."
    else:
        moved = f"the walk reaches {following}: {reach_line(following)}"
    entry = entries.get(phase) if is_stored(entries.get(phase)) else _fresh()
    step = entry["step"]
    reflect = ((framework.stages or {}).get(phase) or {}).get("reflect")
    asked = (
        " If asked, answer them plainly, then ask again."
        if entry.get("asked", 0) < HELD_FOR_QUESTIONS else ""
    )
    tries = entry.get("tries", 0)
    prefix = (
        f"They have stayed on {phase} for {tries} replies without getting further. Your text offers the choice: "
        "keep going with it, skip it (answer let_go), or stop the questions here (answer stopped). "
        if tries >= STALL_LIMIT else ""
    )
    if step == REFLECT:
        body = (
            "You asked what they take from this stage. Whatever they answer, even I don't know, the stage ends: "
            f"{moved}"
        )
    elif step == READ:
        ends = (
            f"your text asks one question about what they take from it ({reflect}), and the stage ends on "
            f"their answer" if reflect else moved
        )
        body = (
            "Your last reply gave your reading. If they go along with it, with more added or not, answer agreed: "
            f"{ends}. If they add to it or change it, report the words in stage_updates (corrected for words "
            "already stored, rejected for a part they say is wrong with no new words) and give your new reading "
            "of this stage only, or ask for the part now missing. If they only say they don't know or don't "
            "give anything, help them look as stage_when_stuck says, starting from stage_have, and ask again."
        )
    else:
        body = (
            "Report in stage_updates every part their message gives. When, with their message, every required "
            "part is filled, your text is your reading of this stage only, and the stage waits for their yes. "
            "While a required part is missing, your text says in a few words what stage_have already holds, then "
            "asks for the first missing part (stage_missing): the question in stage_last_question again in fresh "
            "words, narrower, or helped by stage_when_stuck when they don't know. When a part's stop_pushing "
            "applies, report it released with the closest thing they said instead of asking again."
        )
    return (
        f"{prefix}{body} If they correct an earlier stage, report it corrected: your text names the change in "
        "one sentence from their words and asks one question to be sure of it, and this stage waits. If let_go, "
        f"{moved} If stopped, say in one sentence that they can stop here; the two choices follow.{asked}"
    )


# What the walk does with a stage, for a person watching the conversation.
_ACTIONS = {
    "reading": "reading given, waiting for their yes",
    "reflecting": "asked what they take from it",
    "partial": "partly known, ask the next missing part",
    "done": "done",
    "missing": "missing, ask it",
    "not_reached": "not reached yet",
}


def _status(entry: object) -> str:
    """One word for where a stored stage is."""
    if not is_stored(entry):
        return "missing"
    return {READ: "reading", REFLECT: "reflecting", DONE: "done"}.get(entry["step"]) or (
        "partial" if entry["parts"] else "missing"
    )


def ledger_view(framework: Framework, entries: dict[str, dict], phase: str) -> list[dict]:
    """Every content stage as the store holds it after this turn. A stage with nothing stored is
    missing up to the one the walk is on, and not reached after it, as is anything stored after it
    that is not done, which the walk ignores until it reaches the stage."""
    at = framework.phase_index(phase)
    rows = []
    for stage in content_stages(framework):
        entry = entries.get(stage)
        ahead = framework.phase_index(stage) > at
        if ahead and not (is_stored(entry) and entry["step"] == DONE):
            entry = None
        status = "not_reached" if ahead and entry is None else _status(entry)
        known = "; ".join(p["said"] for p in entry["parts"].values() if p.get("said")) if is_stored(entry) else ""
        rows.append({
            "stage": stage,
            "title": ((framework.stages or {}).get(stage) or {}).get("title"),
            "status": status,
            "known": known or None,
            "action": _ACTIONS[status],
            "asking": stage == phase,
        })
    return rows
