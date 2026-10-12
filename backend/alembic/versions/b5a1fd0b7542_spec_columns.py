"""spec_columns

Revision ID: b5a1fd0b7542
Revises: 112eca0b8681
Create Date: 2026-10-12 20:36:30.538289
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b5a1fd0b7542'
down_revision: Union[str, Sequence[str], None] = '112eca0b8681'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("quantity_ledger", "staged_quantity_ledger", "boq_items")

def upgrade() -> None:
  for table in TABLES:
    op.add_column(table, sa.Column("spec_key", sa.String(length=100), nullable=True))
    op.add_column(table, sa.Column("spec", postgresql.JSONB(), nullable=True))

def downgrade() -> None:
  for table in reversed(TABLES):
    op.drop_column(table, "spec")
    op.drop_column(table, "spec_key")