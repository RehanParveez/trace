"""reading report: manual marks (reading_overrides) and misread reports for the benchmark queue

Revision ID: a9c2e4f6b8d1
Revises: e2a4c6d8f0b3
Create Date: 2026-11-04 06:10:00.000000
"""
from typing import Union, Sequence
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a9c2e4f6b8d1'
down_revision: Union[str, Sequence[str], None] = 'e2a4c6d8f0b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT = "organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid"
ADMIN = "current_setting('app.is_platform_admin', true) = 'true'"
TABLES = ("reading_overrides", "reading_misread_reports")

def _jsonb(name: str, default: str = "'{}'::jsonb", nullable: bool = False):
    return sa.Column(name, postgresql.JSONB(), server_default=sa.text(default) if default else None, nullable=nullable)

def _common():
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("drawing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sheet_id", postgresql.UUID(as_uuid=True), nullable=False),
    ]

def _stamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]

def upgrade() -> None:
    op.create_table(
        "reading_overrides",
        *_common(),
        sa.Column("item_class", sa.String(32), nullable=False),
        sa.Column("mark", sa.String(60), nullable=True),
        _jsonb("geometry"), _jsonb("attrs"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(10), server_default="ACTIVE", nullable=False),
        sa.Column("image_checked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("checked_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        *_stamps(),
        sa.ForeignKeyConstraint(["sheet_id", "organization_id"], ["takeoff_sheets.id", "takeoff_sheets.organization_id"], ondelete="CASCADE", name="fk_reading_overrides_sheet_tenant"),
        sa.ForeignKeyConstraint(["drawing_id", "organization_id"], ["drawings.id", "drawings.organization_id"], ondelete="CASCADE", name="fk_reading_overrides_drawing_tenant"),
        sa.CheckConstraint("status IN ('ACTIVE','WITHDRAWN')", name="ck_reading_overrides_status"),
    )
    op.create_index("ix_reading_overrides_drawing_sheet", "reading_overrides", ["drawing_id", "sheet_id"])
    op.create_index("ix_reading_overrides_org_project", "reading_overrides", ["organization_id", "project_id"])

    op.create_table(
        "reading_misread_reports",
        *_common(),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ckey", sa.String(40), nullable=True),
        sa.Column("item_class", sa.String(32), nullable=True),
        sa.Column("mark", sa.String(60), nullable=True),
        sa.Column("kind", sa.String(16), nullable=False),
        _jsonb("box", default=None, nullable=True),
        _jsonb("expected"), _jsonb("read_as"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("extract_version", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(10), server_default="OPEN", nullable=False),
        sa.Column("reported_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        *_stamps(),
        sa.ForeignKeyConstraint(["sheet_id", "organization_id"], ["takeoff_sheets.id", "takeoff_sheets.organization_id"], ondelete="CASCADE", name="fk_reading_misreads_sheet_tenant"),
        sa.ForeignKeyConstraint(["drawing_id", "organization_id"], ["drawings.id", "drawings.organization_id"], ondelete="CASCADE", name="fk_reading_misreads_drawing_tenant"),
        sa.CheckConstraint("kind IN ('WRONG_VALUE','WRONG_CLASS','WRONG_POSITION','INVENTED','MISSED','OTHER')", name="ck_reading_misreads_kind"),
        sa.CheckConstraint("status IN ('OPEN','QUEUED','RESOLVED','DISMISSED')", name="ck_reading_misreads_status"),
    )
    op.create_index("ix_reading_misreads_drawing_sheet", "reading_misread_reports", ["drawing_id", "sheet_id"])
    op.create_index("ix_reading_misreads_org_status", "reading_misread_reports", ["organization_id", "status"])

    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}")
        op.execute(f"CREATE POLICY {table}_org_isolation ON {table} USING ({TENANT} OR {ADMIN}) WITH CHECK ({TENANT} OR {ADMIN})")

def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}")
        op.drop_table(table)
