"""
Admin API: app config, user management, invite code generation.
All endpoints require admin role.
"""

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user, require_admin
from db.database import get_db
from db.models import AppConfig, DriveFileCache, InviteCode, User
from utils.auth_utils import hash_password
from utils.logger import get_recent_audit_logs, write_audit
from config import get_settings

router = APIRouter(prefix="/api/admin", tags=["admin"])
settings = get_settings()


# ─── Schemas ────────────────────────────────────────────────────────────────

class ConfigUpdate(BaseModel):
    drive_folder_id: Optional[str] = None
    face_similarity_threshold: Optional[float] = None
    stated_purpose: Optional[str] = None
    index_interval_hours: Optional[int] = None


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "user"


class CreateInviteRequest(BaseModel):
    role: str = "user"
    expires_in_hours: Optional[int] = 48


class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[str] = None


# ─── Config ─────────────────────────────────────────────────────────────────

@router.get("/config")
async def get_config(admin: User = Depends(require_admin)):
    return {
        "drive_folder_id": settings.drive_folder_id,
        "face_similarity_threshold": settings.face_similarity_threshold,
        "stated_purpose": settings.stated_purpose,
        "index_interval_hours": settings.index_interval_hours,
        "gemini_model": settings.gemini_model,
        "gemini_key_configured": bool(settings.gemini_api_key),
    }


@router.put("/config")
async def update_config(
    body: ConfigUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    updates = body.model_dump(exclude_none=True)
    for key, value in updates.items():
        stmt = select(AppConfig).where(AppConfig.key == key)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            record = AppConfig(key=key)
            db.add(record)
        record.value = str(value)
        record.updated_by = admin.id
    write_audit("admin_config_update", user_id=admin.id, user_email=admin.email,
                ip_address=request.client.host, details=updates)
    return {"updated": list(updates.keys())}


# ─── Users ───────────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_login": u.last_login.isoformat() if u.last_login else None,
        }
        for u in users
    ]


@router.post("/users", status_code=201)
async def create_user(
    body: CreateUserRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
    )
    db.add(user)
    write_audit("admin_create_user", user_id=admin.id, user_email=admin.email,
                ip_address=request.client.host, details={"new_user_email": body.email})
    return {"message": "User created", "email": body.email}


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.role is not None:
        user.role = body.role
    write_audit("admin_update_user", user_id=admin.id, user_email=admin.email,
                ip_address=request.client.host,
                details={"target_user": user_id, **body.model_dump(exclude_none=True)})
    return {"message": "User updated"}


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(User).where(User.id == user_id))


# ─── Invite Codes ────────────────────────────────────────────────────────────

def _random_code(length: int = 12) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "-".join(
        "".join(secrets.choice(alphabet) for _ in range(4))
        for _ in range(3)
    )  # Format: XXXX-XXXX-XXXX


@router.post("/invite-codes", status_code=201)
async def create_invite(
    body: CreateInviteRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    expires_at = None
    if body.expires_in_hours:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=body.expires_in_hours)
    invite = InviteCode(
        code=_random_code(),
        created_by=admin.id,
        role=body.role,
        expires_at=expires_at,
    )
    db.add(invite)
    await db.flush()
    return {
        "code": invite.code,
        "role": invite.role,
        "expires_at": expires_at.isoformat() if expires_at else None,
    }


@router.get("/invite-codes")
async def list_invites(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InviteCode).order_by(InviteCode.created_at.desc()).limit(50)
    )
    invites = result.scalars().all()
    return [
        {
            "id": inv.id,
            "code": inv.code,
            "role": inv.role,
            "used_by": inv.used_by,
            "used_at": inv.used_at.isoformat() if inv.used_at else None,
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        }
        for inv in invites
    ]


# ─── Audit Log ───────────────────────────────────────────────────────────────

@router.get("/audit-logs")
async def audit_logs(
    limit: int = 100,
    admin: User = Depends(require_admin),
):
    return get_recent_audit_logs(limit=limit)


# ─── Index Stats ─────────────────────────────────────────────────────────────

@router.get("/index-stats")
async def index_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total_q = await db.execute(select(func.count()).select_from(DriveFileCache))
    indexed_q = await db.execute(
        select(func.count()).select_from(DriveFileCache).where(
            DriveFileCache.embeddings.is_not(None)
        )
    )
    error_q = await db.execute(
        select(func.count()).select_from(DriveFileCache).where(
            DriveFileCache.index_error.is_not(None)
        )
    )
    return {
        "total_cached": total_q.scalar(),
        "successfully_indexed": indexed_q.scalar(),
        "with_errors": error_q.scalar(),
    }
