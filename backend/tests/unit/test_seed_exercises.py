# ABOUTME: Checks the committed exercise manifest before anything is uploaded from it.
# ABOUTME: Every entry must name a real audio file and a library section the app knows.

import pytest
from pydantic import ValidationError

from mani.llm.schema import LibrarySection
from scripts.seed_exercises import EXERCISES_DIR, ManifestEntry, load_manifest


def test_every_manifest_entry_names_a_real_file_and_a_known_section():
    entries = load_manifest()

    assert len(entries) == 18
    assert len({e.id for e in entries}) == len({e.filename for e in entries}) == 18
    for entry in entries:
        assert (EXERCISES_DIR / entry.filename).is_file(), entry.filename
        assert entry.category in set(LibrarySection)
        assert entry.duration_minutes > 0
    assert {e.category for e in entries if e.show_on_home_screen} == {LibrarySection.HOME}


def test_an_entry_with_an_unknown_section_is_refused():
    with pytest.raises(ValidationError):
        ManifestEntry.model_validate({
            "id": "4847c6ce-b2cd-46c4-a918-dd2c185237e0", "filename": "x.mp3", "title": "X",
            "description": "", "type": "Breathing", "category": "Sleep", "displayOrder": 0,
            "showOnHomeScreen": False, "durationMinutes": 1.0,
        })
