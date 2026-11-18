# ABOUTME: The thread record a turn keeps: Mani's notes and the frameworks declined or finished, merged onto what is
# ABOUTME: there so the safety keys the pause rules read are never lost.

from mani.chat.record import declined, finished, with_outcomes


def test_outcomes_merge_onto_the_record_and_keep_the_safety_keys():
    record = {"notes": "a", "danger_reached": True}
    after = with_outcomes(record, notes=None, declined=["abcde"], finished=[])
    assert after == {"notes": "a", "danger_reached": True, "declined": ["abcde"], "finished": []}


def test_new_notes_replace_the_old_ones():
    assert with_outcomes({"notes": "a"}, notes="b", declined=[], finished=[])["notes"] == "b"


def test_a_record_with_nothing_declined_or_finished_reads_as_empty_lists():
    assert declined({}) == [] and finished({}) == []
    assert declined({"declined": ["abcde"]}) == ["abcde"]
