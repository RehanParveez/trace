from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from uuid import UUID
import uuid
from sqlalchemy import ForeignKey, ForeignKeyConstraint, Index, Integer, Numeric, String, UniqueConstraint, text
from app.core.database import Base
from app.shared.mixins import TimestampMixin

def _uuid_pk():
  return mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

def _org():
  return mapped_column(PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

def _json(default: str = "'{}'::jsonb"):
  return mapped_column(JSONB, nullable=False, default=dict if default == "'{}'::jsonb" else list, server_default=text(default))

class RebarBbsExpectRun(Base, TimestampMixin):
  __tablename__ = "rebar_bbs_expect_runs"

  __table_args__ = (
    UniqueConstraint("id", "organization_id", name="uq_rebar_bbs_expect_runs_id_org"),
    ForeignKeyConstraint(["document_id", "organization_id"], ["rebar_bbs_documents.id", "rebar_bbs_documents.organization_id"], ondelete="CASCADE", name="fk_rebar_bbs_expect_runs_document_tenant"),
    Index("ix_rebar_bbs_expect_runs_document", "document_id", "created_at"),
  )

  id: Mapped[UUID] = _uuid_pk()
  organization_id: Mapped[UUID] = _org()
  document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  decisions: Mapped[dict] = _json()
  decisions_digest: Mapped[str] = mapped_column(String(64), nullable=False)
  member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
  complete_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
  stats: Mapped[dict] = _json()
  
  created_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )

class RebarBbsExpectation(Base, TimestampMixin):
  __tablename__ = "rebar_bbs_expectations"

  __table_args__ = (
    ForeignKeyConstraint(["run_id", "organization_id"], ["rebar_bbs_expect_runs.id", "rebar_bbs_expect_runs.organization_id"], ondelete="CASCADE", name="fk_rebar_bbs_expectations_run_tenant"),
    Index("ix_rebar_bbs_expectations_run_class", "run_id", "member_class"),
    Index("ix_rebar_bbs_expectations_org_document", "organization_id", "document_id"),
  )

  id: Mapped[UUID] = _uuid_pk()
  organization_id: Mapped[UUID] = _org()
  run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  member_class: Mapped[str] = mapped_column(String(12), nullable=False)
  mark: Mapped[str] = mapped_column(String(60), nullable=False)
  floor: Mapped[str | None] = mapped_column(String(12), nullable=True)
  count: Mapped[object | None] = mapped_column(Numeric(14, 2), nullable=True)
  total_ft: Mapped[object | None] = mapped_column(Numeric(14, 2), nullable=True)
  kg: Mapped[object | None] = mapped_column(Numeric(14, 2), nullable=True)
  complete: Mapped[bool] = mapped_column(nullable=False, default=False, server_default=text("false"))
  plan_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
  source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
  decision_only: Mapped[bool] = mapped_column(nullable=False, default=False, server_default=text("false"))
  lines: Mapped[list] = _json("'[]'::jsonb")
  inputs: Mapped[list] = _json("'[]'::jsonb")
  blocked: Mapped[list] = _json("'[]'::jsonb")
  notes: Mapped[list] = _json("'[]'::jsonb")
