"""sales_tax tables

Revision ID: 6f408575726f
Revises: ce63f695609e
Create Date: 2026-09-26 15:23:59.227485
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '6f408575726f'
down_revision: Union[str, Sequence[str], None] = 'ce63f695609e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "sales_tax_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("authority", sa.Enum("PRA", "SRB", "KPRA", "BRA", "ICT", name="sales_tax_authority"), nullable=False),
        sa.Column("rate_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sales_tax_rates_org_authority", "sales_tax_rates", ["organization_id", "authority"])

    op.create_table(
        "sales_tax_charges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.Enum("RUNNING_BILL", "SUBCONTRACTOR_BILL", name="sales_tax_source_type"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("authority", sa.Enum("PRA", "SRB", "KPRA", "BRA", "ICT", name="sales_tax_authority"), nullable=False),
        sa.Column("rate_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("taxable_amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("charge_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="PKR"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sales_tax_charges_org_project", "sales_tax_charges", ["organization_id", "project_id"])
    op.create_index("ix_sales_tax_charges_source", "sales_tax_charges", ["source_type", "source_id"])

    op.add_column("running_bills", sa.Column("sales_tax_authority", sa.String(10), nullable=True))
    op.add_column("running_bills", sa.Column("sales_tax_rate_percentage", sa.Numeric(5, 2), nullable=True))
    op.add_column("running_bills", sa.Column("sales_tax_amount", sa.Numeric(18, 2), nullable=False, server_default="0"))

    op.add_column("subcontractor_bills", sa.Column("sales_tax_authority", sa.String(10), nullable=True))
    op.add_column("subcontractor_bills", sa.Column("sales_tax_rate_percentage", sa.Numeric(5, 2), nullable=True))
    op.add_column("subcontractor_bills", sa.Column("sales_tax_amount", sa.Numeric(16, 2), nullable=False, server_default="0"))

def downgrade() -> None:
    op.drop_column("subcontractor_bills", "sales_tax_amount")
    op.drop_column("subcontractor_bills", "sales_tax_rate_percentage")
    op.drop_column("subcontractor_bills", "sales_tax_authority")
    op.drop_column("running_bills", "sales_tax_amount")
    op.drop_column("running_bills", "sales_tax_rate_percentage")
    op.drop_column("running_bills", "sales_tax_authority")
    op.drop_table("sales_tax_charges")
    op.execute("DROP TYPE IF EXISTS sales_tax_source_type")
    op.drop_table("sales_tax_rates")
    op.execute("DROP TYPE IF EXISTS sales_tax_authority")