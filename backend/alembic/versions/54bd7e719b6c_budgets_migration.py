"""budgets migration

Revision ID: 54bd7e719b6c
Revises: c2e318666a69
Create Date: 2026-09-15 13:42:07.116978
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '54bd7e719b6c'
down_revision: Union[str, Sequence[str], None] = 'c2e318666a69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "budgets",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )

def downgrade() -> None:
    op.drop_column("budgets", "version")