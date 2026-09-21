"""add labout tables

Revision ID: e8d54566106b
Revises: d200f1b1c6f0
Create Date: 2026-09-21 16:44:05.339081
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e8d54566106b'
down_revision: Union[str, Sequence[str], None] = 'd200f1b1c6f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:

    op.create_table(
        'labour_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'organization_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column(
            'source_type',
            sa.Enum(
                'DIRECT',
                'CONTRACTOR',
                name='labour_source_type',
            ),
            nullable=False,
        ),
        sa.Column('contact_name', sa.String(length=200), nullable=True),
        sa.Column('contact_phone', sa.String(length=30), nullable=True),
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=False,
            server_default='true',
        ),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['organization_id'],
            ['organizations.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index(
        'ix_labour_sources_org',
        'labour_sources',
        ['organization_id'],
        unique=False,
    )

    op.create_table(
        'labour_workers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'organization_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            'source_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('trade', sa.String(length=100), nullable=False),
        sa.Column('cnic', sa.String(length=20), nullable=True),
        sa.Column('phone', sa.String(length=30), nullable=True),
        sa.Column(
            'default_daily_rate',
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=False,
            server_default='true',
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['organization_id'],
            ['organizations.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['source_id'],
            ['labour_sources.id'],
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index(
        'ix_labour_workers_org_source',
        'labour_workers',
        ['organization_id', 'source_id'],
        unique=False,
    )

    op.create_table(
        'labour_deployments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'organization_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            'project_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            'source_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            'worker_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column('trade', sa.String(length=100), nullable=False),
        sa.Column(
            'daily_rate',
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column(
            'status',
            sa.Enum(
                'ACTIVE',
                'ENDED',
                name='labour_deployment_status',
            ),
            nullable=False,
            server_default='ACTIVE',
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['organization_id'],
            ['organizations.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['project_id'],
            ['projects.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['source_id'],
            ['labour_sources.id'],
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['worker_id'],
            ['labour_workers.id'],
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index(
        'ix_labour_deployments_org_project',
        'labour_deployments',
        ['organization_id', 'project_id'],
        unique=False,
    )

    op.create_index(
        'ix_labour_deployments_source',
        'labour_deployments',
        ['source_id'],
        unique=False,
    )

    op.create_index(
        'ix_labour_deployments_worker',
        'labour_deployments',
        ['worker_id'],
        unique=False,
    )

    op.create_table(
        'labour_attendance',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'organization_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            'project_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            'deployment_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            'attendance_date',
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            'units_present',
            sa.Numeric(precision=6, scale=2),
            nullable=False,
        ),
        sa.Column(
            'notes',
            sa.String(length=300),
            nullable=True,
        ),
        sa.Column(
            'recorded_by_user_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['deployment_id'],
            ['labour_deployments.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['organization_id'],
            ['organizations.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['project_id'],
            ['projects.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['recorded_by_user_id'],
            ['users.id'],
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'deployment_id',
            'attendance_date',
            name='uq_labour_attendance_deployment_date',
        ),
    )

    op.create_index(
        'ix_labour_attendance_org_project_date',
        'labour_attendance',
        ['organization_id', 'project_id', 'attendance_date'],
        unique=False,
    )

    op.create_table(
        'labour_advances',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'organization_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            'project_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            'source_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            'worker_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            'amount',
            sa.Numeric(precision=14, scale=2),
            nullable=False,
        ),
        sa.Column(
            'advance_date',
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            'notes',
            sa.String(length=300),
            nullable=True,
        ),
        sa.Column(
            'created_by_user_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['created_by_user_id'],
            ['users.id'],
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['organization_id'],
            ['organizations.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['project_id'],
            ['projects.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['source_id'],
            ['labour_sources.id'],
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['worker_id'],
            ['labour_workers.id'],
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index(
        'ix_labour_advances_org_project',
        'labour_advances',
        ['organization_id', 'project_id'],
        unique=False,
    )

    op.create_table(
        'labour_payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'organization_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            'project_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            'source_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            'worker_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            'period_start',
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            'period_end',
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            'gross_wage_amount',
            sa.Numeric(precision=14, scale=2),
            nullable=False,
        ),
        sa.Column(
            'advance_recovered_amount',
            sa.Numeric(precision=14, scale=2),
            nullable=False,
            server_default='0',
        ),
        sa.Column(
            'net_paid_amount',
            sa.Numeric(precision=14, scale=2),
            nullable=False,
        ),
        sa.Column(
            'payment_date',
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            'notes',
            sa.String(length=300),
            nullable=True,
        ),
        sa.Column(
            'created_by_user_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['created_by_user_id'],
            ['users.id'],
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['organization_id'],
            ['organizations.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['project_id'],
            ['projects.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['source_id'],
            ['labour_sources.id'],
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['worker_id'],
            ['labour_workers.id'],
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index(
        'ix_labour_payments_org_project',
        'labour_payments',
        ['organization_id', 'project_id'],
        unique=False,
    )

    op.execute(
        "ALTER TYPE audit_entity_type ADD VALUE IF NOT EXISTS 'LABOUR'"
    )

def downgrade() -> None:
    op.drop_index(
        'ix_labour_attendance_org_project_date',
        table_name='labour_attendance',
    )
    op.drop_table('labour_attendance')

    op.drop_index(
        'ix_labour_payments_org_project',
        table_name='labour_payments',
    )
    op.drop_table('labour_payments')

    op.drop_index(
        'ix_labour_deployments_worker',
        table_name='labour_deployments',
    )
    op.drop_index(
        'ix_labour_deployments_source',
        table_name='labour_deployments',
    )
    op.drop_index(
        'ix_labour_deployments_org_project',
        table_name='labour_deployments',
    )
    op.drop_table('labour_deployments')

    op.drop_index(
        'ix_labour_advances_org_project',
        table_name='labour_advances',
    )
    op.drop_table('labour_advances')

    op.drop_index(
        'ix_labour_workers_org_source',
        table_name='labour_workers',
    )
    op.drop_table('labour_workers')

    op.drop_index(
        'ix_labour_sources_org',
        table_name='labour_sources',
    )
    op.drop_table('labour_sources')

    op.execute("DROP TYPE IF EXISTS labour_deployment_status")
    op.execute("DROP TYPE IF EXISTS labour_source_type")