# ABOUTME: Checks the deterministic corrections that replaced six regeneration calls.
# ABOUTME: Each case here cost an entire extra model call in the implementation ported from.

import pytest

from mani.chat import repairs
from mani.chat.techniques import Registry
from mani.llm.schema import Reply, SmartPrompt, Style, TechniqueState
from mani.models.rows import Framework

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


def reply(**overrides) -> Reply:
    return Reply(**({"text": "Thank you for telling me."} | overrides))


# Where buttons are allowed besides an offer, for the tests about what a button may say.
AT_THE_END = {"framework_running": True, "current_phase": "somatic_practice", "current_framework_id": "abcde"}


def fix(registry, model_reply, **overrides):
    defaults = {
        "already_offered": [],
        "current_framework_id": None,
        "current_phase": None,
        "selected_label": None,
        "accepted_this_turn": False,
        "framework_running": False,
        "cooldown_passed": True,
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


def test_an_already_offered_technique_is_dropped(registry):
    offered_again = reply(
        prompts=[
            SmartPrompt(label="Yes, let's try it", technique="abcde"),
            SmartPrompt(label="Not right now"),
        ]
    )
    fixed = fix(registry, offered_again, already_offered=["abcde"])
    # The button left behind answers an offer that is gone, and ordinary chat carries none.
    assert fixed.prompts == []
    assert any("already-offered" in n for n in fixed.notes)


def test_the_technique_being_offered_is_not_a_duplicate_of_itself(registry):
    still_offering = reply(
        prompts=[SmartPrompt(label="Yes, let's try it", technique="abcde")]
    )
    fixed = fix(
        registry, still_offering, already_offered=["abcde"], current_framework_id="abcde"
    )
    assert [p.technique for p in fixed.prompts if p.technique] == ["abcde"]


def test_no_framework_is_offered_from_inside_a_running_one(registry):
    """A framework in progress is the whole conversation until it completes or the person
    stops it. The same one restarting itself and a second one opening underneath it are the
    same failure - the person is left inside two at once."""
    nested = reply(
        prompts=[
            SmartPrompt(label="Try ABCDE", technique="abcde"),
            SmartPrompt(label="Try reframing", technique="thought_reframing"),
            SmartPrompt(label="Keep talking", technique=None),
        ]
    )
    fixed = fix(
        registry,
        nested,
        current_framework_id="abcde",
        current_phase="belief",
        framework_running=True,
    )
    # A stage in the middle of a framework carries no buttons at all.
    assert fixed.prompts == []
    assert sum("inside a running framework" in n for n in fixed.notes) == 2


def test_an_invented_technique_id_is_refused(registry):
    """A model-supplied identifier is untrusted until the registry recognises it."""
    invented = reply(prompts=[SmartPrompt(label="Try box breathing", technique="box_breathing")])
    assert fix(registry, invented).prompts == []


def test_the_button_the_user_just_tapped_is_not_offered_back(registry):
    echoed = reply(
        prompts=[SmartPrompt(label="Yes, let's try it"), SmartPrompt(label="Tell me more")]
    )
    fixed = fix(registry, echoed, selected_label="  yes, let's try it ", **AT_THE_END)
    assert [p.label for p in fixed.prompts] == ["Tell me more"]


def test_more_than_three_buttons_are_trimmed(registry):
    many = reply(prompts=[SmartPrompt(label=f"Option {n}") for n in range(6)])
    assert len(fix(registry, many, **AT_THE_END).prompts) == repairs.MAX_PROMPTS


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
    clean = reply(
        prompts=[SmartPrompt(label="Tell me more")],
        style=Style(shape="mirror and ask"),
    )
    fixed = fix(registry, clean, **AT_THE_END)
    assert fixed.notes == []
    assert [p.label for p in fixed.prompts] == ["Tell me more"]


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


def test_a_button_to_a_library_section_that_does_not_exist_lands_on_the_library_home(registry):
    """Same reasoning as the shape: an enum here fails the whole turn. Observed values -
    "library", "default", a topic phrase - all meant the library in general, so the button
    keeps working and opens the front page rather than a section that does not exist."""
    nowhere = reply(
        prompts=[SmartPrompt(label="Go to Library", library="library"),
                 SmartPrompt(label="Tell me more")]
    )
    fixed = fix(registry, nowhere, **AT_THE_END)
    assert [(p.label, p.library) for p in fixed.prompts] == [
        ("Go to Library", "home"), ("Tell me more", None),
    ]
    assert fixed.notes


def test_a_library_section_the_model_cased_differently_is_kept_and_corrected(registry):
    """A client navigates on this string exactly, so a value that matches loosely still has
    to leave repaired at the one spelling that string will actually match against."""
    lowercased = reply(
        prompts=[SmartPrompt(label="Read more", library="emotionalintelligence")]
    )
    fixed = fix(registry, lowercased, **AT_THE_END)
    assert [p.library for p in fixed.prompts] == ["EmotionalIntelligence"]
    assert fixed.notes == []


def test_a_technique_offered_before_the_cooldown_has_passed_is_dropped(registry):
    """The cooldown paces offers so a person is not handed one framework after another. The
    prompt states it; this is what holds it when the model does not."""
    early = reply(
        prompts=[SmartPrompt(label="Try it", technique="abcde"), SmartPrompt(label="Not now")]
    )
    fixed = fix(registry, early, cooldown_passed=False)
    # The button left behind answers an offer that is gone, and ordinary chat carries none.
    assert fixed.prompts == []
    assert any("cooldown" in n for n in fixed.notes)


def test_the_offer_still_waiting_for_an_answer_is_not_held_to_its_own_cooldown(registry):
    """The cooldown is measured from the offer itself, so without this the button for the
    offer the person has not answered yet would vanish on the very next turn."""
    pending = reply(prompts=[SmartPrompt(label="Yes, let's try", technique="abcde")])
    fixed = fix(
        registry, pending, cooldown_passed=False,
        current_framework_id="abcde", current_phase="offering", already_offered=["abcde"],
    )
    assert [p.technique for p in fixed.prompts if p.technique] == ["abcde"]


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


def test_the_offer_buttons_are_try_it_and_keep_chatting(registry):
    """Two buttons under every offer (muhammad, 2026-09-24): both survive the label-length and
    offer-coherence repairs. Three buttons stand under an offer (muhammad, 2026-10-08)."""
    offer = reply(
        text="I have a sequence of questions that could help. Would you like to try it?",
        prompts=[
            SmartPrompt(label="Try it", technique="abcde"),
            SmartPrompt(label="Tell me about this"),
            SmartPrompt(label="Keep chatting", decline=True),
        ],
    )
    fixed = fix(registry, offer)
    assert [p.label for p in fixed.prompts] == ["Try it", "Tell me more", "Keep chatting"]


def test_an_offer_refused_by_the_cooldown_takes_its_words_with_it(registry):
    """Dropping only the buttons left "Would you like to try it?" asking for a yes that
    nothing could take. The mirror before it stays."""
    early = reply(
        text="You open the report and then move away from it. I have a sequence of questions "
             "that could help you start. Would you like to try it?",
        prompts=[
            SmartPrompt(label="Try it", technique="abcde"),
            SmartPrompt(label="Tell me about this"),
            SmartPrompt(label="Keep chatting", decline=True),
        ],
    )
    fixed = fix(registry, early, cooldown_passed=False)
    assert fixed.prompts == []
    assert fixed.text == "You open the report and then move away from it."


@pytest.mark.parametrize("offer", [
    "There's a set of questions that could help you with this. Would you like to try it?",
    "We could go through a few questions together. Would you like to try that?",
    "There are some questions that might help set your mind at ease. Shall we go through them?",
    "Would it help to look at it together, one step at a time?",
])
def test_an_offer_in_any_wording_goes_with_its_button(registry, offer):
    """Offers are worded fresh each time (muhammad, 2026-09-24), so recognising one cannot
    depend on a single fixed sentence."""
    early = reply(
        text=f"You open the report and then move away from it. {offer}",
        prompts=[SmartPrompt(label="Try it", technique="abcde"),
                 SmartPrompt(label="Keep chatting", decline=True)],
    )
    fixed = fix(registry, early, cooldown_passed=False)
    assert fixed.text == "You open the report and then move away from it."


def test_varied_offer_wording_keeps_its_buttons(registry):
    offer = reply(
        text="There are some questions that might help set your mind at ease. Shall we go through them?",
        prompts=[SmartPrompt(label="Try it", technique="abcde"),
                 SmartPrompt(label="Tell me about this"),
                 SmartPrompt(label="Keep chatting", decline=True)],
    )
    assert [p.label for p in fix(registry, offer).prompts] == ["Try it", "Tell me more", "Keep chatting"]


def test_an_offer_made_only_by_buttons_gets_the_clients_permission_question(registry):
    """The client's offer is a spoken question the buttons answer. A reply that mirrors and
    then lets the buttons do the asking leaves the person with nothing to say yes to."""
    silent = reply(
        text="You're replaying the exchange and wondering where you went wrong.",
        prompts=[
            SmartPrompt(label="Try it", technique="abcde"),
            SmartPrompt(label="Keep chatting", decline=True),
        ],
    )
    fixed = fix(registry, silent, conversation_style="direct")
    assert fixed.text.endswith("Would you like to try it?")
    assert len(fixed.prompts) == 3


def test_offer_buttons_under_a_different_question_are_dropped(registry):
    """"What feels strongest right now?" with [Yes, let's try it] under it asks one thing and
    offers another. Dropping the offer is the safe correction; it can come next turn."""
    mixed = reply(
        text="Your chest feels tight and your thoughts are racing. What feels strongest right now?",
        prompts=[
            SmartPrompt(label="Yes, let's try it", technique="abcde"),
            SmartPrompt(label="Tell me more"),
            SmartPrompt(label="I want to keep talking", decline=True),
        ],
    )
    fixed = fix(registry, mixed, conversation_style="reflective")
    assert fixed.prompts == []
    assert fixed.text.endswith("What feels strongest right now?")


def test_a_real_offer_keeps_its_buttons(registry):
    """A question asking whether they want to try is the offer itself, not a second question,
    so the buttons stay; its wording gives way to the client's."""
    offer = reply(
        text="I have a structured approach that can help you work through this. Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique="abcde"),
                 SmartPrompt(label="Keep chatting", decline=True)],
    )
    fixed = fix(registry, offer, conversation_style="direct")
    assert len(fixed.prompts) == 3
    assert fixed.text.startswith("I have a structured approach that can help you work through this.")
    assert fixed.text.endswith("Would you like to try it?")


@pytest.mark.parametrize("style", ["direct", "supportive", "reflective"])
def test_presence_reaches_the_person_in_any_style(registry, style):
    """muhammad, 2026-09-24: presence may be said in any style when the moment calls for it,
    so a reply that says it reaches the person as written."""
    text = "I'm here. What happened after she left?"
    fixed = fix(registry, reply(text=text), conversation_style=style)
    assert fixed.text == text
    assert fixed.notes == []


def test_ordinary_chat_carries_no_buttons(registry):
    """The client: buttons in ordinary chat read as a menu, not a conversation (2026-09-24)."""
    chatty = reply(text="What happened next?", prompts=[
        SmartPrompt(label="Tell me more"), SmartPrompt(label="Not sure"),
    ])
    fixed = fix(registry, chatty)
    assert fixed.prompts == []
    assert any("outside an offer or a framework's end" in n for n in fixed.notes)


def test_an_offer_keeps_the_buttons_it_carries(registry):
    offer = reply(
        text="There are some questions that could help with this. Would you like to try them?",
        prompts=[SmartPrompt(label="Try it", technique="abcde"),
                 SmartPrompt(label="Keep chatting", decline=True)],
    )  # its question gives way to the client's, see the composed-offer tests
    assert [p.label for p in fix(registry, offer).prompts] == ["Try it", "Tell me more", "Keep chatting"]


def test_the_end_of_a_framework_keeps_its_buttons(registry):
    practice = reply(
        text="Hand on your chest. In for four, out for six, three times.",
        prompts=[SmartPrompt(label="I tried it"), SmartPrompt(label="Not yet"),
                 SmartPrompt(label="Feeling better")],
    )
    fixed = fix(registry, practice, framework_running=True, current_phase="grounding",
                current_framework_id="abcde")
    assert [p.label for p in fixed.prompts] == ["I tried it", "Not yet", "Feeling better"]


DESCRIBED = Framework(
    id="abcde", name="ABCDE", body="b", phases=["offering", "activate", "ground"],
    summary="These questions help you separate what happened from what you told yourself about it.",
)
OFFER_BUTTONS = [
    SmartPrompt(label="Try it", technique="abcde"),
    SmartPrompt(label="Keep chatting", decline=True),
]


def test_an_offer_is_manis_line_then_the_clients_question():
    """muhammad, 2026-10-09: the offer is short, as in the client's own examples. The description
    is kept for Tell me more, so nothing is promised before they have asked to hear more."""
    part = "There's a set of questions called ABCDE we could go through for this."
    fixed = fix(Registry([DESCRIBED]), reply(text=part, prompts=OFFER_BUTTONS),
                conversation_style="supportive")
    assert fixed.text == f"{part}\n\nWould you like to try it?"
    assert DESCRIBED.summary not in fixed.text
    assert [p.label for p in fixed.prompts] == ["Try it", "Tell me more", "Keep chatting"]


def test_an_offer_always_names_the_set_of_questions():
    """muhammad, 2026-10-09: the person is told which set of questions is offered. A model line
    that leaves the name out gets it added; one that says it, in any spelling, is left alone."""
    unnamed = "There are some questions we could go through together for this."
    fixed = fix(Registry([DESCRIBED]), reply(text=unnamed, prompts=OFFER_BUTTONS),
                conversation_style="direct")
    assert fixed.text == f"{unnamed} It's called ABCDE.\n\nWould you like to try it?"

    named = "A set of questions called abcde could help with this."
    fixed = fix(Registry([DESCRIBED]), reply(text=named, prompts=OFFER_BUTTONS),
                conversation_style="direct")
    assert fixed.text.count("ABCDE") + fixed.text.count("abcde") == 1


def test_tell_me_more_shows_the_description_and_offers_again():
    """The client's description is the answer to Tell me more, after Mani's own words about it,
    and the offer comes back with Try it and Keep chatting."""
    explained = "We would look at what happened, and at what you told yourself about it."
    last = "There's a set of questions called ABCDE for this.\n\nWould you like to try it?"
    fixed = fix(Registry([DESCRIBED]), reply(text=explained, prompts=OFFER_BUTTONS),
                conversation_style="reflective", last_mani_text=last,
                selected_label="Tell me more", current_framework_id="abcde")
    assert fixed.text == f"{explained}\n\n{DESCRIBED.summary}\n\nWould you like to try it?"
    assert [p.label for p in fixed.prompts] == ["Try it", "Keep chatting"]


def test_the_models_own_permission_question_gives_way_to_the_clients():
    """Told not to ask, the model sometimes asks anyway. Two permission questions in one reply
    read as a form, so the client's wording is the one that stays."""
    part = "You keep going over what he said. There are some questions we could go through."
    fixed = fix(Registry([DESCRIBED]),
                reply(text=f"{part} Would you like to try them?", prompts=OFFER_BUTTONS),
                conversation_style="direct")
    assert fixed.text == f"{part} It's called ABCDE.\n\nWould you like to try it?"
    assert fixed.text.count("?") == 1


def test_the_description_is_not_repeated_when_the_last_reply_showed_it():
    """They asked what it involves, and Mani explained in its own words and offered again.
    The description is already on their screen, so only the question is added."""
    explained = "We would look at what happened, and at what you told yourself about it."
    last = (f"There's a set of questions called ABCDE for this.\n\n{DESCRIBED.summary}"
            "\n\nWould you like to try it?")
    fixed = fix(Registry([DESCRIBED]), reply(text=explained, prompts=OFFER_BUTTONS),
                conversation_style="reflective", last_mani_text=last, offer_asked_about=True)
    assert fixed.text == f"{explained}\n\nWould you like to try it?"


def test_a_description_the_model_already_wrote_is_not_added_twice():
    """Offers showed the description twice when the model copied it as well. Word for word,
    exactly once."""
    part = f"There are some questions we could go through together for this. {DESCRIBED.summary}"
    fixed = fix(Registry([DESCRIBED]), reply(text=part, prompts=OFFER_BUTTONS),
                conversation_style="direct", offer_asked_about=True)
    assert fixed.text.count(DESCRIBED.summary) == 1
    assert fixed.text.endswith("Would you like to try it?")


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


def test_an_offer_sharing_a_reply_with_another_question_leaves_no_half_offer(registry):
    """Its buttons go, so the offer can come next turn; its words go with them, or the person
    reads an offer with nothing to answer it."""
    stacked = reply(
        text="What does that feel like for you? There are some questions we could go through together for this.",
        prompts=OFFER_BUTTONS,
    )
    fixed = fix(registry, stacked)
    assert fixed.prompts == []
    assert fixed.text == "What does that feel like for you?"


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


def test_the_nearest_fit_is_offered_with_the_same_buttons_as_a_confident_one(registry):
    """An offer is an offer. The nearest fit carries no hedging label of its own, so a person
    choosing it is not told they are settling (muhammad, 2026-10-08)."""
    nearest = reply(
        text="Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique="abcde"),
                 SmartPrompt(label="Keep chatting", decline=True)],
    )
    fixed = fix(registry, nearest)
    assert [p.label for p in fixed.prompts] == ["Try it", "Tell me more", "Keep chatting"]
    assert fixed.prompts[0].technique == "abcde" and fixed.prompts[2].decline is True


def test_tell_me_more_survives_beside_an_offer(registry):
    """Three buttons under an offer (muhammad, 2026-10-08): Try it, Tell me more, Keep chatting.
    The explain button used to be dropped here."""
    offered = reply(
        text="Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique="abcde"),
                 SmartPrompt(label="Tell me more"),
                 SmartPrompt(label="Keep chatting", decline=True)],
    )
    fixed = fix(registry, offered)
    assert [p.label for p in fixed.prompts] == ["Try it", "Tell me more", "Keep chatting"]


def test_a_confident_offer_keeps_its_own_label(registry):
    confident = reply(
        text="Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique="abcde"),
                 SmartPrompt(label="Keep chatting", decline=True)],
    )
    assert [p.label for p in fix(registry, confident).prompts] == ["Try it", "Tell me more", "Keep chatting"]


def test_declining_or_knowing_what_to_do_is_told_apart_from_not_knowing_where():
    assert repairs.declines_or_acts("not now")
    assert repairs.declines_or_acts("No")
    assert repairs.declines_or_acts("I'm going to call her")
    assert not repairs.declines_or_acts("idk")
    assert not repairs.declines_or_acts("no idea where")


def test_a_practice_is_the_clients_words_for_the_place_in_the_style_being_spoken():
    stage = {"if_unclear": [
        {"when": "they feel it in the chest",
         "reply": {"supportive": "Supportive chest.", "direct": "Direct chest.", "reflective": "Reflective\nchest."}},
        {"when": "they feel it somewhere else", "reply": "Bring gentle attention."},
        {"when": "they have not said where they feel it", "reply": "Where?", "prompts": ["Chest"]},
    ]}
    assert repairs.practice_for(stage, "Chest", "direct") == ("Direct chest.", [])
    assert repairs.practice_for(stage, "Chest", "reflective")[0] == "Reflective\nchest."
    assert repairs.practice_for(stage, "Somewhere else", "supportive")[0] == "Bring gentle attention."
    assert repairs.practice_for(stage, "Head", "direct") is None
    assert repairs.practice_in(stage, "Hmm. Direct chest. Fine.", "direct")
    assert not repairs.practice_in(stage, "Hmm. Direct chest. Fine.", "supportive")
    assert not repairs.practice_in(stage, "Where?", "direct")


def test_the_acknowledgement_before_a_question_is_the_replys_first_sentence():
    text = "It is okay not to know where. Try bringing gentle attention there. Where is it?"
    assert repairs.first_sentence(text) == "It is okay not to know where."
    assert repairs.first_sentence("No full stop here") == "No full stop here"


def test_internal_words_never_reach_the_person(registry):
    """Loli's test, 2026-10-09: "the nearest fit I have" and "the closest fit I have" reached the
    person in all three styles. A sentence carrying the system's own words is dropped; the
    question stays."""
    leaked = reply(text="This is the closest fit I have. What happened after that?")
    fixed = fix(registry, leaked)
    assert fixed.text == "What happened after that?"
    assert any("internal" in note for note in fixed.notes)


def test_the_model_is_never_asked_for_a_mirroring_voice():
    """muhammad, 2026-09-24: mirroring is there but never forced. Asking for a voice every
    turn, never the same twice, forced the rotation the prompt no longer asks for."""
    style = Reply.model_json_schema()["$defs"]["Style"]
    assert set(style["properties"]) == {"shape"}
    assert "voice" not in Reply.model_fields["style"].description
def test_the_place_a_person_names_is_read_from_their_own_words():
    assert repairs.named_place("Chest") == "Chest"
    assert repairs.named_place("my stomach is in knots") == "Stomach"
    assert repairs.named_place("ahoulder") is None
    assert repairs.named_place("my shoulders") == "Somewhere else"
    assert repairs.named_place("idk") is None
def test_a_feeling_that_comes_back_is_told_from_one_that_only_eased():
    assert repairs.comes_back("I feel calmer for a second, then it comes back")
    assert repairs.comes_back("it came back again")
    assert not repairs.comes_back("I feel calmer now")
