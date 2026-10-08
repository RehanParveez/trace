"""Pricing and comparison_1

Revision ID: 14cba4c36a9c
Revises: d65af0296dbe
Create Date: 2026-10-08 06:53:05.727745
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '14cba4c36a9c'
down_revision: Union[str, Sequence[str], None] = 'd65af0296dbe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_foreign_key(
        'fk_rate_items_analysis_id', 'rate_items', 'rate_analyses',
        ['analysis_id'], ['id'], ondelete='SET NULL',
    )

def downgrade() -> None:
    op.drop_constraint('fk_rate_items_analysis_id', 'rate_items', type_='foreignkey')