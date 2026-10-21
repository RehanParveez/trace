"""detail-only marks: the decisions a person makes about a mark that has a detail and no instance on the plans

Revision ID: d2e8b5a7f1c4
Revises: c9a4e7b1d3f5
Create Date: 2026-10-21 20:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd2e8b5a7f1c4'
down_revision: Union[str, Sequence[str], None] = 'c9a4e7b1d3f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "detail_mark_decisions"
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
        sa.Column('kind', sa.String(length=12), nullable=False),
        sa.Column('mark', sa.String(length=60), nullable=False),
        sa.Column('sheet_id', sa.UUID(), nullable=True),
        sa.Column('ckey', sa.String(length=40), nullable=True),
        sa.Column('value_mm', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('basis', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('decided_by_user_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("kind IN ('COLUMN_MARK','BEAM_DEPTH')", name='ck_detail_mark_decisions_kind'),
        sa.ForeignKeyConstraint(['decided_by_user_id'], ['users.id'], name='fk_detail_mark_decisions_decided_by', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['drawing_id', 'organization_id'], ['drawings.id', 'drawings.organization_id'], name='fk_detail_mark_decisions_drawing_tenant', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sheet_id', 'organization_id'], ['takeoff_sheets.id', 'takeoff_sheets.organization_id'], name='fk_detail_mark_decisions_sheet_tenant', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('drawing_id', 'kind', 'mark', 'sheet_id', 'ckey', name='uq_detail_mark_decisions_key'),
    )
    op.create_index('ix_detail_mark_decisions_drawing', TABLE, ['drawing_id', 'kind'], unique=False)
    op.create_index('ix_detail_mark_decisions_org_project', TABLE, ['organization_id', 'project_id'], unique=False)
    op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{TABLE}" FORCE ROW LEVEL SECURITY')
    for stmt in policy_statements(TABLE):
        op.execute(stmt)

def downgrade() -> None:
    op.execute(f'DROP POLICY IF EXISTS "{TABLE}_support_read" ON "{TABLE}"')
    op.execute(f'DROP POLICY IF EXISTS "{TABLE}_org_isolation" ON "{TABLE}"')
    op.drop_index('ix_detail_mark_decisions_org_project', table_name=TABLE)
    op.drop_index('ix_detail_mark_decisions_drawing', table_name=TABLE)
    op.drop_table(TABLE)
