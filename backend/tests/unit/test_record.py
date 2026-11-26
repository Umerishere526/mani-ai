# ABOUTME: The thread record a turn keeps: Mani's notes, the people and events, and the frameworks declined or finished,
# ABOUTME: and what each reply asked and gave, merged onto what is there so the safety keys are kept, within bounds.

from mani.chat.record import (
    EVENTS_KEPT, LINE_CHARS, PEOPLE_KEPT, REPLIES_KEPT, declined, events, finished, library, people, replies,
    with_outcomes,
    with_answer, with_reply,
)


def test_outcomes_merge_onto_the_record_and_keep_the_safety_keys():
    record = {"notes": "a", "danger_reached": True}
    after = with_outcomes(record, notes=None, people=[], events=[], declined=["abcde"], finished=[])
    assert after == {"notes": "a", "danger_reached": True, "people": [], "events": [], "declined": ["abcde"],
                     "finished": []}


def test_a_library_section_is_kept_until_a_reply_names_another():
    kept = with_outcomes({"library": "Sleep"}, notes=None, people=[], events=[], declined=[], finished=[])
    assert library(kept) == "Sleep"
    assert library(with_outcomes(kept, notes=None, people=[], events=[], declined=[], finished=[],
                                 library="Stress")) == "Stress"


def test_new_notes_replace_the_old_ones():
    assert with_outcomes({"notes": "a"}, notes="b", people=[], events=[], declined=[], finished=[])["notes"] == "b"


def test_a_record_with_nothing_declined_or_finished_reads_as_empty_lists():
    assert declined({}) == [] and finished({}) == []
    assert declined({"declined": ["abcde"]}) == ["abcde"]


def test_the_people_and_events_given_replace_the_stored_ones_within_their_bounds():
    stored = {"people": [{"called": "my mum", "relation": "mother", "told": "calls daily"}]}
    given = [{"called": f"p{i}", "relation": "friend", "told": "x" * 500} for i in range(PEOPLE_KEPT + 3)]
    after = with_outcomes(stored, notes="n", people=given, events=[], declined=[], finished=[])
    kept = people(after)
    assert [p["called"] for p in kept] == [f"p{i}" for i in range(3, PEOPLE_KEPT + 3)], "the latest are kept"
    assert all(len(p["told"]) <= LINE_CHARS for p in kept)


def test_an_event_keeps_its_when_and_one_with_no_words_or_an_odd_when_is_not_kept_as_given():
    given = ([{"what": "Thanksgiving alone this Thursday", "when": "upcoming"}, {"what": "  ", "when": "past"},
              {"what": "argued with Sam", "when": "yesterday"}]
             + [{"what": f"e{i}", "when": "past"} for i in range(EVENTS_KEPT)])
    kept = events(with_outcomes({}, notes="n", people=[], events=given[:3], declined=[], finished=[]))
    assert kept == [{"what": "Thanksgiving alone this Thursday", "when": "upcoming"},
                    {"what": "argued with Sam", "when": "unsaid"}]
    assert len(events(with_outcomes({}, notes="n", people=[], events=given, declined=[], finished=[]))) == EVENTS_KEPT


def test_each_reply_is_kept_with_its_move_gist_and_opening_words_and_only_the_latest_are_kept():
    record = {"danger_reached": True}
    for i in range(REPLIES_KEPT + 2):
        record = with_reply(record, question=f"Q{i}?", intent="feeling", open_chat=True, move="Reflect",
                            gist=f"g{i}", text=f"That sounds really hard, {i}. Q{i}?")
    kept = replies(record)
    assert len(kept) == REPLIES_KEPT and kept[0]["q"] == "Q2?" and record["danger_reached"] is True
    assert kept[-1] == {"q": f"Q{REPLIES_KEPT + 1}?", "intent": "feeling", "open_chat": True, "move": "reflect",
                        "gist": f"g{REPLIES_KEPT + 1}", "opens": "That sounds really hard"}


def test_a_move_outside_the_six_is_kept_as_other():
    after = with_reply({}, question="", intent="none", open_chat=False, move="console", gist="", text="Okay.")
    assert replies(after)[0]["move"] == "other" and replies(after)[0]["opens"] == "Okay"


def test_an_answer_lands_on_the_last_reply_s_question_once_and_never_on_a_reply_that_asked_nothing():
    asked = with_reply({}, question="What did he say?", intent="situation", open_chat=True, move="reflect", gist="",
                       text="What did he say?")
    answered = with_answer(asked, "said I'm lazy")
    assert replies(answered)[-1]["answer"] == "said I'm lazy"
    assert replies(with_answer(answered, "something else"))[-1]["answer"] == "said I'm lazy"
    assert with_answer(asked, "") == asked
    silent = with_reply({}, question="", intent="none", open_chat=True, move="reassure", gist="", text="Okay.")
    assert with_answer(silent, "yes") == silent
