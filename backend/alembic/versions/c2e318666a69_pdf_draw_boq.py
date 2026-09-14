"""pdf draw_boq

Revision ID: c2e318666a69
Revises: b6f0a6d114fa
Create Date: 2026-09-14 14:03:25.024691
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c2e318666a69'
down_revision: Union[str, Sequence[str], None] = 'b6f0a6d114fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("COMMIT")
    op.execute("ALTER TYPE ai_request_purpose ADD VALUE IF NOT EXISTS 'PDF_SCHEDULE_EXTRACTION'")
    op.execute("COMMIT")
    op.execute("ALTER TYPE ai_entity_type ADD VALUE IF NOT EXISTS 'DRAWING'")

def downgrade() -> None:
    # Postgres doesn't support removing enum values directly — a real
    # downgrade would mean creating a new type, migrating rows, and
    # dropping the old one. Not implemented here.
    pass