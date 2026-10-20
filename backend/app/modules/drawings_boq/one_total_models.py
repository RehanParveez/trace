from __future__ import annotations
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy import UniqueConstraint, CheckConstraint, Index, ForeignKey, String
from uuid import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid

class ProjectOneTotalRule(Base, TimestampMixin):
  __tablename__ = "project_one_total_rules"

  __table_args__ = (
    UniqueConstraint("project_id", "kind", "mark", "level_name", name="uq_project_one_total_rules_scope"),
    CheckConstraint("prefer IN ('DRAWING', 'MODEL', 'BOTH')", name="ck_project_one_total_rules_prefer"),
    Index("ix_project_one_total_rules_org_project", "organization_id", "project_id"),
  )

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
    index=True
  )
  
  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="CASCADE"),
    nullable=False
  )
  
  kind: Mapped[str] = mapped_column(String(16), nullable=False)
  mark: Mapped[str] = mapped_column(String(60), nullable=False, default="")
  level_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
  prefer: Mapped[str] = mapped_column(String(16), nullable=False)
  note: Mapped[str | None] = mapped_column(String(500), nullable=True)
  
  updated_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL",
    name="fk_project_one_total_rules_updated_by"),
    nullable=True,
  )
