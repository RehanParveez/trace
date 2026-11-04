"""bbs expectation runs and expectations

Revision ID: e5b7d9f1a3c2
Revises: d4a6c8e0b2f1
Create Date: 2026-11-04 5:18:00.000000
"""
from typing import Union, Sequence
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e5b7d9f1a3c2'
down_revision: Union[str, Sequence[str], None] = 'd4a6c8e0b2f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT = "organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid"
ADMIN = "current_setting('app.is_platform_admin', true) = 'true'"
TABLES = ("rebar_bbs_expect_runs", "rebar_bbs_expectations")

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
        "rebar_bbs_expect_runs",
        _uuid("id", primary_key=True), _org(),
        _uuid("document_id", nullable=False),
        _json("decisions"),
        sa.Column("decisions_digest", sa.String(64), nullable=False),
        sa.Column("member_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("complete_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        _json("stats"),
        _uuid("created_by_user_id", nullable=True),
        *_stamps(),
        _org_fk("rebar_bbs_expect_runs"),
        sa.ForeignKeyConstraint(["document_id", "organization_id"], ["rebar_bbs_documents.id", "rebar_bbs_documents.organization_id"], ondelete="CASCADE", name="fk_rebar_bbs_expect_runs_document_tenant"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL", name="fk_rebar_bbs_expect_runs_user"),
        sa.UniqueConstraint("id", "organization_id", name="uq_rebar_bbs_expect_runs_id_org"),
    )
    op.create_index("ix_rebar_bbs_expect_runs_document", "rebar_bbs_expect_runs", ["document_id", "created_at"])

    op.create_table(
        "rebar_bbs_expectations",
        _uuid("id", primary_key=True), _org(),
        _uuid("run_id", nullable=False),
        _uuid("document_id", nullable=False),
        sa.Column("member_class", sa.String(12), nullable=False),
        sa.Column("mark", sa.String(60), nullable=False),
        sa.Column("floor", sa.String(12), nullable=True),
        sa.Column("count", sa.Numeric(14, 2), nullable=True),
        sa.Column("total_ft", sa.Numeric(14, 2), nullable=True),
        sa.Column("kg", sa.Numeric(14, 2), nullable=True),
        sa.Column("complete", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("plan_count", sa.Integer(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("decision_only", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        _json("lines", "'[]'::jsonb"), _json("inputs", "'[]'::jsonb"), _json("blocked", "'[]'::jsonb"), _json("notes", "'[]'::jsonb"),
        *_stamps(),
        _org_fk("rebar_bbs_expectations"),
        sa.ForeignKeyConstraint(["run_id", "organization_id"], ["rebar_bbs_expect_runs.id", "rebar_bbs_expect_runs.organization_id"], ondelete="CASCADE", name="fk_rebar_bbs_expectations_run_tenant"),
    )
    op.create_index("ix_rebar_bbs_expectations_run_class", "rebar_bbs_expectations", ["run_id", "member_class"])
    op.create_index("ix_rebar_bbs_expectations_org_document", "rebar_bbs_expectations", ["organization_id", "document_id"])

    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}")
        op.execute(f"CREATE POLICY {table}_org_isolation ON {table} USING ({TENANT} OR {ADMIN}) WITH CHECK ({TENANT} OR {ADMIN})")

def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}")
        op.drop_table(table)
