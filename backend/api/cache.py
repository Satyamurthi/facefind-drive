"""
Cache management API: trigger manual re-index, get status.
"""

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_admin
from config import get_settings
from core.indexer import run_index, get_indexer_status
from db.database import get_db
from db.models import User

router = APIRouter(prefix="/api/cache", tags=["cache"])
settings = get_settings()


@router.get("/status")
async def cache_status(_admin: User = Depends(require_admin)):
    """Return current indexer status."""
    return get_indexer_status()


@router.post("/refresh")
async def refresh_cache(
    background_tasks: BackgroundTasks,
    full: bool = False,
    _admin: User = Depends(require_admin),
):
    """
    Trigger a Drive folder re-index in the background.
    full=true: re-index all files. full=false (default): only new/modified files.
    """
    status = get_indexer_status()
    if status["running"]:
        return {"message": "Indexer already running", "status": status}

    folder_id = settings.drive_folder_id
    if not folder_id:
        return {"message": "No DRIVE_FOLDER_ID configured"}

    background_tasks.add_task(
        run_index, folder_id, incremental=not full
    )
    return {"message": f"{'Full' if full else 'Incremental'} re-index started in background"}
