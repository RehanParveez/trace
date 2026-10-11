"""pdf_takeoff

Revision ID: 5ffa2405d4b8
Revises: b4c8d2e3f5a6
Create Date: 2026-10-11 17:04:23.548925
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '5ffa2405d4b8'
down_revision: Union[str, Sequence[str], None] = 'b4c8d2e3f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT = "organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid"
ADMIN = "current_setting('app.is_platform_admin', true) = 'true'"
TABLES = ["takeoff_sheets", "takeoff_calibrations", "takeoff_measurements"]

def _uuid():
  return postgresql.UUID(as_uuid=True)

def _ts():
  return [
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
  ]

def _enable(table: str) -> None:
  op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
  op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
  op.execute(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}")
  op.execute(f"CREATE POLICY {table}_org_isolation ON {table} USING ({TENANT} OR {ADMIN}) WITH CHECK ({TENANT} OR {ADMIN})")

def upgrade() -> None:
  op.drop_constraint("ck_quantity_ledger_source_kind", "quantity_ledger", type_="check")
  op.create_check_constraint(
    "ck_quantity_ledger_source_kind", "quantity_ledger",
    "source_kind IN ('MODEL','SCHEDULE_IMPORT','MANUAL','ESTIMATE','PDF_TAKEOFF')")

  op.create_table(
    "takeoff_sheets",
    sa.Column("id", _uuid(), primary_key=True),
    sa.Column("organization_id", _uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
    sa.Column("project_id", _uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    sa.Column("drawing_id", _uuid(), nullable=False),
    sa.Column("page_no", sa.Integer(), nullable=False),
    sa.Column("width_pt", sa.Numeric(12, 4), nullable=False),
    sa.Column("height_pt", sa.Numeric(12, 4), nullable=False),
    sa.Column("rotation", sa.Integer(), server_default=sa.text("0"), nullable=False),
    sa.Column("content_kind", sa.String(10), server_default="UNKNOWN", nullable=False),
    sa.Column("label", sa.String(200), nullable=True),
    sa.Column("level_id", _uuid(), sa.ForeignKey("building_levels.id", ondelete="SET NULL"), nullable=True),
    sa.Column("scale_text", sa.String(60), nullable=True),
    sa.Column("detected_scale", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column("prep_status", sa.String(10), server_default="PENDING", nullable=False),
    sa.Column("prep_error", sa.Text(), nullable=True),
    sa.Column("prep_meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column("text_chars", sa.Integer(), nullable=True),
    sa.Column("vector_ops", sa.Integer(), nullable=True),
    *_ts(),
    sa.UniqueConstraint("id", "organization_id", name="uq_takeoff_sheets_id_org"),
    sa.UniqueConstraint("drawing_id", "page_no", name="uq_takeoff_sheets_drawing_page"),
    sa.ForeignKeyConstraint(["drawing_id", "organization_id"], ["drawings.id", "drawings.organization_id"],
      ondelete="CASCADE", name="fk_takeoff_sheets_drawing_tenant"),
    sa.CheckConstraint("page_no >= 1", name="ck_takeoff_sheets_page_no"),
    sa.CheckConstraint("width_pt > 0 AND height_pt > 0", name="ck_takeoff_sheets_size"),
    sa.CheckConstraint("rotation IN (0, 90, 180, 270)", name="ck_takeoff_sheets_rotation"),
    sa.CheckConstraint("content_kind IN ('VECTOR','RASTER','UNKNOWN')", name="ck_takeoff_sheets_content_kind"),
    sa.CheckConstraint("prep_status IN ('PENDING','READY','FAILED')", name="ck_takeoff_sheets_prep_status"),
  )
  op.create_index("ix_takeoff_sheets_org_project", "takeoff_sheets", ["organization_id", "project_id"])

  op.create_table(
    "takeoff_calibrations",
    sa.Column("id", _uuid(), primary_key=True),
    sa.Column("organization_id", _uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
    sa.Column("sheet_id", _uuid(), nullable=False),
    sa.Column("method", sa.String(12), nullable=False),
    sa.Column("ref", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column("check_ref", postgresql.JSONB(), nullable=True),
    sa.Column("ratio", sa.Numeric(14, 6), nullable=True),
    sa.Column("label", sa.String(120), nullable=True),
    sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    sa.Column("usable", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    sa.Column("reason", sa.Text(), nullable=True),
    sa.Column("mm_per_pt", sa.Numeric(24, 12), nullable=True),
    sa.Column("check_error_pct", sa.Numeric(10, 4), nullable=True),
    sa.Column("baseline_pt", sa.Numeric(14, 4), nullable=True),
    sa.Column("quality_factor", sa.Numeric(5, 4), server_default=sa.text("0"), nullable=False),
    sa.Column("warnings", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column("created_by_user_id", _uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    *_ts(),
    sa.UniqueConstraint("id", "organization_id", name="uq_takeoff_calibrations_id_org"),
    sa.ForeignKeyConstraint(["sheet_id", "organization_id"], ["takeoff_sheets.id", "takeoff_sheets.organization_id"],
      ondelete="CASCADE", name="fk_takeoff_calibrations_sheet_tenant"),
    sa.CheckConstraint("method IN ('TWO_POINT','SCALE_RATIO')", name="ck_takeoff_calibrations_method"),
    sa.CheckConstraint("ratio IS NULL OR ratio > 0", name="ck_takeoff_calibrations_ratio"),
    sa.CheckConstraint("quality_factor >= 0 AND quality_factor <= 1", name="ck_takeoff_calibrations_quality"),
  )
  op.create_index("ix_takeoff_calibrations_sheet", "takeoff_calibrations", ["sheet_id"])
  op.create_index("uq_takeoff_calibrations_default", "takeoff_calibrations", ["sheet_id"], unique=True,
    postgresql_where=sa.text("is_default"))

  op.create_table(
    "takeoff_measurements",
    sa.Column("id", _uuid(), primary_key=True),
    sa.Column("organization_id", _uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
    sa.Column("project_id", _uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    sa.Column("sheet_id", _uuid(), nullable=False),
    sa.Column("calibration_id", _uuid(), nullable=True),
    sa.Column("kind", sa.String(8), nullable=False),
    sa.Column("quantity_mode", sa.String(40), server_default="DIRECT", nullable=False),
    sa.Column("geometry", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column("params", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column("work_item_code", sa.String(50), nullable=True),
    sa.Column("level_id", _uuid(), sa.ForeignKey("building_levels.id", ondelete="SET NULL"), nullable=True),
    sa.Column("label", sa.String(200), nullable=True),
    sa.Column("tag", sa.String(60), nullable=True),
    sa.Column("material_grade", sa.String(50), nullable=True),
    sa.Column("recon_mode", sa.String(14), server_default="AUTO", nullable=False),
    sa.Column("source", sa.String(12), server_default="MANUAL", nullable=False),
    sa.Column("status", sa.String(10), server_default="DRAFT", nullable=False),
    sa.Column("geometry_hash", sa.String(64), nullable=True),
    sa.Column("computed", postgresql.JSONB(), nullable=True),
    sa.Column("last_result", postgresql.JSONB(), nullable=True),
    sa.Column("created_by_user_id", _uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    sa.Column("confirmed_by_user_id", _uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    *_ts(),
    sa.UniqueConstraint("id", "organization_id", name="uq_takeoff_measurements_id_org"),
    sa.ForeignKeyConstraint(["sheet_id", "organization_id"], ["takeoff_sheets.id", "takeoff_sheets.organization_id"],
      ondelete="CASCADE", name="fk_takeoff_measurements_sheet_tenant"),
    sa.ForeignKeyConstraint(["calibration_id", "organization_id"], ["takeoff_calibrations.id", "takeoff_calibrations.organization_id"],
      name="fk_takeoff_measurements_calibration_tenant"),
    sa.CheckConstraint("kind IN ('LENGTH','AREA','COUNT')", name="ck_takeoff_measurements_kind"),
    sa.CheckConstraint("recon_mode IN ('AUTO','ADD','REPLACE_MODEL','VERIFY_ONLY')", name="ck_takeoff_measurements_recon_mode"),
    sa.CheckConstraint("source IN ('MANUAL','VECTOR_SNAP','TAG_SCAN')", name="ck_takeoff_measurements_source"),
    sa.CheckConstraint("status IN ('DRAFT','CONFIRMED')", name="ck_takeoff_measurements_status"),
    sa.CheckConstraint("status <> 'CONFIRMED' OR work_item_code IS NOT NULL", name="ck_takeoff_measurements_confirmed_item"),
    sa.CheckConstraint("status <> 'CONFIRMED' OR kind = 'COUNT' OR calibration_id IS NOT NULL", name="ck_takeoff_measurements_confirmed_cal"),
  )
  op.create_index("ix_takeoff_measurements_sheet", "takeoff_measurements", ["sheet_id"])
  op.create_index("ix_takeoff_measurements_org_project_status", "takeoff_measurements", ["organization_id", "project_id", "status"])

  for t in TABLES:
    _enable(t)

def downgrade() -> None:
  for t in reversed(TABLES):
    op.execute(f"DROP POLICY IF EXISTS {t}_org_isolation ON {t}")
  op.drop_table("takeoff_measurements")
  op.drop_table("takeoff_calibrations")
  op.drop_table("takeoff_sheets")
  op.execute("DELETE FROM quantity_ledger WHERE source_kind = 'PDF_TAKEOFF'")
  op.drop_constraint("ck_quantity_ledger_source_kind", "quantity_ledger", type_="check")
  op.create_check_constraint(
    "ck_quantity_ledger_source_kind", "quantity_ledger",
    "source_kind IN ('MODEL','SCHEDULE_IMPORT','MANUAL','ESTIMATE')")
