# ABOUTME: Checks how each turn's report merges into Mani's picture of the person, shared by chat and frameworks.
# ABOUTME: What is new is gathered, what is wrong is dropped, the focus moves with them, and a stall is counted.

from mani.chat import picture
from mani.llm.schema import BeliefEntry, FeelingEntry, PictureUpdate, RiskEntry

BROTHER = {
    "focus": "your brother in hospital",
    "situations": ["your brother broke his leg"],
    "feelings": [{"feeling": "guilty"}],
    "beliefs": [{"belief": "work will stop you leaving", "kind": "thought"}],
}


def test_what_their_message_adds_is_gathered_once_and_what_was_stored_is_left_untouched():
    before = {key: (list(value) if isinstance(value, list) else value) for key, value in BROTHER.items()}
    after = picture.merge(BROTHER, PictureUpdate(
        situations=["Your brother  broke his leg", "you are the only developer"],
        feelings=[FeelingEntry(feeling="Guilty", about="not being with him"), FeelingEntry(feeling="ashamed")],
        beliefs=[BeliefEntry(belief="you're a bad brother", kind="thought")],
        wants="to be with him", shift="adds",
    ))
    assert after["situations"] == ["your brother broke his leg", "you are the only developer"]
    assert after["feelings"] == [{"feeling": "guilty", "about": "not being with him"}, {"feeling": "ashamed"}]
    assert [b["belief"] for b in after["beliefs"]] == ["work will stop you leaving", "you're a bad brother"]
    assert after["wants"] == "to be with him"
    assert BROTHER == before, "the stored picture is never changed in place"


def test_what_they_say_is_wrong_is_dropped():
    after = picture.merge(BROTHER, PictureUpdate(drop=["Work will stop you leaving"], shift="corrects"))
    assert "beliefs" not in after
    assert after["shift"] == "corrects"


def test_what_is_really_happening_is_kept_apart_from_what_they_tell_themselves():
    """The coworker review (2026-10-27): a real problem was questioned as a belief."""
    after = picture.merge({}, PictureUpdate(beliefs=[
        BeliefEntry(belief="she falls asleep with the children there", kind="happening"),
        BeliefEntry(belief="it all falls on you", kind="THOUGHT"),
        BeliefEntry(belief="unreadable", kind="maybe"),
    ], risks=[RiskEntry(risk="children unsupervised", to="others"), RiskEntry(risk="x", to="nobody")]))
    assert after["beliefs"] == [
        {"belief": "she falls asleep with the children there", "kind": "happening"},
        {"belief": "it all falls on you", "kind": "thought"},
    ]
    assert after["risks"] == [{"risk": "children unsupervised", "to": "others"}]
    line = picture.render(after)
    assert "what they say is really happening: she falls asleep with the children there" in line
    assert "what they tell themselves: it all falls on you" in line
    assert "risks to others: children unsupervised" in line


def test_the_focus_moves_to_a_new_situation_and_back_keeping_the_earlier_one():
    moved = picture.merge(BROTHER, PictureUpdate(focus="your sister's loan", shift="new_issue"))
    assert moved["focus"] == "your sister's loan" and moved["earlier"] == ["your brother in hospital"]
    back = picture.merge(moved, PictureUpdate(focus="your brother in hospital", shift="back"))
    assert back["focus"] == "your brother in hospital" and back["earlier"] == ["your sister's loan"]
    reworded = picture.merge(BROTHER, PictureUpdate(focus="your brother's broken leg", shift="adds"))
    assert reworded["focus"] == "your brother's broken leg" and "earlier" not in reworded


def test_messages_that_add_nothing_are_counted_until_one_does():
    once = picture.merge(BROTHER, PictureUpdate(shift="nothing_new"))
    twice = picture.merge(once, PictureUpdate(shift="nothing_new"))
    assert (once["quiet"], twice["quiet"]) == (1, 2)
    assert picture.merge(twice, PictureUpdate(shift="adds", wants="to visit him"))["quiet"] == 0
    assert picture.merge(twice, PictureUpdate(shift="sideways")).get("quiet") == 2, "an off-list shift changes nothing"


def test_a_long_list_keeps_what_they_came_with_and_the_latest():
    after = picture.merge({}, PictureUpdate(situations=[f"thing {n}" for n in range(20)]))
    assert len(after["situations"]) == picture.LIST_LIMIT
    assert after["situations"][0] == "thing 0" and after["situations"][-1] == "thing 19"


def test_an_empty_picture_renders_as_nothing_and_a_null_report_keeps_it():
    assert picture.render({}) is None and picture.render(None) is None
    assert picture.merge(BROTHER, None) == BROTHER
    assert picture.added_beliefs(BROTHER, picture.merge(BROTHER, None)) == []


def test_what_a_turn_added_is_read_for_the_framework():
    after = picture.merge(BROTHER, PictureUpdate(
        beliefs=[BeliefEntry(belief="you're a bad brother", kind="thought"),
                 BeliefEntry(belief="the deadline is real", kind="happening")],
        feelings=[FeelingEntry(feeling="ashamed", about="leaving him alone")],
    ))
    assert picture.added_beliefs(BROTHER, after) == ["you're a bad brother"]
    assert picture.added_feelings(BROTHER, after) == ["ashamed about leaving him alone"]
