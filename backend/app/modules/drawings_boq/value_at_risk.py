from __future__ import annotations
from math import sqrt
from app.modules.drawings_boq import quantity_range as QR
from app.modules.drawings_boq import rate_flags as RF

TOP_ITEMS = 8
TOP_FLAGGED = 3
UNPRICED_SHOWN = 8
LEFT_OUT = (
  ("ELE-", "ELECTRICAL", "Wiring, conduit, boxes, cable and circuits are not in the bill: the electrical lines are the fittings alone, counted from the plan legend."),
  ("PIL-", "PILING", "Pile caps, the steel in the piles, the cut-off of the pile heads and test piles are not in the bill: the piling lines are the boring of the shafts and the concrete in them, read from the note or schedule."),
  ("DRN-", "DRAINAGE", "Excavation, bed and surround, and the pipes between the chambers are not in the bill: the drainage lines are the pipes and chambers read from the labels."),
)
NOT_GRADED = "NOT_GRADED"
BEHIND_ASSUMPTION = ("ASSUMED", "MISSING", "NOT_READ")

def _f(v) -> float:
  try:
    return float(v)
  except (TypeError, ValueError):
    return 0.0

def _r2(v: float) -> float:
  return round(v, 2)

def _fractions(rg: dict | None) -> tuple:
  if not rg:
    return 0.0, 0.0
  likely = _f(rg.get("likely"))
  if likely == 0 or not rg.get("bounded_rows"):
    return 0.0, 0.0
  return max(0.0, (likely - _f(rg.get("low"))) / abs(likely)), max(0.0, (_f(rg.get("high")) - likely) / abs(likely))

def _slot(name: str | None, item_id, **more) -> dict:
  return {"item_id": item_id, "name": name, **more}

def build(rows: list) -> dict:
  likely = 0.0
  down2 = up2 = lin_down = lin_up = 0.0
  open_amount = minimum_amount = ungraded_amount = typed_amount = labour_amount = 0.0
  priced = 0
  grades: dict = {}
  swings: list = []
  opens: list = []
  unpriced: list = []
  flagged: dict = {code: {"code": code, "items": 0, "amount": 0.0, "top": []} for code in RF.CODES}
  blocking = 0
  left_out: dict = {group: {"group": group, "text": text, "items": 0, "amount": 0.0} for _, group, text in LEFT_OUT}

  for row in rows:
    quantity = _f(row.get("quantity"))
    rate = row.get("unit_rate")
    name, item_id = row.get("name"), row.get("item_id")
    item_type = str(getattr(row.get("item_type"), "value", row.get("item_type")) or "")
    if item_type == "LABOUR":
      if rate is not None:
        labour_amount += quantity * _f(rate)
      continue

    work_code = str(row.get("work_item_code") or "")
    for prefix, group, _ in LEFT_OUT:
      if work_code.startswith(prefix) and quantity != 0:
        left_out[group]["items"] += 1
        left_out[group]["amount"] += quantity * _f(rate) if rate is not None else 0.0
    codes = RF.flags_of(row)
    if any(RF.blocks_of(code) for code in codes):
      blocking += 1
    for code in codes:
      slot = flagged[code]
      slot["items"] += 1
      amount_for_flag = quantity * _f(rate) if rate is not None else 0.0
      slot["amount"] += amount_for_flag
      slot["top"].append(_slot(name, item_id, amount=_r2(amount_for_flag), unit=row.get("unit")))
    if rate is None:
      if quantity != 0:
        unpriced.append(_slot(name, item_id, unit=row.get("unit"), quantity=round(quantity, 4)))
      continue

    amount = quantity * _f(rate)
    priced += 1
    likely += amount
    rg = row.get("quantity_range") if isinstance(row.get("quantity_range"), dict) else None
    if rg is None and row.get("is_manual"):
      typed_amount += amount
      continue

    grade = str((rg or {}).get("weakest") or NOT_GRADED) if rg else NOT_GRADED
    slot = grades.setdefault(grade, {"grade": grade, "amount": 0.0, "items": 0})
    slot["amount"] += amount
    slot["items"] += 1
    if rg is None:
      ungraded_amount += amount
    down_f, up_f = _fractions(rg)
    down, up = abs(amount) * down_f, abs(amount) * up_f
    down2 += down * down
    up2 += up * up
    lin_down += down
    lin_up += up
    if down + up > 0:
      swings.append(_slot(name, item_id, unit=row.get("unit"), amount=_r2(amount), down=_r2(down), up=_r2(up), weakest=grade))
    if rg is None or rg.get("unbounded_rows"):
      open_amount += amount
      opens.append(_slot(name, item_id, unit=row.get("unit"), amount=_r2(amount), weakest=grade))
    if rg and rg.get("leaves_out_rows"):
      minimum_amount += amount

  behind = sum(g["amount"] for k, g in grades.items() if k in BEHIND_ASSUMPTION)
  order = {g: n for n, g in enumerate(QR.GRADE_ORDER)}
  by_grade = [{"grade": g["grade"], "amount": _r2(g["amount"]), "items": g["items"],
    "share_pct": _r2(g["amount"] / likely * 100.0) if likely else None}
    for g in sorted(grades.values(), key=lambda x: (order.get(x["grade"], 98) if x["grade"] != NOT_GRADED else 99, x["grade"]))]
  flags = []
  for code, text in RF.FLAGS:
    slot = flagged[code]
    if not slot["items"]:
      continue
    top = sorted(slot["top"], key=lambda x: (-abs(x.get("amount") or 0.0), x["name"] or ""))[:TOP_FLAGGED]
    flags.append({"code": code, "text": text, "blocks": RF.blocks_of(code), "items": slot["items"], "amount": None if code == RF.NO_RATE else _r2(slot["amount"]), "top_items": top})

  return {
    "totals": {
      "likely": _r2(likely), "low": _r2(likely - sqrt(down2)), "high": _r2(likely + sqrt(up2)),
      "worst_low": _r2(likely - lin_down), "worst_high": _r2(likely + lin_up),
      "swing_down": _r2(sqrt(down2)), "swing_up": _r2(sqrt(up2)),
      "priced_items": priced, "unpriced_items": len(unpriced),
      "behind_assumption": _r2(behind), "behind_assumption_pct": _r2(behind / likely * 100.0) if likely else None,
      "open_amount": _r2(open_amount), "open_amount_pct": _r2(open_amount / likely * 100.0) if likely else None,
      "minimum_amount": _r2(minimum_amount), "ungraded_amount": _r2(ungraded_amount),
      "typed_amount": _r2(typed_amount), "labour_left_out": _r2(labour_amount),
    },
    "by_grade": by_grade,
    "top_swing": sorted(swings, key=lambda x: (-(x["down"] + x["up"]), x["name"] or ""))[:TOP_ITEMS],
    "top_open": sorted(opens, key=lambda x: (-abs(x["amount"]), x["name"] or ""))[:TOP_ITEMS],
    "unpriced": sorted(unpriced, key=lambda x: (x["name"] or ""))[:UNPRICED_SHOWN],
    "flags": flags,
  }
