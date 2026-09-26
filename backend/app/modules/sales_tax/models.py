from __future__ import annotations
import enum
from sqlalchemy import Enum, Boolean, Date, ForeignKey, Index, Numeric, String, Text
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from decimal import Decimal
from datetime import date

class SalesTaxAuthority(str, enum.Enum):
  PRA = "PRA" 
  SRB = "SRB"    
  KPRA = "KPRA"
  BRA = "BRA"    
  ICT = "ICT"    

class SalesTaxSourceType(str, enum.Enum):
  RUNNING_BILL = "RUNNING_BILL"
  SUBCONTRACTOR_BILL = "SUBCONTRACTOR_BILL"

class SalesTaxRate(Base, TimestampMixin):
  __tablename__ = "sales_tax_rates"

  __table_args__ = (Index("ix_sales_tax_rates_org_authority", "organization_id", "authority"),)

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  authority: Mapped[SalesTaxAuthority] = mapped_column(
    Enum(SalesTaxAuthority,
      name="sales_tax_authority"),
      nullable=False)
  
  rate_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
  effective_from: Mapped[date] = mapped_column(Date, nullable=False)
  is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
  notes: Mapped[str | None] = mapped_column(Text, nullable=True)

class SalesTaxCharge(Base, TimestampMixin):
  __tablename__ = "sales_tax_charges"

  __table_args__ = (
    Index("ix_sales_tax_charges_org_project", "organization_id", "project_id"),
    Index("ix_sales_tax_charges_source", "source_type", "source_id"),
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
  
  source_type: Mapped[SalesTaxSourceType] = mapped_column(
    Enum(SalesTaxSourceType,
      name="sales_tax_source_type"),
      nullable=False,
    )
  
  source_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  
  authority: Mapped[SalesTaxAuthority] = mapped_column(
    Enum(SalesTaxAuthority,
      name="sales_tax_authority"),
      nullable=False,
    )
  
  rate_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
  taxable_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
  tax_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
  charge_date: Mapped[date] = mapped_column(Date, nullable=False)
  currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PKR")
  
  created_by_user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="RESTRICT"),
    nullable=False,
  )