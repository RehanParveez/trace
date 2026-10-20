"""project one-total rules: which source counts for a mark, a kind of member or a work item

Revision ID: a7c1e9d4b2f6
Revises: a1d7c4e9b305
Create Date: 2026-10-20 11:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a7c1e9d4b2f6'
down_revision: Union[str, Sequence[str], None] = 'a1d7c4e9b305'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('project_one_total_rules',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.Column('mark', sa.String(length=60), nullable=False, server_default=''),
    sa.Column('level_name', sa.String(length=200), nullable=False, server_default=''),
    sa.Column('prefer', sa.String(length=16), nullable=False),
    sa.Column('note', sa.String(length=500), nullable=True),
    sa.Column('updated_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], name='fk_project_one_total_rules_updated_by', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'kind', 'mark', 'level_name', name='uq_project_one_total_rules_scope'),
    sa.CheckConstraint("prefer IN ('DRAWING', 'MODEL', 'BOTH')", name='ck_project_one_total_rules_prefer'),
    )
    op.create_index('ix_project_one_total_rules_org_project', 'project_one_total_rules', ['organization_id', 'project_id'], unique=False)
    op.create_index(op.f('ix_project_one_total_rules_organization_id'), 'project_one_total_rules', ['organization_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_project_one_total_rules_organization_id'), table_name='project_one_total_rules')
    op.drop_index('ix_project_one_total_rules_org_project', table_name='project_one_total_rules')
    op.drop_table('project_one_total_rules')
