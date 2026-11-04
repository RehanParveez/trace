from __future__ import annotations
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy import ForeignKeyConstraint, Index, CheckConstraint, Boolean, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from uuid import UUID
import uuid
from datetime import datetime

OVERRIDE_STATUSES = "'ACTIVE','WITHDRAWN'"
MISREAD_KINDS = "'WRONG_VALUE','WRONG_CLASS','WRONG_POSITION','INVENTED','MISSED','OTHER'"
MISREAD_STATUSES = "'OPEN','QUEUED','RESOLVED','DISMISSED'"

class ReadingOverride(Base, TimestampMixin):
  __tablename__ = "reading_overrides"

  __table_args__ = (
    ForeignKeyConstraint(["sheet_id", "organization_id"], ["takeoff_sheets.id", "takeoff_sheets.organization_id"], ondelete="CASCADE", name="fk_reading_overrides_sheet_tenant"),
    ForeignKeyConstraint(["drawing_id", "organization_id"], ["drawings.id", "drawings.organization_id"], ondelete="CASCADE", name="fk_reading_overrides_drawing_tenant"),
    Index("ix_reading_overrides_drawing_sheet", "drawing_id", "sheet_id"),
    Index("ix_reading_overrides_org_project", "organization_id", "project_id"),
    CheckConstraint(f"status IN ({OVERRIDE_STATUSES})", name="ck_reading_overrides_status"),
  )

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
  drawing_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  sheet_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  item_class: Mapped[str] = mapped_column(String(32), nullable=False)
  mark: Mapped[str | None] = mapped_column(String(60), nullable=True)
  geometry: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
  attrs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
  note: Mapped[str | None] = mapped_column(Text, nullable=True)
  status: Mapped[str] = mapped_column(String(10), nullable=False, default="ACTIVE", server_default="ACTIVE")
  image_checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
  
  checked_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
  
  checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  
  created_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )

class ReadingMisreadReport(Base, TimestampMixin):
  __tablename__ = "reading_misread_reports"

  __table_args__ = (
    ForeignKeyConstraint(["sheet_id", "organization_id"], ["takeoff_sheets.id", "takeoff_sheets.organization_id"], ondelete="CASCADE", name="fk_reading_misreads_sheet_tenant"),
    ForeignKeyConstraint(["drawing_id", "organization_id"], ["drawings.id", "drawings.organization_id"], ondelete="CASCADE", name="fk_reading_misreads_drawing_tenant"),
    Index("ix_reading_misreads_drawing_sheet", "drawing_id", "sheet_id"),
    Index("ix_reading_misreads_org_status", "organization_id", "status"),
    CheckConstraint(f"kind IN ({MISREAD_KINDS})", name="ck_reading_misreads_kind"),
    CheckConstraint(f"status IN ({MISREAD_STATUSES})", name="ck_reading_misreads_status"),
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
  candidate_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
  ckey: Mapped[str | None] = mapped_column(String(40), nullable=True)
  item_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
  mark: Mapped[str | None] = mapped_column(String(60), nullable=True)
  kind: Mapped[str] = mapped_column(String(16), nullable=False)
  box: Mapped[list | None] = mapped_column(JSONB, nullable=True)
  expected: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
  read_as: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
  note: Mapped[str | None] = mapped_column(Text, nullable=True)
  extract_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
  status: Mapped[str] = mapped_column(String(10), nullable=False, default="OPEN", server_default="OPEN")
  
  reported_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
