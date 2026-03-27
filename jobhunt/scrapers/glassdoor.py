"""
Glassdoor scraper using Playwright.
Glassdoor requires login for full access — this scrapes publicly visible listings.
"""

import logging
from playwright.async_api import async_playwright, TimeoutError as PwTimeout
from scrapers.base import JobItem
from filters import should_include, detect_region
from config import GLASSDOOR_QUERIES

logger = logging.getLogger(__name__)
BASE_URL = "https://www.glassdoor.com/Job/jobs.htm?sc.keyword={query}&fromAge=14"


async def _scrape_query(page, query: str) -> list[JobItem]:
    results = []
    url = BASE_URL.format(query=query.replace(" ", "+"))

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_selector("li[data-test='jobListing']", timeout=12000)
    except PwTimeout:
        logger.warning(f"Glassdoor: timeout loading '{query}'")
        return results
    except Exception as e:
        logger.warning(f"Glassdoor: failed loading '{query}': {e}")
        return results

    cards = await page.query_selector_all("li[data-test='jobListing']")
    for card in cards:
        try:
            title_el = await card.query_selector("[data-test='job-title']")
            company_el = await card.query_selector("[data-test='employer-name']")
            location_el = await card.query_selector("[data-test='emp-location']")
            link_el = await card.query_selector("a[data-test='job-title']")

            title = (await title_el.inner_text()).strip() if title_el else ""
            company = (await company_el.inner_text()).strip() if company_el else ""
            location = (await location_el.inner_text()).strip() if location_el else ""
            href = await link_el.get_attribute("href") if link_el else ""
            job_url = f"https://www.glassdoor.com{href}" if href and href.startswith("/") else href

            if not title or not job_url:
                continue

            include, category = should_include(title, "", location)
            if not include:
                continue

            results.append(JobItem(
                title=title,
                company=company,
                url=job_url,
                platform="glassdoor",
                location=location,
                region=detect_region(location),
                category=category,
            ))
        except Exception:
            continue

    return results


async def scrape() -> list[JobItem]:
    results = []
    seen = set()

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

            for query in GLASSDOOR_QUERIES:
                items = await _scrape_query(page, query)
                for item in items:
                    if item.url not in seen:
                        seen.add(item.url)
                        results.append(item)

            await browser.close()
    except Exception as e:
        logger.error(f"Glassdoor scraper failed: {e}")

    logger.info(f"Glassdoor: {len(results)} matching jobs found")
    return results
