"""AI shadow reads: what the AI read from the title-block strips of a sheet, beside what the rule reader read.

Adds SHEET_CLASSIFICATION to the AI request purposes and a table that keeps each reading, its stored picture and its comparison. Nothing here feeds a measurement or the bill.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a3c5e7f9b1d2"
down_revision = "f4a6c8e0b2d1"
branch_labels = None
depends_on = None

def upgrade() -> None:
  with op.get_context().autocommit_block():
    op.execute("ALTER TYPE ai_request_purpose ADD VALUE IF NOT EXISTS 'SHEET_CLASSIFICATION'")
  op.create_table(
    "ai_shadow_reads",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
    sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    sa.Column("drawing_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("sheet_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("page_no", sa.Integer(), nullable=False),
    sa.Column("purpose", sa.String(40), nullable=False),
    sa.Column("mode", sa.String(8), nullable=False),
    sa.Column("status", sa.String(8), nullable=False),
    sa.Column("prompt_version", sa.String(12), nullable=False),
    sa.Column("schema_version", sa.String(12), nullable=False),
    sa.Column("crop_key", sa.String(300), nullable=False),
    sa.Column("crop", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column("ai_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_requests.id", ondelete="SET NULL", name="fk_ai_shadow_reads_request"), nullable=True),
    sa.Column("rule_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column("ai_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column("comparison", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    sa.Column("totals", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column("problems", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    sa.Column("error", sa.Text(), nullable=True),
    sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_ai_shadow_reads_created_by"), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.ForeignKeyConstraint(["sheet_id", "organization_id"], ["takeoff_sheets.id", "takeoff_sheets.organization_id"], ondelete="CASCADE", name="fk_ai_shadow_reads_sheet_tenant"),
    sa.ForeignKeyConstraint(["drawing_id", "organization_id"], ["drawings.id", "drawings.organization_id"], ondelete="CASCADE", name="fk_ai_shadow_reads_drawing_tenant"),
    sa.CheckConstraint("status IN ('OK','INVALID','FAILED')", name="ck_ai_shadow_reads_status"),
    sa.CheckConstraint("mode IN ('WEAK','ALL')", name="ck_ai_shadow_reads_mode"),
  )
  op.create_index("ix_ai_shadow_reads_drawing_sheet", "ai_shadow_reads", ["drawing_id", "sheet_id", "created_at"])
  op.create_index("ix_ai_shadow_reads_org_project", "ai_shadow_reads", ["organization_id", "project_id"])

def downgrade() -> None:
  op.drop_index("ix_ai_shadow_reads_org_project", table_name="ai_shadow_reads")
  op.drop_index("ix_ai_shadow_reads_drawing_sheet", table_name="ai_shadow_reads")
  op.drop_table("ai_shadow_reads")
