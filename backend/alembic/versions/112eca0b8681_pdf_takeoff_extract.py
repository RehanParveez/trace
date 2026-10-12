"""pdf_takeoff_extract

Revision ID: 112eca0b8681
Revises: 1df9edecefa3
Create Date: 2026-10-12 15:44:53.031503
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '112eca0b8681'
down_revision: Union[str, Sequence[str], None] = '1df9edecefa3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT = "organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid"
ADMIN = "current_setting('app.is_platform_admin', true) = 'true'"
TABLES = ("takeoff_extractions", "takeoff_candidates")

def _jsonb(name: str, default: str):
  return sa.Column(name, postgresql.JSONB(), server_default=sa.text(default), nullable=False)

def _stamps():
  return [sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)]

def upgrade() -> None:
  op.create_table(
    "takeoff_extractions",
    sa.Column("sheet_id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
    sa.Column("extract_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    sa.Column("index_stamp", sa.String(40), nullable=True),
    sa.Column("calibration_id", postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column("mm_per_pt", sa.Numeric(24, 12), nullable=True),
    sa.Column("scale_unverified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    _jsonb("stats", "'{}'::jsonb"), _jsonb("unmapped_tags", "'[]'::jsonb"), _jsonb("notes", "'[]'::jsonb"),
    sa.Column("ran_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    *_stamps(),
    sa.ForeignKeyConstraint(["sheet_id", "organization_id"], ["takeoff_sheets.id", "takeoff_sheets.organization_id"],
      ondelete="CASCADE", name="fk_takeoff_extractions_sheet_tenant"),
    sa.CheckConstraint("extract_version >= 1", name="ck_takeoff_extractions_version"),
  )
  
  op.create_table(
    "takeoff_candidates",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
    sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    sa.Column("sheet_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("ckey", sa.String(40), nullable=False),
    sa.Column("category", sa.String(10), nullable=False),
    sa.Column("kind", sa.String(8), nullable=False),
    sa.Column("quantity_mode", sa.String(40), nullable=False),
    sa.Column("label", sa.String(200), nullable=False),
    sa.Column("tag", sa.String(60), nullable=True),
    _jsonb("geometry", "'{}'::jsonb"), _jsonb("params", "'{}'::jsonb"), _jsonb("missing", "'[]'::jsonb"),
    sa.Column("suggested_work_item", sa.String(50), nullable=True),
    sa.Column("count", sa.Integer(), server_default=sa.text("1"), nullable=False),
    sa.Column("status", sa.String(10), server_default="VALID", nullable=False),
    sa.Column("confidence", sa.Numeric(5, 4), server_default=sa.text("0"), nullable=False),
    _jsonb("facts", "'{}'::jsonb"), _jsonb("notes", "'[]'::jsonb"),
    sa.Column("source", sa.String(12), server_default="VECTOR_SNAP", nullable=False),
    sa.Column("decision", sa.String(10), server_default="NEW", nullable=False),
    sa.Column("measurement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("takeoff_measurements.id", ondelete="SET NULL"), nullable=True),
    sa.Column("extract_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    sa.Column("mm_per_pt", sa.Numeric(24, 12), nullable=True),
    sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    *_stamps(),
    sa.ForeignKeyConstraint(["sheet_id", "organization_id"], ["takeoff_sheets.id", "takeoff_sheets.organization_id"],
      ondelete="CASCADE", name="fk_takeoff_candidates_sheet_tenant"),
    sa.UniqueConstraint("sheet_id", "ckey", name="uq_takeoff_candidates_sheet_key"),
    sa.CheckConstraint("category IN ('COLUMN','FOOTING','BEAM','DOOR','WINDOW','WALL','ROOM')", name="ck_takeoff_candidates_category"),
    sa.CheckConstraint("kind IN ('LENGTH','AREA','COUNT')", name="ck_takeoff_candidates_kind"),
    sa.CheckConstraint("status IN ('VALID','WARNING','INVALID')", name="ck_takeoff_candidates_status"),
    sa.CheckConstraint("decision IN ('NEW','ACCEPTED','REJECTED')", name="ck_takeoff_candidates_decision"),
    sa.CheckConstraint("source IN ('MANUAL','VECTOR_SNAP','TAG_SCAN')", name="ck_takeoff_candidates_source"),
    sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_takeoff_candidates_confidence"),
    sa.CheckConstraint("count >= 1", name="ck_takeoff_candidates_count"),
  )
  
  op.create_index("ix_takeoff_candidates_sheet", "takeoff_candidates", ["sheet_id"])
  op.create_index("ix_takeoff_candidates_org_project", "takeoff_candidates", ["organization_id", "project_id"])
  for table in TABLES:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}")
    op.execute(f"CREATE POLICY {table}_org_isolation ON {table} USING ({TENANT} OR {ADMIN}) WITH CHECK ({TENANT} OR {ADMIN})")

def downgrade() -> None:
  for table in reversed(TABLES):
    op.execute(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}")
    op.drop_table(table)
