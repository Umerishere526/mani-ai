# ABOUTME: Checks the feeling word measure the evals and the style counts use: whose word a feeling is.
# ABOUTME: Pure functions over text; measurement only, so nothing here changes a reply.

from scripts.wording import introduced_feelings


def test_stressful_is_a_feeling_word_nobody_may_introduce():
    drafted = "An exam in 24 hours sounds incredibly stressful. What do you need to focus on first?"
    said = "i've an exam in 24 hours and i don't know where to start"
    assert introduced_feelings(drafted, said) == ["stressful"]
    assert introduced_feelings(drafted, said + " it is stressful") == []


def test_a_plain_form_of_their_own_feeling_word_is_theirs_but_another_feeling_is_not():
    said = "i'm sad and lonely and stressed about it"
    assert introduced_feelings("The loneliness and the sadness and the stress.", said) == []
    assert introduced_feelings("That sounds overwhelming and stressful.", said) == ["overwhelming"]


def test_a_misspelling_of_their_feeling_word_is_their_word():
    """"emberessed" and "embarrased" were typed; Mani spelling it right did not introduce it."""
    said = "i felt emberessed and just wanted to disappear. i felt embarrased"
    assert introduced_feelings("It is understandable to feel embarrassed. That embarrassment is real.", said) == []
    assert introduced_feelings("That must feel stressful.", "i am mad about it") == ["stressful"]
    assert introduced_feelings("You sound sad.", "i am mad about it") == ["sad"]


def test_the_first_typo_alone_is_enough_to_make_the_right_spelling_theirs():
    """Only "emberessed" had been typed when Mani first said "embarrassed"."""
    said = "i felt emberessed and i didn't know how to handle my emotions"
    assert introduced_feelings("That sounds embarrassing, and you felt embarrassed.", said) == []
    assert introduced_feelings("You felt helpless.", "i feel hopeless") == ["helpless"]
