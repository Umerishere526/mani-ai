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
                count_after=8, end_check_due=False, end_check_asked=False)
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


def test_a_clear_offer_shows_try_it_tell_me_more_and_keep_chatting():
    d = decided(reply(action="offer", framework="abcde"))
    assert labels(d) == ["Try it", "Tell me more", "Keep chatting"]
    assert d.technique.outcome is TechniqueOutcome.OFFERED and d.technique.phase == "offering"


def test_a_stage_two_ahead_is_held_to_the_next_one():
    d = decided(reply(stage="consequence"), running=running("abcde", "activate"))
    assert d.technique.phase == "belief"


def test_a_stage_from_another_framework_leaves_the_phase_unchanged():
    d = decided(reply(stage="painful"), running=running("abcde", "activate"))
    assert d.technique is None and d.prompts == []


def test_the_starting_turn_may_reach_the_second_stage_and_no_further():
    tap = TapEvent(starting=ABCDE)
    assert decided(reply(stage="belief"), open_offer=offered("abcde"), tap=tap).technique.phase == "belief"
    assert decided(reply(stage="dispute"), open_offer=offered("abcde"), tap=tap).technique.phase == "belief"


def test_a_typed_yes_that_opens_the_first_stage_starts_the_framework():
    d = decided(reply(stage="activate"), open_offer=offered("abcde"))
    assert d.technique.outcome is TechniqueOutcome.ACCEPTED and d.technique.phase == "activate"


def test_finish_before_the_last_stage_is_ignored():
    d = decided(reply(action="finish", stage="dispute"), running=running("abcde", "dispute"))
    assert d.finished == [] and d.prompts == [] and not d.retire_technique


def test_finish_on_the_last_stage_shows_the_closing_buttons_and_records_it_finished():
    d = decided(reply(action="finish", stage="effective"), running=running("abcde", "effective"))
    assert labels(d) == ["Keep Chatting", "Go to Library", "Finish for Now"]
    assert d.finished == ["abcde"] and d.retire_technique


def test_finish_after_danger_asks_the_safety_question_first():
    d = decided(reply(action="finish", stage="effective"), running=running("abcde", "effective"), end_check_due=True)
    assert d.end_check and d.prompts == [] and d.finished == [] and not d.retire_technique


def test_after_the_safety_question_a_settled_answer_closes_the_framework():
    d = decided(reply(action="finish", stage="effective"), running=running("abcde", "effective"),
                end_check_due=True, end_check_asked=True)
    assert d.finished == ["abcde"] and labels(d)[-1] == "Finish for Now" and not d.end_check


def test_stop_records_the_framework_declined():
    d = decided(reply(action="stop"), running=running("abcde", "belief"))
    assert d.declined == ["abcde"] and d.technique.outcome is TechniqueOutcome.DECLINED and d.technique.phase is None


def test_keep_chatting_on_an_offer_records_it_declined():
    d = decided(reply(), open_offer=offered("abcde"), tap=TapEvent(declined=True))
    assert d.declined == ["abcde"] and d.technique.outcome is TechniqueOutcome.DECLINED


def test_a_settled_answer_to_the_safety_question_closes_the_framework_whatever_the_action():
    """The final review, 2026-11-18: "i'm okay now" with a plain reply left the set on its last stage, no closing
    buttons, and the safety question still marked asked. The old turn closed it on the settled answer alone."""
    d = decided(reply(), running=running("abcde", "effective"), end_check_due=True, end_check_asked=True)
    assert d.finished == ["abcde"] and labels(d)[-1] == "Finish for Now" and d.retire_technique


def test_any_other_reply_to_an_open_offer_lets_it_lapse():
    d = decided(reply(), open_offer=offered("abcde"))
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
