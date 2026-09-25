from __future__ import annotations
from sqlalchemy import Enum, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
import enum
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from decimal import Decimal
from datetime import datetime

class ChangeOrderType(str, enum.Enum):
  ADDITION = "ADDITION"
  OMISSION = "OMISSION"
  VARIATION = "VARIATION"

class ChangeOrderStatus(str, enum.Enum):
  DRAFT = "DRAFT"
  APPROVED = "APPROVED"
  REJECTED = "REJECTED"
  CANCELLED = "CANCELLED"

class ChangeOrder(Base, TimestampMixin):
  __tablename__ = "change_orders"

  __table_args__ = (
    UniqueConstraint("organization_id", "project_id", "change_order_number", name="uq_change_order_number"),
    Index("ix_change_orders_org_project", "organization_id", "project_id"),
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
  
  boq_version_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("boq_versions.id", ondelete="RESTRICT"),
    nullable=False,
  )
  
  change_order_number: Mapped[int] = mapped_column(Integer, nullable=False)
  change_type: Mapped[ChangeOrderType] = mapped_column(
    Enum(ChangeOrderType,
      name="change_order_type"),
      nullable=False,
  )
  
  status: Mapped[ChangeOrderStatus] = mapped_column(
    Enum(ChangeOrderStatus,
      name="change_order_status"),
      nullable=False,
      default=ChangeOrderStatus.DRAFT,
  )
  
  title: Mapped[str] = mapped_column(String(300), nullable=False)
  description: Mapped[str | None] = mapped_column(Text, nullable=True)
  client_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)

  value_impact: Mapped[Decimal] = mapped_column(
    Numeric(16, 2),
    nullable=False,
    default=Decimal("0"),
  )
  currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PKR")

  requested_by_user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="RESTRICT"),
    nullable=False,
  )
  
  approved_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
  
  approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

  version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

  line_items: Mapped[list["ChangeOrderLineItem"]] = relationship(
    "ChangeOrderLineItem",
    back_populates="change_order",
    cascade="all, delete-orphan",
    order_by="ChangeOrderLineItem.sort_order",
  )

class ChangeOrderLineItem(Base):
  __tablename__ = "change_order_line_items"

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
  
  change_order_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("change_orders.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
  description: Mapped[str] = mapped_column(String(300), nullable=False)
  unit: Mapped[str] = mapped_column(String(50), nullable=False)

  boq_item_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("boq_items.id", ondelete="RESTRICT"),
    nullable=True,
  )
  
  quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
  unit_rate: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
  realized_value_impact: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
  
  created_boq_item_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("boq_items.id", ondelete="SET NULL"),
    nullable=True,
  )

  change_order: Mapped["ChangeOrder"] = relationship("ChangeOrder", back_populates="line_items")