# ABOUTME: Checks the deterministic corrections that replaced six regeneration calls, and the
# ABOUTME: client's offer, Keep chatting and Tell me more texts rendered from their templates.

import pytest

from mani.chat import repairs
from mani.chat.techniques import Registry
from mani.llm.schema import Moment, Offer, Reply, Style, TechniqueState
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
    phases=["offering", "one", "two", "closing", "somatic_checkin", "somatic_practice"],
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
        "may_offer": True,
        "finished_framework_id": None,
        "current_framework_id": None,
        "current_phase": None,
        "accepted_this_turn": False,
        "framework_running": False,
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


def test_the_reply_that_starts_a_framework_may_ask_a_stage_several_in(registry):
    """What they said before accepting answers the first stages, so the reply asks the first that
    it does not answer, however far in."""
    second = reply(state=TechniqueState(technique="abcde", step="belief"))
    fixed = fix(registry, second, accepted_this_turn=True, framework_running=True,
                current_framework_id="abcde", current_phase="offering")
    assert fixed.phase == "belief"

    third = reply(state=TechniqueState(technique="abcde", step="consequence"))
    fixed = fix(registry, third, accepted_this_turn=True, framework_running=True,
                current_framework_id="abcde", current_phase="offering")
    assert fixed.phase == "consequence"
    assert not fixed.notes


def test_a_stage_that_must_be_asked_is_not_jumped_over_and_is_corrected_not_regenerated(registry):
    jumped = reply(state=TechniqueState(technique="with_body_route", step="somatic_practice"))
    fixed = fix(registry, jumped, framework_running=True, current_framework_id="with_body_route",
                current_phase="two")
    assert fixed.phase == "closing"
    assert fixed.notes


def test_a_technique_appearing_mid_flow_is_pulled_back_to_offering(registry):
    straight_in = reply(state=TechniqueState(technique="abcde", step="belief"))
    assert fix(registry, straight_in).phase == "offering"


def test_state_for_an_unknown_technique_is_ignored(registry):
    nonsense = reply(state=TechniqueState(technique="somatic_release", step="offering"))
    fixed = fix(registry, nonsense)
    assert fixed.framework_id is None and fixed.phase is None


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


def test_state_naming_a_different_framework_than_the_running_one_is_ignored(registry):
    """Every framework ends on the same stage ids, so a transition check alone lets the model
    record a framework the person never agreed to. Only the running one may be reported."""
    # Both frameworks exist and both have "offering", so only the identity check can refuse.
    swapped = reply(state=TechniqueState(technique="thought_reframing", step="surface"))
    fixed = fix(
        registry, swapped, framework_running=True,
        current_framework_id="abcde", current_phase="offering",
    )
    assert fixed.framework_id is None
    assert any("not the running one" in n for n in fixed.notes)


@pytest.mark.parametrize("style", ["directive", "supportive", "reflective"])
def test_presence_reaches_the_person_in_any_style(registry, style):
    """muhammad, 2026-09-24: presence may be said in any style when the moment calls for it,
    so a reply that says it reaches the person as written."""
    text = "I'm here. What happened after she left?"
    fixed = fix(registry, reply(text=text), conversation_style=style)
    assert fixed.text == text
    assert fixed.notes == []


# The client's offer, Keep chatting and Tell me more (spec 0003, AC-2 to AC-4).

# The client's short list of the five steps, sent after the permission question (R11).
FIVE_STEPS = (
    "\n\n- A: Activating Event. What happened or what is happening.\n"
    "- B: Belief. What you began believing about it.\n"
    "- C: Consequences. How that belief affected your feelings or actions.\n"
    "- D: Dispute. What supports the belief and what might challenge it.\n"
    "- E: Effective New Belief. A more realistic and helpful way to understand it."
)

SUPPORTIVE_OFFER = (
    "Feeling overwhelmed can make you question how well you're handling things.\n"
    "There's a framework called ABCDE that can help you understand the thoughts behind feeling used "
    "by your coworker, see whether those thoughts are really true, and find a more helpful way to "
    "think about what's happening.\n\nWould you like to try it?" + FIVE_STEPS
)


def offering(**slots) -> Reply:
    return reply(text="Model's own words.", heading_toward="abcde", offer=Offer(**slots))


def test_an_offer_is_the_clients_template_word_for_word_with_only_the_slots_filled(client_abcde):
    fixed = fix(
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
    fixed = fix(
        Registry([client_abcde]), offering(going_through='"Feeling used by Sam."'),
        conversation_style="directive",
    )
    assert fixed.text == (
        "There's a framework called ABCDE that helps you identify the thoughts behind Feeling used by "
        "Sam, question whether they're true, and replace them with more realistic ones."
        "\n\nWould you like to try it?" + FIVE_STEPS
    )


@pytest.mark.parametrize(("change", "reason"), [
    ({"heading_toward": None}, "no framework"),
    ({"heading_toward": "box_breathing"}, "unknown framework"),
    ({"offer": Offer(going_through="  ")}, "no going_through"),
    ({"offer": Offer(going_through="feeling used")}, "no lead_line"),
])
def test_an_offer_that_cannot_be_made_sends_the_models_text_alone(client_abcde, change, reason):
    unusable = offering(lead_line="A line.", going_through="feeling used").model_copy(update=change)
    fixed = fix(Registry([client_abcde]), unusable)
    assert (fixed.text, fixed.prompts, fixed.offer_dropped) == ("Model's own words.", [], reason)


def test_no_offer_for_the_set_just_finished_one_without_a_template_or_a_closed_window(client_abcde):
    both = Registry([client_abcde, REFRAMING])
    slots = {"lead_line": "A line.", "going_through": "feeling used"}
    assert fix(both, offering(**slots), finished_framework_id="abcde").offer_dropped == "they just finished it"
    assert fix(both, offering(**slots), may_offer=False).offer_dropped == "the window is closed"
    no_template = offering(**slots).model_copy(update={"heading_toward": "thought_reframing"})
    assert fix(both, no_template).offer_dropped == "no template"


def test_an_offer_field_outside_the_chatting_moment_or_on_a_concern_does_nothing(client_abcde):
    slots = {"lead_line": "A line.", "going_through": "feeling used"}
    for overrides in ({"moment": Moment.IN_STAGES}, {"guarded": True}):
        fixed = fix(Registry([client_abcde]), offering(**slots), **overrides)
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
    assert directive.going_through.startswith("how they are feeling or what is worrying them, in their own words")
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


def test_a_repeated_clarification_never_reaches_the_person(registry):
    """Code enforces the 'never twice' half of the client's one-time check, regardless of
    what the model does: the [ctx] line already told it not to, this is the backstop."""
    twice = reply(text="Right, that makes sense. What would you like us to focus on today?")
    fixed = fix(registry, twice, clarification_already_used=True)
    assert fixed.text == "Right, that makes sense."
    assert any("clarification" in n for n in fixed.notes)


def test_the_first_clarification_is_left_alone(registry):
    first = reply(text="A few things came up there. Do I have this right?")
    fixed = fix(registry, first, clarification_already_used=False)
    assert fixed.text == first.text


def test_the_acknowledgement_before_a_question_is_the_replys_first_sentence():
    text = "It is okay not to know where. Try bringing gentle attention there. Where is it?"
    assert repairs.first_sentence(text) == "It is okay not to know where."
    assert repairs.first_sentence("No full stop here") == "No full stop here"


def test_internal_words_never_reach_the_person(registry):
    """A sentence carrying the system's own words is dropped; the question stays."""
    leaked = reply(text="That is what my offer_window allows. What happened after that?")
    fixed = fix(registry, leaked)
    assert fixed.text == "What happened after that?"
    assert any("internal" in note for note in fixed.notes)


def test_the_model_is_never_asked_for_a_mirroring_voice():
    """muhammad, 2026-09-24: mirroring is there but never forced. Asking for a voice every
    turn, never the same twice, forced the rotation the prompt no longer asks for."""
    style = Reply.model_json_schema()["$defs"]["Style"]
    assert set(style["properties"]) == {"shape"}
    assert "voice" not in Reply.model_fields["style"].description


# The body route (spec 0003, AC-5): the client's branch for the value the reply reports.

@pytest.fixture(scope="module")
def body_stages() -> dict:
    from scripts.seed import load_somatic_stages

    return load_somatic_stages()


@pytest.mark.parametrize(("body", "at", "style", "fits"), [
    ("chest", "closing", "directive", True),
    ("chest", "retiring", "directive", False),
    ("no_place", "closing", "directive", False),
    ("agreed", "somatic_checkin", "supportive", True),
    ("agreed", "somatic_checkin", "directive", False),
    ("acting", "somatic_practice", "reflective", False),
    ("returned", "retiring", "reflective", True),
])
def test_a_body_answer_counts_only_where_the_route_can_take_it(body, at, style, fits):
    assert repairs.body_answer_fits(body, at, style) is fits


def test_a_place_is_the_clients_practice_word_for_word_with_no_buttons(body_stages):
    step = repairs.body_reply("head", "somatic_checkin", body_stages, "directive", "Model words.")
    head = next(b for b in body_stages["somatic_practice"]["if_unclear"] if b["id"] == "head")
    assert (step.text, step.labels, step.phase, step.handoff) == (
        head["reply"]["directive"], [], "somatic_practice", False,
    )


def test_no_place_is_manis_first_sentence_then_the_clients_where_question(body_stages):
    step = repairs.body_reply(
        "no_place", "somatic_checkin", body_stages, "reflective", "It is hard to say. Is it your chest?",
    )
    assert step.text == "It is hard to say.\n\nWhere does that sit in your body right now?"
    assert step.labels == ["Chest", "Head", "Stomach", "Somewhere else"]


def test_a_decline_and_an_action_are_the_clients_lines_with_the_two_choices(body_stages):
    declined = repairs.body_reply("declined", "somatic_checkin", body_stages, "supportive", "Okay.")
    assert declined.text.startswith("You'd rather not check in with your body right now.")
    assert declined.handoff
    after_where = repairs.body_reply("declined", "somatic_practice", body_stages, "supportive", "Okay.")
    assert (after_where.text, after_where.handoff) == ("Okay.", True), "the client wrote no line for it"
    acting = repairs.body_reply("acting", "closing", body_stages, "supportive", "Okay.")
    assert acting.text.startswith("It sounds like you're ready to act on that.") and acting.handoff


def test_pain_gets_the_clients_safety_line_and_no_practice(body_stages):
    pain = repairs.body_reply("pain", "somatic_checkin", body_stages, "directive", "Okay.")
    assert (pain.text, pain.labels, pain.handoff) == (
        "Let's not do a breathing practice then. I'm here with you. What would help right now?", [], False,
    )
