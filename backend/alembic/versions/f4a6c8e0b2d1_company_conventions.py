"""Company conventions: the figures a company holds for the measurement rules that a drawing does not print.

One row per company and convention. The reader takes a company's row before the software's own figure; a convention with no row is read with the software's own figure and shown as assumed.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f4a6c8e0b2d1"
down_revision = "c7d9e1a3b5f2"
branch_labels = None
depends_on = None

def upgrade() -> None:
  op.create_table(
    "company_conventions",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
    sa.Column("key", sa.String(64), nullable=False),
    sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column("unit", sa.String(24), nullable=True),
    sa.Column("origin", sa.String(24), nullable=False),
    sa.Column("set_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_company_conventions_set_by"), nullable=True),
    sa.Column("set_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column("evidence", sa.Text(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.UniqueConstraint("organization_id", "key", name="uq_company_conventions_key"),
    sa.CheckConstraint("origin IN ('COMPANY','QS_WORKBOOK','PROJECT','CODE_DEFAULT_ASSUMED')", name="ck_company_conventions_origin"),
  )
  op.create_index("ix_company_conventions_org", "company_conventions", ["organization_id"])

def downgrade() -> None:
  op.drop_index("ix_company_conventions_org", table_name="company_conventions")
  op.drop_table("company_conventions")
