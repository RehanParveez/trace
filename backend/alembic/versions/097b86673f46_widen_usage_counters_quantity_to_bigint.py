"""widen usage_counters quantity to bigint

Revision ID: 097b86673f46
Revises: 54bd7e719b6c
Create Date: 2026-09-16 16:00:47.905708
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '097b86673f46'
down_revision: Union[str, Sequence[str], None] = '54bd7e719b6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
  op.alter_column(
    "usage_counters",
    "quantity",
    existing_type=sa.Integer(),
    type_=sa.BigInteger(),
    existing_nullable=False,
  )

def downgrade() -> None:
  op.alter_column(
    "usage_counters",
    "quantity",
    existing_type=sa.BigInteger(),
    type_=sa.Integer(),
    existing_nullable=False,
  )