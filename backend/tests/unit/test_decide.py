# ABOUTME: What code does with the turn's reply: which offer is made or refused, how far a framework moves, when it
# ABOUTME: finishes or is declined, and which buttons the person sees. The model's text is never touched here.

from mani.chat.decide import decide, stage_of
from mani.chat.reply import Safety, TurnReply
from mani.chat.taps import TapEvent
from mani.models.rows import TechniqueOutcome
from tests.unit.frameworks import REGISTRY, THREAD, offered, running

ABCDE = REGISTRY.get("abcde")


def reply(**fields) -> TurnReply:
    return TurnReply(**{"text": "Mani's words.", "safety": Safety(level="none"), "notes": "n", **fields})


def decided(answer: TurnReply, **given):
    base = dict(thread_id=THREAD, running=None, open_offer=None, tap=TapEvent(), record={}, guarded=False,
                count_after=8, end_check_due=False, end_check_asked=False, person_messages=5)
    return decide(answer, REGISTRY, **{**base, **given})


def labels(decision) -> list[str]:
    return [p.label for p in decision.prompts]


def test_an_offer_while_a_framework_runs_is_refused_and_shows_no_buttons():
    d = decided(reply(action="offer", framework="abcde"), running=running("abcde", "belief"))
    assert d.prompts == [] and d.refused == "offer"


def test_an_offer_of_a_declined_framework_is_refused():
    d = decided(reply(action="offer", framework="abcde"), record={"declined": ["abcde"]})
    assert d.prompts == [] and d.refused == "offer"


def test_an_offer_of_an_unknown_framework_is_refused():
    d = decided(reply(action="offer", framework="made_up"))
    assert d.prompts == [] and d.refused == "offer" and d.technique is None


def test_an_offer_while_a_safety_worry_is_open_is_refused():
    d = decided(reply(action="offer", framework="abcde"), guarded=True)
    assert d.prompts == [] and d.refused == "offer"


def test_a_clear_offer_is_the_lead_in_with_the_clients_three_buttons():
    d = decided(reply(action="offer", framework="abcde"))
    assert labels(d) == ["Not sure", "Show me how", "Give me a tool"]
    assert d.technique.outcome is TechniqueOutcome.OFFERED and d.technique.phase == "offering"


def test_a_stage_two_ahead_is_held_to_the_next_one():
    d = decided(reply(stage="consequence"), running=running("abcde", "activate"))
    assert d.technique.phase == "belief"


def test_a_stage_from_another_framework_leaves_the_phase_unchanged():
    d = decided(reply(stage="painful"), running=running("abcde", "activate"))
    assert d.technique is None and d.prompts == []


def test_the_starting_turn_opens_the_first_stage_only():
    """The client's sequence asks every letter on its own reply, even one the chat already touched."""
    tap = TapEvent(starting=ABCDE)
    assert decided(reply(stage="belief"), open_offer=offered("abcde", "steps"), tap=tap).technique.phase == "activate"
    assert decided(reply(stage="dispute"), open_offer=offered("abcde", "steps"), tap=tap).technique.phase == "activate"


def test_a_typed_yes_that_opens_the_first_stage_starts_the_framework():
    d = decided(reply(stage="activate"), open_offer=offered("abcde", "steps"))
    assert d.technique.outcome is TechniqueOutcome.ACCEPTED and d.technique.phase == "activate"


def test_finish_before_the_last_stage_is_ignored():
    d = decided(reply(action="finish", stage="dispute"), running=running("abcde", "dispute"))
    assert d.finished == [] and d.prompts == [] and not d.retire_technique


def test_finish_on_the_last_stage_opens_the_feelings_check_and_finishes_nothing_yet():
    """The client's sequence document, 2026-11-18: after E, how they feel now, with her three buttons."""
    d = decided(reply(action="finish", stage="effective"), running=running("abcde", "effective"))
    assert labels(d) == ["Stronger", "More focused", "Still a bit tired"] and d.technique.phase == "feelings_check"
    assert d.finished == [] and not d.retire_technique


def test_any_answer_to_the_feelings_check_closes_the_set_with_the_closing_buttons():
    for answer in (reply(), reply(action="finish"), reply(stage="effective")):
        d = decided(answer, running=running("abcde", "feelings_check"))
        assert labels(d) == ["Keep Chatting", "Go to Library", "Finish for Now"] and d.finished == ["abcde"] and d.retire_technique


def test_a_guarded_turn_leaves_the_feelings_check_open():
    d = decided(reply(), running=running("abcde", "feelings_check"), guarded=True)
    assert (d.technique, d.finished, d.prompts) == (None, [], [])


def test_finish_after_danger_asks_the_safety_question_first():
    d = decided(reply(action="finish", stage="effective"), running=running("abcde", "effective"), end_check_due=True)
    assert d.end_check and d.prompts == [] and d.finished == [] and not d.retire_technique


def test_after_the_safety_question_a_settled_answer_closes_the_framework():
    d = decided(reply(action="finish", stage="effective"), running=running("abcde", "effective"),
                end_check_due=True, end_check_asked=True)
    assert labels(d) == ["Stronger", "More focused", "Still a bit tired"] and d.technique.phase == "feelings_check" and not d.end_check


def test_stop_records_the_framework_declined():
    d = decided(reply(action="stop"), running=running("abcde", "belief"))
    assert d.declined == ["abcde"] and d.technique.outcome is TechniqueOutcome.DECLINED and d.technique.phase is None


def test_talk_more_first_sets_the_offer_aside_for_now_and_never_declines_it():
    d = decided(reply(), open_offer=offered("abcde", "steps"), tap=TapEvent(set_aside=True))
    assert d.retire_technique and d.declined == [] and d.technique is None


def test_a_settled_answer_to_the_safety_question_closes_the_framework_whatever_the_action():
    """The final review, 2026-11-18: "i'm okay now" with a plain reply left the set on its last stage, no closing
    buttons, and the safety question still marked asked. The old turn closed it on the settled answer alone."""
    d = decided(reply(), running=running("abcde", "effective"), end_check_due=True, end_check_asked=True)
    assert labels(d) == ["Stronger", "More focused", "Still a bit tired"] and d.technique.phase == "feelings_check"


def test_any_other_reply_to_an_open_offer_lets_it_lapse():
    d = decided(reply(), open_offer=offered("abcde", "steps"))
    assert d.retire_technique and d.declined == [] and d.technique is None


def test_a_guarded_turn_changes_no_framework_state():
    d = decided(reply(stage="consequence", action="stop"), running=running("abcde", "belief"), guarded=True)
    assert (d.technique, d.retire_technique, d.declined, d.finished, d.prompts) == (None, False, [], [], [])


def test_library_shows_the_go_to_library_button():
    d = decided(reply(action="library"))
    assert labels(d) == ["Go to Library"] and d.prompts[0].library == "home"


def test_stage_of_reads_only_the_frameworks_own_stages():
    assert stage_of(ABCDE, "made_up", "activate") is None
    assert stage_of(ABCDE, "belief", "activate") == "belief"


def test_a_typed_reply_to_the_lead_in_gets_the_five_steps_and_the_start_buttons():
    """muhammad, 2026-11-18: most people type an answer to the lead-in's question; it gets the reply, then the steps."""
    d = decided(reply(), open_offer=offered("abcde"), count_after=6)
    assert d.show_steps.id == "abcde" and labels(d) == ["Start ABCDE", "I need an example", "Talk more first"]
    assert d.technique.outcome is TechniqueOutcome.OFFERED and d.technique.phase == "steps" and d.declined == []


def test_a_clear_no_to_the_lead_in_declines_the_set():
    d = decided(reply(action="stop"), open_offer=offered("abcde"))
    assert d.declined == ["abcde"] and d.show_steps is None and d.technique.outcome is TechniqueOutcome.DECLINED


def test_a_guarded_turn_at_either_step_of_the_offer_moves_nothing():
    for phase in ("offering", "steps"):
        d = decided(reply(), open_offer=offered("abcde", phase), guarded=True)
        assert (d.show_steps, d.technique, d.retire_technique, d.prompts) == (None, None, False, []), phase


def test_a_lead_in_that_is_no_longer_the_last_reply_lapses_instead_of_showing_the_steps():
    """The final review, 2026-11-18: after a safety exchange, the first ordinary message got the five steps pushed."""
    stale = offered("abcde").model_copy(update={"at_message_count": 4})
    d = decided(reply(), open_offer=stale, count_after=10)
    assert d.show_steps is None and d.retire_technique and d.prompts == []
    fresh = offered("abcde").model_copy(update={"at_message_count": 8})
    assert decided(reply(), open_offer=fresh, count_after=10).show_steps.id == "abcde"


def test_no_offer_before_their_third_message():
    """muhammad, 2026-11-18: the same opening offered on the 2nd message one run and the 3rd the next."""
    for early in (1, 2):
        d = decided(reply(action="offer", framework="abcde"), person_messages=early)
        assert d.refused == "offer" and d.prompts == [] and d.technique is None, early
    assert labels(decided(reply(action="offer", framework="abcde"), person_messages=3)) == [
        "Not sure", "Show me how", "Give me a tool"]


def test_an_offer_the_model_made_on_a_correction_keeps_its_buttons():
    """Code cannot unsay a lead-in already written, so refusing it would leave the words with no buttons and no offer."""
    d = decided(reply(action="offer", framework="abcde", corrected=True), person_messages=5)
    assert d.refused is None and labels(d) == ["Not sure", "Show me how", "Give me a tool"]


def test_a_correction_inside_a_set_still_moves_the_stage():
    d = decided(reply(stage="belief", corrected=True), running=running("abcde", "activate"))
    assert d.technique.phase == "belief"


def test_the_floor_never_closes_an_offer_already_made():
    d = decided(reply(), open_offer=offered("abcde"), count_after=6, person_messages=1)
    assert d.show_steps.id == "abcde"
