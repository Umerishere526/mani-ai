# ABOUTME: Whole turns against a live database with a scripted model: what the one-call turn sends, stores and shows.
# ABOUTME: The model is faked; every write, policy, framework move and safety pause under test is real.

import uuid

import pytest

from mani.chat import crisis, runner
from mani.chat.reply import Event, Person, Question, Safety
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


# Two ordinary exchanges first: an offer may come with the person's 3rd message at the earliest.
WARM_UP = (said("Go on."), said("Tell me more."))


async def warm_up(alice, thread_id) -> None:
    await send(alice, thread_id, "work has been a lot lately")
    await send(alice, thread_id, "my boss keeps adding things")


async def abcde_text(kind: str, style: str = "supportive") -> str:
    from mani.chat import techniques
    from mani.prompts import cache

    framework = (await cache.load()).registry.get("abcde")
    return techniques.steps_text(framework, style) if kind == "steps" else techniques.example_text(framework)


START = ["Start ABCDE", "I need an example", "Talk more first"]


async def test_a_clear_offer_is_the_lead_in_with_its_three_buttons(alice, model):
    model(*WARM_UP, said("Just because a belief feels true doesn't mean it is. How could you test that thought?",
               action="offer", framework="abcde"))
    thread = await start(alice)
    await warm_up(alice, thread.id)
    turn = await send(alice, thread.id, "i always feel like a pushover")
    assert [p.label for p in turn.prompts] == ["Not sure", "Show me how", "Give me a tool"]
    assert (await technique_of(alice, thread.id)).outcome is TechniqueOutcome.OFFERED


async def test_the_offer_runs_lead_in_steps_example_then_start(alice, model):
    """The client's sequence document, 2026-11-18: the steps and the example are hers, sent with no model call."""
    scripted = model(*WARM_UP, said("Lead-in.", action="offer", framework="abcde"),
                     said("A is for Activating Event. What happened?", stage="activate"),
                     said("B is for Belief. What did you tell yourself?", stage="belief"))
    thread = await start(alice)
    await warm_up(alice, thread.id)
    await send(alice, thread.id, "i feel like a pushover")
    steps = await send(alice, thread.id, "Not sure")
    assert scripted.calls == 3 and steps.content == await abcde_text("steps")
    assert [p.label for p in steps.prompts] == START
    example = await send(alice, thread.id, "I need an example")
    assert scripted.calls == 3 and example.content == await abcde_text("example")
    assert [p.label for p in example.prompts] == ["Start ABCDE", "Talk more first"]
    await send(alice, thread.id, "Start ABCDE")
    assert (await technique_of(alice, thread.id)).phase == "activate"
    await send(alice, thread.id, "he dumped a report on me friday")
    technique = await technique_of(alice, thread.id)
    assert technique.outcome is TechniqueOutcome.ACCEPTED and technique.phase == "belief"


async def test_a_typed_reply_to_the_lead_in_gets_the_reply_then_the_steps(alice, model):
    model(*WARM_UP, said("Lead-in.", action="offer", framework="abcde"), said("That's a fair way to start."))
    thread = await start(alice)
    await warm_up(alice, thread.id)
    await send(alice, thread.id, "i feel like a pushover")
    turn = await send(alice, thread.id, "maybe look at what i've actually managed?")
    assert turn.content == "That's a fair way to start.\n\n" + await abcde_text("steps")
    assert [p.label for p in turn.prompts] == START
    assert (await technique_of(alice, thread.id)).phase == "steps"


async def test_talk_more_first_lets_the_offer_lapse_and_it_may_come_back(alice, model):
    model(*WARM_UP, said("Lead-in.", action="offer", framework="abcde"), said("Sure, let's keep talking."),
          said("Lead-in again.", action="offer", framework="abcde"))
    thread = await start(alice)
    await warm_up(alice, thread.id)
    await send(alice, thread.id, "i feel like a pushover")
    await send(alice, thread.id, "Show me how")
    await send(alice, thread.id, "Talk more first")
    technique = await technique_of(alice, thread.id)
    assert technique.outcome is TechniqueOutcome.OFFERED and technique.phase is None, "set aside, not declined"
    again = await send(alice, thread.id, "ok i think i'm ready now")
    assert [p.label for p in again.prompts] == ["Not sure", "Show me how", "Give me a tool"]


async def test_a_declined_framework_is_never_offered_again(alice, model):
    model(*WARM_UP, said("Lead-in.", action="offer", framework="abcde"), said("Okay, we'll leave it.", action="stop"),
          said("Offer again.", action="offer", framework="abcde"))
    thread = await start(alice)
    await warm_up(alice, thread.id)
    await send(alice, thread.id, "i feel like a pushover")
    await send(alice, thread.id, "no, i don't want to do any exercise")
    turn = await send(alice, thread.id, "still feel like a pushover")
    assert turn.prompts == [] and turn.trace["refused"] == "offer"


async def test_after_e_the_feelings_check_then_the_closing_buttons(alice, model):
    model(said("That's a strong shift. How are you feeling now?", action="finish", stage="effective"),
          said("Excellent. You found a path forward."))
    thread = await start(alice)
    await put_technique(thread.id, "abcde", TechniqueOutcome.ACCEPTED, "effective")
    check = await send(alice, thread.id, "I can be a team player and still say no")
    assert [p.label for p in check.prompts] == ["Feel stronger", "Feel more focused", "I'm not sure yet"]
    assert "abcde" not in ((await thread_row(alice, thread.id)).understanding.get("finished") or [])
    closed = await send(alice, thread.id, "Feel more focused")
    assert [p.label for p in closed.prompts] == ["Keep Chatting", "Go to Library", "Finish for Now"]
    assert (await thread_row(alice, thread.id)).understanding["finished"] == ["abcde"]


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
    assert [p.label for p in check.prompts] == ["Feel stronger", "Feel more focused", "I'm not sure yet"]
    assert (await thread_row(alice, thread.id)).understanding["safety_end_check"] == "done"
    closed = await send(alice, thread.id, "Feel stronger")
    assert [p.label for p in closed.prompts][-1] == "Finish for Now"


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


async def test_a_return_check_answer_that_is_fine_marks_the_pause_checked(alice, model):
    model(said("Call now.", safety=DANGER), said("Please call.", safety=DANGER), said("How are things now?"),
          said("Good to hear it."))
    thread = await start(alice)
    await send(alice, thread.id, "i took pills")
    await send(alice, thread.id, "alone")
    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute("update public.chat_pauses set ends_at = now() - interval '1 minute' where user_id = $1",
                           ALICE)
    asked = await send(alice, thread.id, "back now")
    assert asked.paused_until is None
    await send(alice, thread.id, "i'm okay, my sister is here")
    async with pool.as_admin() as conn:
        checked = await conn.fetchval("select checked_at is not null from public.chat_pauses where user_id = $1", ALICE)
    assert checked is True


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


async def test_editing_the_answer_that_marked_a_pause_checked_asks_the_question_again(alice, model):
    """An answer of "I'm fine" marks the pause checked; edited to something unsure, the mark goes with it, so the pause
    still owes the question until they say they are all right."""
    from mani.db import pool

    unsure = Safety(level="unsure", about="themselves")
    _, thread = await _a_pause_that_has_run_out(
        alice, [said("How are things now?"), said("Good to hear it."), said("I'm here. What feels shaky?", safety=unsure)],
        model)
    await send(alice, thread.id, "back now")
    await send(alice, thread.id, "i'm fine")

    async def checked() -> bool:
        async with pool.as_admin() as conn:
            return await conn.fetchval("select checked_at is not null from public.chat_pauses where user_id = $1", ALICE)

    assert await checked() is True
    edited = await runner.edit(alice, thread.id, await last_user_message_id(thread.id), "not really, still shaky")
    assert edited.content == "I'm here. What feels shaky?"
    assert await checked() is False


async def test_the_conversation_paused_in_stops_asking_once_they_said_elsewhere_they_are_all_right(alice, model):
    """muhammad, 2026-11-19: until they say they are all right, in any conversation. The conversation the pause began in
    went on asking, and kept its danger, so its next message could pause with no word from Mani."""
    scripted, paused_in = await _a_pause_that_has_run_out(
        alice, [said("Good to hear it."), said("I'm here with you.", safety=DANGER)], model)
    elsewhere = await start(alice)
    await send(alice, elsewhere.id, "i'm okay, my sister is here")

    back = await send(alice, paused_in.id, "i feel awful again")

    assert back.paused_until is None and back.content == "I'm here with you."
    assert "paused earlier" not in facts_of(scripted)


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


async def test_the_answer_to_the_question_a_new_conversation_opens_with_is_never_refused_for_a_limit(
    alice, model, monkeypatch
):
    """The answer is a safety turn like any other held one: it is answered whatever the limits say."""
    from mani.config import get_settings

    _, _ = await _a_pause_that_has_run_out(alice, [said("Good to hear it.")], model)
    elsewhere = await start(alice)
    monkeypatch.setattr(get_settings(), "minute_message_limit", 1)

    answered = await send(alice, elsewhere.id, "i'm okay, my sister is here")

    assert answered.content == "Good to hear it."


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


async def test_an_owed_return_check_comes_before_the_five_steps(alice, model):
    """A pause elsewhere that has run out owes the question how things are; a lead-in tap does not jump it."""
    from mani.db import pool

    scripted = model(*WARM_UP, said("Lead-in.", action="offer", framework="abcde"), said("Before that, how are things now?"))
    thread = await start(alice)
    await warm_up(alice, thread.id)
    await send(alice, thread.id, "i feel like a pushover")
    other = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute(
            "insert into public.chat_pauses (user_id, thread_id, started_at, ends_at, reason) "
            "values ($1, $2, now() - interval '20 minutes', now() - interval '5 minutes', 'took pills')", ALICE, other.id)
    turn = await send(alice, thread.id, "Not sure")
    assert scripted.calls == 4 and turn.content == crisis.RETURN_CHECK_REPLY


async def test_an_offer_on_the_persons_second_message_is_refused_and_the_next_may_offer(alice, model):
    """The style tap is not one of their messages; their 2nd message gets no offer, their 3rd may."""
    model(said("Go on."), said("Lead-in.", action="offer", framework="abcde"),
          said("Lead-in.", action="offer", framework="abcde"))
    thread = await start(alice)
    await send(alice, thread.id, "i'm tired of always being the understanding friend")
    second = await send(alice, thread.id, "nobody checks in on me")
    assert second.prompts == [] and second.trace["refused"] == "offer"
    assert await technique_of(alice, thread.id) is None
    third = await send(alice, thread.id, "i don't think they'd help")
    assert [p.label for p in third.prompts] == ["Not sure", "Show me how", "Give me a tool"]
