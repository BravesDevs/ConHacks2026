from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.services.ingest_service import ingest_digitalocean_sizes
from app.services.snowflake_service import ensure_snowflake_setup


router = APIRouter(prefix="/snowflake", tags=["snowflake"])


@router.post("/setup")
def setup_snowflake(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    try:
        ensure_snowflake_setup(settings)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/ingest/do-sizes")
async def ingest_do_sizes(settings: Settings = Depends(get_settings)) -> dict:
    try:
        return await ingest_digitalocean_sizes(settings)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
