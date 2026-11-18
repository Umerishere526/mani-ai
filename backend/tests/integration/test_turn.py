# ABOUTME: Whole turns against a live database with a scripted model: what the one-call turn sends, stores and shows.
# ABOUTME: The model is faked; every write, policy, framework move and safety pause under test is real.

import uuid

import pytest

from mani.chat import crisis, runner
from mani.chat.reply import Safety
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


async def test_a_clear_offer_shows_the_three_buttons_and_records_it(alice, model):
    model(said("There's a set of questions called ABCDE. Would you like to try it?", action="offer", framework="abcde"))
    thread = await start(alice)
    turn = await send(alice, thread.id, "i always feel like a pushover")
    assert [p.label for p in turn.prompts] == ["Try it", "Tell me more", "Keep chatting"]
    assert (await technique_of(alice, thread.id)).outcome is TechniqueOutcome.OFFERED


async def test_tell_me_more_sends_the_fixed_explanation_with_no_model_call(alice, model):
    scripted = model(said("Offer.", action="offer", framework="abcde"))
    thread = await start(alice)
    await send(alice, thread.id, "i feel like a pushover")
    turn = await send(alice, thread.id, "Tell me more")
    assert scripted.calls == 1
    assert turn.content.startswith("The ABCDE framework has five steps.")
    assert turn.content.endswith("\n\nWould you like to try it?"), "the client's permission question closes it"
    assert [p.label for p in turn.prompts] == ["Try it", "Keep chatting"]


async def test_try_it_then_a_stage_reply_stores_the_stage(alice, model):
    model(said("Offer.", action="offer", framework="abcde"),
          said("A is for Activating Event. What happened?", stage="activate"),
          said("B is for Belief. What did you tell yourself?", stage="belief"))
    thread = await start(alice)
    await send(alice, thread.id, "i feel like a pushover")
    await send(alice, thread.id, "Try it")
    await send(alice, thread.id, "he dumped a report on me friday")
    technique = await technique_of(alice, thread.id)
    assert technique.outcome is TechniqueOutcome.ACCEPTED and technique.phase == "belief"


async def test_a_declined_framework_is_never_offered_again(alice, model):
    model(said("Offer.", action="offer", framework="abcde"), said("Okay, let's keep talking."),
          said("Offer again.", action="offer", framework="abcde"))
    thread = await start(alice)
    await send(alice, thread.id, "i feel like a pushover")
    await send(alice, thread.id, "Keep chatting")
    turn = await send(alice, thread.id, "still feel like a pushover")
    assert turn.prompts == [] and turn.trace["refused"] == "offer"


async def test_the_last_stage_finished_shows_the_closing_buttons(alice, model):
    model(said("Warm close.", action="finish", stage="effective"))
    thread = await start(alice)
    await put_technique(thread.id, "abcde", TechniqueOutcome.ACCEPTED, "effective")
    turn = await send(alice, thread.id, "I can be a team player and still say no")
    assert [p.label for p in turn.prompts] == ["Keep Chatting", "Go to Library", "Finish for Now"]
    assert (await thread_row(alice, thread.id)).understanding["finished"] == ["abcde"]


async def test_a_finish_after_danger_sends_the_end_check_then_the_close(alice, model):
    model(said("Warm close.", action="finish", stage="effective"),
          said("Glad you're safe. Warm close.", action="finish", stage="effective"))
    thread = await start(alice)
    await put_technique(thread.id, "abcde", TechniqueOutcome.ACCEPTED, "effective")
    await put_record(thread.id, {"danger_reached": True, "danger_about": "themselves"})
    first = await send(alice, thread.id, "my new belief is that I'm allowed limits")
    assert first.content == crisis.END_CHECK and first.prompts == []
    closed = await send(alice, thread.id, "i'm okay now, my sister is here")
    assert [p.label for p in closed.prompts][-1] == "Finish for Now"
    assert (await thread_row(alice, thread.id)).understanding["safety_end_check"] == "done"


async def test_overdose_on_the_first_message_gets_manis_reply_and_the_next_message_pauses(alice, model):
    model(said("Call 911 now. Are you alone?", safety=DANGER), said("Please call now.", safety=DANGER))
    thread = await start(alice)
    first = await send(alice, thread.id, "i took a bunch of my sleeping pills")
    assert first.content == "Call 911 now. Are you alone?" and first.paused_until is None and first.crisis_detected
    second = await send(alice, thread.id, "yes alone. i dont want help")
    assert second.paused_until is not None
    assert second.content == crisis.pause_reply("themselves", 15)


async def test_a_paused_person_is_refused_before_anything_is_paid(alice, model):
    scripted = model(said("Call now.", safety=DANGER), said("Please.", safety=DANGER), said("unused"))
    thread = await start(alice)
    await send(alice, thread.id, "i took pills")
    await send(alice, thread.id, "alone")
    with pytest.raises(ServiceError) as refused:
        await send(alice, thread.id, "hello?")
    assert refused.value.category is ErrorCategory.CHAT_PAUSED and scripted.calls == 2


async def test_every_host_failing_on_a_first_danger_message_still_answers(alice, monkeypatch):
    monkeypatch.setattr(client, "complete", all_hosts_down)
    thread = await start(alice)
    turn = await send(alice, thread.id, "i took a bunch of pills")
    assert turn.content == crisis.TROUBLE_REPLY


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


async def test_a_pausing_body_turn_sends_only_the_pause_reply(alice, model):
    now = Safety(level="danger", about="body", symptom_now="yes")
    model(said("Call your emergency number now.", safety=now),
          said("Okay.", safety=now.model_copy(update={"declined": True})))
    thread = await start(alice)
    await send(alice, thread.id, "my chest is crushing right now")
    paused = await send(alice, thread.id, "no im not calling anyone")
    assert paused.paused_until is not None
    assert paused.content == crisis.pause_reply("body", 15) and crisis.BODY_EMERGENCY not in paused.content


async def test_an_offer_they_moved_past_is_no_longer_open_and_its_old_button_starts_nothing(alice, model):
    """The final review, 2026-11-18: a lapsed offer kept its row as offered, so every later facts block still said a
    yes starts it, an old Try it started it, and no other set could ever be offered."""
    scripted = model(said("Offer.", action="offer", framework="abcde"), said("Tell me about her."),
                     said("Go on."), said("A is for Activating Event. What happened?", stage="activate"),
                     said("Offer again.", action="offer", framework="abcde"))
    thread = await start(alice)
    await send(alice, thread.id, "i always feel like a pushover")
    await send(alice, thread.id, "actually can we talk about my sister")
    await send(alice, thread.id, "she never calls")
    assert "Your last reply offered" not in facts_of(scripted)
    await send(alice, thread.id, "Try it")
    technique = await technique_of(alice, thread.id)
    assert technique is None or technique.outcome is not TechniqueOutcome.ACCEPTED, "an old button starts nothing"
    offered = await send(alice, thread.id, "yes i think that would help")
    assert [p.label for p in offered.prompts] == ["Try it", "Tell me more", "Keep chatting"]


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
