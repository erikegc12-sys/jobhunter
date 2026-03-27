"""
Workday scraper using Playwright.
Workday's CXS JSON API requires a full browser session (JS, cookies, fingerprinting).
We use Playwright to load the search page and intercept the API response directly.
"""

import asyncio
import json
import logging
from playwright.async_api import async_playwright, TimeoutError as PwTimeout

from scrapers.base import JobItem
from filters import should_include, detect_region, detect_level
from config import WORKDAY_TARGETS

logger = logging.getLogger(__name__)

SEARCH_TERMS = [
    "cinematic",
    "video editor",
    "motion designer",
    "motion design",
    "social media editor",
    "game capture",
]


async def _scrape_target(target: dict) -> list[JobItem]:
    company = target["company"]
    site_url = target.get("site_url", "").rstrip("/")
    # Derive the Workday search URL from the site_url or CXS URL
    # site_url examples: https://ea.wd1.myworkdayjobs.com/en-US/EA_BPO
    # or from CXS URL:   https://ea.wd1.myworkdayjobs.com/wday/cxs/ea/EA_BPO/jobs
    if site_url:
        search_base = site_url
    else:
        api_url = target["url"]
        parts = api_url.split("/wday/cxs/")
        if len(parts) == 2:
            base = parts[0]
            path_parts = parts[1].split("/")
            tenant_site = path_parts[1] if len(path_parts) >= 2 else ""
            search_base = f"{base}/en-US/{tenant_site}"
        else:
            search_base = api_url

    # CXS API endpoint (used for intercepting)
    cxs_url = target["url"]

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
        # Block images/fonts to speed things up
        await context.route(
            "**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,eot}", lambda r: r.abort()
        )

        page = await context.new_page()

        for term in SEARCH_TERMS:
            captured: list[dict] = []

            async def handle_response(response):
                if cxs_url.rstrip("/jobs") in response.url and "jobs" in response.url:
                    try:
                        body = await response.json()
                        postings = body.get("jobPostings", [])
                        if postings:
                            captured.extend(postings)
                    except Exception:
                        pass

            page.on("response", handle_response)

            search_url = f"{search_base}?q={term.replace(' ', '+')}"
            try:
                await page.goto(
                    search_url,
                    wait_until="networkidle",
                    timeout=30000,
                )
                await page.wait_for_timeout(2000)
            except PwTimeout:
                logger.warning(f"Workday {company} '{term}': page timeout")
            except Exception as e:
                logger.warning(f"Workday {company} '{term}': {e}")
            finally:
                page.remove_listener("response", handle_response)

            # Process captured API results
            if captured:
                for job in captured:
                    title = job.get("title", "")
                    location = job.get("locationsText", "")
                    path = job.get("externalPath", "")
                    job_url = (search_base.split("/en-US")[0] + path) if path else ""

                    if not job_url or job_url in seen:
                        continue

                    include, category = should_include(title, "", location)
                    if not include:
                        continue

                    seen.add(job_url)
                    results.append(
                        JobItem(
                            title=title,
                            company=company,
                            url=job_url,
                            platform=company.lower().split()[0],
                            location=location,
                            region=detect_region(location),
                            category=category,
                            level=detect_level(title),
                        )
                    )
            else:
                # Fallback: parse rendered HTML for job links
                try:
                    job_links = await page.query_selector_all(
                        "[data-automation-id='jobPostingTitle'], "
                        "a[href*='/job/'], a[href*='externalPath']"
                    )
                    for el in job_links:
                        title = (await el.inner_text()).strip()
                        href = await el.get_attribute("href") or ""
                        if not title or not href:
                            continue
                        job_url = href if href.startswith("http") else (
                            search_base.split("/en-US")[0] + href
                        )
                        if job_url in seen:
                            continue
                        include, category = should_include(title, "", "")
                        if not include:
                            continue
                        seen.add(job_url)
                        results.append(
                            JobItem(
                                title=title,
                                company=company,
                                url=job_url,
                                platform=company.lower().split()[0],
                                location="",
                                region="International",
                                category=category,
                                level=detect_level(title),
                            )
                        )
                except Exception as e:
                    logger.debug(f"Workday {company} HTML fallback error: {e}")

        await browser.close()

    logger.info(f"Workday {company}: {len(results)} matching jobs found")
    return results


async def scrape() -> list[JobItem]:
    all_results: list[JobItem] = []
    for target in WORKDAY_TARGETS:
        try:
            items = await _scrape_target(target)
            all_results.extend(items)
        except Exception as e:
            logger.error(f"Workday {target['company']} scraper failed: {e}")
    logger.info(f"Workday total: {len(all_results)} matching jobs")
    return all_results
