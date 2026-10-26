from __future__ import annotations
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy import ForeignKeyConstraint, Index,  ForeignKey, CheckConstraint, Integer, String, Text, text
import uuid
from uuid import UUID
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

class AiShadowRead(Base, TimestampMixin):
  __tablename__ = "ai_shadow_reads"

  __table_args__ = (
    ForeignKeyConstraint(["sheet_id", "organization_id"], ["takeoff_sheets.id", "takeoff_sheets.organization_id"], ondelete="CASCADE", name="fk_ai_shadow_reads_sheet_tenant"),
    ForeignKeyConstraint(["drawing_id", "organization_id"], ["drawings.id", "drawings.organization_id"], ondelete="CASCADE", name="fk_ai_shadow_reads_drawing_tenant"),
    Index("ix_ai_shadow_reads_drawing_sheet", "drawing_id", "sheet_id", "created_at"),
    Index("ix_ai_shadow_reads_org_project", "organization_id", "project_id"),
    CheckConstraint("status IN ('OK','INVALID','FAILED')", name="ck_ai_shadow_reads_status"),
    CheckConstraint("mode IN ('WEAK','ALL')", name="ck_ai_shadow_reads_mode"),
  )

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
  project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
  drawing_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  sheet_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  page_no: Mapped[int] = mapped_column(Integer, nullable=False)
  purpose: Mapped[str] = mapped_column(String(40), nullable=False)
  mode: Mapped[str] = mapped_column(String(8), nullable=False)
  status: Mapped[str] = mapped_column(String(8), nullable=False)
  prompt_version: Mapped[str] = mapped_column(String(12), nullable=False)
  schema_version: Mapped[str] = mapped_column(String(12), nullable=False)
  crop_key: Mapped[str] = mapped_column(String(300), nullable=False)
  crop: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
  ai_request_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ai_requests.id", ondelete="SET NULL", name="fk_ai_shadow_reads_request"), nullable=True)
  rule_value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
  ai_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
  comparison: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
  totals: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
  problems: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
  error: Mapped[str | None] = mapped_column(Text, nullable=True)
  created_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL", name="fk_ai_shadow_reads_created_by"), nullable=True)
