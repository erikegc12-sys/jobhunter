"""
Orchestrates all scrapers, deduplicates, and saves to the database.
"""

import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import Job
from scrapers import greenhouse, lever, indeed, glassdoor
from scrapers import careers_ea, careers_blizzard, careers_2k
from scrapers import linkedin, vagas, catho, infojobs
from filters import detect_level

logger = logging.getLogger(__name__)

# Track last run time and status
scrape_state = {
    "running": False,
    "last_run": None,
    "last_result": None,  # {"found": int, "new": int, "errors": list}
}


async def run_all_scrapers() -> dict:
    """Run all scrapers concurrently and return summary."""
    if scrape_state["running"]:
        return {"status": "already_running"}

    scrape_state["running"] = True
    start = datetime.utcnow()
    logger.info("=== Scrape run started ===")

    # Run API-based scrapers concurrently (fast, safe)
    try:
        api_results = await asyncio.gather(
            greenhouse.scrape(),
            lever.scrape(),
            return_exceptions=True,
        )
    except Exception as e:
        logger.error(f"API scrapers failed: {e}")
        api_results = [[], []]

    # Run Playwright scrapers sequentially (one browser at a time)
    playwright_results = []
    for scraper in [
        indeed.scrape,
        glassdoor.scrape,
        linkedin.scrape,
        careers_ea.scrape,
        careers_blizzard.scrape,
        careers_2k.scrape,
        vagas.scrape,
        catho.scrape,
        infojobs.scrape,
    ]:
        try:
            items = await scraper()
            playwright_results.append(items)
        except Exception as e:
            logger.error(f"Playwright scraper {scraper.__module__} failed: {e}")
            playwright_results.append([])

    # Flatten all results
    all_items = []
    for batch in [*api_results, *playwright_results]:
        if isinstance(batch, Exception):
            logger.error(f"Scraper returned exception: {batch}")
            continue
        all_items.extend(batch)

    logger.info(f"Total raw results across all scrapers: {len(all_items)}")

    # Save to DB
    new_count, skipped = _save_jobs(all_items)

    elapsed = (datetime.utcnow() - start).seconds
    result = {
        "status": "done",
        "found": len(all_items),
        "new": new_count,
        "skipped": skipped,
        "elapsed_seconds": elapsed,
        "timestamp": datetime.utcnow().isoformat(),
    }

    scrape_state["running"] = False
    scrape_state["last_run"] = datetime.utcnow().isoformat()
    scrape_state["last_result"] = result

    logger.info(f"=== Scrape done: {new_count} new, {skipped} skipped, {elapsed}s ===")
    return result


def _save_jobs(items) -> tuple[int, int]:
    """Insert new jobs, skip duplicates (unique by URL)."""
    db: Session = SessionLocal()
    new_count = 0
    skipped = 0
    try:
        for item in items:
            job = Job(
                title=item.title,
                company=item.company,
                url=item.url,
                platform=item.platform,
                location=item.location,
                description=item.description,
                region=item.region,
                category=item.category,
                level=item.level or detect_level(item.title, item.description),
                date_found=item.date_found,
                status="new",
            )
            db.add(job)
            try:
                db.flush()
                new_count += 1
            except IntegrityError:
                db.rollback()
                skipped += 1
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"DB save error: {e}")
    finally:
        db.close()

    return new_count, skipped
