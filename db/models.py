from sqlalchemy import (
    Column, Integer, Text, DateTime, Index
)
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    url = Column(Text, unique=True, nullable=False)
    source = Column(Text, nullable=False)
    excerpt = Column(Text)
    sector = Column(Text)
    sub_sectors = Column(Text)          # JSON array stored as string
    published_at = Column(DateTime)
    scraped_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_archived = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_sector", "sector"),
        Index("idx_published_at", "published_at"),
        Index("idx_source", "source"),
    )

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "excerpt": self.excerpt,
            "sector": self.sector,
            "sub_sectors": json.loads(self.sub_sectors) if self.sub_sectors else [],
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "is_archived": bool(self.is_archived),
        }


class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source = Column(Text)
    status = Column(Text)               # 'success' | 'failed'
    articles_found = Column(Integer, default=0)
    error_msg = Column(Text)

    def to_dict(self):
        return {
            "id": self.id,
            "run_at": self.run_at.isoformat() if self.run_at else None,
            "source": self.source,
            "status": self.status,
            "articles_found": self.articles_found,
            "error_msg": self.error_msg,
        }
