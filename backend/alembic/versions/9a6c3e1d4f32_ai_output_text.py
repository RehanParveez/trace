"""ai_responses.parsed_output becomes TEXT so it can hold an encrypted value

Revision ID: 9a6c3e1d4f32
Revises: 8f5b2d0c3e21
Create Date: 2026-10-19 02:30:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = '9a6c3e1d4f32'
down_revision: Union[str, Sequence[str], None] = '8f5b2d0c3e21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("ALTER TABLE ai_responses ALTER COLUMN parsed_output TYPE text USING parsed_output::text")

def downgrade() -> None:
    op.execute("ALTER TABLE ai_responses ALTER COLUMN parsed_output TYPE json USING parsed_output::json")
