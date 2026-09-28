"""boq_restrcu tables

Revision ID: b7444f5daa3f
Revises: 1c73529f074e
Create Date: 2026-09-28 18:34:38.260566
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b7444f5daa3f'
down_revision: Union[str, Sequence[str], None] = '1c73529f074e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def _timestamps() -> list:
  return [
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
  ]
 
def upgrade() -> None:
  op.create_table(
    "measurement_rule_sets",
    sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column("code", sa.String(length=50), nullable=False),
    sa.Column("name", sa.String(length=200), nullable=False),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column("is_system", sa.Boolean(), nullable=False),
    sa.Column("is_active", sa.Boolean(), nullable=False),
    sa.Column("opening_deduction_threshold_m2", sa.Numeric(10, 4), nullable=False),
    sa.Column("wall_measurement_method", sa.String(length=30), nullable=False),
    sa.Column("preferred_units", sa.JSON(), nullable=False),
    sa.Column("waste_factors", sa.JSON(), nullable=False),
    sa.Column("net_vs_gross_preference", sa.String(length=10), nullable=False),
    sa.Column("extra_config", sa.JSON(), nullable=False),
    *_timestamps(),
    sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("organization_id", "code", name="uq_measurement_rule_sets_org_code"),
  )
  op.create_index("ix_measurement_rule_sets_org", "measurement_rule_sets", ["organization_id"])
  op.create_index("ix_measurement_rule_sets_organization_id", "measurement_rule_sets", ["organization_id"])
 
  op.create_table(
    "assembly_recipes",
    sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column("code", sa.String(length=80), nullable=False),
    sa.Column("name", sa.String(length=200), nullable=False),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column("trigger_ifc_types", sa.JSON(), nullable=False),
    sa.Column("trigger_conditions", sa.JSON(), nullable=False),
    sa.Column("is_system", sa.Boolean(), nullable=False),
    sa.Column("is_active", sa.Boolean(), nullable=False),
    *_timestamps(),
    sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("organization_id", "code", name="uq_assembly_recipes_org_code"),
  )
  op.create_index("ix_assembly_recipes_org", "assembly_recipes", ["organization_id"])
  op.create_index("ix_assembly_recipes_organization_id", "assembly_recipes", ["organization_id"])
 
  op.create_table(
    "model_audit_results",
    sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("drawing_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("overall_score", sa.Numeric(5, 2), nullable=False),
    sa.Column("issues", sa.JSON(), nullable=False),
    sa.Column("element_count", sa.Integer(), nullable=False),
    sa.Column("missing_material_count", sa.Integer(), nullable=False),
    sa.Column("zero_quantity_count", sa.Integer(), nullable=False),
    sa.Column("unclassified_proxy_count", sa.Integer(), nullable=False),
    sa.Column("extra_stats", sa.JSON(), nullable=False),
    *_timestamps(),
    sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    sa.ForeignKeyConstraint(["drawing_id"], ["drawings.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
  )
  op.create_index("ix_model_audit_results_drawing", "model_audit_results", ["drawing_id"])
  op.create_index("ix_model_audit_results_organization_id", "model_audit_results", ["organization_id"])
 
  op.create_table(
    "assembly_recipe_components",
    sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("recipe_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("sequence", sa.Integer(), nullable=False),
    sa.Column("work_item_code", sa.String(length=50), nullable=True),
    sa.Column("description_template", sa.String(length=500), nullable=False),
    sa.Column("unit", sa.String(length=20), nullable=False),
    sa.Column("quantity_factor", sa.Numeric(12, 6), nullable=False),
    sa.Column("quantity_formula", sa.String(length=300), nullable=True),
    sa.Column("category", sa.String(length=150), nullable=True),
    sa.Column(
      "item_type",
      postgresql.ENUM("MATERIAL", "LABOUR", "CUSTOM", name="boq_item_type", create_type=False),
      nullable=False,
    ),
    sa.Column("waste_factor", sa.Numeric(8, 4), nullable=False),
    sa.Column("is_optional", sa.Boolean(), nullable=False),
    *_timestamps(),
    sa.ForeignKeyConstraint(["recipe_id"], ["assembly_recipes.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
  )
  op.create_index("ix_assembly_recipe_components_recipe", "assembly_recipe_components", ["recipe_id"])
 
  op.create_table(
    "element_type_mappings",
    sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("rule_set_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("ifc_type", sa.String(length=100), nullable=False),
    sa.Column("work_item_code", sa.String(length=50), nullable=True),
    sa.Column("default_category", sa.String(length=150), nullable=True),
    sa.Column("quantity_source_preference", sa.String(length=30), nullable=False),
    sa.Column("unit_override", sa.String(length=20), nullable=True),
    sa.Column("confidence_base", sa.Numeric(5, 4), nullable=False),
    sa.Column("extra_mapping", sa.JSON(), nullable=False),
    *_timestamps(),
    sa.ForeignKeyConstraint(["rule_set_id"], ["measurement_rule_sets.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("rule_set_id", "ifc_type", name="uq_element_type_mappings_rule_ifc"),
  )
  op.create_index("ix_element_type_mappings_rule", "element_type_mappings", ["rule_set_id"])
 
  op.add_column("boq_item_source_elements", sa.Column("formula_snippet", sa.String(length=300), nullable=True))
  op.add_column("boq_item_source_elements", sa.Column("contribution_type", sa.String(length=30), nullable=True))
 
  op.add_column("boq_items", sa.Column("work_item_code", sa.String(length=50), nullable=True))
  op.add_column("boq_items", sa.Column("description", sa.Text(), nullable=True))
  op.add_column("boq_items", sa.Column("calculation_formula", sa.String(length=500), nullable=True))
  op.add_column("boq_items", sa.Column("confidence", sa.Numeric(5, 4), nullable=True))
  op.add_column("boq_items", sa.Column("rule_set_id", postgresql.UUID(as_uuid=True), nullable=True))
  op.add_column("boq_items", sa.Column("recipe_id", postgresql.UUID(as_uuid=True), nullable=True))
  op.add_column("boq_items", sa.Column("gross_quantity", sa.Numeric(18, 4), nullable=True))
  op.add_column("boq_items", sa.Column("net_quantity", sa.Numeric(18, 4), nullable=True))
  op.add_column("boq_items", sa.Column("waste_factor_applied", sa.Numeric(8, 4), nullable=True))
  op.add_column(
    "boq_items",
    sa.Column("source_element_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
  )
  op.create_foreign_key(
    "fk_boq_items_rule_set_id", "boq_items", "measurement_rule_sets",
    ["rule_set_id"], ["id"], ondelete="SET NULL",
  )
  op.create_foreign_key(
    "fk_boq_items_recipe_id", "boq_items", "assembly_recipes",
    ["recipe_id"], ["id"], ondelete="SET NULL",
  )

  op.add_column("boq_versions", sa.Column("rule_set_id", postgresql.UUID(as_uuid=True), nullable=True))
  op.add_column("boq_versions", sa.Column("audit_score", sa.Numeric(5, 2), nullable=True))
  op.add_column(
    "boq_versions",
    sa.Column("generation_meta", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
  )
  op.create_foreign_key(
    "fk_boq_versions_rule_set_id", "boq_versions", "measurement_rule_sets",
    ["rule_set_id"], ["id"], ondelete="SET NULL",
  )
 
  op.add_column("drawings", sa.Column("latest_audit_id", postgresql.UUID(as_uuid=True), nullable=True))
  op.create_foreign_key(
    "fk_drawings_latest_audit_id", "drawings", "model_audit_results",
    ["latest_audit_id"], ["id"], ondelete="SET NULL",
  )
 
def downgrade() -> None:

  op.drop_constraint("fk_drawings_latest_audit_id", "drawings", type_="foreignkey")
  op.drop_column("drawings", "latest_audit_id")
 
  op.drop_constraint("fk_boq_versions_rule_set_id", "boq_versions", type_="foreignkey")
  op.drop_column("boq_versions", "generation_meta")
  op.drop_column("boq_versions", "audit_score")
  op.drop_column("boq_versions", "rule_set_id")
 
  op.drop_constraint("fk_boq_items_recipe_id", "boq_items", type_="foreignkey")
  op.drop_constraint("fk_boq_items_rule_set_id", "boq_items", type_="foreignkey")
  op.drop_column("boq_items", "source_element_count")
  op.drop_column("boq_items", "waste_factor_applied")
  op.drop_column("boq_items", "net_quantity")
  op.drop_column("boq_items", "gross_quantity")
  op.drop_column("boq_items", "recipe_id")
  op.drop_column("boq_items", "rule_set_id")
  op.drop_column("boq_items", "confidence")
  op.drop_column("boq_items", "calculation_formula")
  op.drop_column("boq_items", "description")
  op.drop_column("boq_items", "work_item_code")
 
  op.drop_column("boq_item_source_elements", "contribution_type")
  op.drop_column("boq_item_source_elements", "formula_snippet")
 
  op.drop_table("element_type_mappings")
  op.drop_table("assembly_recipe_components")
  op.drop_table("model_audit_results")
  op.drop_table("assembly_recipes")
  op.drop_table("measurement_rule_sets")
 