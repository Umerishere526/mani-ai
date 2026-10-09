# ABOUTME: Checks which drafted replies are asked for again, and for what reason.
# ABOUTME: Each reason is a rule about the person or the cadence, so each is a plain test.

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
    why = redraft.reasons(offer("act_choice_point"), ["my dog died"], registry(), offer_not_allowed=True)
    assert len(why) == 1 and "not allowed yet" in why[0]


def test_an_offer_what_they_said_rules_out_is_a_reason():
    why = redraft.reasons(offer("behavioral_activation"), ["my dog died"], registry(), offer_not_allowed=False)
    assert len(why) == 1 and "Behavioral Activation" in why[0]
    assert redraft.ruled_out(offer("behavioral_activation"), ["my dog died"], registry()) == "behavioral_activation"


def test_the_same_offer_is_fine_when_nothing_rules_it_out():
    assert redraft.reasons(offer("behavioral_activation"), ["i stopped answering people"], registry(), offer_not_allowed=False) == []
    assert redraft.ruled_out(offer("act_choice_point"), ["my dog died"], registry()) is None


def test_not_offering_when_the_closest_fit_is_due_is_a_reason_if_mani_leans_somewhere():
    leaning = Reply(text="What is the hardest part?", heading_toward="act_choice_point")
    why = redraft.reasons(leaning, ["my dog died"], registry(), offer_not_allowed=False, closest_fit_due=True)
    assert len(why) == 1 and "offer the set of questions that fits best now" in why[0]


def test_a_due_closest_fit_is_not_forced_when_mani_has_no_lean():
    undecided = Reply(text="What is the hardest part?")
    assert redraft.reasons(undecided, ["hi"], registry(), offer_not_allowed=False, closest_fit_due=True) == []


def test_a_comfort_with_no_question_is_a_reason_before_an_offer():
    comfort = Reply(text="It is okay to feel that way. I am here with you.")
    why = redraft.reasons(comfort, ["i felt small"], registry(), offer_not_allowed=False, needs_question=True)
    assert len(why) == 1 and "asks no question" in why[0]


def test_no_question_is_fine_when_it_is_not_needed():
    """While the questions run, on a safety concern, or when they asked only to be heard."""
    comfort = Reply(text="It is okay to feel that way. I am here with you.")
    assert redraft.reasons(comfort, ["i felt small"], registry(), offer_not_allowed=False, needs_question=False) == []


def test_an_offer_carries_its_own_permission_question():
    assert redraft.reasons(offer("act_choice_point"), ["x"], registry(), offer_not_allowed=False, needs_question=True) == []


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


def test_a_due_closest_fit_is_never_asked_to_call_itself_the_nearest():
    """Loli's test, 2026-10-09: "the nearest fit I have ... though we can keep talking instead"
    reached the person in all three styles. This note told the model to say exactly that."""
    leaning = Reply(text="What happened next?", heading_toward="abcde")
    why = " ".join(redraft.reasons(leaning, ["my manager"], registry(), offer_not_allowed=False,
                                   closest_fit_due=True))
    assert why
    assert "nearest" not in why and "closest" not in why


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
    assert rows[1]["action"] == "bypassed, not asked" and rows[2]["asking"] and not rows[1]["asking"]
    assert redraft.ledger_view(Reply(text="x"), framework) == []


