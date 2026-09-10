from __future__ import annotations
import enum
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy import Index, Date, Enum, ForeignKey, Numeric, String, Text
from uuid import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from datetime import date
from decimal import Decimal

class ProcurementStatus(str, enum.Enum):
  REQUESTED = "REQUESTED"
  APPROVED = "APPROVED"
  ORDERED = "ORDERED"
  RECEIVED = "RECEIVED"
  CANCELLED = "CANCELLED"

class ProcurementRequest(Base, TimestampMixin):
  __tablename__ = "procurement_requests"
  __table_args__ = (
    Index("ix_procurement_project", "project_id"),
    Index("ix_procurement_org", "organization_id"),
    Index("ix_procurement_status", "status"),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
  )
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False, index=True,
  )
  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="CASCADE"),
    nullable=False, index=True,
  )
  material_name: Mapped[str] = mapped_column(String(300), nullable=False)
  quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
  unit: Mapped[str] = mapped_column(String(50), nullable=False)
  estimated_amount: Mapped[Decimal | None] = mapped_column(
    Numeric(18, 2), nullable=True,
  )
  status: Mapped[ProcurementStatus] = mapped_column(
    Enum(ProcurementStatus, name="procurement_status"),
    nullable=False, default=ProcurementStatus.REQUESTED,
  )
  needed_by_date: Mapped[date | None] = mapped_column(Date, nullable=True)
  notes: Mapped[str | None] = mapped_column(Text, nullable=True)
  requested_by: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )