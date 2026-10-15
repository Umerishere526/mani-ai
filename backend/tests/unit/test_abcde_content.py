# ABOUTME: Checks the one seeded framework, ABCDE, carries what the client's ABCDE document asks for.
# ABOUTME: Read from the framework file itself, the same structure that is seeded, so no database is needed.

import re

import pytest

from mani.chat import context, repairs
from mani.chat.techniques import Registry
from mani.models.rows import Framework
from scripts.seed import FRAMEWORKS_DIR, parse_framework

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


def test_only_abcde_is_seeded():
    assert [p.stem for p in FRAMEWORKS_DIR.glob("*.md")] == ["abcde"]


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


def test_the_event_stage_carries_the_clients_confirm_and_missing_lines_in_each_style(abcde):
    """The document's three cases for A: an event said back and confirmed, and the event asked for
    with their own word for the feeling (spec 0004, AC-4 and AC-6)."""
    activate = abcde["stages"]["activate"]
    assert activate["confirm"]["supportive"] == (
        "You mentioned <the event, in their words>. Is that what started these feelings?"
    )
    assert activate["missing"]["supportive"] == "What's been happening that's left you feeling so <their word for it>?"
    for key in ("confirm", "missing"):
        assert set(activate[key]) == set(STYLES)
        assert all(line.endswith("?") and "<" in line for line in activate[key].values())


def test_each_letter_opens_with_the_clients_intro_line(abcde):
    """Spec 0004, AC-1 and AC-7: the document introduces each letter by its name as it is reached,
    and a stage said back closes with one of four short phrases."""
    intros = {stage: abcde["stages"][stage]["intro"] for stage in abcde["phases"][1:]}
    assert intros == {
        "activate": "A is for Activating Event.", "belief": "B is for Belief.",
        "consequence": "C is for Consequences.", "dispute": "D is for Dispute.",
        "effective": "E is for Effective New Belief.",
    }
    assert abcde["confirm_phrases"] == [
        "Is that right?", "Do we have this right?", "Did I get that right?", "Does that sound right?",
    ]


def test_the_offer_follows_the_clients_pattern_with_a_slot_for_their_situation(abcde):
    offer = abcde["stages"]["offering"]["offer"]
    assert set(offer) == set(STYLES)
    for text in offer.values():
        assert "There's a framework called ABCDE" in text
        assert "<" in text and ">" in text and "?" not in text, "a slot to fill, and no question of its own"
        # Spec 0005, AC-6: the feeling they named fills it; their worry only when they named none.
        assert "<their feeling from understanding" in text and "only when they named no feeling>" in text
    assert "helps you identify the thoughts behind <" in offer["directive"]
    assert "question whether they're true, and replace them with more realistic ones." in offer["directive"]


def test_the_clients_offer_wording_reaches_the_person_but_never_the_framework_index(abcde):
    """Code renders the offer, Keep chatting and Tell me more from these templates, so the model
    is given none of them to copy (spec 0003)."""
    from mani.prompts import composer

    index = composer.framework_index(Registry([as_framework(abcde)]))
    for key in ("offer", "keep_chatting", "explain"):
        for text in abcde["stages"]["offering"][key].values():
            fixed = max(re.split(r"<[^>]*>", text), key=len).strip()
            assert fixed[:40] not in index, key
    assert abcde["stages"]["offering"]["steps"].splitlines()[0] not in index


def test_the_offer_lists_the_five_steps_by_letter_and_the_clients_name(abcde):
    lines = abcde["stages"]["offering"]["steps"].splitlines()
    names = ["Activating Event", "Belief", "Consequences", "Dispute", "Effective New Belief"]
    assert [line.split(".")[0] for line in lines] == [f"- {l}: {n}" for l, n in zip("ABCDE", names)]


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
