from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "FaceFind Drive"
    app_env: str = "development"
    secret_key: str = "CHANGE_ME"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # Database (Supabase PostgreSQL)
    database_url: str = "postgresql+asyncpg://user:password@host:6543/postgres"

    # Supabase (optional — for Storage / Auth client)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # Google Drive
    google_service_account_file: str = "./service_account/credentials.json"
    drive_folder_id: str = ""

    # Gemini Vision (Face Recognition)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"   # gemini-1.5-flash | gemini-1.5-pro | gemini-2.0-flash
    gemini_concurrency: int = 5              # parallel Gemini calls during indexing
    face_similarity_threshold: float = 0.68  # 0–1 confidence cutoff shown in UI

    # Indexer
    index_interval_hours: int = 6
    index_concurrency: int = 4

    # CORS
    allowed_origins: str = "http://localhost:5173"

    # Audit
    audit_log_file: str = "./logs/audit.jsonl"

    # Consent
    stated_purpose: str = "Event Photo Retrieval"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
