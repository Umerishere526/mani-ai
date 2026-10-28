# ABOUTME: Mani's own conversation before a framework: the client's cadence in its prompt, and when its reply
# ABOUTME: is stored as the check that leads to an offer.

from __future__ import annotations

import datetime as dt
import pathlib
import time
import uuid

from mani.chat import converse, understanding
from mani.chat.techniques import Registry
from mani.db.threads import TurnContext
from mani.llm.schema import ConversationReply, FeelingEntry, PictureUpdate
from mani.models.rows import Prompt, Thread
from mani.prompts import cache, composer
from mani.prompts.cache import Config
from scripts.seed import parse_prompt

THREAD = uuid.uuid4()
USER = uuid.uuid4()
NOW = dt.datetime(2026, 10, 26, tzinfo=dt.UTC)
PROMPTS = pathlib.Path(__file__).parents[2] / "content/prompts"
# The reply to their fifth message is written at message 11: the earliest a check may come.
FIFTH = 11


def ctx(message_count: int, heart: str | None = None) -> TurnContext:
    return TurnContext(
        thread=Thread(
            id=THREAD, user_id=USER, message_count=message_count, created_at=NOW, last_message_at=NOW,
            understanding={"heart": heart} if heart else {},
        ),
        profile=None,
        technique=None,
    )


def reply(**fields) -> ConversationReply:
    return ConversationReply(**({"text": "That sounds difficult. What happened between you?"} | fields))


def test_a_check_comes_only_after_the_heart_of_it_was_said_back_and_agreed():
    """muhammad, 2026-10-26: one live run went from exploring straight to a check at message 6. The conflict is
    agreed in an exchange of its own first, and never before their fifth message."""
    assert not converse.check_allowed(ctx(FIFTH))
    assert not converse.check_allowed(ctx(FIFTH, "exploring"))
    assert not converse.check_allowed(ctx(FIFTH - 2, "core_named"))
    assert converse.check_allowed(ctx(FIFTH, "core_named"))
    assert converse.check_allowed(ctx(FIFTH, "ready"))
    assert converse.check_allowed(ctx(FIFTH, "conflict_named")), "a record from before 2026-10-28 still counts"


def test_a_reply_is_stored_as_the_check_only_when_allowed_flagged_and_it_says_the_core():
    """muhammad, 2026-10-28: the check is about the core alone; what they want and what is in the way are not asked."""
    core = {"core": "One slip feels like proof that you can't change, and underneath the guilt there is shame."}
    assert converse.checked(reply(checking=True, **core), allowed=True)
    assert not converse.checked(reply(checking=True, **core), allowed=False)
    assert not converse.checked(reply(checking=False, **core), allowed=True)
    assert not converse.checked(reply(checking=True, core=" "), allowed=True)
    assert not {"conflict", "want", "in_the_way"} & set(ConversationReply.model_fields)


def test_a_stored_check_is_ready_and_its_core_becomes_the_case_with_the_feeling_underneath():
    from mani.llm.schema import CoreEntry

    checked = reply(
        heart="core_named", checking=True, core="One slip feels like proof that you can't change",
        picture=PictureUpdate(
            feelings=[FeelingEntry(feeling="guilty")],
            core=CoreEntry(belief="you're not capable of change", feeling="shame", about="self"),
        ),
    )
    after = converse.understood_after({"feeling": "frustrated", "heart": "conflict_named"}, checked, check_written=True)
    assert after["heart"] == understanding.READY
    assert after["feeling"] == "frustrated, guilty", "the feeling underneath is Mani's reading, kept apart"
    assert after["case"] == "One slip feels like proof that you can't change. Underneath it you feel shame."
    said_already = reply(checking=True, core="One slip feels like proof you can't change, and underneath it, shame.")
    assert converse.case(said_already, after["picture"]) == said_already.core, "the feeling is not said twice"
    exploring = converse.understood_after({}, reply(heart="exploring"), check_written=False)
    assert exploring == {"heart": "exploring"}


def test_the_note_says_whether_this_reply_may_check_and_names_the_style():
    assert "Do not check" in converse.note("supportive", allowed=False, due=False, wants_title=False)
    assert "Supportive" in converse.note("supportive", allowed=False, due=False, wants_title=False)
    assert "You may check" in converse.note("directive", allowed=True, due=False, wants_title=False)
    assert "this reply checks" in converse.note("directive", allowed=True, due=True, wants_title=True)
    assert "title" in converse.note("directive", allowed=True, due=True, wants_title=True)
    assert "this reply checks" not in converse.note("directive", allowed=False, due=True, wants_title=False)


def test_the_reply_is_written_before_anything_is_judged_about_it():
    """The voice comes first, and nothing in the reply asks for a second question or a reasoning pass."""
    fields = list(ConversationReply.model_fields)
    assert fields[0] == "text"
    assert not {"reasoning", "options", "style"} & set(fields)
    assert fields.index("text") < fields.index("picture")


def test_the_note_carries_the_picture_of_them():
    """muhammad, 2026-10-27: the chat and the framework read the same picture each turn."""
    seen = {"picture": {"focus": "your brother in hospital", "beliefs": [{"belief": "work will stop you", "kind": "thought"}]}}
    note = converse.note("directive", allowed=False, due=False, wants_title=False, understood=seen)
    assert "Your picture of them before their message: focus: your brother in hospital; " \
           "what they tell themselves: work will stop you." in note


def test_the_conversation_prompt_is_the_clients_cadence_and_her_two_conversations():
    """Lolly, 2026-10-26: "I wish mani sounded this way." Her instruction, the order the two ChatGPT
    conversations follow, and both conversations, with the announced questions taken out and her friend's
    43 years kept right."""
    content = "\n".join(parse_prompt(PROMPTS / f"{name}.md")["content"] for name in ("voice", "conversation"))
    assert "directive, concise and clear, no fluff, but warm and never robotic" in content
    assert "Can you tell me what happened between you?" in content
    assert "never a reason to guess" in content
    assert "What's happened that's left you so frustrated and upset?" in content
    assert "If you know he won't change, what is keeping you from making the decision to leave?" in content
    assert "If you miss her this deeply, what's stopping you from reaching out to her?" in content
    for announced in ("Can I ask you something", "Let me ask you something", "I'm curious about something"):
        assert announced not in content
    assert "Twenty three" not in content and "23 years" not in content
    assert "conversation" in cache.REQUIRED_PROMPTS


def test_the_conversation_prompt_is_one_cached_prefix_with_the_person_after_it():
    named = [
        Prompt(id=uuid.uuid4(), name=name, content=body, model_parameters={}, routing={})
        for name, body in (("voice", "VOICE"), ("conversation", "CONVERSATION"), ("framework", "FRAMEWORK"),
                           ("title_generation", "TITLE"))
    ]
    config = Config(prompts={p.name: p for p in named}, registry=Registry([]), loaded_at=time.monotonic())
    built = composer.compose_conversation(config, None, should_generate_title=True)
    assert [name for name, _ in built.layers] == ["voice", "conversation", "title_generation"]
    assert built.text.startswith("VOICE")
    # muhammad, 2026-10-27: a framework's stages speak in the same voice, so it is the same cached prefix.
    staged = composer.compose_framework(config, None)
    assert [name for name, _ in staged.layers] == ["voice", "framework"]


def test_a_framework_turn_is_a_conversation_the_stage_only_gives_the_direction():
    """muhammad, 2026-10-27: frameworks felt mechanical. A new feeling or thought is talked about on the stage in force,
    an earlier stage it changes is said in one short line, the model question is a direction, and another situation
    is a choice between staying and switching."""
    framework = parse_prompt(PROMPTS / "framework.md")["content"]
    for rule in (
        "The stage waits for as many turns as that takes",
        "Say so in one short line",
        "The model question is a direction, never a line to read out",
        "Do you want to stay with the one we selected?",
        "What they say is really happening is never a thought to question",
        "Options only when they are unsure",
    ):
        assert rule in framework, rule


def test_code_picks_the_help_move_from_the_kind_of_problem_and_the_style():
    """muhammad, 2026-10-27: the help-move table. A real situation is helped in the conversation, a thought may go to
    a set of questions, both is a choice, and a risk to someone else always comes first."""
    situation = {"problem_type": "situation"}
    assert "concrete, sensible next steps" in converse.help_move("directive", situation)
    assert "keep talking it through or look at what might help" in converse.help_move("supportive", situation)
    assert "a pattern or a connection" in converse.help_move("reflective", situation)
    assert "offer to look at it together" in converse.help_move("directive", {"problem_type": "belief"})
    assert "which they want to start with" in converse.help_move("directive", {"problem_type": "both"})
    assert converse.help_move("supportive", {}) == converse.UNSURE_MOVE
    risky = {**situation, "risks": [{"risk": "children left unsupervised", "to": "others"}]}
    assert converse.help_move("supportive", risky).startswith(
        "First name the risk to children left unsupervised plainly"
    )


def test_the_conversation_turns_to_helping_when_it_stops_moving_or_they_ask():
    """The 2026-10-27 review: heard but not helped. Mani turns when they ask for help, show frustration, add nothing
    new, or answer in a few words three times running; once turned it stays, until another situation comes in."""
    quiet = {"picture": {"shift": "nothing_new", "quiet": 1}}
    moving = {"picture": {"shift": "adds", "quiet": 0}}
    assert converse.turned({}, reply(asked_for_help=True), moving, [])
    assert converse.turned({}, reply(frustrated=True), moving, [])
    assert converse.turned({}, reply(), quiet, [])
    assert converse.turned({}, reply(), moving, ["fine", "i guess", "yes"])
    assert not converse.turned({}, reply(), moving, ["yes", "I don't know"]), "two short answers are often answers"
    assert not converse.turned({}, reply(), moving, ["my boss keeps taking credit for my work", "yes", "no"])
    assert converse.turned({converse.HELPING: True}, reply(), moving, [])
    new_issue = {"picture": {"shift": "new_issue", "quiet": 0}}
    assert not converse.turned({converse.HELPING: True}, reply(asked_for_help=True), new_issue, [])


def test_turning_is_kept_on_the_record_and_another_situation_starts_understanding_again():
    from mani.llm.schema import PictureUpdate

    helped = converse.understood_after({}, reply(asked_for_help=True), check_written=False)
    assert helped[converse.HELPING] is True
    moved_on = converse.understood_after(
        {**helped, "heart": "ready"}, reply(picture=PictureUpdate(focus="your sister's loans", shift="new_issue")),
        check_written=False,
    )
    assert converse.HELPING not in moved_on and "heart" not in moved_on


def test_the_note_lists_what_was_asked_and_what_is_unknown_and_while_helping_the_move():
    """Never the same question twice; ask for the first gap; once helping, every reply gives something."""
    from mani.models.rows import Message, MessageRole

    asked = [Message(id=uuid.uuid4(), thread_id=THREAD, user_id=USER, role=MessageRole.MANI, created_at=NOW,
                     content="That sounds hard. What happened between you? Was it the words or the silence?")]
    assert converse.asked_before(asked) == ["What happened between you?", "Was it the words or the silence?"]

    exploring = converse.note("directive", allowed=False, due=False, wants_title=False,
                              understood={"picture": {"situations": ["she stopped calling"]}},
                              asked=converse.asked_before(asked))
    assert "Questions you already asked, never to ask again in any words: What happened between you? | " in exploring
    assert "Still unknown: how it is for them, the core: " in exploring
    assert exploring.index("the core") < exploring.index("what they want"), "the core is looked for before the want"
    assert "You are helping now" not in exploring

    situation = {converse.HELPING: True, "picture": {"problem_type": "situation"}}
    helping = converse.note("directive", allowed=True, due=False, wants_title=False, understood=situation)
    assert "You are helping now" in helping and "concrete, sensible next steps" in helping
    assert "Still unknown" not in helping
    assert "this reply checks your understanding" not in helping, "a real situation is helped, not checked toward a set"
    thought = {converse.HELPING: True, "picture": {"problem_type": "belief"}}
    assert "this reply checks your understanding" in converse.note(
        "directive", allowed=True, due=False, wants_title=False, understood=thought,
    ), "for a thought, the check is the way to the set of questions"


def test_the_three_styles_are_three_ways_of_moving_and_help_is_allowed_once_turned():
    """The 2026-10-27 review: the styles differed in tone only, and Mani heard but did not help."""
    voice = parse_prompt(PROMPTS / "voice.md")["content"]
    chat = parse_prompt(PROMPTS / "conversation.md")["content"]
    assert "turns to helping soonest" in voice, "Directive"
    assert "Each reply opens with genuine acknowledgment of how hard this is" in voice, "Supportive"
    assert "names a pattern or a connection in what they said that they may not have seen" in voice, "Reflective"
    assert "never ask them to choose again" in voice
    assert "Ideas they choose from are help; instructions are not." in voice
    assert "No advice, tips or plans" not in voice
    assert "every reply gives them something" in chat
    assert "name it plainly and treat it as something to act on" in chat


def test_the_conversation_prompt_goes_down_to_the_core_and_checks_it_alone():
    """muhammad, 2026-10-28: Mani named fear of failing as the core when the thoughts led to "I'm not capable", and
    shame under the guilt was never named. The prompt follows the thoughts down, names the core and the feeling
    underneath as an invitation, talks about it, and checks it alone."""
    chat = parse_prompt(PROMPTS / "conversation.md")["content"]
    assert "# Finding the core" in chat
    assert "What it says about them" in chat
    assert "guilt about a slip on shame about who they are" in chat
    assert "The core is not what happens because of it" in chat
    assert "your reply checks the core alone" in chat
    assert "what they are torn between, what they want and what is stopping them" not in chat
    assert "conflict_named" not in chat


def test_a_belief_about_themselves_is_never_reported_as_a_feeling():
    from mani.llm.schema import FeelingEntry

    assert "\"incapable\"" in FeelingEntry.model_fields["feeling"].description
