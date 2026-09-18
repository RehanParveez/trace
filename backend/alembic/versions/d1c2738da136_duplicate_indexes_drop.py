"""duplicate indexes drop

Revision ID: d1c2738da136
Revises: a6bc738533da
Create Date: 2026-09-18 06:39:03.887109
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'd1c2738da136'
down_revision: Union[str, Sequence[str], None] = 'a6bc738533da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Budgets
    op.execute("DROP INDEX IF EXISTS ix_budgets_organization_id")
    op.execute("DROP INDEX IF EXISTS ix_budgets_project_id")
    op.execute("DROP INDEX IF EXISTS ix_budget_categories_budget_id")

    op.execute("DROP INDEX IF EXISTS ix_procurement_requests_organization_id")
    op.execute("DROP INDEX IF EXISTS ix_procurement_requests_project_id")

    op.execute("DROP INDEX IF EXISTS ix_expenses_organization_id")
    op.execute("DROP INDEX IF EXISTS ix_expenses_project_id")

    op.execute("DROP INDEX IF EXISTS ix_site_logs_organization_id")
    op.execute("DROP INDEX IF EXISTS ix_site_logs_project_id")
    op.execute("DROP INDEX IF EXISTS ix_site_logs_project")

def downgrade() -> None:
    pass