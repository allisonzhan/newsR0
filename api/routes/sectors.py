"""
GET /api/sectors  — full sector/sub-sector taxonomy.
GET /api/sources  — list of configured sources with last-run status.
"""
import logging
import os

import yaml
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import ScraperRun

router = APIRouter()
logger = logging.getLogger(__name__)

SECTORS_PATH = os.environ.get("NEWSR0_SECTORS_PATH", "config/sectors.yaml")
SOURCES_PATH = os.environ.get("NEWSR0_SOURCES_PATH", "config/sources.yaml")


@router.get("/sectors")
def get_sectors():
    with open(SECTORS_PATH, "r") as f:
        data = yaml.safe_load(f)
    return data.get("sectors", [])


@router.get("/sources")
def get_sources(db: Session = Depends(get_db)):
    with open(SOURCES_PATH, "r") as f:
        data = yaml.safe_load(f)
    sources = data.get("sources", [])

    # Enrich each source with its latest run status
    result = []
    for source in sources:
        name = source["name"]
        latest_run = (
            db.query(ScraperRun)
            .filter(ScraperRun.source == name)
            .order_by(ScraperRun.run_at.desc())
            .first()
        )
        result.append(
            {
                "name": name,
                "url": source.get("url"),
                "type": source.get("type", "rss"),
                "default_sector": source.get("default_sector"),
                "enabled": source.get("enabled", True),
                "last_run_status": latest_run.status if latest_run else None,
                "last_run_at": latest_run.run_at.isoformat() if latest_run else None,
                "last_articles_found": latest_run.articles_found if latest_run else None,
            }
        )
    return result
