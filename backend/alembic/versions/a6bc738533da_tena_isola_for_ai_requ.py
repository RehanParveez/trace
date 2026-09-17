"""tena.isola for ai_requ

Revision ID: a6bc738533da
Revises: b807ab5239cb
Create Date: 2026-09-17 08:18:13.259749
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a6bc738533da'
down_revision: Union[str, Sequence[str], None] = 'b807ab5239cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    op.add_column(
        "ai_responses",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.execute(
        """
        UPDATE ai_responses
        SET organization_id = ai_requests.organization_id
        FROM ai_requests
        WHERE ai_responses.ai_request_id = ai_requests.id
        """
    )

    op.alter_column("ai_responses", "organization_id", nullable=False)

    op.create_foreign_key(
        "fk_ai_responses_organization_id",
        "ai_responses",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_ai_responses_organization_id",
        "ai_responses",
        ["organization_id"],
    )

def downgrade() -> None:
    op.drop_index("ix_ai_responses_organization_id", table_name="ai_responses")
    op.drop_constraint("fk_ai_responses_organization_id", "ai_responses", type_="foreignkey")
    op.drop_column("ai_responses", "organization_id")