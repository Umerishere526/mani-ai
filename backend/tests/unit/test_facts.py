# ABOUTME: What one turn tells the model: the system prompt with the framework guide, and the facts block that says,
# ABOUTME: before the reply is written, what code would refuse, so the reply never offers what the app will not show.

import datetime as dt
import time
import uuid

from mani.chat.facts import facts, framework_guide, system_prompt
from mani.chat.safety import State
from mani.db.threads import TurnContext
from mani.models.rows import Prompt, Thread
from mani.prompts.cache import Config
from scripts.seed import PROMPTS_DIR, parse_prompt
from tests.unit.frameworks import REGISTRY, offered, running

NOW = dt.datetime(2026, 11, 17, tzinfo=dt.UTC)
MANI = parse_prompt(PROMPTS_DIR / "mani.md")
CONFIG = Config(
    prompts={"mani": Prompt(id=uuid.uuid4(), name="mani", content=MANI["content"])},
    registry=REGISTRY, loaded_at=time.monotonic(),
)


def ctx(safety: str = "clear") -> TurnContext:
    thread = Thread(id=uuid.uuid4(), user_id=uuid.uuid4(), created_at=NOW, last_message_at=NOW, safety=safety)
    return TurnContext(thread=thread, profile=None, technique=None)


def facts_for(context: TurnContext, **given) -> str:
    base = dict(record={}, style="supportive", running=None, open_offer=None, event=None, wants_title=False,
                return_check=None, answering_return=None, end_check_asked=False, holding=False, person_messages=5,
                state=State(context.thread.safety))
    return facts(context, CONFIG, **{**base, **given})


def test_no_offer_is_allowed_while_a_safety_worry_is_open():
    assert "You cannot offer a set of questions in this reply" in facts_for(ctx(safety="unsure"))


def test_an_offer_is_allowed_in_a_clear_conversation_with_nothing_open():
    assert "You cannot offer" not in facts_for(ctx())


def test_no_offer_is_allowed_while_one_is_open_or_after_a_framework_was_finished():
    assert "You cannot offer" in facts_for(ctx(), open_offer=offered("abcde"))
    assert "You cannot offer" in facts_for(ctx(), record={"finished": ["abcde"]})


def test_a_running_framework_names_the_next_stage_line_and_the_one_step_rule():
    text = facts_for(ctx(), style="directive", running=running("abcde", "activate"))
    assert '"B is for Belief."' in text and "Never move further than that." in text
    assert "You cannot offer" in text


def test_a_held_turn_never_invites_a_move_a_start_or_an_offer_that_code_would_refuse():
    """A turn held for safety changes no framework state, so its facts never tell the model it may: Mani would say
    the next letter's line while the stored stage stays where it was."""
    moving = facts_for(ctx(safety="unsure"), running=running("abcde", "activate"), holding=True)
    assert "B is for Belief" not in moving and "Stay on this stage" in moving
    starting = facts_for(ctx(safety="unsure"), open_offer=offered("abcde"), holding=True)
    assert "A clear yes in their words starts it" not in starting
    owed = facts_for(ctx(), holding=True)
    assert "You cannot offer" in owed, "a clear thread still owes the question about a pause"


def test_the_notes_from_the_last_turn_are_handed_back():
    assert "Your notes from your last turn: boss, pushover" in facts_for(ctx(), record={"notes": "boss, pushover"})


def test_the_people_and_events_kept_are_handed_back_with_their_relation_and_when():
    record = {"people": [{"called": "Sam", "relation": "unsaid", "told": "stopped calling"}],
              "events": [{"what": "Thanksgiving alone this Thursday", "when": "upcoming"}]}
    text = facts_for(ctx(), record=record)
    assert "Sam (unsaid): stopped calling" in text and "[upcoming] Thanksgiving alone this Thursday" in text
    assert "people they spoke of" not in facts_for(ctx()) and "[upcoming]" not in facts_for(ctx())


def test_the_open_chat_is_told_each_question_asked_and_what_it_was_for():
    record = {"questions": [{"q": "What does a normal week look like?", "intent": "situation"},
                            {"q": "", "intent": "none"},
                            {"q": "What comes up when you picture saying no?", "intent": "feeling"}]}
    text = facts_for(ctx(), record=record)
    assert ('[situation] "What does a normal week look like?"; [feeling] "What comes up when you picture saying no?"'
            in text) and "ended on a question" not in text
    assert "[situation]" not in facts_for(ctx(), record=record, running=running("abcde", "activate"))


def test_three_replies_in_a_row_that_asked_tell_the_next_to_give_something_instead():
    asked = {"q": "Why?", "intent": "feeling"}
    assert "Your last 3 replies each ended on a question" in facts_for(ctx(), record={"questions": [asked] * 3})
    assert "ended on a question" not in facts_for(ctx(), record={"questions": [asked, {"q": "", "intent": "none"}, asked]})


def test_a_settled_answer_to_the_check_after_a_framework_leads_to_how_they_feel():
    """The final review, 2026-11-18: the line said to close the set, while code opens the feelings check."""
    told = facts_for(ctx(), end_check_asked=True)
    assert "ask how they feel now" in told and "close the set now" not in told


def test_the_guide_lists_every_stage_line_of_every_active_framework():
    guide = framework_guide(REGISTRY)
    for line in ("A is for Activating Event.", "E is for Effective New Belief.", "Step 1 is Identify the Thought."):
        assert line in guide


def test_the_guide_says_when_never_to_offer_each_framework():
    """The lines that protect the person (abuse, a fact that is never reframed, an OCD loop) are the one part of a
    framework the model must know before it offers, not after."""
    guide = framework_guide(REGISTRY)
    assert "Never offer it when:" in guide
    assert "In OCD this checking is the compulsion" in guide
    assert "The event itself is never questioned or reinterpreted as harmless" in guide


def test_the_system_prompt_is_mani_then_the_guide_and_the_summary_only_when_due():
    prompt = system_prompt(CONFIG, ctx(), summary_due=False)
    assert prompt.startswith(MANI["content"][:200]) and "A is for Activating Event." in prompt


def test_the_open_offer_line_says_which_step_is_showing():
    """At the lead-in, code adds the five steps after the reply, so a yes does not start the set yet; after the steps,
    a clear yes starts it and a clear no declines it."""
    lead_in = facts_for(ctx(), open_offer=offered("abcde"))
    assert "five steps follow your reply" in lead_in and "starts it" not in lead_in
    steps = facts_for(ctx(), open_offer=offered("abcde", "steps"))
    assert "A clear yes in their words starts it" in steps and "action to stop" in steps
    assert "from the whole story to one moment" in steps


def test_the_last_stage_asks_how_they_feel_and_the_check_in_forces_no_next_step():
    last = facts_for(ctx(), running=running("abcde", "effective"))
    assert "ask how they feel now" in last and "set action to finish" in last
    check_in = facts_for(ctx(), running=running("abcde", "feelings_check"))
    assert "how they feel" in check_in and "force no question" in check_in and "is for" not in check_in


def test_a_held_feelings_check_is_about_their_safety_and_promises_no_close():
    """The final review, 2026-11-18: held for safety, the check's line still said to ask nothing and that code closes."""
    held = facts_for(ctx(safety="unsure"), running=running("abcde", "feelings_check"), holding=True)
    assert "ask nothing" not in held and "code closes the set" not in held and "safety" in held
    assert "say nothing about the set or a next step" in held


def test_no_offer_is_allowed_before_their_third_message():
    assert "You cannot offer" in facts_for(ctx(), person_messages=2)
    assert "You cannot offer" not in facts_for(ctx(), person_messages=3)
