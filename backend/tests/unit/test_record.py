# ABOUTME: The thread record a turn keeps: Mani's notes, the people and events, and the frameworks declined or finished,
# ABOUTME: merged onto what is there so the safety keys the pause rules read are never lost, and kept within bounds.

from mani.chat.record import (
    EVENTS_KEPT, LINE_CHARS, PEOPLE_KEPT, declined, events, finished, people, with_outcomes,
)


def test_outcomes_merge_onto_the_record_and_keep_the_safety_keys():
    record = {"notes": "a", "danger_reached": True}
    after = with_outcomes(record, notes=None, people=[], events=[], declined=["abcde"], finished=[])
    assert after == {"notes": "a", "danger_reached": True, "people": [], "events": [], "declined": ["abcde"],
                     "finished": []}


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
