"""add stair and waterproofing to finish surfaces

Revision ID: 2202fbeab39d
Revises: 353936bb5ca3
Create Date: 2026-10-05 03:46:39.411350
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '2202fbeab39d'
down_revision: Union[str, Sequence[str], None] = '353936bb5ca3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Drop the old check constraint
    op.drop_constraint('ck_finish_rules_surface', 'finish_rules', type_='check')

    # Create the new one with STAIR and WATERPROOFING
    op.create_check_constraint(
        'ck_finish_rules_surface',
        'finish_rules',
        "surface IN ('FLOOR','WALL','CEILING','SKIRTING','DADO','STAIR','WATERPROOFING')"
    )

def downgrade() -> None:
    op.drop_constraint('ck_finish_rules_surface', 'finish_rules', type_='check')
    op.create_check_constraint(
        'ck_finish_rules_surface',
        'finish_rules',
        "surface IN ('FLOOR','WALL','CEILING','SKIRTING','DADO')"
    )