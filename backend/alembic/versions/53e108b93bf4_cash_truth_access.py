"""cash_truth_access

Revision ID: 53e108b93bf4
Revises: d07b208d648c
Create Date: 2026-10-11 11:40:52.344160
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '53e108b93bf4'
down_revision: Union[str, Sequence[str], None] = 'd07b208d648c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("SELECT set_config('app.is_platform_admin', 'true', true)")

    op.add_column("cash_flow_settings", sa.Column(
        "expected_client_wht_percentage", sa.Numeric(5, 2), nullable=False, server_default="0",
    ))

    op.add_column("subcontractor_bills", sa.Column("cancel_reason", sa.String(500), nullable=True))

    op.add_column("change_orders", sa.Column("client_approved_on", sa.Date(), nullable=True))
    op.add_column("change_orders", sa.Column(
        "extension_of_time_days", sa.Integer(), nullable=False, server_default="0",
    ))

    op.add_column("project_schedules", sa.Column("work_week_days", sa.Integer(), nullable=False, server_default="6"))
    op.add_column("project_schedules", sa.Column(
        "holidays", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb"),
    ))

    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'ATTENTION_DIGEST'")

    op.execute("""
        INSERT INTO permissions (id, key, description)
        SELECT gen_random_uuid(), 'project.view_all',
               'See every project in the company. Without it, a person sees only the projects they have been added to.'
        WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE key = 'project.view_all')
    """)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT rp.role_id, (SELECT id FROM permissions WHERE key = 'project.view_all')
        FROM role_permissions rp
        JOIN permissions p ON p.id = rp.permission_id AND p.key = 'project.read'
        WHERE NOT EXISTS (
            SELECT 1 FROM role_permissions x
            WHERE x.role_id = rp.role_id AND x.permission_id = (SELECT id FROM permissions WHERE key = 'project.view_all')
        )
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE key = 'project.view_all')
    """)
    op.execute("DELETE FROM permissions WHERE key = 'project.view_all'")
    op.drop_column("project_schedules", "holidays")
    op.drop_column("project_schedules", "work_week_days")
    op.drop_column("change_orders", "extension_of_time_days")
    op.drop_column("change_orders", "client_approved_on")
    op.drop_column("subcontractor_bills", "cancel_reason")
    op.drop_column("cash_flow_settings", "expected_client_wht_percentage")