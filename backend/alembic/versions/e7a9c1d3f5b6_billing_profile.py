"""The billing profile of a company: the way its BOQ is grouped into bill lines.
"""
from alembic import op
import sqlalchemy as sa

revision = "e7a9c1d3f5b6"
down_revision = "d6f8b0c2e4a5"
branch_labels = None
depends_on = None

def upgrade() -> None:
  op.add_column("organizations", sa.Column("billing_profile", sa.String(24), nullable=True))

def downgrade() -> None:
  op.drop_column("organizations", "billing_profile")
