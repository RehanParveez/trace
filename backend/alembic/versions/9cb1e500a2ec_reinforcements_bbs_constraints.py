"""reinforcements bbs constraints

Revision ID: 9cb1e500a2ec
Revises: 0cbac138a2a1
Create Date: 2026-10-07 13:35:31.455628
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '9cb1e500a2ec'
down_revision: Union[str, Sequence[str], None] = '0cbac138a2a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_KINDS = "schedule_kind IN ('DOOR','WINDOW','FINISH','FIXTURE','GENERAL','BBS')"
_OLD_KINDS = "schedule_kind IN ('DOOR','WINDOW','FINISH','FIXTURE','GENERAL')"
_KIND_CHECKS = (("schedule_imports", "ck_schedule_imports_kind"), ("schedule_rows", "ck_schedule_rows_kind"))
_RULE_CHECKS = (
  ("ck_reinforcement_rules_stock", "stock_length_mm IS NULL OR stock_length_mm > 0"),
  ("ck_reinforcement_rules_cover", "cover_mm IS NULL OR cover_mm >= 0"),
  ("ck_reinforcement_rules_min_lap", "min_lap_mm IS NULL OR min_lap_mm >= 0"),
  ("ck_reinforcement_rules_weight_tol", "weight_tolerance_pct >= 0"),
)

def upgrade() -> None:
  for table, name in _KIND_CHECKS:
    op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
    op.create_check_constraint(name, table, _NEW_KINDS)
  for name, condition in _RULE_CHECKS:
    op.execute(f"ALTER TABLE reinforcement_rules DROP CONSTRAINT IF EXISTS {name}")
    op.create_check_constraint(name, "reinforcement_rules", condition)

def downgrade() -> None:
  for name, _ in _RULE_CHECKS:
    op.execute(f"ALTER TABLE reinforcement_rules DROP CONSTRAINT IF EXISTS {name}")
  op.execute("DELETE FROM schedule_imports WHERE schedule_kind = 'BBS'")   
  for table, name in _KIND_CHECKS:
    op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
    op.create_check_constraint(name, table, _OLD_KINDS)