from __future__ import annotations
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy import UniqueConstraint, ForeignKey, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from uuid import UUID
import uuid

class ProjectExpectedBoq(Base, TimestampMixin):
  """The figures a QS holds for a project, kept as item families (see lab/expected.py), so a run can be checked against them without uploading the workbook again."""
  __tablename__ = "project_expected_boqs"

  __table_args__ = (
    UniqueConstraint("project_id", "name", name="uq_project_expected_boqs_name"),
    Index("ix_project_expected_boqs_org_project", "organization_id", "project_id"),
  )

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True), 
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
    index=True
  )
  
  project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
  name: Mapped[str] = mapped_column(String(160), nullable=False)
  source: Mapped[str | None] = mapped_column(String(255), nullable=True)
  lines: Mapped[list] = mapped_column(JSONB, nullable=False)
  tolerances: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
  default_tolerance_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
  
  updated_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL", 
    name="fk_project_expected_boqs_updated_by"),
    nullable=True
  )
