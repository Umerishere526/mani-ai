# ABOUTME: Checks the one seeded framework, ABCDE, carries what the client's ABCDE document asks for.
# ABOUTME: Read from the framework file itself, the same structure that is seeded, so no database is needed.

import copy
import re

import pytest

from mani.chat import context, repairs
from mani.chat.techniques import Registry
from mani.models.rows import Framework
from scripts.seed import FRAMEWORKS_DIR, missing_for_activation, parse_framework

STYLES = ("directive", "supportive", "reflective")


@pytest.fixture(scope="module")
def abcde() -> dict:
    return parse_framework(FRAMEWORKS_DIR / "abcde.md")


def as_framework(parsed: dict) -> Framework:
    return Framework(
        id=parsed["id"], name=parsed["name"], summary=parsed["summary"], body="b",
        phases=parsed["phases"], activation=parsed["activation"], stages=parsed["stages"],
        confirm_phrases=parsed["confirm_phrases"],
    )


def test_abcde_and_thought_reframe_are_the_active_frameworks():
    assert sorted(p.stem for p in FRAMEWORKS_DIR.glob("*.md")) == ["abcde", "thought_reframe"]


def test_abcde_runs_a_to_e_and_the_body_check_in_follows(abcde):
    assert abcde["phases"] == ["offering", "activate", "belief", "consequence", "dispute", "effective"]
    framework = as_framework(abcde)
    assert framework.closing == "effective", "the last letter is asked, never skipped"


def test_every_letter_has_a_title_for_the_ledger_and_asks_in_all_three_styles(abcde):
    titles = {"activate": "A: Activating Event", "belief": "B: Belief", "consequence": "C: Consequences",
              "dispute": "D: Dispute", "effective": "E: Effective New Belief"}
    for stage, title in titles.items():
        assert abcde["stages"][stage]["title"] == title
        assert set(abcde["stages"][stage]["ask"]) == set(STYLES)


def test_tell_me_more_is_the_five_steps_in_the_selected_style(abcde):
    registry = Registry([as_framework(abcde)])
    for style in STYLES:
        text = repairs.explanation(registry.get("abcde"), style)
        assert text.count("\n") >= 6 and "A: Activating Event" in text and "E: Effective New Belief" in text
        assert text.endswith("Would you like to try it?")


def test_the_event_stage_carries_the_clients_confirm_line_and_asks_with_their_own_word_for_the_feeling(abcde):
    """The document's cases for A: an event said back and confirmed, and the event asked for with their
    own word for the feeling, now the question of the stage's event part (spec 0007)."""
    activate = abcde["stages"]["activate"]
    assert activate["confirm"]["supportive"] == (
        "You mentioned <the event, in their words>. Is that what started these feelings?"
    )
    event = activate["parts"][0]
    assert event["from"] == "understanding.event"
    assert event["ask"]["supportive"] == "What's been happening that's left you feeling so <understanding.feeling>?"
    assert set(activate["confirm"]) == set(event["ask"]) == set(STYLES)
    assert all(line.endswith("?") and "<" in line for line in event["ask"].values())


def test_each_letter_has_its_line_and_the_confirm_phrases_are_the_four(abcde):
    """Spec 0007: every reply inside a stage opens with its letter line, from the content."""
    assert {stage: abcde["stages"][stage]["intro"] for stage in abcde["phases"][1:]} == {
        "activate": "A is for Activating Event.", "belief": "B is for Belief.",
        "consequence": "C is for Consequences.", "dispute": "D is for Dispute.",
        "effective": "E is for Effective New Belief.",
    }
    assert abcde["confirm_phrases"] == [
        "Is that right?", "Do we have this right?", "Did I get that right?", "Does that sound right?",
    ]


def test_every_stage_declares_the_parts_it_needs_and_when_to_stop_asking_for_each(abcde):
    """Spec 0007: code reads parts (id, required, from); the words say what is enough and when to stop."""
    needs = {stage: {p["id"]: p.get("required", True) for p in abcde["stages"][stage]["parts"]}
             for stage in abcde["phases"][1:]}
    assert needs == {
        "activate": {"event": True},
        "belief": {"belief": True, "belief_type": False},
        "consequence": {"felt": True, "did": True},
        "dispute": {"evidence": True, "logic": True, "usefulness": False},
        "effective": {"new_belief": True, "next_step": False},
    }
    every = [p for stage in abcde["phases"][1:] for p in abcde["stages"][stage]["parts"]]
    assert len({p["id"] for p in every}) == len(every)
    assert all(p.get("stop_pushing") for p in every if p.get("required", True))
    assert [stage for stage in abcde["phases"][1:] if abcde["stages"][stage].get("reflect")] == [
        "belief", "consequence", "dispute", "effective",
    ], "A has no reflection: the event needs none"


def test_the_clients_offer_wording_reaches_the_person_but_never_the_framework_index(abcde):
    """Code renders the offer, Keep chatting and Tell me more from these templates, so the model
    is given none of them to copy (spec 0003)."""
    from mani.prompts import composer

    index = composer.framework_index(Registry([as_framework(abcde)]))
    for key in ("offer", "keep_chatting", "explain"):
        for text in abcde["stages"]["offering"][key].values():
            fixed = max(re.split(r"<[^>]*>", text), key=len).strip()
            assert fixed[:40] not in index, key


CLIENT_QUESTIONS = {
    "belief": {
        "directive": "What did you start telling yourself about what was happening?",
        "supportive": "Sometimes when things are difficult, we start drawing conclusions about ourselves or what's happening. What were you telling yourself about the situation?",
        "reflective": "When that happened, what did you begin believing about yourself or the situation?",
    },
    "consequence": {
        "directive": "How did that thought affect how you felt or what you did?",
        "supportive": "Our thoughts can affect how we feel and respond. How did that belief affect how you felt or what you did?",
        "reflective": "When you believed that thought, how did it influence your feelings or the way you responded?",
    },
    "dispute": {
        "directive": "What makes you believe this is true, and what makes you question it?",
        "supportive": "Let's look at that belief together. What makes you think it's true? Is there anything that suggests otherwise?",
        "reflective": "As you think about that belief, what seems to support it, and what might suggest a different explanation?",
    },
    "effective": {
        "directive": "What's a more realistic and helpful way to think about what's happening?",
        "supportive": "Now that you've looked at both sides, what's a more realistic and helpful way to think about what's happening?",
        "reflective": "After considering both sides, what do you think would be a more accurate and helpful way to understand what happened?",
    },
}


def test_every_stage_asks_the_clients_own_question_in_each_style(abcde):
    for stage, asks in CLIENT_QUESTIONS.items():
        assert abcde["stages"][stage]["ask"] == asks, stage


# Spec 0003, AC-9: the supportive ABCDE offer_open turn, measured before the change as the composed
# system prompt plus [ctx] plus the JSON schema of the one Reply then sent (2026-10-12).
CHARACTERS_BEFORE_STRUCTURED_FIELDS = 35752


def test_an_open_offer_turn_costs_less_prompt_than_before_the_structured_fields(abcde):
    import datetime as dt
    import json
    import time
    import uuid

    from mani.db.threads import TurnContext
    from mani.llm.schema import Moment, reply_for
    from mani.models.rows import Prompt, TechniqueOutcome, TechniqueState, Thread
    from mani.prompts import composer
    from mani.prompts.cache import Config
    from scripts.seed import PROMPTS_DIR, load_somatic_stages, parse_prompt

    somatic = load_somatic_stages()
    framework = as_framework({**abcde, "phases": abcde["phases"] + list(somatic),
                              "stages": {**abcde["stages"], **somatic}})
    registry = Registry([framework])
    prompts = {
        name: Prompt(id=uuid.uuid4(), name=name, content=parse_prompt(PROMPTS_DIR / f"{name}.md")["content"])
        for name in ("mani_base", "response_format", "style_supportive")
    }
    system = composer.compose(
        Config(prompts=prompts, registry=registry, loaded_at=time.monotonic()), None,
        style="supportive", offered=["abcde"],
    )
    now = dt.datetime.now(dt.UTC)
    thread = Thread(id=uuid.uuid4(), user_id=uuid.uuid4(), message_count=11, conversation_style="supportive",
                    created_at=now, last_message_at=now)
    offered = TechniqueState(thread_id=thread.id, framework_id="abcde", outcome=TechniqueOutcome.OFFERED,
                             phase="offering", at_message_count=11)
    block = context.build(TurnContext(thread=thread, profile=None, technique=offered), framework=framework,
                          history=[], offer_waiting=True, yes_framework=framework)
    shape = reply_for(Moment.OFFER_OPEN, slots=repairs.slots_for(registry, "supportive", "abcde"))

    total = len(system.text) + len(block) + len(json.dumps(shape.model_json_schema()))
    assert total < CHARACTERS_BEFORE_STRUCTURED_FIELDS


def test_a_framework_whose_parts_the_walk_cannot_read_is_refused_at_seed_with_the_path_named(abcde):
    """Spec 0007: code reads parts, so a framework with none, a repeated id, a part question that refers to
    nothing, or a part bound to no understanding key fails at seed, not in a live chat."""
    assert missing_for_activation(abcde) == []
    broken = copy.deepcopy(abcde)
    del broken["stages"]["activate"]["parts"]
    broken["stages"]["belief"]["parts"][1]["id"] = "belief"
    broken["stages"]["consequence"]["parts"][0]["from"] = "understanding.mood"
    broken["stages"]["consequence"]["parts"][1]["ask"] = "And when you <thought>, what do you do?"
    del broken["stages"]["effective"]["intro"]
    assert missing_for_activation(broken) == [
        "stages.activate.parts",
        "stages.effective.intro",
        "parts.belief listed twice",
        "stages.consequence.parts.felt.from understanding.mood names no understanding key",
        "stages.consequence.parts.did.ask refers to <thought>, which is no part or understanding key",
    ]
