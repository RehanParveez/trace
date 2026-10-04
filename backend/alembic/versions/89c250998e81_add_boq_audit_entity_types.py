"""add BOQ audit entity types

Revision ID: 89c250998e81
Revises: 1a80145778fc
Create Date: 2026-10-04 08:52:08.206210
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '89c250998e81'
down_revision: Union[str, Sequence[str], None] = '1a80145778fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    with op.get_context().autocommit_block():
        for value in ("BOQ_VERSION", "BOQ_ADJUSTMENT", "REVIEW_ISSUE"):
            op.execute(
                f"ALTER TYPE audit_entity_type "
                f"ADD VALUE IF NOT EXISTS '{value}'"
            )

def downgrade() -> None:
    pass
    # ### end Alembic commands ###