"""
Greenhouse JSON API scraper.
Endpoint: https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true
No auth needed — fully public.
"""

import aiohttp
import logging
from scrapers.base import JobItem
from filters import should_include, detect_region
from config import GREENHOUSE_BOARDS

logger = logging.getLogger(__name__)
API_BASE = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"


async def scrape() -> list[JobItem]:
    results = []
    async with aiohttp.ClientSession() as session:
        for target in GREENHOUSE_BOARDS:
            url = API_BASE.format(board=target["board"])
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        logger.warning(f"Greenhouse {target['company']}: HTTP {resp.status}")
                        continue
                    data = await resp.json()
                    jobs = data.get("jobs", [])
                    logger.info(f"Greenhouse {target['company']}: {len(jobs)} total jobs")

                    for job in jobs:
                        title = job.get("title", "")
                        location = job.get("location", {}).get("name", "")
                        description = job.get("content", "") or ""
                        job_url = job.get("absolute_url", "")

                        include, category = should_include(title, description, location)
                        if not include:
                            continue

                        results.append(JobItem(
                            title=title,
                            company=target["company"],
                            url=job_url,
                            platform="greenhouse",
                            location=location,
                            description=description[:2000],
                            region=detect_region(location, description),
                            category=category,
                        ))

            except Exception as e:
                logger.error(f"Greenhouse {target['company']} error: {e}")

    logger.info(f"Greenhouse: {len(results)} matching jobs found")
    return results
