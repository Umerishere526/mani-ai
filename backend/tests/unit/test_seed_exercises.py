# ABOUTME: Checks the committed exercise manifest before anything is uploaded from it.
# ABOUTME: Every entry must have its own id, the client's description and a topic; Workplace Challenges collects others.

import pytest
from pydantic import ValidationError

from mani.llm.schema import LibrarySection
from scripts.seed_exercises import ManifestEntry, ManifestTopic, load_manifest, load_topics, topic_links

ENTRY = {
    "id": "4847c6ce-b2cd-46c4-a918-dd2c185237e0", "filename": "x.mp3", "title": "X", "description": "",
    "type": "Breathing", "category": "Anxiety", "displayOrder": 0, "showOnHomeScreen": False, "durationMinutes": 1.0,
}


def test_every_manifest_entry_has_its_own_id_and_every_recording_its_own_file_and_length():
    entries = load_manifest()
    recorded = [e for e in entries if e.filename is not None]

    assert (len(entries), len(recorded)) == (67, 31), "the client's list: 67 items, 31 of them recorded"
    assert len({e.id for e in entries}) == 67
    assert len({e.filename for e in recorded}) == 31
    assert all(e.duration_minutes > 0 for e in recorded)
    assert all(e.category in set(LibrarySection) for e in entries)


def test_an_entry_with_an_unknown_category_is_refused():
    with pytest.raises(ValidationError):
        ManifestEntry.model_validate({**ENTRY, "category": "Sleeep"})


def test_a_recording_needs_its_length_and_an_unrecorded_item_has_neither():
    assert ManifestEntry.model_validate({**ENTRY, "filename": None, "durationMinutes": None}).filename is None
    for broken in ({"durationMinutes": None}, {"filename": None}):
        with pytest.raises(ValidationError):
            ManifestEntry.model_validate({**ENTRY, **broken})


def test_every_exercise_carries_the_clients_description_where_she_wrote_one():
    undescribed = {e.title for e in load_manifest() if not e.description.strip()}

    # Her document lists these two under Sleep and gives neither a description.
    assert undescribed == {"Insomnia Relaxation", "Fall Asleep Fast"}


def test_every_category_is_a_topic_and_every_topic_but_workplace_challenges_has_her_blurb():
    topics = load_topics()

    assert {t.id for t in topics} == set(LibrarySection)
    assert len({t.id for t in topics}) == len(topics)
    assert {t.title for t in topics if not t.blurb.strip()} == {"Workplace Challenges"}


def test_workplace_challenges_lists_seven_other_topics_exercises_under_their_subcategories():
    topics, entries = load_topics(), load_manifest()
    links = topic_links(topics, entries)
    sleep = [e.id for e in sorted(entries, key=lambda e: e.display_order) if e.category == LibrarySection.SLEEP]

    assert {k.topic_id for k in links} == {LibrarySection.WORKPLACE_CHALLENGES}
    assert [k.exercise_id for k in links if k.subcategory == "Sleep Difficulties"] == sleep
    assert len({k.subcategory for k in links}) == 7
    assert [k.display_order for k in links] == list(range(len(links)))


def test_a_topic_cannot_collect_its_own_exercises():
    with pytest.raises(ValidationError):
        ManifestTopic.model_validate({
            "id": "Stress", "title": "Stress", "blurb": "", "displayOrder": 0,
            "collects": [{"subcategory": "Stress", "topic": "Stress"}],
        })
