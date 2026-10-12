# ABOUTME: Checks on the model's reply that cost no model call: the step set from its ledger, what it missed.
# ABOUTME: Each check is a rule about the person or the cadence, so each is a plain test.

from mani.chat import reply_checks
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


def offer(technique: str) -> Reply:
    return Reply(
        text="There are some questions we could go through. Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique=technique), SmartPrompt(label="Keep chatting", decline=True)],
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


def test_a_step_that_agrees_with_the_ledger_is_left_alone():
    """muhammad, 2026-10-09: what the conversation already holds answers stages; the reply asks the
    first one it does not, and says so in stages_known."""
    starting = reply_checks.StageInForce("abcde", "activate", asked=False)
    draft = ledger(("activate", True), ("belief", True), ("consequence", False), step="consequence")
    assert reply_checks.with_ledger_step(draft, stages().get("abcde"), starting) is draft


def test_a_step_that_disagrees_with_the_ledger_is_set_from_it_without_asking_again():
    starting = reply_checks.StageInForce("abcde", "activate", asked=False)
    stayed = ledger(("activate", True), ("belief", False), step="activate")
    jumped = ledger(("activate", True), ("belief", False), step="consequence")
    for draft in (stayed, jumped):
        corrected = reply_checks.with_ledger_step(draft, stages().get("abcde"), starting)
        assert corrected.state.step == "belief"
        assert corrected.text == draft.text and corrected.state.technique == "abcde"


def test_the_closing_is_asked_even_when_the_ledger_calls_it_met():
    """The closing is theirs to answer, so it is skipped only once it has been asked."""
    framework = stages().get("abcde")
    walk = ledger(("consequence", True), ("closing", True), step="closing")
    not_asked = reply_checks.StageInForce("abcde", "consequence", asked=True)
    assert reply_checks.ledger_stage(walk, framework, not_asked) == "closing"
    asked = reply_checks.StageInForce("abcde", "closing", asked=True)
    assert reply_checks.ledger_stage(ledger(("closing", True), step="closing"), framework, asked) is None


def test_a_reply_with_no_ledger_or_no_state_keeps_its_step():
    framework = stages().get("abcde")
    starting = reply_checks.StageInForce("abcde", "activate", asked=False)
    no_ledger = at("consequence")
    assert reply_checks.with_ledger_step(no_ledger, framework, starting) is no_ledger
    no_state = ledger(("activate", True), ("belief", False), step=None)
    assert reply_checks.with_ledger_step(no_state, framework, starting) is no_state


def test_a_clean_question_stands():
    draft = Reply(text="What is the hardest part of the evenings?")
    assert reply_checks.misses(
        draft, registry(), offer_due=False, needs_question=True, last_mani_text=None
    ) == []


def test_an_offer_what_they_said_rules_out_is_found():
    assert reply_checks.ruled_out(offer("behavioral_activation"), ["my dog died"], registry()) == "behavioral_activation"


def test_the_same_offer_is_fine_when_nothing_rules_it_out():
    assert reply_checks.ruled_out(offer("behavioral_activation"), ["i stopped answering people"], registry()) is None
    assert reply_checks.ruled_out(offer("act_choice_point"), ["my dog died"], registry()) is None


def test_not_offering_when_an_offer_is_due_is_missed_if_mani_leans_somewhere():
    leaning = Reply(text="What is the hardest part?", heading_toward="act_choice_point")
    assert reply_checks.misses(
        leaning, registry(), offer_due=True, needs_question=False, last_mani_text=None
    ) == ["offer due and not made"]


def test_a_due_offer_is_not_missed_when_mani_has_no_lean():
    undecided = Reply(text="What is the hardest part?")
    assert reply_checks.misses(
        undecided, registry(), offer_due=True, needs_question=False, last_mani_text=None
    ) == []


def test_a_comfort_with_no_question_is_missed_before_an_offer():
    comfort = Reply(text="It is okay to feel that way. I am here with you.")
    assert reply_checks.misses(
        comfort, registry(), offer_due=False, needs_question=True, last_mani_text=None
    ) == ["asks no question"]


def test_no_question_is_fine_when_it_is_not_needed():
    """While the questions run, on a safety concern, or when they asked only to be heard."""
    comfort = Reply(text="It is okay to feel that way. I am here with you.")
    assert reply_checks.misses(
        comfort, registry(), offer_due=False, needs_question=False, last_mani_text=None
    ) == []


def test_an_offer_carries_its_own_permission_question():
    assert reply_checks.misses(
        offer("act_choice_point"), registry(), offer_due=False, needs_question=True, last_mani_text=None
    ) == []


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


def test_the_same_choices_asked_again_are_missed():
    """Observed: someone who asked Mani to pick got the same three options back, reworded, twice."""
    assert reply_checks.misses(
        Reply(text=SAME_AGAIN), registry(), offer_due=False, needs_question=False, last_mani_text=FIRST
    ) == ["repeats the last question"]


def test_a_different_question_after_an_answer_is_not_a_repeat():
    moved_on = Reply(text="Opening your laptop to look at one place sounds like a start. When will you do it?")
    assert reply_checks.misses(
        moved_on, registry(), offer_due=False, needs_question=False, last_mani_text=FIRST
    ) == []


def test_a_draft_that_chose_a_shape_asking_nothing_is_not_missing_a_question():
    """Whether someone only wants to be listened to is the model's reading, shown by its shape."""
    from mani.llm.schema import Style

    holding = Reply(text="That has been sitting with you.", style=Style(shape="mirror and hold"))
    asking = Reply(text="That has been sitting with you.", style=Style(shape="mirror and ask"))
    none = Reply(text="That has been sitting with you.")
    for draft, expected in ((holding, []), (asking, ["asks no question"]), (none, ["asks no question"])):
        assert reply_checks.misses(
            draft, registry(), offer_due=False, needs_question=True, last_mani_text=None
        ) == expected


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
    rows = reply_checks.ledger_view(reply, framework)
    assert [(r["stage"], r["status"]) for r in rows] == [
        ("activate", "done"), ("belief", "known"), ("consequence", "missing"), ("effective", "not_reached"),
    ]
    assert rows[0]["title"] == "A: Activating Event"
    assert rows[1]["action"] == "bypassed, not asked" and rows[2]["asking"] and not rows[1]["asking"]
    assert reply_checks.ledger_view(Reply(text="x"), framework) == []


