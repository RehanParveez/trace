"""punch_lists tables

Revision ID: ce63f695609e
Revises: 3699d52b79e4
Create Date: 2026-09-26 03:17:48.771477
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'ce63f695609e'
down_revision: Union[str, Sequence[str], None] = '3699d52b79e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "punch_lists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("inspection_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Enum("OPEN", "CLOSED", name="punch_list_status"), nullable=False, server_default="OPEN"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_punch_lists_org_project", "punch_lists", ["organization_id", "project_id"])

    op.create_table(
        "punch_list_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("punch_list_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("punch_lists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_to_subcontractor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subcontractors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.Enum("OPEN", "IN_PROGRESS", "RESOLVED", "WAIVED", name="punch_list_item_status"), nullable=False, server_default="OPEN"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_punch_list_items_org_list", "punch_list_items", ["organization_id", "punch_list_id"])

    op.create_table(
        "punch_list_item_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("punch_list_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("punch_list_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("site_photo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("site_photos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("photo_purpose", sa.Enum("DEFECT", "RESOLUTION", name="punch_list_photo_purpose"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.add_column("retention_releases", sa.Column("is_final_release", sa.Boolean(), nullable=False, server_default="false"))

    op.execute("COMMIT")
    op.execute("ALTER TYPE audit_entity_type ADD VALUE IF NOT EXISTS 'PUNCH_LIST'")

def downgrade() -> None:
    op.drop_column("retention_releases", "is_final_release")
    op.drop_table("punch_list_item_photos")
    op.execute("DROP TYPE IF EXISTS punch_list_photo_purpose")
    op.drop_table("punch_list_items")
    op.execute("DROP TYPE IF EXISTS punch_list_item_status")
    op.drop_table("punch_lists")
    op.execute("DROP TYPE IF EXISTS punch_list_status")