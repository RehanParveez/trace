"""boq governance

Revision ID: 1a80145778fc
Revises: 2c21d0829eb7
Create Date: 2026-10-04 08:10:38.078445
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1a80145778fc"
down_revision: Union[str, Sequence[str], None] = "2c21d0829eb7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 2c21d0829eb7_drawing_boq_record.py already created
    # the BOQ governance schema:
    #
    # boq_versions lifecycle/origin/calculation/snapshot fields
    # boq_items governance fields
    # snapshots
    # snapshot items
    # adjustments
    # ledger links
    # review issues
    # export jobs
    # all related indexes, foreign keys and constraints
    #
    # Therefore this revision has no additional schema changes.
    pass

def downgrade() -> None:
    pass