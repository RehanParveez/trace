"""pdf_takeoff_prep

Revision ID: 1df9edecefa3
Revises: 5ffa2405d4b8
Create Date: 2026-10-11 19:36:41.113241
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '1df9edecefa3'
down_revision: Union[str, Sequence[str], None] = '5ffa2405d4b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT = "organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid"
ADMIN = "current_setting('app.is_platform_admin', true) = 'true'"
TABLE = "takeoff_sheet_indexes"

def upgrade() -> None:
  op.create_table(
    TABLE,
    sa.Column("sheet_id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
    sa.Column("analysis_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    sa.Column("segment_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    sa.Column("ring_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    sa.Column("word_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    sa.Column("analysis", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column("payload", sa.LargeBinary(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.ForeignKeyConstraint(["sheet_id", "organization_id"], ["takeoff_sheets.id", "takeoff_sheets.organization_id"],
      ondelete="CASCADE", name="fk_takeoff_sheet_indexes_sheet_tenant"),
    sa.CheckConstraint("analysis_version >= 1", name="ck_takeoff_sheet_indexes_version"),
  )
  op.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")
  op.execute(f"ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY")
  op.execute(f"DROP POLICY IF EXISTS {TABLE}_org_isolation ON {TABLE}")
  op.execute(f"CREATE POLICY {TABLE}_org_isolation ON {TABLE} USING ({TENANT} OR {ADMIN}) WITH CHECK ({TENANT} OR {ADMIN})")

def downgrade() -> None:
  op.execute(f"DROP POLICY IF EXISTS {TABLE}_org_isolation ON {TABLE}")
  op.drop_table(TABLE)