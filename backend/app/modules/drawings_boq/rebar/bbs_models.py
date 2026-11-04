from __future__ import annotations
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy import ForeignKey, CheckConstraint, DateTime, ForeignKeyConstraint, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from uuid import UUID
from datetime import datetime

BBS_STATUSES = "'ACTIVE','SUPERSEDED'"
FINDING_STATUSES = "'OPEN','ACCEPTED','REJECTED','SIGNED'"
FINDING_CLASSES = "'ERROR','METHOD','ROUNDING','CONFLICT','MISSING','EXTRA','UNVERIFIABLE','NAMING','CHECK','INFO'"

def _uuid_pk():
  return mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

def _org():
  return mapped_column(PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

def _json(default: str = "'{}'::jsonb"):
  return mapped_column(JSONB, nullable=False, default=dict if default == "'{}'::jsonb" else list, server_default=text(default))

class RebarBbsDocument(Base, TimestampMixin):
  __tablename__ = "rebar_bbs_documents"

  __table_args__ = (
    UniqueConstraint("id", "organization_id", name="uq_rebar_bbs_documents_id_org"),
    UniqueConstraint("project_id", "sha256", name="uq_rebar_bbs_documents_project_sha"),
    UniqueConstraint("project_id", "version", name="uq_rebar_bbs_documents_project_version"),
    Index("ix_rebar_bbs_documents_org_project", "organization_id", "project_id"),
    CheckConstraint(f"status IN ({BBS_STATUSES})", name="ck_rebar_bbs_documents_status"),
    CheckConstraint("version >= 1", name="ck_rebar_bbs_documents_version"),
  )

  id: Mapped[UUID] = _uuid_pk()
  organization_id: Mapped[UUID] = _org()
  
  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  drawing_set_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
  file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
  sha256: Mapped[str] = mapped_column(String(64), nullable=False)
  storage_key: Mapped[str | None] = mapped_column(String(700), nullable=True)
  status: Mapped[str] = mapped_column(String(12), nullable=False, default="ACTIVE", server_default="ACTIVE")
  version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
  title: Mapped[str | None] = mapped_column(String(300), nullable=True)
  pages: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
  profile: Mapped[str] = mapped_column(String(40), nullable=False)
  summary: Mapped[dict] = _json()
  page_counters: Mapped[list] = _json("'[]'::jsonb")
  unread_lines: Mapped[list] = _json("'[]'::jsonb")
  dropped_repeats: Mapped[list] = _json("'[]'::jsonb")
  
  created_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True), 
    ForeignKey("users.id", ondelete="SET NULL"), 
    nullable=True,
  )

class RebarBbsSheet(Base, TimestampMixin):
  __tablename__ = "rebar_bbs_sheets"

  __table_args__ = (
    ForeignKeyConstraint(["document_id", "organization_id"], ["rebar_bbs_documents.id", "rebar_bbs_documents.organization_id"], ondelete="CASCADE", name="fk_rebar_bbs_sheets_document_tenant"),
    UniqueConstraint("id", "organization_id", name="uq_rebar_bbs_sheets_id_org"),
    UniqueConstraint("document_id", "idx", name="uq_rebar_bbs_sheets_document_idx"),
    Index("ix_rebar_bbs_sheets_document", "document_id"),
  )

  id: Mapped[UUID] = _uuid_pk()
  organization_id: Mapped[UUID] = _org()
  document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  idx: Mapped[int] = mapped_column(Integer, nullable=False)
  name: Mapped[str] = mapped_column(String(300), nullable=False)
  first_page: Mapped[int] = mapped_column(Integer, nullable=False)
  last_page: Mapped[int] = mapped_column(Integer, nullable=False)
  printed_total_kg: Mapped[object | None] = mapped_column(Numeric(14, 3), nullable=True)
  dia_totals: Mapped[dict] = _json()

class RebarBbsRow(Base, TimestampMixin):
  __tablename__ = "rebar_bbs_rows"

  __table_args__ = (
    ForeignKeyConstraint(["document_id", "organization_id"], ["rebar_bbs_documents.id", "rebar_bbs_documents.organization_id"], ondelete="CASCADE", name="fk_rebar_bbs_rows_document_tenant"),
    ForeignKeyConstraint(["sheet_id", "organization_id"], ["rebar_bbs_sheets.id", "rebar_bbs_sheets.organization_id"], ondelete="CASCADE", name="fk_rebar_bbs_rows_sheet_tenant"),
    UniqueConstraint("document_id", "row_no", name="uq_rebar_bbs_rows_document_row"),
    Index("ix_rebar_bbs_rows_document_sheet", "document_id", "sheet_id"),
  )

  id: Mapped[UUID] = _uuid_pk()
  organization_id: Mapped[UUID] = _org()
  document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  sheet_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  row_no: Mapped[int] = mapped_column(Integer, nullable=False)
  page: Mapped[int] = mapped_column(Integer, nullable=False)
  y: Mapped[object | None] = mapped_column(Numeric(8, 1), nullable=True)
  member: Mapped[str | None] = mapped_column(String(300), nullable=True)
  sr: Mapped[int | None] = mapped_column(Integer, nullable=True)
  
  description: Mapped[str] = mapped_column(
    String(300),
    nullable=False, 
    default="",
    server_default="",
  )
  
  dia: Mapped[int | None] = mapped_column(Integer, nullable=True)
  spacing_in: Mapped[object | None] = mapped_column(Numeric(8, 3), nullable=True)
  members: Mapped[object | None] = mapped_column(Numeric(12, 3), nullable=True)
  each: Mapped[object | None] = mapped_column(Numeric(12, 3), nullable=True)
  total: Mapped[object | None] = mapped_column(Numeric(12, 3), nullable=True)
  cut_ft: Mapped[object | None] = mapped_column(Numeric(12, 3), nullable=True)
  total_ft: Mapped[object | None] = mapped_column(Numeric(14, 3), nullable=True)
  unit_kg_ft: Mapped[object | None] = mapped_column(Numeric(10, 4), nullable=True)
  total_kg: Mapped[object | None] = mapped_column(Numeric(14, 3), nullable=True)
  parts: Mapped[list] = _json("'[]'::jsonb")
  notes: Mapped[list] = _json("'[]'::jsonb")
  issues: Mapped[list] = _json("'[]'::jsonb")

class RebarAuditRun(Base, TimestampMixin):
  __tablename__ = "rebar_audit_runs"

  __table_args__ = (
    ForeignKeyConstraint(["document_id", "organization_id"], ["rebar_bbs_documents.id", "rebar_bbs_documents.organization_id"], ondelete="CASCADE", name="fk_rebar_audit_runs_document_tenant"),
    UniqueConstraint("id", "organization_id", name="uq_rebar_audit_runs_id_org"),
    Index("ix_rebar_audit_runs_document", "document_id", "created_at"),
  )

  id: Mapped[UUID] = _uuid_pk()
  organization_id: Mapped[UUID] = _org()
  document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  level: Mapped[str] = mapped_column(String(4), nullable=False, default="L1", server_default="L1")
  engine_digest: Mapped[str] = mapped_column(String(64), nullable=False)
  rules_digest: Mapped[str] = mapped_column(String(64), nullable=False)
  decisions_digest: Mapped[str] = mapped_column(String(64), nullable=False)
  previous_document_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
  totals: Mapped[dict] = _json()
  diff: Mapped[dict] = _json()
  
  created_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True), 
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )

class RebarAuditFinding(Base, TimestampMixin):
  __tablename__ = "rebar_audit_findings"

  __table_args__ = (
    ForeignKeyConstraint(["run_id", "organization_id"], ["rebar_audit_runs.id", "rebar_audit_runs.organization_id"], ondelete="CASCADE", name="fk_rebar_audit_findings_run_tenant"),
    Index("ix_rebar_audit_findings_run_class", "run_id", "finding_class"),
    Index("ix_rebar_audit_findings_org_document", "organization_id", "document_id"),
    CheckConstraint(f"status IN ({FINDING_STATUSES})", name="ck_rebar_audit_findings_status"),
    CheckConstraint(f"finding_class IN ({FINDING_CLASSES})", name="ck_rebar_audit_findings_class"),
  )

  id: Mapped[UUID] = _uuid_pk()
  organization_id: Mapped[UUID] = _org()
  run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  code: Mapped[str] = mapped_column(String(40), nullable=False)
  finding_class: Mapped[str] = mapped_column(String(14), nullable=False)
  rule: Mapped[str] = mapped_column(String(300), nullable=False)
  finding_key: Mapped[str] = mapped_column(String(600), nullable=False)
  bbs_ref: Mapped[dict] = _json()
  drawing_ref: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
  effect_basis: Mapped[str | None] = mapped_column(String(12), nullable=True)
  convention: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
  bbs_value: Mapped[str | None] = mapped_column(Text, nullable=True)
  trace_value: Mapped[str | None] = mapped_column(Text, nullable=True)
  diff_kg: Mapped[object | None] = mapped_column(Numeric(14, 3), nullable=True)
  diff_pct: Mapped[object | None] = mapped_column(Numeric(8, 3), nullable=True)
  
  confidence: Mapped[object] = mapped_column(
    Numeric(4, 3),
    nullable=False,
    default=1,
    server_default=text("1"),
  )
  
  question: Mapped[str | None] = mapped_column(Text, nullable=True)
  status: Mapped[str] = mapped_column(String(10), nullable=False, default="OPEN", server_default="OPEN")
  reason: Mapped[str | None] = mapped_column(Text, nullable=True)
  
  decided_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
  
  decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
