# ABOUTME: Checks the few things code does to a reply's words: dashes replaced, a title tidied, and the client's
# ABOUTME: buttons under an offer.

import pytest

from mani.chat import repairs


def test_a_long_title_is_trimmed_not_rejected():
    """The schema capped this at 50 and failed the whole generation over it."""
    title = repairs.clean_title(
        '  "Talking through a really long and rambling worry about work, and then some more about home and family."  ')
    assert title.startswith("Talking through")
    assert not title.endswith(".")
    assert len(title) <= repairs.MAX_TITLE_LENGTH
    assert repairs.clean_title('  "" ') is None


def test_the_offer_carries_the_clients_three_buttons_and_once_told_more_the_other_two():
    buttons = repairs.offer_buttons("abcde", explained=False)
    assert [(p.label, p.technique, bool(p.decline)) for p in buttons] == [
        ("Try it", "abcde", False), ("Tell me more", None, False), ("Keep chatting", None, True),
    ]
    assert [p.label for p in repairs.offer_buttons("abcde", explained=True)] == ["Try it", "Keep chatting"]


@pytest.mark.parametrize(("draft", "sent"), [
    # The client's own example (2026-10-30): a list after the dash keeps it one sentence.
    ("When that anxious feeling starts, where does your mind usually go first—unfinished responsibilities, "
     "someone you care about, or something else?",
     "When that anxious feeling starts, where does your mind usually go first, unfinished responsibilities, "
     "someone you care about, or something else?"),
    # A sentence of its own after the dash becomes its own sentence.
    ("You weren't asked—you were told what would happen.", "You weren't asked. You were told what would happen."),
    ("That sounds hard — it's a lot to carry on your own.", "That sounds hard. It's a lot to carry on your own."),
    # An aside between two dashes reads between two commas.
    ("Your friends—the ones from school—still call you.", "Your friends, the ones from school, still call you."),
    ("It's frustrating—especially after a year of waiting.", "It's frustrating, especially after a year of waiting."),
    ("You keep going – and nothing changes.", "You keep going, and nothing changes."),
    # Short words after the dash stay in the sentence.
    ("Mostly work—maybe also family?", "Mostly work, maybe also family?"),
    # A dash at the end becomes a full stop.
    ("I'm not sure—", "I'm not sure."),
    # Hyphens and number ranges are not dashes.
    ("A well-known self-check, pages 3–5.", "A well-known self-check, pages 3–5."),
    ("Nothing to change here.", "Nothing to change here."),
])
def test_dashes_are_taken_out_of_what_mani_says(draft, sent):
    """The client, 2026-10-30 and 2026-11-03: no dashes in Mani's replies. The prompt asks for none, and code takes out
    any that still come."""
    assert repairs.without_dashes(draft) == sent
    assert "\u2014" not in repairs.without_dashes(draft)
