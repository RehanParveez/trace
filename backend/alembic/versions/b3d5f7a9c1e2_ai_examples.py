"""AX-2: the example bank, answers a person has checked that are shown to a model as examples.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b3d5f7a9c1e2"
down_revision = "a2c4e6f8b0d1"
branch_labels = None
depends_on = None

def upgrade() -> None:
  op.create_table(
    "ai_examples",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
    sa.Column("task", sa.String(24), nullable=False),
    sa.Column("office", sa.String(120), nullable=True),
    sa.Column("kind", sa.String(40), nullable=True),
    sa.Column("crop_ref", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column("words", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    sa.Column("answer", postgresql.JSONB(), nullable=False),
    sa.Column("checked_by", sa.String(120), nullable=False),
    sa.Column("checked_on", sa.String(32), nullable=False),
    sa.Column("drawing", sa.String(64), nullable=False),
    sa.Column("shared", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.CheckConstraint("task IN ('SCHEDULE_ROW','NOTE_FACT')", name="ck_ai_examples_task"),
  )
  op.create_index("ix_ai_examples_task_office", "ai_examples", ["task", "office"])
  op.create_index("ix_ai_examples_org", "ai_examples", ["organization_id"])

def downgrade() -> None:
  op.drop_index("ix_ai_examples_org", table_name="ai_examples")
  op.drop_index("ix_ai_examples_task_office", table_name="ai_examples")
  op.drop_table("ai_examples")
