# ABOUTME: Checks what code enforces on a reply before the person receives it: each of the client's rules that code can
# ABOUTME: read, the event it records, and that a guarded turn's safety words are never cut.

import pytest

from mani.chat import crisis, enforce
from mani.chat.techniques import line_of, stages_of
from tests.unit.frameworks import REGISTRY


def sent(text: str, ask: str = "", *, fixed: bool = False, guarded: bool = False, open_chat: bool = True,
         latest: str = "answer", directive: bool = False, helping: bool = False,
         openers: tuple[str, ...] = (), offered: str | None = None, stage: str | None = None) -> enforce.Sent:
    return enforce.sent(text, ask, fixed=fixed, guarded=guarded, open_chat=open_chat, latest=latest,
                        directive=directive, helping=helping, openers=list(openers),
                        offered=REGISTRY.get(offered), stage=stage)


def test_a_guarded_reply_whose_text_already_asks_its_question_asks_it_once():
    """TC-13 (2026-11-25): a guarded turn joined the text and the chosen question, and both held the same question."""
    reply = sent("Okay. That's clear.\n\nHow long has it been like this for you?",
                 "How long has it been like this for you?", guarded=True, open_chat=False)
    assert reply.text == "Okay. That's clear.\n\nHow long has it been like this for you?"
    assert reply.asked == "How long has it been like this for you?"
    assert reply.enforced == [enforce.REPEATED_QUESTION]


def test_a_nearly_identical_question_counts_as_the_same_and_a_different_one_is_kept():
    assert enforce.repeats("Numb is a lot. How long has it been like this?", "How long has it been like this for you?")
    assert not enforce.repeats("How are you?", "How are you feeling about your sister now?")
    reply = sent("That sounds frightening. Are you hurt?", "Is anyone with you right now?", guarded=True,
                 open_chat=False, latest="other")
    assert reply.text == "That sounds frightening. Are you hurt?\n\nIs anyone with you right now?"


@pytest.mark.parametrize(("written", "received"), [
    # The words the eval and suite runs caught (2026-11-25).
    ("Two words, and they land hard.", "Two words, and they hit hard."),
    ("When was the last time someone noticed you were struggling?",
     "When was the last time someone noticed you were finding it hard?"),
    ("Broken nights add up. Give yourself some space.", "Hurt nights add up. Give yourself some room."),
    # An article before the word still fits the plain word.
    ("That's an unhealthy loop, and a flawed plan.", "That's an unhelpful loop, and an imperfect plan."),
    # Every form of a word (manasa 2026-11-25; muhammad's TC-M runs the same day).
    ("Neither was made with a work trip landing on that weekend in mind.",
     "Neither was made with a work trip falling on that weekend in mind."),
    ("A weekend that landed on you both by accident.", "A weekend that fell on you both by accident."),
    ("Fix the process first, then the feature.", "Repair the process first, then the feature."),
    ("So you asked for a specific fix.", "So you asked for a specific repair."),
    ("How is that landing?", "How is that hitting?"),
])
def test_a_forbidden_word_reaches_them_as_a_plain_word(written, received):
    """Behavioral Framework: the forbidden words never appear in a Mani response; the prompt alone let 7 of 158 eval
    replies through."""
    reply = sent(written)
    assert reply.text == received and not enforce.forbidden_words(reply.text)


def test_each_swap_is_recorded_with_its_word_and_the_chosen_question_is_swapped_too():
    reply = sent("They land hard.", "What does stability look like for you?")
    assert reply.text == "They hit hard.\n\nWhat does steadiness look like for you?"
    assert reply.enforced == ["forbidden_word:land", "forbidden_word:stability"]


def test_a_banned_line_is_taken_out_unless_it_is_all_the_reply_says_or_it_names_help_on_a_guarded_turn():
    """Safety Guardrails section 6: lines Mani never says, cut on crisis turns too (CR-6, manasa 2026-11-25), except a
    sentence that also names where to get help. PROVISIONAL: clinician sign-off required before deploy."""
    reply = sent("I'm here for you. That week sounds long.", "What happened on Friday?")
    assert reply.text == "That week sounds long.\n\nWhat happened on Friday?"
    assert reply.enforced == [enforce.BANNED_LINE_REMOVED]
    alone = sent("You’re not alone.")
    assert alone.text == "You’re not alone." and alone.enforced == [enforce.BANNED_LINE_KEPT]
    guarded = sent("I'm not going anywhere. Please call 988 now.", guarded=True, open_chat=False)
    assert guarded.text == "Please call 988 now."
    assert guarded.enforced == [enforce.BANNED_LINE_REMOVED]
    with_help = sent("You're not alone, call 988 now.", guarded=True, open_chat=False)
    assert with_help.text == "You're not alone, call 988 now."
    assert with_help.enforced == [enforce.BANNED_LINE_KEPT]


@pytest.mark.parametrize("line", [
    "I'm not going anywhere.", "I'm still here with you.", "I'll be here when you come back.", "I’m here with you.",
    "What you're carrying is heavier than I can hold on my own.", "This is more than I can hold.",
])
def test_a_presence_or_burden_line_is_taken_out(line):
    """CR-6, manasa's crisis test (2026-11-25): "heavier than I can hold" made the person a burden, and "I'm not going
    anywhere" promised a presence Mani cannot give. PROVISIONAL: clinician sign-off required before deploy."""
    reply = sent(f"{line} That week sounds long.", "What happened on Friday?")
    assert reply.text == "That week sounds long.\n\nWhat happened on Friday?"
    assert reply.enforced == [enforce.BANNED_LINE_REMOVED]


def test_codes_fixed_safety_words_go_out_untouched():
    reply = sent(f"Your chat is on hold. There's space.\n\n{crisis.END_CHECK}", fixed=True, guarded=True,
                 open_chat=False)
    assert "space" in reply.text and reply.enforced == []


@pytest.mark.parametrize(("message", "stop"), [
    ("I'm done", True), ("Yes, I'm done for now.", True), ("that’s all, thanks", True), ("ok bye!", True),
    ("enough for today", True), ("I have to go", True), ("let's stop here. thank you", True), ("im good for now", True),
    # A stop phrase inside something else they are telling Mani is not a wish to stop.
    ("I'm done with my job", False), ("bye, she said, and left", False), ("I have to go to work tomorrow", False),
    ("thanks", False),
])
def test_a_typed_stop_is_only_a_message_that_says_nothing_but_stop(message, stop):
    assert enforce.typed_stop(message) is stop


def test_a_typed_stop_the_model_missed_is_read_as_one_but_never_on_a_guarded_turn():
    """Eval rule-typed-done 3/3 and TC-17 asked "what do you mean by done?" (R95)."""
    from mani.chat.reply import Question, Safety, TurnReply

    reply = TurnReply(text="Okay.", safety=Safety(level="none"), notes="",
                      question=Question(latest="other", ask="What do you mean by done?"))
    read, events = enforce.read_stop(reply, "I'm done", guarded=False)
    assert read.question.latest == "wants_to_stop" and events == [enforce.TYPED_STOP]
    assert reply.question.latest == "other"
    kept, events = enforce.read_stop(reply, "I'm done", guarded=True)
    assert kept is reply and events == []


def test_a_long_directive_reply_keeps_its_first_sentences_and_its_question():
    """Directive is two or three short sentences (mani.md); 7 eval replies ran to 4 or 5."""
    reply = sent("A job you believe in can still cost too much. You've said it twice now. That matters. It keeps "
                 "coming back.", "When you picture it staying like this, what feels hardest?", directive=True)
    assert reply.text == ("A job you believe in can still cost too much. You've said it twice now.\n\n"
                          "When you picture it staying like this, what feels hardest?")
    assert reply.enforced == [enforce.DIRECTIVE_TRIMMED]


@pytest.mark.parametrize(("text", "ask", "why"), [
    ("One. Two. Three. Four.", "So what would you try first?", "the question leans on what would be cut"),
    ("Try this:\n1. Write it down.\n2. Read it back.\n3. Say it aloud.", "", "a list"),
    ("You said no. Why did she push? You held it. Then she left.", "", "the question sits inside the text"),
])
def test_a_long_directive_reply_that_would_not_read_whole_goes_out_as_written(text, ask, why):
    reply = sent(text, ask, directive=True)
    assert enforce.DIRECTIVE_TRIMMED not in reply.enforced and reply.enforced == [enforce.DIRECTIVE_LONG_KEPT], why


def test_the_directive_cap_leaves_help_other_styles_sets_and_guarded_turns_alone():
    long = "One thing. Two things. Three things. Four things."
    for kept in (sent(long, directive=True, helping=True), sent(long), sent(long, directive=True, open_chat=False),
                 sent(long, directive=True, guarded=True, open_chat=False)):
        assert kept.text == long and kept.enforced == []


def test_a_repeated_stock_opening_is_dropped_when_what_follows_still_stands():
    """Pacing Rules and R116: validation varied across turns, never the same phrases (the 'parrot' feel)."""
    reply = sent("That makes sense. The week piled up on you.", "What happened on Friday?",
                 openers=("That makes sense. The",))
    assert reply.text == "The week piled up on you.\n\nWhat happened on Friday?"
    assert reply.enforced == [enforce.OPENER_DROPPED]


@pytest.mark.parametrize(("text", "guarded"), [
    ("That makes sense to me, given how long you've waited for this.", False),   # too long to be a stock opening
    ("That makes sense. So you left early.", False),                            # the next one leans on it
    ("That really makes sense.", False),                                        # nothing follows it
    ("That makes sense. Please call 988 now.", True),                           # a guarded turn keeps every word
])
def test_a_repeated_opening_that_cannot_go_safely_stays_and_is_recorded(text, guarded):
    reply = sent(text, guarded=guarded, open_chat=not guarded,
                 openers=("Okay.", "That makes sense to", "That makes sense. So", "That really makes sense",
                          "That makes sense. Please"))
    assert reply.text == text and reply.enforced == [enforce.OPENER_REPEATED_KEPT]


def test_an_opening_used_before_only_in_part_is_not_a_repeat():
    reply = sent("That makes sense. The week piled up.", openers=("That makes things worse",))
    assert reply.enforced == []


def test_a_chosen_question_that_asks_two_reaches_them_as_its_first():
    """At most one question per reply (Pacing Rules); 2 eval replies still asked two."""
    reply = sent("That week sounds long.", "When you say done, what do you mean? Done with the job, or with her?")
    assert reply.text == "That week sounds long.\n\nWhen you say done, what do you mean?"
    assert reply.asked == "When you say done, what do you mean?"
    assert reply.enforced == [enforce.SECOND_QUESTION_REMOVED]


def test_a_guarded_turn_keeps_both_its_questions_and_records_them():
    reply = sent("That sounds frightening. Are you hurt?", "Is anyone with you right now?", guarded=True,
                 open_chat=False)
    assert reply.text == "That sounds frightening. Are you hurt?\n\nIs anyone with you right now?"
    assert reply.enforced == [enforce.SECOND_QUESTION_KEPT]


def test_a_figurative_phrase_is_recorded_and_the_text_goes_out_as_written():
    """Manasa, 2026-11-25: "its own kind of ache", "a strange shape" and "the loop" read as constructed, not talked."""
    written = "Not knowing is its own kind of ache. And The Loop is complete then."
    reply = sent(written)
    assert reply.text == written
    assert reply.enforced == ["figurative:its own kind of", "figurative:the loop"]
    assert sent("Not knowing why is hard.").enforced == []


@pytest.mark.parametrize("written", [
    "This weekend is the second kind.",
    "That's the part with the weight in it, not the weekend itself.",
    "Then the belief stands on what you've seen.",
    "You're not deciding between a trip and a birthday.",
    "This is really about being left out.",
    # muhammad's tester, Directive (2026-11-25).
    "Those aren't the same kind of thing, which is part of why it's stuck.",
    "Settled dates make it a straight choice, and you've already said which one you want.",
    "You're not stuck on information.",
    "So what's stopping you isn't the facts.",
    "The logistics aren't what's holding this up. It's the thought of what they'd make of you.",
    "With nothing coming back, your mind fills in the gap.",
])
def test_a_reading_said_as_fact_is_recorded_and_the_text_goes_out_as_written(written):
    """manasa (2026-11-25) and muhammad's tester: assumptions presented as facts. Each is one of muhammad's local test
    replies; code counts them for the eval and the trace, and the prompt is the fix."""
    reply = sent(written)
    assert reply.text == written
    assert any(event.startswith(f"{enforce.INTERPRETIVE}:") for event in reply.enforced)


def test_a_reading_put_as_the_question_or_their_own_words_pointed_back_is_not_recorded():
    reply = sent("The promise you made her keeps coming up.", "How much of this is about feeling left out?")
    assert not any(event.startswith(f"{enforce.INTERPRETIVE}:") for event in reply.enforced)


def test_every_stage_line_of_every_set_is_read_as_one():
    for framework_id in REGISTRY.ids:
        framework = REGISTRY.get(framework_id)
        for stage in stages_of(framework):
            assert enforce.STAGE_LINE.match(line_of(framework, stage)), (framework_id, stage)


def test_a_reply_at_the_offer_loses_the_stage_it_began_and_its_question():
    """Manasa's Reflective Chat 2 (2026-11-25): Step 1 came with the steps, and again after she said yes."""
    reply = sent("That's clearer. Step 1 is Identify the Thought. What goes through your head as you text her?",
                 "What goes through your head?", open_chat=False, offered="thought_reframe")
    assert reply.text == "That's clearer." and reply.asked == ""
    assert reply.enforced == [enforce.STAGE_IN_OFFER]
    staged = sent("Let's look at one moment.", "What happened the last time?", open_chat=False, offered="abcde",
                  stage="activate")
    assert staged.text == "Let's look at one moment." and staged.enforced == [enforce.STAGE_IN_OFFER]


def test_an_offer_that_begins_no_stage_goes_out_as_written_and_a_stage_alone_is_kept():
    lead_in = sent("ABCDE could help you walk into the review calmer.", open_chat=False, offered="abcde")
    assert lead_in.text == "ABCDE could help you walk into the review calmer." and lead_in.enforced == []
    alone = sent("A is for Activating Event.", open_chat=False, offered="abcde")
    assert alone.text == "A is for Activating Event." and alone.enforced == [enforce.STAGE_IN_OFFER_KEPT]
    running = sent("A is for Activating Event.", "What happened?", open_chat=False, stage="activate")
    assert running.asked == "What happened?" and running.enforced == []


@pytest.mark.parametrize("draft", [
    'Polite but firm:\n\n"Hi [name], I reported it on [date]. Could you confirm a repair date by Friday? Thanks, [your name]"',
    "Here's a draft.\n\nSubject: Pay review\n\nHi Sam,\n\nI'd like to talk about my pay.\n\nCould we find 30 minutes "
    "this week?\n\nThanks,\n[Your name]",
])
def test_a_question_inside_wording_written_for_them_stays_and_is_not_mani_asking(draft):
    """muhammad's Directive run (2026-11-25): the text to the landlord and the raise email were cut at the question
    the message itself asks, because code took it for a second question of Mani's."""
    reply = sent(draft, "How long do you want to give him?")
    assert reply.text == f"{draft}\n\nHow long do you want to give him?"
    assert reply.asked == "How long do you want to give him?"
    assert sent("That sounds hard. What happened then? How did you feel?").text == "That sounds hard. How did you feel?"


def test_wording_written_for_them_keeps_its_words_and_is_never_cut_short():
    """The 2026-11-25 Directive run (TC-29): the text to the landlord came back with "broken" swapped for "hurt" and
    cut after its first sentence by the Directive trim."""
    draft = ('Here it is.\n\n"Hi [name], the heating has been broken for three weeks. I have asked twice. Please '
             'arrange the repair this week. Can you confirm a date? Thanks, [you]"')
    reply = sent(draft, directive=True)
    assert reply.text == draft and reply.enforced == []
    assert enforce.forbidden_in_own_words(draft) == []
    assert enforce.forbidden_in_own_words("Broken nights add up.") == ["broken"]
