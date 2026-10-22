from __future__ import annotations
import uuid
from decimal import Decimal
from uuid import UUID
from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.shared.mixins import TimestampMixin

class ReadingSweep(Base, TimestampMixin):
  """One sweep of the reader's tuned constants over a labelled drawing, run by the sweep tool (scripts/tune_sweep.py) in its own process. The result keeps every
  score of every value tried, so the decision about each constant can be made again, under another policy, without reading anything."""
  __tablename__ = "reading_sweeps"

  __table_args__ = (
    ForeignKeyConstraint(["drawing_id", "organization_id"], ["drawings.id", "drawings.organization_id"], ondelete="CASCADE", name="fk_reading_sweeps_drawing_tenant"),
    Index("ix_reading_sweeps_drawing_created", "drawing_id", "created_at"),
    Index("ix_reading_sweeps_org_project", "organization_id", "project_id"),
    CheckConstraint("status IN ('COMPLETE','PARTIAL')", name="ck_reading_sweeps_status"),
  )

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True), 
    ForeignKey("organizations.id", ondelete="CASCADE"), 
    nullable=False,
  )
  
  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  drawing_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  extract_version: Mapped[int] = mapped_column(Integer, nullable=False)
  ladder: Mapped[str] = mapped_column(String(10), nullable=False)
  status: Mapped[str] = mapped_column(String(10), nullable=False)
  constants: Mapped[int] = mapped_column(Integer, nullable=False)
  cells: Mapped[int] = mapped_column(Integer, nullable=False)
  changes: Mapped[int] = mapped_column(Integer, nullable=False)
  label_count: Mapped[int] = mapped_column(Integer, nullable=False)
  labels_stamp: Mapped[str | None] = mapped_column(String(40), nullable=True)
  seconds: Mapped[Decimal] = mapped_column(Numeric(10, 1), nullable=False)
  result: Mapped[dict] = mapped_column(JSONB, nullable=False)
  decisions: Mapped[dict] = mapped_column(JSONB, nullable=False)
  note: Mapped[str | None] = mapped_column(Text, nullable=True)
  
  created_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL", name="fk_reading_sweeps_created_by"),
    nullable=True,
  )
