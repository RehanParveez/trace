"""integ wht & mater_stock tables

Revision ID: 7df245a018d7
Revises: aa03b2f4f9f6
Create Date: 2026-09-22 14:35:43.022728
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '7df245a018d7'
down_revision: Union[str, Sequence[str], None] = 'aa03b2f4f9f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "withholding_tax_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.Enum("GOODS_SUPPLY", "SERVICES", "CONTRACTS_EXECUTION", name="wht_category"), nullable=False),
        sa.Column("filer_rate_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("non_filer_rate_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_wht_rates_org_category", "withholding_tax_rates", ["organization_id", "category"])

    op.create_table(
        "withholding_tax_deductions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.Enum("SUBCONTRACTOR_PAYMENT", "LABOUR_PAYMENT", name="wht_source_type"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payee_name", sa.String(200), nullable=False),
        sa.Column("payee_ntn_or_cnic", sa.String(30), nullable=True),
        sa.Column("category", sa.Enum("GOODS_SUPPLY", "SERVICES", "CONTRACTS_EXECUTION", name="wht_category"), nullable=False),
        sa.Column("gross_amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("rate_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("is_filer", sa.Boolean(), nullable=False),
        sa.Column("deducted_amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("deduction_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="PKR"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_wht_deductions_org_project", "withholding_tax_deductions", ["organization_id", "project_id"])
    op.create_index("ix_wht_deductions_source", "withholding_tax_deductions", ["source_type", "source_id"])

    op.create_table(
        "material_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_name", sa.String(200), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("issue_type", sa.Enum("ISSUED", "WASTAGE", name="material_issue_type"), nullable=False),
        sa.Column("issued_to", sa.String(200), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.String(300), nullable=True),
        sa.Column("recorded_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_material_issues_org_project", "material_issues", ["organization_id", "project_id"])

    op.add_column("subcontractors", sa.Column("is_active_taxpayer", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("subcontractor_payments", sa.Column("wht_category", sa.String(30), nullable=True))
    op.add_column("subcontractor_payments", sa.Column("wht_rate_percentage", sa.Numeric(5, 2), nullable=True))
    op.add_column("subcontractor_payments", sa.Column("wht_deducted_amount", sa.Numeric(16, 2), nullable=False, server_default="0"))

    op.add_column("labour_sources", sa.Column("is_active_taxpayer", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("labour_payments", sa.Column("wht_category", sa.String(30), nullable=True))
    op.add_column("labour_payments", sa.Column("wht_rate_percentage", sa.Numeric(5, 2), nullable=True))
    op.add_column("labour_payments", sa.Column("wht_deducted_amount", sa.Numeric(14, 2), nullable=False, server_default="0"))

    op.execute("COMMIT")
    op.execute("ALTER TYPE audit_entity_type ADD VALUE IF NOT EXISTS 'WITHHOLDING_TAX'")
    op.execute("COMMIT")
    op.execute("ALTER TYPE audit_entity_type ADD VALUE IF NOT EXISTS 'MATERIAL_STOCK'")

def downgrade() -> None:
    op.drop_column("labour_payments", "wht_deducted_amount")
    op.drop_column("labour_payments", "wht_rate_percentage")
    op.drop_column("labour_payments", "wht_category")
    op.drop_column("labour_sources", "is_active_taxpayer")
    op.drop_column("subcontractor_payments", "wht_deducted_amount")
    op.drop_column("subcontractor_payments", "wht_rate_percentage")
    op.drop_column("subcontractor_payments", "wht_category")
    op.drop_column("subcontractors", "is_active_taxpayer")
    op.drop_table("material_issues")
    op.execute("DROP TYPE IF EXISTS material_issue_type")
    op.drop_table("withholding_tax_deductions")
    op.drop_table("withholding_tax_rates")
    op.execute("DROP TYPE IF EXISTS wht_source_type")
    op.execute("DROP TYPE IF EXISTS wht_category")