# ABOUTME: Whole turns against a live database with a scripted model: what the one-call turn sends, stores and shows.
# ABOUTME: The model is faked; every write, policy, framework move and safety pause under test is real.

import uuid

import pytest

from mani.chat import crisis, runner
from mani.chat.reply import Event, Person, Question, Safety, Said
from mani.db import threads
from mani.errors import ErrorCategory, ServiceError
from mani.llm import client
from mani.models.rows import TechniqueOutcome, TechniqueState
from tests.integration.fixtures import ALICE, last_user_message_id, said, send, start, thread_row

DANGER = Safety(level="danger", about="themselves", why="took pills")


def facts_of(scripted) -> str:
    return scripted.last_messages[-1]["content"]


async def technique_of(alice, thread_id):
    from mani.db import pool

    async with pool.as_user(alice) as conn:
        return (await threads.load_turn_context(conn, thread_id, ALICE)).technique


async def put_technique(thread_id, framework_id: str, outcome: TechniqueOutcome, phase: str | None) -> None:
    from mani.db import pool

    async with pool.as_admin() as conn:
        await threads.apply(conn, thread_id, ALICE, threads.ThreadUpdates(technique=TechniqueState(
            thread_id=thread_id, framework_id=framework_id, outcome=outcome, phase=phase, at_message_count=4)))


async def put_record(thread_id, record: dict, safety_state: str = "clear") -> None:
    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute("update public.threads set understanding = $2::jsonb, safety = $3 where id = $1",
                           thread_id, record, safety_state)


async def all_hosts_down(*_, **__):
    raise ServiceError("all hosts failed", ErrorCategory.LLM_UNAVAILABLE, retryable=True)


async def test_a_turn_costs_exactly_one_provider_call_and_sends_the_text_as_written(alice, model):
    scripted = model(said("That sounds heavy. What happened?", notes="first"))
    thread = await start(alice)
    turn = await send(alice, thread.id, "I had a hard day")
    assert scripted.calls == 1
    assert turn.content == "That sounds heavy. What happened?" and turn.prompts == []


async def test_dashes_are_replaced_and_nothing_else_in_the_text_changes(alice, model):
    model(said("It hurts — a lot."))
    thread = await start(alice)
    assert (await send(alice, thread.id, "hi")).content == "It hurts, a lot."


async def test_notes_written_by_one_turn_reach_the_next_turns_facts(alice, model):
    scripted = model(said("Go on.", notes="boss piles work; feels like a pushover"), said("I hear you."))
    thread = await start(alice)
    await send(alice, thread.id, "my boss keeps piling work on me")
    await send(alice, thread.id, "yeah")
    assert "Your notes from your last turn: boss piles work; feels like a pushover" in facts_of(scripted)


async def test_people_and_events_carry_to_the_next_turn_and_a_new_conversation_starts_without_them(alice, model):
    """Each conversation stands alone: what one learned of their people and events never reaches another."""
    scripted = model(
        said("That's soon.", people=[Person(called="my sister", relation="sister", told="won't be there")],
             events=[Event(what="Thanksgiving alone this Thursday", when="upcoming")]),
        said("I hear you."),
    )
    thread = await start(alice)
    await send(alice, thread.id, "thanksgiving is thursday and my sister won't be there")
    await send(alice, thread.id, "yeah")
    assert ("my sister (sister): won't be there" in facts_of(scripted)
            and "[upcoming] Thanksgiving alone this Thursday" in facts_of(scripted))
    other = await start(alice)
    await send(alice, other.id, "hi")
    assert "my sister" not in facts_of(scripted) and "Thanksgiving" not in facts_of(scripted)


async def test_an_open_chat_reply_keeps_one_question_and_the_next_turn_hears_what_it_was_for(alice, model):
    scripted = model(
        said("You keep saying yes. Why is that?\n\nWhat do you tell yourself would happen if you said no?",
             question=Question(latest="answer", intent="Belief")),
        said("Fair. I've been asking a lot. What would help?", question=Question(latest="frustrated", intent="wants")),
        said("I hear you."),
    )
    thread = await start(alice)
    first = await send(alice, thread.id, "i always say yes to my sister")
    assert first.content == "You keep saying yes.\n\nWhat do you tell yourself would happen if you said no?"
    assert (await send(alice, thread.id, "stop asking me things")).content == "Fair. I've been asking a lot."
    await send(alice, thread.id, "ok")
    assert '[belief] "What do you tell yourself would happen if you said no?".' in facts_of(scripted)


async def test_a_question_their_next_message_answers_is_told_as_already_answered(alice, model):
    scripted = model(
        said("That stings.\n\nWhat did he say?", question=Question(intent="situation")),
        said("Lazy is a hard word to hear.", question=Question(latest="answer", answered="called me lazy")),
        said("I hear you."),
    )
    thread = await start(alice)
    await send(alice, thread.id, "my boss had a go at me")
    await send(alice, thread.id, "he called me lazy in front of everyone")
    await send(alice, thread.id, "yeah")
    assert '[situation] "What did he say?" (already answered: "called me lazy")' in facts_of(scripted)


async def test_a_reply_reaches_them_with_its_own_question_last_and_every_sentence_whole(alice, model):
    """At most one question per reply in every style: the one the reply chose, in any form, after its text. A question
    the text slipped in is taken out whole; a guarded turn's words lose nothing."""
    scripted = model(
        said("Your sister leans on you a lot. Why do you think that is?",
             question=Question(latest="answer", intent="situation", ask="Tell me about the last time she asked.")),
        said("Okay.", question=Question(latest="answer", intent="wants", ask="What would you want her to hear?")),
        said("B is for Belief. What went through your mind?", stage="belief",
             question=Question(ask="What did you tell yourself about it?")),
        said("That sounds frightening. Are you hurt?", level="unsure", safety=Safety(level="unsure", about="themselves"),
             question=Question(ask="Is anyone with you right now?")),
    )
    thread = await start(alice, style="Directive")
    first = await send(alice, thread.id, "my sister always asks me for money")
    assert first.content == "Your sister leans on you a lot.\n\nTell me about the last time she asked."
    assert first.trace["question_cut"] == "question in the text"
    await send(alice, thread.id, "last week, again")
    assert '[situation] "Tell me about the last time she asked."' in facts_of(scripted)
    await put_technique(thread.id, "abcde", TechniqueOutcome.ACCEPTED, "activate")
    stage = await send(alice, thread.id, "she called friday and i said yes")
    assert stage.content == "B is for Belief.\n\nWhat did you tell yourself about it?"
    guarded = await send(alice, thread.id, "i don't want to be here anymore")
    assert guarded.content == "That sounds frightening. Are you hurt?\n\nIs anyone with you right now?"


async def test_a_held_worry_whose_text_already_asks_its_question_asks_it_once(alice, model):
    """TC-13 (2026-11-25): with a worry held, the text and the chosen question both carried the same question, and the
    person read it twice."""
    question = "How long has it been like this for you?"
    model(said("Okay. That's clear.", level="unsure", safety=Safety(level="unsure", about="themselves")),
          said(f"So it's exhaustion more than anything.\n\n{question}", question=Question(latest="answer", ask=question)))
    thread = await start(alice)
    await send(alice, thread.id, "i feel numb lately. i wish i could disappear")
    turn = await send(alice, thread.id, "no, i'd never hurt myself. i'm just exhausted")
    assert turn.content == f"So it's exhaustion more than anything.\n\n{question}"
    assert turn.trace["enforced"] == ["repeated_question"]


async def test_a_forbidden_word_and_a_banned_line_never_reach_them_and_the_trace_counts_both(alice, model):
    """Behavioral Framework and Safety Guardrails section 6, which the prompt alone let through (TC-03, TC-17)."""
    model(said("I'm here for you. Two words, and they land hard.",
               question=Question(latest="adds_more", ask="What happened when you were struggling last time?")))
    thread = await start(alice)
    turn = await send(alice, thread.id, "she just said 'whatever' and left")
    assert turn.content == "Two words, and they hit hard.\n\nWhat happened when you were finding it hard last time?"
    assert turn.trace["enforced"] == ["forbidden_word:land", "forbidden_word:struggling", "banned_line_removed"]


async def test_a_long_directive_reply_reaches_them_as_three_sentences(alice, model):
    """Directive is two or three short sentences, its question included; 7 eval replies ran to 4 or 5 (CQ-3)."""
    model(said("A job you believe in can still cost too much. You've said it twice. That matters a lot.",
               question=Question(latest="answer", ask="What feels hardest about it?")))
    thread = await start(alice, style="Directive")
    turn = await send(alice, thread.id, "i love the work but it's eating my evenings")
    assert turn.content == ("A job you believe in can still cost too much. You've said it twice.\n\n"
                            "What feels hardest about it?")
    assert turn.trace["enforced"] == ["directive_trimmed"]


async def test_an_opening_this_conversation_already_used_is_dropped_when_the_rest_stands(alice, model):
    """Pacing Rules and R116: the openers ledger was shown to the model, but nothing enforced it (CQ-5)."""
    model(said("That makes sense. The work kept coming.", question=Question(latest="answer", ask="What came first?")),
          said("That makes sense. The evenings went too.", question=Question(latest="answer", ask="When did that start?")))
    thread = await start(alice)
    await send(alice, thread.id, "work has been a lot")
    turn = await send(alice, thread.id, "and now my evenings are gone")
    assert turn.content == "The evenings went too.\n\nWhen did that start?"
    assert turn.trace["enforced"] == ["opener_dropped"]


# Two ordinary exchanges first: an offer may come with the person's 3rd message at the earliest.
WARM_UP = (said("Go on."), said("Tell me more."))


async def warm_up(alice, thread_id) -> None:
    await send(alice, thread_id, "work has been a lot lately")
    await send(alice, thread_id, "my boss keeps adding things")


async def abcde_steps(style: str = "supportive") -> str:
    from mani.chat import techniques
    from mani.prompts import cache

    return techniques.steps_text((await cache.load()).registry.get("abcde"), style)


START = ["Start ABCDE", "Talk more first"]


async def test_a_clear_offer_is_the_lead_in_with_its_three_buttons(alice, model):
    model(*WARM_UP, said("Just because a belief feels true doesn't mean it is. How could you test that thought?",
               action="offer", framework="abcde"))
    thread = await start(alice)
    await warm_up(alice, thread.id)
    turn = await send(alice, thread.id, "i always feel like a pushover")
    assert [p.label for p in turn.prompts] == ["Not sure", "Show me how", "Give me a tool"]
    assert (await technique_of(alice, thread.id)).outcome is TechniqueOutcome.OFFERED


async def test_the_offer_runs_lead_in_steps_then_start(alice, model):
    """The client's sequence document, 2026-11-18: the steps are hers, sent with no model call."""
    scripted = model(*WARM_UP, said("Lead-in.", action="offer", framework="abcde"),
                     said("A is for Activating Event. What happened?", stage="activate"),
                     said("B is for Belief. What did you tell yourself?", stage="belief"))
    thread = await start(alice)
    await warm_up(alice, thread.id)
    await send(alice, thread.id, "i feel like a pushover")
    steps = await send(alice, thread.id, "Not sure")
    assert scripted.calls == 3 and steps.content == await abcde_steps()
    assert [p.label for p in steps.prompts] == START
    await send(alice, thread.id, "Start ABCDE")
    assert (await technique_of(alice, thread.id)).phase == "activate"
    await send(alice, thread.id, "he dumped a report on me friday")
    technique = await technique_of(alice, thread.id)
    assert technique.outcome is TechniqueOutcome.ACCEPTED and technique.phase == "belief"


async def test_show_me_how_walks_the_steps_on_their_situation_then_offers_the_start(alice, model):
    """Lolly, 2026-11-20: Show me how demonstrates the five steps on the person's own situation, inventing nothing,
    then invites them to try it; it is the model's reply, never the fixed five steps."""
    walk = "A: your boss keeps adding things. B: what you tell yourself then is yours to fill in."
    scripted = model(*WARM_UP, said("Lead-in.", action="offer", framework="abcde"),
                     said(walk, question=Question(ask="Want to try it on your own?")),
                     said("A is for Activating Event. What happened?", stage="activate"))
    thread = await start(alice)
    await warm_up(alice, thread.id)
    await send(alice, thread.id, "i feel like a pushover")
    shown = await send(alice, thread.id, "Show me how")
    assert scripted.calls == 4 and shown.content == f"{walk}\n\nWant to try it on your own?"
    told = facts_of(scripted)
    assert "They tapped Show me how" in told and "only what they have told you" in told
    assert "lead-in to ABCDE" not in told, "the lead-in's next step is not what happens"
    assert [p.label for p in shown.prompts] == ["Start ABCDE", "Talk more first"]
    assert (await technique_of(alice, thread.id)).phase == "steps"
    await send(alice, thread.id, "Start ABCDE")
    technique = await technique_of(alice, thread.id)
    assert technique.outcome is TechniqueOutcome.ACCEPTED and technique.phase == "activate"


async def test_give_me_a_tool_starts_the_first_stage_at_once(alice, model):
    """Lolly, 2026-11-20: Give me a tool begins the exercise immediately, prefilling what it can."""
    scripted = model(*WARM_UP, said("Lead-in.", action="offer", framework="abcde"),
                     said("A is for Activating Event. Your boss keeps adding things. Is that the situation?",
                          stage="activate"))
    thread = await start(alice)
    await warm_up(alice, thread.id)
    await send(alice, thread.id, "i feel like a pushover")
    turn = await send(alice, thread.id, "Give me a tool")
    assert scripted.calls == 4 and turn.prompts == []
    told = facts_of(scripted)
    assert "They tapped Give me a tool" in told and "ask only whether it is right or what is missing" in told
    technique = await technique_of(alice, thread.id)
    assert technique.outcome is TechniqueOutcome.ACCEPTED and technique.phase == "activate"


async def test_a_typed_reply_to_the_lead_in_gets_the_reply_then_the_steps(alice, model):
    model(*WARM_UP, said("Lead-in.", action="offer", framework="abcde"), said("That's a fair way to start."))
    thread = await start(alice)
    await warm_up(alice, thread.id)
    await send(alice, thread.id, "i feel like a pushover")
    turn = await send(alice, thread.id, "maybe look at what i've actually managed?")
    assert turn.content == "That's a fair way to start.\n\n" + await abcde_steps()
    assert [p.label for p in turn.prompts] == START
    assert (await technique_of(alice, thread.id)).phase == "steps"


async def test_talk_more_first_lets_the_offer_lapse_and_it_may_come_back(alice, model):
    model(*WARM_UP, said("Lead-in.", action="offer", framework="abcde"), said("Sure, let's keep talking."),
          said("Lead-in again.", action="offer", framework="abcde"))
    thread = await start(alice)
    await warm_up(alice, thread.id)
    await send(alice, thread.id, "i feel like a pushover")
    await send(alice, thread.id, "Not sure")
    await send(alice, thread.id, "Talk more first")
    technique = await technique_of(alice, thread.id)
    assert technique.outcome is TechniqueOutcome.OFFERED and technique.phase is None, "set aside, not declined"
    again = await send(alice, thread.id, "ok i think i'm ready now")
    assert [p.label for p in again.prompts] == ["Not sure", "Show me how", "Give me a tool"]


async def test_a_declined_framework_is_never_offered_again(alice, model):
    scripted = model(*WARM_UP, said("Lead-in.", action="offer", framework="abcde"), said("Okay, we'll leave it.", action="stop"),
          said("Offer again.", action="offer", framework="abcde"))
    thread = await start(alice)
    await warm_up(alice, thread.id)
    await send(alice, thread.id, "i feel like a pushover")
    await send(alice, thread.id, "no, i don't want to do any exercise")
    turn = await send(alice, thread.id, "still feel like a pushover")
    assert offers_in(scripted.schemas[-1]) == ["thought_reframe"]
    assert turn.prompts == [] and turn.trace["refused"] == "offer"


async def test_a_question_asked_in_a_set_and_what_the_reply_gave_reach_the_next_turn(alice, model):
    """Repetition inside a set: the stage's question, the reply's move and its opening words are kept like any other."""
    scripted = model(
        said("That's a clear moment. B is for Belief. What went through your mind?", stage="belief",
             said=Said(move="acknowledge", gist="named the meeting moment")),
        said("I hear you.", stage="belief"),
    )
    thread = await start(alice)
    await put_technique(thread.id, "abcde", TechniqueOutcome.ACCEPTED, "activate")
    await send(alice, thread.id, "he yelled at me in the meeting on monday")
    await send(alice, thread.id, "that i'm useless")
    told = facts_of(scripted)
    assert '[belief] "What went through your mind?"' in told
    assert "acknowledge: named the meeting moment" in told and '"That\'s a clear moment"' in told


async def test_after_e_the_feelings_check_then_the_closing_buttons(alice, model):
    scripted = model(said("That's a strong shift. How are you feeling now?", action="finish", stage="effective"),
                     said("Thanks for saying so. What do you still need?"))
    thread = await start(alice)
    await put_technique(thread.id, "abcde", TechniqueOutcome.ACCEPTED, "effective")
    check = await send(alice, thread.id, "I can be a team player and still say no")
    assert [p.label for p in check.prompts] == ["Better", "About the same", "It didn't help"]
    assert "abcde" not in ((await thread_row(alice, thread.id)).understanding.get("finished") or [])
    closed = await send(alice, thread.id, "It didn't help")
    assert "They tapped the button \"It didn't help\"" in facts_of(scripted)
    assert [p.label for p in closed.prompts] == ["Continue chatting", "Visit library"]
    assert (await thread_row(alice, thread.id)).understanding["finished"] == ["abcde"]


async def test_visit_library_opens_the_section_an_earlier_reply_named(alice, model):
    """LIB-3: the section a reply names is kept on the thread, so a later Visit library opens it."""
    model(said("That sounds exhausting.", library="Burnout"),
          said("The library has exercises for moments like this.", action="library"))
    thread = await start(alice)
    await send(alice, thread.id, "i'm running on empty at work")
    turn = await send(alice, thread.id, "can you give me something to try?")
    assert [(p.label, p.library) for p in turn.prompts] == [("Visit library", "Burnout")]
    assert (await thread_row(alice, thread.id)).understanding["library"] == "Burnout"


async def test_a_typed_wish_to_stop_gets_a_goodbye_with_no_question_and_the_close(alice, model):
    """R95, the 2026-11-16 relationship test: "Yes, I'm done for now." got another question."""
    model(said("Of course. Take good care tonight.",
               question=Question(latest="wants_to_stop", ask="Would you like to come back to this another time?")))
    thread = await start(alice)
    turn = await send(alice, thread.id, "Yes, I'm done for now.")
    assert turn.content == "Of course. Take good care tonight."
    assert [p.label for p in turn.prompts] == ["Continue chatting", "Visit library"]
    assert turn.trace["question_cut"] == "question after a wish to stop"


async def test_a_typed_stop_the_model_missed_still_closes_with_no_question_except_on_a_guarded_turn(alice, model):
    """Eval rule-typed-done (3/3) and TC-17: the model asked what "done" meant, so the stop path never ran (R95)."""
    model(said("Okay, we can leave it there.", question=Question(latest="other", ask="What do you mean by done?")),
          said("Okay.", level="unsure", safety=Safety(level="unsure", about="themselves"),
               question=Question(latest="other", ask="Are you safe right now?")))
    thread = await start(alice)
    turn = await send(alice, thread.id, "that's all, thanks")
    assert turn.content == "Okay, we can leave it there."
    assert [p.label for p in turn.prompts] == ["Continue chatting", "Visit library"]
    assert turn.trace["enforced"] == ["typed_stop"]
    guarded = await send(alice, thread.id, "bye")
    assert guarded.content == "Okay.\n\nAre you safe right now?" and "enforced" not in guarded.trace


async def test_a_finish_after_danger_sends_the_end_check_then_the_close(alice, model):
    model(said("Warm close.", action="finish", stage="effective"),
          said("Glad you're safe. How are you feeling now?", action="finish", stage="effective"),
          said("Good to hear."))
    thread = await start(alice)
    await put_technique(thread.id, "abcde", TechniqueOutcome.ACCEPTED, "effective")
    await put_record(thread.id, {"danger_reached": True})
    first = await send(alice, thread.id, "my new belief is that I'm allowed limits")
    assert first.content == crisis.END_CHECK and first.prompts == []
    check = await send(alice, thread.id, "i'm okay now, my sister is here")
    assert [p.label for p in check.prompts] == ["Better", "About the same", "It didn't help"]
    assert (await thread_row(alice, thread.id)).understanding["safety_end_check"] == "done"
    closed = await send(alice, thread.id, "Better")
    assert [p.label for p in closed.prompts] == ["Continue chatting", "Visit library"]


async def test_a_set_stopped_while_the_end_check_waits_leaves_no_question_marked_as_asked(alice, model):
    """The audit of 2026-11-20: a stop in answer to the safety question after the last stage left the marker at
    "asked", so every later turn was told it had just asked that question."""
    model(said("Warm close.", action="finish", stage="effective"), said("Okay, we can leave it there.", action="stop"))
    thread = await start(alice)
    await put_technique(thread.id, "abcde", TechniqueOutcome.ACCEPTED, "effective")
    await put_record(thread.id, {"danger_reached": True})
    first = await send(alice, thread.id, "my new belief is that I'm allowed limits")
    assert first.content == crisis.END_CHECK
    await send(alice, thread.id, "i'm fine. i don't want to do this exercise anymore")
    record = (await thread_row(alice, thread.id)).understanding
    assert "safety_end_check" not in record and record["declined"] == ["abcde"]


async def test_overdose_on_the_first_message_gets_manis_reply_and_the_next_message_pauses(alice, model):
    model(said("Call 911 now. Are you alone?", safety=DANGER), said("Please call now.", safety=DANGER))
    thread = await start(alice)
    first = await send(alice, thread.id, "i took a bunch of my sleeping pills")
    assert first.content == "Call 911 now. Are you alone?" and first.paused_until is None and first.crisis_detected
    second = await send(alice, thread.id, "yes alone. i dont want help")
    assert second.paused_until is not None
    assert second.content == "Please call now.\n\n" + crisis.pause_reply("themselves", 30)


async def test_a_paused_person_is_refused_before_anything_is_paid(alice, model):
    scripted = model(said("Call now.", safety=DANGER), said("Please.", safety=DANGER), said("unused"))
    thread = await start(alice)
    await send(alice, thread.id, "i took pills")
    await send(alice, thread.id, "alone")
    with pytest.raises(ServiceError) as refused:
        await send(alice, thread.id, "hello?")
    assert refused.value.category is ErrorCategory.CHAT_PAUSED and scripted.calls == 2


async def test_a_retry_of_a_message_no_host_answered_runs_the_turn_again(alice, model, monkeypatch):
    """The audit of 2026-11-20: the fixed words were stored under the message's id, so a retry of "i took a bunch of
    pills" returned them for ever and the message was never read."""
    key = uuid.uuid4()
    thread = await start(alice)
    with monkeypatch.context() as down:
        down.setattr(client, "complete", all_hosts_down)
        unread = await send(alice, thread.id, "i took a bunch of pills", client_message_id=key)
    assert unread.content == crisis.TROUBLE_REPLY
    count = (await thread_row(alice, thread.id)).message_count
    model(said("Call 911 now. Are you alone?", safety=DANGER))
    read = await send(alice, thread.id, "i took a bunch of pills", client_message_id=key)
    assert read.content == "Call 911 now. Are you alone?" and read.crisis_detected and not read.was_duplicate
    assert (await thread_row(alice, thread.id)).message_count == count, "the unread turn was replaced, not added to"


async def test_every_host_failing_on_a_first_danger_message_still_answers(alice, monkeypatch):
    monkeypatch.setattr(client, "complete", all_hosts_down)
    thread = await start(alice)
    turn = await send(alice, thread.id, "i took a bunch of pills")
    assert turn.content == crisis.TROUBLE_REPLY


async def test_a_held_worry_whose_reply_fails_its_check_twice_still_gets_the_crisis_reply(alice, model, monkeypatch):
    """A reply that says danger without whose fails its check; when the one retry fails too, complete raises, and a
    conversation holding a worry gets the crisis words with its danger kept."""
    model(said("Call 911 now. Are you alone?", safety=DANGER))
    thread = await start(alice)
    await send(alice, thread.id, "i took a bunch of pills")

    async def no_reply_fits(*_, **__):
        raise ServiceError("model returned no parseable reply after 2 attempts", ErrorCategory.LLM_UNAVAILABLE,
                           retryable=True)

    monkeypatch.setattr(client, "complete", no_reply_fits)
    turn = await send(alice, thread.id, "i don't want help")
    assert turn.content == crisis.CRISIS_REPLY and turn.crisis_detected and turn.paused_until is None
    assert (await thread_row(alice, thread.id)).safety == "danger"


async def test_a_fallback_reply_keeps_the_notes_and_moves_no_state(alice, model, monkeypatch):
    model(said("Go on.", notes="kept notes"))
    thread = await start(alice)
    await send(alice, thread.id, "hard week")
    monkeypatch.setattr(client, "complete", all_hosts_down)
    await send(alice, thread.id, "still here")
    row = await thread_row(alice, thread.id)
    assert row.understanding["notes"] == "kept notes" and row.safety == "clear"


async def test_a_retried_send_returns_the_first_reply_without_paying_again(alice, model):
    scripted = model(said("Go on."), said("A different answer."))
    thread = await start(alice)
    key = uuid.uuid4()
    first = await send(alice, thread.id, "hello", client_message_id=key)
    again = await send(alice, thread.id, "hello", client_message_id=key)
    assert again.was_duplicate and again.content == first.content and scripted.calls == 1


async def test_choosing_a_style_opens_in_it_with_no_model_call(alice, model):
    scripted = model(said("unused"))
    thread = await start(alice, style=None)
    turn = await send(alice, thread.id, "Directive")
    assert turn.content == "How can I help you today?" and scripted.calls == 0


async def test_a_title_is_asked_for_once_the_thread_has_an_exchange_and_stored(alice, model):
    scripted = model(said("Go on."), said("Tell me more.", title="Work pressure"))
    thread = await start(alice)
    await send(alice, thread.id, "work is a lot")
    turn = await send(alice, thread.id, "my boss")
    assert "Give this conversation a title." in facts_of(scripted) and turn.title == "Work pressure"


async def test_editing_after_a_finishing_turn_restores_the_framework_state(alice, model):
    model(said("Warm close.", action="finish", stage="effective"), said("Let's keep going.", stage="effective"))
    thread = await start(alice)
    await put_technique(thread.id, "abcde", TechniqueOutcome.ACCEPTED, "effective")
    await send(alice, thread.id, "I can say no")
    await runner.edit(alice, thread.id, await last_user_message_id(thread.id), "not sure yet")
    technique = await technique_of(alice, thread.id)
    row = await thread_row(alice, thread.id)
    assert technique.phase == "effective" and "abcde" not in (row.understanding.get("finished") or [])


async def _a_pause_that_has_run_out(alice, model_replies, model):
    """A conversation paused on danger whose pause has since run out, and the scripted model."""
    from mani.db import pool

    scripted = model(said("Call now.", safety=DANGER), said("Please call.", safety=DANGER), *model_replies)
    paused_in = await start(alice)
    await send(alice, paused_in.id, "i took pills")
    await send(alice, paused_in.id, "alone")
    async with pool.as_admin() as conn:
        await conn.execute("update public.chat_pauses set ends_at = now() - interval '1 minute' where user_id = $1",
                           ALICE)
    return scripted, paused_in


async def test_the_first_message_back_in_the_paused_conversation_is_asked_about_and_a_safe_answer_settles_it(
    alice, model
):
    """muhammad, 2026-11-25: the conversation the pause began in still reads the first message back for safety, with
    code's question, and their answer that they are safe settles that conversation."""
    scripted, paused_in = await _a_pause_that_has_run_out(alice, [said("How are things now?"), said("Good to hear it.")],
                                                          model)
    asked = await send(alice, paused_in.id, "back now")
    assert asked.content == crisis.RETURN_CHECK_REPLY and asked.paused_until is None
    assert "Their chat was paused earlier because of a safety worry (took pills)" in facts_of(scripted)

    answered = await send(alice, paused_in.id, "i'm okay, my sister is here")
    assert answered.content == "Good to hear it." and answered.paused_until is None
    assert "This message answers it: judge it for safety." in facts_of(scripted)
    assert (await thread_row(alice, paused_in.id)).safety == "clear"


async def test_an_edited_answer_to_the_question_after_a_pause_is_read_as_the_answer_again(alice, model):
    """An edit restores the conversation to Mani's question, so the edited message is judged as its answer."""
    unsure = Safety(level="unsure", about="themselves")
    scripted, thread = await _a_pause_that_has_run_out(
        alice, [said("How are things now?"), said("Good to hear it."), said("I'm here. What feels shaky?", safety=unsure)],
        model)
    await send(alice, thread.id, "back now")
    await send(alice, thread.id, "i'm fine")

    edited = await runner.edit(alice, thread.id, await last_user_message_id(thread.id), "not really, still shaky")

    assert edited.content == "I'm here. What feels shaky?"
    assert "This message answers it: judge it for safety." in facts_of(scripted)


async def test_a_new_conversation_after_a_pause_opens_normally_and_never_raises_it(alice, model):
    """Lolly, 2026-11-25: a new chat opened with the question about a pause, then told her what Mani had been worried
    about. A new conversation opens with the style's own opener, answers their first message as written, and nothing
    of the pause reaches its facts."""
    from mani.chat.greeting import OPENERS
    from mani.chat.record import RETURN_CHECK

    scripted, _ = await _a_pause_that_has_run_out(alice, [said("What would help most today?")], model)
    fresh = await start(alice, style=None)

    opened = await send(alice, fresh.id, "Directive")
    answered = await send(alice, fresh.id, "work has been a lot this week")

    assert opened.content == OPENERS["directive"] and scripted.calls == 3
    assert answered.content == "What would help most today?" and answered.paused_until is None
    facts = facts_of(scripted)
    assert "paus" not in facts and "took pills" not in facts and "answers it" not in facts
    row = await thread_row(alice, fresh.id)
    assert row.safety == "clear" and RETURN_CHECK not in (row.understanding or {})


async def test_the_first_message_back_after_a_pause_never_agrees_to_carry_on_whatever_the_model_wrote(alice, model):
    """The client's blocker test, 2026-11-16: back after the pause, saying the pills were still beside her, she was told
    "Yes, we can keep talking". The first turn back is code's fixed words, and the model's read still stands: read as
    danger it gets the way to help (muhammad, 2026-11-20), otherwise the question how things are."""
    still_there = Safety(level="danger", about="themselves", still_there=True, why="pills beside her")
    _, paused_in = await _a_pause_that_has_run_out(
        alice, [said("Yes, we can keep talking.", safety=still_there)], model)

    back = await send(alice, paused_in.id, "the pills are still next to me, can we keep talking?")

    assert back.content == crisis.RETURN_DANGER_REPLY and back.paused_until is None
    assert (await thread_row(alice, paused_in.id)).safety == "danger"


CHEST = Safety(level="unsure", about="body", symptom_now="unsaid")


async def test_a_body_worry_the_model_held_lower_still_gets_call_now(alice, model):
    """muhammad, 2026-11-18: a possible medical emergency gets "call emergency services now" every time; MiniMax held
    chest pain with a strange left arm at unsure in 7 of 30 runs. The line comes once per rise, never every turn."""
    model(said("That needs checking soon.", safety=CHEST), said("I'm here with you.", safety=CHEST))
    thread = await start(alice)
    first = await send(alice, thread.id, "my chest is tight and my left arm feels weird")
    assert first.content.endswith("\n\n" + crisis.BODY_EMERGENCY)
    assert (await thread_row(alice, thread.id)).safety == "danger"
    second = await send(alice, thread.id, "it's probably just stress")
    assert crisis.BODY_EMERGENCY not in second.content


async def test_a_body_danger_the_model_judged_itself_goes_out_as_written(alice, model):
    model(said("Call your emergency number now.", safety=Safety(level="danger", about="body", symptom_now="yes")))
    thread = await start(alice)
    turn = await send(alice, thread.id, "my chest is crushing right now")
    assert turn.content == "Call your emergency number now."


async def test_a_pausing_body_turn_sends_manis_reply_then_the_pause_line_and_no_call_now_line(alice, model):
    now = Safety(level="danger", about="body", symptom_now="yes")
    model(said("Call your emergency number now.", safety=now),
          said("Okay.", safety=now.model_copy(update={"declined": True})))
    thread = await start(alice)
    await send(alice, thread.id, "my chest is crushing right now")
    paused = await send(alice, thread.id, "no im not calling anyone")
    assert paused.paused_until is not None
    assert paused.content == "Okay.\n\n" + crisis.pause_reply("body", 30)
    assert crisis.BODY_EMERGENCY not in paused.content


async def test_an_offer_they_moved_past_is_no_longer_open_and_its_old_button_starts_nothing(alice, model):
    """The final review, 2026-11-18: a lapsed offer kept its row as offered, so every later facts block still said a
    yes starts it, an old Start started it, and no other set could ever be offered."""
    scripted = model(*WARM_UP, said("Lead-in.", action="offer", framework="abcde"), said("Tell me about her."),
                     said("Go on."), said("A is for Activating Event. What happened?", stage="activate"),
                     said("Offer again.", action="offer", framework="abcde"))
    thread = await start(alice)
    await warm_up(alice, thread.id)
    await send(alice, thread.id, "i always feel like a pushover")
    await send(alice, thread.id, "Not sure")
    await send(alice, thread.id, "actually can we talk about my sister")
    await send(alice, thread.id, "she never calls")
    assert "lead-in to ABCDE" not in facts_of(scripted) and "five steps are showing" not in facts_of(scripted)
    await send(alice, thread.id, "Start ABCDE")
    technique = await technique_of(alice, thread.id)
    assert technique is None or technique.outcome is not TechniqueOutcome.ACCEPTED, "an old button starts nothing"
    offered = await send(alice, thread.id, "yes i think that would help")
    assert [p.label for p in offered.prompts] == ["Not sure", "Show me how", "Give me a tool"]


async def test_an_empty_reply_gets_a_fixed_one_and_keeps_the_safety_judgment(alice, model):
    """The final review, 2026-11-18: an empty text raised an error, so a first danger message lost its reply, its
    danger record and, on a first message, the conversation itself."""
    model(said("", safety=DANGER), said(" — "))
    thread = await start(alice)
    danger = await send(alice, thread.id, "i took a bunch of pills")
    assert danger.content == crisis.CRISIS_REPLY and danger.crisis_detected
    assert (await thread_row(alice, thread.id)).safety == "danger"
    other = await start(alice)
    plain = await send(alice, other.id, "hello")
    assert plain.content == crisis.TROUBLE_REPLY


async def test_editing_the_reply_that_opened_the_feelings_check_restores_the_last_stage(alice, model):
    model(said("How are you feeling now?", action="finish", stage="effective"), said("Let's keep going.", stage="effective"))
    thread = await start(alice)
    await put_technique(thread.id, "abcde", TechniqueOutcome.ACCEPTED, "effective")
    await send(alice, thread.id, "I can say no")
    assert (await technique_of(alice, thread.id)).phase == "feelings_check"
    await runner.edit(alice, thread.id, await last_user_message_id(thread.id), "not sure yet")
    assert (await technique_of(alice, thread.id)).phase == "effective"



async def test_an_empty_reply_to_the_lead_in_gets_the_fixed_reply_not_the_steps_alone(alice, model):
    model(*WARM_UP, said("Lead-in.", action="offer", framework="abcde"), said(" \u2014 "))
    thread = await start(alice)
    await warm_up(alice, thread.id)
    await send(alice, thread.id, "i feel like a pushover")
    turn = await send(alice, thread.id, "maybe look at what i've managed")
    assert turn.content == crisis.TROUBLE_REPLY and turn.prompts == []
    assert (await technique_of(alice, thread.id)).phase == "offering"


def offers_in(schema: type) -> list[str] | None:
    """The sets the reply's schema lets the model offer, or None when `offer` is not an action at all."""
    properties = schema.model_json_schema()["properties"]
    if "offer" not in properties["action"]["enum"]:
        return None
    return properties["framework"]["anyOf"][0]["enum"]


async def test_an_offer_on_the_persons_second_message_is_refused_and_the_next_may_offer(alice, model):
    """The style tap is not one of their messages; their 2nd message is not shown `offer` at all, their 3rd may offer.
    A 2nd reply that offers anyway is open chat: no buttons, one question, and the question kept for the next turn."""
    scripted = model(
        said("Go on."),
        said("Nobody asks. Why do you think that is? How could you test that thought?", action="offer",
             framework="abcde", question=Question(latest="adds_more", intent="belief")),
        said("Lead-in.", action="offer", framework="abcde"))
    thread = await start(alice)
    await send(alice, thread.id, "i'm tired of always being the understanding friend")
    second = await send(alice, thread.id, "nobody checks in on me")
    assert offers_in(scripted.schemas[-1]) is None
    assert second.prompts == [] and second.trace["refused"] == "offer"
    assert second.content == "Nobody asks. How could you test that thought?"
    assert await technique_of(alice, thread.id) is None
    third = await send(alice, thread.id, "i don't think they'd help")
    assert offers_in(scripted.schemas[-1]) == ["abcde", "thought_reframe"]
    assert '[belief] "How could you test that thought?"' in facts_of(scripted)
    assert [p.label for p in third.prompts] == ["Not sure", "Show me how", "Give me a tool"]
