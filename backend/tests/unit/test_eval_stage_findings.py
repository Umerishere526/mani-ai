# ABOUTME: Checks the eval's reading of how the stored stage moved after each reply.
# ABOUTME: A hold is listed to be read; a stage that stays put with no hold is a finding.

from scripts.eval_replies import Exchange, _rephrase_findings, _stage_findings


def exchange(phase, notes=()):
    return Exchange(
        message="yes", reply="What happened next?", repair_notes=list(notes),
        framework=("abcde", "accepted", phase),
    )


START = {"framework": "abcde", "phase": "activate"}


def test_a_framework_that_moves_one_stage_on_every_reply_has_nothing_to_read():
    turns = [exchange("belief"), exchange("consequence"), exchange("somatic_checkin")]
    assert _stage_findings(turns, START) == []


def test_a_hold_is_listed_so_it_can_be_read():
    turns = [exchange("belief"), exchange("belief", ["repaired reply on thread t: held at belief"])]
    found = _stage_findings(turns, START)
    assert [f.rule for f in found] == ["held"]
    assert found[0].detail.startswith("counted at belief:")


def test_a_stage_that_stays_put_with_no_hold_is_a_finding():
    found = _stage_findings([exchange("activate")], START)
    assert [f.rule for f in found] == ["stage"]


def test_a_redirect_hold_is_listed_as_a_redirect():
    turns = [exchange("belief", ["repaired reply on thread t: redirect held at belief"])]
    found = _stage_findings(turns, {"framework": "abcde", "phase": "belief"})
    assert [(f.rule, f.detail.split(":")[0]) for f in found] == [("held", "redirect at belief")]


def test_a_hold_after_the_extra_turn_was_used_is_a_finding_of_its_own():
    turns = [exchange("consequence", ["repaired reply on thread t: hold limit at belief"])]
    found = _stage_findings(turns, {"framework": "abcde", "phase": "belief"})
    assert [f.rule for f in found] == ["hold limit"]
    assert found[0].detail.startswith("belief:")


def test_a_reply_that_says_a_question_again_on_purpose_is_not_a_repeated_question():
    from scripts.eval_replies import _score
    from mani.models.rows import SupportStyle

    asked = "What did it mean to you?"
    turns = [
        Exchange(message="a", reply=asked, framework=("abcde", "accepted", "consequence")),
        Exchange(message="I don't get it", reply="What did it mean to you?",
                 repair_notes=["held at consequence"],
                 framework=("abcde", "accepted", "consequence")),
    ]
    scenario = {"start_in": {"framework": "abcde", "phase": "belief"}}
    assert not [f for f in _score(turns, SupportStyle.SUPPORTIVE, scenario) if f.rule == "repeated_question"]


def asked(message, reply, notes=("repaired reply on thread t: held at belief",)):
    return Exchange(message=message, reply=reply, repair_notes=list(notes), framework=("abcde", "accepted", "belief"))


def test_a_rephrase_with_one_question_is_clean():
    assert _rephrase_findings(asked("I don't get it", "Put simply, what did that mean to you?")) == []


def test_a_rephrase_with_two_questions_is_a_finding():
    found = _rephrase_findings(asked("I don't get it", "What facts show you are fine? What might challenge that belief?"))
    assert [f.rule for f in found] == ["rephrase questions"]
    assert found[0].detail.startswith("2 question marks:")


def test_a_rephrase_with_no_question_is_a_finding():
    assert [f.rule for f in _rephrase_findings(asked("I still don't get it", "It is okay."))] == ["rephrase questions"]


def test_a_reply_that_is_not_a_held_request_is_not_read_as_a_rephrase():
    assert _rephrase_findings(asked("I don't get it", "What happened? Why?", notes=())) == []
    assert _rephrase_findings(asked("why does that matter?", "What happened? Why?")) == []
    assert _rephrase_findings(asked("I don't get it", "What happened? Why?", notes=("redirect held at belief",))) == []

