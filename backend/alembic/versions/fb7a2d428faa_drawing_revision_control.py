"""drawing revision control

Revision ID: fb7a2d428faa
Revises: 531da87dd0e4
Create Date: 2026-09-23 03:52:21.105918
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'fb7a2d428faa'
down_revision: Union[str, Sequence[str], None] = '531da87dd0e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("drawings", sa.Column("revision_group_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("drawings", sa.Column("revision_label", sa.String(50), nullable=True))
    op.add_column("drawings", sa.Column("is_current_revision", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("drawings", sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True))

    # Every existing drawing becomes the root of its own single-drawing
    # revision group.
    op.execute("UPDATE drawings SET revision_group_id = id WHERE revision_group_id IS NULL")

    op.alter_column("drawings", "revision_group_id", nullable=False)
    op.create_index("ix_drawings_revision_group", "drawings", ["revision_group_id"])
    op.create_foreign_key(
        "fk_drawings_revision_group", "drawings", "drawings",
        ["revision_group_id"], ["id"], ondelete="RESTRICT",
    )

def downgrade() -> None:
    op.drop_constraint("fk_drawings_revision_group", "drawings", type_="foreignkey")
    op.drop_index("ix_drawings_revision_group", table_name="drawings")
    op.drop_column("drawings", "superseded_at")
    op.drop_column("drawings", "is_current_revision")
    op.drop_column("drawings", "revision_label")
    op.drop_column("drawings", "revision_group_id")