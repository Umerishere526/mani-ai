# ABOUTME: Account deletion - the one thing a user's own session cannot ask GoTrue for.
# ABOUTME: Every owned table cascades from auth.users, so there is nothing else to clean up.

from fastapi import APIRouter

from mani import auth_admin
from mani.auth.deps import CurrentUser

router = APIRouter(prefix="/v1/account", tags=["account"])


@router.delete("", status_code=204)
async def delete_account(user: CurrentUser) -> None:
    await auth_admin.delete_user(user.user_id)
