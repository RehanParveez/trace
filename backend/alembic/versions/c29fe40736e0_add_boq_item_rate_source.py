"""add boq_item rate_source

Revision ID: c29fe40736e0
Revises: bb836ec0b1d2
Create Date: 2026-09-05 16:08:40.041806
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c29fe40736e0'
down_revision: Union[str, Sequence[str], None] = 'bb836ec0b1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
  boq_item_rate_source = sa.Enum('LIBRARY', 'AI_SUGGESTED', 'MANUAL', name='boq_item_rate_source')
  boq_item_rate_source.create(op.get_bind(), checkfirst=True)
  op.add_column('boq_items', sa.Column('rate_source', boq_item_rate_source, nullable=True))

def downgrade() -> None:
  op.drop_column('boq_items', 'rate_source')
  sa.Enum(name='boq_item_rate_source').drop(op.get_bind(), checkfirst=True)