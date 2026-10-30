from alembic import op
import sqlalchemy as sa

revision = "e2a4c6d8f0b3"
down_revision = "d6f8a0c2e4b1"
branch_labels = None
depends_on = None

def upgrade() -> None:
  op.add_column("takeoff_measurements", sa.Column("role", sa.String(24), nullable=False, server_default=""))

def downgrade() -> None:
  op.drop_column("takeoff_measurements", "role")
