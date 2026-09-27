from __future__ import annotations
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.shared.mixins import TimestampMixin

class BankGuaranteeHolderType(str, enum.Enum):
  CLIENT = "CLIENT"              
  SUBCONTRACTOR = "SUBCONTRACTOR" 

class BankGuaranteePurpose(str, enum.Enum):
  RETENTION = "RETENTION"

class BankGuaranteeStatus(str, enum.Enum):
  ACTIVE = "ACTIVE"
  RENEWED = "RENEWED"   
  RELEASED = "RELEASED" 
  CALLED = "CALLED"     

class BankGuarantee(Base, TimestampMixin):
  __tablename__ = "bank_guarantees"

  __table_args__ = (
    Index("ix_bank_guarantees_org_project", "organization_id", "project_id"),
    Index("ix_bank_guarantees_agreement", "agreement_id"),
    Index("ix_bank_guarantees_boq_version", "boq_version_id"),
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
  
  holder_type: Mapped[BankGuaranteeHolderType] = mapped_column(
    Enum(BankGuaranteeHolderType,
      name="bank_guarantee_holder_type"),
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
  
  purpose: Mapped[BankGuaranteePurpose] = mapped_column(
    Enum(BankGuaranteePurpose,
      name="bank_guarantee_purpose"),
      nullable=False,
      default=BankGuaranteePurpose.RETENTION,
    )
  
  guarantee_number: Mapped[str] = mapped_column(String(100), nullable=False)
  issuing_bank: Mapped[str] = mapped_column(String(200), nullable=False)
  amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
  currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PKR")
  issue_date: Mapped[date] = mapped_column(Date, nullable=False)
  expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
  
  status: Mapped[BankGuaranteeStatus] = mapped_column(
    Enum(BankGuaranteeStatus,
      name="bank_guarantee_status"),
      nullable=False,
      default=BankGuaranteeStatus.ACTIVE,
    )
  
  renewed_from_guarantee_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("bank_guarantees.id", ondelete="SET NULL"),
    nullable=True,
  )
  
  superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  notes: Mapped[str | None] = mapped_column(Text, nullable=True)
  
  created_by_user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="RESTRICT"),
    nullable=False,
  )