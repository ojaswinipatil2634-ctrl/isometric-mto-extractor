"""
ORM model for a persisted MTO extraction run (Phase 8).

One row per `/mto` request: the OCR title-block fields, graph topology
summary, and business-rules output (hardware + violations) are stored
together so `/mto/history` and `/mto/{id}` can serve them back without
re-running any of the vision/graph pipelines. Nested structures
(hardware line items, violations, NPS values, warnings) are stored as
JSON columns rather than normalized into separate tables - simpler for
this build's scope, and SQLite's JSON support (via SQLAlchemy's JSON
type, stored as TEXT) handles this fine at this scale.
"""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MTOExtractionRun(Base):
    __tablename__ = "mto_extraction_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # OCR title-block fields (Phase 3) - all best-effort, any may be None.
    drawing_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    revision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    line_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    service: Mapped[str | None] = mapped_column(String(128), nullable=True)
    material_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nps_values: Mapped[list] = mapped_column(JSON, default=list)

    # Graph topology summary (Phase 6).
    node_count: Mapped[int] = mapped_column(Integer, default=0)
    edge_count: Mapped[int] = mapped_column(Integer, default=0)
    branch_count: Mapped[int] = mapped_column(Integer, default=0)
    dead_end_count: Mapped[int] = mapped_column(Integer, default=0)
    loop_count: Mapped[int] = mapped_column(Integer, default=0)
    is_fully_connected: Mapped[bool] = mapped_column(Boolean, default=True)

    # Business rules output (Phase 7).
    hardware: Mapped[list] = mapped_column(JSON, default=list)
    violations: Mapped[list] = mapped_column(JSON, default=list)
    duplicate_fitting_count: Mapped[int] = mapped_column(Integer, default=0)

    # Actual MTO line items (PIPE/FITTING/FLANGE/VALVE/GASKET/BOLT) from
    # the vision extraction pipeline - see app/services/vision_extraction/.
    # This is the primary MTO deliverable; `hardware` above is the older,
    # detection-dependent gasket/bolt/nut-only output kept for backward
    # compatibility with the Phase 6/7 connectivity-rule checks.
    items: Mapped[list] = mapped_column(JSON, default=list)
    mto_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    extraction_source: Mapped[str] = mapped_column(String(16), default="mock")
    used_mock: Mapped[bool] = mapped_column(Boolean, default=True)

    # Symbol detection availability (informational only - see
    # app/services/mto/pipeline.py). Graph/business-rules already degrade
    # on their own when this is False; this is stored purely so history
    # and exports can show whether YOLO contributed to a given run.
    symbol_detection_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    symbol_detection_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)

    warnings: Mapped[list] = mapped_column(JSON, default=list)
    processing_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
