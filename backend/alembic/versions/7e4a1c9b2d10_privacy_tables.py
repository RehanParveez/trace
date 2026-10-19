"""privacy tables: organization keys, support access grants, data exports, deletion requests

Revision ID: 7e4a1c9b2d10
Revises: d2b408afee19
Create Date: 2026-10-19 06:07:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '7e4a1c9b2d10'
down_revision: Union[str, Sequence[str], None] = 'd2b408afee19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'organization_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('wrapped_dek', sa.LargeBinary(), nullable=False),
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('key_ref', sa.String(length=255), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('retired_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'version', name='uq_organization_keys_org_version'),
    )
    op.create_index('ix_organization_keys_organization_id', 'organization_keys', ['organization_id'], unique=False)

    op.create_table(
        'support_access_grants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('granted_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reason', sa.String(length=500), nullable=False),
        sa.Column('starts_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('expires_at > starts_at', name='ck_support_grant_positive'),
        sa.CheckConstraint("expires_at <= starts_at + interval '72 hours'", name='ck_support_grant_max_72h'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['revoked_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_support_access_grants_organization_id', 'support_access_grants', ['organization_id'], unique=False)
    op.create_index('ix_support_grants_org_expires', 'support_access_grants', ['organization_id', 'expires_at'], unique=False)

    op.create_table(
        'data_export_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requested_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('storage_key', sa.String(length=500), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('table_count', sa.Integer(), nullable=True),
        sa.Column('row_count', sa.BigInteger(), nullable=True),
        sa.Column('file_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_data_export_jobs_organization_id', 'data_export_jobs', ['organization_id'], unique=False)
    op.create_index('ix_data_export_jobs_org_created', 'data_export_jobs', ['organization_id', 'created_at'], unique=False)

    op.create_table(
        'organization_deletion_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requested_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['cancelled_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_organization_deletion_requests_organization_id', 'organization_deletion_requests', ['organization_id'], unique=False)
    op.create_index('uq_org_deletion_one_pending', 'organization_deletion_requests', ['organization_id'], unique=True,
                    postgresql_where=sa.text("status IN ('PENDING','EXECUTING')"))
    
    with op.get_context().autocommit_block():
        for value in ('SUPPORT_ACCESS', 'DATA_EXPORT', 'DATA_DELETION'):
            op.execute(f"ALTER TYPE audit_entity_type ADD VALUE IF NOT EXISTS '{value}'")

def downgrade() -> None:
    op.drop_index('uq_org_deletion_one_pending', table_name='organization_deletion_requests')
    op.drop_index('ix_organization_deletion_requests_organization_id', table_name='organization_deletion_requests')
    op.drop_table('organization_deletion_requests')
    op.drop_index('ix_data_export_jobs_org_created', table_name='data_export_jobs')
    op.drop_index('ix_data_export_jobs_organization_id', table_name='data_export_jobs')
    op.drop_table('data_export_jobs')
    op.drop_index('ix_support_grants_org_expires', table_name='support_access_grants')
    op.drop_index('ix_support_access_grants_organization_id', table_name='support_access_grants')
    op.drop_table('support_access_grants')
    op.drop_index('ix_organization_keys_organization_id', table_name='organization_keys')
    op.drop_table('organization_keys')
