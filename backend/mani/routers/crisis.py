# ABOUTME: The help resources shown when a conversation is flagged.
# ABOUTME: Open to a paused person too; it is what the pause points them to.

from fastapi import APIRouter

from mani.auth.deps import CurrentUser
from mani.chat.crisis import Resource, resources_for

router = APIRouter(prefix="/v1/crisis", tags=["crisis"])


@router.get("/resources", response_model=list[Resource])
def resources(_: CurrentUser, country: str | None = None) -> list[Resource]:
    """Crisis services, optionally for one country.

    A country with no entries of its own gets the helpline directory alone.
    """
    return resources_for(country)
