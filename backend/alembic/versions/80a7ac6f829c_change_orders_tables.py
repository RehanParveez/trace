"""change_orders tables

Revision ID: 80a7ac6f829c
Revises: 19dd356d101f
Create Date: 2026-09-25 03:21:30.313354
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '80a7ac6f829c'
down_revision: Union[str, Sequence[str], None] = '19dd356d101f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    op.create_table(
        "change_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("boq_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("boq_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("change_order_number", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.Enum("ADDITION", "OMISSION", "VARIATION", name="change_order_type"), nullable=False),
        sa.Column("status", sa.Enum("DRAFT", "APPROVED", "REJECTED", "CANCELLED", name="change_order_status"), nullable=False, server_default="DRAFT"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("client_reference", sa.String(100), nullable=True),
        sa.Column("value_impact", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="PKR"),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", "project_id", "change_order_number", name="uq_change_order_number"),
    )
    op.create_index("ix_change_orders_org_project", "change_orders", ["organization_id", "project_id"])

    op.create_table(
        "change_order_line_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("change_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("change_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("boq_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("boq_items.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit_rate", sa.Numeric(16, 2), nullable=True),
        sa.Column("realized_value_impact", sa.Numeric(16, 2), nullable=True),
        sa.Column("created_boq_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("boq_items.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_change_order_line_items_order", "change_order_line_items", ["change_order_id"])

    op.execute("COMMIT")
    op.execute("ALTER TYPE audit_entity_type ADD VALUE IF NOT EXISTS 'CHANGE_ORDER'")

def downgrade() -> None:
    op.drop_table("change_order_line_items")
    op.drop_table("change_orders")
    op.execute("DROP TYPE IF EXISTS change_order_status")
    op.execute("DROP TYPE IF EXISTS change_order_type")