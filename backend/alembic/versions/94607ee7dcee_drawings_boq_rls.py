"""drawings_boq rls

Revision ID: 94607ee7dcee
Revises: 9cb1e500a2ec
Create Date: 2026-10-07 21:05:28.052335
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '94607ee7dcee'
down_revision: Union[str, Sequence[str], None] = '9cb1e500a2ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT = "organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid"
ADMIN = "current_setting('app.is_platform_admin', true) = 'true'"

TENANT_TABLES = [
  "drawings", "drawing_elements", "building_levels", "boq_versions", "boq_items", "material_library",
  "boq_item_source_elements", "model_audit_results", "calculation_runs", "run_stage_log",
  "quantity_solids", "staged_quantity_solids", "quantity_ledger", "staged_quantity_ledger",
  "ledger_deductions", "staged_ledger_deductions", "boq_item_ledger_links", "boq_item_adjustments",
  "boq_snapshots", "boq_snapshot_items", "review_issues", "export_jobs", "building_spaces", "space_boundaries",
  "element_relations", "schedule_imports", "schedule_rows", "space_finishes", "rebar_schedule_rows",
  "rebar_bar_marks", "staged_rebar_bar_marks", "labour_rates",
]

SYSTEM_ROW_TABLES = [
  "measurement_rule_sets", "work_items", "assembly_recipes", "rebar_shapes", "bar_sizes", "material_normalization_cache",
]
CHILD_TABLES = {
  "opening_measurement_rules": ("rule_set_id", "measurement_rule_sets"),
  "reinforcement_rules": ("rule_set_id", "measurement_rule_sets"),
  "material_wastage_rules": ("rule_set_id", "measurement_rule_sets"),
  "element_type_mappings": ("rule_set_id", "measurement_rule_sets"),
  "finish_rules": ("rule_set_id", "measurement_rule_sets"),
  "assembly_recipe_components": ("recipe_id", "assembly_recipes"),
}

def _enable(table: str, using: str, check: str) -> None:
  op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
  op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
  op.execute(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}")
  op.execute(f"CREATE POLICY {table}_org_isolation ON {table} USING ({using}) WITH CHECK ({check})")

def upgrade() -> None:
  op.execute("DROP POLICY IF EXISTS tenant_isolation ON labour_rates")
  for t in TENANT_TABLES:
    _enable(t, f"{TENANT} OR {ADMIN}", f"{TENANT} OR {ADMIN}")
  for t in SYSTEM_ROW_TABLES:
    _enable(t, f"organization_id IS NULL OR {TENANT} OR {ADMIN}", f"{TENANT} OR {ADMIN}")
  for t, (fk, parent) in CHILD_TABLES.items():
    visible = f"EXISTS (SELECT 1 FROM {parent} p WHERE p.id = {t}.{fk})"
    writable = (f"EXISTS (SELECT 1 FROM {parent} p WHERE p.id = {t}.{fk} "
                f"AND (p.organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid OR {ADMIN}))")
    _enable(t, visible, writable)

def downgrade() -> None:
  for t in [*TENANT_TABLES, *SYSTEM_ROW_TABLES, *CHILD_TABLES]:
    op.execute(f"DROP POLICY IF EXISTS {t}_org_isolation ON {t}")
    if t != "labour_rates":
      op.execute(f"ALTER TABLE {t} NO FORCE ROW LEVEL SECURITY")
      op.execute(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY")
  op.execute("CREATE POLICY tenant_isolation ON labour_rates "
             "USING (organization_id = current_setting('app.current_org_id')::uuid)")