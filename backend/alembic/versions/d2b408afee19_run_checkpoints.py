"""run checkpoints

Revision ID: d2b408afee19
Revises: 604a51068871
Create Date: 2026-10-18 04:51:10.321152
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd2b408afee19'
down_revision: Union[str, Sequence[str], None] = '604a51068871'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'run_checkpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kind', sa.String(length=10), nullable=False),
        sa.Column('label', sa.String(length=200), server_default='', nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("kind IN ('COMPARE','RANGE')", name='ck_run_checkpoints_kind'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id', 'organization_id'], ['calculation_runs.id', 'calculation_runs.organization_id'], name='fk_run_checkpoints_run_tenant', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', 'kind', 'label', name='uq_run_checkpoints_run_kind_label'),
    )
    op.create_index('ix_run_checkpoints_org_project_kind', 'run_checkpoints', ['organization_id', 'project_id', 'kind'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_run_checkpoints_org_project_kind', table_name='run_checkpoints')
    op.drop_table('run_checkpoints')