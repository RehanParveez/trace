"""LX-1: a company's consent to learn from its corrections: OFF, OWN or SHARED.
"""
from alembic import op
import sqlalchemy as sa

revision = "c4e6a8b0d2f1"
down_revision = "b3d5f7a9c1e2"
branch_labels = None
depends_on = None

def upgrade() -> None:
  op.add_column("organizations", sa.Column("learning_consent", sa.String(8), nullable=False, server_default="OFF"))
  op.create_check_constraint("ck_organizations_learning_consent", "organizations", "learning_consent IN ('OFF','OWN','SHARED')")

def downgrade() -> None:
  op.drop_constraint("ck_organizations_learning_consent", "organizations", type_="check")
  op.drop_column("organizations", "learning_consent")
