# ABOUTME: Runs whole turns against a live database with a scripted model in place.
# ABOUTME: The model is faked; every write, policy and transition under test is real.

import dataclasses
import json
import logging
import uuid
from types import SimpleNamespace

import asyncpg
import pytest

from mani.auth.jwt import Claims
from mani.chat import context, crisis, orchestrator
from mani.config import get_settings
from mani.db import llm_calls, messages as messages_db, profiles, threads
from mani.errors import ErrorCategory, ServiceError
from mani.llm import chain, client
from mani.llm.schema import Crisis, Reply, SmartPrompt, Style, TechniqueState
from mani.models.rows import TechniqueOutcome
from tests.integration.cleanup import remove_test_users

ALICE = uuid.UUID("a0000000-0000-4000-8000-0000000000d1")
# The real exercise pick, kept before the autouse fixture below replaces it in every test.
REAL_CHOOSE_EXERCISE = client.choose_exercise


def claims_for(user_id: uuid.UUID) -> Claims:
    return Claims(sub=str(user_id), raw={"sub": str(user_id), "role": "authenticated"})


class ScriptedModel:
    """A model that answers from a script, and counts how often it was asked.

    The count is the regression test for one chat call per turn: the implementation ported
    from made up to twenty-one provider calls for one user message, because every output
    check it failed was answered by generating again.
    """

    def __init__(self, *replies: Reply) -> None:
        self._replies = list(replies)
        self.calls = 0
        self.last_messages: list[dict] | None = None
        self.last_kwargs: dict = {}

    async def __call__(self, messages, schema, **kwargs):
        self.calls += 1
        self.last_messages = messages
        self.last_kwargs = kwargs
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
        self.instruction: str | None = None

    async def __call__(self, candidates, framework_name, instruction, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        self.candidates = candidates
        self.instruction = instruction
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


async def send(claims: Claims, thread_id, content, **kwargs):
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        return await orchestrator.send(conn, claims, thread_id, content, **kwargs)


async def test_a_turn_makes_one_chat_call_and_does_not_retry_a_malformed_reply(alice, model):
    scripted = model(Reply(text="Here you go. What happened?"))
    thread = await start(alice)
    await send(alice, thread.id, "I had a hard day")

    assert scripted.calls == 1
    assert scripted.last_kwargs["retry_malformed"] is False


async def test_the_model_replies_out_with_only_its_unstorable_parts_taken_out(alice, model):
    """Leaked script text, a stage jumped to, a repeated label and an unknown technique id: the
    words go out as written, and only the technique button and the offer it answered go."""
    written = "Here you go. What happened?\n\n**Mani:** breathe\n\n(Include prompts: yes/no)"
    scripted = model(
        Reply(
            text=written,
            prompts=[
                SmartPrompt(label="Tell me more"),
                SmartPrompt(label="Tell me more"),
                SmartPrompt(label="Try it", technique="made_up_technique"),
                SmartPrompt(label="Later"),
            ],
            state=TechniqueState(technique="abcde", step="examine"),
            style=Style(shape="mirror and ask"),
        )
    )
    thread = await start(alice)
    turn = await send(alice, thread.id, "I had a hard day")

    assert scripted.calls == 1
    assert turn.content == written
    assert [p.label for p in turn.prompts] == ["Later"]


# Drafts that break a rule the prompt states: each is stored as the model wrote it, after one call.
EARLY_OFFER = Reply(
    text="There are some questions we could go through together. Would you like to try it?",
    prompts=[SmartPrompt(label="Try it", technique="structured_problem_solving"),
             SmartPrompt(label="Keep chatting", decline=True)],
    state=TechniqueState(technique="structured_problem_solving", step="offering"),
)
GRIEF_OFFER = Reply(
    text="There are some questions we could go through together. Would you like to try it?",
    prompts=[SmartPrompt(label="Try it", technique="behavioral_activation"),
             SmartPrompt(label="Keep chatting", decline=True)],
    state=TechniqueState(technique="behavioral_activation", step="offering"),
)


@pytest.mark.parametrize(
    ("message", "draft", "opened"),
    [
        ("i've an exam in 24 hours and i have not studied at all",
         Reply(text="An exam in 24 hours sounds incredibly stressful. What do you need first?"), False),
        ("i felt small when she questioned me in front of everyone",
         Reply(text="It is okay to feel that way. I am here with you."), False),
        ("i have an exam tomorrow and i don't know where to start", EARLY_OFFER, False),
        ("my dog died and i can't stop thinking about him", GRIEF_OFFER, True),
        ("i miss him and the flat is quiet",
         Reply(text="What is the hardest part of the evenings?", heading_toward="act_choice_point"), True),
    ],
    ids=["a feeling never named", "no question", "an offer too early", "an offer the words rule out",
         "no offer after several messages"],
)
async def test_a_draft_that_used_to_be_asked_for_again_is_stored_as_written_after_one_call(
    alice, model, message, draft, opened
):
    scripted = model(draft)
    thread = await start(alice)
    if opened:
        await past_the_opening(thread)
    turn = await send(alice, thread.id, message)

    assert scripted.calls == 1
    assert turn.content == draft.text
    assert [p.label for p in turn.prompts] == [p.label for p in draft.prompts or []]


async def test_the_question_asked_last_turn_is_asked_again_when_the_model_writes_it_again(alice, model):
    asked = Reply(text="What was it about that moment that stayed with you?")
    scripted = model(asked, asked)
    thread = await start(alice)
    await send(alice, thread.id, "my manager criticized me in front of everyone")
    turn = await send(alice, thread.id, "it was just bad")

    assert scripted.calls == 2
    assert turn.content == asked.text


async def test_a_tapped_button_reaches_the_model_as_its_label_under_a_key(alice, model):
    """response_format.md `buttons` says what `tapped:` means, so the code sends no sentence."""
    scripted = model(
        Reply(
            text="There are some questions we could go through together. Would you like to try it?",
            prompts=[SmartPrompt(label="Try it", technique="abcde"),
                     SmartPrompt(label="Keep chatting", decline=True)],
            state=TechniqueState(technique="abcde", step="offering"),
        ),
        Reply(text="Of course. What is on your mind?"),
    )
    thread = await start(alice)
    await past_the_opening(thread)
    await send(alice, thread.id, "my manager embarrassed me in front of everyone")
    await send(alice, thread.id, "Keep chatting")

    assert scripted.last_messages[-1]["content"].endswith("[/ctx]\n\ntapped: Keep chatting")


async def test_what_they_said_rules_out_is_told_not_offered_by_the_router(alice, model):
    """Behavioral Activation tops the shortlist for these words, and early grief rules it out: the
    model is told so, and the shortlist and the offer line never name it."""
    scripted = model(Reply(text="What is it like at home without him?"))
    thread = await start(alice)
    await past_the_opening(thread)
    await send(alice, thread.id, "i stopped doing the things i enjoy since he died and i can't make myself start anything")

    sent = scripted.last_messages[-1]["content"].splitlines()
    assert "ruled_out: behavioral_activation" in sent
    assert not [line for line in sent if "behavioral_activation" in line and line != "ruled_out: behavioral_activation"]


def _offer(technique: str) -> Reply:
    return Reply(
        text="There are some questions we could go through together. Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique=technique),
                 SmartPrompt(label="Keep chatting", decline=True)],
        state=TechniqueState(technique=technique, step="offering"),
    )


@pytest.mark.parametrize("technique", ["structured_problem_solving", "abcde"])
async def test_an_offer_is_made_on_the_second_message_in_any_style(alice, model, technique):
    """muhammad, 2026-10-01: once Mani can tell what fits it should offer, not wait out the old
    four. No framework waits for a later message either: ABCDE's offer stands on the second."""
    from mani.db import pool
    from mani.models.rows import SupportStyle

    scripted = model(
        Reply(text="What is the hardest part of it?", heading_toward=technique),
        _offer(technique),
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
    assert [p.technique for p in turn.prompts if p.technique] == [technique]
    assert [p.label for p in turn.prompts] == ["Try it", "Keep chatting"]


async def _supportive(thread):
    """The style tap and its opener, which the real greeting flow adds before their first message."""
    from mani.db import pool
    from mani.models.rows import SupportStyle

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set conversation_style = $2, message_count = message_count + 2 "
            "where id = $1",
            thread.id, SupportStyle.SUPPORTIVE.value,
        )


async def test_words_that_match_no_phrase_get_no_offer_guidance_at_any_message(alice, model):
    """There is no nearest fit: with nothing on the shortlist, nothing is offerable."""
    scripted = model(Reply(text="What is that like?"))
    thread = await start(alice)
    await _supportive(thread)
    for message in (
        "i miss him and the flat is quiet", "it happened at work", "it is hard to explain",
        "i just feel off", "the weather was grey",
    ):
        await send(alice, thread.id, message)
        sent = scripted.last_messages[-1]["content"].splitlines()
        assert not [
            line for line in sent
            if line.startswith(("framework_shortlist", "offer:", "closest_fit"))
        ], message
    assert scripted.calls == 5


async def test_a_sign_from_the_first_message_is_still_offerable_at_the_sixth(alice, model):
    """covers: AC-1, AC-2 - the first message's phrases still count once four more have passed,
    so the set they point to stays on the shortlist; nothing names it for the offer."""
    scripted = model(Reply(text="What was happening just then?"))
    thread = await start(alice)
    await _supportive(thread)
    for message in (
        "I'm very upset. My manager embarrassed me today because he wants me to fail.",
        "EVERYTHING WENT WRONG",
        "I felt really embarrassed.",
        "it happened at work",
        "it is hard to explain",
        "i just feel off",
    ):
        await send(alice, thread.id, message)

    sent = scripted.last_messages[-1]["content"].splitlines()
    assert "framework_shortlist: abcde" in sent
    assert not [line for line in sent if line.startswith(("offer:", "closest_fit"))]


async def test_every_framework_with_a_sign_is_listed_by_id_except_one_ruled_out(alice, model):
    scripted = model(Reply(text="That is a lot at once. What feels most pressing?"))
    thread = await start(alice)
    await send(
        alice, thread.id,
        "since my dog died nobody cares about me, so i must be a bad friend, i keep canceling "
        "plans, i cannot change what happened, i do not know what to do, and i keep typing and "
        "deleting",
    )

    sent = scripted.last_messages[-1]["content"].splitlines()
    assert "framework_shortlist: dbt_stop, act_choice_point, abcde, structured_problem_solving, thought_reframe" in sent
    assert "ruled_out: behavioral_activation" in sent


async def test_an_offer_off_the_shortlist_goes_out_and_is_logged_by_id_only(alice, model, caplog):
    """The rule is told, not enforced: the button stands, and the log shows it was off the list."""
    model(_offer("act_choice_point"))
    thread = await start(alice)
    await past_the_opening(thread)
    with caplog.at_level("INFO", logger="mani.chat.orchestrator"):
        turn = await send(alice, thread.id, "i miss him and the flat is quiet")

    assert [p.technique for p in turn.prompts if p.technique] == ["act_choice_point"]
    offers = [r.getMessage() for r in caplog.records if r.getMessage().startswith("offer on thread")]
    assert offers == [
        f"offer on thread {thread.id}: act_choice_point on_shortlist: no shortlist: none "
        "cooldown_passed: yes"
    ]
    assert "flat is quiet" not in caplog.text


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
        )
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "everything feels like too much")

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
        ),
        Reply(
            text="Good. What happened first?",
            state=TechniqueState(technique="abcde", step="activate"),
        ),
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep spiralling")
    await send(alice, thread.id, "Yes, let's try it")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)

    assert ctx.technique.outcome is TechniqueOutcome.ACCEPTED
    assert ctx.technique.phase == "activate"
    # So the first stage builds on what they already said instead of asking it again.
    assert "framework_starting: yes" in scripted.last_messages[-1]["content"]


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


async def test_an_offer_button_on_the_turn_that_retires_a_framework_cannot_cancel_the_retirement(
    alice, model
):
    """The offer's OFFERED row would be written over the retirement, so the finished framework
    would be running again. They have already chosen Chat More, so no choices are written, and
    the model's offer goes with the Keep chatting that answers it."""
    model(Reply(
        text="That is a good place to stop. Want to try another?",
        prompts=[SmartPrompt(label="Try it", technique="thought_reframe"),
                 SmartPrompt(label="Keep chatting", decline=True)],
        state=TechniqueState(technique="thought_reframe", step="offering"),
    ))
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="somatic_practice",
        )

    turn = await send(alice, thread.id, "Chat More")

    assert turn.prompts == []
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert (ctx.technique.framework_id, ctx.technique.phase) == ("abcde", None)
    assert ctx.technique.outcome is TechniqueOutcome.ACCEPTED


async def test_a_library_button_from_the_model_does_not_silence_the_library_offer(alice, model):
    """Only the two choices the orchestrator writes at the end of a framework count as the library
    having been offered, so a stray library button mid framework leaves it still pending."""
    scripted = model(
        Reply(
            text="What happened right before that?",
            prompts=[SmartPrompt(label="Go to Library", library="home")],
            state=TechniqueState(technique="abcde", step="belief"),
        ),
        Reply(text="And what did you tell yourself then?",
              state=TechniqueState(technique="abcde", step="belief")),
    )
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="belief",
        )

    await send(alice, thread.id, "she ignored my message")
    await send(alice, thread.id, "I thought I was being a burden")

    assert "library_pending: yes" in scripted.last_messages[-1]["content"].splitlines()


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


async def serve_with_row(monkeypatch, name: str, **changes) -> None:
    """Serve the seeded configuration with one prompt row changed, as a portal edit would."""
    config = await orchestrator.cache.load()
    changed = config.prompts[name].model_copy(update=changes)
    served = dataclasses.replace(config, prompts={**config.prompts, name: changed})

    async def load():
        return served

    monkeypatch.setattr(orchestrator.cache, "load", load)


async def test_an_exercise_row_with_no_level_offers_the_first_candidate_without_a_pick(
    alice, model, monkeypatch, abcde_exercise, caplog
):
    """The reply is already built when the pick runs, so a broken exercise_select row costs
    the pick and not the turn, and nothing is sent at a level nobody chose."""
    model(Reply(text="How has the rest of the week been?"))
    chooser = ScriptedChooser()
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)
    await serve_with_row(monkeypatch, "exercise_select", model_parameters={"maxTokens": 200})

    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)
    with caplog.at_level(logging.WARNING, logger="mani.chat.orchestrator"):
        turn = await send(alice, thread.id, "that helped, thanks")

    assert chooser.calls == 0
    assert turn.exercise is not None
    assert turn.exercise.id == abcde_exercise
    assert "exercise_select" in caplog.text


async def test_the_chat_turn_thinks_at_the_level_its_row_names(alice, model, monkeypatch):
    """Every seeded row says high, so only a changed row shows the level is read, not assumed."""
    scripted = model(Reply(text="Tell me more about that."))
    thread = await start(alice)
    await serve_with_row(monkeypatch, "mani_base", model_parameters={"reasoning_effort": "low"})

    await send(alice, thread.id, "I had a hard day")

    assert scripted.last_kwargs["reasoning_effort"] == "low"


async def test_a_chat_row_with_no_level_refuses_the_turn_before_the_model_is_asked(
    alice, model, monkeypatch
):
    """A config error, not a call at some default level: no tokens are spent finding out."""
    scripted = model(Reply(text="Tell me more about that."))
    thread = await start(alice)
    await serve_with_row(monkeypatch, "mani_base", model_parameters={})

    with pytest.raises(ServiceError) as refused:
        await send(alice, thread.id, "I had a hard day")

    assert refused.value.category is ErrorCategory.CONFIG_ERROR
    assert scripted.calls == 0


async def test_the_exercise_pick_sends_what_its_own_row_names(
    alice, model, monkeypatch, abcde_exercise
):
    """Model, thinking level, budget and routing are the exercise_select row's, and the seeded
    row asks for exactly what the pick sent when it borrowed the chat turn's settings."""
    sent: dict = {}

    class Bound:
        async def ainvoke(self, messages):
            sent["messages"] = messages
            call = {"name": "StartExercise", "args": {"exercise_id": str(abcde_exercise)}, "id": "1"}
            return SimpleNamespace(tool_calls=[call], usage_metadata={}, response_metadata={})

    real_model = chain._model

    def spy(*configuration):
        sent["model"] = configuration[3]
        sent["extra_body"] = json.loads(configuration[-1])
        sent["params"] = real_model(*configuration)._default_params
        return SimpleNamespace(bind_tools=lambda tools, tool_choice: Bound())

    monkeypatch.setattr(chain, "_model", spy)
    monkeypatch.setattr(get_settings(), "openrouter_api_key", "sk-test-not-a-real-key")
    monkeypatch.setattr(orchestrator.client, "choose_exercise", REAL_CHOOSE_EXERCISE)
    model(Reply(text="How has the rest of the week been?"))

    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)
    turn = await send(alice, thread.id, "that helped, thanks")

    row = (await orchestrator.cache.load()).prompts["exercise_select"]
    assert turn.exercise is not None
    assert turn.exercise.id == abcde_exercise
    assert sent["messages"][0]["content"].startswith(row.content)
    assert sent["model"] == "openai/gpt-6-luna"
    assert sent["extra_body"]["reasoning"] == {"effort": "high"}
    assert sent["extra_body"]["provider"]["order"] == get_settings().openrouter_provider_order
    assert sent["extra_body"]["provider"]["data_collection"] == "deny"
    assert sent["params"]["max_completion_tokens"] == 200 + chain.REASONING_ALLOWANCE_TOKENS
    assert "temperature" not in sent["params"]


async def test_asking_about_an_offer_leaves_it_open(alice, model):
    """A question about the offer is answered and the offer made again, so it is still waiting
    for their answer - unlike carrying on past it, which is Keep chatting."""
    model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Try it", technique="abcde")],
            state=TechniqueState(technique="abcde", step="offering"),
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
    await send(alice, thread.id, "I keep spiralling")
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


async def test_the_router_shortlist_reaches_the_prompt_without_a_second_call(alice, model):
    """The router runs in process; it must narrow the field without paying for it."""
    scripted = model(
        Reply(text="How is that affecting your days?"),
        Reply(text="What would it look like to take one step?"),
        Reply(text="What keeps that feeling from arriving?"),
    )
    thread = await start(alice)
    await send(alice, thread.id, "I have stopped answering people for a week now.")
    await send(alice, thread.id, "I know what I need to do, I just cannot make myself begin.")
    await send(alice, thread.id, "I keep waiting to want to do something, but it never comes.")

    assert scripted.calls == 3
    final_prompt = scripted.last_messages[-1]["content"]
    assert "framework_shortlist: behavioral_activation" in final_prompt


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
        ),
        Reply(text="Good. What happened first?"),
    )
    from mani.db import pool
    from mani.routers.serializers import to_messages

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep spiralling")
    await send(alice, thread.id, "Yes, let's try it")

    async with pool.as_user(alice) as conn:
        history = await messages_db.recent_for_context(conn, thread.id, ALICE)
        live = await messages_db.latest_mani_id(conn, thread.id, ALICE)

    rendered = to_messages(history, live)
    offered = next(m for m in history if any(o.get("technique") for o in m.prompt_options or []))
    offer = next(m for m in rendered if m.id == offered.id)
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
    assert "active_framework" not in sent
    assert not any(line.startswith(("stage", "next_stage")) for line in sent.splitlines())
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

    turn = await send(alice, thread.id, "something else happened today")
    assert [p.technique for p in turn.prompts] == ["thought_reframe"]


async def test_the_router_runs_again_after_a_declined_offer(alice, model):
    scripted = model(Reply(text="What has that been like?"))
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.DECLINED,
            at_message_count=2, phase=None,
        )
    await send(alice, thread.id, "I have stopped answering people for a week now.")
    await send(alice, thread.id, "I know what I need to do, I just cannot make myself begin.")
    await send(alice, thread.id, "I keep waiting to want to do something, but it never comes.")

    assert "framework_shortlist: behavioral_activation" in scripted.last_messages[-1]["content"]


async def test_tapping_decline_records_it_even_when_the_model_reports_no_state(alice, model):
    """After a decline there is no technique to report, so state: null is the model doing
    what the schema asks. The decline is the button's meaning, not the model's to confirm."""
    model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Yes, let's try it", technique="abcde"),
                     SmartPrompt(label="Not right now", decline=True)],
            state=TechniqueState(technique="abcde", step="offering"),
        ),
        Reply(text="That's fine. What would help most right now?"),
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep spiralling")
    await send(alice, thread.id, "Not right now")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.technique.outcome is TechniqueOutcome.DECLINED
    assert "active_framework" not in context.build(ctx)


async def test_an_empty_reply_fails_cleanly_and_stores_nothing(alice, model):
    """A reply with no words must fail as a retryable turn, not reach the
    messages_content_not_empty constraint as a 500."""
    model(Reply(text="  \n"))
    from mani.errors import ServiceError

    thread = await start(alice)
    with pytest.raises(ServiceError) as raised:
        await send(alice, thread.id, "hello")
    assert raised.value.retryable
    assert [m.role for m in await _history(alice, thread.id)] == ["mani"]  # the greeting only


async def test_an_imminent_action_is_offerable_on_the_first_message(alice, model):
    """The two-exchange wait exists so a framework is not offered on a first hint. STOP is
    the case where waiting is the failure: the message may be sent before a third turn."""
    scripted = model(Reply(text="Before you send it, can we pause for a moment?"))
    thread = await start(alice)
    await send(alice, thread.id, "I am about to send it")

    sent = scripted.last_messages[-1]["content"].splitlines()
    assert "framework_shortlist: dbt_stop" in sent
    assert "cooldown_passed: yes" in sent


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
            at_message_count=2, phase="closing",
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
    await _land_on(alice, thread.id, "closing")

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
        Reply(text="It feels a little better. Would you like to notice what is happening in your body?",
              state=TechniqueState(technique="abcde", step="somatic_checkin")),
        Reply(text="It is not always easy to say where. Is it your chest or your shoulders?",
              state=TechniqueState(technique="abcde", step="somatic_practice")),
        Reply(text="Chest, I see.", state=TechniqueState(technique="abcde", step="somatic_practice")),
        Reply(text="Panic comes in waves. Would you like the library?"),
    )
    thread = await start(alice)
    await _land_on(alice, thread.id, "closing")

    checked_in = await send(alice, thread.id, "not a 100% but a little better")
    assert checked_in.content.endswith("Would you like to notice what is happening in your body?")

    said_yes = await send(alice, thread.id, "yes")
    assert said_yes.content.count("notice what is happening in your body") == 0
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
    await _land_on(alice, thread.id, "closing")

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
    )
    # What the model actually does: reports no answer either way, and makes the offer again.
    offered_again = offer.model_copy(update={
        "text": "You pick the phone back up. I have a sequence of questions that could help. "
                "Would you like to try it?",
    })
    model(offer, offered_again)
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "my manager criticized me in front of everyone")
    turn = await send(alice, thread.id, "every time I try to start I pick the phone back up")

    assert turn.prompts == []
    assert turn.content == offered_again.text
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
    )
    scripted = model(offer, Reply(text="You pick the phone back up. What happens right before?"))
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "my manager criticized me in front of everyone")
    await send(alice, thread.id, "every time I try to start I pick the phone back up")

    sent = scripted.last_messages[-1]["content"]
    assert "offer_waiting: yes" in sent
    # The offer is still open, so the offering stage is named and nothing else about a stage.
    assert "stage: offering" in sent.splitlines()
    assert not any(line.startswith(("stage_", "next_stage")) for line in sent.splitlines())
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
    )
    model(
        offer,
        Reply(text="You keep replaying it. Which part stays with you?"),
        Reply(text="Okay. We'll take it one step at a time together. What happened?",
              state=TechniqueState(technique="abcde", step="activate", accepted=True)),
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "my manager criticized me in front of everyone")
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
    )
    chats = [
        Reply(text=text) for text in (
            "What else has been on your mind about it?",
            "When does it come back to you most?",
            "Who was in the room when it happened?",
            "How did the evening go afterwards?",
        )
    ]
    model(offer, *chats, offer)
    thread = await start(alice)
    await send(alice, thread.id, "my manager criticized me in front of everyone")
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
            at_message_count=2, phase="closing",
        )

    turn = await send(alice, thread.id, "yes, that fits what happened")
    assert turn.content.endswith("Would you like to notice what is happening in your body?")
