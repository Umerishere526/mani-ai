# ABOUTME: Checks the route for a person who stays stuck: the offer after "Are you feeling stuck?" and ABCDE's stuck questions.
# ABOUTME: Fake frameworks, history and turn snapshots, so the context block and the candidate are tested with no model.

import datetime as dt
import uuid

from mani.chat import context
from mani.chat.orchestrator import stuck_offer_candidate
from mani.chat.techniques import Registry
from mani.db.threads import TurnContext
from mani.models.rows import Framework, Message, MessageRole, TechniqueOutcome, TechniqueState, Thread

NOW = dt.datetime(2026, 10, 5, tzinfo=dt.UTC)
USER = uuid.UUID("a0000000-0000-4000-8000-00000000000a")
THREAD = uuid.UUID("b0000000-0000-4000-8000-00000000000b")
TONES = ("supportive", "reflective", "direct")
STUCK_ASK = "What goes through your mind when you feel this?"
CHECK = "That is okay. Are you feeling stuck?"


def abcde(**activation) -> Framework:
    return Framework(
        id="abcde", name="ABCDE", summary="s", body="b",
        phases=["offering", "activate", "belief", "consequence", "somatic_checkin", "somatic_practice"],
        activation={"stuck_offer": True, **activation},
        stages={
            "offering": {
                "purpose": "Offer it once the event and belief are understood.",
                "ask": dict.fromkeys(TONES, "Would you like to look at it together?"),
                "stuck": {
                    "purpose": "Say it is hard to put into words right now.",
                    "boundaries": ["must not say \"stuck\" back to them"],
                },
            },
            "activate": {"purpose": "Find the event.", "ask": dict.fromkeys(TONES, "What happened?")},
            "belief": {
                "purpose": "Find the belief.",
                "ask": dict.fromkeys(TONES, "What did you tell yourself about it?"),
                "stuck": {"purpose": "Find what goes through their mind.", "ask": dict.fromkeys(TONES, STUCK_ASK)},
            },
            "consequence": {"purpose": "Find the effect.", "ask": dict.fromkeys(TONES, "How has that affected you?")},
        },
    )


def turn(technique: TechniqueState | None = None, message_count: int = 10) -> TurnContext:
    thread = Thread(id=THREAD, user_id=USER, message_count=message_count, created_at=NOW, last_message_at=NOW)
    return TurnContext(thread=thread, profile=None, technique=technique)


def said(role: MessageRole, content: str) -> Message:
    return Message(id=uuid.uuid4(), thread_id=THREAD, user_id=USER, role=role, content=content, created_at=NOW)


def history(*mani: str) -> list[Message]:
    """Their first message, then Mani's messages each followed by their answer, ending on Mani."""
    messages = [said(MessageRole.USER, "i am depressed")]
    for i, text in enumerate(mani):
        messages.append(said(MessageRole.MANI, text))
        if i < len(mani) - 1:
            messages.append(said(MessageRole.USER, "i dont know cant think"))
    return messages


def accepted(known: dict[str, str]) -> TechniqueState:
    return TechniqueState(
        thread_id=THREAD, framework_id="abcde", outcome=TechniqueOutcome.ACCEPTED,
        phase="offering", at_message_count=6, known=known,
    )


def test_a_framework_started_from_the_stuck_offer_asks_its_stuck_questions():
    stuck = context.build(turn(accepted({"stuck": "yes"})), framework=abcde(), framework_starting=True)
    plain = context.build(turn(accepted({})), framework=abcde(), framework_starting=True)

    assert f"step_ask: {STUCK_ASK}" in stuck.splitlines()
    assert "step_ask: What did you tell yourself about it?" in plain.splitlines()
    assert STUCK_ASK not in plain


def test_the_candidate_after_the_check_carries_its_stuck_branch_only_when_asked_for():
    with_branch = context.build(turn(), candidate=abcde(), stuck_candidate=True)
    without = context.build(turn(), candidate=abcde())

    line = next(l for l in with_branch.splitlines() if l.startswith("offer_when_stuck: "))
    assert "only if they answered yes" in line and "if they said no, offer nothing" in line
    assert "offer_when_stuck" not in without


def candidate(ctx: TurnContext, messages: list[Message], user_texts=("i dont know cant think",), **activation):
    return stuck_offer_candidate(ctx, Registry([abcde(**activation)]), messages, list(user_texts))


def test_the_candidate_comes_only_on_the_turn_right_after_the_check():
    assert candidate(turn(), history("What happened?", CHECK)).id == "abcde"
    assert candidate(turn(), history(CHECK, "What was in that message?")) is None


def test_the_candidate_waits_while_no_offer_is_allowed():
    # The check was the very first reply: this is their first message after it.
    assert candidate(turn(), [said(MessageRole.MANI, CHECK)]) is None
    running = TechniqueState(thread_id=THREAD, framework_id="abcde", outcome=TechniqueOutcome.ACCEPTED, phase="belief", at_message_count=4)
    assert candidate(turn(running), history("What happened?", CHECK)) is None
    declined = TechniqueState(thread_id=THREAD, framework_id="abcde", outcome=TechniqueOutcome.DECLINED, phase="offering", at_message_count=2)
    assert candidate(turn(declined, 20), history("What happened?", CHECK)).id == "abcde"


def test_the_candidate_is_never_shown_when_their_words_rule_it_out():
    assert candidate(turn(), history("What happened?", CHECK), ["he hit me"], never_offer_when_said=["hit me"]) is None
