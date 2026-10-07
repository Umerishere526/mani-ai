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


# While pain may still be physical the offer is held (the prompt says so), so a closest fit that
# is due is not forced then.
_PAIN = ("pain", "hurts", "hurting", "ache", "aching", "injury", "injured")


def pain_mentioned(user_texts: list[str]) -> bool:
    return any(word in text.lower() for text in user_texts for word in _PAIN)


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
    closest_fit_due: bool = False,
    needs_question: bool = False,
    earliest_wait: bool = False,
    last_mani_text: str | None = None,
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

    technique = offered(reply, registry)
    if not technique and repeats(reply, last_mani_text):
        notes.append(
            "your draft asks the question you asked last turn, with the same choices; answer "
            "what they just said first (a yes or a question of theirs counts), then move on: "
            "if they asked you to choose, offer one small step as a draft they can accept or change"
        )
    if needs_question and not technique and "?" not in reply.text:
        notes.append(
            "your draft asks no question; end with one question that follows what they just said "
            "and moves toward which set of questions fits them, in their words"
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
            "offer nothing and ask one question that follows what they just said and moves "
            "toward which set fits them"
        )
    elif not technique and closest_fit_due and reply.heading_toward and not pain_mentioned(user_texts):
        notes.append(
            "you have talked for several replies and not offered: offer the nearest set of "
            "questions now, with offer_fit closest unless you are confident, and say it is the "
            "nearest and that they can keep talking instead"
        )
    elif technique and ruled_out(reply, user_texts, registry):
        framework = registry.get(technique)
        name = framework.name if framework else technique
        notes.append(
            f"your draft offered {name}, which does not fit what they have told you (see "
            "'Never offer one when'); offer nothing and ask one question instead"
        )
    return notes
