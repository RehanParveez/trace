"""project expected BOQ: the figures a QS holds for a project, by item family, with a tolerance for each

Revision ID: b3d8f1a6c5e2
Revises: a7c1e9d4b2f6
Create Date: 2026-10-20 01:3:00.000000

After this migration run `python -m scripts.rls_audit --apply`, as for every table that carries an organization_id, so the table is covered by the row level security.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b3d8f1a6c5e2'
down_revision: Union[str, Sequence[str], None] = 'a7c1e9d4b2f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('project_expected_boqs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('source', sa.String(length=255), nullable=True),
    sa.Column('lines', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tolerances', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('default_tolerance_pct', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('updated_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], name='fk_project_expected_boqs_updated_by', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'name', name='uq_project_expected_boqs_name'),
    )
    op.create_index('ix_project_expected_boqs_org_project', 'project_expected_boqs', ['organization_id', 'project_id'], unique=False)
    op.create_index(op.f('ix_project_expected_boqs_organization_id'), 'project_expected_boqs', ['organization_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_project_expected_boqs_organization_id'), table_name='project_expected_boqs')
    op.drop_index('ix_project_expected_boqs_org_project', table_name='project_expected_boqs')
    op.drop_table('project_expected_boqs')
