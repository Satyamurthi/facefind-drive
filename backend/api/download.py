"""
Download API: single-file proxy and multi-file ZIP streaming.
Thumbnails are also proxied through backend (not exposed directly to client).
"""

import io
import zipfile
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core import drive_client
from db.database import get_db
from db.models import DriveFileCache, User

router = APIRouter(prefix="/api/download", tags=["download"])


@router.get("/thumbnail/{file_id}")
async def get_thumbnail(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Proxy Drive thumbnail image through the backend."""
    result = await db.execute(
        select(DriveFileCache).where(DriveFileCache.file_id == file_id)
    )
    record = result.scalar_one_or_none()
    if not record or not record.thumbnail_url:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(record.thumbnail_url, timeout=10)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Could not fetch thumbnail")
        content_type = resp.headers.get("content-type", "image/jpeg")
        return StreamingResponse(io.BytesIO(resp.content), media_type=content_type)


@router.get("/file/{file_id}")
async def download_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Download a single Drive file (proxied through backend)."""
    result = await db.execute(
        select(DriveFileCache).where(DriveFileCache.file_id == file_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="File not found in index")

    try:
        file_bytes = drive_client.download_file(file_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Drive download failed: {exc}")

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=record.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{record.filename}"',
            "Content-Length": str(len(file_bytes)),
        },
    )


class ZipRequest(BaseModel):
    file_ids: List[str]


@router.post("/zip")
async def download_zip(
    body: ZipRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Stream a ZIP archive containing all requested files."""
    if not body.file_ids:
        raise HTTPException(status_code=400, detail="No file IDs provided")
    if len(body.file_ids) > 200:
        raise HTTPException(status_code=400, detail="Maximum 200 files per ZIP request")

    # Fetch filenames from cache
    result = await db.execute(
        select(DriveFileCache).where(DriveFileCache.file_id.in_(body.file_ids))
    )
    records = {r.file_id: r for r in result.scalars().all()}

    def generate_zip():
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            seen_names: set[str] = set()
            for file_id in body.file_ids:
                record = records.get(file_id)
                if not record:
                    continue
                try:
                    file_bytes = drive_client.download_file(file_id)
                    # Deduplicate filenames within the ZIP
                    name = record.filename
                    if name in seen_names:
                        base, ext = name.rsplit(".", 1) if "." in name else (name, "")
                        name = f"{base}_{file_id[:6]}.{ext}" if ext else f"{base}_{file_id[:6]}"
                    seen_names.add(name)
                    zf.writestr(name, file_bytes)
                except Exception:
                    pass  # Skip failed downloads
        zip_buffer.seek(0)
        return zip_buffer.read()

    import asyncio
    zip_data = await asyncio.get_event_loop().run_in_executor(None, generate_zip)

    return StreamingResponse(
        io.BytesIO(zip_data),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="facefind_matches.zip"'},
    )
