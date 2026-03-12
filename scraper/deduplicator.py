"""
Deduplicator — removes duplicate articles by URL (exact) and by title
similarity (fuzzy match at a configurable threshold).
"""
import logging
from typing import Optional

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

FUZZY_THRESHOLD = 90  # percent similarity required to consider titles duplicates


def deduplicate(articles: list[dict], existing_urls: set[str],
                existing_titles: list[str]) -> list[dict]:
    """
    Filter a list of scraped article dicts against:
      - existing_urls: set of URLs already in the DB
      - existing_titles: list of titles already in the DB (for fuzzy match)

    Returns a list of articles that are not duplicates.
    """
    seen_urls_in_batch: set[str] = set()
    seen_titles_in_batch: list[str] = []
    unique: list[dict] = []

    for article in articles:
        url = article.get("url", "")
        title = article.get("title", "")

        # Exact URL dedup
        if url in existing_urls or url in seen_urls_in_batch:
            logger.debug("Duplicate URL skipped: %s", url)
            continue

        # Fuzzy title dedup against existing DB titles
        if _is_title_duplicate(title, existing_titles):
            logger.debug("Fuzzy duplicate title skipped: %s", title)
            continue

        # Fuzzy title dedup within current batch
        if _is_title_duplicate(title, seen_titles_in_batch):
            logger.debug("Fuzzy duplicate title (batch) skipped: %s", title)
            continue

        unique.append(article)
        seen_urls_in_batch.add(url)
        seen_titles_in_batch.append(title)

    logger.info("Dedup result: %d unique out of %d total", len(unique), len(articles))
    return unique


def _is_title_duplicate(title: str, existing_titles: list[str]) -> bool:
    """Return True if title is sufficiently similar to any existing title."""
    if not title:
        return False
    for existing in existing_titles:
        score = fuzz.ratio(title.lower(), existing.lower())
        if score >= FUZZY_THRESHOLD:
            return True
    return False
