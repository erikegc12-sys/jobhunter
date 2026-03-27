"""
Lever JSON API scraper.
Endpoint: https://api.lever.co/v0/postings/{company}?mode=json
No auth needed — fully public.
"""

import aiohttp
import logging
from scrapers.base import JobItem
from filters import should_include, detect_region
from config import LEVER_COMPANIES

logger = logging.getLogger(__name__)
API_BASE = "https://api.lever.co/v0/postings/{company}?mode=json"


async def scrape() -> list[JobItem]:
    results = []
    if not LEVER_COMPANIES:
        return results

    async with aiohttp.ClientSession() as session:
        for target in LEVER_COMPANIES:
            url = API_BASE.format(company=target["slug"])
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        logger.warning(f"Lever {target['company']}: HTTP {resp.status}")
                        continue
                    jobs = await resp.json()
                    logger.info(f"Lever {target['company']}: {len(jobs)} total jobs")

                    for job in jobs:
                        title = job.get("text", "")
                        location = job.get("categories", {}).get("location", "")
                        description = job.get("descriptionPlain", "") or ""
                        job_url = job.get("hostedUrl", "")

                        include, category = should_include(title, description, location)
                        if not include:
                            continue

                        results.append(JobItem(
                            title=title,
                            company=target["company"],
                            url=job_url,
                            platform="lever",
                            location=location,
                            description=description[:2000],
                            region=detect_region(location, description),
                            category=category,
                        ))

            except Exception as e:
                logger.error(f"Lever {target['company']} error: {e}")

    logger.info(f"Lever: {len(results)} matching jobs found")
    return results
