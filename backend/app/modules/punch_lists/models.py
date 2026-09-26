from __future__ import annotations
from sqlalchemy import Enum, Date, DateTime, ForeignKey, Index, String, Text
import enum
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from datetime import date, datetime

class PunchListStatus(str, enum.Enum):
  OPEN = "OPEN"
  CLOSED = "CLOSED"

class PunchListItemStatus(str, enum.Enum):
  OPEN = "OPEN"
  IN_PROGRESS = "IN_PROGRESS"
  RESOLVED = "RESOLVED"
  WAIVED = "WAIVED"

class PunchListPhotoPurpose(str, enum.Enum):
  DEFECT = "DEFECT"
  RESOLUTION = "RESOLUTION"

class PunchList(Base, TimestampMixin):
  __tablename__ = "punch_lists"

  __table_args__ = (Index("ix_punch_lists_org_project", "organization_id", "project_id"),)

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
  
  title: Mapped[str] = mapped_column(String(300), nullable=False)
  inspection_date: Mapped[date] = mapped_column(Date, nullable=False)
  
  status: Mapped[PunchListStatus] = mapped_column(
    Enum(PunchListStatus,
      name="punch_list_status"),
      nullable=False,
      default=PunchListStatus.OPEN,
    )
  
  notes: Mapped[str | None] = mapped_column(Text, nullable=True)
  
  created_by_user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="RESTRICT"),
    nullable=False,
  )
  
  closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

  items: Mapped[list["PunchListItem"]] = relationship(
    "PunchListItem",
    back_populates="punch_list",
    cascade="all, delete-orphan",
  )

class PunchListItem(Base, TimestampMixin):
  __tablename__ = "punch_list_items"

  __table_args__ = (Index("ix_punch_list_items_org_list", "organization_id", "punch_list_id"),)

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
  
  punch_list_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("punch_lists.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  location: Mapped[str] = mapped_column(String(200), nullable=False)
  description: Mapped[str] = mapped_column(Text, nullable=False)

  assigned_to_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
  
  assigned_to_subcontractor_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("subcontractors.id", ondelete="SET NULL"),
    nullable=True,
  )

  status: Mapped[PunchListItemStatus] = mapped_column(
    Enum(PunchListItemStatus,
      name="punch_list_item_status"),
      nullable=False,
      default=PunchListItemStatus.OPEN,
    )
  
  due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
  resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
  
  created_by_user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="RESTRICT"),
    nullable=False,
  )

  punch_list: Mapped["PunchList"] = relationship("PunchList", back_populates="items")
  
  photos: Mapped[list["PunchListItemPhoto"]] = relationship(
    "PunchListItemPhoto",
    back_populates="item",
    cascade="all, delete-orphan",
  )

class PunchListItemPhoto(Base, TimestampMixin):
  __tablename__ = "punch_list_item_photos"

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
  
  punch_list_item_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("punch_list_items.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  site_photo_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("site_photos.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  photo_purpose: Mapped[PunchListPhotoPurpose] = mapped_column(
    Enum(PunchListPhotoPurpose,
      name="punch_list_photo_purpose"),
      nullable=False,
    )

  item: Mapped["PunchListItem"] = relationship("PunchListItem", back_populates="photos")