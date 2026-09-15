"""
Search API: Upload a reference image and find matching faces in Drive.

Uses Server-Sent Events (SSE) to stream progress and results back to the client.
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from config import get_settings
from core import face_engine, indexer
from db.database import get_db
from db.models import User
from utils.logger import write_audit

router = APIRouter(prefix="/api/search", tags=["search"])
settings = get_settings()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


async def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.post("")
async def search(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a reference image to search for matching faces in the Drive folder.
    Returns a Server-Sent Events stream:
      - progress events: {type: "progress", message: "..."}
      - face_select event (if multiple faces): {type: "face_select", faces: [...]}
      - result event: {type: "result", matches: [...], total: N}
      - error event: {type: "error", message: "..."}
    """
    # Validate file
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image format")

    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Image too large (max 10 MB)")

    threshold = settings.face_similarity_threshold
    folder_id = settings.drive_folder_id

    async def event_stream() -> AsyncIterator[str]:
        try:
            # Step 1: Extract reference embeddings
            yield await _sse_event({"type": "progress", "message": "Detecting face in reference image…"})
            ref_embeddings = await asyncio.get_event_loop().run_in_executor(
                None,
                face_engine.extract_embeddings,
                image_bytes,
            )

            if not ref_embeddings:
                yield await _sse_event({
                    "type": "error",
                    "message": "No face detected in the uploaded image. Please upload a clear photo.",
                })
                return

            # Step 2: Use first embedding if single face; for multiple, use all (search for any)
            face_count = len(ref_embeddings)
            yield await _sse_event({
                "type": "progress",
                "message": f"Found {face_count} face(s) in reference image. Searching Drive…",
                "face_count": face_count,
            })

            # Step 3: Load cached embeddings from DB
            yield await _sse_event({"type": "progress", "message": "Loading index…"})
            cached_files = await indexer.get_all_cached(db)
            yield await _sse_event({
                "type": "progress",
                "message": f"Comparing against {len(cached_files)} indexed images…",
            })

            # Step 4: Compare
            matches = await asyncio.get_event_loop().run_in_executor(
                None,
                face_engine.compare_against_index,
                ref_embeddings,
                cached_files,
                threshold,
            )

            # Step 5: Audit log
            write_audit(
                action="search",
                user_id=current_user.id,
                user_email=current_user.email,
                ip_address=request.client.host if request.client else None,
                reference_image_bytes=image_bytes,
                matches_returned=len(matches),
                threshold_used=threshold,
                details={"folder_id": folder_id, "indexed_total": len(cached_files)},
            )

            yield await _sse_event({
                "type": "result",
                "matches": matches,
                "total": len(matches),
                "indexed_total": len(cached_files),
                "threshold": threshold,
            })

        except Exception as exc:
            yield await _sse_event({"type": "error", "message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
