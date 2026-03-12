"""
Scraper engine — orchestrates all configured sources, tags articles,
deduplicates, and persists results to the database.
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import yaml

from db.database import SessionLocal, init_db
from db.models import Article, ScraperRun
from scraper.deduplicator import deduplicate
from scraper.html_parser import scrape_dynamic, scrape_static
from scraper.rss_parser import parse_feed
from scraper.tagger import tag_article

logger = logging.getLogger(__name__)

SOURCES_PATH = os.environ.get("NEWSR0_SOURCES_PATH", "config/sources.yaml")


def _load_sources() -> list[dict]:
    with open(SOURCES_PATH, "r") as f:
        data = yaml.safe_load(f)
    return [s for s in data.get("sources", []) if s.get("enabled", True)]


def _fetch_articles(source: dict) -> list[dict]:
    """Dispatch to the correct parser based on source type."""
    source_type = source.get("type", "rss").lower()
    if source_type == "rss":
        return parse_feed(source)
    elif source_type == "html":
        # Use dynamic (Playwright) only when explicitly flagged; default to static
        if source.get("dynamic", False):
            return scrape_dynamic(source)
        return scrape_static(source)
    else:
        raise ValueError(f"Unknown source type: {source_type}")


def run_scraper(source_filter: Optional[list[str]] = None) -> list[int]:
    """
    Run the full scraper cycle.

    Args:
        source_filter: optional list of source names to run; if None, run all.

    Returns:
        list of ScraperRun IDs created during this cycle.
    """
    init_db()
    sources = _load_sources()
    if source_filter:
        sources = [s for s in sources if s["name"] in source_filter]

    db = SessionLocal()
    run_ids: list[int] = []

    # Pre-load existing URLs and titles for dedup
    existing_urls: set[str] = {row[0] for row in db.query(Article.url).all()}
    existing_titles: list[str] = [row[0] for row in db.query(Article.title).all()]

    try:
        for source in sources:
            name = source["name"]
            run = ScraperRun(source=name, run_at=datetime.now(timezone.utc))
            db.add(run)
            db.flush()

            try:
                raw_articles = _fetch_articles(source)
                unique_articles = deduplicate(raw_articles, existing_urls, existing_titles)

                saved_count = 0
                for art in unique_articles:
                    sector, sub_sectors = tag_article(
                        art["title"],
                        art.get("excerpt", ""),
                        default_sector=source.get("default_sector"),
                        default_sub_sector=source.get("default_sub_sector"),
                    )
                    db_article = Article(
                        title=art["title"],
                        url=art["url"],
                        source=art["source"],
                        excerpt=art.get("excerpt", ""),
                        sector=sector,
                        sub_sectors=json.dumps(sub_sectors),
                        published_at=art.get("published_at"),
                        scraped_at=datetime.now(timezone.utc),
                    )
                    db.add(db_article)
                    existing_urls.add(art["url"])
                    existing_titles.append(art["title"])
                    saved_count += 1

                run.status = "success"
                run.articles_found = saved_count
                logger.info("Source %s: saved %d new articles", name, saved_count)

            except PermissionError as exc:
                run.status = "failed"
                run.error_msg = str(exc)
                logger.error("robots.txt blocked %s: %s", name, exc)

            except Exception as exc:
                run.status = "failed"
                run.error_msg = str(exc)
                logger.error("Scraper failed for %s: %s", name, exc, exc_info=True)

            db.commit()
            run_ids.append(run.id)

    finally:
        db.close()

    logger.info("Scraper cycle complete. Runs: %s", run_ids)
    return run_ids
