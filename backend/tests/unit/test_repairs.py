# ABOUTME: Checks the deterministic corrections that replaced six regeneration calls, and the
# ABOUTME: client's offer, Keep chatting and Tell me more texts rendered from their templates.

import pytest

from mani.chat import repairs
from mani.chat.techniques import Registry
from mani.llm.schema import Moment, Offer, Reply, Style
from mani.models.rows import Framework
from scripts.seed import FRAMEWORKS_DIR, parse_framework

REFRAMING = Framework(
    id="thought_reframing", name="Thought Reframing", summary="s", body="b",
    phases=["offering", "surface", "externalize", "explore", "land", "ground"],
)
ABCDE = Framework(
    id="abcde", name="ABCDE", summary="s", body="b",
    phases=["offering", "activate", "belief", "consequence", "dispute", "effect", "ground"],
)


BODY_ROUTE = Framework(
    id="with_body_route", name="With body route", summary="s", body="b",
    phases=["offering", "one", "two", "closing", "somatic_body", "somatic_practice"],
)


@pytest.fixture
def registry() -> Registry:
    return Registry([REFRAMING, ABCDE, BODY_ROUTE])


@pytest.fixture(scope="module")
def client_abcde() -> Framework:
    """ABCDE as the client wrote it, from the same file that is seeded."""
    parsed = parse_framework(FRAMEWORKS_DIR / "abcde.md")
    return Framework(
        id=parsed["id"], name=parsed["name"], summary=parsed["summary"], body="b",
        phases=parsed["phases"], activation=parsed["activation"], stages=parsed["stages"],
    )


def reply(**overrides) -> Reply:
    return Reply(**({"text": "Thank you for telling me."} | overrides))


def fix(registry, model_reply, **overrides):
    defaults = {
        "moment": Moment.CHATTING,
        "confirmed": False,
        "conversation_style": "supportive",
        "wants_title": False,
    }
    return repairs.apply(model_reply, registry, **(defaults | overrides))


def test_leaked_script_metadata_is_stripped(registry):
    leaked = reply(
        text="Let's try something.\n\n**Mani:** Take a breath.\n\n(Include prompts: yes/no)"
    )
    fixed = fix(registry, leaked)
    assert "**Mani:**" not in fixed.text
    assert "Include prompts" not in fixed.text
    assert "Let's try something." in fixed.text
    assert fixed.notes


def test_a_long_title_is_trimmed_not_rejected(registry):
    """The schema capped this at 50 and failed the whole generation over it."""
    long = reply(title='  "Talking through a really long and rambling worry about work."  ')
    fixed = fix(registry, long, wants_title=True)
    assert fixed.title.startswith("Talking through")
    assert not fixed.title.endswith(".")
    assert len(fixed.title) <= repairs.MAX_TITLE_LENGTH


def test_a_title_is_ignored_when_none_was_asked_for(registry):
    assert fix(registry, reply(title="Unasked for")).title is None


def test_a_clean_reply_is_left_alone(registry):
    clean = reply(style=Style(shape="mirror and ask"))
    fixed = fix(registry, clean)
    assert fixed.notes == []
    assert fixed.text == clean.text
    assert fixed.prompts == []


def test_a_style_the_model_reports_in_title_case_still_counts(registry):
    """The shapes are taught in a table, so the model returns them capitalised as often as
    not. Dropping those would starve the anti-repetition loop rather than protect it."""
    titled = reply(style=Style(shape="Mirror And Ask"))
    fixed = fix(registry, titled)
    assert fixed.style == Style(shape="mirror and ask")
    assert fixed.notes == []


def test_an_off_list_shape_is_dropped_rather_than_failing_the_turn(registry):
    """A value outside the set is a ValidationError if the schema types it as an enum, and
    that costs a second provider call and then the person's message. It is only a self
    report about a reply that is otherwise fine, so it is dropped and the reply stands."""
    invented = reply(style=Style(shape="vibes"))
    fixed = fix(registry, invented)
    assert fixed.style is None
    assert fixed.text == "Thank you for telling me."
    assert fixed.notes


@pytest.mark.parametrize("style", ["directive", "supportive", "reflective"])
def test_presence_reaches_the_person_in_any_style(registry, style):
    """muhammad, 2026-09-24: presence may be said in any style when the moment calls for it,
    so a reply that says it reaches the person as written."""
    text = "I'm here. What happened after she left?"
    fixed = fix(registry, reply(text=text), conversation_style=style)
    assert fixed.text == text
    assert fixed.notes == []


# The client's offer, Keep chatting and Tell me more (spec 0003, AC-2 to AC-4).

SUPPORTIVE_OFFER = (
    "Feeling overwhelmed can make you question how well you're handling things.\n"
    "There's a framework called ABCDE that can help you understand the thoughts behind feeling used "
    "by your coworker, see whether those thoughts are really true, and find a more helpful way to "
    "think about what's happening.\n\nWould you like to try it?"
)


def offering(**slots) -> Reply:
    return reply(text="Model's own words.", heading_toward="abcde", offer=Offer(**slots))


def yes_to_the_check(registry, model_reply, **overrides):
    """The reply to a clear yes to Mani's check, the only turn an offer can be made on (spec 0006)."""
    return fix(registry, model_reply, **({"moment": Moment.CHECK_OPEN, "confirmed": True} | overrides))


def test_an_offer_is_the_clients_template_word_for_word_with_only_the_slots_filled(client_abcde):
    fixed = yes_to_the_check(
        Registry([client_abcde]),
        offering(
            lead_line="Feeling overwhelmed can make you question how well you're handling things.",
            going_through="feeling used by your coworker",
        ),
    )
    assert fixed.text == SUPPORTIVE_OFFER
    assert "Model's own words" not in fixed.text
    assert [(p.label, p.technique, p.decline) for p in fixed.prompts] == [
        ("Try it", "abcde", None), ("Tell me more", None, None), ("Keep chatting", None, True),
    ]
    assert fixed.offer_dropped is None


def test_a_slot_loses_its_quotes_and_trailing_punctuation_and_keeps_its_case(client_abcde):
    fixed = yes_to_the_check(
        Registry([client_abcde]), offering(going_through='"Feeling used by Sam."'),
        conversation_style="directive",
    )
    assert fixed.text == (
        "There's a framework called ABCDE that helps you identify the thoughts behind Feeling used by "
        "Sam, question whether they're true, and replace them with more realistic ones."
        "\n\nWould you like to try it?"
    )


@pytest.mark.parametrize(("change", "reason"), [
    ({"offer": Offer(going_through="  ")}, "no going_through"),
    ({"offer": Offer(going_through="feeling used")}, "no lead_line"),
])
def test_an_offer_that_cannot_be_made_sends_the_models_text_alone(client_abcde, change, reason):
    unusable = offering(lead_line="A line.", going_through="feeling used").model_copy(update=change)
    fixed = yes_to_the_check(Registry([client_abcde]), unusable)
    assert (fixed.text, fixed.prompts, fixed.offer_dropped) == ("Model's own words.", [], reason)


@pytest.mark.parametrize("heading_toward", [None, "box_breathing"])
def test_with_one_active_set_a_yes_offers_it_whatever_the_reply_heads_toward(client_abcde, heading_toward):
    """Spec 0006, AC-8: no framework id in code. With one set active, a yes to the check offers it."""
    unsure = offering(going_through="feeling used").model_copy(update={"heading_toward": heading_toward})
    fixed = yes_to_the_check(Registry([client_abcde]), unsure, conversation_style="directive")
    assert fixed.offer_dropped is None
    assert fixed.prompts[0].technique == "abcde"


def test_with_several_active_sets_an_offer_needs_the_one_the_reply_heads_toward(client_abcde):
    unsure = offering(going_through="feeling used").model_copy(update={"heading_toward": None})
    fixed = yes_to_the_check(Registry([client_abcde, REFRAMING]), unsure, conversation_style="directive")
    assert (fixed.text, fixed.offer_dropped) == ("Model's own words.", "no framework")


def test_an_empty_going_through_is_filled_from_the_feeling_they_named(client_abcde):
    """Spec 0006, AC-8: the offer is not dropped for a slot the stored understanding can fill,
    nor when the yes turn's reply forgot the offer field altogether."""
    for model_reply in (offering(going_through=" "), reply(text="Model's own words.", heading_toward="abcde")):
        fixed = yes_to_the_check(
            Registry([client_abcde]), model_reply, conversation_style="directive", feeling="your frustration",
        )
        assert "the thoughts behind your frustration," in fixed.text, model_reply


def test_no_offer_without_a_yes_to_the_check_or_for_a_set_without_a_template(client_abcde):
    both = Registry([client_abcde, REFRAMING])
    slots = {"lead_line": "A line.", "going_through": "feeling used"}
    unconfirmed = fix(both, offering(**slots), moment=Moment.CHECK_OPEN)
    assert (unconfirmed.text, unconfirmed.offer_dropped) == ("Model's own words.", "no yes to the check")
    no_template = offering(**slots).model_copy(update={"heading_toward": "thought_reframing"})
    assert yes_to_the_check(both, no_template).offer_dropped == "no template"


def test_an_offer_field_outside_the_answer_to_a_check_or_on_a_concern_does_nothing(client_abcde):
    slots = {"lead_line": "A line.", "going_through": "feeling used"}
    for overrides in ({"moment": Moment.IN_STAGES}, {"moment": Moment.CHATTING}, {"guarded": True}):
        fixed = yes_to_the_check(Registry([client_abcde]), offering(**slots), **overrides)
        assert (fixed.text, fixed.prompts, fixed.offer_dropped) == ("Model's own words.", [], None)


def test_keep_chatting_is_the_clients_question_with_their_words(client_abcde):
    assert repairs.keep_chatting(client_abcde, "supportive", "heavy.") == (
        "We can keep talking. What's been happening that's making things feel so heavy?"
    )
    assert repairs.keep_chatting(client_abcde, "supportive", "") is None


def test_once_told_more_the_offer_comes_back_with_two_buttons():
    assert [p.label for p in repairs.offer_buttons("abcde", explained=True)] == ["Try it", "Keep chatting"]


def test_the_slot_descriptions_are_the_clients_placeholders(client_abcde):
    directive = repairs.slots_for(Registry([client_abcde]), "directive", "abcde")
    assert directive.lead_line is None
    assert directive.going_through.startswith("their feeling from understanding as a short noun phrase")
    assert directive.their_words == "what they said they are struggling with, in their words"
    assert repairs.slots_for(Registry([client_abcde]), "supportive", None).lead_line.startswith(
        "A short warm line"
    )


@pytest.mark.parametrize(
    ("text", "said_before", "expected"),
    [
        # Observed: "Sam" in two of three replies, and as a reply's first word.
        ("I'm right here with you, Sam. What happened?", True, "I'm right here with you. What happened?"),
        ("Sam, what happened after that?", False, "What happened after that?"),
        # Once in a conversation is fine.
        ("Thank you for telling me, Sam. What happened?", False, "Thank you for telling me, Sam. What happened?"),
    ],
)
def test_their_name_is_used_once_at_most_and_never_first(registry, text, said_before, expected):
    fixed = fix(registry, reply(text=text), nickname="Sam", name_said_before=said_before)
    assert fixed.text == expected


CHECK_IN = ("Before we move on, let's check in. What are you noticing in your body right now "
            "compared with when we started?")


def test_the_body_check_in_is_sent_word_for_word():
    """The client: the somatic flow follows the supplied script exactly, never reworded. Mani's
    reflection stays; its own version of the question gives way to the script's."""
    reworded = "You can wait without deciding what it means. How does your body feel now?"
    assert repairs.with_the_check_in(reworded, CHECK_IN) == (
        f"You can wait without deciding what it means.\n\n{CHECK_IN}"
    )


def test_a_check_in_already_word_for_word_is_left_alone():
    exact = f"You can wait without deciding what it means. {CHECK_IN}"
    assert repairs.with_the_check_in(exact, CHECK_IN) == exact


def test_internal_words_never_reach_the_person(registry):
    """A sentence carrying the system's own words is dropped; the question stays."""
    leaked = reply(text="That is what my check_answer says. What happened after that?")
    fixed = fix(registry, leaked)
    assert fixed.text == "What happened after that?"
    assert any("internal" in note for note in fixed.notes)


def test_the_model_is_never_asked_for_a_mirroring_voice():
    """muhammad, 2026-09-24: mirroring is there but never forced. Asking for a voice every
    turn, never the same twice, forced the rotation the prompt no longer asks for."""
    style = Reply.model_json_schema()["$defs"]["Style"]
    assert set(style["properties"]) == {"shape"}
    assert "voice" not in Reply.model_fields["style"].description


# Mani's replies from the client's way of communication document, each as the client lays it out.
CLIENT_LAYOUT = [
    "I'm listening. What's frustrating you?",
    "When everything feels frustrating, sometimes it's because several things have been building up for a "
    "while. I don't want to assume that's what's happening to you.\n\nTell me, are you frustrated with the "
    "people around you, the circumstances you're dealing with, or how you're feeling about your life right now?",
    "That would be frustrating, especially when other people's lack of follow-through creates additional work "
    "for you. But I want to understand the pattern rather than assume everyone is the problem.\n\nWhen people "
    "fail to deliver, what typically happens next?\n\nDo you confront them, take over the work yourself, or end "
    "up chasing them until they do what they promised?",
    "So your ability to do your job depends on other people fulfilling their responsibilities. When they don't, "
    "your work gets held up, and you're left dealing with the consequences.\n\nHere's what I want to understand: "
    "When people fail to follow through, do they face any consequences, or does the responsibility for getting "
    "things back on track fall on you?",
]


@pytest.mark.parametrize("laid", CLIENT_LAYOUT)
def test_manis_own_text_keeps_the_models_line_breaks_and_gets_none_added(registry, laid):
    """muhammad, 2026-10-26: a line break the model wrote is kept, and code adds none of its own."""
    assert fix(registry, reply(text=laid), chat_text=True).text == laid
    one_line = laid.replace("\n\n", " ")
    assert fix(registry, reply(text=one_line), chat_text=True).text == one_line


def test_the_options_go_on_the_line_under_the_question_and_only_where_the_reply_is_free_text(registry):
    """muhammad, 2026-10-22: the options were left out of the text whenever the prompt's other lines said
    one question. They are a field the model has to fill, and code puts them on their own line."""
    asked = reply(
        text="A really long day has left you feeling anxious.\nWhat part of it is weighing on you most?",
        options="Is it something that happened, what still needs doing, or the day catching up with you",
    )
    assert fix(registry, asked, chat_text=True).text == (
        "A really long day has left you feeling anxious.\nWhat part of it is weighing on you most?\n\n"
        "Is it something that happened, what still needs doing, or the day catching up with you?"
    )
    assert fix(registry, reply(text="Take your time."), chat_text=True).text == "Take your time."
    assert fix(registry, asked).text == asked.text, "a stage reply is not laid out and carries none"
