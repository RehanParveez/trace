"""add running_bills tables

Revision ID: d200f1b1c6f0
Revises: 2da069d18fcc
Create Date: 2026-09-21 11:30:01.268972
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd200f1b1c6f0'
down_revision: Union[str, Sequence[str], None] = '2da069d18fcc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "running_bills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("boq_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("boq_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("bill_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("DRAFT", "ISSUED", "CANCELLED", name="running_bill_status"), nullable=False, server_default="DRAFT"),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("gross_value_this_period", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("gross_value_cumulative", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("retention_percentage", sa.Numeric(5, 2), nullable=False, server_default="10"),
        sa.Column("retention_cap_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("retention_this_period", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("retention_cumulative", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("advance_recovery_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("other_deductions_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("other_deductions_note", sa.String(500), nullable=True),
        sa.Column("net_payable", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="PKR"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", "project_id", "bill_number", name="uq_running_bill_number"),
    )
    op.create_index("ix_running_bills_org_project", "running_bills", ["organization_id", "project_id"])

    op.create_table(
        "running_bill_line_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("running_bills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("boq_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("boq_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("material_name", sa.String(300), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("contract_quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit_rate", sa.Numeric(18, 2), nullable=False),
        sa.Column("previous_percentage", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("cumulative_percentage", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("previous_quantity", sa.Numeric(18, 3), nullable=False, server_default="0"),
        sa.Column("cumulative_quantity", sa.Numeric(18, 3), nullable=False, server_default="0"),
        sa.Column("this_period_quantity", sa.Numeric(18, 3), nullable=False, server_default="0"),
        sa.Column("previous_value", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("cumulative_value", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("this_period_value", sa.Numeric(18, 2), nullable=False, server_default="0"),
    )
    op.create_index("ix_running_bill_line_items_bill", "running_bill_line_items", ["bill_id"])

    op.execute("COMMIT")
    op.execute("ALTER TYPE audit_entity_type ADD VALUE IF NOT EXISTS 'RUNNING_BILL'")

def downgrade() -> None:
    op.drop_table("running_bill_line_items")
    op.drop_table("running_bills")
    op.execute("DROP TYPE IF EXISTS running_bill_status")