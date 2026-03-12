"""
RSS feed parser — primary scraping method for sources that publish RSS/Atom feeds.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import feedparser
import requests

logger = logging.getLogger(__name__)

EXCERPT_MAX_CHARS = 150
REQUEST_TIMEOUT = 15  # seconds
MIN_CRAWL_DELAY = 1   # seconds between requests per domain


def _parse_date(entry: feedparser.FeedParserDict) -> Optional[datetime]:
    """Return a timezone-aware datetime from a feed entry, or None."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
    return None


def _extract_excerpt(entry: feedparser.FeedParserDict) -> str:
    """Extract a short excerpt from the feed entry."""
    text = ""
    if hasattr(entry, "summary") and entry.summary:
        text = entry.summary
    elif hasattr(entry, "description") and entry.description:
        text = entry.description
    elif hasattr(entry, "content") and entry.content:
        text = entry.content[0].get("value", "")

    # Strip basic HTML tags
    import re
    text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(text.split())  # normalize whitespace
    return text[:EXCERPT_MAX_CHARS]


def parse_feed(source: dict) -> list[dict]:
    """
    Fetch and parse an RSS/Atom feed for a source config entry.

    Returns a list of article dicts:
        title, url, source, excerpt, published_at
    """
    name = source.get("name", "Unknown")
    url = source.get("url", "")
    articles = []

    logger.info("Fetching RSS feed: %s (%s)", name, url)
    time.sleep(MIN_CRAWL_DELAY)

    try:
        headers = {"User-Agent": "newsR0-scraper/1.0 (news aggregator; respectful bot)"}
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except requests.RequestException as exc:
        logger.error("Failed to fetch %s: %s", name, exc)
        raise

    if feed.bozo and not feed.entries:
        raise ValueError(f"Feed parse error for {name}: {feed.bozo_exception}")

    for entry in feed.entries:
        article_url = entry.get("link", "").strip()
        title = entry.get("title", "").strip()
        if not article_url or not title:
            continue

        articles.append(
            {
                "title": title,
                "url": article_url,
                "source": name,
                "excerpt": _extract_excerpt(entry),
                "published_at": _parse_date(entry),
            }
        )

    logger.info("Parsed %d articles from %s", len(articles), name)
    return articles
