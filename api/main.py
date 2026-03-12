"""
newsR0 FastAPI application entrypoint.

Run with:
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes.articles import router as articles_router
from api.routes.sectors import router as sectors_router
from db.database import init_db
from db.models import Article

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/scraper.log"),
    ],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database on startup and archive old articles."""
    init_db()
    _archive_old_articles()
    yield


def _archive_old_articles():
    """Mark articles older than 7 days as archived."""
    from db.database import SessionLocal
    from datetime import timedelta

    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        updated = (
            db.query(Article)
            .filter(Article.published_at < cutoff, Article.is_archived == 0)
            .update({"is_archived": 1})
        )
        db.commit()
        if updated:
            logger.info("Archived %d old articles", updated)
    finally:
        db.close()


app = FastAPI(
    title="newsR0",
    description="Intelligent News Aggregator & Web Scraper API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles_router, prefix="/api")
app.include_router(sectors_router, prefix="/api")

# Serve the frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
