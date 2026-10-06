# ABOUTME: Why a drafted reply is asked for again once: a feeling or size they never gave, or an offer that does not match what the facts allow.
# ABOUTME: Pure checks on the draft, so each reason is a unit test; the orchestrator makes the one extra call.

from __future__ import annotations

import re
from collections.abc import Callable

from mani.chat import repairs, router
from mani.chat.context import STUCK_FIT_LABEL, panic_guidance, stuck_guidance
from mani.chat.techniques import STUCK_BRANCH, Registry, passed_over_stages
from mani.llm.schema import Reply
from mani.models.rows import Framework


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


# While pain may still be physical the offer is held (the prompt says so), so an offer that is
# due is not asked for then.
# Whole words, so "painful" (a feeling) is not read as pain in the body.
_PAIN = re.compile(r"\b(pain|hurts|hurting|ache|aching|injury|injured)\b")


def pain_mentioned(user_texts: list[str]) -> bool:
    return any(_PAIN.search(text.lower()) for text in user_texts)


def offers_the_pick(technique: str | None, fit: router.Fit | None) -> bool:
    """Whether an offer of `technique` is the framework the facts fully fit. Only that may be
    offered; a framework they only point to never is. A turn whose facts are not read (`fit`
    None) is judged by its timing alone."""
    return fit is None or technique == fit.pick


_NOT_ALLOWED = (
    "your draft offered a set of questions, which is not allowed yet: offer nothing and stay with "
    "what they just said"
)


def _named(framework: Framework) -> str:
    return f"{framework.name} (`{framework.id}`)"


def _offer_guidance(
    framework: Framework, style: str, facts: frozenset[str], *, stuck_route: bool = False,
) -> str:
    """The framework's own offering stage, so a redrafted offer draws on its authored wording.
    DBT STOP's panic branch when they are panicked with no action in view; ABCDE's stuck branch
    when it fits only because they are stuck and its first stages are passed over (spec 0009)."""
    offering = framework.stages.get("offering") or {}
    panic = offering.get("panic")
    if panic and "overwhelmed_now" in facts and "about_to_act" not in facts:
        return f"its offer: {panic_guidance(panic, style)}"
    stuck = offering.get(STUCK_BRANCH)
    if stuck and stuck_route and passed_over_stages(framework, dict.fromkeys(facts, "")):
        return f"its offer: {stuck_guidance(stuck, STUCK_FIT_LABEL)}"
    parts = [offering.get("purpose", "")]
    if offering.get("boundaries"):
        parts.append("; ".join(offering["boundaries"]))
    ask = (offering.get("ask") or {}).get(style)
    if ask:
        parts.append(f"ask: {ask}")
    return "its offer: " + ". ".join(p for p in parts if p)


def _offer_reason(
    technique: str,
    reply: Reply,
    user_texts: list[str],
    registry: Registry,
    *,
    fit: router.Fit | None,
    style: str,
    clear_ok: bool,
    earliest_ok: Callable[[str], bool],
    waiting: str | None,
    asked_about_waiting: bool,
) -> str | None:
    """The one reason a draft that offers cannot stand, in the order of spec 0005's AC-7. What
    rules out any offer now (a veto, the cooldown) comes before the facts, so an offer made while
    a decline cools down is never told to ask what is happening."""
    if technique == waiting:
        # Showing again the offer they typed past is no new offer; only its window applies.
        return None if asked_about_waiting or clear_ok else _NOT_ALLOWED
    if ruled_out(reply, user_texts, registry):
        return (
            f"your draft offered {registry.get(technique).name}, which does not fit what they "
            "have told you (see 'Never offer one when'); offer nothing and stay with what they said"
        )
    if not clear_ok:
        return _NOT_ALLOWED
    if offers_the_pick(technique, fit):
        if not earliest_ok(technique):
            return (
                f"your draft offered {registry.get(technique).name} too early: its fit depends on "
                "what they took it to mean, which they have not said yet; offer nothing and stay "
                "with what they said"
            )
        return None
    if fit.pick is not None:
        pick = registry.get(fit.pick)
        if earliest_ok(fit.pick):
            return (
                f"the facts you listed point to {_named(pick)}: offer that instead; "
                f"{_offer_guidance(pick, style, fit.facts, stuck_route=fit.stuck_route)}"
            )
        return _NOT_ALLOWED
    # Nothing fits: a framework they only point to is never offered, so ask for what it needs.
    missing = (
        f"ask about {router.FACTS[fit.missing]}" if fit.missing else "ask what is happening for them"
    )
    return (
        "nothing they have said fits a set of questions yet: offer nothing, and "
        f"{missing}, in their terms, never naming it"
    )


def _due_reason(
    registry: Registry,
    *,
    fit: router.Fit,
    style: str,
    clear_ok: bool,
    earliest_ok: Callable[[str], bool],
) -> str | None:
    """A draft that does not offer when an offer is due and the facts fully fit a framework. A
    framework they only point to is never asked for."""
    if fit.pick is not None and clear_ok and earliest_ok(fit.pick):
        pick = registry.get(fit.pick)
        return (
            f"you have talked for several replies and not offered: offer {_named(pick)}; "
            f"{_offer_guidance(pick, style, fit.facts, stuck_route=fit.stuck_route)}"
        )
    return None


def reasons(
    reply: Reply,
    user_texts: list[str],
    registry: Registry,
    *,
    fit: router.Fit | None = None,
    style: str = "supportive",
    clear_ok: bool = True,
    offer_due: bool = False,
    earliest_ok: Callable[[str], bool] = lambda _: True,
    waiting: str | None = None,
    asked_about_waiting: bool = False,
) -> list[str]:
    """What is wrong with the draft that only the model can fix, as lines for the model to read.
    Empty when the draft stands.

    `fit` is what the first draft's facts point to, None on a turn whose facts are not read.
    `waiting` is the framework of an offer they typed past, and `asked_about_waiting` whether
    their message asked about it.
    """
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
    stock = repairs.used_stock_phrases(reply.text)
    if stock:
        notes.append(
            f"your draft used {', '.join(repr(p) for p in stock)}; say it another way, "
            "in plain words, without that phrase"
        )

    technique = offered(reply, registry)
    if technique:
        reason = _offer_reason(
            technique, reply, user_texts, registry, fit=fit, style=style, clear_ok=clear_ok,
            earliest_ok=earliest_ok, waiting=waiting, asked_about_waiting=asked_about_waiting,
        )
    elif fit is not None and offer_due and (fit.stuck_route or not pain_mentioned(user_texts)):
        reason = _due_reason(
            registry, fit=fit, style=style, clear_ok=clear_ok, earliest_ok=earliest_ok,
        )
    else:
        reason = None
    if reason:
        notes.append(reason)
    return notes
