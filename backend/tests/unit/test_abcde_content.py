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


def test_abcde_and_thought_reframe_are_the_frameworks_seeded():
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
        # The client's review, 2026-10-29: the offer names the belief they confirmed, and never suggests Mani has
        # already decided it is wrong.
        assert "the belief that <the core belief they confirmed" in text
        assert "really true" not in text and "whether they're true" not in text
    assert "what supports it, and whether there's a more balanced way to see it." in offer["directive"]
    assert "look at what's supporting that belief, and find a more balanced way to think about it." in offer["supportive"]


def test_the_clients_offer_wording_reaches_the_person_but_never_the_framework_index(abcde):
    """Code renders the offer, Keep chatting and Tell me more from these templates, so the model
    is given none of them to copy (spec 0003)."""
    from mani.prompts import composer

    index = composer.framework_index(Registry([as_framework(abcde)]))
    for key in ("offer", "keep_chatting", "explain"):
        for text in abcde["stages"]["offering"][key].values():
            fixed = max(re.split(r"<[^>]*>", text), key=len).strip()
            assert fixed[:40] not in index, key


def test_the_offer_does_not_list_the_steps(abcde):
    """muhammad, 2026-10-22: the offer is the framework line and the permission question; the five steps are
    told only when they ask Tell me more."""
    assert "steps" not in abcde["stages"]["offering"]


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
        for name in ("voice", "moments")
    }
    system = composer.compose_moment(
        Config(prompts=prompts, registry=registry, loaded_at=time.monotonic()), None, offered=["abcde"],
    )
    now = dt.datetime.now(dt.UTC)
    thread = Thread(id=uuid.uuid4(), user_id=uuid.uuid4(), message_count=11, conversation_style="supportive",
                    created_at=now, last_message_at=now)
    offered = TechniqueState(thread_id=thread.id, framework_id="abcde", outcome=TechniqueOutcome.OFFERED,
                             phase="offering", at_message_count=11)
    block = context.build(TurnContext(thread=thread, profile=None, technique=offered), framework=framework,
                          history=[], offer_waiting=True, yes_framework=framework)
    shape = reply_for(Moment.OFFER_OPEN, slots=repairs.slots_for(registry, "supportive", "abcde"))

    # The voice is the prefix every turn shares, the chat's included, and is cached once for all of them
    # (muhammad, 2026-10-27); what this turn adds after it is held to the old figure.
    voice = len(prompts["voice"].content) + 2
    total = len(system.text) - voice + len(block) + len(json.dumps(shape.model_json_schema()))
    assert system.text.startswith(prompts["voice"].content)
    assert total < CHARACTERS_BEFORE_STRUCTURED_FIELDS


def test_the_stages_that_look_at_the_belief_or_thought_carry_the_stack_in_both_frameworks():
    """Lolly, 2026-10-22: the stack must reach C, D and E. A framework says which of its stages carry it."""
    carrying = {
        name: sorted(stage for stage, body in parse_framework(FRAMEWORKS_DIR / f"{name}.md")["stages"].items()
                     if body.get("carries_case"))
        for name in ("abcde", "thought_reframe")
    }
    assert carrying == {
        "abcde": ["consequence", "dispute", "effective"],
        "thought_reframe": ["alternative", "feels_true", "painful", "replacement"],
    }


def test_the_stages_keep_clinical_words_and_judgements_out_of_what_mani_says(abcde):
    """Lolly, 2026-10-22: the language read as artificial. The offer never names the method, B never calls a
    belief irrational or distorted, C never judges a feeling, and A counts only what happened as the event."""
    stages = abcde["stages"]
    assert any("clinical terms such as REBT, CBT" in rule for rule in stages["offering"]["boundaries"])
    assert any("must not call the belief irrational" in rule for rule in stages["belief"]["boundaries"])
    assert "must not judge the feeling or behaviour as wrong or unhealthy" in stages["consequence"]["boundaries"]
    assert "rather than as their interpretation of it" in stages["activate"]["ready_when"]
    assert "commitment for next time counts as the path" in stages["effective"]["ready_when"]
