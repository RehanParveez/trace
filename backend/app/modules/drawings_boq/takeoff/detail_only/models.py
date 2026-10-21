from __future__ import annotations
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy import UniqueConstraint, ForeignKeyConstraint, Index, CheckConstraint, ForeignKey, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
import uuid
from decimal import Decimal

class DetailMarkDecision(Base, TimestampMixin):
  __tablename__ = "detail_mark_decisions"

  __table_args__ = (
    UniqueConstraint("drawing_id", "kind", "mark", "sheet_id", "ckey", name="uq_detail_mark_decisions_key"),
    
    ForeignKeyConstraint(["drawing_id", "organization_id"], ["drawings.id", "drawings.organization_id"], ondelete="CASCADE", name="fk_detail_mark_decisions_drawing_tenant"),
    ForeignKeyConstraint(["sheet_id", "organization_id"], ["takeoff_sheets.id", "takeoff_sheets.organization_id"], ondelete="CASCADE", name="fk_detail_mark_decisions_sheet_tenant"),
    
    Index("ix_detail_mark_decisions_drawing", "drawing_id", "kind"),
    Index("ix_detail_mark_decisions_org_project", "organization_id", "project_id"),
    CheckConstraint("kind IN ('COLUMN_MARK','BEAM_DEPTH')", name="ck_detail_mark_decisions_kind"),
  )

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False
  )
  
  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  drawing_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  kind: Mapped[str] = mapped_column(String(12), nullable=False)
  mark: Mapped[str] = mapped_column(String(60), nullable=False)
  sheet_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
  ckey: Mapped[str | None] = mapped_column(String(40), nullable=True)
  value_mm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
  basis: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
  
  decided_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL", name="fk_detail_mark_decisions_decided_by"),
    nullable=True,
  )
