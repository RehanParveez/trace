from __future__ import annotations
from decimal import Decimal, InvalidOperation

WIRE_ITEM, CHAIRS_ITEM = "STL-BINDING-WIRE", "STL-CHAIRS"
ITEMS = (WIRE_ITEM, CHAIRS_ITEM)

def _dec(value) -> Decimal:
  try:
    return Decimal(str(value))
  except (InvalidOperation, ValueError, TypeError):
    return Decimal("0")

def allowances_of(rows, bars_kg: Decimal) -> dict | None:
  wire = sum((_dec(r.get("quantity")) for r in rows if r.get("code") == WIRE_ITEM), Decimal("0"))
  chairs = sum((_dec(r.get("quantity")) for r in rows if r.get("code") == CHAIRS_ITEM), Decimal("0"))
  if wire <= 0 and chairs <= 0:
    return None
  extra = wire + chairs
  return {"binding_wire_kg": float(round(wire, 3)), "chairs_kg": float(round(chairs, 3)), "kg": float(round(extra, 3)), "bars_kg": float(round(bars_kg, 3)),
    "with_bars_kg": float(round(bars_kg + extra, 3)), "share_pct": float(round(extra / bars_kg * 100, 3)) if bars_kg > 0 else 0.0}