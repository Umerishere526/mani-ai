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
from mani.llm.schema import BeliefEntry, ConversationReply, FeelingEntry, PictureUpdate
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


def test_mani_reads_the_person_before_it_writes_the_reply():
    """muhammad, 2026-10-29 (approach A): written first, the text followed the facts of the last message, and the
    picture judged after it never shaped what Mani said. The whole reading comes first, then the facts, the heart,
    what this turn calls for, and the text last of those; nothing asks for a second question or a reasoning pass."""
    fields = list(ConversationReply.model_fields)
    assert fields[: fields.index("text")] == [
        "reading", "picture", "heart", "need", "needs_info", "info_needed", "shape", "window", "insight", "insight_from",
        "link", "move", "plan",
    ]
    assert not {"reasoning", "options", "style"} & set(fields)


def test_the_reading_is_required_of_the_model_but_a_reply_without_it_still_reads():
    from openai.lib._pydantic import to_strict_json_schema

    sent = to_strict_json_schema(ConversationReply)
    assert sent["required"][0] == "reading" and "anyOf" not in sent["properties"]["reading"]
    assert set(sent["$defs"]["Reading"]["required"]) >= {"underneath", "wants", "needs", "desire", "core", "problem_type"}
    assert reply().reading is None, "code never pays a second call for a missing reading"


def test_the_reading_is_laid_over_the_picture_and_unclear_keeps_what_was_held():
    from mani.llm.schema import Reading, UnderneathEntry

    def reading(**fields):
        return Reading(**({
            "underneath": [], "wants": "unclear", "needs": "unclear", "desire": "unclear", "core": "unclear",
            "core_from": "unclear", "core_feeling": "unclear", "core_about": "self", "tension": "none",
            "problem_type": "unclear",
        } | fields))

    first = converse.understood_after({}, reply(reading=reading(
        underneath=[UnderneathEntry(feeling="loneliness", rests_on="we barely have meaningful conversations")],
        wants="meaningful conversations", needs="to feel close and chosen", desire="a relationship that feels alive",
        core="you might be settling for something that isn't fulfilling", core_from="I wonder if I'm settling",
        core_feeling="fear", core_about="situation", tension="you love them, and you're not sure you're happy",
        problem_type="situation",
    ), picture=PictureUpdate(beliefs=[BeliefEntry(belief="relationships become less exciting", kind="thought")])),
        check_written=False)
    seen = first["picture"]
    assert seen["core"] == {
        "belief": "you might be settling for something that isn't fulfilling", "about": "situation", "feeling": "fear",
        "tension": "you love them, and you're not sure you're happy", "rests_on": "I wonder if I'm settling",
    }
    assert (seen["wants"], seen["needs"], seen["desire"]) == (
        "meaningful conversations", "to feel close and chosen", "a relationship that feels alive")
    assert seen["problem_type"] == "both", "what they tell themselves is never a situation alone"
    kept = converse.understood_after(first, reply(reading=reading()), check_written=False)["picture"]
    assert kept["core"] == seen["core"] and kept["wants"] == seen["wants"], "unclear never writes over a reading"


def test_the_note_names_what_the_reading_lacks_and_what_is_already_known():
    held = {"picture": {
        "situations": ["you both got busy with work"], "in_the_way": "work",
        "beliefs": [{"belief": "you may be settling", "kind": "thought"}],
    }}
    sent = converse.note("directive", allowed=False, due=False, wants_title=False, understood=held,
                         their_count=3, latest="work")
    assert "Your picture holds what they tell themselves (you may be settling) but no core" in sent
    assert "Still empty in your reading: what they want, the need underneath, what they long for" in sent
    assert "Already known, never ask for it again: what is in the way: work." in sent
    assert "Their answer only repeats what they already told you" in sent
    early = converse.note("directive", allowed=False, due=False, wants_title=False, understood=held,
                          their_count=1, latest="I've been with my partner for five years")
    assert "but no core" not in early and "Still empty" not in early and "only repeats" not in early
    named = {"picture": {"core": {"belief": "you might be settling", "about": "situation"}}, "heart": "exploring"}
    assert "a core you have not said to them yet" in converse.note(
        "directive", allowed=False, due=False, wants_title=False, understood=named, their_count=3)


def test_the_note_carries_the_picture_of_them():
    """muhammad, 2026-10-27: the chat and the framework read the same picture each turn."""
    seen = {"picture": {"focus": "your brother in hospital", "beliefs": [{"belief": "work will stop you", "kind": "thought"}]}}
    note = converse.note("directive", allowed=False, due=False, wants_title=False, understood=seen)
    assert "Your picture of them before their message: focus: your brother in hospital; " \
           "what they tell themselves: work will stop you." in note


def test_mani_works_like_lollys_role_played_session():
    """muhammad, 2026-10-29: Mani runs the chat the way a therapist runs a session, neutral and empathetic, with
    therapist's questions that move it forward, ending on a step they choose. Lolly's role-played session is the
    example the model follows; her two ChatGPT conversations are kept only as her tone note, because the model
    copied their mirror-then-question shape over every rule against it."""
    voice = parse_prompt(PROMPTS / "voice.md")["content"]
    assert "Run the conversation the way a good therapist runs a session" in voice
    assert "directive, concise and clear, no fluff, but warm and never robotic" in voice
    assert "Never call this therapy, counselling or a session" in voice
    assert "What you can tell, you never ask." in voice
    for lolly in ("You: Why are you sad?", "You: What would you like to happen with your parents?",
                  "Have they ever been there for you in the way you want?",
                  "You: Do you think that just by wanting it, you're going to get it?",
                  "You: Have you tried anything to change the wanting into asking?",
                  "You could text: Hey mom and dad", "Is that a maybe as a yes, or a maybe as a no?"):
        assert lolly in voice, lolly
    for chatgpt in ("If you know he won't change", "If you miss her this deeply", "Each reply is your mirror"):
        assert chatgpt not in voice, chatgpt
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


def test_the_chat_never_carries_a_help_move_and_a_risk_to_others_still_comes_first():
    """The client's test, 2026-10-29: the framework is the solution, so the chat has no help moves. A risk to
    someone else is still named and acted on first."""
    assert not hasattr(converse, "HELP_MOVES") and not hasattr(converse, "help_move")
    risky = {"picture": {"risks": [{"risk": "children left unsupervised", "to": "others"}]}}
    sent = converse.note("supportive", allowed=False, due=False, wants_title=False, understood=risky)
    assert "First name the risk to children left unsupervised plainly" in sent
    assert converse.risk_first({}) is None


def test_the_conversation_presses_toward_the_framework_when_it_stops_moving_or_they_ask():
    """The 2026-10-27 review, then the client's test 2026-10-29: when they ask what to do, show frustration, add
    nothing new, or answer in a few words three times running, Mani presses toward the framework, never into
    solving it in the chat; it stays so until another situation comes in."""
    quiet = {"picture": {"shift": "nothing_new", "quiet": converse.QUIET_TO_HELP}}
    once = {"picture": {"shift": "nothing_new", "quiet": 1}}
    answered = {"picture": {"shift": "answered", "quiet": 0}}
    moving = {"picture": {"shift": "adds", "quiet": 0}}
    assert converse.toward({}, reply(asked_for_help=True), moving, [])
    assert converse.toward({}, reply(frustrated=True), moving, [])
    assert converse.toward({}, reply(), quiet, [])
    assert not converse.toward({}, reply(), once, []), "one message with nothing new is not enough (2026-10-29)"
    assert not converse.toward({}, reply(), answered, ["comfortable"]), "a short answer to Mani's question is an answer"
    assert converse.toward({}, reply(), moving, ["fine", "i guess", "yes"])
    assert not converse.toward({}, reply(), moving, ["yes", "I don't know"]), "two short answers are often answers"
    assert not converse.toward({}, reply(), moving, ["my boss keeps taking credit for my work", "yes", "no"])
    assert converse.toward({converse.TOWARD: True}, reply(), moving, [])
    new_issue = {"picture": {"shift": "new_issue", "quiet": 0}}
    assert not converse.toward({converse.TOWARD: True}, reply(asked_for_help=True), new_issue, [])


def test_pressing_is_kept_on_the_record_and_another_situation_starts_understanding_again():
    from mani.llm.schema import PictureUpdate

    pressed = converse.understood_after({"helping": True}, reply(asked_for_help=True), check_written=False)
    assert pressed[converse.TOWARD] is True and "helping" not in pressed, "an old helping record is dropped"
    moved_on = converse.understood_after(
        {**pressed, "heart": "ready"}, reply(picture=PictureUpdate(focus="your sister's loans", shift="new_issue")),
        check_written=False,
    )
    assert converse.TOWARD not in moved_on and "heart" not in moved_on


def test_the_note_lists_what_was_asked_and_what_is_unknown_and_when_pressing_the_way_in():
    """Never the same question twice; ask for the first gap; once helping, every reply gives something."""
    from mani.models.rows import Message, MessageRole

    asked = [Message(id=uuid.uuid4(), thread_id=THREAD, user_id=USER, role=MessageRole.MANI, created_at=NOW,
                     content="That sounds hard. What happened between you? Was it the words or the silence?")]
    assert converse.asked_before(asked) == ["What happened between you?", "Was it the words or the silence?"]

    exploring = converse.note("directive", allowed=False, due=False, wants_title=False,
                              understood={"picture": {"situations": ["she stopped calling"]}},
                              asked=converse.asked_before(asked))
    assert "Questions you already asked, never to ask again in any words: What happened between you? | " in exploring
    assert "Still unknown" not in exploring, "no list of questions to work through (2026-10-29)"
    assert "What happened is not known yet: let them tell it." in converse.note(
        "directive", allowed=False, due=False, wants_title=False, understood={})

    pressing = {converse.TOWARD: True, "picture": {"problem_type": "situation"}}
    sent = converse.note("directive", allowed=True, due=False, wants_title=False, understood=pressing)
    assert "Do not solve it in the chat" in sent and "at most one small idea" in sent
    assert "this reply checks your understanding" in sent, "pressing toward the framework, the check is the way in"
    assert "Do not solve it in the chat" not in exploring


def test_the_three_styles_are_three_ways_of_moving_and_help_is_allowed_once_turned():
    """The 2026-10-27 review: the styles differed in tone only, and Mani heard but did not help."""
    voice = parse_prompt(PROMPTS / "voice.md")["content"]
    chat = parse_prompt(PROMPTS / "conversation.md")["content"]
    assert "turns to suggestions soonest" in voice, "Directive"
    assert "genuine acknowledgment of how hard this is" in voice, "Supportive"
    assert "names a pattern or a connection in what they said that they may not have seen" in voice, "Reflective"
    assert "Suggestions they choose from are help; instructions are not." in voice
    assert "No advice, tips or plans" not in voice
    assert "every reply gives them something" in chat
    assert "name it plainly and treat it as something to act on" in chat


def test_the_conversation_prompt_goes_down_to_the_core_and_checks_it_alone():
    """muhammad, 2026-10-28: Mani named fear of failing as the core when the thoughts led to "I'm not capable", and
    shame under the guilt was never named. The prompt follows the thoughts down, names the core and the feeling
    underneath as an invitation, talks about it, and checks it alone."""
    chat = parse_prompt(PROMPTS / "conversation.md")["content"]
    assert "# Finding the core" in chat
    assert "you never ask them for it" in chat
    assert "guilt about a slip on shame about who they are" in chat
    assert "The core is not what happens because of it" in chat
    assert "your insight into the core" in chat
    assert "what they are torn between, what they want and what is stopping them" not in chat
    assert "conflict_named" not in chat


def test_a_belief_about_themselves_is_never_reported_as_a_feeling():
    from mani.llm.schema import FeelingEntry

    assert "\"incapable\"" in FeelingEntry.model_fields["feeling"].description


def test_the_conversation_prompt_holds_the_five_principles_and_nothing_pushes_a_question():
    """muhammad, 2026-10-29, on feat/fix-chat-flow: infer and never ask what can be inferred, three questions every
    turn; internal and external dependencies; action-oriented suggestions; a progression from chat to framework;
    simple questions only when needed."""
    chat = parse_prompt(PROMPTS / "conversation.md")["content"]
    voice = parse_prompt(PROMPTS / "voice.md")["content"]
    for rule in ("1. What does this person need from you right now?",
                 "2. Do you have something useful to give, or do you really need more information?",
                 "3. Is there an insight that what they said already supports?",
                 "Whatever you can infer from what they said, you already have",
                 "when it is a suggestion, end by handing it back to them to choose", "Keep a plan of where this conversation is heading",
                 "fill picture's dependencies", "inside them", "outside them", "aim at what is in their control"):
        assert rule in chat, rule
    assert "with the words to use where that helps" in chat and "give them the words" in voice
    for gone in ("Follow their story in order", "What it says about them", "your question goes to the first"):
        assert gone not in chat, gone
    assert parse_prompt(PROMPTS / "voice.md")["model_parameters"]["reasoning_effort"] == "medium"


def test_the_three_answers_and_the_plan_are_kept_and_the_note_carries_the_plan():
    told = {"picture": {"situations": ["he never reaches out first"]}}
    after = converse.understood_after(told, reply(
        need="to make sense of why he keeps doing this", needs_info=False,
        insight="his promises keep the friendship going without him changing anything", insight_from="he says he will",
        plan="He has asked twice and nothing changed; next, what he needs to say clearly.",
    ), check_written=False)
    assert after["plan"] == "He has asked twice and nothing changed; next, what he needs to say clearly."
    assert after["thinking"] == {"need": "to make sense of why he keeps doing this", "needs_info": False,
                                 "insight": "his promises keep the friendship going without him changing anything",
                                 "from": "he says he will"}
    note = converse.note("directive", allowed=False, due=False, wants_title=False, understood=after)
    assert "Your plan from your last reply: He has asked twice and nothing changed" in note


def test_mani_follows_lollys_cadence_and_checks_by_her_barometer():
    """The meeting, 2026-10-29: acknowledge, open the window to the situation and the challenge, insight, ask; never
    summarise or show the notes; the check is the insight and an offer to work through it with a framework; "I don't
    know" and two feelings get Lolly's questions; Directive is about the challenge and what they can control."""
    voice = parse_prompt(PROMPTS / "voice.md")["content"]
    chat = parse_prompt(PROMPTS / "conversation.md")["content"]
    moments = parse_prompt(PROMPTS / "moments.md")["content"]
    assert "acknowledge, open the window, give your insight, then ask" in voice
    assert "the situation and the challenge in it" in voice
    assert "Never summarise what they told you and never show them your notes" in voice
    assert "Never leave them with a suggestion and nothing to answer" in voice
    assert "they carry what the person told you, so they know you were listening" in voice
    assert "Using something they said inside your question, so it lands on their situation, is not summarising" in voice
    assert "when you see your friends doing well?" in voice
    assert "short, plain" not in voice and "short, plain" not in chat
    assert "Say it the way a person would, in everyday words, never as an assessment" in voice
    assert "Is what's bothering you the situation, or something more about yourself?" in voice
    assert "which is more pervasive, or whether it is both" in voice
    assert "Less about the feeling, more about the challenge and what they can control" in voice
    assert "# The barometer" in chat and "# Checking your understanding" not in chat
    assert "Do you want to work through it with a framework?" in chat
    assert "Does that feel true for you?" not in chat
    assert "would rather keep talking" in moments


def test_a_chat_reply_is_checked_for_its_shape_and_for_fixing_what_the_framework_is_for():
    """The client's test, 2026-10-29: in the chat Mani listens, and suggestions only move the conversation; the
    three shapes; the insight is the aha, never a solution."""
    from mani.chat import reply_checks
    from mani.llm.schema import Window

    window = Window(feeling="unsure you're happy", tied_to=["their 'it'll get better'", "work"], closest="their 'it'll get better'")
    assert reply_checks.chat_misses(
        "Work crowded in, and the answer was to wait. How does waiting sit with you?", shape="window", window=window,
        insight=None, move="none", asked_for_help=False) == []
    assert reply_checks.chat_misses(
        "You could set aside one evening a week. Would that work?", shape="open_ask", window=None, insight=None,
        move="none", asked_for_help=False) == ["solution in chat: you could set"]
    assert reply_checks.chat_misses(
        "One small thing: you could text them tonight. Would it help to work through it together?",
        shape="open_ask", window=None, insight=None, move="small_idea", asked_for_help=True) == []
    assert "insight reply names no outside thing" in reply_checks.chat_misses(
        "Maybe it's about being chosen. Is that it?", shape="insight", window=None, insight="it's about being chosen",
        move="none", asked_for_help=False)
    assert "insight is a solution" in reply_checks.chat_misses(
        "x?", shape="insight", window=window, insight="you could plan a trip together", move="none",
        asked_for_help=False)
    for allowed in ("Is it more the lack of time, or that it feels one-sided?",
                    "Could we stay with your brother first, and come back to the money?",
                    "It might help to look at what comfortable would mean for you.",
                    "You can still love them and feel unsure. Have you tried talking about it?"):
        assert reply_checks.solutions(allowed) == [], allowed


def test_a_link_back_to_the_core_and_the_shape_are_kept_with_what_mani_asked_itself():
    from mani.llm.schema import Window

    after = converse.understood_after({}, reply(
        link="core: the same sense of not doing enough", shape="window", move="clarifying_options",
        window=Window(feeling="lonely", tied_to=["work"], closest="work"),
    ), check_written=False)
    thinking = after[converse.THINKING]
    assert thinking["link"] == "core: the same sense of not doing enough"
    assert (thinking["shape"], thinking["move"]) == ("window", "clarifying_options")
    assert thinking["window"] == {"feeling": "lonely", "tied_to": ["work"], "closest": "work"}

def test_the_conversation_prompt_listens_in_three_shapes_and_leaves_the_solution_to_the_framework():
    """The client's test, 2026-10-29: the framework is the solution; suggestions in the chat only move it on; the
    insight is the aha, never a solution; three shapes; opening the window joins a feeling to what it is tied to."""
    chat = parse_prompt(PROMPTS / "conversation.md")["content"]
    for rule in ("The framework is the solution; the chat never tries to fix the problem.",
                 "**An insight is not a solution.**",
                 "# The three reply shapes", "`open_ask`", "`window`", "`insight`",
                 "When it is tied to two things, name both, then ask about the one closest to the feeling.",
                 "7. Move the conversation, never fix it",
                 "give at most one small idea"):
        assert rule in chat, rule
    for gone in ("# Helping", "Help the person consider options", "shift toward helping"):
        assert gone not in chat, gone
