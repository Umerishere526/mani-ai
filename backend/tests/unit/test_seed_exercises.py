# ABOUTME: Checks the committed exercise manifest before anything is uploaded from it.
# ABOUTME: Every entry must have its own id and file and a library category the app shows.

import pytest
from pydantic import ValidationError

from scripts.seed_exercises import ExerciseCategory, ManifestEntry, load_manifest


def test_every_manifest_entry_has_its_own_file_and_a_known_category():
    entries = load_manifest()

    assert len(entries) == 30
    assert len({e.id for e in entries}) == len({e.filename for e in entries}) == 30
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
