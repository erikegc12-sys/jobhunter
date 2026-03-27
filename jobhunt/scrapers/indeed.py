"""
Indeed scraper using Playwright.
Scrapes both international (indeed.com) and Brazilian (br.indeed.com) listings.
Indeed is heavily anti-bot — best-effort, results may be empty.
"""

import logging
from playwright.async_api import async_playwright, TimeoutError as PwTimeout
from scrapers.base import JobItem
from filters import should_include, detect_region
from config import INDEED_QUERIES_INTL, INDEED_QUERIES_BR

logger = logging.getLogger(__name__)

SEARCHES = (
    [("https://www.indeed.com/jobs?q={q}&sort=date&fromage=14", q) for q in INDEED_QUERIES_INTL]
    + [("https://br.indeed.com/jobs?q={q}&sort=date&fromage=14", q) for q in INDEED_QUERIES_BR]
)


async def _scrape_query(page, url_tpl: str, query: str) -> list[JobItem]:
    results = []
    url = url_tpl.format(q=query.replace(" ", "+"))
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_selector(
            '[data-testid="jobsearch-ResultsList"], #mosaic-jobResults', timeout=10000
        )
    except PwTimeout:
        logger.warning(f"Indeed: timeout loading '{query}'")
        return results
    except Exception as e:
        logger.warning(f"Indeed: failed '{query}': {e}")
        return results

    cards = await page.query_selector_all("div.job_seen_beacon, div.tapItem")
    for card in cards:
        try:
            title_el   = await card.query_selector("h2.jobTitle span, h2.jobTitle a")
            company_el = await card.query_selector("[data-testid='company-name']")
            location_el = await card.query_selector("[data-testid='text-location']")
            link_el    = await card.query_selector("h2.jobTitle a, a.jcs-JobTitle")

            title    = (await title_el.inner_text()).strip()   if title_el   else ""
            company  = (await company_el.inner_text()).strip() if company_el else ""
            location = (await location_el.inner_text()).strip() if location_el else ""
            href     = await link_el.get_attribute("href")    if link_el    else ""

            base = "https://br.indeed.com" if "br.indeed" in url else "https://www.indeed.com"
            job_url = f"{base}{href}" if href and href.startswith("/") else href

            if not title or not job_url:
                continue

            include, category = should_include(title, "", location)
            if not include:
                continue

            results.append(JobItem(
                title=title, company=company, url=job_url,
                platform="indeed", location=location,
                region=detect_region(location), category=category,
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
                viewport={"width": 1280, "height": 800},
            )
            await context.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2}", lambda r: r.abort())
            page = await context.new_page()

            for url_tpl, query in SEARCHES:
                for item in await _scrape_query(page, url_tpl, query):
                    if item.url not in seen:
                        seen.add(item.url)
                        results.append(item)

            await browser.close()
    except Exception as e:
        logger.error(f"Indeed scraper failed: {e}")

    logger.info(f"Indeed: {len(results)} matching jobs found")
    return results
