"""stair candidates

Revision ID: 4d38f84bc1ea
Revises: d61212e6c984
Create Date: 2026-10-15 05:24:47.120430
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '4d38f84bc1ea'
down_revision: Union[str, Sequence[str], None] = 'd61212e6c984'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATEGORY_OLD = "category IN ('COLUMN','FOOTING','BEAM','DOOR','WINDOW','WALL','ROOM','SLAB','LINTEL')"
CATEGORY_NEW = "category IN ('COLUMN','FOOTING','BEAM','DOOR','WINDOW','WALL','ROOM','SLAB','LINTEL','STAIR')"

def upgrade() -> None:
    # A staircase read from the riser, tread, width and steps printed on the drawing is a candidate of its own kind. Alembic does not compare check constraints, so this one is written by hand.
    op.drop_constraint('ck_takeoff_candidates_category', 'takeoff_candidates', type_='check')
    op.create_check_constraint('ck_takeoff_candidates_category', 'takeoff_candidates', CATEGORY_NEW)

def downgrade() -> None:
    op.execute("DELETE FROM takeoff_candidates WHERE category = 'STAIR'")
    op.drop_constraint('ck_takeoff_candidates_category', 'takeoff_candidates', type_='check')
    op.create_check_constraint('ck_takeoff_candidates_category', 'takeoff_candidates', CATEGORY_OLD)