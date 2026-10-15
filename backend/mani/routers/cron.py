# ABOUTME: Endpoints a scheduler calls, never a person - guarded by a shared secret, not a JWT.
# ABOUTME: GET, because Vercel Cron always triggers its configured path with GET.

import hmac
import logging

from fastapi import APIRouter, Header, HTTPException

from mani.config import get_settings
from mani.summarize import reconcile_due

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/cron", tags=["cron"])


def _check_secret(authorization: str | None) -> None:
    """The same convention Vercel Cron documents: it sends CRON_SECRET as this header.

    An unset secret refuses everything - there is no host where "not configured" should
    mean "open". Runs before anything else in the handler, on every call.
    """
    secret = get_settings().cron_secret
    # Compared in constant time, so the time a refusal takes says nothing about the secret.
    if not secret or not hmac.compare_digest(
        (authorization or "").encode(), f"Bearer {secret}".encode()
    ):
        raise HTTPException(status_code=401, detail="unauthorized")


@router.get("/fold-summaries")
async def fold_summaries(authorization: str | None = Header(default=None)) -> dict:
    """Catch up every thread whose rolling summary has fallen behind. See reconcile_due."""
    _check_secret(authorization)
    processed = await reconcile_due()
    logger.info("cron fold-summaries: %d thread(s) reconciled", processed)
    return {"processed": processed}
