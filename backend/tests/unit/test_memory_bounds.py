# ABOUTME: Checks what the model returns for a person's memory is cut to the tuned limits.
# ABOUTME: Builds the memory from fake lists, so no model call or database is needed.

from mani import memory
from mani.llm.schema import Memory
from tests.seeded import seeded_tuning


def long_memory() -> Memory:
    fields = Memory.model_fields
    return Memory.model_validate({name: [f"{name} one", " ", f"{name} two", "x" * 300] for name in fields})


def test_each_list_is_cut_to_the_tuned_number_of_entries_and_characters():
    tuned = seeded_tuning(memory={"max_entries": 2, "max_entry_chars": 5}).memory

    bounded = memory.bounded(long_memory(), tuned).model_dump()

    assert all(len(entries) == 2 and all(len(e) <= 5 for e in entries) for entries in bounded.values())


def test_the_seeded_limits_keep_six_entries_of_a_hundred_and_sixty_characters():
    seeded = seeded_tuning().memory
    many = Memory.model_validate({name: ["y" * 300] * 10 for name in Memory.model_fields})

    bounded = memory.bounded(many, seeded).model_dump()

    assert all(len(entries) == 6 and all(len(e) == 160 for e in entries) for entries in bounded.values())
