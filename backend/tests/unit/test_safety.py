# ABOUTME: Checks how the model's judgment of each message moves a conversation's safety state: a refusal never
# ABOUTME: lowers a concern, a person's worry is asked about once, and a body symptom is danger only when happening now.

from mani.chat.safety import State, after, danger_of


def test_the_models_judgment_moves_the_state():
    """muhammad, 2026-11-10: the model reads the whole conversation and judges whether anyone is in danger now. "I mean
    my workplace" and "my friend is with me and stops me" settle a concern because they show no one is."""
    assert after(State.CLEAR, "now", False) is State.DANGER
    assert after(State.CLEAR, "unsure", False) is State.UNSURE
    assert after(State.UNSURE, "none", False) is State.CLEAR
    assert after(State.DANGER, "none", False) is State.CLEAR, "handled now: away from him, a friend with him"
    assert after(State.DANGER, "unsure", False) is State.UNSURE
    assert after(State.UNSURE, None, False) is State.UNSURE, "a reply that judged nothing leaves it as it was"


def test_a_concern_about_a_person_is_asked_about_once_and_then_held_as_danger():
    """muhammad, 2026-11-16: no safety question after safety question (the client's safety test, seven in a row). Once
    Mani has asked what they meant, an answer that still leaves it unsure is held as danger, so the reply says how to
    reach help and asks nothing more about it; from there only a judgment of none lowers it. A symptom in the body, or
    a danger of no known kind, follows the judgment as before."""
    for about in ("themselves", "someone_else", "from_someone"):
        assert after(State.UNSURE, "unsure", False, about=about, asked=True) is State.DANGER, about
        assert after(State.DANGER, "unsure", False, about=about) is State.DANGER, about
        assert after(State.DANGER, "none", False, about=about) is State.CLEAR, "a step toward safety settles it"
        assert after(State.UNSURE, "none", False, about=about, asked=True) is State.CLEAR, "they explained"
        assert after(State.UNSURE, "unsure", False, about=about) is State.UNSURE, "first sight: Mani has not asked yet"
    for about in ("body", None):
        assert after(State.UNSURE, "unsure", False, about=about, asked=True) is State.UNSURE, about
        assert after(State.DANGER, "unsure", False, about=about) is State.UNSURE, about


def test_a_refusal_never_settles_a_concern():
    """manasa's safety test, 2026-11-06: each time she pushed back, Mani agreed to drop the question and went back to
    chatting."""
    assert after(State.UNSURE, "none", True) is State.UNSURE
    assert after(State.DANGER, "none", True) is State.DANGER
    assert after(State.DANGER, "now", True) is State.DANGER
    assert after(State.CLEAR, "none", True) is State.CLEAR, "nothing was open to keep"


def test_a_refusal_never_lowers_a_concern_not_even_from_danger_to_unsure():
    """The review of 2026-11-10: someone in danger who said "stop asking" lost the danger instruction, because a
    refusal only blocked clearing. A refusal holds the concern where it stands, whatever the model judges."""
    assert after(State.DANGER, "unsure", True) is State.DANGER
    assert after(State.DANGER, "none", True) is State.DANGER
    assert after(State.UNSURE, "unsure", True) is State.UNSURE
    assert after(State.UNSURE, "now", True) is State.DANGER, "a refusal never holds back a rise"
    assert after(State.DANGER, "unsure", False) is State.UNSURE, "answered, then lowered by the judgment"


def test_a_judgment_code_does_not_know_never_clears_a_concern():
    """A reply that judged nothing, or one in words outside the closed set, changes nothing."""
    assert after(State.UNSURE, None, False) is State.UNSURE
    assert after(State.DANGER, "mostly fine", False) is State.DANGER


def test_a_symptom_in_the_body_is_danger_only_when_they_said_it_is_happening_now():
    """Lolly's chest chat, replayed 2026-11-11: "the pain is in my chest a tightening feeling" was read as happening now,
    and Mani told her to call the emergency number four times. Not said is unsure, which asks."""
    assert danger_of("now", "body", "yes") == "now"
    assert danger_of("now", "body", "unsaid") == "unsure"
    assert danger_of("now", "body", None) == "unsure"
    assert danger_of("now", "body", "no") == "unsure"
    assert danger_of("now", "themselves", None) == "now", "only a symptom in the body waits for their word"
    assert danger_of("none", "body", None) == "none"


def test_a_settled_symptom_reopens_only_when_their_newest_message_says_it_is_happening():
    """The stroke chat, baseline of 2026-11-11: help was called and it settled; "I am afraid of losing him" was read as
    danger now from the father's symptoms earlier in the conversation, and safety flipped back with nothing new said."""
    assert danger_of("now", "body", "yes", reopening=True) == "now"
    assert danger_of("now", "body", "unsaid", reopening=True) == "none"
    assert danger_of("unsure", "body", None, reopening=True) == "none"
    assert danger_of("now", "themselves", None, reopening=True) == "now", "only a symptom in the body waits for their word"
    assert danger_of("now", "body", "unsaid") == "unsure", "a concern that never settled still asks"
