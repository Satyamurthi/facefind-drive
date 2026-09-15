"""
APScheduler setup for periodic Drive folder re-indexing.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import get_settings
from core.indexer import run_index

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler()


async def _scheduled_index():
    folder_id = settings.drive_folder_id
    if not folder_id:
        logger.warning("No DRIVE_FOLDER_ID configured — skipping scheduled index")
        return
    logger.info("Scheduled incremental index starting for folder %s", folder_id)
    summary = await run_index(folder_id, incremental=True)
    logger.info("Scheduled index complete: %s", summary)


def start_scheduler():
    scheduler.add_job(
        _scheduled_index,
        trigger=IntervalTrigger(hours=settings.index_interval_hours),
        id="drive_index",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started — Drive re-index every %d hour(s)",
        settings.index_interval_hours,
    )


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
