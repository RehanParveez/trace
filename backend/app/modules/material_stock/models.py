from __future__ import annotations
import enum
from sqlalchemy import Enum, Date, ForeignKey, Index, Numeric, String
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from decimal import Decimal
import uuid
from datetime import date

class MaterialIssueType(str, enum.Enum):
  ISSUED = "ISSUED"
  WASTAGE = "WASTAGE"

class MaterialIssue(Base, TimestampMixin):
  __tablename__ = "material_issues"

  __table_args__ = (Index("ix_material_issues_org_project", "organization_id", "project_id"),)

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
  
  material_name: Mapped[str] = mapped_column(String(200), nullable=False)
  unit: Mapped[str] = mapped_column(String(50), nullable=False)
  quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
  
  issue_type: Mapped[MaterialIssueType] = mapped_column(
    Enum(MaterialIssueType,
    name="material_issue_type"),
    nullable=False,
  )
  
  issued_to: Mapped[str | None] = mapped_column(String(200), nullable=True)
  issue_date: Mapped[date] = mapped_column(Date, nullable=False)
  notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
  
  recorded_by_user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="RESTRICT"),
    nullable=False,
  )