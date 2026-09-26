"""drawin_boq updat

Revision ID: d89b0712838c
Revises: 6f408575726f
Create Date: 2026-09-26 20:41:07.791307
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd89b0712838c'
down_revision: Union[str, Sequence[str], None] = '6f408575726f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute(
        "ALTER TABLE drawing_elements ADD COLUMN IF NOT EXISTS ifc_global_id VARCHAR(64)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_drawing_elements_ifc_global_id "
        "ON drawing_elements (ifc_global_id)"
    )

    op.create_table(
        "boq_item_source_elements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("boq_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("boq_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("drawing_element_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drawing_elements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity_contributed", sa.Numeric(18, 3), nullable=False),
        sa.UniqueConstraint("boq_item_id", "drawing_element_id", name="uq_boq_item_source_element"),
    )
    op.create_index("ix_boq_item_source_elements_item", "boq_item_source_elements", ["boq_item_id"])
    op.create_index("ix_boq_item_source_elements_element", "boq_item_source_elements", ["drawing_element_id"])

def downgrade() -> None:
    op.drop_table("boq_item_source_elements")