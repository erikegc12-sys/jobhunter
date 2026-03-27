"""
Vagas.com.br scraper using Playwright.
URL: https://www.vagas.com.br/vagas-de-{keyword}
"""

import logging
from playwright.async_api import async_playwright, TimeoutError as PwTimeout
from scrapers.base import JobItem
from filters import should_include, detect_level
from config import VAGAS_QUERIES

logger = logging.getLogger(__name__)
BASE_URL = "https://www.vagas.com.br/vagas-de-{q}"


async def _scrape_query(page, query: str) -> list[JobItem]:
    results = []
    url = BASE_URL.format(q=query)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(2000)
    except PwTimeout:
        logger.warning(f"Vagas: timeout '{query}'")
        return results
    except Exception as e:
        logger.warning(f"Vagas: error '{query}': {e}")
        return results

    # Vagas job cards
    cards = await page.query_selector_all("li.vaga, .vaga, article.vaga")
    if not cards:
        # Fallback: grab all job links
        cards = await page.query_selector_all("a[href*='/vagas/']")

    for card in cards:
        try:
            title_el   = await card.query_selector("h2.cargo, .cargo, h2, h3")
            company_el = await card.query_selector(".empresa, .company")
            loc_el     = await card.query_selector(".local, .location")
            link_el    = await card.query_selector("a[href*='/vagas/']")
            if not link_el and (await card.get_attribute("href") or "").startswith("/"):
                link_el = card

            title   = (await title_el.inner_text()).strip()   if title_el   else (await card.inner_text()).strip()[:80]
            company = (await company_el.inner_text()).strip() if company_el else ""
            location = (await loc_el.inner_text()).strip()    if loc_el     else "Brasil"
            href    = await link_el.get_attribute("href")    if link_el    else ""

            job_url = f"https://www.vagas.com.br{href}" if href and href.startswith("/") else href
            if not title or not job_url:
                continue

            include, category = should_include(title, "", location)
            if not include:
                continue

            results.append(JobItem(
                title=title, company=company, url=job_url,
                platform="vagas", location=location or "Brasil",
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

            for query in VAGAS_QUERIES:
                for item in await _scrape_query(page, query):
                    if item.url not in seen:
                        seen.add(item.url)
                        results.append(item)

            await browser.close()
    except Exception as e:
        logger.error(f"Vagas scraper failed: {e}")

    logger.info(f"Vagas: {len(results)} matching jobs found")
    return results
