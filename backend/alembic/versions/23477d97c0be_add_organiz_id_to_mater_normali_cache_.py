"""add organiz_id to mater_normali_cache + harden drawi_boq RLS

Revision ID: 23477d97c0be
Revises: 06c3885d71fc
Create Date: 2026-09-17 06:16:21.123627
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '23477d97c0be'
down_revision: Union[str, Sequence[str], None] = '06c3885d71fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    op.add_column(
        "material_normalization_cache",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.create_index(
        "ix_material_normalization_cache_organization",
        "material_normalization_cache",
        ["organization_id"],
    )

    op.create_foreign_key(
        "fk_material_normalization_cache_organization",
        "material_normalization_cache",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )

def downgrade() -> None:
    op.drop_constraint(
        "fk_material_normalization_cache_organization",
        "material_normalization_cache",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_material_normalization_cache_organization",
        table_name="material_normalization_cache",
    )
    op.drop_column("material_normalization_cache", "organization_id")