"""bbs project decisions, match runs and matches

Revision ID: d4a6c8e0b2f1
Revises: c7e1a3b5d9f2
Create Date: 2026-11-04 16:24:00.000000
"""
from typing import Union, Sequence
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd4a6c8e0b2f1'
down_revision: Union[str, Sequence[str], None] = 'c7e1a3b5d9f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT = "organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid"
ADMIN = "current_setting('app.is_platform_admin', true) = 'true'"
TABLES = ("rebar_bbs_decisions", "rebar_bbs_match_runs", "rebar_bbs_matches")

def _uuid(name: str, **kw):
    return sa.Column(name, postgresql.UUID(as_uuid=True), **kw)

def _org():
    return _uuid("organization_id", nullable=False)

def _json(name: str, default: str = "'{}'::jsonb"):
    return sa.Column(name, postgresql.JSONB(), server_default=sa.text(default), nullable=False)

def _stamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]

def _org_fk(table: str):
    return sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name=f"fk_{table}_org")

def upgrade() -> None:
    op.create_table(
        "rebar_bbs_decisions",
        _uuid("id", primary_key=True), _org(),
        _uuid("project_id", nullable=False),
        sa.Column("key", sa.String(40), nullable=False),
        _json("value"),
        _uuid("decided_by_user_id", nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        *_stamps(),
        _org_fk("rebar_bbs_decisions"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE", name="fk_rebar_bbs_decisions_project"),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"], ondelete="SET NULL", name="fk_rebar_bbs_decisions_user"),
        sa.UniqueConstraint("organization_id", "project_id", "key", name="uq_rebar_bbs_decisions_project_key"),
    )
    op.create_index("ix_rebar_bbs_decisions_org_project", "rebar_bbs_decisions", ["organization_id", "project_id"])

    op.create_table(
        "rebar_bbs_match_runs",
        _uuid("id", primary_key=True), _org(),
        _uuid("document_id", nullable=False),
        _json("floor_map"), _json("floor_map_proposed"),
        sa.Column("floor_map_confirmed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("member_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        _json("stats"),
        _uuid("created_by_user_id", nullable=True),
        *_stamps(),
        _org_fk("rebar_bbs_match_runs"),
        sa.ForeignKeyConstraint(["document_id", "organization_id"], ["rebar_bbs_documents.id", "rebar_bbs_documents.organization_id"], ondelete="CASCADE", name="fk_rebar_bbs_match_runs_document_tenant"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL", name="fk_rebar_bbs_match_runs_user"),
        sa.UniqueConstraint("id", "organization_id", name="uq_rebar_bbs_match_runs_id_org"),
    )
    op.create_index("ix_rebar_bbs_match_runs_document", "rebar_bbs_match_runs", ["document_id", "created_at"])

    op.create_table(
        "rebar_bbs_matches",
        _uuid("id", primary_key=True), _org(),
        _uuid("run_id", nullable=False),
        _uuid("document_id", nullable=False),
        _uuid("row_id", nullable=True),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("family", sa.String(12), nullable=True),
        sa.Column("sheet_name", sa.String(300), nullable=True),
        sa.Column("member", sa.String(300), nullable=True),
        _json("floors", "'[]'::jsonb"),
        sa.Column("method", sa.String(16), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), server_default=sa.text("0"), nullable=False),
        sa.Column("basis", sa.String(20), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        _json("elements", "'[]'::jsonb"),
        *_stamps(),
        _org_fk("rebar_bbs_matches"),
        sa.ForeignKeyConstraint(["run_id", "organization_id"], ["rebar_bbs_match_runs.id", "rebar_bbs_match_runs.organization_id"], ondelete="CASCADE", name="fk_rebar_bbs_matches_run_tenant"),
        sa.CheckConstraint("kind IN ('MATCH','ASK','EXTRA','MISSING')", name="ck_rebar_bbs_matches_kind"),
    )
    op.create_index("ix_rebar_bbs_matches_run_kind", "rebar_bbs_matches", ["run_id", "kind"])
    op.create_index("ix_rebar_bbs_matches_org_document", "rebar_bbs_matches", ["organization_id", "document_id"])

    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}")
        op.execute(f"CREATE POLICY {table}_org_isolation ON {table} USING ({TENANT} OR {ADMIN}) WITH CHECK ({TENANT} OR {ADMIN})")

def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}")
        op.drop_table(table)
