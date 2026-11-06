# ABOUTME: The body check-in after a framework: which answer is valid at each step, and what the client's script sends.
# ABOUTME: Pure functions over a framework's somatic stages; the orchestrator applies the Step they return.

from __future__ import annotations

from dataclasses import dataclass, field

from mani.chat.repairs import (
    with_the_check_in,
    without_body_offer,
    without_last_question,
)

ASK, BODY, PRACTICE, EFFECT, CLOSING = (
    "somatic_ask", "somatic_body", "somatic_practice", "somatic_effect", "somatic_closing",
)
STAGES = (ASK, BODY, PRACTICE, EFFECT, CLOSING)
# Where the route is on the turn after its last step, when the run retires.
RETIRING = "retiring"

AREAS = ("chest", "stomach", "head", "jaw_face", "hands", "eyes", "feet", "toes", "arms")
# The answers a step accepts. Anywhere else a value is ignored, so a stray reading never moves the route.
_ANSWERS = {
    # Whether they would like to check in with their body at all (muhammad, 2026-10-27).
    ASK: {"yes", "no", "pain", "unclear"},
    BODY: {*AREAS, "other", "nearest", "none", "no", "pain", "unclear"},
    PRACTICE: {"better", "same", "worse", "pain", "unclear"},
    EFFECT: {"helped", "somewhat", "not_really", "unclear"},
    RETIRING: {"finish", "keep_chatting", PLAN := "plan"},
}
LIBRARY_ID = "library"
# The closing choice that ends the conversation: shown on the last step, so the turn after it may carry it.
FINISH_LABEL = "Finish for Now"


def closing_shown(history: list) -> bool:
    """Whether Mani's last reply offered the three closing choices, so this message answers them."""
    last = next((m for m in reversed(history) if m.role.value == "mani"), None)
    return bool(last and any(
        str(o.get("label", "")).lower() == FINISH_LABEL.lower() for o in (last.prompt_options or [])
    ))


@dataclass(frozen=True)
class Button:
    label: str
    library: bool = False


@dataclass(frozen=True)
class Step:
    """What a body answer does. `text` is None where the model's own words stand (asking where, offering the
    closest exercise, a clarifying question, Keep Chatting, Finish for Now). `phase` is None when the route has
    ended."""

    text: str | None
    buttons: list[Button] = field(default_factory=list)
    phase: str | None = None
    physical_response: str | None = None
    conversation_effect: str | None = None


def fits(value: str, at: str) -> bool:
    return value in _ANSWERS.get(at, ())


def _script(stages: dict, stage: str) -> dict:
    return (stages.get(stage) or {}).get("script") or {}


def _buttons(items: list[dict] | None) -> list[Button]:
    return [Button(label=i["label"], library=i["id"] == LIBRARY_ID) for i in items or []]


def ask(text: str, stages: dict) -> tuple[str, list[Button]]:
    """What follows the framework's last stage: Mani's own one-sentence reflection of their last answer, then the
    question whether they would like to check in with their body at all, with Yes and Not right now."""
    script = _script(stages, ASK)
    return with_the_check_in(text, script["text"]), _buttons(script["buttons"])


def close(text: str, stages: dict, *, plan: bool = False) -> tuple[str, list[Button]]:
    """What follows the framework's last stage while the body check-in is paused (muhammad, 2026-11-05): Mani's own
    close, without a body offer or a question of its own, and the three closing choices, with Plan Next Step first
    when something practical is still ahead of them (muhammad, 2026-11-06)."""
    script = _script(stages, CLOSING)
    buttons = (script.get("plan_buttons") or [] if plan else []) + script["buttons"]
    return without_last_question(without_body_offer(text)), _buttons(buttons)


def _opening(stages: dict) -> Step:
    """Step 1 once they said yes: the client's introduction, its general question and its five buttons (muhammad,
    2026-11-04: always the client's Step 1, never a question of ours before its buttons)."""
    script = _script(stages, BODY)
    return Step(script["text"], _buttons(script["buttons"]), BODY)


# The button sets whose labels a tap may carry at each step: (stage holding the set, key of the set).
_TAPS = {
    ASK: [(ASK, "buttons")],
    BODY: [(BODY, "buttons"), (BODY, "other_buttons"), (BODY, "nearest_buttons")],
    PRACTICE: [(PRACTICE, "buttons")],
    EFFECT: [(EFFECT, "buttons"), (BODY, "no_tension_buttons")],
    RETIRING: [(CLOSING, "plan_buttons"), (CLOSING, "buttons")],
}


def tapped_value(at: str, label: str, stages: dict) -> str | None:
    """The answer a tapped button means at this step, or None when the tap does not settle it (Yes to the
    closest exercise leaves the model to say which one it offered)."""
    wanted = label.strip().lower()
    for stage, key in _TAPS.get(at, ()):
        for item in _script(stages, stage).get(key) or []:
            if item["label"].lower() == wanted:
                return None if (key == "nearest_buttons" and item["id"] == "yes") else item["id"]
    return None


def _effect_step(stages: dict, lead: str, *, physical_response: str | None = None) -> Step:
    """Step 5: the question after `lead`, with its three buttons, and the effect answer to come."""
    script = _script(stages, EFFECT)
    text = f"{lead}\n\n{script['question']}" if lead else script["question"]
    return Step(text, _buttons(script["buttons"]), EFFECT, physical_response=physical_response)


def _stop(stages: dict) -> Step:
    """Pain, trouble breathing or feeling faint: the client's line, no exercise, and the route ends."""
    return Step(_script(stages, BODY)["pain"], [], CLOSING)


def step(at: str, value: str, stages: dict, *, physical_response: str | None = None) -> Step | None:
    """What the answer `value` does at step `at`, or None when it is not valid there."""
    if not fits(value, at):
        return None
    if at == ASK and value != "pain":
        if value == "yes":
            return _opening(stages)
        if value == "no":
            return _effect_step(stages, "")
        return Step(None, _buttons(_script(stages, ASK)["buttons"]), ASK)
    if value == "pain":
        return _stop(stages)
    body, practice, effect = (_script(stages, s) for s in (BODY, PRACTICE, EFFECT))
    if at == BODY:
        if value in AREAS:
            text = f"{practice['exercises'][value]}\n\n{practice['check']}"
            return Step(text, _buttons(practice["buttons"]), PRACTICE)
        if value == "other":
            return Step(None, _buttons(body["other_buttons"]), BODY)
        if value == "nearest":
            return Step(None, _buttons(body["nearest_buttons"]), BODY)
        if value == "none":
            return Step(body["no_tension"], _buttons(body["no_tension_buttons"]), EFFECT, physical_response="no_tension")
        if value == "no":
            return _effect_step(stages, "")
        return Step(None, _buttons(body["buttons"]), BODY)
    if at == PRACTICE:
        if value in ("better", "same", "worse"):
            return _effect_step(stages, practice["replies"][value], physical_response=value)
        return Step(None, _buttons(practice["buttons"]), PRACTICE)
    if at == EFFECT:
        if value == "unclear":
            kind = "no_tension_buttons" if physical_response == "no_tension" else "buttons"
            return Step(None, _buttons((body if kind == "no_tension_buttons" else effect)[kind]), EFFECT)
        replies = body["no_tension_replies"] if physical_response == "no_tension" else effect["replies"]
        closing = _script(stages, CLOSING)
        return Step(replies[value], _buttons(closing["buttons"]), CLOSING, conversation_effect=value)
    return Step(None, [], None)
