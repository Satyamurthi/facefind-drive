import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Boolean, DateTime, Text, Integer, JSON
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def gen_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="user")          # "user" | "admin"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id = Column(String, primary_key=True, default=gen_uuid)
    code = Column(String, unique=True, nullable=False, index=True)
    created_by = Column(String, nullable=False)    # admin user id
    used_by = Column(String, nullable=True)        # user id who redeemed
    role = Column(String, default="user")
    used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DriveFileCache(Base):
    __tablename__ = "drive_file_cache"

    id = Column(String, primary_key=True, default=gen_uuid)
    file_id = Column(String, unique=True, nullable=False, index=True)
    filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    web_view_link = Column(Text, nullable=True)
    modified_time = Column(String, nullable=True)  # ISO string from Drive
    face_count = Column(Integer, default=0)
    embeddings = Column(JSON, nullable=True)        # List[List[float]]
    indexed_at = Column(DateTime, default=datetime.utcnow)
    index_error = Column(Text, nullable=True)       # error message if indexing failed


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(String, nullable=True)
    user_email = Column(String, nullable=True)
    action = Column(String, nullable=False)         # "search" | "download" | "login" | "admin_*"
    reference_image_hash = Column(String, nullable=True)
    folder_id = Column(String, nullable=True)
    matches_returned = Column(Integer, nullable=True)
    threshold_used = Column(Float, nullable=True)
    ip_address = Column(String, nullable=True)
    details = Column(JSON, nullable=True)           # extra context


class AppConfig(Base):
    __tablename__ = "app_config"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String, nullable=True)
