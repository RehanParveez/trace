"""bank_guarantees tables

Revision ID: fdfe622e666a
Revises: d89b0712838c
Create Date: 2026-09-27 05:05:02.351938
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'fdfe622e666a'
down_revision: Union[str, Sequence[str], None] = 'd89b0712838c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bank_guarantees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("holder_type", sa.Enum("CLIENT", "SUBCONTRACTOR", name="bank_guarantee_holder_type"), nullable=False),
        sa.Column("boq_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("boq_versions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("agreement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subcontract_agreements.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("purpose", sa.Enum("RETENTION", name="bank_guarantee_purpose"), nullable=False, server_default="RETENTION"),
        sa.Column("guarantee_number", sa.String(100), nullable=False),
        sa.Column("issuing_bank", sa.String(200), nullable=False),
        sa.Column("amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="PKR"),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Enum("ACTIVE", "RENEWED", "RELEASED", "CALLED", name="bank_guarantee_status"), nullable=False, server_default="ACTIVE"),
        sa.Column("renewed_from_guarantee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bank_guarantees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_bank_guarantees_org_project", "bank_guarantees", ["organization_id", "project_id"])
    op.create_index("ix_bank_guarantees_agreement", "bank_guarantees", ["agreement_id"])
    op.create_index("ix_bank_guarantees_boq_version", "bank_guarantees", ["boq_version_id"])

    op.add_column("running_bills", sa.Column("retention_secured_by_guarantee", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("subcontractor_bills", sa.Column("retention_secured_by_guarantee", sa.Boolean(), nullable=False, server_default="false"))

    op.execute("COMMIT")
    op.execute("ALTER TYPE audit_entity_type ADD VALUE IF NOT EXISTS 'BANK_GUARANTEE'")

def downgrade() -> None:
    op.drop_column("subcontractor_bills", "retention_secured_by_guarantee")
    op.drop_column("running_bills", "retention_secured_by_guarantee")
    op.drop_table("bank_guarantees")
    op.execute("DROP TYPE IF EXISTS bank_guarantee_status")
    op.execute("DROP TYPE IF EXISTS bank_guarantee_purpose")
    op.execute("DROP TYPE IF EXISTS bank_guarantee_holder_type")