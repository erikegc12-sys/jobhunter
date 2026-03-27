"""
LinkedIn job scraper using Playwright.
Scrapes public search results (no login) for both international and BR.
LinkedIn is aggressive with bot detection — best-effort.
"""

import logging
from playwright.async_api import async_playwright, TimeoutError as PwTimeout
from scrapers.base import JobItem
from filters import should_include, detect_region
from config import LINKEDIN_QUERIES_INTL, LINKEDIN_QUERIES_BR

logger = logging.getLogger(__name__)

# f_TPR=r604800 = last 7 days; sortBy=DD = most recent
INTL_URL = "https://www.linkedin.com/jobs/search/?keywords={q}&f_TPR=r604800&sortBy=DD"
BR_URL   = "https://www.linkedin.com/jobs/search/?keywords={q}&location=Brasil&f_TPR=r604800&sortBy=DD"

SEARCHES = (
    [(INTL_URL, q) for q in LINKEDIN_QUERIES_INTL]
    + [(BR_URL, q) for q in LINKEDIN_QUERIES_BR]
)

JOB_CARD_SELECTORS = [
    ".base-search-card",
    ".job-search-card",
    "li.jobs-search-results__list-item",
]
TITLE_SEL   = ".base-search-card__title, .job-search-card__title"
COMPANY_SEL = ".base-search-card__subtitle, .job-search-card__company-name"
LOC_SEL     = ".job-search-card__location"
LINK_SEL    = "a.base-card__full-link, a.job-search-card__list-tail"


async def _scrape_query(page, url_tpl: str, query: str) -> list[JobItem]:
    results = []
    url = url_tpl.format(q=query.replace(" ", "+"))
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
    except PwTimeout:
        logger.warning(f"LinkedIn: timeout '{query}'")
        return results
    except Exception as e:
        logger.warning(f"LinkedIn: error '{query}': {e}")
        return results

    # Try each card selector
    cards = []
    for sel in JOB_CARD_SELECTORS:
        cards = await page.query_selector_all(sel)
        if cards:
            break

    for card in cards:
        try:
            title_el   = await card.query_selector(TITLE_SEL)
            company_el = await card.query_selector(COMPANY_SEL)
            loc_el     = await card.query_selector(LOC_SEL)
            link_el    = await card.query_selector(LINK_SEL)

            title    = (await title_el.inner_text()).strip()   if title_el   else ""
            company  = (await company_el.inner_text()).strip() if company_el else ""
            location = (await loc_el.inner_text()).strip()     if loc_el     else ""
            href     = await link_el.get_attribute("href")    if link_el    else ""

            # Fallback: try the card itself as a link
            if not href:
                href = await card.get_attribute("href") or ""

            job_url = href.split("?")[0] if href.startswith("http") else ""
            if not title or not job_url:
                continue

            include, category = should_include(title, "", location)
            if not include:
                continue

            results.append(JobItem(
                title=title, company=company, url=job_url,
                platform="linkedin", location=location,
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
                viewport={"width": 1280, "height": 900},
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
        logger.error(f"LinkedIn scraper failed: {e}")

    logger.info(f"LinkedIn: {len(results)} matching jobs found")
    return results
