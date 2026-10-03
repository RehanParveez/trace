"""seed frame monolithic a convention

Revision ID: 5db4f7917cd6
Revises: 1cd633356ed6
Create Date: 2026-10-03 13:12:45.445029
"""
from typing import Sequence, Union

import json
import uuid
from alembic import op
import sqlalchemy as sa

revision: str = '5db4f7917cd6'
down_revision: Union[str, Sequence[str], None] = '1cd633356ed6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PARAMS = {
  "sliver_area_mm2": 1.0,
  "min_z_overlap_mm": 0.1,
  "conservation_tolerance_rel": 0.0001,
  "conservation_tolerance_abs_mm3": 5000,
}

def upgrade() -> None:
  conn = op.get_bind()
  conn.execute(
    sa.text(
      """
      INSERT INTO measurement_conventions
        (id, code, name, description, is_system, is_active, conserves_volume, parameters, created_at, updated_at)
      VALUES
        (CAST(:id AS uuid), 'FRAME_MONOLITHIC_A', 'Monolithic frame A',
         'Columns own footprint; beams face-to-face; beam top belongs to slab; slab less columns.',
         true, true, true, CAST(:params AS jsonb), now(), now())
      ON CONFLICT (code) DO NOTHING
      """
    ),
    {"id": str(uuid.uuid4()), "params": json.dumps(PARAMS)},
  )

def downgrade() -> None:
  op.get_bind().execute(
    sa.text("DELETE FROM measurement_conventions WHERE code = 'FRAME_MONOLITHIC_A'")
  )