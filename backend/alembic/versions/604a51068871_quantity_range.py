"""quantity range

Revision ID: 604a51068871
Revises: 18e69886fced
Create Date: 2026-10-17 19:02:28.577223
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '604a51068871'
down_revision: Union[str, Sequence[str], None] = '18e69886fced'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_KINDS = "kind IN ('CONTRACT_BOQ','PROCUREMENT','MEASUREMENT_BOOK','AUDIT_REPORT','REVISION_COMPARISON','BBS')"
NEW_KINDS = "kind IN ('CONTRACT_BOQ','PROCUREMENT','MEASUREMENT_BOOK','MEASUREMENT_SHEET','STAGE_REPORT','AUDIT_REPORT','REVISION_COMPARISON','BBS')"

def upgrade() -> None:
    op.add_column('boq_items', sa.Column('quantity_range', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('boq_snapshot_items', sa.Column('work_stage', sa.String(length=40), nullable=True))
    op.add_column('boq_snapshot_items', sa.Column('spec_key', sa.String(length=100), nullable=True))
    op.add_column('boq_snapshot_items', sa.Column('spec', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('boq_snapshot_items', sa.Column('quantity_range', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.drop_constraint('ck_export_jobs_kind', 'export_jobs', type_='check')
    op.create_check_constraint('ck_export_jobs_kind', 'export_jobs', NEW_KINDS)

def downgrade() -> None:
    op.execute("DELETE FROM export_jobs WHERE kind IN ('MEASUREMENT_SHEET','STAGE_REPORT')")
    op.drop_constraint('ck_export_jobs_kind', 'export_jobs', type_='check')
    op.create_check_constraint('ck_export_jobs_kind', 'export_jobs', OLD_KINDS)
    op.drop_column('boq_snapshot_items', 'quantity_range')
    op.drop_column('boq_snapshot_items', 'spec')
    op.drop_column('boq_snapshot_items', 'spec_key')
    op.drop_column('boq_snapshot_items', 'work_stage')
    op.drop_column('boq_items', 'quantity_range')
