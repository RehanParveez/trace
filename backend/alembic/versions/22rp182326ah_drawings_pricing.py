"""drawings_pricing
Revision ID: 22rp182326ah
Revises: 33e61acb2269
Create Date: 2026-09-01
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "22rp182326ah"
down_revision = "33e61acb2269"
branch_labels = None
depends_on = None

boq_item_type = postgresql.ENUM("MATERIAL", "LABOUR", "CUSTOM", name="boq_item_type")
boq_version_status = postgresql.ENUM("ACTIVE", "SUPERSEDED", name="boq_version_status")

def upgrade() -> None:
  bind = op.get_bind()
  boq_item_type.create(bind, checkfirst=True)
  boq_version_status.create(bind, checkfirst=True)

  op.add_column(
    "material_library",
    sa.Column("default_rate", sa.Numeric(14, 2), nullable=True),
  )

  op.create_table(
    "labour_rates",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column(
      "organization_id",
      postgresql.UUID(as_uuid=True),
      sa.ForeignKey("organizations.id", ondelete="CASCADE"),
      nullable=False,
    ),
    sa.Column("trade", sa.String(150), nullable=False),
    sa.Column("unit", sa.String(20), nullable=False),
    sa.Column("rate", sa.Numeric(14, 2), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.UniqueConstraint("organization_id", "trade", name="uq_labour_rates_org_trade"),
  )
  op.create_index("ix_labour_rates_org", "labour_rates", ["organization_id"])

  # RLS — mirror every other organization-owned table (§8/§13 of your architecture doc)
  op.execute("ALTER TABLE labour_rates ENABLE ROW LEVEL SECURITY")
  op.execute("ALTER TABLE labour_rates FORCE ROW LEVEL SECURITY")
  op.execute(
    """
    CREATE POLICY tenant_isolation ON labour_rates
      USING (organization_id = current_setting('app.current_org_id')::uuid)
    """
  )

  op.add_column(
    "boq_versions",
    sa.Column("status", boq_version_status, nullable=False, server_default="ACTIVE"),
  )
  op.add_column(
    "boq_versions",
    sa.Column("covered_area_sqft", sa.Numeric(14, 2), nullable=True),
  )
  op.add_column(
    "boq_versions",
    sa.Column("export_meta", sa.JSON(), nullable=False, server_default="{}"),
  )

  op.add_column(
    "boq_items",
    sa.Column("item_type", boq_item_type, nullable=False, server_default="MATERIAL"),
  )
  op.add_column(
    "boq_items",
    sa.Column(
      "created_by_user_id",
      postgresql.UUID(as_uuid=True),
      sa.ForeignKey("users.id", ondelete="SET NULL"),
      nullable=True,
    ),
  )

def downgrade() -> None:
  op.drop_column("boq_items", "created_by_user_id")
  op.drop_column("boq_items", "item_type")
  op.drop_column("boq_versions", "export_meta")
  op.drop_column("boq_versions", "covered_area_sqft")
  op.drop_column("boq_versions", "status")
  op.execute("DROP POLICY IF EXISTS tenant_isolation ON labour_rates")
  op.drop_table("labour_rates")
  op.drop_column("material_library", "default_rate")

  bind = op.get_bind()
  boq_version_status.drop(bind, checkfirst=True)
  boq_item_type.drop(bind, checkfirst=True)