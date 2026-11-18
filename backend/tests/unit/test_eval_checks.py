# ABOUTME: Checks the eval's code checks on a reply: a reply outside its sentence or word limits fails, and a sentence
# ABOUTME: is counted once even with a question inside quotes or an ellipsis.

from evals import run_eval


def test_a_directive_reply_over_four_sentences_fails():
    case = {"checks": {"max_sentences": 4}}
    assert run_eval.rule_checks(case, {"text": "That makes sense. A is for Activating Event. What happened?"}) == []
    five = "That makes sense. It hurts. A is for Activating Event. Take your time. What happened?"
    assert run_eval.rule_checks(case, {"text": five}) == ["5 sentences > 4"]


def test_a_quoted_question_and_an_ellipsis_count_once():
    assert run_eval.sentences('He said "why me?" and left... Then what?') == 2


def test_a_reply_outside_its_word_limits_fails():
    six = "That sounds hard. What happened next?"
    assert run_eval.rule_checks({"checks": {"max_words": 6}}, {"text": six}) == []
    assert run_eval.rule_checks({"checks": {"max_words": 5}}, {"text": six}) == ["6 words > 5"]
    assert run_eval.rule_checks({"checks": {"min_words": 7}}, {"text": six}) == ["6 words < 7"]
