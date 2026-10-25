"""takeoff corrections log: what people changed or decided about what the reader found

Revision ID: c7d9e1a3b5f2
Revises: b3c5d7e9f2a4
Create Date: 2026-10-25 17:19:00.000000
"""
from typing import Union, Sequence
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c7d9e1a3b5f2'
down_revision: Union[str, Sequence[str], None] = 'b3c5d7e9f2a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "takeoff_corrections"
TENANT = "organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid"
ADMIN = "current_setting('app.is_platform_admin', true) = 'true'"

def _jsonb(name: str):
    return sa.Column(name, postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False)

def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("drawing_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sheet_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("subject", sa.String(120), nullable=True),
        _jsonb("before"), _jsonb("after"), _jsonb("context"),
        sa.Column("extract_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_takeoff_corrections_project", TABLE, ["organization_id", "project_id", "created_at"])
    op.create_index("ix_takeoff_corrections_kind", TABLE, ["organization_id", "kind"])
    op.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS {TABLE}_org_isolation ON {TABLE}")
    op.execute(f"CREATE POLICY {TABLE}_org_isolation ON {TABLE} USING ({TENANT} OR {ADMIN}) WITH CHECK ({TENANT} OR {ADMIN})")

def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {TABLE}_org_isolation ON {TABLE}")
    op.drop_table(TABLE)
