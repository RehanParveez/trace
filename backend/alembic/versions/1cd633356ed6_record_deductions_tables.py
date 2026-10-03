"""record_deductions_tables

Revision ID: 1cd633356ed6
Revises: 8c76d2c5890e
Create Date: 2026-10-03 06:39:11.886089
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '1cd633356ed6'
down_revision: Union[str, Sequence[str], None] = '8c76d2c5890e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEDUCTION_TYPES = "'OVERLAP_ALLOCATION','EXTENT_TRIMMING','VOID_DEDUCTION','MATERIAL_SUBSTITUTION','MEASUREMENT_CONVENTION'"
_CANONICAL_UNITS = "'m3','m2','m','kg','nos'"

def upgrade() -> None:
    op.create_table(
        "ledger_deductions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_solid_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_solid_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deduction_type", sa.String(length=30), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=20, scale=6), nullable=False, server_default="0"),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("rule_code", sa.String(length=80), nullable=False),
        sa.Column("rule_version", sa.String(length=40), nullable=True),
        sa.Column("geometry", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("engine_version", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_ledger_deductions_id_org"),
        sa.ForeignKeyConstraint(
            ["run_id", "organization_id"],
            ["calculation_runs.id", "calculation_runs.organization_id"],
            name="fk_ledger_deductions_run_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["from_solid_id", "organization_id"],
            ["quantity_solids.id", "quantity_solids.organization_id"],
            name="fk_ledger_deductions_from_solid_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["to_solid_id", "organization_id"],
            ["quantity_solids.id", "quantity_solids.organization_id"],
            name="fk_ledger_deductions_to_solid_tenant",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(f"deduction_type IN ({_DEDUCTION_TYPES})", name="ck_ledger_deductions_type"),
        sa.CheckConstraint("quantity >= 0", name="ck_ledger_deductions_non_negative"),
        sa.CheckConstraint(f"unit IN ({_CANONICAL_UNITS})", name="ck_ledger_deductions_unit"),
        sa.CheckConstraint(
            "to_solid_id IS NULL OR to_solid_id <> from_solid_id",
            name="ck_ledger_deductions_distinct_solids",
        ),
        sa.CheckConstraint(
            "deduction_type <> 'OVERLAP_ALLOCATION' OR to_solid_id IS NOT NULL",
            name="ck_ledger_deductions_overlap_needs_owner",
        ),
    )
    op.create_index("ix_ledger_deductions_run_from", "ledger_deductions", ["run_id", "from_solid_id"], unique=False)
    op.create_index("ix_ledger_deductions_run_to", "ledger_deductions", ["run_id", "to_solid_id"], unique=False)
    op.create_index("ix_ledger_deductions_run_type", "ledger_deductions", ["run_id", "deduction_type"], unique=False)

    op.create_table(
        "staged_ledger_deductions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_solid_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_solid_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deduction_type", sa.String(length=30), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=20, scale=6), nullable=False, server_default="0"),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("rule_code", sa.String(length=80), nullable=False),
        sa.Column("rule_version", sa.String(length=40), nullable=True),
        sa.Column("geometry", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("engine_version", sa.String(length=30), nullable=False),
        sa.Column("stage", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["run_id", "organization_id"],
            ["calculation_runs.id", "calculation_runs.organization_id"],
            name="fk_staged_ledger_deductions_run_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["from_solid_id", "organization_id"],
            ["staged_quantity_solids.id", "staged_quantity_solids.organization_id"],
            name="fk_staged_ledger_deductions_from_solid_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["to_solid_id", "organization_id"],
            ["staged_quantity_solids.id", "staged_quantity_solids.organization_id"],
            name="fk_staged_ledger_deductions_to_solid_tenant",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(f"deduction_type IN ({_DEDUCTION_TYPES})", name="ck_staged_ledger_deductions_type"),
        sa.CheckConstraint("quantity >= 0", name="ck_staged_ledger_deductions_non_negative"),
        sa.CheckConstraint(f"unit IN ({_CANONICAL_UNITS})", name="ck_staged_ledger_deductions_unit"),
        sa.CheckConstraint(
            "to_solid_id IS NULL OR to_solid_id <> from_solid_id",
            name="ck_staged_ledger_deductions_distinct_solids",
        ),
        sa.CheckConstraint(
            "deduction_type <> 'OVERLAP_ALLOCATION' OR to_solid_id IS NOT NULL",
            name="ck_staged_ledger_deductions_overlap_needs_owner",
        ),
    )
    op.create_index(
        "ix_staged_ledger_deductions_run_stage",
        "staged_ledger_deductions",
        ["run_id", "stage"],
        unique=False,
    )

def downgrade() -> None:
    op.drop_index("ix_staged_ledger_deductions_run_stage", table_name="staged_ledger_deductions")
    op.drop_table("staged_ledger_deductions")

    op.drop_index("ix_ledger_deductions_run_type", table_name="ledger_deductions")
    op.drop_index("ix_ledger_deductions_run_to", table_name="ledger_deductions")
    op.drop_index("ix_ledger_deductions_run_from", table_name="ledger_deductions")
    op.drop_table("ledger_deductions")