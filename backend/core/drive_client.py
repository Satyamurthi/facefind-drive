"""
Google Drive API client using a service account.

Scope is strictly drive.readonly — the service account can only read files
inside folders where the admin has explicitly shared access.
"""

from __future__ import annotations

import logging
import time
from typing import Iterator, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import io

from config import get_settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

SUPPORTED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/bmp",
    "image/tiff",
}

IMAGE_FIELDS = "id,name,mimeType,modifiedTime,thumbnailLink,webViewLink,size"


def _build_service():
    settings = get_settings()
    creds = service_account.Credentials.from_service_account_file(
        settings.google_service_account_file, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _retry(fn, max_retries: int = 5, base_delay: float = 1.0):
    """Exponential backoff wrapper for Drive API calls."""
    for attempt in range(max_retries):
        try:
            return fn()
        except HttpError as exc:
            if exc.resp.status in (429, 500, 503) and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning("Drive API error %s, retrying in %.1fs…", exc.resp.status, delay)
                time.sleep(delay)
            else:
                raise
    return None


def list_images(
    folder_id: str,
    *,
    modified_after: Optional[str] = None,
) -> Iterator[dict]:
    """
    Yield all image file metadata dicts in the given folder (recursive=False).
    Handles Drive pagination automatically.

    Args:
        folder_id: Google Drive folder ID.
        modified_after: ISO 8601 datetime string — only return files modified after this time.
    """
    service = _build_service()
    mime_filter = " or ".join(f"mimeType='{m}'" for m in SUPPORTED_MIME_TYPES)
    query = f"'{folder_id}' in parents and ({mime_filter}) and trashed=false"
    if modified_after:
        query += f" and modifiedTime > '{modified_after}'"

    page_token: Optional[str] = None
    while True:
        params = dict(
            q=query,
            fields=f"nextPageToken,files({IMAGE_FIELDS})",
            pageSize=200,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        if page_token:
            params["pageToken"] = page_token

        response = _retry(lambda: service.files().list(**params).execute())
        for file in response.get("files", []):
            yield file

        page_token = response.get("nextPageToken")
        if not page_token:
            break


def download_file(file_id: str) -> bytes:
    """Download a Drive file by ID and return its raw bytes."""
    service = _build_service()
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request, chunksize=4 * 1024 * 1024)
    done = False
    while not done:
        _, done = _retry(lambda: downloader.next_chunk())
    return buf.getvalue()


def get_file_metadata(file_id: str) -> dict:
    """Fetch metadata for a single file."""
    service = _build_service()
    return _retry(
        lambda: service.files().get(
            fileId=file_id,
            fields=IMAGE_FIELDS,
            supportsAllDrives=True,
        ).execute()
    )
