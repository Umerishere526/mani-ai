# ABOUTME: The onboarding profile - nickname, topics, support style.
# ABOUTME: Stored in a table rather than auth metadata, so it is not user-writable directly.

from fastapi import APIRouter

from mani.auth.deps import CurrentUser
from mani.db import profiles
from mani.db.deps import UserConn
from mani.models.api import ProfileIn, ProfileOut
from mani.routers.serializers import to_profile

router = APIRouter(prefix="/v1/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
async def get_profile(user: CurrentUser, conn: UserConn) -> ProfileOut:
    return to_profile(await profiles.get(conn, user.user_id))


@router.put("", response_model=ProfileOut)
async def put_profile(user: CurrentUser, conn: UserConn, body: ProfileIn) -> ProfileOut:
    """Partial by design: fields left out keep the values onboarding collected."""
    profile = await profiles.upsert(
        conn,
        user.user_id,
        nickname=body.nickname,
        topics=body.topics,
        support_style=body.support_style.value if body.support_style else None,
        age_bracket=body.age_bracket,
    )
    return to_profile(profile)
