from __future__ import annotations
from app.modules.drawings_boq import quantity_range as QR
from app.engine.measure.stages import stage_label

NO_STAGE = "NOT_SPLIT"
NO_STAGE_LABEL = "Not split by stage"
NO_TRADE = "Other"
_FIXED = {"BELOW_PLINTH": 0, "PLINTH_TO_LINTEL": 1, "LINTEL_TO_SLAB": 2, "TOP": 100, "PARAPET": 101, "MUMTY": 102, NO_STAGE: 1000}

def stage_rank(stage: str | None) -> int:
  s = stage or NO_STAGE
  if s.startswith("UPPER_FLOOR_"):
    try:
      return 10 + int(s.rsplit("_", 1)[1])
    except ValueError:
      return 99
  return _FIXED.get(s, 99)

def _get(r, key):
  return r.get(key) if isinstance(r, dict) else getattr(r, key, None)

def build(rows: list) -> dict:
  by_stage: dict = {}
  everything: list = []
  for r in rows:
    stage = _get(r, "work_stage") or NO_STAGE
    trade = _get(r, "category") or NO_TRADE
    item = {"name": _get(r, "material_name"), "code": _get(r, "work_item_code"), "unit": _get(r, "unit") or "", "quantity": str(_get(r, "quantity") if _get(r, "quantity") is not None else "0"),
      "quantity_range": _get(r, "quantity_range"), "derived": (_get(r, "spec_key") == "derived") or ((_get(r, "spec") or {}).get("kind") == "DERIVED"),
      "weakest": (_get(r, "quantity_range") or {}).get("weakest"), "review_status": _get(r, "review_status") or "OK", "item_id": str(_get(r, "id") or _get(r, "source_item_id") or "")}
    by_stage.setdefault(stage, {}).setdefault(trade, []).append(item)
    everything.append(item)
  
  stages = []
  for stage in sorted(by_stage, key=lambda s: (stage_rank(s), s)):
    trades = []
    flat: list = []
    for trade in sorted(by_stage[stage], key=lambda t: (t == NO_TRADE, t)):
      items = sorted(by_stage[stage][trade], key=lambda i: (i["name"] or "", i["unit"]))
      trades.append({"trade": trade, "items": items, "totals": QR.range_totals(items)})
      flat.extend(items)
    stages.append({"stage": stage, "label": NO_STAGE_LABEL if stage == NO_STAGE else (stage_label(stage) or stage), "trades": trades, "totals": QR.range_totals(flat)})
  return {"stages": stages, "totals": QR.range_totals(everything)}
