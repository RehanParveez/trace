"""rate import rows: the spec, the labour part and the kind of rate

Revision ID: b3c5d7e9f2a4
Revises: e4b7a9c2d6f1
Create Date: 2026-10-22 18:30:00.000000
"""
from typing import Union, Sequence
from alembic import op
import sqlalchemy as sa

revision: str = 'b3c5d7e9f2a4'
down_revision: Union[str, Sequence[str], None] = 'e4b7a9c2d6f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "rate_import_rows"

def upgrade() -> None:
    op.add_column(TABLE, sa.Column('spec_key', sa.String(length=80), nullable=True))
    op.add_column(TABLE, sa.Column('labour', sa.Numeric(precision=16, scale=4), nullable=True))
    op.add_column(TABLE, sa.Column('rate_kind', sa.String(length=12), nullable=True))

def downgrade() -> None:
    op.drop_column(TABLE, 'rate_kind')
    op.drop_column(TABLE, 'labour')
    op.drop_column(TABLE, 'spec_key')
