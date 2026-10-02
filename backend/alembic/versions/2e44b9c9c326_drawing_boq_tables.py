"""drawing_boq_tables

Revision ID: 2e44b9c9c326
Revises: 6c66b904251a
Create Date: 2026-10-01 18:42:49.093630
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '2e44b9c9c326'
down_revision: Union[str, Sequence[str], None] = '6c66b904251a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UNIT_TO_FORMULA = {
  "m3": "SOLID_NET_VOLUME",
  "m2": "WALL_FACE_AREA_NET",   
  "m":  "SOLID_NET_VOLUME",   

  "cft": "SOLID_NET_VOLUME",    
  "sft": "WALL_FACE_AREA_NET", 
  "nos": "OPENING_COUNT",       
  "rft": "SOLID_NET_VOLUME",    
  "kg":  "REBAR_KG",       
}
 
def _ts():
  return [
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
  ]
 
def _uuid_pk():
  return sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True)
 
def _jsonb(name):
  return sa.Column(name, postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
 
def upgrade() -> None:
  conn = op.get_bind()

  op.create_table(
    "measurement_conventions",
    _uuid_pk(),
    sa.Column("code", sa.String(80), nullable=False),
    sa.Column("name", sa.String(200), nullable=False),
    sa.Column("description", sa.Text),
    sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.text("true")),
    sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    sa.Column("conserves_volume", sa.Boolean, nullable=False, server_default=sa.text("true")),
    _jsonb("parameters"),
    *_ts(),
    sa.UniqueConstraint("code", name="uq_measurement_conventions_code"),
  )
  op.create_index("ix_measurement_conventions_active", "measurement_conventions", ["is_active"])
 
  t = "measurement_rule_sets"
  op.add_column(t, sa.Column("jurisdiction", sa.String(50)))
  op.add_column(t, sa.Column("province", sa.String(50)))
  op.add_column(t, sa.Column("city", sa.String(100)))
  op.add_column(t, sa.Column("standard_name", sa.String(100)))
  op.add_column(t, sa.Column("standard_edition", sa.String(50)))
  op.add_column(t, sa.Column("effective_from", sa.Date))
  op.add_column(t, sa.Column("effective_to", sa.Date))
  op.add_column(t, sa.Column("convention_code", sa.String(80)))
  op.add_column(t, sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"))
  op.add_column(t, sa.Column("immutable_version", sa.Integer, nullable=False, server_default=sa.text("1")))
  op.add_column(t, sa.Column("published_at", sa.DateTime(timezone=True)))
  op.add_column(t, sa.Column("published_by_user_id", postgresql.UUID(as_uuid=True)))
  op.add_column(t, sa.Column("content_hash", sa.String(64)))
  op.add_column(t, sa.Column("supersedes_rule_set_id", postgresql.UUID(as_uuid=True)))
 
  op.execute("""
    UPDATE measurement_rule_sets
       SET status = CASE WHEN is_active THEN 'ACTIVE' ELSE 'ARCHIVED' END,
           published_at = now()
  """)
 
  op.create_foreign_key("fk_measurement_rule_sets_convention_code", t, "measurement_conventions",
                        ["convention_code"], ["code"], ondelete="RESTRICT")
  op.create_foreign_key("fk_measurement_rule_sets_published_by", t, "users",
                        ["published_by_user_id"], ["id"], ondelete="SET NULL")
  op.create_foreign_key("fk_measurement_rule_sets_supersedes", t, t,
                        ["supersedes_rule_set_id"], ["id"], ondelete="SET NULL")
 
  op.create_check_constraint("ck_measurement_rule_sets_status", t,
                             "status IN ('DRAFT','ACTIVE','SUPERSEDED','ARCHIVED')")
  op.create_check_constraint("ck_measurement_rule_sets_net_gross", t,
                             "net_vs_gross_preference IN ('net','gross')")
  op.create_check_constraint("ck_measurement_rule_sets_version_pos", t, "immutable_version >= 1")
  op.create_check_constraint("ck_measurement_rule_sets_effective_range", t,
                             "effective_from IS NULL OR effective_to IS NULL OR effective_to >= effective_from")
  op.create_check_constraint("ck_measurement_rule_sets_published_at", t,
                             "status = 'DRAFT' OR published_at IS NOT NULL")
 
  op.drop_constraint("uq_measurement_rule_sets_org_code", t, type_="unique")
  op.create_unique_constraint("uq_measurement_rule_sets_org_code_version", t,
                              ["organization_id", "code", "immutable_version"])
  op.create_index("uq_measurement_rule_sets_system_code_version", t, ["code", "immutable_version"],
                  unique=True, postgresql_where=sa.text("organization_id IS NULL"))
  op.create_index("uq_measurement_rule_sets_active_org", t, ["organization_id", "code"], unique=True,
                  postgresql_where=sa.text("status = 'ACTIVE' AND organization_id IS NOT NULL"))
  op.create_index("uq_measurement_rule_sets_active_system", t, ["code"], unique=True,
                  postgresql_where=sa.text("status = 'ACTIVE' AND organization_id IS NULL"))
  op.create_index("ix_measurement_rule_sets_status", t, ["status"])

  op.create_table(
    "opening_measurement_rules",
    _uuid_pk(),
    sa.Column("rule_set_id", postgresql.UUID(as_uuid=True),
              sa.ForeignKey("measurement_rule_sets.id", ondelete="CASCADE"), nullable=False),
    sa.Column("element_scope", sa.String(50), nullable=False, server_default="ALL"),
    sa.Column("lower_area_m2", sa.Numeric(10, 4), nullable=False, server_default="0"),
    sa.Column("upper_area_m2", sa.Numeric(10, 4)),
    sa.Column("deduction_behavior", sa.String(20), nullable=False, server_default="DEDUCT"),
    sa.Column("deduction_fraction", sa.Numeric(5, 4)),
    sa.Column("edge_behavior", sa.String(50)),
    _jsonb("extra_config"),
    *_ts(),
    sa.UniqueConstraint("rule_set_id", "element_scope", "lower_area_m2",
                        name="uq_opening_measurement_rules_scope_lower"),
    sa.CheckConstraint("deduction_behavior IN ('DEDUCT','IGNORE','PARTIAL')",
                       name="ck_opening_measurement_rules_deduction"),
    sa.CheckConstraint("lower_area_m2 >= 0", name="ck_opening_measurement_rules_lower"),
    sa.CheckConstraint("upper_area_m2 IS NULL OR upper_area_m2 > lower_area_m2",
                       name="ck_opening_measurement_rules_range"),
    sa.CheckConstraint("deduction_fraction IS NULL OR (deduction_fraction >= 0 AND deduction_fraction <= 1)",
                       name="ck_opening_measurement_rules_fraction"),
    sa.CheckConstraint("deduction_behavior <> 'PARTIAL' OR deduction_fraction IS NOT NULL",
                       name="ck_opening_measurement_rules_partial_needs_fraction"),
  )
  op.create_index("ix_opening_measurement_rules_rule_set", "opening_measurement_rules", ["rule_set_id"])
 
  op.create_table(
    "material_wastage_rules",
    _uuid_pk(),
    sa.Column("rule_set_id", postgresql.UUID(as_uuid=True),
              sa.ForeignKey("measurement_rule_sets.id", ondelete="CASCADE"), nullable=False),
    sa.Column("material_class", sa.String(80), nullable=False),
    sa.Column("procurement_stage", sa.String(40), nullable=False, server_default="SITE"),
    sa.Column("factor", sa.Numeric(8, 4), nullable=False, server_default="1.0"),
    sa.Column("unit", sa.String(20)),
    sa.Column("justification", sa.Text),
    *_ts(),
    sa.UniqueConstraint("rule_set_id", "material_class", "procurement_stage",
                        name="uq_material_wastage_rules_class_stage"),
    sa.CheckConstraint("factor >= 1 AND factor <= 2", name="ck_material_wastage_rules_factor"),
  )
  op.create_index("ix_material_wastage_rules_rule_set", "material_wastage_rules", ["rule_set_id"])
 
  op.create_table(
    "reinforcement_rules",
    _uuid_pk(),
    sa.Column("rule_set_id", postgresql.UUID(as_uuid=True),
              sa.ForeignKey("measurement_rule_sets.id", ondelete="CASCADE"), nullable=False),
    sa.Column("element_scope", sa.String(50), nullable=False, server_default="ALL"),
    sa.Column("bar_role", sa.String(50), nullable=False),
    sa.Column("lap_basis", sa.String(30)),
    sa.Column("lap_coefficient", sa.Numeric(8, 4)),
    _jsonb("hook_rules"),
    _jsonb("bend_rules"),
    sa.Column("dev_length_method", sa.String(40)),
    _jsonb("splice_constraints"),
    _jsonb("extra_config"),
    *_ts(),
    sa.UniqueConstraint("rule_set_id", "element_scope", "bar_role", name="uq_reinforcement_rules_scope_role"),
    sa.CheckConstraint("lap_coefficient IS NULL OR lap_coefficient >= 0", name="ck_reinforcement_rules_lap_coeff"),
  )
  op.create_index("ix_reinforcement_rules_rule_set", "reinforcement_rules", ["rule_set_id"])
 
  op.create_table(
    "work_items",
    _uuid_pk(),
    sa.Column("organization_id", postgresql.UUID(as_uuid=True),
              sa.ForeignKey("organizations.id", ondelete="CASCADE")),
    sa.Column("code", sa.String(50), nullable=False),
    sa.Column("description", sa.String(500), nullable=False),
    sa.Column("unit", sa.String(20), nullable=False),
    sa.Column("trade", sa.String(80)),
    sa.Column("wbs_code", sa.String(50)),
    sa.Column("specification", sa.Text),
    sa.Column("csr_ref", sa.String(80)),
    sa.Column("default_formula_code", sa.String(80)),
    sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.text("false")),
    sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    _jsonb("extra"),
    *_ts(),
    sa.UniqueConstraint("organization_id", "code", name="uq_work_items_org_code"),
  )
  op.create_index("ix_work_items_org", "work_items", ["organization_id"])
  op.create_index("ix_work_items_code", "work_items", ["code"])
  op.create_index("uq_work_items_system_code", "work_items", ["code"], unique=True,
      postgresql_where=sa.text("organization_id IS NULL"))
 
  op.execute("""
    INSERT INTO opening_measurement_rules
      (id, rule_set_id, element_scope, lower_area_m2, upper_area_m2, deduction_behavior, extra_config, created_at, updated_at)
    SELECT gen_random_uuid(), id, 'ALL', 0, opening_deduction_threshold_m2, 'IGNORE', '{}'::jsonb, now(), now()
      FROM measurement_rule_sets WHERE opening_deduction_threshold_m2 > 0
    UNION ALL
    SELECT gen_random_uuid(), id, 'ALL', opening_deduction_threshold_m2, NULL, 'DEDUCT', '{}'::jsonb, now(), now()
      FROM measurement_rule_sets
  """)
 
  rows = conn.execute(sa.text("SELECT id, waste_factors FROM measurement_rule_sets")).fetchall()
  for rs_id, wf in rows:
    if not isinstance(wf, dict):
      continue
    for material_class, factor in wf.items():
      try:
        f = float(factor)
      except (TypeError, ValueError):
        print(f"[p2] skip non-numeric waste factor {material_class}={factor!r} (rule_set {rs_id})")
        continue
      if not (1.0 <= f <= 2.0):
        print(f"[p2] SKIP waste factor {material_class}={f} (rule_set {rs_id}) – not in [1,2], fix manually")
        continue
      conn.execute(sa.text("""
        INSERT INTO material_wastage_rules
          (id, rule_set_id, material_class, procurement_stage, factor, created_at, updated_at)
        VALUES (gen_random_uuid(), :rs, :mc, 'SITE', :f, now(), now())
        ON CONFLICT DO NOTHING
      """), {"rs": rs_id, "mc": str(material_class).upper(), "f": f})
 
  op.add_column("assembly_recipes", sa.Column("rule_set_id", postgresql.UUID(as_uuid=True)))
  op.create_foreign_key("fk_assembly_recipes_rule_set_id", "assembly_recipes", "measurement_rule_sets",
                        ["rule_set_id"], ["id"], ondelete="CASCADE")
  op.drop_constraint("uq_assembly_recipes_org_code", "assembly_recipes", type_="unique")
  op.create_index("uq_assembly_recipes_ruleset_code", "assembly_recipes", ["rule_set_id", "code"], unique=True,
                  postgresql_where=sa.text("rule_set_id IS NOT NULL"))
  op.create_index("uq_assembly_recipes_org_code_unbound", "assembly_recipes", ["organization_id", "code"], unique=True,
                  postgresql_where=sa.text("rule_set_id IS NULL AND organization_id IS NOT NULL"))
  op.create_index("uq_assembly_recipes_system_code_unbound", "assembly_recipes", ["code"], unique=True,
                  postgresql_where=sa.text("rule_set_id IS NULL AND organization_id IS NULL"))
  op.create_index("ix_assembly_recipes_rule_set", "assembly_recipes", ["rule_set_id"])
 
  c = "assembly_recipe_components"
  op.add_column(c, sa.Column("quantity_formula_code", sa.String(80)))
  op.add_column(c, sa.Column("output_unit", sa.String(20)))
  op.execute("UPDATE assembly_recipe_components SET output_unit = unit")
  for unit, code in UNIT_TO_FORMULA.items():
    conn.execute(sa.text("UPDATE assembly_recipe_components SET quantity_formula_code = :c WHERE unit = :u"),
      {"c": code, "u": unit})
  op.execute("UPDATE assembly_recipe_components SET quantity_formula_code = 'LEGACY_UNMAPPED' WHERE quantity_formula_code IS NULL")
  op.execute("""
    UPDATE assembly_recipes SET is_active = false
     WHERE id IN (SELECT recipe_id FROM assembly_recipe_components WHERE quantity_formula_code = 'LEGACY_UNMAPPED')
  """)
  op.alter_column(c, "quantity_formula_code", nullable=False)
  op.alter_column(c, "output_unit", nullable=False)
 
  op.execute("ALTER TABLE assembly_recipe_components ALTER COLUMN item_type TYPE VARCHAR(20) USING item_type::text")
  op.create_check_constraint("ck_assembly_recipe_components_item_type", c,
                             "item_type IN ('MATERIAL','LABOUR','CUSTOM')")
  op.create_check_constraint("ck_assembly_recipe_components_unit_safe", c, "unit = output_unit")
  op.create_check_constraint("ck_assembly_recipe_components_waste", c, "waste_factor >= 1")
 
  op.alter_column(c, "quantity_factor", nullable=True, server_default="1.0")
 
  op.execute("""
    CREATE OR REPLACE FUNCTION ruleset_is_locked(rs uuid) RETURNS boolean AS $$
      SELECT COALESCE((SELECT status <> 'DRAFT' FROM measurement_rule_sets WHERE id = rs), false)
    $$ LANGUAGE sql STABLE;
  """)
 
  op.execute("""
    CREATE OR REPLACE FUNCTION trg_ruleset_immutable() RETURNS trigger AS $$
    DECLARE ignore_cols text[] := ARRAY['status','effective_to','is_active','updated_at'];
    BEGIN
      IF TG_OP = 'DELETE' THEN
        IF OLD.status <> 'DRAFT' THEN
          RAISE EXCEPTION 'Published rule set % is immutable and cannot be deleted', OLD.id;
        END IF;
        RETURN OLD;
      END IF;
      IF OLD.status <> 'DRAFT' THEN
        IF (to_jsonb(NEW) - ignore_cols) IS DISTINCT FROM (to_jsonb(OLD) - ignore_cols) THEN
          RAISE EXCEPTION 'Published rule set % is immutable (only status/effective_to may change)', OLD.id;
        END IF;
        IF NEW.status <> OLD.status AND NOT (
             (OLD.status = 'ACTIVE'     AND NEW.status IN ('SUPERSEDED','ARCHIVED')) OR
             (OLD.status = 'SUPERSEDED' AND NEW.status = 'ARCHIVED')) THEN
          RAISE EXCEPTION 'Illegal rule set status transition % -> %', OLD.status, NEW.status;
        END IF;
      END IF;
      RETURN NEW;
    END $$ LANGUAGE plpgsql;
  """)
  op.execute("""
    CREATE TRIGGER trg_ruleset_immutable BEFORE UPDATE OR DELETE ON measurement_rule_sets
    FOR EACH ROW EXECUTE FUNCTION trg_ruleset_immutable();
  """)
 
  op.execute("""
    CREATE OR REPLACE FUNCTION trg_ruleset_child_immutable() RETURNS trigger AS $$
    BEGIN
      IF TG_OP IN ('UPDATE','DELETE') AND ruleset_is_locked(OLD.rule_set_id) THEN
        RAISE EXCEPTION 'Rule set % is published; % on % is not allowed', OLD.rule_set_id, TG_OP, TG_TABLE_NAME;
      END IF;
      IF TG_OP IN ('INSERT','UPDATE') AND ruleset_is_locked(NEW.rule_set_id) THEN
        RAISE EXCEPTION 'Rule set % is published; % on % is not allowed', NEW.rule_set_id, TG_OP, TG_TABLE_NAME;
      END IF;
      IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
      RETURN NEW;
    END $$ LANGUAGE plpgsql;
  """)
  for tbl in ("opening_measurement_rules", "material_wastage_rules", "reinforcement_rules",
              "element_type_mappings", "assembly_recipes"):
    op.execute(f"""
      CREATE TRIGGER trg_{tbl}_immutable BEFORE INSERT OR UPDATE OR DELETE ON {tbl}
      FOR EACH ROW EXECUTE FUNCTION trg_ruleset_child_immutable();
    """)
 
  op.execute("""
    CREATE OR REPLACE FUNCTION trg_recipe_component_immutable() RETURNS trigger AS $$
    DECLARE rid uuid;
    BEGIN
      IF TG_OP IN ('UPDATE','DELETE') THEN
        SELECT rule_set_id INTO rid FROM assembly_recipes WHERE id = OLD.recipe_id;
        IF ruleset_is_locked(rid) THEN RAISE EXCEPTION 'Recipe belongs to a published rule set (immutable)'; END IF;
      END IF;
      IF TG_OP IN ('INSERT','UPDATE') THEN
        SELECT rule_set_id INTO rid FROM assembly_recipes WHERE id = NEW.recipe_id;
        IF ruleset_is_locked(rid) THEN RAISE EXCEPTION 'Recipe belongs to a published rule set (immutable)'; END IF;
      END IF;
      IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
      RETURN NEW;
    END $$ LANGUAGE plpgsql;
  """)
  op.execute("""
    CREATE TRIGGER trg_assembly_recipe_components_immutable
    BEFORE INSERT OR UPDATE OR DELETE ON assembly_recipe_components
    FOR EACH ROW EXECUTE FUNCTION trg_recipe_component_immutable();
  """)
 
def downgrade() -> None:
  op.execute("DROP TRIGGER IF EXISTS trg_assembly_recipe_components_immutable ON assembly_recipe_components")
  for tbl in ("opening_measurement_rules", "material_wastage_rules", "reinforcement_rules",
      "element_type_mappings", "assembly_recipes"):
    op.execute(f"DROP TRIGGER IF EXISTS trg_{tbl}_immutable ON {tbl}")
  op.execute("DROP TRIGGER IF EXISTS trg_ruleset_immutable ON measurement_rule_sets")
  op.execute("DROP FUNCTION IF EXISTS trg_recipe_component_immutable()")
  op.execute("DROP FUNCTION IF EXISTS trg_ruleset_child_immutable()")
  op.execute("DROP FUNCTION IF EXISTS trg_ruleset_immutable()")
  op.execute("DROP FUNCTION IF EXISTS ruleset_is_locked(uuid)")
 
  # components
  c = "assembly_recipe_components"
  op.drop_constraint("ck_assembly_recipe_components_waste", c, type_="check")
  op.drop_constraint("ck_assembly_recipe_components_unit_safe", c, type_="check")
  op.drop_constraint("ck_assembly_recipe_components_item_type", c, type_="check")
  op.execute("ALTER TABLE assembly_recipe_components ALTER COLUMN item_type TYPE boq_item_type USING item_type::boq_item_type")
  op.execute("UPDATE assembly_recipe_components SET quantity_factor = 1.0 WHERE quantity_factor IS NULL")
  op.alter_column(c, "quantity_factor", nullable=False, server_default=None)
  op.drop_column(c, "output_unit")
  op.drop_column(c, "quantity_formula_code")
 
  for ix in ("ix_assembly_recipes_rule_set", "uq_assembly_recipes_system_code_unbound",
      "uq_assembly_recipes_org_code_unbound", "uq_assembly_recipes_ruleset_code"):
    op.drop_index(ix, table_name="assembly_recipes")
  op.drop_constraint("fk_assembly_recipes_rule_set_id", "assembly_recipes", type_="foreignkey")
  op.drop_column("assembly_recipes", "rule_set_id")
  op.create_unique_constraint("uq_assembly_recipes_org_code", "assembly_recipes", ["organization_id", "code"])
 
  op.drop_table("work_items")
  op.drop_table("reinforcement_rules")
  op.drop_table("material_wastage_rules")
  op.drop_table("opening_measurement_rules")
 
  t = "measurement_rule_sets"
  for ix in ("ix_measurement_rule_sets_status", "uq_measurement_rule_sets_active_system",
      "uq_measurement_rule_sets_active_org", "uq_measurement_rule_sets_system_code_version"):
    op.drop_index(ix, table_name=t)
  op.drop_constraint("uq_measurement_rule_sets_org_code_version", t, type_="unique")
  op.create_unique_constraint("uq_measurement_rule_sets_org_code", t, ["organization_id", "code"])
  for ck in ("published_at", "effective_range", "version_pos", "net_gross", "status"):
    op.drop_constraint(f"ck_measurement_rule_sets_{ck}", t, type_="check")
  for fk in ("supersedes", "published_by", "convention_code"):
    op.drop_constraint(f"fk_measurement_rule_sets_{fk}", t, type_="foreignkey")
  for col in ("supersedes_rule_set_id", "content_hash", "published_by_user_id", "published_at",
      "immutable_version", "status", "convention_code", "effective_to", "effective_from",
      "standard_edition", "standard_name", "city", "province", "jurisdiction"):
    op.drop_column(t, col)
 
  op.drop_table("measurement_conventions")
 