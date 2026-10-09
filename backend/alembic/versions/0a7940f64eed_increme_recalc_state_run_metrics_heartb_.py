"""increme recalc_state, run metrics & heartb, stage_timis, staging_retent_indexs

Revision ID: 0a7940f64eed
Revises: 015389ebd02b
Create Date: 2026-10-09 07:34:33.923280
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0a7940f64eed'
down_revision: Union[str, Sequence[str], None] = '015389ebd02b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT = "organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid"
ADMIN = "current_setting('app.is_platform_admin', true) = 'true'"
ACTIVE = "status IN ('QUEUED','RUNNING','STAGED','PROMOTED')"
STAGED = [
  ("staged_quantity_solids", "ix_staged_quantity_solids_created"),
  ("staged_quantity_ledger", "ix_staged_quantity_ledger_created"),
  ("staged_ledger_deductions", "ix_staged_ledger_deductions_created"),
  ("staged_rebar_bar_marks", "ix_staged_rebar_bar_marks_created"),
]
NEW_TABLES = ["run_element_state", "run_dependency_edges"]
STAGED_FK_INDEXES = [
  ("staged_quantity_ledger", "ix_staged_quantity_ledger_solid", ["solid_id", "organization_id"]),
  ("staged_ledger_deductions", "ix_staged_ledger_deductions_from_solid", ["from_solid_id", "organization_id"]),
  ("staged_ledger_deductions", "ix_staged_ledger_deductions_to_solid", ["to_solid_id", "organization_id"]),
  ("staged_rebar_bar_marks", "ix_staged_rebar_bar_marks_solid", ["solid_id", "organization_id"]),
]

def _tenant_policy(table: str) -> None:
  op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
  op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
  op.execute(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}")
  op.execute(f"CREATE POLICY {table}_org_isolation ON {table} USING ({TENANT} OR {ADMIN}) WITH CHECK ({TENANT} OR {ADMIN})")

def upgrade() -> None:
  op.add_column("calculation_runs", sa.Column("mode", sa.String(length=12), server_default="FULL", nullable=False))
  op.add_column("calculation_runs", sa.Column("baseline_run_id", postgresql.UUID(as_uuid=True), nullable=True))
  op.add_column("calculation_runs", sa.Column("force_full", sa.Boolean(), server_default=sa.text("false"), nullable=False))
  op.add_column("calculation_runs", sa.Column("verify", sa.Boolean(), server_default=sa.text("false"), nullable=False))
  op.add_column("calculation_runs", sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()),
    server_default=sa.text("'{}'::jsonb"), nullable=False))
  op.add_column("calculation_runs", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
  op.add_column("calculation_runs", sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False))
  op.add_column("calculation_runs", sa.Column("alloc_signature", sa.String(length=64), nullable=True))
  op.add_column("calculation_runs", sa.Column("state_available", sa.Boolean(), server_default=sa.text("false"), nullable=False))
  op.create_foreign_key("fk_calculation_runs_baseline", "calculation_runs", "calculation_runs",
    ["baseline_run_id"], ["id"], ondelete="SET NULL")
  op.create_check_constraint("ck_calculation_runs_mode", "calculation_runs", "mode IN ('FULL','INCREMENTAL')")
  op.create_check_constraint("ck_calculation_runs_attempts", "calculation_runs", "attempts >= 0")
  op.create_index("ix_calculation_runs_org_created", "calculation_runs", ["organization_id", "created_at"])
  op.create_index("ix_calculation_runs_active_heartbeat", "calculation_runs", ["status", "heartbeat_at"],
    postgresql_where=sa.text(ACTIVE))
  op.create_index("ix_calculation_runs_project_state", "calculation_runs", ["project_id", "completed_at"],
    postgresql_where=sa.text("state_available"))

  op.add_column("run_stage_log", sa.Column("duration_ms", sa.Integer(), nullable=True))
  op.add_column("run_stage_log", sa.Column("peak_rss_mb", sa.Integer(), nullable=True))

  op.create_table(
    "run_element_state",
    sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("element_key", sa.String(length=80), nullable=False),
    sa.Column("element_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("solid_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("alloc_hash", sa.String(length=64), nullable=False),
    sa.Column("participating", sa.Boolean(), nullable=False),
    sa.Column("approximate", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column("owned_mm3", postgresql.DOUBLE_PRECISION(), nullable=True),
    sa.Column("bounds", postgresql.ARRAY(postgresql.DOUBLE_PRECISION()), nullable=True),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("run_id", "element_key", name="uq_run_element_state_run_key"),
    sa.ForeignKeyConstraint(["run_id", "organization_id"], ["calculation_runs.id", "calculation_runs.organization_id"],
      ondelete="CASCADE", name="fk_run_element_state_run_tenant"),
  )
  op.create_index("ix_run_element_state_run_element", "run_element_state", ["run_id", "element_id"])
  op.create_index("ix_run_element_state_run_solid", "run_element_state", ["run_id", "solid_id"])

  op.create_table(
    "run_dependency_edges",
    sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("key_a", sa.String(length=80), nullable=False),
    sa.Column("key_b", sa.String(length=80), nullable=False),
    sa.Column("element_a_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("element_b_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("overlap_mm3", postgresql.DOUBLE_PRECISION(), nullable=False),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("run_id", "key_a", "key_b", name="uq_run_dependency_edges_run_pair"),
    sa.CheckConstraint("key_a < key_b", name="ck_run_dependency_edges_ordered"),
    sa.ForeignKeyConstraint(["run_id", "organization_id"], ["calculation_runs.id", "calculation_runs.organization_id"],
      ondelete="CASCADE", name="fk_run_dependency_edges_run_tenant"),
  )
  op.create_index("ix_run_dependency_edges_run_a", "run_dependency_edges", ["run_id", "key_a"])
  op.create_index("ix_run_dependency_edges_run_b", "run_dependency_edges", ["run_id", "key_b"])
  op.create_index("ix_run_dependency_edges_run_ea", "run_dependency_edges", ["run_id", "element_a_id"])
  op.create_index("ix_run_dependency_edges_run_eb", "run_dependency_edges", ["run_id", "element_b_id"])

  for table, name in STAGED:
    op.create_index(name, table, ["created_at"])
  for table, name, cols in STAGED_FK_INDEXES:
    op.create_index(name, table, cols)
  for table in NEW_TABLES:
    _tenant_policy(table)

def downgrade() -> None:
  for table in NEW_TABLES:
    op.execute(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}")
  for table, name, _cols in STAGED_FK_INDEXES:
    op.drop_index(name, table_name=table)
  for table, name in STAGED:
    op.drop_index(name, table_name=table)
  op.drop_table("run_dependency_edges")
  op.drop_table("run_element_state")
  op.drop_column("run_stage_log", "peak_rss_mb")
  op.drop_column("run_stage_log", "duration_ms")
  op.drop_index("ix_calculation_runs_project_state", table_name="calculation_runs")
  op.drop_index("ix_calculation_runs_active_heartbeat", table_name="calculation_runs")
  op.drop_index("ix_calculation_runs_org_created", table_name="calculation_runs")
  op.drop_constraint("ck_calculation_runs_attempts", "calculation_runs", type_="check")
  op.drop_constraint("ck_calculation_runs_mode", "calculation_runs", type_="check")
  op.drop_constraint("fk_calculation_runs_baseline", "calculation_runs", type_="foreignkey")
  for col in ("state_available", "alloc_signature", "attempts", "heartbeat_at", "metrics", "verify", "force_full",
    "baseline_run_id", "mode"):
    op.drop_column("calculation_runs", col)
