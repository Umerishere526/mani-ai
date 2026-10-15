# ABOUTME: Checks which drafted replies are asked for again, and for what reason.
# ABOUTME: Each reason is a rule about the person or the cadence, so each is a plain test.

import pytest

from mani.chat import redraft
from mani.chat.techniques import Registry
from mani.llm.schema import Reply, SmartPrompt, StageKnown, TechniqueState
from mani.models.rows import Framework


def registry() -> Registry:
    return Registry([
        Framework(
            id="behavioral_activation", name="Behavioral Activation", summary="s", body="b",
            phases=["offering"], activation={"never_offer_when_said": ["died"]},
        ),
        Framework(
            id="act_choice_point", name="ACT Choice Point", summary="s", body="b",
            phases=["offering"], activation={},
        ),
    ])


# Mani's earlier replies as the offer gate wants to find them: one of them said what Mani made
# of their situation, in its own words, and they answered it. Tests about anything other than
# that gate pass these, so the gate is satisfied and the reason under test is the one returned.
SAID_UNDERSTANDING = [
    "What has been happening?",
    (
        "So your own work stalls whenever somebody else misses their part, and you are the one "
        "left explaining it. Have I got that right?"
    ),
]


def offer(technique: str, understanding_said: str | None = "earlier") -> Reply:
    return Reply(
        text="There are some questions we could go through. Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique=technique), SmartPrompt(label="Keep chatting", decline=True)],
        understanding_said=understanding_said,
    )


def stages() -> Registry:
    return Registry([Framework(
        id="abcde", name="ABCDE", summary="s", body="b",
        phases=["offering", "activate", "belief", "consequence", "closing"],
    )])


def at(step: str | None) -> Reply:
    return Reply(
        text="What changed first?",
        state=None if step is None else TechniqueState(technique="abcde", step=step),
    )


def ledger(*entries: tuple[str, bool], step: str | None) -> Reply:
    return Reply(
        text="What did it come to mean for you?",
        stages_known=[StageKnown(stage=s, known="their words" if met else None, met=met)
                      for s, met in entries],
        state=None if step is None else TechniqueState(technique="abcde", step=step),
    )


def test_a_draft_that_asks_the_first_stage_its_ledger_leaves_open_stands():
    """muhammad, 2026-10-09: what the conversation already holds answers stages; the reply asks the
    first one it does not, and says so in stages_known."""
    starting = redraft.StageInForce("abcde", "activate", asked=False)
    draft = ledger(("activate", True), ("belief", True), ("consequence", False), step="consequence")
    assert redraft.reasons(draft, [], stages(), offer_not_allowed=False, stage_in_force=starting) == []


def test_a_draft_whose_step_disagrees_with_its_own_ledger_is_redrafted():
    starting = redraft.StageInForce("abcde", "activate", asked=False)
    stayed = ledger(("activate", True), ("belief", False), step="activate")
    jumped = ledger(("activate", True), ("belief", False), step="consequence")
    for draft in (stayed, jumped):
        reasons = redraft.reasons(draft, [], stages(), offer_not_allowed=False, stage_in_force=starting)
        assert len(reasons) == 1 and "belief is the first stage not yet answered" in reasons[0]


def test_the_closing_is_asked_even_when_the_ledger_calls_it_met():
    """The closing is theirs to answer, so it is skipped only once it has been asked."""
    framework = stages().get("abcde")
    walk = ledger(("consequence", True), ("closing", True), step="closing")
    not_asked = redraft.StageInForce("abcde", "consequence", asked=True)
    assert redraft.ledger_stage(walk, framework, not_asked) == "closing"
    asked = redraft.StageInForce("abcde", "closing", asked=True)
    assert redraft.ledger_stage(ledger(("closing", True), step="closing"), framework, asked) is None


def test_a_draft_with_no_ledger_is_not_judged_by_one():
    starting = redraft.StageInForce("abcde", "activate", asked=False)
    assert redraft.reasons(at("consequence"), [], stages(), offer_not_allowed=False,
                           stage_in_force=starting) == []


def test_a_clean_question_stands():
    draft = Reply(text="What is the hardest part of the evenings?")
    assert redraft.reasons(draft, ["i'm lonely"], registry(), offer_not_allowed=False) == []


def test_an_offer_before_the_clients_cadence_allows_it_is_a_reason():
    why = redraft.reasons(offer("act_choice_point"), ["my dog died"], registry(), offer_not_allowed=True,
                            mani_texts=SAID_UNDERSTANDING)
    assert len(why) == 1 and "may not be offered in this reply" in why[0]


def test_an_offer_what_they_said_rules_out_is_a_reason():
    why = redraft.reasons(offer("behavioral_activation"), ["my dog died"], registry(), offer_not_allowed=False,
                            mani_texts=SAID_UNDERSTANDING)
    assert len(why) == 1 and "Behavioral Activation" in why[0]
    assert redraft.ruled_out(offer("behavioral_activation"), ["my dog died"], registry()) == "behavioral_activation"


def test_the_same_offer_is_fine_when_nothing_rules_it_out():
    assert redraft.reasons(offer("behavioral_activation"), ["i stopped answering people"], registry(),
                                   offer_not_allowed=False, mani_texts=SAID_UNDERSTANDING) == []
    assert redraft.ruled_out(offer("act_choice_point"), ["my dog died"], registry()) is None


def test_a_comfort_with_no_question_is_a_reason_before_an_offer():
    comfort = Reply(text="It is okay to feel that way. I am here with you.")
    why = redraft.reasons(comfort, ["i felt small"], registry(), offer_not_allowed=False, needs_question=True)
    assert len(why) == 1 and "asks no question" in why[0]


def test_no_question_is_fine_when_it_is_not_needed():
    """While the questions run, on a safety concern, or when they asked only to be heard."""
    comfort = Reply(text="It is okay to feel that way. I am here with you.")
    assert redraft.reasons(comfort, ["i felt small"], registry(), offer_not_allowed=False, needs_question=False) == []


def test_an_offer_carries_its_own_permission_question():
    assert redraft.reasons(offer("act_choice_point"), ["x"], registry(), offer_not_allowed=False,
                                   needs_question=True, mani_texts=SAID_UNDERSTANDING) == []


FIRST = (
    "It can be hard to choose when everything feels like a big step. Would picking one of these small "
    "actions, opening your laptop to look at one travel destination, browsing a site for one new "
    "learning opportunity, or simply sitting near a window for a few minutes, feel most manageable "
    "to you today?"
)
SAME_AGAIN = (
    "It is okay that you are not sure. Between opening your laptop to look at one travel destination, "
    "browsing for one learning opportunity, or sitting by a window for a few minutes, which one "
    "feels like the most manageable one to start with today?"
)


def test_the_same_choices_asked_again_are_redrafted():
    """Observed: someone who asked Mani to pick got the same three options back, reworded, twice."""
    why = redraft.reasons(
        Reply(text=SAME_AGAIN), [], registry(), offer_not_allowed=False, last_mani_text=FIRST
    )
    assert any("asks the question you asked last turn" in w for w in why)


def test_a_different_question_after_an_answer_is_not_a_repeat():
    moved_on = Reply(text="Opening your laptop to look at one place sounds like a start. When will you do it?")
    assert redraft.reasons(
        moved_on, [], registry(), offer_not_allowed=False, last_mani_text=FIRST
    ) == []


def test_a_draft_that_chose_a_shape_asking_nothing_is_not_asked_for_a_question():
    """Whether someone only wants to be listened to is the model's reading, shown by its shape."""
    from mani.llm.schema import Style

    holding = Reply(text="That has been sitting with you.", style=Style(shape="mirror and hold"))
    asking = Reply(text="That has been sitting with you.", style=Style(shape="mirror and ask"))
    none = Reply(text="That has been sitting with you.")
    for draft, expected in ((holding, []), (asking, 1), (none, 1)):
        found = redraft.reasons(draft, [], registry(), offer_not_allowed=False, needs_question=True)
        assert len(found) == (expected if isinstance(expected, int) else len(expected))


def test_a_ledger_status_and_met_always_agree():
    assert StageKnown(stage="a", met=True).status == "known"
    assert StageKnown(stage="a", known="some", met=False).status == "partial"
    assert StageKnown(stage="a").status == "missing"
    confirm = StageKnown(stage="a", status="confirm", known="a possible event")
    assert confirm.met is False


def test_the_ledger_view_lists_every_stage_with_what_the_reply_does():
    framework = Framework(
        id="abcde", name="ABCDE", summary="s", body="b",
        phases=["offering", "activate", "belief", "consequence", "effective", "somatic_checkin"],
        stages={"activate": {"title": "A: Activating Event"}},
    )
    reply = ledger(("belief", True), ("consequence", False), step="consequence")
    rows = redraft.ledger_view(reply, framework)
    assert [(r["stage"], r["status"]) for r in rows] == [
        ("activate", "done"), ("belief", "known"), ("consequence", "missing"), ("effective", "not_reached"),
    ]
    assert rows[0]["title"] == "A: Activating Event"
    assert rows[1]["action"] == "confirmed by them, gone on from" and rows[2]["asking"] and not rows[1]["asking"]
    assert redraft.ledger_view(Reply(text="x"), framework) == []




def test_a_stage_asked_twice_may_be_left_whatever_the_ledger_says():
    """A person who cannot answer a stage is never asked it a third time (muhammad, 2026-10-12)."""
    stuck = ledger(("belief", False), ("consequence", False), step="consequence")
    twice = redraft.StageInForce("abcde", "belief", asked=True, asks=2)
    once = redraft.StageInForce("abcde", "belief", asked=True, asks=1)
    assert redraft.reasons(stuck, [], stages(), offer_not_allowed=False, stage_in_force=twice) == []
    assert redraft.reasons(stuck, [], stages(), offer_not_allowed=False, stage_in_force=once)


def test_the_closing_is_never_left_unasked_however_often_it_was_asked():
    stays = ledger(("closing", False), step="closing")
    closing = redraft.StageInForce("abcde", "closing", asked=True, asks=5)
    assert redraft.ledger_stage(stays, stages().get("abcde"), closing) == "closing"


def _abcde_view_framework() -> Framework:
    return Framework(
        id="abcde", name="ABCDE", summary="s", body="b",
        phases=["offering", "activate", "belief", "consequence", "dispute", "effective",
                "closing", "somatic_checkin"],
        stages={"activate": {"title": "A"}, "dispute": {"title": "D"}},
    )


def test_a_reply_with_no_ledger_still_shows_where_the_questions_stand():
    rows = redraft.ledger_view(Reply(text="x"), _abcde_view_framework(), "dispute")
    assert [(r["stage"], r["status"]) for r in rows] == [
        ("activate", "done"), ("belief", "done"), ("consequence", "done"),
        ("dispute", "unreported"), ("effective", "not_reached"), ("closing", "not_reached"),
    ]
    assert rows[3]["asking"] and rows[3]["title"] == "D"
    assert redraft.ledger_view(Reply(text="x"), _abcde_view_framework(), "offering") == []


def test_a_ledger_naming_a_stage_that_does_not_exist_still_shows_every_real_stage():
    reply = ledger(("activate", True), ("examine", False), step="belief")
    rows = redraft.ledger_view(reply, _abcde_view_framework())
    assert [r["stage"] for r in rows] == [
        "activate", "belief", "consequence", "dispute", "effective", "closing",
    ]


def test_a_draft_staying_on_a_stage_asked_twice_is_redrafted():
    draft = at("belief")
    twice = redraft.StageInForce("abcde", "belief", asked=True, asks=2)
    once = redraft.StageInForce("abcde", "belief", asked=True, asks=1)
    assert any("twice" in n for n in redraft.reasons(draft, [], stages(), offer_not_allowed=False, stage_in_force=twice))
    assert redraft.reasons(draft, [], stages(), offer_not_allowed=False, stage_in_force=once) == []


def test_an_offer_the_draft_did_not_choose_is_redrafted():
    draft = Reply(text="There's a framework called ABCDE.", next_move="ask",
                  understanding_said="earlier",
                  prompts=[SmartPrompt(label="Try it", technique="act_choice_point")])
    notes = redraft.reasons(draft, ["that's it exactly"], registry(), offer_not_allowed=False,
                            mani_texts=SAID_UNDERSTANDING)
    assert any("next_move" in n for n in notes)


def test_choosing_to_offer_without_the_button_is_redrafted():
    draft = Reply(text="There's a framework called ABCDE that could help.", next_move="offer",
                  understanding_said="earlier")
    notes = redraft.reasons(draft, ["that's it exactly"], registry(), offer_not_allowed=False,
                            may_offer=True, mani_texts=SAID_UNDERSTANDING)
    assert any("Try it" in n for n in notes)


def test_choosing_to_offer_is_not_pressed_when_no_offer_may_be_made():
    draft = Reply(text="What has stayed with you since?", next_move="offer",
                  understanding_said="earlier")
    assert redraft.reasons(draft, ["that's it exactly"], registry(), offer_not_allowed=False,
                           may_offer=False, mani_texts=SAID_UNDERSTANDING) == []


def test_an_acknowledgement_chosen_as_the_move_is_not_asked_for_a_question():
    draft = Reply(text="That landed hard.", next_move="acknowledge")
    assert redraft.reasons(draft, [], registry(), offer_not_allowed=False, needs_question=True) == []


def test_a_draft_with_no_move_and_no_question_still_asks_for_one():
    draft = Reply(text="That landed hard.")
    notes = redraft.reasons(draft, [], registry(), offer_not_allowed=False, needs_question=True)
    assert any("asks no question" in n for n in notes)


# The offer gate: a set of questions waits until Mani has said what it makes of their situation
# and they have answered it. The draft says where that stands; stated_understanding checks the
# part of the claim that Mani's own earlier replies can bear out.

# The conversation that first showed the gap (muhammad, 2026-10-13): two replies that are a few
# words in front of a question, and nothing said about what is going on for them.
ONLY_QUESTIONS = [
    "Something's frustrating you. What's been happening?",
    "It's hard to pin down when it feels like everything. What's been getting to you most today?",
]
THEIR_MESSAGES = ["i am frustrated", "everything", "The client keeps changing requirements."]


def test_a_reply_that_only_leads_into_a_question_has_said_no_understanding():
    """The false positive the gate exists for: the model claims an understanding was put to them
    when every reply so far has been a question with a few words in front of it."""
    assert redraft.stated_understanding(ONLY_QUESTIONS, THEIR_MESSAGES) is False


def test_a_reply_that_says_what_is_going_on_counts():
    said = ONLY_QUESTIONS + SAID_UNDERSTANDING[-1:]
    assert redraft.stated_understanding(said, THEIR_MESSAGES) is True


def test_their_own_words_handed_back_are_not_an_understanding():
    paraphrase = ["So the client keeps changing requirements and that makes your job harder."]
    assert redraft.stated_understanding(paraphrase, THEIR_MESSAGES) is False


def test_nothing_said_yet_is_not_an_understanding():
    assert redraft.stated_understanding([], THEIR_MESSAGES) is False
    assert redraft.stated_understanding(ONLY_QUESTIONS, []) is False


def test_an_offer_claiming_an_understanding_that_was_never_said_is_redrafted():
    notes = redraft.reasons(
        offer("act_choice_point"), THEIR_MESSAGES, registry(), offer_not_allowed=False,
        mani_texts=ONLY_QUESTIONS,
    )
    assert any("said what you make of their situation" in n for n in notes)


@pytest.mark.parametrize("claimed", ["not_yet", "this_reply", None])
def test_an_offer_waits_until_the_draft_says_the_understanding_was_answered(claimed):
    """this_reply is not enough either: a reply that says it and offers in the same breath has
    not given them the chance to answer it."""
    notes = redraft.reasons(
        offer("act_choice_point", understanding_said=claimed), ["that's it exactly"], registry(),
        offer_not_allowed=False, mani_texts=SAID_UNDERSTANDING,
    )
    assert any("said what you make of their situation" in n for n in notes)


def test_an_offer_stands_once_it_was_said_and_answered():
    assert redraft.reasons(
        offer("act_choice_point"), ["that's it exactly"], registry(), offer_not_allowed=False,
        mani_texts=SAID_UNDERSTANDING,
    ) == []


def test_a_reply_that_offers_nothing_is_not_held_to_the_gate():
    draft = Reply(text="What has that been like for you?", understanding_said="not_yet")
    assert redraft.reasons(
        draft, THEIR_MESSAGES, registry(), offer_not_allowed=False, mani_texts=ONLY_QUESTIONS,
    ) == []


def test_a_set_offered_when_they_asked_for_something_is_redrafted():
    """They asked Mani for something, so that is what the reply answers; the set waits."""
    draft = offer("act_choice_point")
    draft = draft.model_copy(update={"next_move": "answer_request"})
    notes = redraft.reasons(
        draft, ["so what should I do about it?"], registry(), offer_not_allowed=False,
        mani_texts=SAID_UNDERSTANDING,
    )
    assert any("answer what they asked" in n for n in notes)


def test_an_earlier_offer_is_not_itself_an_understanding():
    """An offer's own words run long and say nothing about the person, so left in they satisfy
    the gate for the rest of the conversation and the second offer is never checked."""
    offer_text = (
        "There's a framework called ACT Choice Point that helps you identify the thoughts "
        "behind what is happening, question whether they are true, and replace them with more "
        "realistic ones."
    )
    assert redraft.stated_understanding(
        [offer_text], THEIR_MESSAGES, ("ACT Choice Point",)
    ) is False
    # The same words with nothing naming a set still count, so the exclusion is the name only.
    assert redraft.stated_understanding([offer_text], THEIR_MESSAGES, ()) is True


def test_a_stray_offer_move_inside_a_framework_is_not_sent_back_for_an_understanding():
    """may_offer is false while the questions run and on a safety concern. A next_move of offer
    there is nothing the model can act on, and the stage question must not be redrafted away."""
    draft = at("belief").model_copy(update={"next_move": "offer", "understanding_said": "not_yet"})
    assert redraft.reasons(
        draft, THEIR_MESSAGES, stages(), offer_not_allowed=False, may_offer=False,
        mani_texts=ONLY_QUESTIONS,
    ) == []


def test_an_imminent_action_is_offered_without_waiting_to_be_understood():
    """The one offer that cannot wait: a pause before something about to be done."""
    assert redraft.reasons(
        offer("act_choice_point", understanding_said="not_yet"), THEIR_MESSAGES, registry(),
        offer_not_allowed=False, mani_texts=ONLY_QUESTIONS, urgent=True,
    ) == []


def test_a_second_reply_in_a_row_that_asks_nothing_is_asked_again():
    """Reflective ended two replies running on "I don't want to assume." with nothing to answer.
    Choosing to ask nothing is honoured once; the reply after it has to ask something."""
    draft = Reply(text="I don't want to assume.", next_move="acknowledge")
    after_a_question = redraft.reasons(
        draft, THEIR_MESSAGES, registry(), offer_not_allowed=False, needs_question=True,
        last_mani_text="Which part gets to you most?",
    )
    after_no_question = redraft.reasons(
        draft, THEIR_MESSAGES, registry(), offer_not_allowed=False, needs_question=True,
        last_mani_text="That would be frustrating, I may be wrong.",
    )
    assert after_a_question == []
    assert any("asks no question" in n for n in after_no_question)


def _with_unknown(text: str) -> Reply:
    from mani.llm.schema import WorkingRead

    return Reply(text="Which part gets to you most?", working_read=WorkingRead(unknown=text))


def test_a_read_still_wanting_the_same_thing_is_noted_but_not_sent_back():
    """In the scenario run most of these followed "idk", a correction or a request for help: the
    person had not answered, so wanting the same thing was right, and a redraft left it unchanged
    11 times in 17 (muhammad, 2026-10-14)."""
    from mani.llm.schema import WorkingRead

    before = WorkingRead(unknown="whether the frustration is about the fallout or about not being able to rely on people")
    again = _with_unknown("whether the frustration is mostly about the fallout, or not being able to rely on people")
    assert redraft.same_unknown(before, again)
    assert redraft.reasons(
        again, THEIR_MESSAGES, registry(), offer_not_allowed=False, previous_read=before,
    ) == []


def test_a_read_that_has_moved_on_to_something_new_is_left_alone():
    from mani.llm.schema import WorkingRead

    before = WorkingRead(unknown="whether the frustration is about the fallout or about not being able to rely on people")
    moved = _with_unknown("how long it has been this way, and whether anyone above them knows")
    assert redraft.reasons(
        moved, THEIR_MESSAGES, registry(), offer_not_allowed=False, previous_read=before,
    ) == []


def test_a_stored_read_that_is_not_a_read_is_ignored_not_an_error():
    from mani.llm.schema import WorkingRead

    assert WorkingRead.stored("plain text from before the read had slots") is None
    assert WorkingRead.stored(None) is None


def _asking(text: str) -> Reply:
    return Reply(text=text)


def test_a_question_asked_a_few_replies_ago_is_not_asked_again_in_other_words():
    earlier = [
        "That sounds hard. I wonder if several things are adding up, or one is spilling into the rest. Which feels closer?",
        "What has been taking up the most space for you?",
        "I wonder if you feel unheard, or stuck. Which is closer?",
    ]
    again = _asking("Could it be several things adding up, or one thing spilling into the rest? Which feels closer?")
    assert redraft.asks_what_is_known(again, None, earlier) == "an earlier question"
    new = _asking("When people let you down, what do you do next?")
    assert redraft.asks_what_is_known(new, None, earlier) is None


def test_two_questions_that_share_only_how_a_question_is_put_are_different_questions():
    """Seen in the scenario run: a short question shares most of its words with any other that asks
    "what" of "your" something. Over half the earlier-question redrafts were that, and the redraft
    pushed Mani off following what the person had just said."""
    earlier = ["That must have stung. What did your manager do?"]
    follows_them = _asking("Facing them again sounds hard. What are you afraid your colleagues think?")
    assert redraft.asks_what_is_known(follows_them, None, earlier) is None
    again = _asking("That sounds like a lot. What exactly did your manager do?")
    assert redraft.asks_what_is_known(again, None, earlier) == "an earlier question"
    asked_before = ["What has being left out changed in your work?"]
    same = _asking("What has changed in your work since the meetings started?")
    assert redraft.asks_what_is_known(same, None, asked_before) == "an earlier question"


def test_a_question_made_of_what_the_read_already_holds_is_asking_for_what_is_known():
    from mani.llm.schema import WorkingRead

    held = WorkingRead(impact="the team's motivation is dropping and the work keeps slipping")
    asks = _asking("Is the team's motivation dropping and the work slipping?")
    assert redraft.asks_what_is_known(asks, held, []) == "impact"
    other = _asking("Who else knows how the team is doing?")
    assert redraft.asks_what_is_known(other, held, []) is None


def test_a_question_that_adds_one_word_of_its_own_to_the_read_is_a_new_question():
    """Asking whether something they said is still so asks for something they have not said. Only a
    question made wholly of the read's words is asking for what is known."""
    from mani.llm.schema import WorkingRead

    held = WorkingRead(situation="the client keeps changing requirements")
    still = _asking("Is the client still changing requirements?")
    assert redraft.asks_what_is_known(still, held, []) is None


def test_a_repeat_is_sent_back_for_a_new_question_but_not_inside_a_framework():
    from mani.llm.schema import WorkingRead

    held = WorkingRead(response="takes the changes on and rebuilds the whole thing")
    draft = _asking("Do you take the changes on and rebuild the whole thing?")
    notes = redraft.reasons(
        draft, THEIR_MESSAGES, registry(), offer_not_allowed=False, previous_read=held,
        mani_texts=[],
    )
    assert any("already have" in n for n in notes)
    inside = redraft.reasons(
        draft, THEIR_MESSAGES, stages(), offer_not_allowed=False, previous_read=held, mani_texts=[],
        stage_in_force=redraft.StageInForce("abcde", "belief", asked=True, asks=1),
    )
    assert not any("already have" in n for n in inside)


def test_two_replies_in_a_row_that_put_a_choice_are_sent_back_for_an_open_question():
    """Every reply ended on "which feels closer, or is it something else?". A choice is for when
    the answer tells Mani something it needs, so a second one in a row is asked again."""
    choice = _asking("Is it more that things keep going wrong, or that nobody is listening?")
    after_a_choice = redraft.reasons(
        choice, THEIR_MESSAGES, registry(), offer_not_allowed=False,
        last_mani_text="I wonder if it is several things, or one thing spilling over. Which is closer?",
    )
    after_an_open_one = redraft.reasons(
        choice, THEIR_MESSAGES, registry(), offer_not_allowed=False,
        last_mani_text="What has been taking up the most space for you?",
    )
    assert any("put them a choice" in n for n in after_a_choice)
    assert not any("put them a choice" in n for n in after_an_open_one)


def _stage_reply(status: str, step: str = "consequence", **read) -> Reply:
    from mani.llm.schema import WorkingRead

    return Reply(
        text="How has it affected what you feel or do?",
        stages_known=[StageKnown(stage=step, known=None, status=status)],
        state=TechniqueState(technique="abcde", step=step),
        working_read=WorkingRead(**read),
    )


def _abcde_with_read_slots() -> Registry:
    return Registry([Framework(
        id="abcde", name="ABCDE", summary="s", body="b",
        phases=["offering", "activate", "belief", "consequence", "dispute", "effective"],
        stages={"consequence": {"read_slots": ["impact", "response"]},
                "belief": {"read_slots": ["meaning"]}},
    )])


def test_a_stage_the_read_already_answers_is_not_asked_as_if_it_were_unknown():
    """Stage C was asked ("how has it affected you?") though the read held the lost sleep. The
    stage says which read slots answer it, so asking it as missing is sent back to be confirmed."""
    start = redraft.StageInForce("abcde", "consequence", asked=False, asks=0)
    held = _stage_reply("missing", impact="it is wearing them down and they are not sleeping")
    notes = redraft.reasons(
        held, THEIR_MESSAGES, _abcde_with_read_slots(), offer_not_allowed=False, stage_in_force=start,
    )
    assert any("already holds impact" in n for n in notes)
    empty = _stage_reply("missing")
    assert not any(
        "already holds" in n for n in redraft.reasons(
            empty, THEIR_MESSAGES, _abcde_with_read_slots(), offer_not_allowed=False, stage_in_force=start,
        )
    )
    confirming = _stage_reply("confirm", impact="it is wearing them down")
    assert not any(
        "already holds" in n for n in redraft.reasons(
            confirming, THEIR_MESSAGES, _abcde_with_read_slots(), offer_not_allowed=False,
            stage_in_force=start,
        )
    )


def test_a_partial_stage_asks_for_its_gap_until_the_read_holds_all_of_it():
    """Partial means asking only for the gap. Stage C is answered by what it does to them and what
    they do about it, so with only the first in the read the draft is right to ask for the second."""
    start = redraft.StageInForce("abcde", "consequence", asked=False, asks=0)
    gap = _stage_reply("partial", impact="they are not sleeping")
    assert not any(
        "already holds" in n for n in redraft.reasons(
            gap, THEIR_MESSAGES, _abcde_with_read_slots(), offer_not_allowed=False, stage_in_force=start,
        )
    )
    whole = _stage_reply("partial", impact="they are not sleeping", response="they work later")
    assert any(
        "already holds" in n for n in redraft.reasons(
            whole, THEIR_MESSAGES, _abcde_with_read_slots(), offer_not_allowed=False, stage_in_force=start,
        )
    )


def test_a_redraft_gets_only_what_is_left_of_the_turns_budget():
    """A slow first call used to start a redraft that could run its own full timeout on top. The
    redraft is cut at what the budget has left, and not started when too little is left for one."""
    budget, least = redraft.REDRAFT_BUDGET_MS, redraft.REDRAFT_MIN_MS
    assert redraft.redraft_seconds(1_000) == (budget - 1_000) / 1000
    assert redraft.redraft_seconds(budget - least) == least / 1000
    assert redraft.redraft_seconds(budget - least + 1) is None
    assert redraft.redraft_seconds(budget) is None


@pytest.mark.parametrize("phrase", [
    "this doesnt make sense",
    "this doesn't make sense",
    "what?",
    "What?",
    "i don't understand",
    "i didnt understand that",
    "that's confusing",
    "I'm confused",
    "what do you mean?",
])
def test_is_confused_catches_real_confusion(phrase: str):
    assert redraft.is_confused(phrase)


@pytest.mark.parametrize("phrase", [
    "I guess it was my manager, that makes sense now that I think about it",
    "what happened was my mom called",
    "I don't know, maybe around Tuesday",
    "yes, that's right",
    "",
])
def test_is_confused_leaves_real_answers_alone(phrase: str):
    assert not redraft.is_confused(phrase)


def test_a_draft_that_advances_past_a_stage_right_after_confusion_is_redrafted():
    """muhammad's transcript: "this doesnt make sense" mid-stage must not be read as an answer.
    The model's own step and stages_known ledger agreeing with each other proves nothing when the
    person's own words say they didn't answer."""
    starting = redraft.StageInForce("abcde", "activate", asked=True)
    stepped_ahead = ledger(("activate", True), ("belief", False), step="belief")
    notes = redraft.reasons(
        stepped_ahead, ["this doesnt make sense"], stages(), offer_not_allowed=False,
        stage_in_force=starting,
    )
    assert any("activate" in n and "confusion" in n for n in notes)

    marked_met_in_place = ledger(("activate", True), step="activate")
    notes = redraft.reasons(
        marked_met_in_place, ["what?"], stages(), offer_not_allowed=False, stage_in_force=starting,
    )
    assert any("activate" in n and "confusion" in n for n in notes)


def test_a_normal_stage_advance_after_a_real_answer_is_unaffected():
    starting = redraft.StageInForce("abcde", "activate", asked=True)
    draft = ledger(("activate", True), ("belief", False), step="belief")
    assert redraft.reasons(
        draft, ["it was my manager criticizing the report in front of the team"], stages(),
        offer_not_allowed=False, stage_in_force=starting,
    ) == []


@pytest.mark.parametrize("phrase", [
    "what does dispute mean?",
    "can you give an example?",
    "why are you asking this?",
    "What does that mean",
    "could you explain that",
    "it was my manager criticizing me, but what do you mean by evidence?",
])
def test_is_question_catches_genuine_questions(phrase: str):
    assert redraft.is_question(phrase)


@pytest.mark.parametrize("phrase", [
    "it was my manager criticizing the report",
    "I don't know, maybe around Tuesday",
    "yes, that's right",
    "",
])
def test_is_question_leaves_real_answers_alone(phrase: str):
    assert not redraft.is_question(phrase)


def test_a_draft_that_advances_past_a_stage_right_after_a_question_is_redrafted():
    """A genuine mid-stage question ("what does dispute mean?") has no deterministic backstop
    today unless the model happens to set next_move to answer_request and hold the stage; if it
    silently advances instead, the stage is lost the same way confusion was before Task A."""
    starting = redraft.StageInForce("abcde", "belief", asked=True)
    stepped_ahead = ledger(("belief", True), ("consequence", False), step="consequence")
    notes = redraft.reasons(
        stepped_ahead, ["what does dispute mean?"], stages(), offer_not_allowed=False,
        stage_in_force=starting,
    )
    assert any("belief" in n and "question" in n for n in notes)


def test_answering_the_question_and_holding_the_stage_is_not_rejected():
    """The legitimate case this must not break: the model claims answer_request and keeps
    state.step on the stage in force, because it answered without yet moving the stage on."""
    starting = redraft.StageInForce("abcde", "belief", asked=True)
    held = ledger(("belief", False), step="belief").model_copy(
        update={"next_move": "answer_request"}
    )
    assert redraft.reasons(
        held, ["what does dispute mean?"], stages(), offer_not_allowed=False,
        stage_in_force=starting,
    ) == []


def test_advancing_with_answer_request_claimed_is_not_rejected_on_step_grounds_alone():
    """The model may legitimately say its answer to a question also completed the stage - e.g.
    answering "why are you asking this" by walking through the stage's own content. next_move
    answer_request with the stage advanced is not, by itself, rejected."""
    starting = redraft.StageInForce("abcde", "belief", asked=True)
    advanced = ledger(("belief", True), ("consequence", False), step="consequence").model_copy(
        update={"next_move": "answer_request"}
    )
    notes = redraft.reasons(
        advanced, ["why are you asking this?"], stages(), offer_not_allowed=False,
        stage_in_force=starting,
    )
    assert not any("question" in n and "belief" in n for n in notes)


@pytest.mark.parametrize(("phrase", "count"), [
    ("what does dispute mean? and why does it matter if I already know what happened?", 2),
    ("what does dispute mean?", 1),
    ("can you explain that? and why does it matter? and what should I do?", 3),
    ("it was my manager criticizing the report", 0),
    ("really?? like actually?", 2),
    ("what??", 1),
])
def test_question_count_counts_question_sentences_in_the_user_message(phrase: str, count: int):
    assert redraft.question_count(phrase) == count


def test_two_questions_answered_as_one_is_redrafted_even_with_answer_request_claimed():
    """Task G: the model may truthfully set next_move to answer_request after answering only one
    of several questions. The count of questions asked against questions_answered catches what
    the single-boolean check (Task F) cannot."""
    starting = redraft.StageInForce("abcde", "belief", asked=True)
    held = ledger(("belief", False), step="belief").model_copy(
        update={"next_move": "answer_request", "questions_answered": 1}
    )
    notes = redraft.reasons(
        held,
        ["what does dispute mean? and why does it matter if I already know what happened?"],
        stages(), offer_not_allowed=False, stage_in_force=starting,
    )
    assert any("2 questions" in n and "answered 1" in n for n in notes)


def test_two_questions_answered_as_one_is_redrafted_even_when_the_stage_advances():
    """A partially-answered multi-question message is wrong even if the stage correctly held or
    advanced - the person is still owed an answer to the part that was skipped."""
    starting = redraft.StageInForce("abcde", "belief", asked=True)
    advanced = ledger(("belief", True), ("consequence", False), step="consequence").model_copy(
        update={"next_move": "answer_request", "questions_answered": 1}
    )
    notes = redraft.reasons(
        advanced,
        ["what does dispute mean? and why does it matter if I already know what happened?"],
        stages(), offer_not_allowed=False, stage_in_force=starting,
    )
    assert any("2 questions" in n and "answered 1" in n for n in notes)


def test_a_single_question_answered_is_not_double_rejected_by_the_count_check():
    """Must not double-reject what Task F's existing single-question check already handles: a
    single question with questions_answered set to 1 passes the new check cleanly."""
    starting = redraft.StageInForce("abcde", "belief", asked=True)
    held = ledger(("belief", False), step="belief").model_copy(
        update={"next_move": "answer_request", "questions_answered": 1}
    )
    assert redraft.reasons(
        held, ["what does dispute mean?"], stages(), offer_not_allowed=False,
        stage_in_force=starting,
    ) == []


def test_a_single_question_with_questions_answered_unset_is_not_rejected_by_the_count_check():
    starting = redraft.StageInForce("abcde", "belief", asked=True)
    held = ledger(("belief", False), step="belief").model_copy(
        update={"next_move": "answer_request"}
    )
    notes = redraft.reasons(
        held, ["what does dispute mean?"], stages(), offer_not_allowed=False,
        stage_in_force=starting,
    )
    assert not any("questions" in n and "answered" in n for n in notes)
