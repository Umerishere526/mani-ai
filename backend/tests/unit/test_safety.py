# ABOUTME: Checks how the model's judgment of each message moves a conversation's safety state: a refusal never
# ABOUTME: lowers a concern, only the model raises one to danger, and a body symptom is danger unless it stopped.

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


def test_only_the_model_raises_a_concern_about_a_person_to_danger_and_only_none_lowers_it():
    """Production, 2026-11-20: an answer the model judged unsure was held as danger because Mani had already asked, and
    the next sad message paused the chat. Unsure stays unsure; danger the model judged about a person is lowered only
    by a judgment of none of that same worry. A symptom in the body, or a danger of no known kind, follows the
    judgment."""
    for about in ("themselves", "someone_else", "from_someone"):
        assert after(State.UNSURE, "unsure", False, about=about) is State.UNSURE, about
        assert after(State.DANGER, "unsure", False, about=about, danger_about=about) is State.DANGER, about
        assert after(State.DANGER, "unsure", False, about=about) is State.DANGER, "a danger of unknown kind holds"
        assert after(State.DANGER, "none", False, about=about) is State.CLEAR, "a step toward safety settles it"
        assert after(State.UNSURE, "none", False, about=about) is State.CLEAR, "they explained"
    assert after(State.DANGER, "unsure", False, about="themselves", danger_about="body") is State.UNSURE, (
        "chest pain, then \"I wish I weren't here\": the body danger does not hold the new worry")
    for about in ("body", None):
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


def test_a_body_worry_that_has_not_stopped_is_danger_now():
    """muhammad, 2026-11-18: a possible medical emergency gets "call emergency services now" every time, no exceptions,
    and over-triggering is accepted. MiniMax held "my chest is tight and painful right now and my left arm feels weird"
    at unsure in 7 of 30 runs that day. Only their word that it stopped holds it below danger."""
    assert danger_of("now", "body", "yes") == "now"
    assert danger_of("now", "body", "unsaid") == "now"
    assert danger_of("unsure", "body", "unsaid") == "now"
    assert danger_of("unsure", "body", None) == "now"
    assert danger_of("now", "body", "no") == "unsure", "they said it stopped"
    assert danger_of("none", "body", "unsaid") == "none"
    assert danger_of("now", "themselves", None) == "now"


def test_a_settled_symptom_reopens_only_when_their_newest_message_says_it_is_happening():
    """The stroke chat, baseline of 2026-11-11: help was called and it settled; "I am afraid of losing him" was read as
    danger now from the father's symptoms earlier in the conversation, and safety flipped back with nothing new said."""
    assert danger_of("now", "body", "yes", reopening=True) == "now"
    assert danger_of("now", "body", "unsaid", reopening=True) == "none"
    assert danger_of("unsure", "body", None, reopening=True) == "none"
    assert danger_of("now", "themselves", None, reopening=True) == "now", "only a symptom in the body waits for their word"
    assert danger_of("now", "body", "unsaid") == "now", "a worry that never settled gets the number"
