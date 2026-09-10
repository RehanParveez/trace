from __future__ import annotations
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy import UniqueConstraint, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from decimal import Decimal

class Budget(Base, TimestampMixin):
  __tablename__ = "budgets"
  __table_args__ = (
    UniqueConstraint(
      "project_id",
      name="uq_budgets_project_id",
    ),
    Index("ix_budgets_project", "project_id"),
    Index("ix_budgets_organization", "organization_id"),
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
  approved_amount: Mapped[Decimal] = mapped_column(
    Numeric(18, 2), nullable=False,
  )
  currency: Mapped[str] = mapped_column(
    String(3), nullable=False, default="PKR", server_default="PKR",
  )
  notes: Mapped[str | None] = mapped_column(Text, nullable=True)

  categories: Mapped[list["BudgetCategory"]] = relationship(
    "BudgetCategory",
    back_populates="budget",
    cascade="all, delete-orphan",
    order_by="BudgetCategory.created_at",
  )

class BudgetCategory(Base, TimestampMixin):
  __tablename__ = "budget_categories"
  __table_args__ = (
    Index("ix_budget_categories_budget", "budget_id"),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
  )
  budget_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("budgets.id", ondelete="CASCADE"),
    nullable=False, index=True,
  )
  name: Mapped[str] = mapped_column(String(200), nullable=False)
  allocated_amount: Mapped[Decimal] = mapped_column(
    Numeric(18, 2), nullable=False, default=0,
  )

  budget: Mapped["Budget"] = relationship(
    "Budget", back_populates="categories",
  )