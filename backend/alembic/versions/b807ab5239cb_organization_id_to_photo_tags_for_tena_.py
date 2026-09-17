"""organization_id to photo_tags for tena.isola

Revision ID: b807ab5239cb
Revises: 23477d97c0be
Create Date: 2026-09-17 06:41:49.381425
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b807ab5239cb'
down_revision: Union[str, Sequence[str], None] = '23477d97c0be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "photo_tags",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.execute("""
        UPDATE photo_tags pt
        SET organization_id = sp.organization_id
        FROM site_photos sp
        WHERE pt.site_photo_id = sp.id
    """)

    op.alter_column(
        "photo_tags",
        "organization_id",
        nullable=False,
    )

    op.create_foreign_key(
        "fk_photo_tags_organization",
        "photo_tags",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_index(
        "ix_photo_tags_organization",
        "photo_tags",
        ["organization_id"],
    )

def downgrade() -> None:
    op.drop_index("ix_photo_tags_organization", table_name="photo_tags")
    op.drop_constraint("fk_photo_tags_organization", "photo_tags", type_="foreignkey")
    op.drop_column("photo_tags", "organization_id")