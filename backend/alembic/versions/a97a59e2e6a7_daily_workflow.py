"""daily_workflow

Revision ID: a97a59e2e6a7
Revises: 5926588b8434
Create Date: 2026-10-11 06:55:40.126942
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a97a59e2e6a7'
down_revision: Union[str, Sequence[str], None] = '5926588b8434'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ADMIN = "current_setting('app.is_platform_admin', true) = 'true'"
ORG = "current_setting('app.current_org_id', true)::uuid"

def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {table}_org_isolation ON {table} "
        f"USING (organization_id = {ORG} OR {ADMIN})"
    )

def upgrade() -> None:
    op.execute("SELECT set_config('app.is_platform_admin', 'true', true)")

    op.add_column("expenses", sa.Column("budget_category_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_expenses_budget_category", "expenses", "budget_categories",
        ["budget_category_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_expenses_budget_category", "expenses", ["budget_category_id"])
    op.execute("""
        UPDATE expenses e
        SET budget_category_id = m.category_id
        FROM (
            SELECT e2.id AS expense_id, (array_agg(bc.id))[1] AS category_id
            FROM expenses e2
            JOIN budgets b ON b.project_id = e2.project_id AND b.organization_id = e2.organization_id
            JOIN budget_categories bc ON bc.budget_id = b.id
                 AND lower(trim(bc.name)) = lower(trim(e2.category))
            GROUP BY e2.id
            HAVING count(bc.id) = 1
        ) m
        WHERE e.id = m.expense_id
    """)

    op.add_column("procurement_requests", sa.Column("supplier_name", sa.String(200), nullable=True))
    op.create_table(
        "procurement_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("supplier_name", sa.String(200), nullable=True),
        sa.Column("invoice_number", sa.String(100), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("notes", sa.String(300), nullable=True),
        sa.Column("recorded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("void_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["procurement_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["voided_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint("quantity > 0", name="ck_procurement_delivery_quantity_positive"),
        sa.CheckConstraint("amount IS NULL OR amount >= 0", name="ck_procurement_delivery_amount_non_negative"),
    )
    op.create_index("ix_procurement_deliveries_org_project", "procurement_deliveries", ["organization_id", "project_id"])
    op.create_index("ix_procurement_deliveries_request", "procurement_deliveries", ["request_id"])
    op.create_index("ix_procurement_deliveries_project_date", "procurement_deliveries", ["project_id", "received_date"])
    op.execute("""
        INSERT INTO procurement_deliveries
            (id, organization_id, project_id, request_id, received_date, quantity)
        SELECT gen_random_uuid(), r.organization_id, r.project_id, r.id,
               (r.updated_at AT TIME ZONE 'Asia/Karachi')::date, r.quantity
        FROM procurement_requests r
        WHERE r.status = 'RECEIVED'
    """)
    _enable_rls("procurement_deliveries")

    op.add_column("site_logs", sa.Column("work_done", sa.Text(), nullable=True))
    op.add_column("site_logs", sa.Column("client_instructions", sa.Text(), nullable=True))

    op.create_table(
        "whatsapp_senders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone_number", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("default_project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["default_project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "phone_number", name="uq_whatsapp_senders_org_phone"),
    )
    op.create_index("ix_whatsapp_senders_org", "whatsapp_senders", ["organization_id"])
    _enable_rls("whatsapp_senders")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS whatsapp_senders_org_isolation ON whatsapp_senders")
    op.drop_index("ix_whatsapp_senders_org", table_name="whatsapp_senders")
    op.drop_table("whatsapp_senders")

    op.drop_column("site_logs", "client_instructions")
    op.drop_column("site_logs", "work_done")

    op.execute("DROP POLICY IF EXISTS procurement_deliveries_org_isolation ON procurement_deliveries")
    op.drop_index("ix_procurement_deliveries_project_date", table_name="procurement_deliveries")
    op.drop_index("ix_procurement_deliveries_request", table_name="procurement_deliveries")
    op.drop_index("ix_procurement_deliveries_org_project", table_name="procurement_deliveries")
    op.drop_table("procurement_deliveries")
    op.drop_column("procurement_requests", "supplier_name")

    op.drop_index("ix_expenses_budget_category", table_name="expenses")
    op.drop_constraint("fk_expenses_budget_category", "expenses", type_="foreignkey")
    op.drop_column("expenses", "budget_category_id")