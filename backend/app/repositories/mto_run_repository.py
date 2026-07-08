"""
Repository for `MTOExtractionRun` persistence.

Per the project's separation-of-concerns rule, routes and services
never issue SQLAlchemy queries directly - all persistence access goes
through this repository.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.mto_run import MTOExtractionRun


class MTORunRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, run: MTOExtractionRun) -> MTOExtractionRun:
        self._db.add(run)
        self._db.commit()
        self._db.refresh(run)
        return run

    def get_by_id(self, run_id: int) -> MTOExtractionRun | None:
        return self._db.get(MTOExtractionRun, run_id)

    def list_recent(self, limit: int = 50, offset: int = 0) -> list[MTOExtractionRun]:
        stmt = (
            select(MTOExtractionRun)
            .order_by(MTOExtractionRun.created_at.desc(), MTOExtractionRun.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self._db.scalars(stmt).all())

    def count_all(self) -> int:
        stmt = select(func.count()).select_from(MTOExtractionRun)
        return self._db.scalar(stmt) or 0
