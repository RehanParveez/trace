"""add site_photo to audit_entity_type

Revision ID: 0843eb82db27
Revises: c29fe40736e0
Create Date: 2026-09-05 19:30:32.410128
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0843eb82db27'
down_revision: Union[str, Sequence[str], None] = 'c29fe40736e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
  with op.get_context().autocommit_block():
    op.execute("ALTER TYPE audit_entity_type ADD VALUE IF NOT EXISTS 'SITE_PHOTO'")

def downgrade() -> None:
  pass