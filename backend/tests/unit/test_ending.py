# ABOUTME: Checks the body ending helpers: the check in word for word, the practice for a place, the returning reply.
# ABOUTME: Pure functions on the client's own words, so each case is a plain assertion.

from mani.chat import ending

CHECK_IN = ("Before we move on, let's check in. What are you noticing in your body right now "
            "compared with when we started?")


def test_the_body_check_in_is_sent_word_for_word():
    """The client: the somatic flow follows the supplied script exactly, never reworded. Mani's
    reflection stays; its own version of the question gives way to the script's."""
    reworded = "You can wait without deciding what it means. How does your body feel now?"
    assert ending.with_the_check_in(reworded, CHECK_IN) == (
        f"You can wait without deciding what it means.\n\n{CHECK_IN}"
    )


def test_a_check_in_already_word_for_word_is_left_alone():
    exact = f"You can wait without deciding what it means. {CHECK_IN}"
    assert ending.with_the_check_in(exact, CHECK_IN) == exact


def test_the_place_a_person_names_is_read_from_their_own_words():
    assert ending.named_place("Chest") == "Chest"
    assert ending.named_place("my stomach is in knots") == "Stomach"
    assert ending.named_place("ahoulder") is None
    assert ending.named_place("my shoulders") == "Somewhere else"
    assert ending.named_place("idk") is None


def test_declining_or_knowing_what_to_do_is_told_apart_from_not_knowing_where():
    assert ending.declines_or_acts("not now")
    assert ending.declines_or_acts("No")
    assert ending.declines_or_acts("I'm going to call her")
    assert not ending.declines_or_acts("idk")
    assert not ending.declines_or_acts("no idea where")


def test_a_practice_is_the_clients_words_for_the_place_in_the_style_being_spoken():
    stage = {"if_unclear": [
        {"when": "they feel it in the chest",
         "reply": {"supportive": "Supportive chest.", "direct": "Direct chest.", "reflective": "Reflective\nchest."}},
        {"when": "they feel it somewhere else", "reply": "Bring gentle attention."},
        {"when": "they have not said where they feel it", "reply": "Where?", "prompts": ["Chest"]},
    ]}
    assert ending.practice_for(stage, "Chest", "direct") == ("Direct chest.", [])
    assert ending.practice_for(stage, "Chest", "reflective")[0] == "Reflective\nchest."
    assert ending.practice_for(stage, "Somewhere else", "supportive")[0] == "Bring gentle attention."
    assert ending.practice_for(stage, "Head", "direct") is None
    assert ending.practice_in(stage, "Hmm. Direct chest. Fine.", "direct")
    assert not ending.practice_in(stage, "Hmm. Direct chest. Fine.", "supportive")
    assert not ending.practice_in(stage, "Where?", "direct")


def test_a_feeling_that_comes_back_is_told_from_one_that_only_eased():
    assert ending.comes_back("I feel calmer for a second, then it comes back")
    assert ending.comes_back("it came back again")
    assert not ending.comes_back("I feel calmer now")


def test_the_acknowledgement_before_a_question_is_the_replys_first_sentence():
    text = "It is okay not to know where. Try bringing gentle attention there. Where is it?"
    assert ending.first_sentence(text) == "It is okay not to know where."
    assert ending.first_sentence("No full stop here") == "No full stop here"
