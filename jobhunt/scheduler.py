"""
APScheduler — scraper every 6h, Gmail check every 30min.
"""

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import SCRAPE_INTERVAL_HOURS

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def _run_gmail_check():
    from gmail_checker import check_gmail
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, check_gmail)
    logger.info(f"Gmail check: {result}")


def start_scheduler():
    from runner import run_all_scrapers

    scheduler.add_job(
        run_all_scrapers,
        trigger="interval",
        hours=SCRAPE_INTERVAL_HOURS,
        id="scrape_job",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.add_job(
        _run_gmail_check,
        trigger="interval",
        minutes=30,
        id="gmail_job",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    logger.info(f"Scheduler: scrape every {SCRAPE_INTERVAL_HOURS}h · Gmail every 30min")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
