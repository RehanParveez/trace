"""site candidates

Revision ID: 05a81572e4d3
Revises: 7c1a5e92d3b4
Create Date: 2026-10-16 18:13:36.482526
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '05a81572e4d3'
down_revision: Union[str, Sequence[str], None] = '7c1a5e92d3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATEGORY_OLD = "category IN ('COLUMN','FOOTING','BEAM','DOOR','WINDOW','WALL','ROOM','SLAB','LINTEL','STAIR')"
CATEGORY_NEW = "category IN ('COLUMN','FOOTING','BEAM','DOOR','WINDOW','WALL','ROOM','SLAB','LINTEL','STAIR','SITE')"

def upgrade() -> None:
    op.drop_constraint('ck_takeoff_candidates_category', 'takeoff_candidates', type_='check')
    op.create_check_constraint('ck_takeoff_candidates_category', 'takeoff_candidates', CATEGORY_NEW)

def downgrade() -> None:
    op.execute("DELETE FROM takeoff_candidates WHERE category = 'SITE'")
    op.drop_constraint('ck_takeoff_candidates_category', 'takeoff_candidates', type_='check')
    op.create_check_constraint('ck_takeoff_candidates_category', 'takeoff_candidates', CATEGORY_OLD)