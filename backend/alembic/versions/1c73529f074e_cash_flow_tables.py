"""cash_flow tables

Revision ID: 1c73529f074e
Revises: fdfe622e666a
Create Date: 2026-09-27 13:01:49.736976
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '1c73529f074e'
down_revision: Union[str, Sequence[str], None] = 'fdfe622e666a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "cash_flow_settings",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("procurement_payment_days", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("subcontractor_payment_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("client_collection_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("labour_lookback_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", name="uq_cash_flow_settings_org"),
    )

    op.add_column("running_bills", sa.Column("collected_amount", sa.Numeric(18, 2), nullable=False, server_default="0"))
    op.add_column("running_bills", sa.Column("fully_collected_at", sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column("running_bills", "fully_collected_at")
    op.drop_column("running_bills", "collected_amount")
    op.drop_table("cash_flow_settings")