"""
GET /api/articles — filtered article listing.
POST /api/refresh — trigger an immediate scraper run.
GET /api/runs/{run_id} — run status.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Article, ScraperRun

router = APIRouter()
logger = logging.getLogger(__name__)

# Articles older than 7 days are archived by default
ARCHIVE_DAYS = 7


@router.get("/articles")
def list_articles(
    q: Optional[str] = Query(None, description="Keyword search in title and excerpt"),
    sector: Optional[str] = Query(None, description="Comma-separated sector names"),
    sub_sector: Optional[str] = Query(None, description="Comma-separated sub-sector names"),
    source: Optional[str] = Query(None, description="Comma-separated source names"),
    from_date: Optional[datetime] = Query(None, description="ISO8601 start date"),
    to_date: Optional[datetime] = Query(None, description="ISO8601 end date"),
    include_archived: bool = Query(False, description="Include archived articles"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Article)

    if not include_archived:
        query = query.filter(Article.is_archived == 0)

    if q:
        like = f"%{q}%"
        query = query.filter(
            Article.title.ilike(like) | Article.excerpt.ilike(like)
        )

    if sector:
        sectors = [s.strip() for s in sector.split(",")]
        query = query.filter(Article.sector.in_(sectors))

    if sub_sector:
        # sub_sectors is stored as a JSON array; use LIKE for simple matching
        for ss in sub_sector.split(","):
            query = query.filter(Article.sub_sectors.like(f'%"{ss.strip()}"%'))

    if source:
        sources = [s.strip() for s in source.split(",")]
        query = query.filter(Article.source.in_(sources))

    if from_date:
        query = query.filter(Article.published_at >= from_date)

    if to_date:
        query = query.filter(Article.published_at <= to_date)

    total = query.count()
    articles = (
        query.order_by(Article.published_at.desc().nullslast())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "articles": [a.to_dict() for a in articles],
        "total": total,
        "filters_applied": {
            "q": q,
            "sector": sector,
            "sub_sector": sub_sector,
            "source": source,
            "from_date": from_date.isoformat() if from_date else None,
            "to_date": to_date.isoformat() if to_date else None,
        },
    }


@router.post("/refresh")
def trigger_refresh(db: Session = Depends(get_db)):
    """Trigger an immediate background scraper run."""
    import threading
    from scraper.engine import run_scraper

    placeholder_run = ScraperRun(
        source="all",
        status="started",
        run_at=datetime.now(timezone.utc),
    )
    db.add(placeholder_run)
    db.commit()
    db.refresh(placeholder_run)
    run_id = placeholder_run.id

    def _run():
        try:
            run_scraper()
        except Exception as exc:
            logger.error("Background scraper run failed: %s", exc, exc_info=True)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {"status": "started", "run_id": run_id}


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(ScraperRun).filter(ScraperRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run.to_dict()
