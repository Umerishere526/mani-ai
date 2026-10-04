# ABOUTME: Why a drafted reply is asked for again once: a feeling or size they never gave, an offer too early, not allowed yet, due and missing, or ruled out.
# ABOUTME: Pure checks on the draft, so each reason is a unit test; the orchestrator makes the one extra call.

from __future__ import annotations

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


def reasons(
    reply: Reply,
    user_texts: list[str],
    registry: Registry,
    *,
    offer_not_allowed: bool,
    closest_fit_due: bool = False,
    earliest_wait: bool = False,
) -> list[str]:
    """What is wrong with the draft that only the model can fix, as lines for the model to read.
    Empty when the draft stands."""
    notes: list[str] = []

    said = " ".join(user_texts)
    unwanted = [
        *repairs.introduced_feelings(reply.text, said),
        *repairs.introduced_size(reply.text, said),
    ]
    if unwanted:
        notes.append(
            f"your draft used {', '.join(unwanted)}, which they have not said; "
            "use their words for it, or leave it out"
        )

    technique = offered(reply, registry)
    if technique and earliest_wait:
        framework = registry.get(technique)
        name = framework.name if framework else technique
        notes.append(
            f"your draft offered {name} too early: its fit depends on what they took it to mean, "
            "which they have not said yet; offer nothing and stay with what they said"
        )
    elif technique and offer_not_allowed:
        notes.append(
            "your draft offered a set of questions, which is not allowed yet for a fit that is "
            "not clear; if you are confident which set fits, set offer_fit to clear, otherwise "
            "offer nothing and stay with what they just said"
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
            "'Never offer one when'); offer nothing and stay with what they said"
        )
    return notes
