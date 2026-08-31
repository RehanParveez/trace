from __future__ import annotations
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.shared.mixins import TimestampMixin

class ProgressClaimStatus(str, enum.Enum):
  DRAFT = "DRAFT"
  SUBMITTED = "SUBMITTED"
  APPROVED = "APPROVED"
  REJECTED = "REJECTED"

class ProgressClaim(Base, TimestampMixin):
  __tablename__ = "progress_claims"

  __table_args__ = (
    Index(
      "ix_progress_claims_org_project",
      "organization_id",
      "project_id",
    ),
    Index(
      "ix_progress_claims_org_status",
      "organization_id",
      "status",
    ),
    Index(
      "ix_progress_claims_project_date",
      "project_id",
      "claim_date",
    ),
    CheckConstraint(
      "claimed_quantity > 0",
      name="ck_progress_claim_claimed_quantity_positive",
    ),
    CheckConstraint(
      "claimed_percentage >= 0 AND claimed_percentage <= 100",
      name="ck_progress_claim_percentage_range",
    ),
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
    index=True,
  )

  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  boq_item_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("boq_items.id", ondelete="RESTRICT"),
    nullable=False,
    index=True,
  )

  claim_date: Mapped[date] = mapped_column(
    Date,
    nullable=False,
  )

  claimed_quantity: Mapped[Decimal] = mapped_column(
    Numeric(precision=18, scale=4),
    nullable=False,
  )

  claimed_percentage: Mapped[Decimal] = mapped_column(
    Numeric(precision=7, scale=4),
    nullable=False,
  )

  notes: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
  )

  status: Mapped[ProgressClaimStatus] = mapped_column(
    Enum(
      ProgressClaimStatus,
      name="progress_claim_status",
    ),
    nullable=False,
    default=ProgressClaimStatus.DRAFT,
    index=True,
  )

  submitted_by: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )

  submitted_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )

  reviewed_by: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )

  reviewed_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )

  review_note: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
  )

  version: Mapped[int] = mapped_column(
    nullable=False,
    default=1,
  )

class PhotoBOQLink(Base, TimestampMixin):
  __tablename__ = "photo_boq_links"

  __table_args__ = (
    UniqueConstraint(
      "progress_claim_id",
      "site_photo_id",
      "boq_item_id",
      name="uq_photo_boq_link_claim_photo_boq",
    ),
    Index(
      "ix_photo_boq_links_org_project",
      "organization_id",
      "project_id",
    ),
    Index(
      "ix_photo_boq_links_claim",
      "progress_claim_id",
    ),
    Index(
      "ix_photo_boq_links_photo",
      "site_photo_id",
    ),
    Index(
      "ix_photo_boq_links_boq_item",
      "boq_item_id",
    ),
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
    index=True,
  )

  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  progress_claim_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "progress_claims.id",
      ondelete="CASCADE",
    ),
    nullable=False,
  )

  site_photo_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "site_photos.id",
      ondelete="CASCADE",
    ),
    nullable=False,
  )

  boq_item_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "boq_items.id",
      ondelete="CASCADE",
    ),
    nullable=False,
  )

  note: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
  )

  created_by: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )