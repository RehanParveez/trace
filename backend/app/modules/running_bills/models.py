from __future__ import annotations
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.shared.mixins import TimestampMixin

class RunningBillStatus(str, enum.Enum):
  DRAFT = "DRAFT"
  ISSUED = "ISSUED"
  CANCELLED = "CANCELLED"

class RunningBill(Base, TimestampMixin):
  __tablename__ = "running_bills"

  __table_args__ = (
    UniqueConstraint("organization_id", "project_id", "bill_number", name="uq_running_bill_number"),
    Index("ix_running_bills_org_project", "organization_id", "project_id"),
  )

  id: Mapped[UUID] = mapped_column(
      PGUUID(as_uuid=True),
      primary_key=True,
      default=uuid.uuid4
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
  
  boq_version_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("boq_versions.id", ondelete="RESTRICT"),
    nullable=False,
  )
  
  bill_number: Mapped[int] = mapped_column(Integer, nullable=False)

  status: Mapped[RunningBillStatus] = mapped_column(
    Enum(RunningBillStatus, name="running_bill_status"),
    nullable=False,
    default=RunningBillStatus.DRAFT,
  )

  period_start: Mapped[date] = mapped_column(Date, nullable=False)
  period_end: Mapped[date] = mapped_column(Date, nullable=False)

  gross_value_this_period: Mapped[Decimal] = mapped_column(
    Numeric(18, 2),
    nullable=False, default=Decimal("0"),
  )
  
  gross_value_cumulative: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))

  retention_percentage: Mapped[Decimal] = mapped_column(
    Numeric(5, 2),
    nullable=False, default=Decimal("10"),
  )
  
  retention_cap_percentage: Mapped[Decimal | None] = mapped_column(
    Numeric(5, 2),
    nullable=True,
  )
  
  retention_this_period: Mapped[Decimal] = mapped_column(
    Numeric(18, 2),
    nullable=False, default=Decimal("0"),
  )
  
  retention_cumulative: Mapped[Decimal] = mapped_column(
    Numeric(18, 2),
    nullable=False, default=Decimal("0"),
  )
  
  advance_recovery_amount: Mapped[Decimal] = mapped_column(
    Numeric(18, 2),
    nullable=False, default=Decimal("0")
  )
  
  other_deductions_amount: Mapped[Decimal] = mapped_column(
    Numeric(18, 2),
    nullable=False, default=Decimal("0"),
  )
  
  other_deductions_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

  net_payable: Mapped[Decimal] = mapped_column(
    Numeric(18, 2),
    nullable=False, default=Decimal("0"),
  )
  
  sales_tax_authority: Mapped[str | None] = mapped_column(String(10), nullable=True)
  sales_tax_rate_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
  sales_tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
  
  currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PKR")

  notes: Mapped[str | None] = mapped_column(Text, nullable=True)

  created_by_user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="RESTRICT"),
    nullable=False,
  )
  
  issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

  version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

  line_items: Mapped[list["RunningBillLineItem"]] = relationship(
    "RunningBillLineItem",
    back_populates="bill",
    cascade="all, delete-orphan",
    order_by="RunningBillLineItem.sort_order",
  )

class RunningBillLineItem(Base):
  __tablename__ = "running_bill_line_items"

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  bill_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("running_bills.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  boq_item_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("boq_items.id", ondelete="RESTRICT"),
    nullable=False,
  )

  sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

  material_name: Mapped[str] = mapped_column(String(300), nullable=False)
  unit: Mapped[str] = mapped_column(String(50), nullable=False)
  contract_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
  unit_rate: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

  previous_percentage: Mapped[Decimal] = mapped_column(
    Numeric(5, 2), nullable=False, default=Decimal("0"),
  )
  
  cumulative_percentage: Mapped[Decimal] = mapped_column(
    Numeric(5, 2),
    nullable=False, default=Decimal("0"),
  )

  previous_quantity: Mapped[Decimal] = mapped_column(
    Numeric(18, 3),
    nullable=False, default=Decimal("0"),
  )
  
  cumulative_quantity: Mapped[Decimal] = mapped_column(
    Numeric(18, 3),
    nullable=False, default=Decimal("0"),
  )
  
  this_period_quantity: Mapped[Decimal] = mapped_column(
    Numeric(18, 3),
    nullable=False, default=Decimal("0"),
  )

  previous_value: Mapped[Decimal] = mapped_column(
    Numeric(18, 2),
    nullable=False, default=Decimal("0"),
  )
  
  cumulative_value: Mapped[Decimal] = mapped_column(
    Numeric(18, 2),
    nullable=False, default=Decimal("0"),
  )
  
  this_period_value: Mapped[Decimal] = mapped_column(
    Numeric(18, 2),
    nullable=False,
    default=Decimal("0")
  )

  bill: Mapped["RunningBill"] = relationship("RunningBill", back_populates="line_items")