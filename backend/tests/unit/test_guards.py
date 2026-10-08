# ABOUTME: Checks the guards that stop a model supplied id or value from being stored or sent unchecked.
# ABOUTME: Real replies and a real registry; the reply's words are never edited, only what cannot be stored goes.

import pytest

from mani.chat import guards
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

OFFER = [
    SmartPrompt(label="Try it", technique="abcde"),
    SmartPrompt(label="Tell me about this"),
    SmartPrompt(label="Keep chatting", decline=True),
]


# The shapes as Config.reply_shapes holds them once parsed from the mani_base row.
SHAPES = frozenset({"warmth lead", "mirror and ask", "presence only"})


@pytest.fixture
def registry() -> Registry:
    return Registry([REFRAMING, ABCDE])


def reply(**overrides) -> Reply:
    return Reply(**({"text": "Thank you for telling me."} | overrides))


def check(registry, model_reply, **overrides):
    defaults = {
        "current_framework_id": None,
        "current_phase": None,
        "accepted_this_turn": False,
        "framework_running": False,
        "declined": False,
        "retiring": False,
        "wants_title": False,
        "shapes": SHAPES,
    }
    return guards.check(model_reply, registry, **(defaults | overrides))


def test_the_reply_goes_out_as_the_model_wrote_it_apart_from_surrounding_whitespace(registry):
    """No sentence is cut for a feeling they never named, their name, a repeated question, or an
    offer made early: the model's words are the person's words."""
    written = (
        "Sam, that sounds really stressful and you must feel so anxious. Is it the same thing as "
        "last time? Would you like to try a set of questions together?"
    )
    checked = check(registry, reply(text=f"  {written}\n"), accepted_this_turn=False)
    assert checked.text == written
    assert checked.notes == []


def test_buttons_are_kept_as_the_model_sent_them_in_its_order(registry):
    """No cap, no duplicate removal, no policing of labels outside an offer."""
    many = reply(prompts=[SmartPrompt(label=label) for label in
                          ["Sad", "Sad", "I'm overthinking it", "One two three four five six", "A", "B"]])
    checked = check(registry, many)
    assert [p.label for p in checked.prompts] == [
        "Sad", "Sad", "I'm overthinking it", "One two three four five six", "A", "B",
    ]
    assert checked.notes == []


def test_a_button_with_no_label_is_dropped(registry):
    blank = reply(prompts=[SmartPrompt(label="  "), SmartPrompt(label="Tell me more")])
    checked = check(registry, blank)
    assert [p.label for p in checked.prompts] == ["Tell me more"]
    assert checked.notes == ["dropped a button: empty label"]


def test_an_invented_technique_id_is_refused_and_takes_the_offers_other_buttons_with_it(registry):
    """A model-supplied identifier is untrusted until the registry recognises it, and Keep
    chatting and Tell me about this answer an offer that is no longer there."""
    invented = reply(prompts=[
        SmartPrompt(label="Try it", technique="box_breathing"),
        SmartPrompt(label="Tell me about this"),
        SmartPrompt(label="Keep chatting", decline=True),
        SmartPrompt(label="Go to Library", library="home"),
    ])
    checked = check(registry, invented)
    assert [p.label for p in checked.prompts] == ["Go to Library"]
    assert "box_breathing" not in " ".join(checked.notes)


def test_an_offer_with_a_known_technique_keeps_its_two_buttons(registry):
    checked = check(registry, reply(prompts=OFFER))
    assert [p.label for p in checked.prompts] == ["Try it", "Tell me about this", "Keep chatting"]
    assert checked.notes == []


def test_no_framework_is_offered_from_inside_a_running_one(registry):
    """A framework in progress is the whole conversation until it completes or the person
    stops it. The same one restarting itself and a second one opening underneath it are the
    same failure - the person is left inside two at once."""
    nested = reply(prompts=[
        SmartPrompt(label="Try ABCDE", technique="abcde"),
        SmartPrompt(label="Try reframing", technique="thought_reframing"),
        SmartPrompt(label="Keep chatting", decline=True),
    ])
    checked = check(
        registry, nested,
        current_framework_id="abcde", current_phase="belief", framework_running=True,
    )
    assert checked.prompts == []
    assert sum("a framework is running" in n for n in checked.notes) == 2


@pytest.mark.parametrize("turn", [{"declined": True}, {"retiring": True}])
def test_an_offer_cannot_stand_on_a_turn_that_records_a_decline_or_a_retirement(registry, turn):
    """Storing the offer would overwrite the decline or cancel the retirement this turn writes."""
    offered_again = reply(prompts=OFFER)
    checked = check(registry, offered_again, **turn)
    assert checked.prompts == []
    assert checked.text == "Thank you for telling me."


def test_a_library_button_survives_a_turn_that_drops_the_offer(registry):
    mixed = reply(prompts=[*OFFER, SmartPrompt(label="Go to Library", library="home")])
    checked = check(registry, mixed, declined=True)
    assert [p.label for p in checked.prompts] == ["Go to Library"]


def test_a_button_to_a_library_section_that_does_not_exist_lands_on_the_library_home(registry):
    """An enum here would fail the whole turn. Observed values - "library", "default", a topic
    phrase - all meant the library in general, so the button keeps working and opens the front
    page rather than a section that does not exist."""
    nowhere = reply(prompts=[
        SmartPrompt(label="Go to Library", library="my mother's funeral"),
        SmartPrompt(label="Tell me more"),
    ])
    checked = check(registry, nowhere)
    assert [(p.label, p.library) for p in checked.prompts] == [
        ("Go to Library", "home"), ("Tell me more", None),
    ]
    assert checked.notes == ["sent a button to the library home: unknown library section"]


def test_a_library_section_the_model_cased_differently_is_kept_and_corrected(registry):
    """A client navigates on this string exactly, so a value that matches loosely still has
    to leave at the one spelling that string will actually match against."""
    lowercased = reply(prompts=[SmartPrompt(label="Read more", library="emotionalintelligence")])
    checked = check(registry, lowercased)
    assert [p.library for p in checked.prompts] == ["EmotionalIntelligence"]
    assert checked.notes == []


def test_the_reply_that_starts_a_framework_may_ask_the_second_stage(registry):
    """What they said before accepting answers the first stage, so the reply asks the second."""
    running = {"accepted_this_turn": True, "framework_running": True,
               "current_framework_id": "abcde", "current_phase": "offering"}
    second = reply(state=TechniqueState(technique="abcde", step="belief"))
    assert check(registry, second, **running).phase == "belief"

    third = reply(state=TechniqueState(technique="abcde", step="consequence"))
    assert check(registry, third, **running).phase == "belief"


def test_a_skipped_phase_is_corrected_rather_than_regenerated(registry):
    jumped = reply(state=TechniqueState(technique="thought_reframing", step="land"))
    checked = check(registry, jumped, current_framework_id="thought_reframing",
                    current_phase="offering")
    assert checked.phase == "surface"
    assert checked.notes == ["corrected the reported stage: skipped surface, externalize, explore"]


def test_a_technique_appearing_mid_flow_is_pulled_back_to_offering(registry):
    straight_in = reply(state=TechniqueState(technique="abcde", step="belief"))
    assert check(registry, straight_in).phase == "offering"


def test_state_for_an_unknown_technique_is_ignored(registry):
    nonsense = reply(state=TechniqueState(technique="somatic_release", step="offering"))
    checked = check(registry, nonsense)
    assert checked.framework_id is None and checked.phase is None
    assert checked.notes == ["ignored state: technique not in the registry"]


def test_state_naming_a_different_framework_than_the_running_one_is_ignored(registry):
    """Every framework ends on the same stage ids, so a transition check alone lets the model
    record a framework the person never agreed to. Only the running one may be reported."""
    swapped = reply(state=TechniqueState(technique="thought_reframing", step="surface"))
    checked = check(
        registry, swapped, framework_running=True,
        current_framework_id="abcde", current_phase="offering",
    )
    assert checked.framework_id is None
    assert checked.notes == ["ignored state: not the running framework"]


def test_a_long_title_is_trimmed_not_rejected(registry):
    """The schema capped this at 50 and failed the whole generation over it."""
    long = reply(title='  "Talking through a really long and rambling worry about work."  ')
    checked = check(registry, long, wants_title=True)
    assert checked.title.startswith("Talking through")
    assert not checked.title.endswith(".")
    assert len(checked.title) <= guards.MAX_TITLE_LENGTH


def test_a_title_is_ignored_when_none_was_asked_for(registry):
    assert check(registry, reply(title="Unasked for")).title is None


def test_a_style_the_model_reports_in_title_case_still_counts(registry):
    """The shapes are taught in a table, so the model returns them capitalised as often as
    not. Dropping those would starve the anti-repetition loop rather than protect it."""
    checked = check(registry, reply(style=Style(shape="Mirror And Ask")))
    assert checked.style == Style(shape="mirror and ask")
    assert checked.notes == []


def test_an_off_list_shape_is_dropped_rather_than_failing_the_turn(registry):
    """A value outside the set is a ValidationError if the schema types it as an enum, and
    that costs the person's message. It is only a self report about a reply that is otherwise
    fine, so it is dropped and the reply stands."""
    checked = check(registry, reply(style=Style(shape="vibes")))
    assert checked.style is None
    assert checked.text == "Thank you for telling me."
    assert checked.notes == ["dropped the response shape: not on the list"]


def test_with_no_shapes_taught_every_shape_is_dropped_and_the_reply_still_stands(registry):
    """A mani_base row edited in the portal so its shapes no longer parse leaves the set empty."""
    checked = check(registry, reply(style=Style(shape="mirror and ask")), shapes=frozenset())
    assert checked.style is None
    assert checked.text == "Thank you for telling me."
    assert checked.notes == ["dropped the response shape: not on the list"]
