from __future__ import annotations
from pydantic import BaseModel
from uuid import UUID
from decimal import Decimal

class SteelBoqIn(BaseModel):
  item_id: UUID | None = None

class SteelBoqOut(BaseModel):
  version_id: UUID
  item_id: UUID
  item_name: str
  unit: str
  source: str | None
  effect_kg: Decimal
  delta: Decimal
  state: str
  in_sync: bool
  quantity_now: Decimal
  quantity_after: Decimal
  net_quantity: Decimal | None
  adjustment_id: UUID | None
  revoked: int
  applied_count: int
  open_count: int
  note: str
  dry_run: bool
