# ABOUTME: Proves the admin's unresolved crisis events: a danger a turn found is listed until an admin resolves it
# ABOUTME: with a note. Against a live database with a scripted model; the routes are called as the portal calls them.

import pytest

from mani.chat.reply import Safety
from mani.db import pool
from mani.errors import ErrorCategory, ServiceError
from mani.routers import admin
from tests.integration.fixtures import said, send, start


async def test_an_admin_lists_an_unresolved_crisis_event_and_resolves_it_once(alice, model):
    """S16 (PROVISIONAL: clinician sign-off required before deploy): production recorded 7 crisis events in 30 days and
    nothing could mark one as seen. No alerting is sent; that needs operations."""
    model(said("Call 911 now, or call or text 988. Are you alone?", safety=Safety(level="danger", about="themselves")))
    thread = await start(alice)
    await send(alice, thread.id, "i took a bunch of pills")

    async with pool.as_admin() as conn:
        listed = [e for e in await admin.list_crisis_events(conn, unresolved=True) if e.thread_id == thread.id]
        assert len(listed) == 1 and listed[0].resolved_at is None
        resolved = await admin.resolve_crisis_event(
            conn, listed[0].id, admin.CrisisResolveIn(resolution="Called; she is with her sister."))
        assert resolved.resolution == "Called; she is with her sister." and resolved.resolved_at is not None
        assert thread.id not in {e.thread_id for e in await admin.list_crisis_events(conn, unresolved=True)}
        assert thread.id in {e.thread_id for e in await admin.list_crisis_events(conn, unresolved=False)}
        with pytest.raises(ServiceError) as again:
            await admin.resolve_crisis_event(conn, listed[0].id, admin.CrisisResolveIn(resolution="again"))
        assert again.value.category is ErrorCategory.CONFLICT
