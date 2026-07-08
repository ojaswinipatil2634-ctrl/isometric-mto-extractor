"""
SQLite persistence setup (Phase 8).

Uses SQLAlchemy's synchronous engine/session. FastAPI's request handlers
are already async, but the actual DB work here is fast, local SQLite
reads/writes - a sync session per request (via `get_db` as a FastAPI
dependency) is simpler than wiring an async driver for no real benefit
at this scale, and matches SQLite's own single-writer nature.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# SQLite connections are not thread-safe by default; FastAPI can serve
# a worker's requests across different threads, so this must be off.
_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

# Ensure the directory for a sqlite:///./data/app.db-style URL exists
# before SQLAlchemy tries to open it.
if settings.DATABASE_URL.startswith("sqlite:///"):
    db_path = settings.DATABASE_URL.replace("sqlite:///", "", 1)
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """
    Create all tables if they don't exist yet. Safe to call on every
    startup - this is CREATE TABLE IF NOT EXISTS semantics under the
    hood, not a destructive migration.
    """
    from app.models import mto_run  # noqa: F401 - registers the model on Base.metadata

    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency yielding a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
