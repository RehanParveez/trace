from __future__ import annotations
import enum
import uuid
from datetime import date, datetime
from uuid import UUID
from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.shared.mixins import TimestampMixin

class WhatsAppMessageType(str, enum.Enum):
  IMAGE = "IMAGE"
  TEXT = "TEXT"
  INTERACTIVE = "INTERACTIVE"
  OTHER = "OTHER"

class WhatsAppMessageStatus(str, enum.Enum):
  RECEIVED = "RECEIVED"
  MEDIA_DOWNLOADING = "MEDIA_DOWNLOADING"
  AWAITING_PROJECT_SELECTION = "AWAITING_PROJECT_SELECTION"
  PROCESSED = "PROCESSED"
  FAILED = "FAILED"
  IGNORED = "IGNORED"

class PhotoTagSource(str, enum.Enum):
  MANUAL = "MANUAL"
  AI = "AI"

class WhatsAppChannel(Base, TimestampMixin):
  __tablename__ = "whatsapp_channels"

  __table_args__ = (
    UniqueConstraint(
      "organization_id",
      name="uq_whatsapp_channels_organization",
    ),
    UniqueConstraint(
      "phone_number_id",
      name="uq_whatsapp_channels_phone_number_id",
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

  phone_number_id: Mapped[str] = mapped_column(
    String(64),
    nullable=False,
    index=True,
  )

  business_account_id: Mapped[str] = mapped_column(
    String(64),
    nullable=False,
  )

  display_phone_number: Mapped[str | None] = mapped_column(
    String(32),
    nullable=True,
  )

  access_token: Mapped[str] = mapped_column(
    Text,
    nullable=False,
  )

  is_active: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=True,
  )

  messages: Mapped[list["WhatsAppMessage"]] = relationship(
    "WhatsAppMessage",
    back_populates="channel",
    cascade="all, delete-orphan",
  )

class WhatsAppMessage(Base, TimestampMixin):
  __tablename__ = "whatsapp_messages"

  __table_args__ = (
    UniqueConstraint(
      "wa_message_id",
      name="uq_whatsapp_messages_wa_message_id",
    ),
    Index(
      "ix_whatsapp_messages_org_status",
      "organization_id",
      "status",
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

  channel_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("whatsapp_channels.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  wa_message_id: Mapped[str] = mapped_column(
    String(128),
    nullable=False,
  )

  from_phone_number: Mapped[str] = mapped_column(
    String(32),
    nullable=False,
  )

  message_type: Mapped[WhatsAppMessageType] = mapped_column(
    Enum(WhatsAppMessageType, name="whatsapp_message_type"),
    nullable=False,
  )

  caption_text: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
  )

  media_id: Mapped[str | None] = mapped_column(
    String(128),
    nullable=True,
  )
  
  raw_payload: Mapped[dict] = mapped_column(
    JSON,
    nullable=False,
    default=dict,
  )

  status: Mapped[WhatsAppMessageStatus] = mapped_column(
    Enum(WhatsAppMessageStatus, name="whatsapp_message_status"),
    nullable=False,
    default=WhatsAppMessageStatus.RECEIVED,
    index=True,
  )

  prompt_wa_message_id: Mapped[str | None] = mapped_column(
    String(128),
    nullable=True,
    index=True,
  )

  received_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
  )

  processed_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )

  error_message: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
  )

  channel: Mapped["WhatsAppChannel"] = relationship(
    "WhatsAppChannel",
    back_populates="messages",
  )

  site_photo: Mapped["SitePhoto | None"] = relationship(
    "SitePhoto",
    back_populates="whatsapp_message",
    uselist=False,
  )

class SitePhoto(Base, TimestampMixin):
  __tablename__ = "site_photos"

  __table_args__ = (
    Index(
      "ix_site_photos_org_project",
      "organization_id",
      "project_id",
    ),
    Index(
      "ix_site_photos_org_photo_date",
      "organization_id",
      "photo_date",
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

  project_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
  )

  whatsapp_message_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("whatsapp_messages.id", ondelete="SET NULL"),
    nullable=True,
    unique=True,
  )

  storage_key: Mapped[str] = mapped_column(
    String(1000),
    nullable=False,
  )

  sender_phone_number: Mapped[str | None] = mapped_column(
    String(32),
    nullable=True,
  )

  caption_raw: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
  )

  caption_parsed: Mapped[dict] = mapped_column(
    JSON,
    nullable=False,
    default=dict,
  )

  location_text: Mapped[str | None] = mapped_column(
    String(500),
    nullable=True,
  )

  photo_date: Mapped[date | None] = mapped_column(
    Date,
    nullable=True,
  )

  is_ai_tagged: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=False,
  )

  whatsapp_message: Mapped["WhatsAppMessage | None"] = relationship(
    "WhatsAppMessage",
    back_populates="site_photo",
  )

  tags: Mapped[list["PhotoTag"]] = relationship(
    "PhotoTag",
    back_populates="site_photo",
    cascade="all, delete-orphan",
  )

class PhotoTag(Base, TimestampMixin):
  __tablename__ = "photo_tags"

  __table_args__ = (
    Index(
      "ix_photo_tags_site_photo",
      "site_photo_id",
    ),
    
    UniqueConstraint(
      "site_photo_id",
      "tag",
      name="uq_photo_tags_site_photo_tag",
    ),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  site_photo_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("site_photos.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  tag: Mapped[str] = mapped_column(
    String(100),
    nullable=False,
  )

  confidence: Mapped[float | None] = mapped_column(
    Float,
    nullable=True,
  )

  source: Mapped[PhotoTagSource] = mapped_column(
    Enum(PhotoTagSource, name="photo_tag_source"),
    nullable=False,
    default=PhotoTagSource.MANUAL,
  )

  site_photo: Mapped["SitePhoto"] = relationship(
    "SitePhoto",
    back_populates="tags",
  )