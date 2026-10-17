"""stored_datums and per-elem params

Revision ID: 18e69886fced
Revises: 05a81572e4d3
Create Date: 2026-10-17 15:52:00.923082
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '18e69886fced'
down_revision: Union[str, Sequence[str], None] = '05a81572e4d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('project_datums',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=40), nullable=False),
    sa.Column('source', sa.String(length=8), nullable=False),
    sa.Column('z_mm', sa.Numeric(precision=14, scale=3), nullable=False),
    sa.Column('basis', sa.String(length=20), nullable=True),
    sa.Column('note', sa.String(length=300), nullable=True),
    sa.Column('run_id', sa.UUID(), nullable=True),
    sa.Column('updated_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("source IN ('TYPED','RUN')", name='ck_project_datums_source'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['run_id'], ['calculation_runs.id'], name='fk_project_datums_run', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], name='fk_project_datums_updated_by', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'name', 'source', name='uq_project_datums_name_source')
    )
    op.create_index('ix_project_datums_org_project', 'project_datums', ['organization_id', 'project_id'], unique=False)
    op.create_index(op.f('ix_project_datums_organization_id'), 'project_datums', ['organization_id'], unique=False)
    op.create_table('project_element_parameters',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('element_id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('value', sa.Numeric(precision=14, scale=3), nullable=False),
    sa.Column('label', sa.String(length=120), nullable=True),
    sa.Column('updated_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], name='fk_project_element_parameters_updated_by', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'element_id', 'code', name='uq_project_element_parameters_code')
    )
    op.create_index('ix_project_element_parameters_org_project', 'project_element_parameters', ['organization_id', 'project_id'], unique=False)
    op.create_index(op.f('ix_project_element_parameters_organization_id'), 'project_element_parameters', ['organization_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_project_element_parameters_organization_id'), table_name='project_element_parameters')
    op.drop_index('ix_project_element_parameters_org_project', table_name='project_element_parameters')
    op.drop_table('project_element_parameters')
    op.drop_index(op.f('ix_project_datums_organization_id'), table_name='project_datums')
    op.drop_index('ix_project_datums_org_project', table_name='project_datums')
    op.drop_table('project_datums')
