"""add subcontractor tables

Revision ID: aa03b2f4f9f6
Revises: e8d54566106b
Create Date: 2026-09-22 04:08:21.698739
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'aa03b2f4f9f6'
down_revision: Union[str, Sequence[str], None] = 'e8d54566106b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "subcontractors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("trade_specialization", sa.String(100), nullable=False),
        sa.Column("contact_name", sa.String(200), nullable=True),
        sa.Column("contact_phone", sa.String(30), nullable=True),
        sa.Column("ntn_or_cnic", sa.String(30), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_subcontractors_org", "subcontractors", ["organization_id"])

    op.create_table(
        "subcontract_agreements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subcontractor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subcontractors.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scope_description", sa.Text(), nullable=False),
        sa.Column("contract_value", sa.Numeric(16, 2), nullable=False),
        sa.Column("default_retention_percentage", sa.Numeric(5, 2), nullable=False, server_default="10"),
        sa.Column("default_retention_cap_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Enum("ACTIVE", "COMPLETED", "TERMINATED", name="subcontract_agreement_status"), nullable=False, server_default="ACTIVE"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_subcontract_agreements_org_project", "subcontract_agreements", ["organization_id", "project_id"])
    op.create_index("ix_subcontract_agreements_subcontractor", "subcontract_agreements", ["subcontractor_id"])

    op.create_table(
        "subcontract_agreement_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agreement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subcontract_agreements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("rate", sa.Numeric(16, 2), nullable=False),
    )
    op.create_index("ix_subcontract_agreement_items_agreement", "subcontract_agreement_items", ["agreement_id"])

    op.create_table(
        "subcontractor_bills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agreement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subcontract_agreements.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("bill_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("DRAFT", "ISSUED", "CANCELLED", name="subcontractor_bill_status"), nullable=False, server_default="DRAFT"),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("gross_value_this_period", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("gross_value_cumulative", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("retention_percentage", sa.Numeric(5, 2), nullable=False, server_default="10"),
        sa.Column("retention_cap_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("retention_this_period", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("retention_cumulative", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("other_deductions_amount", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("other_deductions_note", sa.String(500), nullable=True),
        sa.Column("net_payable", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="PKR"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", "agreement_id", "bill_number", name="uq_subcontractor_bill_number"),
    )
    op.create_index("ix_subcontractor_bills_org_project", "subcontractor_bills", ["organization_id", "project_id"])

    op.create_table(
        "subcontractor_bill_line_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subcontractor_bills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agreement_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subcontract_agreement_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("contract_quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("rate", sa.Numeric(16, 2), nullable=False),
        sa.Column("previous_percentage", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("cumulative_percentage", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("this_period_value", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("cumulative_value", sa.Numeric(16, 2), nullable=False, server_default="0"),
    )
    op.create_index("ix_subcontractor_bill_line_items_bill", "subcontractor_bill_line_items", ["bill_id"])

    op.create_table(
        "subcontractor_advances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agreement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subcontract_agreements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("advance_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.String(300), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_subcontractor_advances_org_agreement", "subcontractor_advances", ["organization_id", "agreement_id"])

    op.create_table(
        "subcontractor_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agreement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subcontract_agreements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subcontractor_bills.id", ondelete="SET NULL"), nullable=True),
        sa.Column("gross_amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("advance_recovered_amount", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("net_paid_amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.String(300), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_subcontractor_payments_org_agreement", "subcontractor_payments", ["organization_id", "agreement_id"])

    op.execute("COMMIT")
    op.execute("ALTER TYPE audit_entity_type ADD VALUE IF NOT EXISTS 'SUBCONTRACTOR'")

def downgrade() -> None:
    op.drop_table("subcontractor_payments")
    op.drop_table("subcontractor_advances")
    op.drop_table("subcontractor_bill_line_items")
    op.drop_table("subcontractor_bills")
    op.drop_table("subcontract_agreement_items")
    op.drop_table("subcontract_agreements")
    op.drop_table("subcontractors")
    op.execute("DROP TYPE IF EXISTS subcontractor_bill_status")
    op.execute("DROP TYPE IF EXISTS subcontract_agreement_status")