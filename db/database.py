import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from db.models import Base

DB_PATH = os.environ.get("NEWSR0_DB_PATH", "db/newsR0.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """FastAPI dependency that yields a DB session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
