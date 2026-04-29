from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import require_internal_job_token
from app.schemas.snowflake_v2 import SnowflakeJobsGetResponse
from app.services.job_service import get_job


router = APIRouter(prefix="/snowflake/v2/jobs", tags=["snowflake-workflows"])


@router.get("/{job_id}")
def get_job_status(
    job_id: str, settings=Depends(require_internal_job_token)
) -> SnowflakeJobsGetResponse:
    """Fetch a Snowflake pipeline job record by job_id."""
    try:
        job = get_job(settings, job_id=job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="not_found")
        return {"job": job}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
