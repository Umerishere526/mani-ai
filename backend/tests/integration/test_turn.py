# ABOUTME: Runs whole turns against a live database with a scripted model in place.
# ABOUTME: The model is faked; every write, policy and transition under test is real.

import dataclasses
import uuid

import asyncpg
import pytest

from mani.auth.jwt import Claims
from mani.chat import context, crisis, orchestrator, safety
from mani.config import get_settings
from mani.db import llm_calls, messages as messages_db, profiles, threads
from mani.llm import client
from mani.chat.repairs import PERMISSION_QUESTIONS
from mani.llm.schema import Crisis, Fact, Reply, SmartPrompt, Style, TechniqueState
from mani.models.rows import TechniqueOutcome
from tests.integration.cleanup import remove_test_users

ALICE = uuid.UUID("a0000000-0000-4000-8000-0000000000d1")


def claims_for(user_id: uuid.UUID) -> Claims:
    return Claims(sub=str(user_id), raw={"sub": str(user_id), "role": "authenticated"})


class ScriptedModel:
    """A model that answers from a script, and counts how often it was asked.

    The count is the regression test for the behaviour this port exists to remove: the
    implementation ported from made up to twenty-one provider calls for one user message,
    because every output check it failed was answered by generating again.
    """

    def __init__(self, *replies: Reply) -> None:
        self._replies = list(replies)
        self.calls = 0
        self.last_messages: list[dict] | None = None
        self.all_kwargs: list[dict] = []

    async def __call__(self, messages, schema, **kwargs):
        self.calls += 1
        self.last_messages = messages
        self.all_kwargs.append(kwargs)
        reply = self._replies[min(self.calls - 1, len(self._replies) - 1)]
        return client.Call(
            value=reply,
            model="test/model",
            usage=llm_calls.Usage(input_tokens=100, output_tokens=20),
            latency_ms=1,
            call_id=uuid.uuid4(),
        )


class ScriptedChooser:
    """Stands in for the exercise-selection tool call, counting when it was needed.

    A completing framework is the only turn shape that reaches it, and only when the
    catalog actually has something for that framework - so `calls` is the regression test
    for the second provider call staying rare rather than becoming routine.
    """

    def __init__(self, chosen: str | None = None) -> None:
        self._chosen = chosen
        self.calls = 0
        self.kwargs: dict = {}
        self.candidates: list[dict] = []

    async def __call__(self, candidates, framework_name, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        self.candidates = candidates
        return self._chosen if self._chosen is not None else candidates[0]["id"]


@pytest.fixture(autouse=True)
def no_real_exercise_call(monkeypatch):
    """Every completing framework reaches the exercise pick once the catalog is seeded, and
    no test here may spend a real provider call on it. A test that wants to watch the pick
    installs its own chooser, which replaces this one."""
    monkeypatch.setattr(orchestrator.client, "choose_exercise", ScriptedChooser())


async def reachable() -> bool:
    try:
        conn = await asyncpg.connect(get_settings().database_url, timeout=3)
    except (OSError, asyncpg.PostgresError):
        return False
    await conn.close()
    return True


@pytest.fixture
async def alice():
    if not await reachable():
        pytest.skip("no database reachable; run `supabase start`")
    from mani.db import pool

    await pool.open_pool()
    async with pool.as_admin() as conn:
        await remove_test_users(conn, ALICE)
        await conn.execute(
            "insert into auth.users (id, email) values ($1, 'd1@t.test')", ALICE
        )
    try:
        yield claims_for(ALICE)
    finally:
        async with pool.as_admin() as conn:
            await remove_test_users(conn, ALICE)
        await pool.close_pool()


@pytest.fixture
def model(monkeypatch):
    def install(*replies: Reply) -> ScriptedModel:
        scripted = ScriptedModel(*replies)
        monkeypatch.setattr(orchestrator.client, "complete", scripted)
        return scripted

    return install


async def start(claims: Claims):
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        await profiles.upsert(conn, ALICE, nickname="Al")
        thread, _ = await orchestrator.start_thread(conn, claims)
    return thread


async def past_the_opening(thread):
    """The rounds of conversation the client wants before anything is offered, already had.
    For tests about what happens to an offer, not about when one may come."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set message_count = message_count + 8 where id = $1", thread.id
        )
    return thread


async def after_the_style_tap(thread):
    """The style tap and its opener, which the real greeting flow adds before their first
    message, so their messages count as they do in a real conversation."""
    from mani.db import pool
    from mani.models.rows import SupportStyle

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set conversation_style = $2, message_count = message_count + 2 "
            "where id = $1",
            thread.id, SupportStyle.SUPPORTIVE.value,
        )
    return thread


async def send(claims: Claims, thread_id, content, **kwargs):
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        return await orchestrator.send(conn, claims, thread_id, content, **kwargs)


async def test_a_turn_costs_exactly_one_provider_call(alice, model):
    scripted = model(
        Reply(
            # Everything the six checks look at is wrong at once: leaked script text, a
            # phase jumped to out of order, a duplicated label, and four buttons.
            text="Here you go. What happened?\n\n**Mani:** breathe\n\n(Include prompts: yes/no)",
            prompts=[
                SmartPrompt(label="Tell me more"),
                SmartPrompt(label="tell me more"),
                SmartPrompt(label="Try it", technique="made_up_technique"),
                SmartPrompt(label="Later"),
                SmartPrompt(label="Not now"),
            ],
            state=TechniqueState(technique="abcde", step="balanced"),
            style=Style(shape="mirror and ask"),
        )
    )
    thread = await start(alice)
    turn = await send(alice, thread.id, "I had a hard day")

    assert scripted.calls == 1
    assert "**Mani:**" not in turn.content
    # "Tell me more" goes with the unknown technique it would have explained, and the rest go
    # because ordinary chat carries no buttons.
    assert turn.prompts == []


async def test_a_reply_that_asks_nothing_or_asks_again_costs_one_provider_call_and_is_not_changed(alice, model):
    """A question asked a second time and a reply with no question are what the instructions are
    for; neither costs another call or is changed in code."""
    repeated = "Which part of the exam feels most urgent?"
    comfort = "It is okay to feel that way. Take your time."
    scripted = model(Reply(text=repeated), Reply(text=repeated), Reply(text=comfort))
    thread = await start(alice)

    turns = [
        await send(alice, thread.id, message)
        for message in ("i've an exam in 24 hours and i have not studied at all", "the maths part", "i felt small")
    ]

    assert scripted.calls == 3
    assert [t.content for t in turns] == [repeated, repeated, comfort]


async def test_a_draft_with_a_feeling_they_never_used_is_redrafted_once_and_the_second_is_kept(alice, model):
    """The one tone check kept in code: "An exam sounds incredibly stressful" was said to someone
    who never said stressed. A second draft that still does it is left as drafted, not trimmed."""
    scripted = model(
        Reply(text="An exam in 24 hours sounds incredibly stressful. What do you need first?"),
        Reply(text="An exam in 24 hours and nothing studied. What do you need first?"),
        Reply(text="That sounds so stressful. What do you need first?"),
    )
    thread = await start(alice)
    first = await send(alice, thread.id, "i've an exam in 24 hours and i have not studied at all")
    still = await send(alice, thread.id, "it is the maths part")

    # Two calls for the first turn, then a draft and its one redraft, both still stressful.
    assert scripted.calls == 4
    assert first.content == "An exam in 24 hours and nothing studied. What do you need first?"
    assert still.content == "That sounds so stressful. What do you need first?"


async def test_an_offer_before_the_clients_cadence_allows_it_is_redrafted_once(alice, model):
    """The model is asked once more, told the offer is too early, rather than the offer being
    dropped in code."""
    early = Reply(
        text="There are some questions we could go through together. Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique="structured_problem_solving"),
                 SmartPrompt(label="Keep chatting", decline=True)],
        state=TechniqueState(technique="structured_problem_solving", step="offering"),
    )
    scripted = model(early, Reply(text="With the exam so close, what have you got to work with?"))
    thread = await start(alice)
    turn = await send(alice, thread.id, "i have an exam tomorrow and i don't know where to start")

    assert scripted.calls == 2
    assert turn.content == "With the exam so close, what have you got to work with?"
    assert turn.prompts == []


async def test_behavioral_activation_is_not_offered_to_someone_whose_dog_died(alice, model):
    wrong = Reply(
        text="There are some questions we could go through together. Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique="behavioral_activation"),
                 SmartPrompt(label="Keep chatting", decline=True)],
        state=TechniqueState(technique="behavioral_activation", step="offering"),
    )
    scripted = model(wrong, Reply(text="When the flat feels empty, what do you find yourself wanting to do?"))
    thread = await start(alice)
    await past_the_opening(thread)
    turn = await send(alice, thread.id, "my dog died and i can't stop thinking about him")

    assert scripted.calls == 2
    assert not [p for p in turn.prompts if p.technique]
    assert turn.content.endswith("wanting to do?")


# A message that fits ABCDE (an event, and what they took it to mean), and the facts a model
# reports from it. An offer in a test about something else needs a fit, as a real offer does.
ABCDE_SAID = "my manager shouted at me so I must be useless"
ABCDE_FACTS = [
    Fact(fact="event", words="my manager shouted at me"),
    Fact(fact="meaning", words="I must be useless"),
]


def _offer(technique: str, *facts: Fact) -> Reply:
    return Reply(
        text="There are some questions we could go through together. Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique=technique),
                 SmartPrompt(label="Keep chatting", decline=True)],
        state=TechniqueState(technique=technique, step="offering"),
        facts=list(facts),
    )


_EXAM_FACTS = (
    Fact(fact="practical_problem", words="i have an exam tomorrow"),
    Fact(fact="unsure_what_to_do", words="don't know where to start"),
)


async def test_a_confident_offer_is_made_on_the_second_message_in_any_style(alice, model):
    """muhammad, 2026-10-01: if Mani is confident it should offer, not wait out the old four."""
    from mani.db import pool
    from mani.models.rows import SupportStyle

    scripted = model(
        Reply(text="What is the hardest part of it?"),
        _offer("structured_problem_solving", *_EXAM_FACTS),
    )
    thread = await start(alice)
    async with pool.as_admin() as conn:
        # The style tap and its opener, which the real greeting flow adds before their first message.
        await conn.execute(
            "update public.threads set conversation_style = $2, message_count = message_count + 2 "
            "where id = $1",
            thread.id, SupportStyle.SUPPORTIVE.value,
        )
    await send(alice, thread.id, "i have an exam tomorrow and i don't know where to start")
    turn = await send(alice, thread.id, "i'm confused between studying everything or picking topics")

    assert scripted.calls == 2
    assert [p.technique for p in turn.prompts if p.technique] == ["structured_problem_solving"]
    assert [p.label for p in turn.prompts] == ["Try it", "Keep chatting"]


async def test_a_framework_they_only_point_to_is_never_offered(alice, model):
    """covers spec 0005 AC-16: an event with no meaning yet leads to ABCDE, which is not a fit.
    An offer of it is asked again, told to ask what they took it to mean, and a second such
    offer is removed."""
    from mani.db import pool

    event = Fact(fact="event", words="my brother moved out last week")
    scripted = model(_offer("abcde", event), _offer("abcde", event))
    thread = await start(alice)
    await past_the_opening(thread)
    turn = await send(alice, thread.id, "my brother moved out last week and the flat is quiet")

    assert scripted.calls == 2
    redrafted = scripted.last_messages[-1]["content"]
    assert "nothing they have said fits a set of questions yet" in redrafted
    assert "what they took that event to mean" in redrafted
    assert not any(p.technique for p in turn.prompts)
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.technique is None


async def test_a_full_fit_not_offered_by_the_fourth_message_is_asked_for(alice, model):
    """covers spec 0005 AC-7 reason 6: a clear fit left unoffered makes a chat circle."""
    facts = [Fact(fact="painful_thought", words="nobody cares about me")]
    scripted = model(
        Reply(text="What makes it feel that way?", facts=facts),
        _offer("thought_reframe", *facts),
    )
    thread = await start(alice)
    await past_the_opening(thread)
    turn = await send(alice, thread.id, "my brother moved out and nobody cares about me")

    assert scripted.calls == 2
    assert "offer Thought Reframe (`thought_reframe`)" in scripted.last_messages[-1]["content"]
    assert [p.label for p in turn.prompts] == ["Try it", "Keep chatting"]


async def test_with_nothing_said_that_fits_no_closest_fit_is_owed(alice, model):
    """covers spec 0005 AC-9, AC-14: chat 1 of 5 October. Nothing specific named by the fourth
    message, so nothing is forced and Mani keeps talking."""
    scripted = model(*[Reply(text=text) for text in (
        "What is going on that leads to this stress?",
        "Which of those feels heaviest today?",
        "What has been happening with them lately?",
        "What happened most recently with them?",
    )])
    thread = await after_the_style_tap(await start(alice))
    for message in (
        "i feel emotionally stressed",
        "work pressure, parents pressure, society pressure",
        "yes",
        "i suggest at all of them",
    ):
        turn = await send(alice, thread.id, message)

    assert "closest_fit" not in scripted.last_messages[-1]["content"]
    assert scripted.calls == 4
    assert not any(p.technique for p in turn.prompts)


async def test_the_manager_chat_is_redrafted_from_problem_solving_to_abcde(alice, model):
    """covers spec 0005 AC-7, AC-14: an event and the motive they believe lay behind it fit
    ABCDE. A draft offering Structured Problem Solving at their third message is asked again,
    told what the facts point to and given ABCDE's own offer wording."""
    from mani.db import pool
    from mani.models.rows import SupportStyle

    facts = (
        Fact(fact="event", words="my manager embarrassed me today"),
        Fact(fact="meaning", words="he wants me to fail"),
    )
    scripted = model(
        Reply(text="What happened just then?"),
        Reply(text="What went wrong after that?"),
        _offer("structured_problem_solving", *facts),
        _offer("abcde", *facts),
    )
    thread = await start(alice)
    async with pool.as_admin() as conn:
        # The style tap and its opener, which the real greeting flow adds before their first message.
        await conn.execute(
            "update public.threads set conversation_style = $2, message_count = message_count + 2 "
            "where id = $1",
            thread.id, SupportStyle.SUPPORTIVE.value,
        )
    for message in (
        "I'm very upset. My manager embarrassed me today because he wants me to fail.",
        "EVERYTHING WENT WRONG",
        "I felt really embarrassed.",
    ):
        turn = await send(alice, thread.id, message)

    assert scripted.calls == 4
    redrafted = scripted.last_messages[-1]["content"]
    assert "the facts you listed point to ABCDE (`abcde`)" in redrafted
    assert [p.technique for p in turn.prompts if p.technique] == ["abcde"]


async def test_panic_is_redrafted_from_act_to_dbt_stops_panic_offer(alice, model):
    """covers spec 0005 AC-7, AC-11, AC-14: chat 2 of 5 October. Panicked right now, with no
    action named, fits DBT STOP; an ACT offer is asked again with STOP's panic wording."""
    panic = Fact(fact="overwhelmed_now", words="might have a panic attack")
    scripted = model(
        Reply(text="I am right here with you. What is happening for you right now?"),
        _offer("act_choice_point", panic),
        _offer("dbt_stop", panic),
    )
    thread = await after_the_style_tap(await start(alice))
    await send(alice, thread.id, "I feel like I might have a panic attack.")
    turn = await send(alice, thread.id, "my chest is tight and my thoughts are racing")

    assert scripted.calls == 3
    redrafted = scripted.last_messages[-1]["content"]
    assert "the facts you listed point to DBT STOP (`dbt_stop`)" in redrafted
    assert "when they are panicked right now with no action named" in redrafted
    assert "about to send" not in redrafted.split("rewrite:", 1)[1]
    assert [p.technique for p in turn.prompts if p.technique] == ["dbt_stop"]


async def test_an_offer_still_wrong_after_the_redraft_is_dropped(alice, model):
    """covers spec 0005 AC-8: a framework is started only from an offer the facts agree with."""
    from mani.db import pool

    panic = Fact(fact="overwhelmed_now", words="might have a panic attack")
    scripted = model(
        Reply(text="What is happening for you right now?"),
        _offer("act_choice_point", panic),
        _offer("act_choice_point", panic),
    )
    thread = await after_the_style_tap(await start(alice))
    await send(alice, thread.id, "I feel like I might have a panic attack.")
    turn = await send(alice, thread.id, "my chest is tight and my thoughts are racing")

    assert scripted.calls == 3
    assert not any(p.technique for p in turn.prompts)
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.technique is None

async def test_offering_again_after_they_typed_past_an_offer_is_redrafted_once(alice, model):
    """Typing past an offer is Keep chatting; a second offer in that same reply is asked for again
    once."""
    scripted = model(
        _offer("structured_problem_solving", "clear"),
        _offer("structured_problem_solving", "clear"),
        Reply(text="Which of those two would cost you less if it went wrong?"),
    )
    thread = await start(alice)
    await past_the_opening(thread)
    await send(alice, thread.id, "i have an exam tomorrow and i do not know where to start")
    turn = await send(alice, thread.id, "i could study everything or pick topics")

    assert scripted.calls == 3
    assert turn.content == "Which of those two would cost you less if it went wrong?"
    assert turn.prompts == []


async def test_abcde_is_not_offered_before_they_have_said_what_it_meant(alice, model):
    """Direct offered ACT or a plan at message 2 about a colleague, then ABCDE was the fit."""
    from mani.db import pool

    scripted = model(
        Reply(text="What was that like for you?"),
        _offer("abcde", "clear"),
        Reply(text="When she did that, what did it say to you about yourself?"),
    )
    thread = await start(alice)
    async with pool.as_admin() as conn:
        # The style tap and its opener, before their first message.
        await conn.execute("update public.threads set message_count = message_count + 2 where id = $1", thread.id)
    await send(alice, thread.id, "my colleague questioned two of my recommendations in front of the team")
    turn = await send(alice, thread.id, "i felt embarrassed and did not know how to handle it")

    assert scripted.calls == 3
    assert turn.content.endswith("about yourself?")
    assert not [p for p in turn.prompts if p.technique]


async def test_the_turn_is_stored_and_the_thread_state_follows_it(alice, model):
    model(
        Reply(
            text="Want to try something with me?",
            prompts=[
                SmartPrompt(label="Yes, let's try it", technique="abcde"),
                SmartPrompt(label="Not right now", decline=True),
            ],
            state=TechniqueState(technique="abcde", step="offering"),
            style=Style(shape="warmth lead"),
            facts=ABCDE_FACTS,
        )
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, ABCDE_SAID)

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)

    assert ctx.technique.framework_id == "abcde"
    assert ctx.technique.outcome is TechniqueOutcome.OFFERED
    assert ctx.techniques_offered == ["abcde"]
    assert ctx.recent_styles[-1].shape == "warmth lead"
    assert [m.role for m in (await _history(alice, thread.id))][-2:] == ["user", "mani"]


async def test_tapping_the_offer_records_acceptance(alice, model):
    scripted = model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Yes, let's try it", technique="abcde")],
            state=TechniqueState(technique="abcde", step="offering"),
            facts=ABCDE_FACTS,
        ),
        Reply(
            text="Okay. How has thinking that affected you?",
            state=TechniqueState(technique="abcde", step="consequence"),
        ),
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, ABCDE_SAID)
    await send(alice, thread.id, "Yes, let's try it")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)

    assert ctx.technique.outcome is TechniqueOutcome.ACCEPTED
    # They said the event and what it meant before the offer, so those two stages are not asked.
    assert ctx.technique.phase == "consequence"
    sent = scripted.last_messages[-1]["content"]
    assert "framework_starting: yes" in sent
    assert 'activate: "my manager shouted at me" | belief: "I must be useless"' in sent
    assert "stage: consequence" in sent


async def test_a_typed_yes_to_the_offer_skips_the_stages_they_already_answered(alice, model):
    scripted = model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Yes, let's try it", technique="abcde")],
            state=TechniqueState(technique="abcde", step="offering"),
            facts=ABCDE_FACTS,
        ),
        Reply(
            text="Okay. How has thinking that affected you?",
            state=TechniqueState(technique="abcde", step="consequence", accepted=True),
        ),
    )
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, ABCDE_SAID)
    await send(alice, thread.id, "yes")

    assert (await _stored_stage(alice, thread.id))[0] == "consequence"
    assert "already_told: activate" in scripted.last_messages[-1]["content"]


async def test_a_reply_that_asks_a_stage_they_already_answered_is_recorded_on_the_first_open_stage(
    alice, model
):
    model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Yes, let's try it", technique="abcde")],
            state=TechniqueState(technique="abcde", step="offering"),
            facts=ABCDE_FACTS,
        ),
        Reply(
            text="Okay. What happened?",
            state=TechniqueState(technique="abcde", step="activate"),
        ),
        Reply(
            text="What makes you think that is true?",
            state=TechniqueState(technique="abcde", step="evidence_for"),
        ),
    )
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, ABCDE_SAID)
    await send(alice, thread.id, "Yes, let's try it")
    assert (await _stored_stage(alice, thread.id))[0] == "consequence"

    # The next reply moves on from the stage recorded, so the stages told are never asked later.
    await send(alice, thread.id, "i stopped talking to everyone")
    assert (await _stored_stage(alice, thread.id))[0] == "evidence_for"


async def test_a_typed_yes_reaches_the_model_with_the_question_it_answers(alice, model):
    scripted = model(
        Reply(text="Something happened at work. What did you mean by stuck?"),
        Reply(text="Stuck how, then: unable to start, or unable to finish?"),
    )
    thread = await start(alice)
    await send(alice, thread.id, "I feel stuck")
    await send(alice, thread.id, "Yes")

    final_prompt = scripted.last_messages[-1]["content"]
    assert "their_last: short" in final_prompt
    assert 'answering: "What did you mean by stuck?"' in final_prompt


async def test_tapping_a_button_is_not_read_as_a_short_reply(alice, model):
    scripted = model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Try it", technique="abcde")],
            state=TechniqueState(technique="abcde", step="offering"),
            facts=ABCDE_FACTS,
        ),
        Reply(text="Good. What happened first?", state=TechniqueState(technique="abcde", step="activate")),
    )
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, ABCDE_SAID)
    await send(alice, thread.id, "Try it")

    assert "their_last" not in scripted.last_messages[-1]["content"]
    assert "answering" not in scripted.last_messages[-1]["content"]


async def test_a_four_word_reply_is_not_read_as_an_answer_to_the_last_question(alice, model):
    # covers: AC-4
    scripted = model(
        Reply(text="Something happened at work. What did you mean by stuck?"),
        Reply(text="What part of the day feels most stuck?"),
    )
    thread = await start(alice)
    await send(alice, thread.id, "I feel stuck")
    await send(alice, thread.id, "I don't really know")

    final_prompt = scripted.last_messages[-1]["content"]
    assert "their_last" not in final_prompt
    assert "answering" not in final_prompt


async def test_a_short_reply_while_an_offer_waits_carries_no_answering_line(alice, model):
    # covers: AC-4
    offer = Reply(
        text="I have a sequence of questions that could help. Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique="abcde"),
                 SmartPrompt(label="Keep chatting", decline=True)],
        state=TechniqueState(technique="abcde", step="offering"),
        facts=ABCDE_FACTS,
    )
    scripted = model(offer, Reply(text="What happens right before you pick it up?"))
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, ABCDE_SAID)
    await send(alice, thread.id, "not sure")

    final_prompt = scripted.last_messages[-1]["content"]
    assert "offer_waiting: yes" in final_prompt
    assert "their_last" not in final_prompt
    assert "answering" not in final_prompt


async def test_a_short_reply_on_a_safety_concern_carries_no_answering_line(alice, model):
    # covers: AC-4
    scripted = model(
        Reply(text="What does stuck look like today?"),
        Reply(text="I'm with you. What is happening right now?"),
    )
    thread = await start(alice)
    await send(alice, thread.id, "I feel stuck")
    await send(alice, thread.id, "hurt myself")

    final_prompt = scripted.last_messages[-1]["content"]
    assert "safety: concern" in final_prompt
    assert "their_last" not in final_prompt
    assert "answering" not in final_prompt


async def test_finishing_a_technique_retires_it_without_losing_the_turn(alice, model):
    """The turn after a technique lands is the normal successful path, not an edge case.

    Retiring the row is an UPDATE inside the turn's one transaction: if it is refused,
    the user's message and Mani's reply go down with it. The row has to survive, because
    at_message_count is what the next turn's cooldown is measured from.
    """
    model(Reply(text="How has the rest of the week been?"))
    from mani.db import pool

    thread = await start(alice)
    # The phase clamp only advances one step per turn, so the landed state is set
    # directly rather than walked through all six of abcde's phases.
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="somatic_practice",
        )

    turn = await send(alice, thread.id, "that helped, thanks")

    assert turn.content == "How has the rest of the week been?"

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)

    # Retired, not deleted: the framework is finished but the thread remembers running it.
    assert ctx.technique is not None
    assert ctx.technique.phase is None
    assert ctx.technique.outcome is TechniqueOutcome.ACCEPTED
    assert ctx.technique.at_message_count == 2
    assert "cooldown_passed: no" in context.build(ctx)
    assert [m.role for m in (await _history(alice, thread.id))][-2:] == ["user", "mani"]


async def _retire_abcde_on(alice, thread_id) -> None:
    """Land a thread on ABCDE's final phase, so the next turn is the completing one."""
    from mani.db import pool

    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread_id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="somatic_practice",
        )


@pytest.fixture
async def abcde_exercise(alice):
    """One exercise that names abcde, for the turns where the hand-off should fire.

    A fixture rather than seed content: the real catalog is empty, and the mechanism has
    to be provable before there is anything real in it.
    """
    from mani.db import pool

    async with pool.as_admin() as conn:
        exercise_id = await conn.fetchval(
            "insert into admin.exercises (title, category, audio_path, framework_id) "
            "values ('Settling after ABCDE', 'grounding', 'abcde/settle.mp3', 'abcde') "
            "returning id"
        )
    try:
        yield exercise_id
    finally:
        async with pool.as_admin() as conn:
            await conn.execute("delete from admin.exercises where id = $1", exercise_id)


@pytest.fixture
async def library_exercise(alice):
    """An ordinary library exercise, linked to no framework."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        exercise_id = await conn.fetchval(
            "insert into admin.exercises (title, type, category, audio_path) "
            "values ('Unwinding', 'Breathing', 'Burnout', 'test-unwinding.mp3') returning id"
        )
    try:
        yield exercise_id
    finally:
        async with pool.as_admin() as conn:
            await conn.execute("delete from admin.exercises where id = $1", exercise_id)


@pytest.fixture
async def empty_catalog(alice):
    """Hide the seeded catalog for one test, and put back exactly what was hidden."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        hidden = await conn.fetch(
            "update admin.exercises set is_active = false where is_active returning id"
        )
    try:
        yield
    finally:
        async with pool.as_admin() as conn:
            await conn.execute(
                "update admin.exercises set is_active = true where id = any($1::uuid[])",
                [r["id"] for r in hidden],
            )


async def test_a_completing_framework_with_an_empty_catalog_still_costs_one_call(
    alice, model, monkeypatch, empty_catalog
):
    """With nothing in the catalog the hand-off's second call never happens, and a
    completing turn costs exactly what every other turn costs."""
    scripted = model(Reply(text="How has the rest of the week been?"))
    chooser = ScriptedChooser()
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)

    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)

    turn = await send(alice, thread.id, "that helped, thanks")

    assert scripted.calls == 1
    assert chooser.calls == 0
    assert turn.exercise is None


async def test_a_completing_framework_hands_off_to_its_exercise(
    alice, model, monkeypatch, abcde_exercise
):
    """With something in the catalog for that framework, the turn spends a second call -
    a bound tool call - and the reply carries the exercise it chose."""
    scripted = model(Reply(text="How has the rest of the week been?"))
    chooser = ScriptedChooser()
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)

    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)

    turn = await send(alice, thread.id, "that helped, thanks")

    assert scripted.calls == 1
    assert chooser.calls == 1
    assert chooser.kwargs["purpose"] is llm_calls.Purpose.EXERCISE_SELECT
    assert turn.exercise is not None
    assert turn.exercise.id == abcde_exercise
    assert turn.exercise.framework_id == "abcde"


def _parameters_in_force(monkeypatch, parameters: dict) -> None:
    """Make the mani_base row carry these model parameters, as a seeded prompt file would."""
    from mani.prompts import composer

    original = composer.model_settings

    def settings_with(config):
        model, _, routing = original(config)
        return model, parameters, routing

    monkeypatch.setattr(composer, "model_settings", settings_with)


async def test_reasoning_effort_and_room_reach_every_chat_call(alice, model, monkeypatch):
    """covers spec 0006 AC-1: the first draft and the redraft are asked with the effort and
    the max tokens the prompt row names."""
    _parameters_in_force(monkeypatch, {"temperature": 1, "reasoning_effort": "low", "maxTokens": 4096})
    scripted = model(
        _offer("abcde", *ABCDE_FACTS),  # too early at the first message, so it is redrafted
        Reply(text="What happened just then?"),
    )
    thread = await start(alice)
    await send(alice, thread.id, ABCDE_SAID)

    assert scripted.calls == 2
    for kwargs in scripted.all_kwargs:
        assert kwargs["reasoning_effort"] == "low"
        assert kwargs["max_tokens"] == 4096


async def test_a_prompt_without_an_effort_sends_none(alice, model, monkeypatch):
    _parameters_in_force(monkeypatch, {"temperature": 1})
    scripted = model(Reply(text="What has been going on?"))
    thread = await start(alice)
    await send(alice, thread.id, "hello there")

    assert scripted.all_kwargs[0]["reasoning_effort"] is None
    assert scripted.all_kwargs[0]["max_tokens"] == client.DEFAULT_MAX_TOKENS


async def test_the_exercise_pick_gets_the_effort_and_its_own_room(
    alice, model, monkeypatch, abcde_exercise
):
    """covers spec 0006 AC-1: a model that thinks first must not use up the pick's 200 tokens
    before it makes the tool call, or the pick silently falls back to the first exercise."""
    _parameters_in_force(
        monkeypatch, {"temperature": 1, "reasoning_effort": "low", "exerciseMaxTokens": 1024}
    )
    model(Reply(text="How has the rest of the week been?"))
    chooser = ScriptedChooser()
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)

    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)
    await send(alice, thread.id, "that helped, thanks")

    assert chooser.kwargs["reasoning_effort"] == "low"
    assert chooser.kwargs["max_tokens"] == 1024


async def test_the_exercise_pick_keeps_its_small_default_room(alice, model, monkeypatch, abcde_exercise):
    _parameters_in_force(monkeypatch, {"temperature": 1})
    model(Reply(text="How has the rest of the week been?"))
    chooser = ScriptedChooser()
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)

    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)
    await send(alice, thread.id, "that helped, thanks")

    assert chooser.kwargs["reasoning_effort"] is None
    assert chooser.kwargs["max_tokens"] == client.DEFAULT_EXERCISE_MAX_TOKENS == 200


async def test_the_hand_off_chooses_from_the_whole_catalog_for_this_conversation(
    alice, model, monkeypatch, abcde_exercise, library_exercise
):
    """Every active exercise is a candidate, the framework's own listed first, and the
    chooser sees what the person just said - so a library exercise can win on fit."""
    model(Reply(text="How has the rest of the week been?"))
    chooser = ScriptedChooser(chosen=str(library_exercise))
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)

    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)

    turn = await send(alice, thread.id, "that helped, thanks")

    ids = [c["id"] for c in chooser.candidates]
    assert ids[0] == str(abcde_exercise)
    assert str(library_exercise) in ids
    assert {"type": "Breathing", "category": "Burnout"}.items() <= next(
        c for c in chooser.candidates if c["id"] == str(library_exercise)
    ).items()
    assert chooser.kwargs["said"][-1] == "that helped, thanks"
    assert turn.exercise is not None
    assert turn.exercise.id == library_exercise


async def test_an_ordinary_turn_never_reaches_the_exercise_hand_off(
    alice, model, monkeypatch, abcde_exercise
):
    """The second call is scoped to a completing framework, not to having a catalog."""
    model(Reply(text="Tell me more about that."))
    chooser = ScriptedChooser()
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)

    thread = await start(alice)
    turn = await send(alice, thread.id, "I had a hard day")

    assert chooser.calls == 0
    assert turn.exercise is None


async def test_asking_about_an_offer_leaves_it_open(alice, model):
    """A question about the offer is answered and the offer made again, so it is still waiting
    for their answer - unlike carrying on past it, which is Keep chatting."""
    model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Try it", technique="abcde")],
            state=TechniqueState(technique="abcde", step="offering"),
            facts=ABCDE_FACTS,
        ),
        Reply(
            text="We'd look at what happened and what you told yourself about it. Would you like to try it?",
            prompts=[SmartPrompt(label="Try it", technique="abcde"),
                     SmartPrompt(label="Keep chatting", decline=True)],
            state=TechniqueState(technique="abcde", step="offering"),
        ),
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, ABCDE_SAID)
    await send(alice, thread.id, "what would that involve?")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)

    assert ctx.technique.outcome is TechniqueOutcome.OFFERED


async def test_a_model_reported_crisis_does_not_lock_the_thread(alice, model):
    """The model's own crisis judgment no longer locks: a small model over-fires it on
    ordinary distress, pain, or injury. Only the deterministic screen locks. A model report
    is a non-locking concern - the reply stays in the model's words, no event is recorded,
    and the conversation the person came for is not cut off."""
    model(
        Reply(text="I hear you, and I'm right here with you.", crisis=Crisis(reason="hopelessness")),
        Reply(text="What has today been like?"),
    )
    from mani.db import pool

    thread = await start(alice)
    turn = await send(alice, thread.id, "there is no point in me being here")

    assert turn.crisis_detected is False
    assert turn.content != crisis.CRISIS_REPLY
    assert turn.content.strip()

    async with pool.as_admin() as conn:
        event = await conn.fetchrow(
            "select reason from admin.crisis_events where thread_id = $1", thread.id
        )
    assert event is None

    # The thread is not locked, so a following turn is answered normally.
    again = await send(alice, thread.id, "I guess I am still here")
    assert again.crisis_detected is False
    assert again.content.strip()


async def test_the_safety_screen_locks_a_thread_with_no_provider_call(alice, model):
    """An explicit statement is caught before the model is ever asked anything - the
    scripted model has no reply queued, so a call here would raise, not just cost extra."""
    from mani.db import pool

    scripted = model()
    thread = await start(alice)
    turn = await send(alice, thread.id, "I am going to kill myself tonight.")

    assert scripted.calls == 0
    assert turn.crisis_detected is True
    assert turn.content.strip()

    async with pool.as_admin() as conn:
        event = await conn.fetchrow(
            "select reason from admin.crisis_events where thread_id = $1", thread.id
        )
    assert event["reason"] == "safety screen: suicide"


async def test_the_facts_choose_the_framework_without_a_second_call(alice, model):
    """The choice is made in process from the facts the reply carries; an offer they agree with
    costs nothing more."""
    scripted = model(
        Reply(text="How is that affecting your days?"),
        Reply(text="What would it look like to take one step?"),
        _offer("behavioral_activation", Fact(fact="cannot_begin", words="cannot make myself begin")),
    )
    thread = await start(alice)
    await send(alice, thread.id, "I have stopped answering people for a week now.")
    await send(alice, thread.id, "I know what I need to do, I just cannot make myself begin.")
    turn = await send(alice, thread.id, "I keep waiting to want to do something, but it never comes.")

    assert scripted.calls == 3
    assert [p.technique for p in turn.prompts if p.technique] == ["behavioral_activation"]

async def test_a_framework_completing_on_a_crisis_turn_is_still_retired(alice, model):
    """A crisis turn is still a turn. It used to return before the end-of-turn write, so a
    framework that finished on the same message stayed mid-flight forever - and the thread
    locks one way, so nothing would ever correct it."""
    from mani.db import pool

    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)

    turn = await send(alice, thread.id, "I am going to kill myself tonight.")
    assert turn.crisis_detected is True

    # The thread is locked, so the snapshot is read as admin rather than through a turn.
    async with pool.as_admin() as conn:
        row = await conn.fetchrow(
            "select phase, outcome from public.thread_technique_state where thread_id = $1",
            thread.id,
        )
    assert row["phase"] is None
    assert row["outcome"] == TechniqueOutcome.ACCEPTED


async def test_a_clear_wish_to_die_locks_before_any_call(alice, model):
    """"I want to die" is a clear wish to die, so the deterministic screen locks it before the
    model is ever asked - the sole locking authority, not the model. The scripted model has no
    reply queued, so a call here would raise rather than just cost extra."""
    from mani.db import pool

    scripted = model()
    thread = await start(alice)
    turn = await send(alice, thread.id, "I want to die")

    assert scripted.calls == 0
    assert turn.crisis_detected is True
    assert turn.llm_call_id is None

    async with pool.as_admin() as conn:
        event = await conn.fetchrow(
            "select reason from admin.crisis_events where thread_id = $1", thread.id
        )
    assert event["reason"] == "safety screen: suicide"


async def test_a_crisis_thread_refuses_another_turn(alice, model):
    # A deterministic crisis locks the thread; the model is never called for the first turn.
    model()
    thread = await start(alice)
    await send(alice, thread.id, "I want to die")

    from mani.errors import ServiceError

    with pytest.raises(ServiceError):
        await send(alice, thread.id, "are you there")


async def test_a_retried_send_returns_the_first_reply_without_paying_again(alice, model):
    scripted = model(Reply(text="I'm here. What happened?"), Reply(text="A different answer."))
    thread = await start(alice)
    client_id = uuid.uuid4()

    first = await send(alice, thread.id, "hello", client_message_id=client_id)
    again = await send(alice, thread.id, "hello", client_message_id=client_id)

    assert scripted.calls == 1
    assert again.was_duplicate is True
    assert again.content == first.content


async def test_a_title_is_written_once_the_thread_has_an_exchange(alice, model):
    """`message_count == 3` exactly was the reference's gate; one crisis turn writes a
    single message, moved the count past it, and the thread was never titled."""
    model(
        Reply(text="Go on."),
        Reply(text="I see.", title='"Replaying a hard day at work."'),
    )
    from mani.db import pool

    thread = await start(alice)
    await send(alice, thread.id, "work was hard")
    turn = await send(alice, thread.id, "I keep replaying it")

    assert turn.title == "Replaying a hard day at work"
    async with pool.as_user(alice) as conn:
        assert (await threads.get(conn, thread.id, ALICE)).title == turn.title


async def test_starting_a_chat_twice_reuses_the_untouched_thread(alice):
    """Tapping "new chat" repeatedly used to leave a trail of empty threads."""
    from mani.db import pool

    async with pool.as_user(alice) as conn:
        first, created_first = await orchestrator.start_thread(conn, alice)
        second, created_second = await orchestrator.start_thread(conn, alice)

    assert second.id == first.id
    assert created_first is True and created_second is False

    async with pool.as_user(alice) as conn:
        history = await messages_db.recent_for_context(conn, first.id, ALICE)
    assert len(history) == 1, "a reused thread must not get a second greeting"


async def test_starting_a_chat_after_speaking_makes_a_new_one(alice, model):
    model(Reply(text="Go on."))
    from mani.db import pool

    first = await start(alice)
    await send(alice, first.id, "work was hard")

    async with pool.as_user(alice) as conn:
        second, created = await orchestrator.start_thread(conn, alice)

    assert second.id != first.id and created is True


async def test_buttons_are_returned_only_on_manis_newest_message(alice, model):
    """Buttons are presentation, not history. The reference kept them on old rows and
    cleaned up with an UPDATE, so a failed write left stale offers tappable."""
    model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Yes, let's try it", technique="abcde")],
            facts=ABCDE_FACTS,
        ),
        Reply(text="Good. What happened first?"),
    )
    from mani.db import pool
    from mani.routers.serializers import to_messages

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, ABCDE_SAID)
    await send(alice, thread.id, "Yes, let's try it")

    async with pool.as_user(alice) as conn:
        history = await messages_db.recent_for_context(conn, thread.id, ALICE)
        live = await messages_db.latest_mani_id(conn, thread.id, ALICE)

    rendered = to_messages(history, live)
    # The offer's words are composed by the backend, ending on the client's permission question.
    offer = next(m for m in rendered if any(q in m.content for q in PERMISSION_QUESTIONS.values()))
    newest = rendered[-1]

    assert newest.id == live and newest.content == "Good. What happened first?"
    assert offer.prompts == [], "an answered offer must not stay tappable"
    assert [m for m in rendered if m.prompts] == []
    # What the person chose stays in the record even once the offer is gone.
    assert [m.selected_prompt for m in rendered if m.selected_prompt] == [
        "Yes, let's try it"
    ]


async def test_a_failed_summary_is_logged_and_does_not_break_the_thread(
    alice, model, monkeypatch, caplog
):
    """Summarization is allowed to fail - it costs Mani some memory, not a reply. The
    swallow must leave a trace, or a silently dead summary looks like working code."""
    from mani import summarize

    model(Reply(text="Go on."))
    thread = await start(alice)
    await send(alice, thread.id, "work was hard")

    async def explode(*_args, **_kwargs):
        raise RuntimeError("provider is down")

    monkeypatch.setattr(summarize, "update", explode)
    with caplog.at_level("ERROR"):
        await summarize.update_quietly(alice, thread.id)

    assert "summarization failed" in caplog.text
    assert [m.content for m in await _history(alice, thread.id)][-1] == "Go on."


async def _history(claims: Claims, thread_id):
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        return await messages_db.recent_for_context(conn, thread_id, ALICE)


async def test_a_concern_pauses_a_running_framework_for_that_turn(alice, model):
    """The specification: avoid continuing the framework until the safety concern has been
    addressed. The model is told, gets no stage question to ask, and cannot advance or open
    a framework on this turn - the framework resumes where it stood once the concern passes."""
    scripted = model(
        Reply(
            text="Thank you for telling me. I'm with you.",
            prompts=[SmartPrompt(label="Try this", technique="thought_reframe")],
            state=TechniqueState(technique="abcde", step="consequence"),
        )
    )
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="belief",
        )

    turn = await send(alice, thread.id, "honestly I don’t want to be here anymore")

    sent = scripted.last_messages[-1]["content"]
    assert "safety: concern" in sent
    assert "stage_ask" not in sent and "active_framework" not in sent
    assert not any(p.technique for p in turn.prompts)

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.technique.phase == "belief"


async def test_a_new_chat_after_a_crisis_carries_the_flag_but_not_the_lock(alice, model):
    """New chat must not become a way round the crisis path, and must not lock someone out
    either: the next conversation opens, and the model is told to stay gentle and near
    support. What was said is never carried across - only that it happened."""
    scripted = model(Reply(text="I'm glad you came back. What is on your mind?"))
    from mani.db import pool

    first = await start(alice)
    await send(alice, first.id, "I am going to kill myself")  # the screen locks this thread

    async with pool.as_user(alice) as conn:
        second, created = await threads.create_or_reuse(conn, ALICE)
    assert created and second.id != first.id

    await send(alice, second.id, "hi again")
    assert "recent_crisis: yes" in scripted.last_messages[-1]["content"]


async def test_a_finished_framework_no_longer_counts_as_running(alice, model):
    """Retired means finished. The row stays so the cooldown can be measured from it, but it
    must not keep stripping every later technique button as though the framework were live."""
    model(
        Reply(
            text="Would you like to try another way of looking at it?",
            prompts=[SmartPrompt(label="Yes, let's try", technique="thought_reframe")],
            state=TechniqueState(technique="thought_reframe", step="offering"),
            facts=[Fact(fact="painful_thought", words="nobody cares about me")],
        )
    )
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            # Finished long enough ago that the cooldown has passed: what this checks is that
            # the finished row no longer blocks offers, not the cooldown itself.
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=-context.COOLDOWN_AFTER_COMPLETE, phase=None,
        )

    turn = await send(alice, thread.id, "something else happened today and nobody cares about me")
    assert [p.technique for p in turn.prompts] == ["thought_reframe"]


async def test_the_facts_are_read_again_after_a_declined_offer(alice, model):
    """A declined offer does not switch off the choice: once its cooldown has passed, what they
    say next can lead to a different framework."""
    from mani.db import pool

    scripted = model(
        Reply(text="What has that been like?"),
        Reply(text="What would one step look like?"),
        _offer("behavioral_activation", Fact(fact="cannot_begin", words="cannot make myself begin")),
    )
    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.DECLINED,
            at_message_count=-context.CLEAR_COOLDOWN_AFTER_DECLINE, phase=None,
        )
    await send(alice, thread.id, "I have stopped answering people for a week now.")
    await send(alice, thread.id, "I know what I need to do, I just cannot make myself begin.")
    turn = await send(alice, thread.id, "I keep waiting to want to do something, but it never comes.")

    assert scripted.calls == 3
    assert [p.technique for p in turn.prompts if p.technique] == ["behavioral_activation"]

async def test_tapping_decline_records_it_even_when_the_model_reports_no_state(alice, model):
    """After a decline there is no technique to report, so state: null is the model doing
    what the schema asks. The decline is the button's meaning, not the model's to confirm."""
    model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Yes, let's try it", technique="abcde"),
                     SmartPrompt(label="Not right now", decline=True)],
            state=TechniqueState(technique="abcde", step="offering"),
            facts=ABCDE_FACTS,
        ),
        Reply(text="That's fine. What would help most right now?"),
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, ABCDE_SAID)
    await send(alice, thread.id, "Not right now")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.technique.outcome is TechniqueOutcome.DECLINED
    assert "active_framework" not in context.build(ctx)


async def test_a_reply_that_repairs_empty_fails_cleanly_and_stores_nothing(alice, model):
    """A reply that was only leaked script metadata is empty once cleaned. It must fail as a
    retryable turn, not reach the messages_content_not_empty constraint as a 500."""
    model(Reply(text="(Include prompts: Yes, No)"))
    from mani.errors import ServiceError

    thread = await start(alice)
    with pytest.raises(ServiceError) as raised:
        await send(alice, thread.id, "hello")
    assert raised.value.retryable
    assert [m.role for m in await _history(alice, thread.id)] == ["mani"]  # the greeting only


async def test_an_imminent_action_reaches_the_offer_on_the_first_message(alice, model):
    """The two-exchange wait exists so a framework is not offered on a first hint. STOP is
    the case where waiting is the failure: the message may be sent before a third turn."""
    scripted = model(Reply(text="Before you send it, can we pause for a moment?"))
    thread = await start(alice)
    await send(alice, thread.id, "I am furious and I am about to send a message I will regret")

    sent = scripted.last_messages[-1]["content"]
    assert "offer: offering" in sent and "offer_ask" in sent
    assert "framework_shortlist" not in sent


async def test_a_new_chat_asks_how_the_person_wants_to_be_spoken_to(alice):
    thread = await start(alice)
    [first] = await _history(alice, thread.id)
    assert first.content == "Hi Al. It's MANI. How would you like me to speak with you today?"
    assert [o["label"] for o in first.prompt_options] == ["Direct", "Supportive", "Reflective"]


async def test_choosing_a_style_sets_it_and_opens_in_it_with_no_model_call(alice, model):
    """The client's cadence: greeting, style selection, then that style's opening question.
    The opener is fixed wording from the spec, so it costs nothing to say."""
    scripted = model(Reply(text="What is happening for you?"))
    from mani.db import pool

    thread = await start(alice)
    turn = await send(alice, thread.id, "Reflective")

    assert turn.content == "What's on your mind today?"
    assert turn.prompts == []
    assert scripted.calls == 0
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.thread.conversation_style.value == "reflective"

    await send(alice, thread.id, "I keep going over an argument with my sister")
    assert "conversation_style: reflective" in scripted.last_messages[-1]["content"]


async def test_the_same_message_sent_twice_at_once_is_answered_and_paid_for_once(alice, model):
    """A mobile client retrying while the first request is still waiting on the model. Both
    used to pass the duplicate check, both paid for a generation, and the second returned a
    reply that was never stored."""
    import asyncio

    scripted = model(Reply(text="What has been the hardest part?"))
    real = orchestrator.client.complete

    async def slow(*args, **kwargs):
        await asyncio.sleep(0.3)  # long enough that the second request arrives mid-call
        return await real(*args, **kwargs)

    orchestrator.client.complete = slow
    try:
        thread = await start(alice)
        client_message_id = uuid.uuid4()
        first, second = await asyncio.gather(
            send(alice, thread.id, "work has been hard lately", client_message_id=client_message_id),
            send(alice, thread.id, "work has been hard lately", client_message_id=client_message_id),
        )
    finally:
        orchestrator.client.complete = real

    assert scripted.calls == 1
    assert first.message_id == second.message_id
    assert first.content == second.content


async def test_a_message_id_reused_in_another_chat_is_refused_not_answered(alice, model):
    """The key is per person, so a reuse in a second chat used to return the first chat's
    reply - a message from another conversation, and nothing written where it was sent."""
    from mani.errors import ErrorCategory, ServiceError

    model(Reply(text="What has been the hardest part?"))
    first_chat = await start(alice)
    client_message_id = uuid.uuid4()
    await send(alice, first_chat.id, "work has been hard lately", client_message_id=client_message_id)

    from mani.db import pool

    async with pool.as_user(alice) as conn:
        second_chat, _ = await threads.create_or_reuse(conn, ALICE)
    with pytest.raises(ServiceError) as refused:
        await send(alice, second_chat.id, "a different chat", client_message_id=client_message_id)
    assert refused.value.category is ErrorCategory.CONFLICT


async def test_two_summaries_started_together_pay_for_one(alice, monkeypatch):
    """A summary runs after the reply, in the background. A second message arriving before it
    has committed schedules another over the same messages - two generations, one kept."""
    import asyncio

    from mani import summarize
    from mani.llm.schema import Extraction

    calls = 0

    async def slow_summary(messages, schema, **kwargs):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.3)
        return client.Call(value=Extraction(summary="The user talked about work."),
                           model="test/model", usage=llm_calls.Usage(), latency_ms=1,
                           call_id=uuid.uuid4())

    monkeypatch.setattr(orchestrator.client, "complete",
                        ScriptedModel(Reply(text="Go on.")))
    thread = await start(alice)
    await send(alice, thread.id, "work was hard")
    monkeypatch.setattr(summarize.client, "complete", slow_summary)

    await asyncio.gather(
        summarize.update_quietly(alice, thread.id), summarize.update_quietly(alice, thread.id)
    )
    assert calls == 1


async def test_past_the_daily_limit_a_turn_is_refused_before_anything_is_paid(
    alice, model, monkeypatch
):
    from mani.config import get_settings
    from mani.errors import ErrorCategory, ServiceError

    scripted = model(Reply(text="What has been the hardest part?"))
    monkeypatch.setattr(get_settings(), "daily_message_limit", 1)
    thread = await start(alice)
    await send(alice, thread.id, "work has been hard lately")

    with pytest.raises(ServiceError) as refused:
        await send(alice, thread.id, "and it's getting worse")
    assert refused.value.category is ErrorCategory.RATE_LIMITED
    assert scripted.calls == 1


async def test_a_crisis_is_still_answered_past_the_daily_limit(alice, model, monkeypatch):
    """The limit caps what can be spent, never whether someone in danger gets a reply: the
    safety screen runs first and answers with no model call at all."""
    from mani.config import get_settings

    model(Reply(text="What has been the hardest part?"))
    monkeypatch.setattr(get_settings(), "daily_message_limit", 1)
    thread = await start(alice)
    await send(alice, thread.id, "work has been hard lately")

    turn = await send(alice, thread.id, "I am going to kill myself")
    assert turn.crisis_detected


async def test_finishing_a_framework_always_offers_chat_more_and_the_library(alice, model):
    """The client's cadence ends every framework on the same two choices. Left to the model
    they came back mislabeled ("Something else"), or not at all, on the reply that ends it."""
    model(Reply(text="Your shoulders feel looser. Does that feel right? What would you like next?",
                prompts=[SmartPrompt(label="Something else")]))
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="somatic_practice",
        )

    turn = await send(alice, thread.id, "my shoulders feel a bit looser")
    assert [(p.label, p.library) for p in turn.prompts] == [
        ("Chat More", None), ("Go to Library", "home"),
    ]


async def test_the_body_check_in_waits_for_their_answer_before_the_two_choices(alice, model):
    """The client's order: ask about the body, mirror what they notice, then Chat More / Go to
    Library. Observed: the model put both on the check-in question, and they came again on the
    reply after it."""
    model(Reply(text="What are you noticing in your body now, compared with when we started?",
                prompts=[SmartPrompt(label="Chat More"),
                         SmartPrompt(label="Go to Library", library="home")],
                state=TechniqueState(technique="abcde", step="somatic_checkin")))
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="balanced",
        )

    turn = await send(alice, thread.id, "yes, that fits what happened")
    assert turn.prompts == []


async def _land_on(alice, thread_id, phase) -> None:
    from mani.db import pool

    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread_id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase=phase,
        )


PLACES = ["Chest", "Head", "Stomach", "Somewhere else"]


async def test_a_body_they_already_described_is_asked_where_not_handed_off(alice, model):
    """muhammad, 2026-10-02: "a bit lighter in my chest" reached Chat More / Go to Library with no
    practice at all, and tapping Chat More asked about the body again. A body described before
    the check-in is answered with where they feel it."""
    model(
        Reply(text="You feel a bit lighter. What would you like to do next?",
              state=TechniqueState(technique="abcde", step="somatic_checkin")),
        Reply(text="Your chest feels lighter. What would you like to do next?",
              state=TechniqueState(technique="abcde", step="somatic_checkin")),
    )
    thread = await start(alice)
    await _land_on(alice, thread.id, "balanced")

    turn = await send(alice, thread.id, "a bit lighter")
    assert turn.content.startswith("You feel a bit lighter.")
    assert turn.content.endswith("Where are you feeling that most right now?")
    assert [p.label for p in turn.prompts] == PLACES

    named = await send(alice, thread.id, "in my chest")
    assert "Place one hand on your chest." in named.content


async def test_the_body_is_asked_about_once_then_where_then_the_practice(alice, model):
    """muhammad, 2026-10-02: "yes" to the body check-in got the same question back, and "idk"
    ended the chat on Chat More. Yes leads to where; idk leads to where again, with its buttons;
    a place leads to its practice; and the two choices come only after the practice."""
    model(
        Reply(text="You were able to stay with the pause. How has it been?",
              state=TechniqueState(technique="abcde", step="somatic_checkin")),
        Reply(text="It feels a little better. What are you noticing in your body right now?",
              state=TechniqueState(technique="abcde", step="somatic_checkin")),
        Reply(text="It is not always easy to say where. Is it your chest or your shoulders?",
              state=TechniqueState(technique="abcde", step="somatic_practice")),
        Reply(text="Chest, I see.", state=TechniqueState(technique="abcde", step="somatic_practice")),
        Reply(text="Panic comes in waves. Would you like the library?"),
    )
    thread = await start(alice)
    await _land_on(alice, thread.id, "balanced")

    checked_in = await send(alice, thread.id, "not a 100% but a little better")
    assert checked_in.content.endswith("What are you noticing in your body right now?")

    said_yes = await send(alice, thread.id, "yes")
    assert said_yes.content.count("noticing in your body") == 0
    assert said_yes.content.endswith("Where are you feeling that most right now?")
    assert [p.label for p in said_yes.prompts] == PLACES

    unsure = await send(alice, thread.id, "idk")
    assert unsure.content.endswith("Where are you feeling that most right now?")
    assert [p.label for p in unsure.prompts] == PLACES

    named = await send(alice, thread.id, "Chest")
    assert "Place one hand on your chest." in named.content
    assert named.prompts == []

    after = await send(alice, thread.id, "I feel calmer for a second, then it comes back")
    assert [(p.label, p.library) for p in after.prompts] == [
        ("Chat More", None), ("Go to Library", "home"),
    ]


async def test_declining_the_body_check_goes_to_the_two_choices(alice, model):
    model(Reply(text="You would rather not check in. Would you like to keep chatting or go to the Library?",
                state=TechniqueState(technique="abcde", step="somatic_checkin")))
    thread = await start(alice)
    await _land_on(alice, thread.id, "balanced")

    turn = await send(alice, thread.id, "not now")

    assert [(p.label, p.library) for p in turn.prompts] == [
        ("Chat More", None), ("Go to Library", "home"),
    ]


async def test_a_choice_already_made_is_not_offered_again(alice, model):
    """If they have already said Chat More, the ending reply just carries on talking."""
    model(Reply(text="We can keep talking. What's on your mind now?"))
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="somatic_practice",
        )

    turn = await send(alice, thread.id, "Chat More")
    assert turn.prompts == []


async def test_carrying_on_past_an_offer_is_keep_chatting(alice, model):
    """muhammad, 2026-09-24: someone who types on without answering the offer has chosen to keep
    chatting. Observed: "Would you like to try it?" came back on the very next reply, and the
    one after."""
    offer = Reply(
        text="I have a sequence of questions that could help. Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique="abcde"),
                 SmartPrompt(label="Tell me about this"),
                 SmartPrompt(label="Keep chatting", decline=True)],
        state=TechniqueState(technique="abcde", step="offering"),
        facts=ABCDE_FACTS,
    )
    # What the model actually does: reports no answer either way, and makes the offer again.
    offered_again = offer.model_copy(update={
        "text": "You pick the phone back up. I have a sequence of questions that could help. "
                "Would you like to try it?",
    })
    model(offer, offered_again)
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, ABCDE_SAID)
    turn = await send(alice, thread.id, "every time I try to start I pick the phone back up")

    assert turn.prompts == []
    assert turn.content == "You pick the phone back up."
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.technique.outcome is TechniqueOutcome.DECLINED


async def test_an_offer_they_typed_past_is_flagged_then_closed(alice, model):
    """The model is told, on the turn itself, that its offer is waiting and they typed instead;
    a reply that neither re-offers nor reports an answer has let it go, and so does the offer."""
    offer = Reply(
        text="I have a sequence of questions that could help. Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique="abcde"),
                 SmartPrompt(label="Tell me about this"),
                 SmartPrompt(label="Keep chatting", decline=True)],
        state=TechniqueState(technique="abcde", step="offering"),
        facts=ABCDE_FACTS,
    )
    scripted = model(offer, Reply(text="You pick the phone back up. What happens right before?"))
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, ABCDE_SAID)
    await send(alice, thread.id, "every time I try to start I pick the phone back up")

    sent = scripted.last_messages[-1]["content"]
    assert "offer_waiting: yes" in sent
    # The offering stage's question is the offer itself; handing it over again is asking for it.
    assert not any(line.startswith("stage_ask:") for line in sent.splitlines())
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.technique.outcome is TechniqueOutcome.DECLINED


async def test_asking_for_a_declined_framework_themselves_starts_it(alice, model):
    """Someone who carried on past an offer and then asks for that help themselves has said
    yes, even before the cooldown would let Mani offer it again. Observed: Mani began the
    questions in its own words while nothing was running."""
    offer = Reply(
        text="I have a sequence of questions that could help. Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique="abcde"),
                 SmartPrompt(label="Tell me about this"),
                 SmartPrompt(label="Keep chatting", decline=True)],
        state=TechniqueState(technique="abcde", step="offering"),
        facts=ABCDE_FACTS,
    )
    model(
        offer,
        Reply(text="You keep replaying it. Which part stays with you?"),
        Reply(text="Okay. We'll take it one step at a time together. What happened?",
              state=TechniqueState(technique="abcde", step="activate", accepted=True)),
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, ABCDE_SAID)
    await send(alice, thread.id, "I keep replaying it")
    await send(alice, thread.id, "actually I'd like some help looking at it")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert (ctx.technique.framework_id, ctx.technique.outcome, ctx.technique.phase) == (
        "abcde", TechniqueOutcome.ACCEPTED, "activate",
    )


async def test_a_declined_framework_can_be_offered_again_after_a_few_replies(alice, model):
    """muhammad, 2026-09-24: after "I want to keep talking", Mani checks again after a few
    more messages - the same framework if it still fits best."""
    offer = Reply(
        text="We could look at what happened and what you told yourself about it. Would you like to try?",
        prompts=[SmartPrompt(label="Yes, let's try it", technique="abcde"),
                 SmartPrompt(label="Tell me more"),
                 SmartPrompt(label="I want to keep talking", decline=True)],
        state=TechniqueState(technique="abcde", step="offering"),
        facts=ABCDE_FACTS,
    )
    # Each reply asks something different: a question repeated word for word is redrafted.
    chats = [
        Reply(text=text) for text in (
            "What else has been on your mind about it?",
            "When does it come back to you most?",
            "Who was in the room when it happened?",
            "How did the evening go afterwards?",
            "What would you want to say to them now?",
        )
    ]
    # The first offer comes before the client's cadence allows it, so it costs one redraft.
    model(offer, *chats, offer)
    thread = await start(alice)
    await send(alice, thread.id, ABCDE_SAID)
    await send(alice, thread.id, "I want to keep talking")
    for text in ("it keeps coming back", "I replay it at night", "I can't let it go"):
        await send(alice, thread.id, text)

    again = await send(alice, thread.id, "maybe I do want to look at it")
    assert [p.technique for p in again.prompts if p.technique] == ["abcde"]


async def test_the_body_check_in_is_sent_from_the_script_not_reworded(alice, model):
    """The client: the somatic flow follows the supplied script exactly (2026-09-24)."""
    model(
        Reply(
            text="How does your body feel after all that?",
            state=TechniqueState(technique="abcde", step="somatic_checkin"),
        ),
    )
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="balanced",
        )

    turn = await send(alice, thread.id, "yes, that fits what happened")
    assert turn.content.endswith("What are you noticing in your body right now?")


async def _stored_stage(alice, thread_id):
    from mani.db import pool

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread_id, ALICE)
    return ctx.technique.phase, ctx.technique.holds


async def _stand_at(alice, thread_id, phase: str) -> None:
    from mani.db import pool

    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread_id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase=phase,
        )


async def test_a_hold_is_counted_in_the_database_and_cleared_by_the_next_move(alice, model):
    model(
        Reply(text="Put another way: what did it mean to you?",
              state=TechniqueState(technique="abcde", step="belief")),
        Reply(text="What changed after you believed that?",
              state=TechniqueState(technique="abcde", step="consequence")),
    )
    thread = await start(alice)
    await _stand_at(alice, thread.id, "belief")

    await send(alice, thread.id, "what do you mean?")
    assert await _stored_stage(alice, thread.id) == ("belief", 1)

    await send(alice, thread.id, "oh, I see, she thinks I am lazy")
    assert await _stored_stage(alice, thread.id) == ("consequence", 0)


async def test_a_reply_with_no_state_still_moves_the_stored_stage_on(alice, model):
    model(Reply(text="What changed after you believed that?"))
    thread = await start(alice)
    await _stand_at(alice, thread.id, "belief")

    await send(alice, thread.id, "I don't know")

    assert await _stored_stage(alice, thread.id) == ("consequence", 0)


async def test_the_last_stage_is_answered_with_a_conclusion_then_the_body_check_and_nothing_else_asked(alice, model):
    scripted = model(
        Reply(text="Taking the half day is your choice. Is that something you could do today?",
              state=TechniqueState(technique="abcde", step="somatic_checkin")),
    )
    thread = await start(alice)
    await _stand_at(alice, thread.id, "balanced")

    turn = await send(alice, thread.id, "I will ask my manager for a half day")

    assert "they have replied to the last stage" in scripted.last_messages[-1]["content"]
    assert turn.content.startswith("Taking the half day is your choice.\n\n")
    assert "in your body" in turn.content.splitlines()[-1]
    assert turn.content.count("?") == 1
    assert await _stored_stage(alice, thread.id) == ("somatic_checkin", 0)


async def test_not_knowing_what_is_fair_gets_one_gentler_question_then_the_conclusion(alice, model):
    gentler = "That is fine. What is one thing about this that you do know is true?"
    scripted = model(
        Reply(text=gentler, state=TechniqueState(technique="abcde", step="balanced")),
        Reply(text="You said you have lost your confidence, and it is okay not to know yet. Is that right?",
              state=TechniqueState(technique="abcde", step="somatic_checkin")),
    )
    thread = await start(alice)
    await _stand_at(alice, thread.id, "balanced")

    first = await send(alice, thread.id, "i don't know myself. i've lost my confidence")
    assert f"if they say they do not know what would be fair, or cannot put it into words (uses your extra turn): {gentler}" in (
        scripted.last_messages[-1]["content"]
    )
    assert first.content == gentler
    assert await _stored_stage(alice, thread.id) == ("balanced", 1)

    second = await send(alice, thread.id, "i still don't know")
    assert "you have already stayed on the answered stage once" in scripted.last_messages[-1]["content"]
    assert second.content.startswith("You said you have lost your confidence, and it is okay not to know yet.\n\n")
    assert second.content.count("?") == 1
    assert await _stored_stage(alice, thread.id) == ("somatic_checkin", 0)


async def test_a_hold_at_the_last_stage_gets_no_body_check(alice, model):
    model(Reply(text="Put simply: what would be fair to say?",
                state=TechniqueState(technique="abcde", step="balanced")))
    thread = await start(alice)
    await _stand_at(alice, thread.id, "balanced")

    turn = await send(alice, thread.id, "I don't get it")

    assert "in your body" not in turn.content
    assert await _stored_stage(alice, thread.id) == ("balanced", 1)


async def test_a_person_who_wants_to_stop_at_the_last_stage_gets_the_clients_line_and_no_body_check(alice, model):
    model(Reply(text="You want to stop here. Would you like to continue chatting?",
                state=TechniqueState(technique="abcde", step="balanced")))
    thread = await start(alice)
    await _stand_at(alice, thread.id, "balanced")

    turn = await send(alice, thread.id, "I want to stop")

    assert turn.content == "You want to stop here. Would you like to continue chatting?"
    assert await _stored_stage(alice, thread.id) == ("balanced", 0)


async def test_a_safety_concern_at_the_last_stage_gets_no_conclusion_and_no_body_check(alice, model):
    model(Reply(text="Thank you for telling me. I'm with you.",
                state=TechniqueState(technique="abcde", step="somatic_checkin")))
    thread = await start(alice)
    await _stand_at(alice, thread.id, "balanced")

    turn = await send(alice, thread.id, "honestly I don’t want to be here anymore")

    assert "in your body" not in turn.content
    assert await _stored_stage(alice, thread.id) == ("balanced", 0)


async def test_a_request_to_hear_the_question_again_shows_the_model_only_that_question_and_is_held(alice, model):
    scripted = model(Reply(text="Put simply: what did that mean to you?"))
    thread = await start(alice)
    await _stand_at(alice, thread.id, "belief")

    await send(alice, thread.id, "I don't get it")

    prompt = scripted.last_messages[-1]["content"]
    assert "asked_again: yes" in prompt
    assert "answered_ask:" in prompt
    assert "\nstage:" not in prompt
    assert "their_last" not in prompt
    # The reply reported no state, and the code still holds the stage and counts it.
    assert await _stored_stage(alice, thread.id) == ("belief", 1)


async def test_a_second_request_after_the_extra_turn_moves_on(alice, model):
    scripted = model(
        Reply(text="Put simply: what did that mean to you?"),
        Reply(text="That may help with the next one. What changed after you believed that?"),
    )
    thread = await start(alice)
    await _stand_at(alice, thread.id, "belief")

    await send(alice, thread.id, "I don't get it")
    await send(alice, thread.id, "I still don't get it")

    prompt = scripted.last_messages[-1]["content"]
    assert "hold_used: yes" in prompt and "asked_again" not in prompt
    assert await _stored_stage(alice, thread.id) == ("consequence", 0)


URGE = "I keep typing the message and deleting it"
LOGGER = "mani.chat.orchestrator"


def _flagged(kind, text="What do you notice right now?", step="consequence", **extra) -> Reply:
    return Reply(
        text=text, state=TechniqueState(technique="abcde", step=step),
        crisis=Crisis(reason="SECRET words the person used", category=kind), **extra,
    )


@pytest.mark.parametrize("kind", [c.value for c in safety.Category])
async def test_a_flag_of_a_real_kind_pauses_a_running_framework_and_leaves_the_reply_alone(
    alice, model, caplog, kind
):
    model(_flagged(kind))
    thread = await start(alice)
    await _stand_at(alice, thread.id, "belief")

    with caplog.at_level("INFO", logger=LOGGER):
        turn = await send(alice, thread.id, URGE)

    assert turn.content == "What do you notice right now?"
    assert await _stored_stage(alice, thread.id) == ("belief", 0)
    assert f"framework paused: concern {kind}" in caplog.text


@pytest.mark.parametrize("category", [None, "", "banana", "OTHERS", 3])
async def test_a_flag_with_no_readable_kind_pauses_as_unspecified(alice, model, caplog, category):
    model(Reply(
        text="What do you notice right now?", state=TechniqueState(technique="abcde", step="consequence"),
        crisis=Crisis.model_validate({"reason": "SECRET words", "category": category}),
    ))
    thread = await start(alice)
    await _stand_at(alice, thread.id, "belief")

    with caplog.at_level("INFO", logger=LOGGER):
        await send(alice, thread.id, URGE)

    assert await _stored_stage(alice, thread.id) == ("belief", 0)
    assert "framework paused: concern unspecified" in caplog.text
    assert "banana" not in caplog.text and "OTHERS" not in caplog.text


async def test_a_flag_of_other_is_a_reply_with_no_flag_in_a_running_framework(alice, model, caplog):
    model(_flagged("other"))
    thread = await start(alice)
    await _stand_at(alice, thread.id, "belief")

    with caplog.at_level("INFO", logger=LOGGER):
        await send(alice, thread.id, URGE)

    assert await _stored_stage(alice, thread.id) == ("consequence", 0)
    assert "concern flagged as other, framework continued" in caplog.text
    assert "framework paused" not in caplog.text


async def test_the_log_carries_the_kind_and_never_what_the_model_wrote_about_the_person(alice, model, caplog):
    model(_flagged("self_harm"))
    thread = await start(alice)
    await _stand_at(alice, thread.id, "belief")

    with caplog.at_level("INFO", logger=LOGGER):
        await send(alice, thread.id, URGE)

    assert "model flagged a safety concern" in caplog.text
    assert "self_harm" in caplog.text
    assert "SECRET" not in caplog.text


async def test_a_turn_the_screen_blocks_pauses_whatever_kind_the_model_gave(alice, model, caplog):
    model(_flagged("other"))
    thread = await start(alice)
    await _stand_at(alice, thread.id, "belief")

    with caplog.at_level("INFO", logger=LOGGER):
        await send(alice, thread.id, "honestly I don’t want to be here anymore")

    assert await _stored_stage(alice, thread.id) == ("belief", 0)
    assert "framework paused: screen" in caplog.text


async def _make_the_confident_offer(alice, model, kind):
    from mani.db import pool
    from mani.models.rows import SupportStyle

    model(
        Reply(text="What is the hardest part of it?"),
        Reply(
            text="Some questions we could go through together?",
            prompts=[SmartPrompt(label="Try it", technique="structured_problem_solving"), SmartPrompt(label="Keep chatting", decline=True)],
            crisis=Crisis(category=kind), facts=list(_EXAM_FACTS),
        ),
    )
    thread = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set conversation_style = $2, message_count = message_count + 2 where id = $1",
            thread.id, SupportStyle.SUPPORTIVE.value,
        )
    await send(alice, thread.id, "i have an exam tomorrow and i don't know where to start")
    return await send(alice, thread.id, "i'm confused between studying everything or picking topics")


async def test_outside_a_framework_a_flag_of_other_keeps_the_offer(alice, model):
    kept = await _make_the_confident_offer(alice, model, "other")
    assert [p.technique for p in kept.prompts if p.technique] == ["structured_problem_solving"]


async def test_outside_a_framework_a_flag_of_a_real_kind_drops_a_new_offer(alice, model):
    dropped = await _make_the_confident_offer(alice, model, "abuse_or_violence")
    assert not any(p.technique for p in dropped.prompts)


@pytest.mark.parametrize("kind,practice", [(None, True), ("other", True), ("medical_emergency", False)])
async def test_the_body_route_runs_for_other_exactly_as_for_no_flag_and_not_for_a_real_kind(
    alice, model, kind, practice
):
    crisis = Crisis(category=kind) if kind else None
    model(Reply(
        text="What do you notice?", crisis=crisis,
        state=TechniqueState(technique="abcde", step="somatic_checkin"),
    ))
    thread = await start(alice)
    await _stand_at(alice, thread.id, "somatic_checkin")

    await send(alice, thread.id, "my chest feels tight")

    phase, _ = await _stored_stage(alice, thread.id)
    assert (phase == "somatic_practice") is practice


async def test_the_facts_a_draft_reports_are_kept_on_its_call_row_as_ids_never_words(
    alice, model, monkeypatch
):
    """What the router read from the draft's facts is on the cost row, so a missing offer can be
    traced to a dropped fact. The person's words never reach the row, which outlives them."""
    from mani.db import pool

    scripted = model(Reply(
        text="What has today been like?",
        facts=[Fact(fact="event", words="manager shouted at me"),
               Fact(fact="painful_thought", words="never said"),
               Fact(fact="my own label", words="manager shouted at me")],
    ))
    async with pool.as_admin() as conn:
        call_id = await llm_calls.record(
            conn, purpose=llm_calls.Purpose.CHAT, model="test/model", outcome=llm_calls.Outcome.OK,
            usage=llm_calls.Usage(), latency_ms=1, user_id=ALICE,
        )
    real_call = scripted.__call__

    async def with_real_row(messages, schema, **kwargs):
        made = await real_call(messages, schema, **kwargs)
        return dataclasses.replace(made, call_id=call_id)

    monkeypatch.setattr(orchestrator.client, "complete", with_real_row)
    thread = await after_the_style_tap(await start(alice))
    await send(alice, thread.id, "my manager shouted at me today")

    async with pool.as_admin() as conn:
        kept = await conn.fetchval("select facts from admin.llm_calls where id = $1", call_id)
    assert kept == {
        "reported": ["event", "painful_thought"], "unknown": 1, "facts": ["event"],
        "dropped": ["dropped a fact not in their words: painful_thought"],
        "pick": None, "leading": "abcde", "missing": "meaning", "stuck_route": False,
    }
    assert "shouted" not in str(kept) and "my own label" not in str(kept)


# The model may quote their earlier stuck words or only the yes itself.
@pytest.mark.parametrize("stuck_words", ["dont know cant think", "yes"])
async def test_a_yes_to_the_stuck_check_is_offered_abcde_which_starts_at_the_stuck_line(
    alice, model, stuck_words
):
    """covers spec 0009 AC-2, AC-4 and AC-7: after "Are you feeling stuck?" and a yes, ABCDE is
    offered on `stuck` alone, and accepting it passes over "What happened?" with nothing said back."""
    stuck_line = "What goes through your mind when you feel this?"
    scripted = model(
        Reply(text="What has today been like?"),
        Reply(text="That is okay. Are you feeling stuck?"),
        _offer("abcde", Fact(fact="stuck", words=stuck_words)),
        Reply(
            text=f"Okay. I'll guide you through it one step at a time. {stuck_line}",
            state=TechniqueState(technique="abcde", step="belief", accepted=True),
        ),
    )
    thread = await after_the_style_tap(await start(alice))
    await send(alice, thread.id, "i am depressed")
    await send(alice, thread.id, "i dont know cant think of anything")
    offered = await send(alice, thread.id, "yes")

    assert "offer_when_stuck: only if they answered yes" in scripted.last_messages[-1]["content"]
    assert [p.technique for p in offered.prompts if p.technique] == ["abcde"]

    started = await send(alice, thread.id, "Try it")

    sent = scripted.last_messages[-1]["content"]
    assert f"stage_ask: {stuck_line}" in sent
    assert "already_told" not in sent and "stage_if_earlier_missing" not in sent
    assert (await _stored_stage(alice, thread.id))[0] == "belief"
    assert started.content.endswith(stuck_line)
    assert scripted.calls == 4
