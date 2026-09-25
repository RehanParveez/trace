"""scheduling tables

Revision ID: 3699d52b79e4
Revises: 80a7ac6f829c
Create Date: 2026-09-25 15:59:59.176855
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '3699d52b79e4'
down_revision: Union[str, Sequence[str], None] = '80a7ac6f829c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "project_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_completion_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", "project_id", name="uq_project_schedule_project"),
    )

    op.create_table(
        "schedule_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("planned_start_date", sa.Date(), nullable=True),
        sa.Column("planned_duration_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_milestone_marker", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("actual_start_date", sa.Date(), nullable=True),
        sa.Column("actual_end_date", sa.Date(), nullable=True),
        sa.Column("percent_complete", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.Enum("NOT_STARTED", "IN_PROGRESS", "COMPLETE", name="schedule_task_status"), nullable=False, server_default="NOT_STARTED"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_schedule_tasks_org_project", "schedule_tasks", ["organization_id", "project_id"])

    op.create_table(
        "schedule_dependencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("predecessor_task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("schedule_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("successor_task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("schedule_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("predecessor_task_id", "successor_task_id", name="uq_schedule_dependency_pair"),
    )

    op.execute("COMMIT")
    op.execute("ALTER TYPE audit_entity_type ADD VALUE IF NOT EXISTS 'SCHEDULE_TASK'")

def downgrade() -> None:
    op.drop_table("schedule_dependencies")
    op.drop_table("schedule_tasks")
    op.execute("DROP TYPE IF EXISTS schedule_task_status")
    op.drop_table("project_schedules")