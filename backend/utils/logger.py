import json
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import get_settings

settings = get_settings()


def _ensure_log_dir():
    log_path = Path(settings.audit_log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    return log_path


def write_audit(
    action: str,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[dict] = None,
    reference_image_bytes: Optional[bytes] = None,
    matches_returned: Optional[int] = None,
    threshold_used: Optional[float] = None,
):
    """Append one JSON-lines record to the audit log file."""
    log_path = _ensure_log_dir()
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user_id": user_id,
        "user_email": user_email,
        "ip_address": ip_address,
        "folder_id": settings.drive_folder_id,
        "matches_returned": matches_returned,
        "threshold_used": threshold_used,
        "reference_image_hash": (
            hashlib.sha256(reference_image_bytes).hexdigest()
            if reference_image_bytes
            else None
        ),
        "details": details or {},
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def get_recent_audit_logs(limit: int = 100) -> list[dict]:
    log_path = _ensure_log_dir()
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    records = []
    for line in lines[-limit:]:
        try:
            records.append(json.loads(line))
        except Exception:
            pass
    return list(reversed(records))
