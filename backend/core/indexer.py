"""
Drive Folder Indexer

Scans a Google Drive folder, downloads each image, extracts face embeddings,
and stores results in the DriveFileCache table.

Supports:
  - Full re-index
  - Incremental update (only new/modified files)
  - Progress callback for SSE streaming
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core import drive_client, face_engine
from db.database import AsyncSessionLocal
from db.models import DriveFileCache

logger = logging.getLogger(__name__)
settings = get_settings()

# Global state for indexer status
_indexer_state = {
    "running": False,
    "last_completed": None,
    "total_files": 0,
    "indexed_files": 0,
    "errors": 0,
}


def get_indexer_status() -> dict:
    return dict(_indexer_state)


async def _upsert_file(session: AsyncSession, file_meta: dict, embeddings: list, error: Optional[str]):
    """Insert or update a DriveFileCache record."""
    stmt = select(DriveFileCache).where(DriveFileCache.file_id == file_meta["id"])
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()

    if record is None:
        record = DriveFileCache(file_id=file_meta["id"])
        session.add(record)

    record.filename = file_meta.get("name", "unknown")
    record.mime_type = file_meta.get("mimeType")
    record.thumbnail_url = file_meta.get("thumbnailLink")
    record.web_view_link = file_meta.get("webViewLink")
    record.modified_time = file_meta.get("modifiedTime")
    record.face_count = len(embeddings)
    record.embeddings = embeddings if not error else None
    record.indexed_at = datetime.now(timezone.utc)
    record.index_error = error


async def _process_file(
    file_meta: dict,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> tuple[list, Optional[str]]:
    """Download a Drive image and extract face embeddings. Returns (embeddings, error)."""
    file_id = file_meta["id"]
    filename = file_meta.get("name", file_id)

    try:
        if progress_cb:
            progress_cb(f"Indexing: {filename}")
        # Run blocking I/O in thread pool
        image_bytes = await asyncio.get_event_loop().run_in_executor(
            None, drive_client.download_file, file_id
        )
        embeddings = await asyncio.get_event_loop().run_in_executor(
            None,
            face_engine.extract_embeddings,
            image_bytes,
        )
        logger.debug("Indexed %s — %d face(s) found", filename, len(embeddings))
        return embeddings, None
    except Exception as exc:
        logger.warning("Failed to index %s: %s", filename, exc)
        return [], str(exc)


async def run_index(
    folder_id: str,
    *,
    incremental: bool = True,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Index (or re-index) all images in the given Drive folder.

    Args:
        folder_id: Target Google Drive folder ID.
        incremental: If True, only process files modified since last index.
        progress_cb: Optional callable called with status strings (for SSE).

    Returns:
        Summary dict with counts.
    """
    if _indexer_state["running"]:
        return {"error": "Indexer already running"}

    _indexer_state["running"] = True
    _indexer_state["errors"] = 0
    _indexer_state["indexed_files"] = 0

    try:
        # Determine cutoff for incremental indexing
        modified_after: Optional[str] = None
        if incremental and _indexer_state["last_completed"]:
            modified_after = _indexer_state["last_completed"].isoformat()

        # Collect all files first to know total count
        if progress_cb:
            progress_cb("Listing Drive folder…")

        all_files = list(drive_client.list_images(folder_id, modified_after=modified_after))
        _indexer_state["total_files"] = len(all_files)

        if progress_cb:
            progress_cb(f"Found {len(all_files)} image(s) to process")

        sem = asyncio.Semaphore(settings.index_concurrency)

        async def process_with_sem(file_meta: dict):
            async with sem:
                return file_meta, await _process_file(file_meta, progress_cb)

        tasks = [process_with_sem(f) for f in all_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        async with AsyncSessionLocal() as session:
            for item in results:
                if isinstance(item, Exception):
                    _indexer_state["errors"] += 1
                    continue
                file_meta, (embeddings, error) = item
                await _upsert_file(session, file_meta, embeddings, error)
                if error:
                    _indexer_state["errors"] += 1
                _indexer_state["indexed_files"] += 1
            await session.commit()

        _indexer_state["last_completed"] = datetime.now(timezone.utc)
        if progress_cb:
            progress_cb(f"Done — {_indexer_state['indexed_files']} files indexed")

        return {
            "total_files": _indexer_state["total_files"],
            "indexed_files": _indexer_state["indexed_files"],
            "errors": _indexer_state["errors"],
        }

    finally:
        _indexer_state["running"] = False


async def get_all_cached(session: AsyncSession) -> list[dict]:
    """Return all cached Drive files as plain dicts for comparison."""
    stmt = select(DriveFileCache).where(DriveFileCache.embeddings.is_not(None))
    result = await session.execute(stmt)
    records = result.scalars().all()
    return [
        {
            "file_id": r.file_id,
            "filename": r.filename,
            "thumbnail_url": r.thumbnail_url,
            "web_view_link": r.web_view_link,
            "embeddings": r.embeddings,
        }
        for r in records
    ]
