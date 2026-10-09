# ABOUTME: Checks the guards that stop a model supplied id or value from being stored or sent unchecked.
# ABOUTME: Real replies and a real registry; the reply's words are never edited, only what cannot be stored goes.

import pytest

from mani.chat import guards
from mani.chat.techniques import Registry
from mani.llm.schema import Reply, SmartPrompt, StageReport, Style, TechniqueState
from mani.models.rows import Framework, StageStatus

REFRAMING = Framework(
    id="thought_reframing", name="Thought Reframing", summary="s", body="b",
    phases=["offering", "surface", "externalize", "explore", "land", "ground"],
)
ABCDE = Framework(
    id="abcde", name="ABCDE", summary="s", body="b",
    phases=["offering", "activate", "belief", "consequence", "dispute", "effect", "ground"],
)

WITH_ENDING = Framework(
    id="abcde", name="ABCDE", summary="s", body="b",
    phases=["offering", "activate", "closing", "somatic_checkin", "somatic_practice"],
)

# Shaped as the seed writes a framework: its own stages, `closing` as the last own phase, then the ending.
STAGED = Framework(
    id="abcde", name="ABCDE", summary="s", body="b",
    phases=["offering", "activate", "belief", "consequence", "closing", "somatic_checkin", "somatic_practice"],
)

OFFER = [
    SmartPrompt(label="Yes, let's try it", technique="abcde"),
    SmartPrompt(label="Tell me about this"),
    SmartPrompt(label="I want to keep talking", decline=True),
]


# The shapes as Config.reply_shapes holds them once parsed from the mani_base row.
SHAPES = frozenset({"warmth lead", "mirror and ask", "presence only"})


@pytest.fixture
def registry() -> Registry:
    return Registry([REFRAMING, ABCDE])


@pytest.fixture
def ending_registry() -> Registry:
    return Registry([WITH_ENDING])


@pytest.fixture
def staged_registry() -> Registry:
    return Registry([STAGED])


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


def test_an_invented_technique_id_is_refused_and_takes_the_decline_with_it(registry):
    """A model-supplied identifier is untrusted until the registry recognises it, and I want to
    keep talking answers an offer that is no longer there. A Tell me about this answers nothing in
    particular, so it stays."""
    invented = reply(prompts=[
        SmartPrompt(label="Yes, let's try it", technique="box_breathing"),
        SmartPrompt(label="Tell me about this"),
        SmartPrompt(label="I want to keep talking", decline=True),
        SmartPrompt(label="Go to Library", library="home"),
    ])
    checked = check(registry, invented)
    assert [p.label for p in checked.prompts] == ["Tell me about this", "Go to Library"]
    assert "box_breathing" not in " ".join(checked.notes)


def test_an_offer_with_a_known_technique_keeps_its_two_buttons(registry):
    checked = check(registry, reply(prompts=OFFER))
    assert [p.label for p in checked.prompts] == ["Yes, let's try it", "Tell me about this", "I want to keep talking"]
    assert checked.notes == []


def test_no_framework_is_offered_from_inside_a_running_one(registry):
    """A framework in progress is the whole conversation until it completes or the person
    stops it. The same one restarting itself and a second one opening underneath it are the
    same failure - the person is left inside two at once."""
    nested = reply(prompts=[
        SmartPrompt(label="Try ABCDE", technique="abcde"),
        SmartPrompt(label="Try reframing", technique="thought_reframing"),
        SmartPrompt(label="I want to keep talking", decline=True),
    ])
    checked = check(
        registry, nested,
        current_framework_id="abcde", current_phase="belief", framework_running=True,
    )
    assert checked.prompts == []
    assert sum("a framework is running" in n for n in checked.notes) == 2


@pytest.mark.parametrize("turn", [{"declined": True}, {"retiring": True}])
def test_an_offer_cannot_stand_on_a_turn_that_records_a_decline_or_a_retirement(registry, turn):
    """Storing the offer would overwrite the decline or cancel the retirement this turn writes. Its
    Yes, let's try it and I want to keep talking go; a Tell me about this answers nothing in
    particular and stays."""
    offered_again = reply(prompts=OFFER)
    checked = check(registry, offered_again, **turn)
    assert [p.label for p in checked.prompts] == ["Tell me about this"]
    assert checked.text == "Thank you for telling me."


def test_a_library_button_survives_a_turn_that_drops_the_offer(registry):
    mixed = reply(prompts=[*OFFER, SmartPrompt(label="Go to Library", library="home")])
    checked = check(registry, mixed, declined=True)
    assert [p.label for p in checked.prompts] == ["Tell me about this", "Go to Library"]


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


def test_the_reply_that_accepts_an_offer_records_no_phase_because_the_ledger_decides(staged_registry):
    """What they said before accepting may answer several stages; the code reads which from the
    reported stages, so whatever step the reply names is not recorded."""
    running = {"accepted_this_turn": True, "framework_running": True,
               "current_framework_id": "abcde", "current_phase": "offering"}
    third = reply(state=TechniqueState(technique="abcde", step="consequence"))
    checked = check(staged_registry, third, **running)
    assert checked.framework_id == "abcde"
    assert checked.phase is None
    assert checked.notes == []


def test_a_step_before_the_last_own_phase_records_nothing_and_is_not_corrected(staged_registry):
    running = {"framework_running": True, "current_framework_id": "abcde", "current_phase": "activate"}
    jumped = reply(state=TechniqueState(technique="abcde", step="consequence"))
    checked = check(staged_registry, jumped, **running)
    assert (checked.framework_id, checked.phase, checked.notes) == ("abcde", None, [])


def test_a_skipped_ending_phase_is_corrected_rather_than_regenerated(staged_registry):
    jumped = reply(state=TechniqueState(technique="abcde", step="somatic_practice"))
    checked = check(staged_registry, jumped, framework_running=True,
                    current_framework_id="abcde", current_phase="closing")
    assert checked.phase == "somatic_checkin"
    assert checked.notes == ["corrected the reported stage: skipped somatic_checkin"]


@pytest.mark.parametrize("step", ["belief", "offering", "vibing"])
def test_from_the_last_own_phase_on_a_step_before_it_holds_the_stored_phase(staged_registry, step):
    stepped_back = reply(state=TechniqueState(technique="abcde", step=step))
    checked = check(staged_registry, stepped_back, framework_running=True,
                    current_framework_id="abcde", current_phase="somatic_checkin")
    assert checked.phase == "somatic_checkin"
    assert checked.framework_id == "abcde"


def test_a_technique_appearing_mid_flow_records_no_phase_and_keeps_the_framework(staged_registry):
    straight_in = reply(state=TechniqueState(technique="abcde", step="belief"))
    checked = check(staged_registry, straight_in)
    assert (checked.framework_id, checked.phase) == ("abcde", None)


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


def ending_check(registry, model_reply, phase="somatic_practice", **overrides):
    """A turn on an accepted framework, stored on `phase`, whose ending is open."""
    return check(
        registry, model_reply, current_framework_id="abcde", current_phase=phase,
        framework_running=True, ending_open=True, **overrides,
    )


@pytest.mark.parametrize(
    ("written", "kept"),
    [("choice", guards.Ending.CHOICE), (" Keep_Talking ", guards.Ending.KEEP_TALKING)],
)
@pytest.mark.parametrize("phase", ["closing", "somatic_checkin", "somatic_practice"])
def test_an_ending_is_kept_while_the_ending_is_open_whatever_its_casing(
    ending_registry, written, kept, phase
):
    checked = ending_check(ending_registry, reply(ending=written), phase=phase)
    assert checked.ending is kept
    assert checked.notes == []


def test_an_ending_off_the_list_is_dropped_with_a_note(ending_registry):
    checked = ending_check(ending_registry, reply(ending="done"))
    assert checked.ending is None
    assert checked.notes == ["ignored ending: not one of the endings"]


def test_an_ending_before_the_ending_is_open_is_dropped_with_a_note(ending_registry):
    checked = check(
        ending_registry, reply(ending="choice"), current_framework_id="abcde",
        current_phase="activate", framework_running=True, ending_open=False,
    )
    assert checked.ending is None
    assert checked.notes == ["ignored ending: the ending is not open"]


def test_an_ending_with_no_framework_running_is_dropped(ending_registry):
    checked = check(ending_registry, reply(ending="choice"), ending_open=True)
    assert checked.ending is None


def test_a_reply_that_moves_the_stage_forward_is_not_also_the_end(ending_registry):
    """Offering the body check, or starting its steps, is the reply before the ending."""
    moved = reply(ending="choice", state=TechniqueState(technique="abcde", step="somatic_checkin"))
    checked = ending_check(ending_registry, moved, phase="closing")
    assert checked.ending is None
    assert checked.phase == "somatic_checkin"
    assert checked.notes == ["ignored ending: the reply moves the stage forward"]


def test_a_reply_that_holds_or_steps_back_may_end(ending_registry):
    held = reply(ending="keep_talking", state=TechniqueState(technique="abcde", step="somatic_checkin"))
    assert ending_check(ending_registry, held, phase="somatic_checkin").ending is guards.Ending.KEEP_TALKING
    back = reply(ending="choice", state=TechniqueState(technique="abcde", step="closing"))
    assert ending_check(ending_registry, back, phase="somatic_practice").ending is guards.Ending.CHOICE


def test_a_kept_ending_drops_a_technique_button_because_the_turn_retires(ending_registry):
    """Not running, so the running guard cannot be what drops it: only the retiring one can."""
    offer = reply(ending="choice", prompts=OFFER)
    checked = check(
        ending_registry, offer, current_framework_id="abcde", current_phase="somatic_practice",
        framework_running=False, ending_open=True,
    )
    assert checked.ending is guards.Ending.CHOICE
    assert [p.label for p in checked.prompts] == ["Tell me about this"]
    assert "dropped a technique button: this turn declines or retires an offer" in checked.notes


def stages(*pairs: tuple[str, str]) -> TechniqueState:
    return TechniqueState(
        technique="abcde", step="activate",
        stages=[StageReport(stage=stage, status=status) for stage, status in pairs],
    )


RUNNING = {"framework_running": True, "current_framework_id": "abcde", "current_phase": "activate"}


def test_reported_stages_are_kept_by_id_with_their_status(staged_registry):
    checked = check(staged_registry, reply(state=stages(
        ("activate", "known"), ("belief", "partial"), ("consequence", "missing"),
    )), **RUNNING)
    assert checked.stages == {
        "activate": StageStatus.KNOWN, "belief": StageStatus.PARTIAL, "consequence": StageStatus.MISSING,
    }
    assert checked.notes == []


def test_a_status_is_normalised_like_a_response_shape(staged_registry):
    checked = check(staged_registry, reply(state=stages(("activate", " Known "))), **RUNNING)
    assert checked.stages == {"activate": StageStatus.KNOWN}


def test_a_stage_listed_twice_takes_its_last_entry(staged_registry):
    checked = check(staged_registry, reply(state=stages(
        ("belief", "known"), ("belief", "missing"),
    )), **RUNNING)
    assert checked.stages == {"belief": StageStatus.MISSING}


@pytest.mark.parametrize(
    ("entry", "reason"),
    [
        (("closing", "known"), "not a stage of the framework"),
        (("offering", "known"), "not a stage of the framework"),
        (("somatic_checkin", "known"), "not a stage of the framework"),
        (("invented", "known"), "not a stage of the framework"),
        (("belief", "passed"), "status not on the list"),
        (("belief", "Done"), "status not on the list"),
    ],
)
def test_a_stage_report_that_cannot_be_stored_costs_the_entry_and_leaves_a_note_with_only_the_reason(
    staged_registry, entry, reason
):
    checked = check(staged_registry, reply(state=stages(("activate", "known"), entry)), **RUNNING)
    assert checked.stages == {"activate": StageStatus.KNOWN}
    assert checked.notes == [f"dropped a stage report: {reason}"]


def test_no_reported_stages_is_none_not_empty(staged_registry):
    checked = check(staged_registry, reply(state=TechniqueState(technique="abcde", step="activate")), **RUNNING)
    assert checked.stages is None


def test_stages_in_a_state_that_is_ignored_are_dropped_with_it():
    registry = Registry([STAGED, REFRAMING])
    other = reply(state=TechniqueState(
        technique="thought_reframing", step="surface",
        stages=[StageReport(stage="surface", status="known")],
    ))
    assert check(registry, other, **RUNNING).stages is None
    unknown = reply(state=TechniqueState(
        technique="somatic_release", step="offering",
        stages=[StageReport(stage="activate", status="known")],
    ))
    assert check(registry, unknown, **RUNNING).stages is None
