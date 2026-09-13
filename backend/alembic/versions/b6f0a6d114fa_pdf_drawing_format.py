"""pdf_drawing_format

Revision ID: b6f0a6d114fa
Revises: 78b661df1c9a
Create Date: 2026-09-13 16:01:14.315560
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b6f0a6d114fa'
down_revision: Union[str, Sequence[str], None] = '78b661df1c9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("COMMIT")
    op.execute("ALTER TYPE drawing_format ADD VALUE IF NOT EXISTS 'PDF'")

def downgrade() -> None:
    # Postgres doesn't support removing enum values directly — a real
    # downgrade would mean creating a new type, migrating rows, and
    # dropping the old one. Not implemented here.
    pass