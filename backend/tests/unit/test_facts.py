# ABOUTME: What one turn tells the model: the system prompt with the framework guide, and the facts block that says,
# ABOUTME: before the reply is written, what code would refuse, so the reply never offers what the app will not show.

import datetime as dt
import time
import uuid

from mani.chat.facts import facts, framework_guide, system_prompt
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
                return_check=None, answering_return=None, end_check_asked=False, holding=False)
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


def test_the_last_stage_says_to_close_and_finish():
    assert "close and finish" in facts_for(ctx(), running=running("abcde", "effective"))


def test_the_notes_from_the_last_turn_are_handed_back():
    assert "Your notes from your last turn: boss, pushover" in facts_for(ctx(), record={"notes": "boss, pushover"})


def test_the_check_after_a_framework_says_to_close_once_settled():
    assert "If their answer settles it, close the set now" in facts_for(ctx(), end_check_asked=True)


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
