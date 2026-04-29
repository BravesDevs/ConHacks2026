from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.optimization_run import OptimizationRun
from app.schemas.runs import RunOut


router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/latest", response_model=RunOut)
async def latest_run(repo: str = Query(...), db: AsyncSession = Depends(get_db)) -> RunOut:
    res = await db.execute(select(OptimizationRun).where(OptimizationRun.repo == repo).order_by(desc(OptimizationRun.id)).limit(1))
    run = res.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="not_found")
    return RunOut.model_validate(run)


@router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)) -> RunOut:
    res = await db.execute(select(OptimizationRun).where(OptimizationRun.id == run_id))
    run = res.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="not_found")
    return RunOut.model_validate(run)


@router.get("", response_model=list[RunOut])
async def list_runs(
    repo: str = Query(...),
    limit: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[RunOut]:
    res = await db.execute(
        select(OptimizationRun).where(OptimizationRun.repo == repo).order_by(desc(OptimizationRun.id)).limit(limit)
    )
    return [RunOut.model_validate(r) for r in res.scalars().all()]
