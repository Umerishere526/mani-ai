# ABOUTME: Endpoints a scheduler calls, never a person - guarded by a shared secret, not a JWT.
# ABOUTME: GET, because Vercel Cron always triggers its configured path with GET.

import hmac
import logging

from fastapi import APIRouter, Header, HTTPException

from mani import catch_up
from mani.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/cron", tags=["cron"])


def _check_secret(authorization: str | None) -> None:
    """The same convention Vercel Cron documents: it sends CRON_SECRET as this header.

    An unset secret refuses everything - there is no host where "not configured" should
    mean "open". Runs before anything else in the handler, on every call.
    """
    secret = get_settings().cron_secret
    if not secret or not hmac.compare_digest((authorization or "").encode(), f"Bearer {secret}".encode()):
        raise HTTPException(status_code=401, detail="unauthorized")


@router.get("/catch-up")
async def run_catch_up(authorization: str | None = Header(default=None)) -> dict:
    """Finish what the app left: summaries fallen behind, follow-ups it never asked for, and quiet chats to fold
    into memory. See mani/catch_up.py."""
    _check_secret(authorization)
    done = await catch_up.run()
    logger.info("cron catch-up: %s", done)
    return done
