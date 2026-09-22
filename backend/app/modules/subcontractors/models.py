from __future__ import annotations
import enum
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint

class SubcontractAgreementStatus(str, enum.Enum):
  ACTIVE = "ACTIVE"
  COMPLETED = "COMPLETED"
  TERMINATED = "TERMINATED"

class SubcontractorBillStatus(str, enum.Enum):
  DRAFT = "DRAFT"
  ISSUED = "ISSUED"
  CANCELLED = "CANCELLED"

class Subcontractor(Base, TimestampMixin):
  __tablename__ = "subcontractors"

  __table_args__ = (Index("ix_subcontractors_org", "organization_id"),)

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
  
  name: Mapped[str] = mapped_column(String(200), nullable=False)
  trade_specialization: Mapped[str] = mapped_column(String(100), nullable=False)
  contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
  contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
  ntn_or_cnic: Mapped[str | None] = mapped_column(String(30), nullable=True)
  is_active_taxpayer: Mapped[bool] = mapped_column(nullable=False, default=False)
  is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
  notes: Mapped[str | None] = mapped_column(Text, nullable=True)

  agreements: Mapped[list["SubcontractAgreement"]] = relationship(
    "SubcontractAgreement",
    back_populates="subcontractor",
  )

class SubcontractAgreement(Base, TimestampMixin):
  __tablename__ = "subcontract_agreements"

  __table_args__ = (
    Index("ix_subcontract_agreements_org_project", "organization_id", "project_id"),
    Index("ix_subcontract_agreements_subcontractor", "subcontractor_id"),
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
  
  subcontractor_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("subcontractors.id", ondelete="RESTRICT"),
    nullable=False,
  )
  
  scope_description: Mapped[str] = mapped_column(Text, nullable=False)
  contract_value: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
  
  default_retention_percentage: Mapped[Decimal] = mapped_column(
    Numeric(5, 2),
    nullable=False,
    default=Decimal("10"),
  )
  
  default_retention_cap_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
  start_date: Mapped[date] = mapped_column(Date, nullable=False)
  end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
  
  status: Mapped[SubcontractAgreementStatus] = mapped_column(
    Enum(SubcontractAgreementStatus,
    name="subcontract_agreement_status"),
    nullable=False,
    default=SubcontractAgreementStatus.ACTIVE,
  )
  
  notes: Mapped[str | None] = mapped_column(Text, nullable=True)
  version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
  subcontractor: Mapped["Subcontractor"] = relationship("Subcontractor", back_populates="agreements")
  
  items: Mapped[list["SubcontractAgreementItem"]] = relationship(
    "SubcontractAgreementItem",
    back_populates="agreement",
    cascade="all, delete-orphan",
    order_by="SubcontractAgreementItem.sort_order",
  )

class SubcontractAgreementItem(Base):
  __tablename__ = "subcontract_agreement_items"

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  agreement_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("subcontract_agreements.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
  description: Mapped[str] = mapped_column(String(300), nullable=False)
  unit: Mapped[str] = mapped_column(String(50), nullable=False)
  quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
  rate: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)

  agreement: Mapped["SubcontractAgreement"] = relationship(
    "SubcontractAgreement",
    back_populates="items",
  )

class SubcontractorBill(Base, TimestampMixin):
  __tablename__ = "subcontractor_bills"

  __table_args__ = (
    UniqueConstraint("organization_id", "agreement_id", "bill_number", name="uq_subcontractor_bill_number"),
    Index("ix_subcontractor_bills_org_project", "organization_id", "project_id"),
  )

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
  
  agreement_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("subcontract_agreements.id",
    ondelete="RESTRICT"),
    nullable=False,
  )
  
  bill_number: Mapped[int] = mapped_column(Integer, nullable=False)
  
  status: Mapped[SubcontractorBillStatus] = mapped_column(
    Enum(SubcontractorBillStatus,
    name="subcontractor_bill_status"),
    nullable=False,
    default=SubcontractorBillStatus.DRAFT,
  )
  
  period_start: Mapped[date] = mapped_column(Date, nullable=False)
  period_end: Mapped[date] = mapped_column(Date, nullable=False)

  gross_value_this_period: Mapped[Decimal] = mapped_column(
    Numeric(16, 2),
    nullable=False,
    default=Decimal("0"),
  )
  
  gross_value_cumulative: Mapped[Decimal] = mapped_column(
    Numeric(16, 2),
    nullable=False,
    default=Decimal("0"),
  )
  
  retention_percentage: Mapped[Decimal] = mapped_column(
    Numeric(5, 2),
    nullable=False,
    default=Decimal("10"),
  )
  
  retention_cap_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
  retention_this_period: Mapped[Decimal] = mapped_column(
    Numeric(16, 2),
    nullable=False,
    default=Decimal("0"),
  )
  
  retention_cumulative: Mapped[Decimal] = mapped_column(
    Numeric(16, 2),
    nullable=False,
    default=Decimal("0"),
  )
  
  other_deductions_amount: Mapped[Decimal] = mapped_column(
    Numeric(16, 2),
    nullable=False,
    default=Decimal("0")
  )
  
  other_deductions_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
  net_payable: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=Decimal("0"))
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
  line_items: Mapped[list["SubcontractorBillLineItem"]] = relationship(
    "SubcontractorBillLineItem",
    back_populates="bill",
    cascade="all, delete-orphan",
    order_by="SubcontractorBillLineItem.sort_order",
  )

class SubcontractorBillLineItem(Base):
  __tablename__ = "subcontractor_bill_line_items"

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  bill_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("subcontractor_bills.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  agreement_item_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("subcontract_agreement_items.id",
    ondelete="RESTRICT"),
    nullable=False,
  )
  
  sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
  description: Mapped[str] = mapped_column(String(300), nullable=False)
  unit: Mapped[str] = mapped_column(String(50), nullable=False)
  contract_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
  rate: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
  
  previous_percentage: Mapped[Decimal] = mapped_column(
    Numeric(5, 2),
    nullable=False,
    default=Decimal("0"),
  )
  
  cumulative_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0"))
  this_period_value: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=Decimal("0"))
  cumulative_value: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=Decimal("0"))
  bill: Mapped["SubcontractorBill"] = relationship("SubcontractorBill", back_populates="line_items")

class SubcontractorAdvance(Base, TimestampMixin):
  __tablename__ = "subcontractor_advances"

  __table_args__ = (Index("ix_subcontractor_advances_org_agreement", "organization_id", "agreement_id"),)

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
  
  agreement_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("subcontract_agreements.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
  advance_date: Mapped[date] = mapped_column(Date, nullable=False)
  notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
  
  created_by_user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="RESTRICT"),
    nullable=False,
  )

class SubcontractorPayment(Base, TimestampMixin):
  __tablename__ = "subcontractor_payments"

  __table_args__ = (Index("ix_subcontractor_payments_org_agreement", "organization_id", "agreement_id"),)

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
  )
  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False,
  )
  agreement_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True), ForeignKey("subcontract_agreements.id", ondelete="CASCADE"), nullable=False,
  )
  bill_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True), ForeignKey("subcontractor_bills.id", ondelete="SET NULL"), nullable=True,
  )
  gross_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
  
  advance_recovered_amount: Mapped[Decimal] = mapped_column(
    Numeric(16, 2),
    nullable=False,
    default=Decimal("0"),
  )
  
  wht_category: Mapped[str | None] = mapped_column(String(30), nullable=True)
  wht_rate_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
  
  wht_deducted_amount: Mapped[Decimal] = mapped_column(
    Numeric(16, 2),
    nullable=False, 
    default=Decimal("0"),
  )
  
  net_paid_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
  payment_date: Mapped[date] = mapped_column(Date, nullable=False)
  notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
  
  created_by_user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="RESTRICT"),
    nullable=False,
  )