"""takeoff view alignments

Revision ID: 7c1a5e92d3b4
Revises: 4d38f84bc1ea
Create Date: 2026-10-15 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '7c1a5e92d3b4'
down_revision: Union[str, Sequence[str], None] = '4d38f84bc1ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "takeoff_view_alignments"
TENANT = "organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid"
ADMIN = "current_setting('app.is_platform_admin', true) = 'true'"

def upgrade() -> None:
    # Where a person placed a drawing view on the building frame, or which view they marked as the reference. Views nobody decided are placed by the engine and not stored.
    op.create_table(TABLE,
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('drawing_id', sa.UUID(), nullable=False),
    sa.Column('frame_key', sa.String(length=200), nullable=False),
    sa.Column('role', sa.String(length=12), server_default='PLACEMENT', nullable=False),
    sa.Column('dx_mm', sa.Numeric(precision=14, scale=3), server_default='0', nullable=False),
    sa.Column('dy_mm', sa.Numeric(precision=14, scale=3), server_default='0', nullable=False),
    sa.Column('method', sa.String(length=20), server_default='MANUAL', nullable=False),
    sa.Column('updated_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("role IN ('PLACEMENT','REFERENCE')", name='ck_takeoff_view_alignments_role'),
    sa.ForeignKeyConstraint(['drawing_id', 'organization_id'], ['drawings.id', 'drawings.organization_id'], name='fk_takeoff_view_alignments_drawing_tenant', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], name='fk_takeoff_view_alignments_updated_by', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('drawing_id', 'frame_key', name='uq_takeoff_view_alignments_key')
    )
    op.create_index('ix_takeoff_view_alignments_org_project', TABLE, ['organization_id', 'project_id'], unique=False)
    op.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS {TABLE}_org_isolation ON {TABLE}")
    op.execute(f"CREATE POLICY {TABLE}_org_isolation ON {TABLE} USING ({TENANT} OR {ADMIN}) WITH CHECK ({TENANT} OR {ADMIN})")

def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {TABLE}_org_isolation ON {TABLE}")
    op.drop_index('ix_takeoff_view_alignments_org_project', table_name=TABLE)
    op.drop_table(TABLE)
