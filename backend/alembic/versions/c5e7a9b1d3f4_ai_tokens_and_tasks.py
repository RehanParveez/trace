"""AI foundation: token counts on AI requests, the new AI task purposes, and the task, cache key, model and validators of a shadow reading.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c5e7a9b1d3f4"
down_revision = "f6c8e0a2b4d3"
branch_labels = None
depends_on = None

PURPOSES = ("NOTE_FACT", "SCHEDULE_ROW", "LEGEND_ENTRY", "VOCAB", "EXPLAIN")

def upgrade() -> None:
  with op.get_context().autocommit_block():
    for value in PURPOSES:
      op.execute(f"ALTER TYPE ai_request_purpose ADD VALUE IF NOT EXISTS '{value}'")
  op.add_column("ai_requests", sa.Column("input_tokens", sa.Integer(), nullable=True))
  op.add_column("ai_requests", sa.Column("output_tokens", sa.Integer(), nullable=True))
  op.add_column("ai_shadow_reads", sa.Column("task", sa.String(24), nullable=False, server_default="SHEET"))
  op.add_column("ai_shadow_reads", sa.Column("cache_key", sa.String(64), nullable=True))
  op.add_column("ai_shadow_reads", sa.Column("model", sa.String(100), nullable=True))
  op.add_column("ai_shadow_reads", sa.Column("validators", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
  op.create_index("ix_ai_shadow_reads_cache_key", "ai_shadow_reads", ["drawing_id", "cache_key"])

def downgrade() -> None:
  op.drop_index("ix_ai_shadow_reads_cache_key", table_name="ai_shadow_reads")
  op.drop_column("ai_shadow_reads", "validators")
  op.drop_column("ai_shadow_reads", "model")
  op.drop_column("ai_shadow_reads", "cache_key")
  op.drop_column("ai_shadow_reads", "task")
  op.drop_column("ai_requests", "output_tokens")
  op.drop_column("ai_requests", "input_tokens")
