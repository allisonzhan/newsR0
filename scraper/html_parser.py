"""
HTML scraper — fallback for sources that do not publish RSS feeds.
Uses BeautifulSoup for static pages; Playwright for JS-rendered pages.

Phase 4 feature — sources with type: html in sources.yaml will use this parser.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

EXCERPT_MAX_CHARS = 150
REQUEST_TIMEOUT = 20
MIN_CRAWL_DELAY = 2   # longer delay for HTML scraping

_robots_cache: dict[str, RobotFileParser] = {}
USER_AGENT = "newsR0-scraper/1.0 (news aggregator; respectful bot)"


def _get_robots(base_url: str) -> RobotFileParser:
    """Fetch and cache robots.txt for a domain."""
    parsed = urlparse(base_url)
    domain = f"{parsed.scheme}://{parsed.netloc}"
    if domain not in _robots_cache:
        rp = RobotFileParser()
        rp.set_url(f"{domain}/robots.txt")
        try:
            rp.read()
        except Exception as exc:
            logger.warning("Could not read robots.txt for %s: %s", domain, exc)
        _robots_cache[domain] = rp
    return _robots_cache[domain]


def _can_fetch(url: str) -> bool:
    """Check robots.txt permission before fetching."""
    rp = _get_robots(url)
    return rp.can_fetch(USER_AGENT, url)


def _extract_excerpt(soup: BeautifulSoup, url: str) -> str:
    """Extract excerpt from meta description or first paragraph."""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"][:EXCERPT_MAX_CHARS]
    p = soup.find("p")
    if p:
        return p.get_text(strip=True)[:EXCERPT_MAX_CHARS]
    return ""


def scrape_static(source: dict) -> list[dict]:
    """
    Scrape a static HTML page with BeautifulSoup.
    Applies a generic heuristic for article cards — customize per source as needed.
    """
    name = source.get("name", "Unknown")
    url = source.get("url", "")
    articles = []

    if not _can_fetch(url):
        raise PermissionError(f"robots.txt disallows scraping {url}")

    logger.info("Scraping HTML (static): %s (%s)", name, url)
    time.sleep(MIN_CRAWL_DELAY)

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    # Generic heuristic: look for <article> or <h2>/<h3> anchor tags
    candidates = soup.find_all(["article", "h2", "h3"], limit=50)
    for tag in candidates:
        anchor = tag.find("a", href=True) if tag.name != "a" else tag
        if not anchor:
            continue
        title = anchor.get_text(strip=True)
        href = anchor["href"]
        if not href.startswith("http"):
            href = base_url + href
        if not title or not href:
            continue
        articles.append(
            {
                "title": title,
                "url": href,
                "source": name,
                "excerpt": "",
                "published_at": None,
            }
        )

    logger.info("Scraped %d candidate articles from %s (HTML)", len(articles), name)
    return articles


def scrape_dynamic(source: dict) -> list[dict]:
    """
    Scrape a JS-rendered page using Playwright.
    Requires `playwright` to be installed and browsers downloaded.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ImportError(
            "Playwright is not installed. Run: pip install playwright && playwright install chromium"
        )

    name = source.get("name", "Unknown")
    url = source.get("url", "")

    if not _can_fetch(url):
        raise PermissionError(f"robots.txt disallows scraping {url}")

    logger.info("Scraping HTML (dynamic/Playwright): %s (%s)", name, url)
    time.sleep(MIN_CRAWL_DELAY)

    articles = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        content = page.content()
        browser.close()

    soup = BeautifulSoup(content, "html.parser")
    base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    candidates = soup.find_all(["article", "h2", "h3"], limit=50)
    for tag in candidates:
        anchor = tag.find("a", href=True)
        if not anchor:
            continue
        title = anchor.get_text(strip=True)
        href = anchor["href"]
        if not href.startswith("http"):
            href = base_url + href
        if not title or not href:
            continue
        articles.append(
            {
                "title": title,
                "url": href,
                "source": name,
                "excerpt": "",
                "published_at": None,
            }
        )

    logger.info("Scraped %d candidate articles from %s (Playwright)", len(articles), name)
    return articles
