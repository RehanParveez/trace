from __future__ import annotations
import enum
import uuid
from datetime import datetime
from uuid import UUID
from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

SUPPORT_GRANT_MAX_HOURS = 72

class OrganizationKey(Base):
  __tablename__ = "organization_keys"
  __table_args__ = (UniqueConstraint("organization_id", "version", name="uq_organization_keys_org_version"),)

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
  version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
  wrapped_dek: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
  provider: Mapped[str] = mapped_column(String(20), nullable=False)
  key_ref: Mapped[str] = mapped_column(String(255), nullable=False, default="")
  is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
  retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class SupportAccessGrant(Base):
  __tablename__ = "support_access_grants"
  __table_args__ = (
    CheckConstraint("expires_at > starts_at", name="ck_support_grant_positive"),
    CheckConstraint(f"expires_at <= starts_at + interval '{SUPPORT_GRANT_MAX_HOURS} hours'", name="ck_support_grant_max_72h"),
    Index("ix_support_grants_org_expires", "organization_id", "expires_at"),
  )

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
    index=True
  )
  
  granted_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True), 
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
  
  reason: Mapped[str] = mapped_column(String(500), nullable=False)
  starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
  expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
  revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  
  revoked_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
  
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ExportStatus(str, enum.Enum):
  QUEUED = "QUEUED"
  RUNNING = "RUNNING"
  COMPLETED = "COMPLETED"
  FAILED = "FAILED"
  EXPIRED = "EXPIRED"

class DataExportJob(Base):
  """A request by the company to download everything it has stored."""
  __tablename__ = "data_export_jobs"
  __table_args__ = (Index("ix_data_export_jobs_org_created", "organization_id", "created_at"),)

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"), 
    nullable=False, 
    index=True,
  )
  
  requested_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
  status: Mapped[str] = mapped_column(String(20), nullable=False, default=ExportStatus.QUEUED.value)
  storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
  size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
  table_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
  row_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
  file_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
  error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
  started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class DeletionStatus(str, enum.Enum):
  PENDING = "PENDING"
  CANCELLED = "CANCELLED"
  EXECUTING = "EXECUTING"
  COMPLETED = "COMPLETED"
  FAILED = "FAILED"

class OrganizationDeletionRequest(Base):
  __tablename__ = "organization_deletion_requests"
  
  __table_args__ = (
    Index("uq_org_deletion_one_pending", "organization_id", unique=True, postgresql_where=text("status IN ('PENDING','EXECUTING')")),
  )

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
    index=True
  )
  
  requested_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
  
  status: Mapped[str] = mapped_column(String(20), nullable=False, default=DeletionStatus.PENDING.value)
  reason: Mapped[str | None] = mapped_column(Text, nullable=True)
  requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
  scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
  cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  
  cancelled_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True), 
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
  
  executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
