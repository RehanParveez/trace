"""add currency to organizations

Revision ID: 4bf9067223ec
Revises: 097b86673f46
Create Date: 2026-09-17 04:23:18.683559
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '4bf9067223ec'
down_revision: Union[str, Sequence[str], None] = '097b86673f46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="PKR"),
    )

    op.execute(
        """
        UPDATE organizations o
        SET currency = sub.currency
        FROM (
            SELECT DISTINCT ON (organization_id)
                organization_id, currency
            FROM budgets
            GROUP BY organization_id, currency
            ORDER BY organization_id, COUNT(*) DESC
        ) AS sub
        WHERE o.id = sub.organization_id
        """
    )

    op.execute(
        """
        DO $$
        DECLARE mixed_count integer;
        BEGIN
            SELECT COUNT(*) INTO mixed_count FROM (
                SELECT organization_id FROM budgets
                GROUP BY organization_id
                HAVING COUNT(DISTINCT currency) > 1
            ) AS mixed;
            IF mixed_count > 0 THEN
                RAISE NOTICE 'currency migration: % org(s) had budgets in multiple currencies; set to majority value, review manually.', mixed_count;
            END IF;
        END $$;
        """
    )

def downgrade() -> None:
    op.drop_column("organizations", "currency")