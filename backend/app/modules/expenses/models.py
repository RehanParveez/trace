from __future__ import annotations
import enum
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy import Index, Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
import uuid
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from datetime import date
from decimal import Decimal

class ExpenseStatus(str, enum.Enum):
  PENDING = "PENDING"
  APPROVED = "APPROVED"
  REJECTED = "REJECTED"

class Expense(Base, TimestampMixin):
  __tablename__ = "expenses"
  __table_args__ = (
    Index("ix_expenses_project", "project_id"),
    Index("ix_expenses_org", "organization_id"),
    Index("ix_expenses_status", "status"),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
  )
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False, index=True,
  )
  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="CASCADE"),
    nullable=False, index=True,
  )
  category: Mapped[str] = mapped_column(String(150), nullable=False)
  description: Mapped[str | None] = mapped_column(Text, nullable=True)
  amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
  expense_date: Mapped[date] = mapped_column(Date, nullable=False)
  status: Mapped[ExpenseStatus] = mapped_column(
    Enum(ExpenseStatus, name="expense_status"),
    nullable=False, default=ExpenseStatus.PENDING,
  )
  submitted_by: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
  reviewed_by: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
  review_note: Mapped[str | None] = mapped_column(Text, nullable=True)