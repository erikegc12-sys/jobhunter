"""
Blizzard Entertainment careers — careers.blizzard.com (Phenom People ATS)
Search URL: https://careers.blizzard.com/global/en/search-results?keywords={term}
"""

import logging
from playwright.async_api import async_playwright, TimeoutError as PwTimeout
from scrapers.base import JobItem
from filters import should_include, detect_region, detect_level

logger = logging.getLogger(__name__)

BASE_SEARCH = "https://careers.blizzard.com/global/en/search-results"

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
            locale="en-US",
            viewport={"width": 1280, "height": 900},
        )
        await context.route(
            "**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf}", lambda r: r.abort()
        )
        page = await context.new_page()

        for term in SEARCH_TERMS:
            url = f"{BASE_SEARCH}?keywords={term.replace(' ', '+')}"
            try:
                await page.goto(url, wait_until="networkidle", timeout=35000)
                await page.wait_for_timeout(1500)
            except PwTimeout:
                logger.warning(f"Blizzard '{term}': page timeout")
                continue
            except Exception as e:
                logger.warning(f"Blizzard '{term}': {e}")
                continue

            job_links = await page.query_selector_all("a[href*='/job/']")
            for a in job_links:
                try:
                    title = (await a.inner_text()).strip()
                    href = await a.get_attribute("href") or ""

                    if not title or not href:
                        continue

                    job_url = (
                        href if href.startswith("http")
                        else f"https://careers.blizzard.com{href}"
                    )

                    if job_url in seen:
                        continue

                    # Extract location from parent card text
                    card_text = await a.evaluate(
                        "el => {"
                        "  const p = el.closest('li,article,[class*=ph-card],[class*=card]');"
                        "  return p ? p.innerText : el.parentElement ? el.parentElement.innerText : '';"
                        "}"
                    )
                    location = ""
                    if card_text:
                        import re as _re
                        m = _re.search(r"Location\s*\n\s*(.+?)(?:\n|$)", card_text)
                        if m:
                            location = m.group(1).strip()

                    include, category = should_include(title, "", location)
                    if not include:
                        continue

                    seen.add(job_url)
                    results.append(
                        JobItem(
                            title=title,
                            company="Blizzard Entertainment",
                            url=job_url,
                            platform="blizzard",
                            location=location,
                            region=detect_region(location),
                            category=category,
                            level=detect_level(title),
                        )
                    )
                except Exception:
                    continue

        await browser.close()

    logger.info(f"Blizzard: {len(results)} matching jobs found")
    return results
