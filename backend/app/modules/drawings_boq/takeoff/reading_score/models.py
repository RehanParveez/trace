from __future__ import annotations
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy import UniqueConstraint, ForeignKeyConstraint, Index, CheckConstraint, Boolean, ForeignKey, Integer, Numeric, String, Text, text
from uuid import UUID
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from decimal import Decimal
import uuid

class ReadingLabel(Base, TimestampMixin):
  __tablename__ = "reading_labels"

  __table_args__ = (
    UniqueConstraint("drawing_id", "source", "source_ref", name="uq_reading_labels_source"),
    ForeignKeyConstraint(["sheet_id", "organization_id"], ["takeoff_sheets.id", "takeoff_sheets.organization_id"], ondelete="CASCADE", name="fk_reading_labels_sheet_tenant"),
    ForeignKeyConstraint(["drawing_id", "organization_id"], ["drawings.id", "drawings.organization_id"], ondelete="CASCADE", name="fk_reading_labels_drawing_tenant"),
    Index("ix_reading_labels_drawing_sheet", "drawing_id", "sheet_id"),
    Index("ix_reading_labels_org_project", "organization_id", "project_id"),
    CheckConstraint("polarity IN ('POSITIVE','NEGATIVE')", name="ck_reading_labels_polarity"),
    CheckConstraint("source IN ('REGISTER','IMPORT')", name="ck_reading_labels_source"),
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
  sheet_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  family: Mapped[str] = mapped_column(String(24), nullable=False)
  mark: Mapped[str | None] = mapped_column(String(60), nullable=True)
  
  polarity: Mapped[str] = mapped_column(
    String(8),
    nullable=False,
    default="POSITIVE",
    server_default="POSITIVE",
  )
  
  x_pt: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
  y_pt: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
  
  attrs: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )
  
  complete: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=False,
    server_default=text("false"),
  )
  
  source: Mapped[str] = mapped_column(String(10), nullable=False)
  source_ref: Mapped[str] = mapped_column(String(80), nullable=False)
  extract_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
  
  created_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL", name="fk_reading_labels_created_by"),
    nullable=True,
  )

class ReadingScore(Base, TimestampMixin):
  __tablename__ = "reading_scores"

  __table_args__ = (
    ForeignKeyConstraint(["drawing_id", "organization_id"], ["drawings.id", "drawings.organization_id"], ondelete="CASCADE", name="fk_reading_scores_drawing_tenant"),
    Index("ix_reading_scores_drawing_created", "drawing_id", "created_at"),
    Index("ix_reading_scores_org_project", "organization_id", "project_id"),
    CheckConstraint("mode IN ('DRY_RUN','STORED')", name="ck_reading_scores_mode"),
    CheckConstraint("status IN ('OK','REGRESSION','PARTIAL','NO_LABELS')", name="ck_reading_scores_status"),
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
  label_drawing_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
  extract_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
  analysis_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
  mode: Mapped[str] = mapped_column(String(10), nullable=False)
  status: Mapped[str] = mapped_column(String(10), nullable=False)
  rule_hash: Mapped[str] = mapped_column(String(40), nullable=False)
  labels_stamp: Mapped[str] = mapped_column(String(40), nullable=False)
  label_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
  overall_f1: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
  result: Mapped[dict] = mapped_column(JSONB, nullable=False)
  baseline: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
  note: Mapped[str | None] = mapped_column(Text, nullable=True)
  
  created_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL", name="fk_reading_scores_created_by"),
    nullable=True,
  )
