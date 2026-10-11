from __future__ import annotations
import enum
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy import CheckConstraint, DateTime, Index, Date, Enum, ForeignKey, Numeric, String, Text
from uuid import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from datetime import date, datetime
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
    nullable=False,
  )
  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  material_name: Mapped[str] = mapped_column(String(300), nullable=False)
  quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
  unit: Mapped[str] = mapped_column(String(50), nullable=False)
  
  estimated_amount: Mapped[Decimal | None] = mapped_column(
    Numeric(18, 2),
    nullable=True,
  )
  
  status: Mapped[ProcurementStatus] = mapped_column(
    Enum(ProcurementStatus, name="procurement_status"),
    nullable=False,
    default=ProcurementStatus.REQUESTED,
  )
  
  needed_by_date: Mapped[date | None] = mapped_column(Date, nullable=True)
  supplier_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
  notes: Mapped[str | None] = mapped_column(Text, nullable=True)
  
  requested_by: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
  
class ProcurementDelivery(Base, TimestampMixin):
  __tablename__ = "procurement_deliveries"
  
  __table_args__ = (
    CheckConstraint("quantity > 0", name="ck_procurement_delivery_quantity_positive"),
    CheckConstraint("amount IS NULL OR amount >= 0", name="ck_procurement_delivery_amount_non_negative"),
    Index("ix_procurement_deliveries_org_project", "organization_id", "project_id"),
    Index("ix_procurement_deliveries_request", "request_id"),
    Index("ix_procurement_deliveries_project_date", "project_id", "received_date"),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True, 
    default=uuid.uuid4,
  )
  
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
  request_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("procurement_requests.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  received_date: Mapped[date] = mapped_column(Date, nullable=False)
  quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
  supplier_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
  invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
  amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
  notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
  
  recorded_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
  
  voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  
  voided_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
  
  void_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)