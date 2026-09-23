from __future__ import annotations
import enum
from sqlalchemy import Enum, Date, ForeignKey, Index, Numeric, String
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from decimal import Decimal
from datetime import date

class RetentionHolderType(str, enum.Enum):
  CLIENT = "CLIENT"      
  SUBCONTRACTOR = "SUBCONTRACTOR"  

class RetentionRelease(Base, TimestampMixin):
  __tablename__ = "retention_releases"

  __table_args__ = (Index("ix_retention_releases_org_project", "organization_id", "project_id"),)

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
  
  holder_type: Mapped[RetentionHolderType] = mapped_column(
    Enum(RetentionHolderType,
      name="retention_holder_type"),
      nullable=False,
    )
  
  boq_version_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("boq_versions.id", ondelete="RESTRICT"),
    nullable=True,
  )
  
  agreement_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("subcontract_agreements.id", ondelete="RESTRICT"),
    nullable=True,
  )
  
  amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
  release_date: Mapped[date] = mapped_column(Date, nullable=False)
  
  notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
  
  created_by_user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="RESTRICT"),
    nullable=False,
  )