from __future__ import annotations
import enum
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from datetime import date
from decimal import Decimal
from uuid import UUID
from sqlalchemy import Date, Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint

class LabourSourceType(str, enum.Enum):
  DIRECT = "DIRECT"
  CONTRACTOR = "CONTRACTOR"

class LabourDeploymentStatus(str, enum.Enum):
  ACTIVE = "ACTIVE"
  ENDED = "ENDED"

class LabourSource(Base, TimestampMixin):
  __tablename__ = "labour_sources"

  __table_args__ = (
    Index("ix_labour_sources_org", "organization_id"),
  )

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  name: Mapped[str] = mapped_column(String(200), nullable=False)
  source_type: Mapped[LabourSourceType] = mapped_column(
    Enum(LabourSourceType, name="labour_source_type"),
    nullable=False,
  )
  
  contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
  contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
  is_active_taxpayer: Mapped[bool] = mapped_column(nullable=False, default=False)
  is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
  notes: Mapped[str | None] = mapped_column(Text, nullable=True)

  workers: Mapped[list["LabourWorker"]] = relationship("LabourWorker", back_populates="source")

class LabourWorker(Base, TimestampMixin):
  __tablename__ = "labour_workers"

  __table_args__ = (
    Index("ix_labour_workers_org_source", "organization_id", "source_id"),
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
  
  source_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("labour_sources.id", ondelete="RESTRICT"),
    nullable=False,
  )
  name: Mapped[str] = mapped_column(String(200), nullable=False)
  trade: Mapped[str] = mapped_column(String(100), nullable=False)
  cnic: Mapped[str | None] = mapped_column(String(20), nullable=True)
  phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
  default_daily_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
  is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

  source: Mapped["LabourSource"] = relationship("LabourSource", back_populates="workers")

class LabourDeployment(Base, TimestampMixin):
  __tablename__ = "labour_deployments"

  __table_args__ = (
    Index("ix_labour_deployments_org_project", "organization_id", "project_id"),
    Index("ix_labour_deployments_source", "source_id"),
    Index("ix_labour_deployments_worker", "worker_id"),
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
  
  source_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("labour_sources.id", ondelete="RESTRICT"),
    nullable=False,
  )
  
  worker_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("labour_workers.id", ondelete="RESTRICT"),
    nullable=True,
  )
  
  trade: Mapped[str] = mapped_column(String(100), nullable=False)
  daily_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
  start_date: Mapped[date] = mapped_column(Date, nullable=False)
  end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
  
  status: Mapped[LabourDeploymentStatus] = mapped_column(
    Enum(LabourDeploymentStatus, name="labour_deployment_status"),
    nullable=False,
    default=LabourDeploymentStatus.ACTIVE,
  )

  attendance: Mapped[list["LabourAttendance"]] = relationship("LabourAttendance", back_populates="deployment")

class LabourAttendance(Base, TimestampMixin):
  __tablename__ = "labour_attendance"

  __table_args__ = (
    UniqueConstraint("deployment_id", "attendance_date", name="uq_labour_attendance_deployment_date"),
    Index("ix_labour_attendance_org_project_date", "organization_id", "project_id", "attendance_date"),
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
  
  deployment_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("labour_deployments.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
  units_present: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
  
  notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
  
  recorded_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True), 
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )

  deployment: Mapped["LabourDeployment"] = relationship("LabourDeployment", back_populates="attendance")

class LabourAdvance(Base, TimestampMixin):
  __tablename__ = "labour_advances"

  __table_args__ = (
    Index("ix_labour_advances_org_project", "organization_id", "project_id"),
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
  
  source_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("labour_sources.id", ondelete="RESTRICT"),
    nullable=False,
  )
  
  worker_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True), 
    ForeignKey("labour_workers.id", ondelete="RESTRICT"),
    nullable=True,
  )
  
  amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
  advance_date: Mapped[date] = mapped_column(Date, nullable=False)
  notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
  
  created_by_user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="RESTRICT"),
    nullable=False,
  )

class LabourPayment(Base, TimestampMixin):
  __tablename__ = "labour_payments"

  __table_args__ = (
    Index("ix_labour_payments_org_project", "organization_id", "project_id"),
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
  
  source_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("labour_sources.id", ondelete="RESTRICT"),
    nullable=False,
  )
  
  worker_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("labour_workers.id", ondelete="RESTRICT"),
    nullable=True,
  )
  
  period_start: Mapped[date] = mapped_column(Date, nullable=False)
  period_end: Mapped[date] = mapped_column(Date, nullable=False)
  
  gross_wage_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
  
  advance_recovered_amount: Mapped[Decimal] = mapped_column(
    Numeric(14, 2),
    nullable=False,
    default=Decimal("0"),
  )
  
  wht_category: Mapped[str | None] = mapped_column(String(30), nullable=True)
  wht_rate_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
  
  wht_deducted_amount: Mapped[Decimal] = mapped_column(
    Numeric(14, 2),
    nullable=False, default=Decimal("0"),
  )
  
  net_paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
  payment_date: Mapped[date] = mapped_column(Date, nullable=False)
  
  notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
  
  created_by_user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="RESTRICT"),
    nullable=False,
  )