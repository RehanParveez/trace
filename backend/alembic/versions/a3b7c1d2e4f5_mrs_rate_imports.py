"""Official rate schedule imports and project rate book selection

Revision ID: a3b7c1d2e4f5
Revises: 53e108b93bf4
Create Date: 2026-10-11 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a3b7c1d2e4f5'
down_revision: Union[str, Sequence[str], None] = '53e108b93bf4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT = "organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid"
ADMIN = "current_setting('app.is_platform_admin', true) = 'true'"
TABLES = ["rate_imports", "rate_import_rows", "project_rate_selections"]

def upgrade() -> None:
    op.create_table('rate_imports',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('source_system', sa.String(length=30), server_default='PUNJAB_MRS', nullable=False),
    sa.Column('authority', sa.String(length=200), nullable=True),
    sa.Column('province', sa.String(length=50), nullable=True),
    sa.Column('district', sa.String(length=100), nullable=True),
    sa.Column('edition', sa.String(length=80), nullable=True),
    sa.Column('effective_from', sa.Date(), nullable=True),
    sa.Column('effective_to', sa.Date(), nullable=True),
    sa.Column('source_document_name', sa.String(length=300), nullable=False),
    sa.Column('source_url', sa.String(length=1000), nullable=True),
    sa.Column('file_kind', sa.String(length=5), nullable=False),
    sa.Column('file_size_bytes', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('storage_key', sa.String(length=500), nullable=False),
    sa.Column('page_count', sa.Integer(), nullable=True),
    sa.Column('layout_profile', sa.String(length=60), server_default='GENERIC', nullable=False),
    sa.Column('status', sa.String(length=20), server_default='PARSING', nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('row_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('mapped_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('verification_status', sa.String(length=20), nullable=True),
    sa.Column('verification', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('parse_summary', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('spot_check_confirmed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('spot_check_confirmed_by_user_id', sa.UUID(), nullable=True),
    sa.Column('override_reason', sa.Text(), nullable=True),
    sa.Column('rate_book_id', sa.UUID(), nullable=True),
    sa.Column('created_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('PARSING','PENDING_REVIEW','DRAFT_CREATED','FAILED','CANCELLED')", name='ck_rate_imports_status'),
    sa.CheckConstraint("file_kind IN ('PDF','CSV')", name='ck_rate_imports_file_kind'),
    sa.CheckConstraint('effective_from IS NULL OR effective_to IS NULL OR effective_to >= effective_from', name='ck_rate_imports_effective_range'),
    sa.CheckConstraint('row_count >= 0 AND mapped_count >= 0 AND mapped_count <= row_count', name='ck_rate_imports_counts'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['spot_check_confirmed_by_user_id'], ['users.id'], name='fk_rate_imports_spot_check_user', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['rate_book_id'], ['rate_books.id'], name='fk_rate_imports_rate_book', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name='fk_rate_imports_created_by', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'organization_id', name='uq_rate_imports_id_org')
    )
    op.create_index('ix_rate_imports_org', 'rate_imports', ['organization_id'], unique=False)
    op.create_index('uq_rate_imports_org_hash', 'rate_imports', ['organization_id', 'content_hash'], unique=True,
      postgresql_where=sa.text("status NOT IN ('FAILED','CANCELLED')"))

    op.create_table('rate_import_rows',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('rate_import_id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('seq', sa.Integer(), nullable=False),
    sa.Column('page', sa.Integer(), nullable=True),
    sa.Column('line_no', sa.Integer(), nullable=True),
    sa.Column('chapter', sa.String(length=200), nullable=True),
    sa.Column('item_no', sa.String(length=60), nullable=True),
    sa.Column('description', sa.Text(), server_default='', nullable=False),
    sa.Column('unit_raw', sa.String(length=60), nullable=True),
    sa.Column('basis_qty', sa.Numeric(precision=14, scale=4), server_default=sa.text('1'), nullable=False),
    sa.Column('unit', sa.String(length=20), nullable=True),
    sa.Column('rate_raw', sa.String(length=40), nullable=True),
    sa.Column('rate', sa.Numeric(precision=16, scale=4), nullable=True),
    sa.Column('rate_alt', sa.Numeric(precision=16, scale=4), nullable=True),
    sa.Column('unit_rate', sa.Numeric(precision=18, scale=6), nullable=True),
    sa.Column('raw_line', sa.Text(), nullable=True),
    sa.Column('flags', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('status', sa.String(length=14), server_default='PARSED', nullable=False),
    sa.Column('work_item_code', sa.String(length=50), nullable=True),
    sa.Column('suggested_code', sa.String(length=50), nullable=True),
    sa.Column('suggestion_reason', sa.String(length=200), nullable=True),
    sa.Column('spot_check', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('correction_note', sa.Text(), nullable=True),
    sa.Column('original', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('PARSED','NEEDS_REVIEW','MAPPED','IGNORED')", name='ck_rate_import_rows_status'),
    sa.CheckConstraint('basis_qty > 0', name='ck_rate_import_rows_basis'),
    sa.CheckConstraint("status <> 'MAPPED' OR (work_item_code IS NOT NULL AND unit IS NOT NULL)", name='ck_rate_import_rows_mapped_has_code'),
    sa.ForeignKeyConstraint(['rate_import_id'], ['rate_imports.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('rate_import_id', 'seq', name='uq_rate_import_rows_import_seq')
    )
    op.create_index(op.f('ix_rate_import_rows_organization_id'), 'rate_import_rows', ['organization_id'], unique=False)
    op.create_index('ix_rate_import_rows_import_status', 'rate_import_rows', ['rate_import_id', 'status'], unique=False)
    op.create_index('ix_rate_import_rows_import_page', 'rate_import_rows', ['rate_import_id', 'page'], unique=False)
    op.create_index('ix_rate_import_rows_import_code', 'rate_import_rows', ['rate_import_id', 'work_item_code'], unique=False)

    op.create_table('project_rate_selections',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('province', sa.String(length=50), nullable=True),
    sa.Column('district', sa.String(length=100), nullable=True),
    sa.Column('rate_book_ids', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('updated_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], name='fk_project_rate_selections_updated_by', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', name='uq_project_rate_selections_project')
    )
    op.create_index('ix_project_rate_selections_org', 'project_rate_selections', ['organization_id'], unique=False)

    for t in TABLES:
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {t}_org_isolation ON {t} USING ({TENANT} OR {ADMIN}) WITH CHECK ({TENANT} OR {ADMIN})")

def downgrade() -> None:
    for t in reversed(TABLES):
        op.execute(f"DROP POLICY IF EXISTS {t}_org_isolation ON {t}")
    op.drop_index('ix_project_rate_selections_org', table_name='project_rate_selections')
    op.drop_table('project_rate_selections')
    op.drop_index('ix_rate_import_rows_import_code', table_name='rate_import_rows')
    op.drop_index('ix_rate_import_rows_import_page', table_name='rate_import_rows')
    op.drop_index('ix_rate_import_rows_import_status', table_name='rate_import_rows')
    op.drop_index(op.f('ix_rate_import_rows_organization_id'), table_name='rate_import_rows')
    op.drop_table('rate_import_rows')
    op.drop_index('uq_rate_imports_org_hash', table_name='rate_imports', postgresql_where=sa.text("status NOT IN ('FAILED','CANCELLED')"))
    op.drop_index('ix_rate_imports_org', table_name='rate_imports')
    op.drop_table('rate_imports')
