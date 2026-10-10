"""billing_integrity

Revision ID: 5926588b8434
Revises: 0a7940f64eed
Create Date: 2026-10-10 13:13:56.815695
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '5926588b8434'
down_revision: Union[str, Sequence[str], None] = '0a7940f64eed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("running_bills", sa.Column("cancel_reason", sa.String(500), nullable=True))
    op.add_column(
        "running_bills",
        sa.Column("previous_bill_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_running_bills_previous_bill", "running_bills", "running_bills",
        ["previous_bill_id"], ["id"], ondelete="SET NULL",
    )
    op.execute("""
        UPDATE running_bills rb
        SET previous_bill_id = (
            SELECT p.id FROM running_bills p
            WHERE p.organization_id = rb.organization_id
              AND p.project_id = rb.project_id
              AND p.boq_version_id = rb.boq_version_id
              AND p.status = 'ISSUED'
              AND p.bill_number < rb.bill_number
            ORDER BY p.bill_number DESC
            LIMIT 1
        )
    """)

    op.create_table(
        "running_bill_collections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bill_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_received", sa.Numeric(18, 2), nullable=False),
        sa.Column("client_wht_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("credited_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("collection_date", sa.Date(), nullable=False),
        sa.Column("reference", sa.String(120), nullable=True),
        sa.Column("idempotency_key", sa.String(100), nullable=True),
        sa.Column("recorded_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("void_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bill_id"], ["running_bills.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["voided_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("amount_received >= 0", name="ck_rb_collection_amount_non_negative"),
        sa.CheckConstraint("client_wht_amount >= 0", name="ck_rb_collection_wht_non_negative"),
        sa.CheckConstraint("credited_amount > 0", name="ck_rb_collection_credited_positive"),
    )
    op.create_index("ix_rb_collections_org_bill", "running_bill_collections", ["organization_id", "bill_id"])
    op.create_index(
        "uq_rb_collection_idempotency", "running_bill_collections",
        ["organization_id", "bill_id", "idempotency_key"],
        unique=True, postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.execute("""
        INSERT INTO running_bill_collections
            (id, organization_id, bill_id, project_id, amount_received, client_wht_amount,
             credited_amount, collection_date, reference, recorded_by_user_id)
        SELECT gen_random_uuid(), organization_id, id, project_id, collected_amount, 0,
               collected_amount, COALESCE(fully_collected_at::date, issued_at::date, created_at::date),
               'Opening balance (collected before collection history existed)', created_by_user_id
        FROM running_bills
        WHERE collected_amount > 0
    """)

    op.execute("ALTER TABLE running_bill_collections ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE running_bill_collections FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY running_bill_collections_org_isolation ON running_bill_collections
        USING (
            organization_id = current_setting('app.current_org_id', true)::uuid
            OR current_setting('app.is_platform_admin', true) = 'true'
        )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS running_bill_collections_org_isolation ON running_bill_collections")
    op.drop_index("uq_rb_collection_idempotency", table_name="running_bill_collections")
    op.drop_index("ix_rb_collections_org_bill", table_name="running_bill_collections")
    op.drop_table("running_bill_collections")
    op.drop_constraint("fk_running_bills_previous_bill", "running_bills", type_="foreignkey")
    op.drop_column("running_bills", "previous_bill_id")
    op.drop_column("running_bills", "cancel_reason")