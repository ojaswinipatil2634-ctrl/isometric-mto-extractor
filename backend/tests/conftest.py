import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mto_client():
    """
    A TestClient wired to a fresh in-memory SQLite database instead of
    the real `./data/app.db` - Phase 8 tests need isolated, repeatable
    state (e.g. asserting exact history counts) rather than accumulating
    rows in the developer's real database across test runs.

    StaticPool is required here: a plain `sqlite:///:memory:` engine
    hands out a brand new (and separately empty) in-memory database on
    every new connection, which breaks anything beyond a single query
    within one session. StaticPool keeps one underlying connection alive
    and shares it, so the schema and data created by one request are
    still there for the next.
    """
    from app.core.database import Base, get_db

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Import models so they're registered on Base.metadata before create_all.
    from app.models import mto_run  # noqa: F401

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)
