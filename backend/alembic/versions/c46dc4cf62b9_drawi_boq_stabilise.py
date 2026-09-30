"""drawi_boq stabilise

Revision ID: c46dc4cf62b9
Revises: b7444f5daa3f
Create Date: 2026-09-30 16:28:36.747785
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c46dc4cf62b9"
down_revision: Union[str, Sequence[str], None] = "b7444f5daa3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _constraint_exists(conn, name: str, table: str) -> bool:
    return bool(
        conn.execute(
            sa.text(
                """
                SELECT 1
                FROM pg_constraint c
                JOIN pg_class t ON c.conrelid = t.oid
                JOIN pg_namespace n ON t.relnamespace = n.oid
                WHERE c.conname = :name
                  AND t.relname = :table
                  AND n.nspname = current_schema()
                """
            ),
            {"name": name, "table": table},
        ).scalar()
    )


def upgrade() -> None:
    conn = op.get_bind()

    op.execute(
        """
        UPDATE boq_items
        SET recipe_id = NULL
        WHERE recipe_id IS NOT NULL
          AND recipe_id NOT IN (SELECT id FROM assembly_recipes)
        """
    )

    if _constraint_exists(conn, "fk_boq_items_rule_set_id", "boq_items"):
        op.drop_constraint(
            "fk_boq_items_rule_set_id",
            "boq_items",
            type_="foreignkey",
        )
    op.create_foreign_key(
        "fk_boq_items_rule_set_id",
        "boq_items",
        "measurement_rule_sets",
        ["rule_set_id"],
        ["id"],
        ondelete="SET NULL",
    )

    if not _constraint_exists(conn, "fk_boq_items_recipe_id", "boq_items"):
        op.create_foreign_key(
            "fk_boq_items_recipe_id",
            "boq_items",
            "assembly_recipes",
            ["recipe_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if _constraint_exists(conn, "fk_boq_items_recipe_id", "assembly_recipe_components"):
        op.drop_constraint(
            "fk_boq_items_recipe_id",
            "assembly_recipe_components",
            type_="foreignkey",
        )
    if not _constraint_exists(
        conn, "fk_assembly_recipe_components_recipe_id", "assembly_recipe_components"
    ):
        op.create_foreign_key(
            "fk_assembly_recipe_components_recipe_id",
            "assembly_recipe_components",
            "assembly_recipes",
            ["recipe_id"],
            ["id"],
            ondelete="CASCADE",
        )

    if _constraint_exists(
        conn, "material_normalization_cache_input_hash_key", "material_normalization_cache"
    ):
        op.drop_constraint(
            "material_normalization_cache_input_hash_key",
            "material_normalization_cache",
            type_="unique",
        )

    op.create_index(
        "uq_material_norm_cache_org_hash",
        "material_normalization_cache",
        ["organization_id", "input_hash"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NOT NULL"),
    )
    op.create_index(
        "uq_material_norm_cache_system_hash",
        "material_normalization_cache",
        ["input_hash"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_material_norm_cache_system_hash",
        table_name="material_normalization_cache",
    )
    op.drop_index(
        "uq_material_norm_cache_org_hash",
        table_name="material_normalization_cache",
    )
    op.create_unique_constraint(
        "material_normalization_cache_input_hash_key",
        "material_normalization_cache",
        ["input_hash"],
    )

    op.drop_constraint(
        "fk_assembly_recipe_components_recipe_id",
        "assembly_recipe_components",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_boq_items_recipe_id",
        "assembly_recipe_components",
        "assembly_recipes",
        ["recipe_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint(
        "fk_boq_items_rule_set_id",
        "boq_items",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_boq_items_rule_set_id",
        "boq_items",
        "measurement_rule_sets",
        ["rule_set_id"],
        ["id"],
        ondelete="SET NULL",
    )