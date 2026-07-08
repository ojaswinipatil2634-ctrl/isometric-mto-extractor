import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.mto_run import MTOExtractionRun
from app.repositories.mto_run_repository import MTORunRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def _make_run(filename: str = "drawing.png") -> MTOExtractionRun:
    return MTOExtractionRun(filename=filename, hardware=[], violations=[], nps_values=[], warnings=[])


def test_create_assigns_an_id(db_session):
    repo = MTORunRepository(db_session)

    saved = repo.create(_make_run())

    assert saved.id is not None


def test_get_by_id_returns_saved_run(db_session):
    repo = MTORunRepository(db_session)
    saved = repo.create(_make_run("test.png"))

    fetched = repo.get_by_id(saved.id)

    assert fetched is not None
    assert fetched.filename == "test.png"


def test_get_by_id_returns_none_for_missing_run(db_session):
    repo = MTORunRepository(db_session)

    assert repo.get_by_id(9999) is None


def test_list_recent_orders_newest_first(db_session):
    repo = MTORunRepository(db_session)
    first = repo.create(_make_run("first.png"))
    second = repo.create(_make_run("second.png"))

    runs = repo.list_recent()

    assert [r.id for r in runs] == [second.id, first.id]


def test_list_recent_respects_limit_and_offset(db_session):
    repo = MTORunRepository(db_session)
    for i in range(5):
        repo.create(_make_run(f"file{i}.png"))

    page = repo.list_recent(limit=2, offset=1)

    assert len(page) == 2


def test_count_all(db_session):
    repo = MTORunRepository(db_session)
    assert repo.count_all() == 0

    repo.create(_make_run())
    repo.create(_make_run())

    assert repo.count_all() == 2
