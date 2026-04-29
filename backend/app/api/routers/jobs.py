from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.enums import RunStatus
from app.models.optimization_run import OptimizationRun
from app.models.terraform_snapshot import TerraformSnapshot
from app.schemas.runs import ManualOptimizeIn, RunOut
from app.services.events import event_bus


router = APIRouter(prefix="/jobs", tags=["jobs"])


def _require_token(token: str, header_value: str | None) -> None:
    if not token or not header_value or header_value != f"Bearer {token}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
        )


@router.post("/optimize", response_model=RunOut)
async def scheduled_optimize(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> RunOut:
    settings = get_settings()
    _require_token(settings.internal_job_token, authorization)
    if not settings.scheduler_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="scheduler_disabled"
        )

    res = await db.execute(
        select(TerraformSnapshot).order_by(desc(TerraformSnapshot.id)).limit(1)
    )
    latest = res.scalar_one_or_none()
    run = OptimizationRun(
        repo=latest.repo if latest else "unknown",
        terraform_snapshot_id=latest.id if latest else None,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    await event_bus.publish(
        "run.queued", {"type": "run.queued", "repo": run.repo, "run_id": run.id}
    )
    return RunOut.model_validate(run)


@router.post("/optimize/manual", response_model=RunOut)
async def manual_optimize(
    body: ManualOptimizeIn,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> RunOut:
    settings = get_settings()
    _require_token(settings.manual_trigger_token, authorization)

    terraform_snapshot_id = None
    if body.terraform_sha:
        res = await db.execute(
            select(TerraformSnapshot)
            .where(
                TerraformSnapshot.repo == body.repo,
                TerraformSnapshot.sha == body.terraform_sha,
            )
            .order_by(desc(TerraformSnapshot.id))
            .limit(1)
        )
        snap = res.scalar_one_or_none()
        terraform_snapshot_id = snap.id if snap else None
    else:
        res = await db.execute(
            select(TerraformSnapshot)
            .where(TerraformSnapshot.repo == body.repo)
            .order_by(desc(TerraformSnapshot.id))
            .limit(1)
        )
        snap = res.scalar_one_or_none()
        terraform_snapshot_id = snap.id if snap else None

    run = OptimizationRun(
        repo=body.repo,
        terraform_snapshot_id=terraform_snapshot_id,
        status=RunStatus.queued,
        constraints=body.constraints or {},
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    await event_bus.publish(
        "run.queued", {"type": "run.queued", "repo": run.repo, "run_id": run.id}
    )
    return RunOut.model_validate(run)
