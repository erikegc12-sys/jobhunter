"""
Catho.com.br scraper using Playwright.
URL: https://www.catho.com.br/vagas/{keyword}/
"""

import logging
from playwright.async_api import async_playwright, TimeoutError as PwTimeout
from scrapers.base import JobItem
from filters import should_include, detect_level
from config import CATHO_QUERIES

logger = logging.getLogger(__name__)
BASE_URL = "https://www.catho.com.br/vagas/{q}/"


async def _scrape_query(page, query: str) -> list[JobItem]:
    results = []
    url = BASE_URL.format(q=query)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(2000)
    except PwTimeout:
        logger.warning(f"Catho: timeout '{query}'")
        return results
    except Exception as e:
        logger.warning(f"Catho: error '{query}': {e}")
        return results

    cards = await page.query_selector_all(
        "li[class*='job'], div[class*='job-card'], article[class*='job'], "
        "div[class*='JobCard'], li[class*='JobCard']"
    )
    if not cards:
        cards = await page.query_selector_all("a[href*='/vagas/']")

    for card in cards:
        try:
            title_el   = await card.query_selector("h2, h3, [class*='title'], [class*='Title']")
            company_el = await card.query_selector("[class*='company'], [class*='Company'], [class*='empresa']")
            loc_el     = await card.query_selector("[class*='location'], [class*='Location'], [class*='local']")
            link_el    = await card.query_selector("a[href*='/vagas/']")

            title    = (await title_el.inner_text()).strip()   if title_el   else ""
            company  = (await company_el.inner_text()).strip() if company_el else ""
            location = (await loc_el.inner_text()).strip()     if loc_el     else "Brasil"
            href     = await link_el.get_attribute("href")    if link_el    else ""

            job_url = f"https://www.catho.com.br{href}" if href and href.startswith("/") else href
            if not title or not job_url:
                continue

            include, category = should_include(title, "", location)
            if not include:
                continue

            results.append(JobItem(
                title=title, company=company, url=job_url,
                platform="catho", location=location or "Brasil",
                region="BR", category=category,
                level=detect_level(title),
            ))
        except Exception:
            continue

    return results


async def scrape() -> list[JobItem]:
    results = []
    seen: set[str] = set()
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="pt-BR",
                viewport={"width": 1280, "height": 900},
            )
            await context.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2}", lambda r: r.abort())
            page = await context.new_page()

            for query in CATHO_QUERIES:
                for item in await _scrape_query(page, query):
                    if item.url not in seen:
                        seen.add(item.url)
                        results.append(item)

            await browser.close()
    except Exception as e:
        logger.error(f"Catho scraper failed: {e}")

    logger.info(f"Catho: {len(results)} matching jobs found")
    return results
