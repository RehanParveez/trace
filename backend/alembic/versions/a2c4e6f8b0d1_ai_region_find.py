"""AX-1: the purpose of a request that asks a model where schedules and section pictures are on a page.
"""
from alembic import op

revision = "a2c4e6f8b0d1"
down_revision = "e7a9c1d3f5b6"
branch_labels = None
depends_on = None

def upgrade() -> None:
  with op.get_context().autocommit_block():
    op.execute("ALTER TYPE ai_request_purpose ADD VALUE IF NOT EXISTS 'REGION_FIND'")

def downgrade() -> None:
  pass
