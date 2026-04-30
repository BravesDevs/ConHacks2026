from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.rest import Client

from app.core.config import get_settings
from app.models.github_connection import GitHubConnection
from app.models.optimization_run import OptimizationRun

logger = logging.getLogger(__name__)


async def resolve_phone_for_run(db: AsyncSession, run: OptimizationRun) -> str | None:
    """Find the phone number of the GitHub user whose connection tracks this run's repo."""
    res = await db.execute(select(GitHubConnection))
    for conn in res.scalars().all():
        if conn.phone_number and run.repo in (conn.tracked_repos or []):
            return conn.phone_number
    # Fallback: any connection with a phone (single-user demos)
    res = await db.execute(
        select(GitHubConnection).where(GitHubConnection.phone_number.is_not(None)).limit(1)
    )
    conn = res.scalar_one_or_none()
    if conn and conn.phone_number:
        return conn.phone_number
    # Final fallback: env var
    settings = get_settings()
    return settings.customer_phone_number or None


async def initiate_call(db: AsyncSession, run: OptimizationRun) -> str:
    settings = get_settings()
    phone = await resolve_phone_for_run(db, run)
    if not phone:
        raise RuntimeError(f"no phone number available for run {run.id}")
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    call = client.calls.create(
        to=phone,
        from_=settings.twilio_from_number,
        url=f"{settings.public_base_url}/voice/twiml/{run.id}",
    )
    logger.info("Twilio call placed for run %s to %s: %s", run.id, phone, call.sid)
    return call.sid
