from __future__ import annotations
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID
import uuid
from sqlalchemy import ForeignKey, UniqueConstraint, CheckConstraint, Index, DateTime, ForeignKeyConstraint, Integer, Numeric, String, Text, text
from datetime import datetime

MATCH_KINDS = "'MATCH','ASK','EXTRA','MISSING'"

def _uuid_pk():
  return mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

def _org():
  return mapped_column(PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

def _json(default: str = "'{}'::jsonb"):
  return mapped_column(JSONB, nullable=False, default=dict if default == "'{}'::jsonb" else list, server_default=text(default))

class RebarBbsDecision(Base, TimestampMixin):
  __tablename__ = "rebar_bbs_decisions"

  __table_args__ = (
    UniqueConstraint("organization_id", "project_id", "key", name="uq_rebar_bbs_decisions_project_key"),
    Index("ix_rebar_bbs_decisions_org_project", "organization_id", "project_id"),
  )

  id: Mapped[UUID] = _uuid_pk()
  organization_id: Mapped[UUID] = _org()
  
  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  key: Mapped[str] = mapped_column(String(40), nullable=False)
  value: Mapped[dict] = _json()
  
  decided_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"), 
    nullable=True,
  )
  
  decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class RebarBbsMatchRun(Base, TimestampMixin):
  __tablename__ = "rebar_bbs_match_runs"

  __table_args__ = (
    UniqueConstraint("id", "organization_id", name="uq_rebar_bbs_match_runs_id_org"),
    ForeignKeyConstraint(["document_id", "organization_id"], ["rebar_bbs_documents.id", "rebar_bbs_documents.organization_id"], ondelete="CASCADE", name="fk_rebar_bbs_match_runs_document_tenant"),
    Index("ix_rebar_bbs_match_runs_document", "document_id", "created_at"),
  )

  id: Mapped[UUID] = _uuid_pk()
  organization_id: Mapped[UUID] = _org()
  document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  floor_map: Mapped[dict] = _json()
  floor_map_proposed: Mapped[dict] = _json()
  floor_map_confirmed: Mapped[bool] = mapped_column(nullable=False, default=False, server_default=text("false"))
  member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
  stats: Mapped[dict] = _json()
  
  created_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )

class RebarBbsMatch(Base, TimestampMixin):
  __tablename__ = "rebar_bbs_matches"

  __table_args__ = (
    ForeignKeyConstraint(["run_id", "organization_id"], ["rebar_bbs_match_runs.id", "rebar_bbs_match_runs.organization_id"], ondelete="CASCADE", name="fk_rebar_bbs_matches_run_tenant"),
    CheckConstraint(f"kind IN ({MATCH_KINDS})", name="ck_rebar_bbs_matches_kind"),
    Index("ix_rebar_bbs_matches_run_kind", "run_id", "kind"),
    Index("ix_rebar_bbs_matches_org_document", "organization_id", "document_id"),
  )

  id: Mapped[UUID] = _uuid_pk()
  organization_id: Mapped[UUID] = _org()
  run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  row_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
  kind: Mapped[str] = mapped_column(String(8), nullable=False)
  family: Mapped[str | None] = mapped_column(String(12), nullable=True)
  sheet_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
  member: Mapped[str | None] = mapped_column(String(300), nullable=True)
  floors: Mapped[list] = _json("'[]'::jsonb")
  method: Mapped[str | None] = mapped_column(String(16), nullable=True)
  confidence: Mapped[object] = mapped_column(Numeric(4, 3), nullable=False, default=0, server_default=text("0"))
  basis: Mapped[str | None] = mapped_column(String(20), nullable=True)
  reason: Mapped[str | None] = mapped_column(Text, nullable=True)
  elements: Mapped[list] = _json("'[]'::jsonb")
