# ABOUTME: Why a drafted reply is asked for again once: a feeling they never named, an offer too early, an offer ruled out.
# ABOUTME: Pure checks on the draft, so each reason is a unit test; the orchestrator makes the one extra call.

from __future__ import annotations

import re

from mani.chat import repairs, router
from mani.chat.techniques import Registry
from mani.llm.schema import Reply


def offered(reply: Reply, registry: Registry) -> str | None:
    """The framework a draft offers, if it carries an offer button for one that exists. An id the
    registry does not know is repairs.apply's to remove, not worth another call."""
    return next(
        (p.technique for p in reply.prompts or [] if p.technique and registry.get(p.technique)),
        None,
    )


def ruled_out(reply: Reply, user_texts: list[str], registry: Registry) -> str | None:
    """The framework a draft offers when what the person has said rules it out: the phrases a
    framework file lists under `never_offer_when_said` (early grief for Behavioral Activation).
    A prompt rule alone did not hold, so this is checked in code."""
    technique = offered(reply, registry)
    activation = registry.activations.get(technique) if technique else None
    if activation and router.vetoes(activation, user_texts):
        return technique
    return None


# Stock empathy that could be said to anyone (client meeting, 2026-10-02: "every answer was: it
# sounds like"; the specification: "avoids repetitive reassurance"). Not used at all
# (muhammad, 2026-10-05). Earlier in the list wins, so the note names the phrase as written.
STOCK_PHRASES = (
    "that sounds", "it sounds like", "sounds like you", "i hear you", "i hear that", "i can hear",
    "it seems like", "it feels like",
    "that must be", "it makes sense", "that makes sense", "makes sense that",
    "it's okay to feel", "it is okay to feel", "thank you for sharing", "i'm here for you",
    "i am here for you", "it is understandable", "it's understandable", "sounds very",
    "sounds really", "sounds so", "sounds hard", "sounds difficult", "sounds tough", "sounds rough",
    "sounds painful",
)


# Guidance of Mani's own: breathing, grounding, "focus on…". Not given outside a framework, not
# even in panic (muhammad, 2026-10-05); practices come from a practice stage or the Library.
_INSTRUCTION = re.compile(
    r"\b(focus on (your|the|being)\b|take (a|some) (deep |slow )?breaths?\b|breathe (in|out|slowly|deeply)\b"
    r"|slow (down )?your breath|ground yourself|feet on the floor|count to \w+|5-4-3-2-1"
    r"|try to (relax|calm|breathe|ground|focus)|just focus\b"
    r"|(?:^|[.!?]\s+)(?:(?:please|just|now)\s+)*(?:breathe|keep breathing)\b)",
    re.IGNORECASE,
)


def instruction(reply: Reply) -> str | None:
    """The first piece of guidance of Mani's own in the draft, if any."""
    match = _INSTRUCTION.search(reply.text)
    return match.group(0) if match else None


def stock_phrase(reply: Reply) -> str | None:
    """The first stock phrase the draft uses, if any."""
    draft = reply.text.lower().replace("\u2019", "'")
    return next((p for p in STOCK_PHRASES if p in draft), None)


_QUESTION = re.compile(r"[^.!?\n]*\?")
REPEAT_OVERLAP = 0.7


def _last_question_words(text: str) -> set[str]:
    questions = _QUESTION.findall(text)
    return set(re.findall(r"[a-z']{4,}", questions[-1].lower())) if questions else set()


def repeats(reply: Reply, last_mani_text: str | None) -> bool:
    """Whether the draft's closing question is, by its words, the question Mani asked last turn.
    A person who answers a question and gets it back unchanged is stuck, however it is reworded."""
    now, before = _last_question_words(reply.text), _last_question_words(last_mani_text or "")
    return bool(now and before and len(now & before) / min(len(now), len(before)) >= REPEAT_OVERLAP)


def reasons(
    reply: Reply,
    user_texts: list[str],
    registry: Registry,
    *,
    offer_not_allowed: bool,
    earliest_wait: bool = False,
    last_mani_text: str | None = None,
    framework_running: bool = False,
) -> list[str]:
    """What is wrong with the draft that only the model can fix, as lines for the model to read.
    Empty when the draft stands."""
    notes: list[str] = []

    unwanted = repairs.introduced_feelings(reply.text, " ".join(user_texts))
    if unwanted:
        notes.append(
            f"your draft used {', '.join(unwanted)}, which they have not said; "
            "name no feeling they have not named"
        )

    told = None if framework_running else instruction(reply)
    if told:
        notes.append(
            f'your draft gives an instruction of your own ("{told}"); give no instructions, '
            "exercises or techniques: stay with what they said and ask one simple question"
        )

    stock = stock_phrase(reply)
    if stock:
        notes.append(
            f'your draft says "{stock}", stock empathy that could be said to anyone; leave it '
            "out and answer them directly, about what they said, in plain words"
        )

    technique = offered(reply, registry)
    if not technique and repeats(reply, last_mani_text):
        notes.append(
            "your draft asks the question you asked last turn, with the same choices; answer "
            "what they just said first (a yes or a question of theirs counts), then move on: "
            "if they asked you to choose, offer one small step as a draft they can accept or change"
        )
    if technique and earliest_wait:
        framework = registry.get(technique)
        name = framework.name if framework else technique
        notes.append(
            f"your draft offered {name} too early: its fit depends on what they took it to mean, "
            "which they have not said yet; offer nothing and ask one question about what it "
            "meant to them, in their words"
        )
    elif technique and offer_not_allowed:
        notes.append(
            "your draft offered a set of questions, which is not allowed yet for a fit that is "
            "not clear; if you are confident which set fits, set offer_fit to clear, otherwise "
            "offer nothing and reply to what they just said"
        )
    elif technique and ruled_out(reply, user_texts, registry):
        framework = registry.get(technique)
        name = framework.name if framework else technique
        notes.append(
            f"your draft offered {name}, which does not fit what they have told you (see "
            "'Never offer one when'); offer nothing and reply to what they just said"
        )
    elif technique and "?" in repairs.without_permission_question(reply.text):
        # Left as it is, the repair drops the offer's buttons so the reply asks one thing.
        notes.append(
            "your draft offers and also asks a question of its own; an offer ends on your part "
            "with no question (asking whether they want to try is added for you), so either "
            "drop your question and keep the offer, or keep the question and offer nothing"
        )
    return notes
