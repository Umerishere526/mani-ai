# ABOUTME: The help resources shown when a conversation is flagged.
# ABOUTME: Returns an empty list until real services are supplied - no invented numbers.

from fastapi import APIRouter

from mani.auth.deps import CurrentUser
from mani.chat.crisis import Resource, resources_for

router = APIRouter(prefix="/v1/crisis", tags=["crisis"])


@router.get("/resources", response_model=list[Resource])
def resources(_: CurrentUser, country: str | None = None) -> list[Resource]:
    """Crisis services, optionally for one country.

    An empty list is the honest answer while the list is unwritten. A wrong number here
    would be worse than none, so the client must handle empty rather than assume content.
    """
    return resources_for(country)
