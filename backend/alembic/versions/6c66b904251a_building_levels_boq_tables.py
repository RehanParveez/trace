"""building_levels_boq tables

Revision ID: 6c66b904251a
Revises: c46dc4cf62b9
Create Date: 2026-10-01 08:33:26.451977
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '6c66b904251a'
down_revision: Union[str, Sequence[str], None] = 'c46dc4cf62b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "building_levels",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("drawing_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("elevation_mm", sa.Numeric(precision=14, scale=3), nullable=True),
        sa.Column("ifc_storey_id", sa.String(length=64), nullable=True),
        sa.Column("sequence", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["drawing_id"], ["drawings.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "drawing_id", "ifc_storey_id", name="uq_building_levels_drawing_storey"
        ),
    )
    op.create_index(
        "ix_building_levels_drawing_sequence",
        "building_levels",
        ["drawing_id", "sequence"],
        unique=False,
    )
    op.create_index(
        op.f("ix_building_levels_organization_id"),
        "building_levels",
        ["organization_id"],
        unique=False,
    )

    op.add_column(
        "drawings",
        sa.Column(
            "ingestion_meta",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )

    op.add_column(
        "drawing_elements",
        sa.Column("discipline", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "drawing_elements",
        sa.Column("structural_role", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "drawing_elements",
        sa.Column("classification_source", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "drawing_elements",
        sa.Column(
            "classification_confidence",
            sa.Numeric(precision=5, scale=4),
            nullable=True,
        ),
    )
    op.add_column(
        "drawing_elements",
        sa.Column("quantity_source", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "drawing_elements",
        sa.Column("level_id", sa.UUID(), nullable=True),
    )

    op.add_column(
        "drawing_elements",
        sa.Column("length_mm", sa.Numeric(precision=14, scale=3), nullable=True),
    )
    op.add_column(
        "drawing_elements",
        sa.Column("width_mm", sa.Numeric(precision=14, scale=3), nullable=True),
    )
    op.add_column(
        "drawing_elements",
        sa.Column("height_mm", sa.Numeric(precision=14, scale=3), nullable=True),
    )
    op.add_column(
        "drawing_elements",
        sa.Column("thickness_mm", sa.Numeric(precision=14, scale=3), nullable=True),
    )
    op.add_column(
        "drawing_elements",
        sa.Column(
            "elevation_base_mm", sa.Numeric(precision=14, scale=3), nullable=True
        ),
    )
    op.add_column(
        "drawing_elements",
        sa.Column(
            "elevation_top_mm", sa.Numeric(precision=14, scale=3), nullable=True
        ),
    )
    op.add_column(
        "drawing_elements",
        sa.Column("area_mm2", sa.Numeric(precision=20, scale=3), nullable=True),
    )
    op.add_column(
        "drawing_elements",
        sa.Column("volume_mm3", sa.Numeric(precision=24, scale=3), nullable=True),
    )

    op.add_column(
        "drawing_elements",
        sa.Column("bbox_min_x_mm", sa.Numeric(precision=14, scale=3), nullable=True),
    )
    op.add_column(
        "drawing_elements",
        sa.Column("bbox_min_y_mm", sa.Numeric(precision=14, scale=3), nullable=True),
    )
    op.add_column(
        "drawing_elements",
        sa.Column("bbox_min_z_mm", sa.Numeric(precision=14, scale=3), nullable=True),
    )
    op.add_column(
        "drawing_elements",
        sa.Column("bbox_max_x_mm", sa.Numeric(precision=14, scale=3), nullable=True),
    )
    op.add_column(
        "drawing_elements",
        sa.Column("bbox_max_y_mm", sa.Numeric(precision=14, scale=3), nullable=True),
    )
    op.add_column(
        "drawing_elements",
        sa.Column("bbox_max_z_mm", sa.Numeric(precision=14, scale=3), nullable=True),
    )

    op.add_column(
        "drawing_elements",
        sa.Column("geometry_kind", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "drawing_elements",
        sa.Column("profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "drawing_elements",
        sa.Column(
            "placement", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "drawing_elements",
        sa.Column(
            "normalization_status",
            sa.String(length=10),
            server_default="PENDING",
            nullable=False,
        ),
    )
    op.add_column(
        "drawing_elements",
        sa.Column(
            "normalization_issues",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_drawing_elements_org_drawing_type",
        "drawing_elements",
        ["organization_id", "drawing_id", "ifc_type"],
        unique=False,
    )
    op.create_index(
        "ix_drawing_elements_drawing_level_role",
        "drawing_elements",
        ["drawing_id", "level_id", "structural_role"],
        unique=False,
    )
    op.create_index(
        "ix_drawing_elements_drawing_status",
        "drawing_elements",
        ["drawing_id", "normalization_status"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_drawing_elements_level_id",
        "drawing_elements",
        "building_levels",
        ["level_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_check_constraint(
        "ck_drawing_elements_geometry_kind",
        "drawing_elements",
        "geometry_kind IS NULL OR geometry_kind IN "
        "('EXTRUDED_PROFILE','AXIS_SWEPT','BOX_ONLY','QTO_ONLY','UNSUPPORTED')",
    )
    op.create_check_constraint(
        "ck_drawing_elements_normalization_status",
        "drawing_elements",
        "normalization_status IN ('PENDING','VALID','WARNING','INVALID')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_drawing_elements_normalization_status",
        "drawing_elements",
        type_="check",
    )
    op.drop_constraint(
        "ck_drawing_elements_geometry_kind",
        "drawing_elements",
        type_="check",
    )

    op.drop_constraint(
        "fk_drawing_elements_level_id", "drawing_elements", type_="foreignkey"
    )

    op.drop_index(
        "ix_drawing_elements_drawing_status", table_name="drawing_elements"
    )
    op.drop_index(
        "ix_drawing_elements_drawing_level_role", table_name="drawing_elements"
    )
    op.drop_index(
        "ix_drawing_elements_org_drawing_type", table_name="drawing_elements"
    )

    op.drop_column("drawing_elements", "normalization_issues")
    op.drop_column("drawing_elements", "normalization_status")
    op.drop_column("drawing_elements", "placement")
    op.drop_column("drawing_elements", "profile")
    op.drop_column("drawing_elements", "geometry_kind")
    op.drop_column("drawing_elements", "bbox_max_z_mm")
    op.drop_column("drawing_elements", "bbox_max_y_mm")
    op.drop_column("drawing_elements", "bbox_max_x_mm")
    op.drop_column("drawing_elements", "bbox_min_z_mm")
    op.drop_column("drawing_elements", "bbox_min_y_mm")
    op.drop_column("drawing_elements", "bbox_min_x_mm")
    op.drop_column("drawing_elements", "volume_mm3")
    op.drop_column("drawing_elements", "area_mm2")
    op.drop_column("drawing_elements", "elevation_top_mm")
    op.drop_column("drawing_elements", "elevation_base_mm")
    op.drop_column("drawing_elements", "thickness_mm")
    op.drop_column("drawing_elements", "height_mm")
    op.drop_column("drawing_elements", "width_mm")
    op.drop_column("drawing_elements", "length_mm")
    op.drop_column("drawing_elements", "level_id")
    op.drop_column("drawing_elements", "quantity_source")
    op.drop_column("drawing_elements", "classification_confidence")
    op.drop_column("drawing_elements", "classification_source")
    op.drop_column("drawing_elements", "structural_role")
    op.drop_column("drawing_elements", "discipline")

    op.drop_column("drawings", "ingestion_meta")

    op.drop_index(
        op.f("ix_building_levels_organization_id"), table_name="building_levels"
    )
    op.drop_index(
        "ix_building_levels_drawing_sequence", table_name="building_levels"
    )
    op.drop_table("building_levels")