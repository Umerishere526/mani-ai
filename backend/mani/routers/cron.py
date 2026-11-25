# ABOUTME: Endpoints a scheduler calls, never a person - guarded by a shared secret, not a JWT.
# ABOUTME: GET, because Vercel Cron always triggers its configured path with GET.

import hmac
import logging

from fastapi import APIRouter, Header

from mani import catch_up
from mani.config import get_settings
from mani.errors import ErrorCategory, ServiceError
from mani.models.api import CatchUpOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/cron", tags=["cron"])


def _check_secret(authorization: str | None) -> None:
    """The same convention Vercel Cron documents: it sends CRON_SECRET as this header.

    An unset secret refuses everything - there is no host where "not configured" should
    mean "open". Runs before anything else in the handler, on every call.
    """
    secret = get_settings().cron_secret
    if not secret or not hmac.compare_digest((authorization or "").encode(), f"Bearer {secret}".encode()):
        raise ServiceError("cron call without the right secret", ErrorCategory.UNAUTHENTICATED,
                           user_message="Not authorized.")


@router.get("/catch-up", response_model=CatchUpOut)
async def run_catch_up(authorization: str | None = Header(default=None)) -> CatchUpOut:
    """Finish what the app left: summaries fallen behind and follow-ups it never asked for. See mani/catch_up.py."""
    _check_secret(authorization)
    done = await catch_up.run()
    logger.info("cron catch-up: %s", done)
    return CatchUpOut(**done)
