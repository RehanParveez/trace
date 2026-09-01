from __future__ import annotations
import enum
import uuid
from datetime import datetime
from uuid import UUID
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.shared.mixins import TimestampMixin

class NotificationType(str, enum.Enum):
  DRAWING_PARSED = "DRAWING_PARSED"
  DRAWING_FAILED = "DRAWING_FAILED"
  BOQ_ITEM_APPROVED = "BOQ_ITEM_APPROVED"
  SITE_PHOTO_NEEDS_PROJECT = "SITE_PHOTO_NEEDS_PROJECT"
  PROGRESS_CLAIM_SUBMITTED = "PROGRESS_CLAIM_SUBMITTED"
  PROGRESS_CLAIM_APPROVED = "PROGRESS_CLAIM_APPROVED"
  PROGRESS_CLAIM_REJECTED = "PROGRESS_CLAIM_REJECTED"
  SUBSCRIPTION_USAGE_WARNING = "SUBSCRIPTION_USAGE_WARNING"
  MEMBER_JOINED = "MEMBER_JOINED"
  ORGANIZATION_INVITATION_RECEIVED = "ORGANIZATION_INVITATION_RECEIVED"

class Notification(Base, TimestampMixin):
  __tablename__ = "notifications"

  __table_args__ = (
    Index(
      "ix_notifications_org_user_read",
      "organization_id",
      "user_id",
      "is_read",
    ),
    Index(
      "ix_notifications_user_created",
      "user_id",
      "created_at",
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

  user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  type: Mapped[NotificationType] = mapped_column(
    Enum(NotificationType, name="notification_type"),
    nullable=False,
    index=True,
  )

  title: Mapped[str] = mapped_column(
    String(200),
    nullable=False,
  )

  body: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
  )

  link_path: Mapped[str | None] = mapped_column(
    String(500),
    nullable=True,
  )

  is_read: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=False,
    index=True,
  )

  read_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )