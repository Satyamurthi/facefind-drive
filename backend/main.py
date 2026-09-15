"""
FaceFind Drive — FastAPI Application Entry Point
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from db.database import init_db
from core.scheduler import start_scheduler, stop_scheduler
from api import auth, search, admin, download, cache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("Starting FaceFind Drive backend…")
    # Ensure log directory exists
    os.makedirs(os.path.dirname(settings.audit_log_file), exist_ok=True)
    # Initialize DB tables
    await init_db()
    logger.info("Database initialized")
    # Start background scheduler
    start_scheduler()
    logger.info("Scheduler started")
    yield
    # Shutdown
    stop_scheduler()
    logger.info("FaceFind Drive backend stopped")


app = FastAPI(
    title="FaceFind Drive API",
    description="Facial recognition search over a Google Drive folder.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(search.router)
app.include_router(admin.router)
app.include_router(download.router)
app.include_router(cache.router)


@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "app": settings.app_name}


@app.get("/api/purpose")
async def stated_purpose():
    """Public endpoint — returns the app's stated purpose for the consent banner."""
    return {"stated_purpose": settings.stated_purpose, "app_name": settings.app_name}
