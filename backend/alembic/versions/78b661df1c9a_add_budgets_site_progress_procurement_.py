"""add budgets site_progress procurement expenses

Revision ID: 78b661df1c9a
Revises: 0843eb82db27
Create Date: 2026-09-10 14:50:42.514235
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "78b661df1c9a"
down_revision: Union[str, Sequence[str], None] = "0843eb82db27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  op.create_table(
    "budgets",
    sa.Column("id", sa.UUID(), nullable=False),
    sa.Column("organization_id", sa.UUID(), nullable=False),
    sa.Column("project_id", sa.UUID(), nullable=False),
    sa.Column("approved_amount", sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column("currency", sa.String(length=3), server_default="PKR", nullable=False),
    sa.Column("notes", sa.Text(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("project_id", name="uq_budgets_project_id"),
  )
  op.create_index("ix_budgets_organization", "budgets", ["organization_id"], unique=False)
  op.create_index("ix_budgets_project", "budgets", ["project_id"], unique=False)

  op.create_table(
    "budget_categories",
    sa.Column("id", sa.UUID(), nullable=False),
    sa.Column("budget_id", sa.UUID(), nullable=False),
    sa.Column("name", sa.String(length=200), nullable=False),
    sa.Column("allocated_amount", sa.Numeric(precision=18, scale=2), server_default="0", nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.ForeignKeyConstraint(["budget_id"], ["budgets.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
  )
  op.create_index("ix_budget_categories_budget", "budget_categories", ["budget_id"], unique=False)

  op.create_table(
    "site_logs",
    sa.Column("id", sa.UUID(), nullable=False),
    sa.Column("organization_id", sa.UUID(), nullable=False),
    sa.Column("project_id", sa.UUID(), nullable=False),
    sa.Column("log_date", sa.Date(), nullable=False),
    sa.Column("workforce_count", sa.Integer(), nullable=True),
    sa.Column("weather", sa.String(length=255), nullable=True),
    sa.Column("blockers", sa.Text(), nullable=True),
    sa.Column("notes", sa.Text(), nullable=True),
    sa.Column("created_by", sa.UUID(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
  )
  op.create_index("ix_site_logs_org", "site_logs", ["organization_id"], unique=False)
  op.create_index("ix_site_logs_project", "site_logs", ["project_id"], unique=False)
  op.create_index("ix_site_logs_project_date", "site_logs", ["project_id", "log_date"], unique=False)

  op.create_table(
    "procurement_requests",
    sa.Column("id", sa.UUID(), nullable=False),
    sa.Column("organization_id", sa.UUID(), nullable=False),
    sa.Column("project_id", sa.UUID(), nullable=False),
    sa.Column("material_name", sa.String(length=300), nullable=False),
    sa.Column("quantity", sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column("unit", sa.String(length=50), nullable=False),
    sa.Column("estimated_amount", sa.Numeric(precision=18, scale=2), nullable=True),
    sa.Column(
      "status",
      sa.Enum("REQUESTED", "APPROVED", "ORDERED", "RECEIVED", "CANCELLED", name="procurement_status"),
      server_default="REQUESTED",
      nullable=False,
    ),
    sa.Column("needed_by_date", sa.Date(), nullable=True),
    sa.Column("notes", sa.Text(), nullable=True),
    sa.Column("requested_by", sa.UUID(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="SET NULL"),
    sa.PrimaryKeyConstraint("id"),
  )
  op.create_index("ix_procurement_org", "procurement_requests", ["organization_id"], unique=False)
  op.create_index("ix_procurement_project", "procurement_requests", ["project_id"], unique=False)
  op.create_index("ix_procurement_status", "procurement_requests", ["status"], unique=False)

  op.create_table(
    "expenses",
    sa.Column("id", sa.UUID(), nullable=False),
    sa.Column("organization_id", sa.UUID(), nullable=False),
    sa.Column("project_id", sa.UUID(), nullable=False),
    sa.Column("category", sa.String(length=150), nullable=False),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column("expense_date", sa.Date(), nullable=False),
    sa.Column(
      "status",
      sa.Enum("PENDING", "APPROVED", "REJECTED", name="expense_status"),
      server_default="PENDING",
      nullable=False,
    ),
    sa.Column("submitted_by", sa.UUID(), nullable=True),
    sa.Column("reviewed_by", sa.UUID(), nullable=True),
    sa.Column("review_note", sa.Text(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
    sa.ForeignKeyConstraint(["submitted_by"], ["users.id"], ondelete="SET NULL"),
    sa.PrimaryKeyConstraint("id"),
  )
  op.create_index("ix_expenses_org", "expenses", ["organization_id"], unique=False)
  op.create_index("ix_expenses_project", "expenses", ["project_id"], unique=False)
  op.create_index("ix_expenses_status", "expenses", ["status"], unique=False)


def downgrade() -> None:
  op.drop_index("ix_expenses_status", table_name="expenses")
  op.drop_index("ix_expenses_project", table_name="expenses")
  op.drop_index("ix_expenses_org", table_name="expenses")
  op.drop_table("expenses")
  op.execute("DROP TYPE IF EXISTS expense_status")

  op.drop_index("ix_procurement_status", table_name="procurement_requests")
  op.drop_index("ix_procurement_project", table_name="procurement_requests")
  op.drop_index("ix_procurement_org", table_name="procurement_requests")
  op.drop_table("procurement_requests")
  op.execute("DROP TYPE IF EXISTS procurement_status")

  op.drop_index("ix_site_logs_project_date", table_name="site_logs")
  op.drop_index("ix_site_logs_project", table_name="site_logs")
  op.drop_index("ix_site_logs_org", table_name="site_logs")
  op.drop_table("site_logs")

  op.drop_index("ix_budget_categories_budget", table_name="budget_categories")
  op.drop_table("budget_categories")

  op.drop_index("ix_budgets_project", table_name="budgets")
  op.drop_index("ix_budgets_organization", table_name="budgets")
  op.drop_table("budgets")