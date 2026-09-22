from __future__ import annotations
import enum
from sqlalchemy import Enum
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from sqlalchemy import ForeignKey, Boolean, Date, Index, Numeric, String, Text
from decimal import Decimal
from datetime import date

class WHTCategory(str, enum.Enum):
  GOODS_SUPPLY = "GOODS_SUPPLY"
  SERVICES = "SERVICES"
  CONTRACTS_EXECUTION = "CONTRACTS_EXECUTION"

class WHTSourceType(str, enum.Enum):
  SUBCONTRACTOR_PAYMENT = "SUBCONTRACTOR_PAYMENT"
  LABOUR_PAYMENT = "LABOUR_PAYMENT"

class WithholdingTaxRate(Base, TimestampMixin):
  __tablename__ = "withholding_tax_rates"

  __table_args__ = (Index("ix_wht_rates_org_category", "organization_id", "category"),)

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
  
  category: Mapped[WHTCategory] = mapped_column(
    Enum(WHTCategory, name="wht_category"), 
    nullable=False,
  )
  
  filer_rate_percentage: Mapped[Decimal] = mapped_column(
    Numeric(5, 2),
    nullable=False,
  )
  
  non_filer_rate_percentage: Mapped[Decimal] = mapped_column(
    Numeric(5, 2),
    nullable=False,
  )
  
  effective_from: Mapped[date] = mapped_column(Date, nullable=False)
  is_active: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=True,
  )
  
  notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class WithholdingTaxDeduction(Base, TimestampMixin):
  __tablename__ = "withholding_tax_deductions"

  __table_args__ = (
    Index("ix_wht_deductions_org_project", "organization_id", "project_id"),
    Index("ix_wht_deductions_source", "source_type", "source_id"),
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
  
  source_type: Mapped[WHTSourceType] = mapped_column(
    Enum(WHTSourceType,
    name="wht_source_type"),
    nullable=False,
  )
  
  source_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    nullable=False,
  )

  payee_name: Mapped[str] = mapped_column(String(200), nullable=False)
  
  payee_ntn_or_cnic: Mapped[str | None] = mapped_column(
    String(30),
    nullable=True,
  )
  
  category: Mapped[WHTCategory] = mapped_column(
    Enum(WHTCategory, name="wht_category"),
    nullable=False,
  )
  
  gross_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
  rate_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
  is_filer: Mapped[bool] = mapped_column(Boolean, nullable=False)
  deducted_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
  deduction_date: Mapped[date] = mapped_column(Date, nullable=False)
  currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PKR")
  
  created_by_user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="RESTRICT"),
    nullable=False,
  )