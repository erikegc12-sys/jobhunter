"""
EA (Electronic Arts) careers — jobs.ea.com (Taleo ATS)
Search URL: https://jobs.ea.com/en_US/careers/SearchJobs/{keyword}
"""

import logging
from playwright.async_api import async_playwright, TimeoutError as PwTimeout
from scrapers.base import JobItem
from filters import should_include, detect_region, detect_level

logger = logging.getLogger(__name__)

BASE_URL = "https://jobs.ea.com/en_US/careers/SearchJobs"

SEARCH_TERMS = [
    "cinematic",
    "video editor",
    "motion designer",
    "motion design",
    "social media editor",
    "game capture",
]


async def scrape() -> list[JobItem]:
    results: list[JobItem] = []
    seen: set[str] = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        await context.route(
            "**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf}", lambda r: r.abort()
        )
        page = await context.new_page()

        for term in SEARCH_TERMS:
            url = f"{BASE_URL}/{term.replace(' ', '%20')}"
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(1500)
            except PwTimeout:
                logger.warning(f"EA '{term}': page timeout")
                continue
            except Exception as e:
                logger.warning(f"EA '{term}': {e}")
                continue

            # Each job is in an <article> element
            articles = await page.query_selector_all("article")
            for article in articles:
                try:
                    # Get the primary JobDetail link (first one in the article)
                    link = await article.query_selector("a[href*='JobDetail']")
                    if not link:
                        continue

                    title = (await link.inner_text()).strip()
                    href = await link.get_attribute("href") or ""

                    if not title or not href:
                        continue

                    job_url = (
                        href
                        if href.startswith("http")
                        else f"https://jobs.ea.com{href}"
                    )

                    if job_url in seen:
                        continue

                    # Extract location from article text
                    full_text = (await article.inner_text()).strip()
                    # Article text format: "{title}\n{location} • Role ID …"
                    lines = [l.strip() for l in full_text.splitlines() if l.strip()]
                    location = lines[1] if len(lines) > 1 else ""
                    # Clean up location (remove "Role ID …" suffix)
                    if "Role ID" in location:
                        location = location.split("Role ID")[0].strip().rstrip("•").strip()

                    include, category = should_include(title, "", location)
                    if not include:
                        continue

                    seen.add(job_url)
                    results.append(
                        JobItem(
                            title=title,
                            company="Electronic Arts",
                            url=job_url,
                            platform="ea",
                            location=location,
                            region=detect_region(location),
                            category=category,
                            level=detect_level(title),
                        )
                    )
                except Exception:
                    continue

        await browser.close()

    logger.info(f"EA: {len(results)} matching jobs found")
    return results
