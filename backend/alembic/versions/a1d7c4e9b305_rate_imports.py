"""staging tables for loading a schedule of rates into a rate book

Revision ID: a1d7c4e9b305
Revises: 9a6c3e1d4f32
Create Date: 2026-10-19 10:10:00.000000
"""
import importlib.util
import pathlib
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = 'a1d7c4e9b305'
down_revision: Union[str, Sequence[str], None] = '9a6c3e1d4f32'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def _ts():
    return [sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)]

def _rls_upgrade() -> None:
    path = pathlib.Path(__file__).with_name("8f5b2d0c3e21_rls_scopes.py")
    spec = importlib.util.spec_from_file_location("_rls_scopes_for_rate_imports", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.upgrade()

def upgrade() -> None:
    op.create_table(
        "rate_imports",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="UPLOADED"),
        sa.Column("source_kind", sa.String(4), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=True),
        sa.Column("file_size", sa.BigInteger, nullable=False, server_default=sa.text("0")),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("layout_profile", sa.String(40), nullable=False, server_default="GENERIC"),
        sa.Column("first_page", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("last_page", sa.Integer, nullable=True),
        sa.Column("book_code", sa.String(50), nullable=True),
        sa.Column("book_name", sa.String(200), nullable=True),
        sa.Column("edition", sa.String(50), nullable=True),
        sa.Column("jurisdiction", sa.String(50), nullable=True),
        sa.Column("province", sa.String(50), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="PKR"),
        sa.Column("effective_from", sa.Date, nullable=True),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("page_count", sa.Integer, nullable=True),
        sa.Column("row_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("report", pg.JSONB, nullable=True),
        sa.Column("sample_seq", pg.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rate_book_id", pg.UUID(as_uuid=True), sa.ForeignKey("rate_books.id", ondelete="SET NULL"), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by_user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        *_ts(),
        sa.UniqueConstraint("id", "organization_id", name="uq_rate_imports_id_org"),
        sa.CheckConstraint("status IN ('UPLOADED','PARSING','REVIEW','PUBLISHED','FAILED','CANCELLED')", name="ck_rate_imports_status"),
        sa.CheckConstraint("source_kind IN ('PDF','CSV')", name="ck_rate_imports_kind"),
        sa.CheckConstraint("file_size >= 0", name="ck_rate_imports_size"),
    )
    op.create_index("ix_rate_imports_org_created", "rate_imports", ["organization_id", "created_at"])
    op.create_index("ix_rate_imports_org_hash", "rate_imports", ["organization_id", "content_hash"])

    op.create_table(
        "rate_import_rows",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("import_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("page", sa.Integer, nullable=True),
        sa.Column("line_no", sa.Integer, nullable=True),
        sa.Column("chapter", sa.String(200), nullable=True),
        sa.Column("item_no", sa.String(60), nullable=True),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("raw_line", sa.Text, nullable=True),
        sa.Column("unit_raw", sa.String(60), nullable=True),
        sa.Column("basis_qty", sa.Numeric(14, 4), nullable=False, server_default=sa.text("1")),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("unit_known", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("rate_raw", sa.String(60), nullable=True),
        sa.Column("rate", sa.Numeric(16, 4), nullable=True),
        sa.Column("rate_alt", sa.Numeric(16, 4), nullable=True),
        sa.Column("unit_rate", sa.Numeric(18, 6), nullable=True),
        sa.Column("flags", pg.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("needs_review", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("reviewed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("skipped", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("edited", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("original", pg.JSONB, nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("work_item_code", sa.String(50), nullable=True),
        sa.Column("mapping_source", sa.String(10), nullable=True),
        sa.Column("suggestions", pg.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_sample", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("sample_verified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        *_ts(),
        sa.UniqueConstraint("import_id", "seq", name="uq_rate_import_rows_seq"),
        sa.ForeignKeyConstraint(["import_id", "organization_id"], ["rate_imports.id", "rate_imports.organization_id"], ondelete="CASCADE",
          name="fk_rate_import_rows_import_tenant"),
        sa.CheckConstraint("basis_qty > 0", name="ck_rate_import_rows_basis"),
        sa.CheckConstraint("mapping_source IS NULL OR mapping_source IN ('SUGGESTED','MANUAL','CSR_REF')", name="ck_rate_import_rows_mapping_source"),
    )
    op.create_index("ix_rate_import_rows_import_review", "rate_import_rows", ["import_id", "needs_review"])
    op.create_index("ix_rate_import_rows_import_code", "rate_import_rows", ["import_id", "work_item_code"])
    op.create_index("ix_rate_import_rows_org", "rate_import_rows", ["organization_id"])

    _rls_upgrade()

def downgrade() -> None:
    op.drop_table("rate_import_rows")
    op.drop_table("rate_imports")
