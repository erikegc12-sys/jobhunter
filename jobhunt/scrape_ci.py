"""
CI scraper — runs Greenhouse, Lever, and Workday scrapers,
merges with existing docs/jobs.json (dedup by URL), writes back.
No database needed. Run by GitHub Actions.
"""
import asyncio
import json
import os
import sys
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Resolve paths relative to this file
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

JOBS_JSON = os.path.join(HERE, "docs", "jobs.json")


async def main():
    from scrapers import greenhouse, lever
    from scrapers.workday import scrape as workday_scrape

    logger.info("Running API scrapers (Greenhouse + Lever)...")
    api_results = await asyncio.gather(
        greenhouse.scrape(),
        lever.scrape(),
        return_exceptions=True,
    )

    logger.info("Running Workday scrapers...")
    try:
        workday_results = await workday_scrape()
    except Exception as e:
        logger.error(f"Workday failed: {e}")
        workday_results = []

    # Flatten
    new_jobs = []
    for batch in [*api_results, workday_results]:
        if isinstance(batch, Exception):
            logger.error(f"Scraper error: {batch}")
            continue
        new_jobs.extend(batch)

    logger.info(f"Scraped {len(new_jobs)} matching jobs total")

    # Load existing jobs for dedup
    existing = {}
    if os.path.exists(JOBS_JSON):
        try:
            with open(JOBS_JSON, encoding="utf-8") as f:
                data = json.load(f)
            for job in data.get("jobs", []):
                existing[job["url"]] = job
        except Exception as e:
            logger.warning(f"Could not load existing jobs.json: {e}")

    added = 0
    for job in new_jobs:
        if job.url not in existing:
            existing[job.url] = {
                "title": job.title,
                "company": job.company,
                "url": job.url,
                "platform": job.platform,
                "location": job.location,
                "region": job.region,
                "category": job.category,
                "level": job.level,
                "status": "new",
                "date_found": job.date_found.isoformat() if hasattr(job.date_found, "isoformat") else str(job.date_found),
            }
            added += 1

    out = {
        "jobs": list(existing.values()),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    os.makedirs(os.path.dirname(JOBS_JSON), exist_ok=True)
    with open(JOBS_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    logger.info(f"Done: {added} new jobs added, {len(existing)} total in jobs.json")


if __name__ == "__main__":
    asyncio.run(main())
