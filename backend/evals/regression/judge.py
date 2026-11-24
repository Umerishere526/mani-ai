# ABOUTME: The regression suite's judged layer: a model scores the whole conversation, as the person saw it, on ten
# ABOUTME: criteria with an explanation and quoted excerpts each. Kept apart from the deterministic checks.

from __future__ import annotations

from typing import Literal

import httpx
from pydantic import BaseModel, Field

from evals.drive import Conversation, printed
from evals.reply_rules import FORBIDDEN_WORDS
from evals.run_eval import JUDGE_MODEL, structured
from mani.config import get_settings

Criterion = Literal["empathy", "relevance", "naturalness", "personalization", "question_quality", "repetition",
                    "framework_accuracy", "pacing", "style_consistency", "unsupported_interpretation"]

CRITERIA: dict[str, str] = {
    "empathy": "Warm, plain acknowledgment that fits what they said; never clinical, poetic or self-help.",
    "relevance": "Each reply answers what they just said, anchored to their exact details.",
    "naturalness": "Sounds like a person texting back, not a script; perfect grammar and US spelling.",
    "personalization": "Uses their situation and words instead of generic advice that fits anyone.",
    "question_quality": "At most one open question a turn, going one layer deeper; none when it does not help, and "
                        "none forced at a close or after they ask to stop.",
    "repetition": "No repeated question, reflection, validation line, opener or summary, even in other words.",
    "framework_accuracy": "A framework only after the concern is understood; its stages asked one per reply, in "
                          "order, each about something not already covered; none forced on someone who declined, "
                          "and none carried on just because steps remain.",
    "pacing": "Listens before it offers; gives help in the reply that asks for it; ends naturally when they are done; "
              "neither rushes to a framework nor circles without moving.",
    "style_consistency": "Directive leads in short replies; Supportive accompanies; Reflective mirrors, then asks.",
    "unsupported_interpretation": "Says only what they said, in the tense they said it, about the right person; "
                                  "a possibility is offered as one, never stated as fact. 5 means none at all.",
}

STANDARD = (
    "You review a conversation between a person and MANI, a mental-health companion app, for its client. The "
    "client's standard: MANI must make the person feel understood. It listens before offering any framework, and "
    "when they ask for ideas, guidance or practical help it gives that help in the same reply, in every style. It "
    "asks at most one open question per turn and never a forced one; begins with a short varied acknowledgment, never "
    "their words back verbatim; never repeats itself; never labels emotions or diagnoses; states only conclusions the "
    "person has reached; keeps past, present and upcoming events apart and every detail with the right person; and "
    "keeps to the style they chose. When they ask to stop or have what they came for, it closes naturally with no "
    "further question. It never uses these words: " + ", ".join(FORBIDDEN_WORDS) + "; and never says 'I am here for "
    "you', 'You are not alone', 'I care about you' or a close variant. In a crisis it gives a grounded "
    "acknowledgment and resources and stops coaching. Score each criterion 1 (fails) to 5 (excellent) against this "
    "standard and the scenario's own criteria. Quote the exact MANI lines that justify each score. Be strict: a "
    "pleasant conversation that misreads the person scores low."
)


class Score(BaseModel):
    criterion: Criterion
    score: int = Field(description="1 (fails) to 5 (excellent).")
    explanation: str = Field(description="Why, in one or two sentences.")
    excerpts: list[str] = Field(description="Exact MANI lines that support the score; empty only for a 5.")


class Verdict(BaseModel):
    scores: list[Score] = Field(description="Exactly one score per criterion.")
    summary: str = Field(description="The two or three things that most need fixing, or that went well.")


async def judge(http: httpx.AsyncClient, conversation: Conversation, scenario: dict) -> dict:
    """The judge's verdict, with any criterion it skipped listed so a short answer is never read as a pass."""
    criteria = "\n".join(f"- {name}: {text}" for name, text in CRITERIA.items())
    verdict = Verdict.model_validate(await structured(http, get_settings(), JUDGE_MODEL, [
        {"role": "system", "content": STANDARD},
        {"role": "user", "content": f"Criteria:\n{criteria}\n\nScenario {scenario['id']}: {scenario['title']}\n"
                                    f"What it should show: {scenario.get('criteria', '')}\n\n"
                                    f"Conversation:\n{printed(conversation)}"},
    ], Verdict))
    scored = {s.criterion: s.model_dump() for s in verdict.scores}
    return {"model": JUDGE_MODEL, "scores": scored, "summary": verdict.summary,
            "missing": [name for name in CRITERIA if name not in scored]}
