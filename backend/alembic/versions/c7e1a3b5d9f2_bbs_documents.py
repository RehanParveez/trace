"""bbs documents, sheets, rows, audit runs and findings

Revision ID: c7e1a3b5d9f2
Revises: a9c2e4f6b8d1
Create Date: 2026-11-04 3:38:00.000000
"""
from typing import Union, Sequence
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c7e1a3b5d9f2'
down_revision: Union[str, Sequence[str], None] = 'a9c2e4f6b8d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT = "organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid"
ADMIN = "current_setting('app.is_platform_admin', true) = 'true'"
TABLES = ("rebar_bbs_documents", "rebar_bbs_sheets", "rebar_bbs_rows", "rebar_audit_runs", "rebar_audit_findings")
CLASSES = "'ERROR','METHOD','ROUNDING','CONFLICT','MISSING','EXTRA','UNVERIFIABLE','NAMING','INFO'"

def _uuid(name: str, **kw):
    return sa.Column(name, postgresql.UUID(as_uuid=True), **kw)

def _org():
    return _uuid("organization_id", nullable=False)

def _json(name: str, default: str = "'{}'::jsonb", nullable: bool = False):
    return sa.Column(name, postgresql.JSONB(), server_default=sa.text(default) if default else None, nullable=nullable)

def _stamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]

def _org_fk(table: str):
    return sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name=f"fk_{table}_org")

def upgrade() -> None:
    op.create_table(
        "rebar_bbs_documents",
        _uuid("id", primary_key=True), _org(),
        _uuid("project_id", nullable=False),
        _uuid("drawing_set_id", nullable=True),
        sa.Column("file_name", sa.String(500), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(700), nullable=True),
        sa.Column("status", sa.String(12), server_default="ACTIVE", nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("title", sa.String(300), nullable=True),
        sa.Column("pages", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("profile", sa.String(40), nullable=False),
        _json("summary"), _json("page_counters", "'[]'::jsonb"), _json("unread_lines", "'[]'::jsonb"), _json("dropped_repeats", "'[]'::jsonb"),
        _uuid("created_by_user_id", nullable=True),
        *_stamps(),
        _org_fk("rebar_bbs_documents"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE", name="fk_rebar_bbs_documents_project"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL", name="fk_rebar_bbs_documents_user"),
        sa.UniqueConstraint("id", "organization_id", name="uq_rebar_bbs_documents_id_org"),
        sa.UniqueConstraint("project_id", "sha256", name="uq_rebar_bbs_documents_project_sha"),
        sa.UniqueConstraint("project_id", "version", name="uq_rebar_bbs_documents_project_version"),
        sa.CheckConstraint("status IN ('ACTIVE','SUPERSEDED')", name="ck_rebar_bbs_documents_status"),
        sa.CheckConstraint("version >= 1", name="ck_rebar_bbs_documents_version"),
    )
    op.create_index("ix_rebar_bbs_documents_org_project", "rebar_bbs_documents", ["organization_id", "project_id"])

    op.create_table(
        "rebar_bbs_sheets",
        _uuid("id", primary_key=True), _org(),
        _uuid("document_id", nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("first_page", sa.Integer(), nullable=False),
        sa.Column("last_page", sa.Integer(), nullable=False),
        sa.Column("printed_total_kg", sa.Numeric(14, 3), nullable=True),
        _json("dia_totals"),
        *_stamps(),
        _org_fk("rebar_bbs_sheets"),
        sa.ForeignKeyConstraint(["document_id", "organization_id"], ["rebar_bbs_documents.id", "rebar_bbs_documents.organization_id"], ondelete="CASCADE", name="fk_rebar_bbs_sheets_document_tenant"),
        sa.UniqueConstraint("id", "organization_id", name="uq_rebar_bbs_sheets_id_org"),
        sa.UniqueConstraint("document_id", "idx", name="uq_rebar_bbs_sheets_document_idx"),
    )
    op.create_index("ix_rebar_bbs_sheets_document", "rebar_bbs_sheets", ["document_id"])

    op.create_table(
        "rebar_bbs_rows",
        _uuid("id", primary_key=True), _org(),
        _uuid("document_id", nullable=False),
        _uuid("sheet_id", nullable=False),
        sa.Column("row_no", sa.Integer(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("y", sa.Numeric(8, 1), nullable=True),
        sa.Column("member", sa.String(300), nullable=True),
        sa.Column("sr", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(300), server_default="", nullable=False),
        sa.Column("dia", sa.Integer(), nullable=True),
        sa.Column("spacing_in", sa.Numeric(8, 3), nullable=True),
        sa.Column("members", sa.Numeric(12, 3), nullable=True),
        sa.Column("each", sa.Numeric(12, 3), nullable=True),
        sa.Column("total", sa.Numeric(12, 3), nullable=True),
        sa.Column("cut_ft", sa.Numeric(12, 3), nullable=True),
        sa.Column("total_ft", sa.Numeric(14, 3), nullable=True),
        sa.Column("unit_kg_ft", sa.Numeric(10, 4), nullable=True),
        sa.Column("total_kg", sa.Numeric(14, 3), nullable=True),
        _json("parts", "'[]'::jsonb"), _json("notes", "'[]'::jsonb"), _json("issues", "'[]'::jsonb"),
        *_stamps(),
        _org_fk("rebar_bbs_rows"),
        sa.ForeignKeyConstraint(["document_id", "organization_id"], ["rebar_bbs_documents.id", "rebar_bbs_documents.organization_id"], ondelete="CASCADE", name="fk_rebar_bbs_rows_document_tenant"),
        sa.ForeignKeyConstraint(["sheet_id", "organization_id"], ["rebar_bbs_sheets.id", "rebar_bbs_sheets.organization_id"], ondelete="CASCADE", name="fk_rebar_bbs_rows_sheet_tenant"),
        sa.UniqueConstraint("document_id", "row_no", name="uq_rebar_bbs_rows_document_row"),
    )
    op.create_index("ix_rebar_bbs_rows_document_sheet", "rebar_bbs_rows", ["document_id", "sheet_id"])

    op.create_table(
        "rebar_audit_runs",
        _uuid("id", primary_key=True), _org(),
        _uuid("document_id", nullable=False),
        sa.Column("level", sa.String(4), server_default="L1", nullable=False),
        sa.Column("engine_digest", sa.String(64), nullable=False),
        sa.Column("rules_digest", sa.String(64), nullable=False),
        sa.Column("decisions_digest", sa.String(64), nullable=False),
        _uuid("previous_document_id", nullable=True),
        _json("totals"), _json("diff"),
        _uuid("created_by_user_id", nullable=True),
        *_stamps(),
        _org_fk("rebar_audit_runs"),
        sa.ForeignKeyConstraint(["document_id", "organization_id"], ["rebar_bbs_documents.id", "rebar_bbs_documents.organization_id"], ondelete="CASCADE", name="fk_rebar_audit_runs_document_tenant"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL", name="fk_rebar_audit_runs_user"),
        sa.UniqueConstraint("id", "organization_id", name="uq_rebar_audit_runs_id_org"),
    )
    op.create_index("ix_rebar_audit_runs_document", "rebar_audit_runs", ["document_id", "created_at"])

    op.create_table(
        "rebar_audit_findings",
        _uuid("id", primary_key=True), _org(),
        _uuid("run_id", nullable=False),
        _uuid("document_id", nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("finding_class", sa.String(14), nullable=False),
        sa.Column("rule", sa.String(300), nullable=False),
        sa.Column("finding_key", sa.String(600), nullable=False),
        _json("bbs_ref"), _json("drawing_ref", default=None, nullable=True),
        sa.Column("bbs_value", sa.Text(), nullable=True),
        sa.Column("trace_value", sa.Text(), nullable=True),
        sa.Column("diff_kg", sa.Numeric(14, 3), nullable=True),
        sa.Column("diff_pct", sa.Numeric(8, 3), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), server_default=sa.text("1"), nullable=False),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("status", sa.String(10), server_default="OPEN", nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        _uuid("decided_by_user_id", nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        *_stamps(),
        _org_fk("rebar_audit_findings"),
        sa.ForeignKeyConstraint(["run_id", "organization_id"], ["rebar_audit_runs.id", "rebar_audit_runs.organization_id"], ondelete="CASCADE", name="fk_rebar_audit_findings_run_tenant"),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"], ondelete="SET NULL", name="fk_rebar_audit_findings_user"),
        sa.CheckConstraint("status IN ('OPEN','ACCEPTED','REJECTED','SIGNED')", name="ck_rebar_audit_findings_status"),
        sa.CheckConstraint(f"finding_class IN ({CLASSES})", name="ck_rebar_audit_findings_class"),
    )
    op.create_index("ix_rebar_audit_findings_run_class", "rebar_audit_findings", ["run_id", "finding_class"])
    op.create_index("ix_rebar_audit_findings_org_document", "rebar_audit_findings", ["organization_id", "document_id"])

    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}")
        op.execute(f"CREATE POLICY {table}_org_isolation ON {table} USING ({TENANT} OR {ADMIN}) WITH CHECK ({TENANT} OR {ADMIN})")

def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}")
        op.drop_table(table)
