"""reader tuning: the stored sweeps of the reader's tuned constants

Revision ID: e4b7a9c2d6f1
Revises: d2e8b5a7f1c4
Create Date: 2026-10-21 7:48:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e4b7a9c2d6f1'
down_revision: Union[str, Sequence[str], None] = 'd2e8b5a7f1c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "reading_sweeps"
ORG = "NULLIF(current_setting('app.current_org_id', true), '')::uuid"
ADMIN = "current_setting('app.is_platform_admin', true) = 'true'"
SUPPORT_ORG = "NULLIF(current_setting('app.support_org_id', true), '')::uuid"

def policy_statements(table: str) -> list[str]:
    return [
        f'CREATE POLICY "{table}_org_isolation" ON "{table}" FOR ALL USING (organization_id = {ORG}) WITH CHECK (organization_id = {ORG})',
        f'CREATE POLICY "{table}_support_read" ON "{table}" FOR SELECT USING ({ADMIN} AND organization_id = {SUPPORT_ORG} AND support_grant_active(organization_id))',
    ]

def upgrade() -> None:
    op.create_table(TABLE,
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('drawing_id', sa.UUID(), nullable=False),
        sa.Column('extract_version', sa.Integer(), nullable=False),
        sa.Column('ladder', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('constants', sa.Integer(), nullable=False),
        sa.Column('cells', sa.Integer(), nullable=False),
        sa.Column('changes', sa.Integer(), nullable=False),
        sa.Column('label_count', sa.Integer(), nullable=False),
        sa.Column('labels_stamp', sa.String(length=40), nullable=True),
        sa.Column('seconds', sa.Numeric(precision=10, scale=1), nullable=False),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('decisions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('COMPLETE','PARTIAL')", name='ck_reading_sweeps_status'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name='fk_reading_sweeps_created_by', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['drawing_id', 'organization_id'], ['drawings.id', 'drawings.organization_id'], name='fk_reading_sweeps_drawing_tenant', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_reading_sweeps_drawing_created', TABLE, ['drawing_id', 'created_at'], unique=False)
    op.create_index('ix_reading_sweeps_org_project', TABLE, ['organization_id', 'project_id'], unique=False)
    op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{TABLE}" FORCE ROW LEVEL SECURITY')
    for stmt in policy_statements(TABLE):
        op.execute(stmt)

def downgrade() -> None:
    op.execute(f'DROP POLICY IF EXISTS "{TABLE}_support_read" ON "{TABLE}"')
    op.execute(f'DROP POLICY IF EXISTS "{TABLE}_org_isolation" ON "{TABLE}"')
    op.drop_index('ix_reading_sweeps_org_project', table_name=TABLE)
    op.drop_index('ix_reading_sweeps_drawing_created', table_name=TABLE)
    op.drop_table(TABLE)
