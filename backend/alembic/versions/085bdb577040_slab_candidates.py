"""slab candidates

Revision ID: 085bdb577040
Revises: f8d11a359a36
Create Date: 2026-10-14 19:36:35.144387
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '085bdb577040'
down_revision: Union[str, Sequence[str], None] = 'f8d11a359a36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATEGORY_OLD = "category IN ('COLUMN','FOOTING','BEAM','DOOR','WINDOW','WALL','ROOM','SLAB')"
CATEGORY_NEW = "category IN ('COLUMN','FOOTING','BEAM','DOOR','WINDOW','WALL','ROOM','SLAB','LINTEL')"

def upgrade() -> None:
    # A lintel read from the printed lintel table is a candidate of its own kind. Alembic does not compare check constraints, so this one is written by hand.
    op.drop_constraint('ck_takeoff_candidates_category', 'takeoff_candidates', type_='check')
    op.create_check_constraint('ck_takeoff_candidates_category', 'takeoff_candidates', CATEGORY_NEW)

def downgrade() -> None:
    op.execute("DELETE FROM takeoff_candidates WHERE category = 'LINTEL'")
    op.drop_constraint('ck_takeoff_candidates_category', 'takeoff_candidates', type_='check')
    op.create_check_constraint('ck_takeoff_candidates_category', 'takeoff_candidates', CATEGORY_OLD)