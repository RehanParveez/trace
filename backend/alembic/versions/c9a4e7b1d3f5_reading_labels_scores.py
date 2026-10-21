"""reading accuracy: labelled examples (ground truth about a sheet) and the stored scores of the reader

Revision ID: c9a4e7b1d3f5
Revises: b3d8f1a6c5e2
Create Date: 2026-10-21 8:55:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c9a4e7b1d3f5'
down_revision: Union[str, Sequence[str], None] = 'b3d8f1a6c5e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("reading_labels", "reading_scores")
ORG = "NULLIF(current_setting('app.current_org_id', true), '')::uuid"
ADMIN = "current_setting('app.is_platform_admin', true) = 'true'"
SUPPORT_ORG = "NULLIF(current_setting('app.support_org_id', true), '')::uuid"

def _stamps():
    return [sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)]

def policy_statements(table: str) -> list[str]:
    return [
        f'CREATE POLICY "{table}_org_isolation" ON "{table}" FOR ALL USING (organization_id = {ORG}) WITH CHECK (organization_id = {ORG})',
        f'CREATE POLICY "{table}_support_read" ON "{table}" FOR SELECT USING ({ADMIN} AND organization_id = {SUPPORT_ORG} AND support_grant_active(organization_id))',
    ]

def upgrade() -> None:
    op.create_table('reading_labels',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('drawing_id', sa.UUID(), nullable=False),
        sa.Column('sheet_id', sa.UUID(), nullable=False),
        sa.Column('family', sa.String(length=24), nullable=False),
        sa.Column('mark', sa.String(length=60), nullable=True),
        sa.Column('polarity', sa.String(length=8), server_default='POSITIVE', nullable=False),
        sa.Column('x_pt', sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column('y_pt', sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column('attrs', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('complete', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('source', sa.String(length=10), nullable=False),
        sa.Column('source_ref', sa.String(length=80), nullable=False),
        sa.Column('extract_version', sa.Integer(), nullable=True),
        sa.Column('created_by_user_id', sa.UUID(), nullable=True),
        *_stamps(),
        sa.CheckConstraint("polarity IN ('POSITIVE','NEGATIVE')", name='ck_reading_labels_polarity'),
        sa.CheckConstraint("source IN ('REGISTER','IMPORT')", name='ck_reading_labels_source'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name='fk_reading_labels_created_by', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['drawing_id', 'organization_id'], ['drawings.id', 'drawings.organization_id'], name='fk_reading_labels_drawing_tenant', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sheet_id', 'organization_id'], ['takeoff_sheets.id', 'takeoff_sheets.organization_id'], name='fk_reading_labels_sheet_tenant', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('drawing_id', 'source', 'source_ref', name='uq_reading_labels_source'),
    )
    op.create_index('ix_reading_labels_drawing_sheet', 'reading_labels', ['drawing_id', 'sheet_id'], unique=False)
    op.create_index('ix_reading_labels_org_project', 'reading_labels', ['organization_id', 'project_id'], unique=False)

    op.create_table('reading_scores',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('drawing_id', sa.UUID(), nullable=False),
        sa.Column('label_drawing_id', sa.UUID(), nullable=True),
        sa.Column('extract_version', sa.Integer(), nullable=True),
        sa.Column('analysis_version', sa.Integer(), nullable=True),
        sa.Column('mode', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('rule_hash', sa.String(length=40), nullable=False),
        sa.Column('labels_stamp', sa.String(length=40), nullable=False),
        sa.Column('label_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('overall_f1', sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('baseline', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.UUID(), nullable=True),
        *_stamps(),
        sa.CheckConstraint("mode IN ('DRY_RUN','STORED')", name='ck_reading_scores_mode'),
        sa.CheckConstraint("status IN ('OK','REGRESSION','PARTIAL','NO_LABELS')", name='ck_reading_scores_status'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name='fk_reading_scores_created_by', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['drawing_id', 'organization_id'], ['drawings.id', 'drawings.organization_id'], name='fk_reading_scores_drawing_tenant', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_reading_scores_drawing_created', 'reading_scores', ['drawing_id', 'created_at'], unique=False)
    op.create_index('ix_reading_scores_org_project', 'reading_scores', ['organization_id', 'project_id'], unique=False)

    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        for stmt in policy_statements(table):
            op.execute(stmt)

def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f'DROP POLICY IF EXISTS "{table}_support_read" ON "{table}"')
        op.execute(f'DROP POLICY IF EXISTS "{table}_org_isolation" ON "{table}"')
    op.drop_index('ix_reading_scores_org_project', table_name='reading_scores')
    op.drop_index('ix_reading_scores_drawing_created', table_name='reading_scores')
    op.drop_table('reading_scores')
    op.drop_index('ix_reading_labels_org_project', table_name='reading_labels')
    op.drop_index('ix_reading_labels_drawing_sheet', table_name='reading_labels')
    op.drop_table('reading_labels')
