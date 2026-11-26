# ABOUTME: Checks "What Mani knows" shows every part of the thread record the backend sends in debug: notes, people,
# ABOUTME: events, the replies ledger with each question and its answer, and the frameworks declined or finished.

from __future__ import annotations

import understanding_view

# A record as backend/mani/chat/record.py keeps it.
RECORD = {
    "notes": "pushover at work",
    "people": [{"called": "Sam", "relation": "manager", "told": "keeps adding tasks"},
               {"called": "Mum", "relation": "", "told": ""}],
    "events": [{"what": "review on Friday", "when": "upcoming"}],
    "replies": [
        {"q": "What did Sam say?", "intent": "event", "open_chat": True, "move": "reflect", "gist": "named the load",
         "opens": "That sounds like a", "answer": "stay late again"},
        {"q": "", "intent": "", "open_chat": False, "move": "help", "gist": "offered ABCDE", "opens": "Would you like"},
    ],
    "declined": ["thought_reframe"],
    "finished": ["abcde"],
    "worry_about": "themselves",
}


def test_every_part_of_the_record_gets_its_own_lines():
    assert understanding_view.lines(RECORD) == [
        "**Notes:** pushover at work",
        "**People:**", "- Sam (manager): keeps adding tasks", "- Mum",
        "**Events:**", "- upcoming: review on Friday",
        "**Replies, oldest first:**",
        "- reflect - named the load · asked (event, open chat): What did Sam say? → stay late again",
        "- help - offered ABCDE",
        "**Declined:** thought_reframe",
        "**Finished:** abcde",
    ]


def test_an_empty_record_shows_nothing():
    """The safety keys alone are not shown here: the turn's trace has them."""
    assert understanding_view.lines({}) == []
    assert understanding_view.lines({"people": [], "events": [], "replies": [], "worry_about": "body"}) == []
