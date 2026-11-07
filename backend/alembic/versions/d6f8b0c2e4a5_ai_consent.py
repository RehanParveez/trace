"""AI consent per company: OFF, LOCAL or OUTSIDE.
"""
from alembic import op
import sqlalchemy as sa
from app.core.config import settings

revision = "d6f8b0c2e4a5"
down_revision = "c5e7a9b1d3f4"
branch_labels = None
depends_on = None

def upgrade() -> None:
  op.add_column("organizations", sa.Column("ai_consent", sa.String(8), nullable=False, server_default="OFF"))
  op.create_check_constraint("ck_organizations_ai_consent", "organizations", "ai_consent IN ('OFF','LOCAL','OUTSIDE')")
  keep = "OUTSIDE" if str(settings.ai_provider or "").strip().lower() == "anthropic" else "LOCAL"
  op.execute(sa.text("UPDATE organizations SET ai_consent = :keep WHERE ai_enabled = true").bindparams(keep=keep))

def downgrade() -> None:
  op.drop_constraint("ck_organizations_ai_consent", "organizations", type_="check")
  op.drop_column("organizations", "ai_consent")
