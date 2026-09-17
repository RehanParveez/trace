"""rls policies for budgets, expenses, procurement, audit

Revision ID: 06c3885d71fc
Revises: 4bf9067223ec
Create Date: 2026-09-17 05:06:38.564253
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '06c3885d71fc'
down_revision: Union[str, Sequence[str], None] = '4bf9067223ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RLS_TABLES = ["budgets", "budget_categories", "expenses", "procurement_requests", "audit_log"]

def upgrade() -> None:
    op.add_column(
        "budget_categories",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute("""
        UPDATE budget_categories bc
        SET organization_id = b.organization_id
        FROM budgets b
        WHERE bc.budget_id = b.id
    """)
    op.alter_column("budget_categories", "organization_id", nullable=False)
    op.create_foreign_key(
        "fk_budget_categories_organization",
        "budget_categories", "organizations",
        ["organization_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index(
        "ix_budget_categories_organization",
        "budget_categories", ["organization_id"],
    )

    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_org_isolation ON {table}
            USING (
                organization_id = current_setting('app.current_org_id', true)::uuid
                OR current_setting('app.is_platform_admin', true) = 'true'
            )
        """)

def downgrade() -> None:
    for table in RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_budget_categories_organization", table_name="budget_categories")
    op.drop_constraint("fk_budget_categories_organization", "budget_categories", type_="foreignkey")
    op.drop_column("budget_categories", "organization_id")