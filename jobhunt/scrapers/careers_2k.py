"""
2K Games careers — 2k.com/en-US/careers
Uses Playwright to scrape their careers listing page.
"""

import logging
from playwright.async_api import async_playwright, TimeoutError as PwTimeout
from scrapers.base import JobItem
from filters import should_include, detect_region

logger = logging.getLogger(__name__)
CAREERS_URL = "https://2k.com/en-US/careers/"


async def scrape() -> list[JobItem]:
    results = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 900},
            )
            page = await context.new_page()
            await page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2}", lambda r: r.abort())

            try:
                await page.goto(CAREERS_URL, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(3000)
            except PwTimeout:
                logger.warning("2K: timeout loading careers page")
                await browser.close()
                return results

            # Try common job listing selectors
            cards = await page.query_selector_all("a[href*='job'], li[class*='job'], div[class*='job-item']")
            if not cards:
                # Fallback: grab all links with job-like text
                cards = await page.query_selector_all("a")

            for card in cards:
                try:
                    title = (await card.inner_text()).strip()
                    href = await card.get_attribute("href") or ""

                    if not title or not href:
                        continue
                    if "job" not in href.lower() and "career" not in href.lower() and len(title) < 5:
                        continue

                    job_url = href if href.startswith("http") else f"https://2k.com{href}"

                    include, category = should_include(title)
                    if not include:
                        continue

                    results.append(JobItem(
                        title=title,
                        company="2K Games",
                        url=job_url,
                        platform="2k",
                        region="International",
                        category=category,
                    ))
                except Exception:
                    continue

            await browser.close()
    except Exception as e:
        logger.error(f"2K scraper failed: {e}")

    logger.info(f"2K: {len(results)} matching jobs found")
    return results
