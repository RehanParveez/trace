"""work_stage

Revision ID: 8a6f8f042d65
Revises: b5a1fd0b7542
Create Date: 2026-10-13 04:36:33.484105
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '8a6f8f042d65'
down_revision: Union[str, Sequence[str], None] = 'b5a1fd0b7542'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    for table in ("quantity_ledger", "staged_quantity_ledger", "boq_items"):
        op.add_column(table, sa.Column("work_stage", sa.String(length=40), nullable=True))
    op.drop_constraint("uq_quantity_ledger_run_solid_work_item", "quantity_ledger", type_="unique")
    op.drop_constraint("uq_staged_quantity_ledger_run_solid_work_item", "staged_quantity_ledger", type_="unique")
    op.create_index("uq_quantity_ledger_run_solid_work_item_stage", "quantity_ledger",
        ["run_id", "solid_id", "work_item_code", sa.text("coalesce(work_stage, '')")], unique=True)
    op.create_index("uq_staged_quantity_ledger_run_solid_work_item_stage", "staged_quantity_ledger",
        ["run_id", "solid_id", "work_item_code", sa.text("coalesce(work_stage, '')")], unique=True)

def downgrade() -> None:
    op.drop_index("uq_staged_quantity_ledger_run_solid_work_item_stage", table_name="staged_quantity_ledger")
    op.drop_index("uq_quantity_ledger_run_solid_work_item_stage", table_name="quantity_ledger")
    op.create_unique_constraint("uq_staged_quantity_ledger_run_solid_work_item", "staged_quantity_ledger", ["run_id", "solid_id", "work_item_code"])
    op.create_unique_constraint("uq_quantity_ledger_run_solid_work_item", "quantity_ledger", ["run_id", "solid_id", "work_item_code"])
    for table in ("boq_items", "staged_quantity_ledger", "quantity_ledger"):
        op.drop_column(table, "work_stage")