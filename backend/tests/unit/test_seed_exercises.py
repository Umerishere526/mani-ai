# ABOUTME: Checks the committed exercise manifest before anything is uploaded from it.
# ABOUTME: Every entry must have its own id and file, the client's description, and a topic the app shows.

import pytest
from pydantic import ValidationError

from scripts.seed_exercises import ExerciseCategory, ManifestEntry, load_manifest, load_topics


def test_every_manifest_entry_has_its_own_file_and_a_known_category():
    entries = load_manifest()

    assert len(entries) == 31
    assert len({e.id for e in entries}) == len({e.filename for e in entries}) == 31
    for entry in entries:
        assert entry.category in set(ExerciseCategory)
        assert entry.duration_minutes > 0


def test_an_entry_with_an_unknown_category_is_refused():
    with pytest.raises(ValidationError):
        ManifestEntry.model_validate({
            "id": "4847c6ce-b2cd-46c4-a918-dd2c185237e0", "filename": "x.mp3", "title": "X",
            "description": "", "type": "Breathing", "category": "Sleeep", "displayOrder": 0,
            "showOnHomeScreen": False, "durationMinutes": 1.0,
        })


def test_every_exercise_carries_the_clients_description():
    assert [e.title for e in load_manifest() if not e.description.strip()] == []


def test_every_category_in_the_manifest_is_a_topic_with_the_clients_blurb():
    topics = load_topics()

    assert len({t.id for t in topics}) == len(topics)
    assert {e.category for e in load_manifest()} <= {t.id for t in topics}
    assert all(t.blurb.strip() for t in topics)
