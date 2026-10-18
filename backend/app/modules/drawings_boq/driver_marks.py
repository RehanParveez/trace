from __future__ import annotations
from math import sqrt

TOP_MARKS = 8
WORKLIST = 15
SOURCE_KEYS = ("formwork_source", "steel_source")
MARK_FIELDS = ("measurement_id", "sheet_id", "drawing_id", "page_no", "tag", "candidate_id")

def _s(v) -> str | None:
  return None if v in (None, "", "None") else str(v)

def mark_of(trace: dict | None) -> dict | None:
  """The PDF mark a ledger row was measured from, read from its trace; None for rows that came from the model."""
  inputs = (trace or {}).get("inputs")
  if not isinstance(inputs, dict):
    return None
  src = inputs if inputs.get("measurement_id") else next(
    (inputs[k] for k in SOURCE_KEYS if isinstance(inputs.get(k), dict) and inputs[k].get("measurement_id")), None)
  mid = _s((src or {}).get("measurement_id"))
  if not mid:
    return None
  page = src.get("page_no")
  return {"measurement_id": mid, "sheet_id": _s(src.get("sheet_id")), "drawing_id": _s(src.get("drawing_id")),
    "page_no": page if isinstance(page, int) and not isinstance(page, bool) else None, "tag": _s(src.get("tag")),
    "candidate_id": _s(src.get("candidate_id"))}

def bump(bucket: dict, mark: dict | None, item: dict, weight: float, down2: float = 0.0, up2: float = 0.0, open_q: float = 0.0) -> None:
  if not mark:
    u = bucket.setdefault("unmarked", {"weight": 0.0, "down2": 0.0, "up2": 0.0, "open_q": 0.0})
    u["weight"] += weight
    u["down2"] += down2
    u["up2"] += up2
    u["open_q"] += open_q
    return

  slot = bucket.setdefault("marks", {}).setdefault(mark["measurement_id"],
    {**{k: mark.get(k) for k in MARK_FIELDS}, "rows": 0, "weight": 0.0, "down2": 0.0, "up2": 0.0, "open_q": 0.0, "items": {}})
  slot["rows"] += 1
  slot["weight"] += weight
  slot["down2"] += down2
  slot["up2"] += up2
  slot["open_q"] += open_q
  slot["items"][item["item_id"]] = item["name"]

def _shown(slot: dict, **extra) -> dict:
  names = sorted(n for n in slot["items"].values() if n)
  return {**{k: slot.get(k) for k in MARK_FIELDS}, "rows": slot["rows"], "item_count": len(slot["items"]), "items": names[:3], **extra}

def top(bucket: dict, limit: int = TOP_MARKS) -> list:
  ranked = sorted(bucket.get("marks", {}).values(), key=lambda s: (-s["weight"], s["measurement_id"]))
  return [_shown(s, weight=round(s["weight"], 4)) for s in ranked[:limit]]

def confirm_first(g: dict, likely: float, total_down: float, total_up: float, limit: int = WORKLIST) -> dict:
  span2 = total_down + total_up
  span = sqrt(total_down) + sqrt(total_up)
  marks = [s for s in g.get("marks", {}).values() if s["down2"] + s["up2"] > 0]
  marks.sort(key=lambda s: (-(s["down2"] + s["up2"]), s["measurement_id"]))
  run_down, run_up, rows, halved = total_down, total_up, [], None
  
  for s in marks[:limit]:
    own_down, own_up = sqrt(max(total_down - s["down2"], 0.0)), sqrt(max(total_up - s["up2"], 0.0))
    run_down, run_up = max(run_down - s["down2"], 0.0), max(run_up - s["up2"], 0.0)
    after = own_down + own_up
    
    rows.append(_shown(s,
      share_pct=round((s["down2"] + s["up2"]) / span2 * 100.0, 1) if span2 else 0.0,
      low_after=round(likely - own_down, 4), high_after=round(likely + own_up, 4),
      narrows_pct=round((1.0 - after / span) * 100.0, 1) if span else 0.0,
      cum_low=round(likely - sqrt(run_down), 4), cum_high=round(likely + sqrt(run_up), 4)))
    if halved is None and span and sqrt(run_down) + sqrt(run_up) <= span / 2.0:
      halved = len(rows)
  u = g.get("unmarked") or {}
  
  return {"marks": rows, "total_marks": len(marks), "halved_after": halved,
    "unmarked_share_pct": round((u.get("down2", 0.0) + u.get("up2", 0.0)) / span2 * 100.0, 1) if span2 else 0.0}

def open_marks(g: dict, likely: float, limit: int = WORKLIST) -> dict:
  marks = [s for s in g.get("marks", {}).values() if s["open_q"] > 0]
  marks.sort(key=lambda s: (-s["open_q"], s["measurement_id"]))
  rows = [_shown(s, quantity=round(s["open_q"], 4),
    share_of_quantity_pct=round(s["open_q"] / abs(likely) * 100.0, 1) if likely else None) for s in marks[:limit]]
  u = g.get("unmarked") or {}
  return {"marks": rows, "total_marks": len(marks), "unmarked_quantity": round(u.get("open_q", 0.0), 4)}

def _lists(result: dict):
  for unit in result.get("units", []):
    for d in unit.get("drivers", []):
      yield d.get("marks") or []
    for o in unit.get("open_inputs", []):
      yield o.get("marks") or []
    yield (unit.get("confirm_first") or {}).get("marks") or []
    yield (unit.get("open_marks") or {}).get("marks") or []

def lookups(result: dict) -> dict:
  sheets, measurements = set(), set()
  for marks in _lists(result):
    for m in marks:
      measurements.add(m["measurement_id"])
      if m.get("sheet_id"):
        sheets.add(m["sheet_id"])
  return {"sheets": sorted(sheets), "measurements": sorted(measurements)}

def state_of(found: tuple | None, run_at=None) -> str:
  if found is None:
    return "gone"
  status, confirmed_at = found
  if status != "CONFIRMED":
    return "reopened"
  if run_at is not None and confirmed_at is not None and confirmed_at > run_at:
    return "changed"
  return "confirmed"

def annotate(result: dict, sheets: dict, measurements: dict, run_at=None) -> dict:
  seen: dict = {}
  for marks in _lists(result):
    for m in marks:
      drawing_id, project_id = sheets.get(m.get("sheet_id")) or (None, None)
      m["drawing_id"] = m.get("drawing_id") or drawing_id
      m["project_id"] = project_id
      m["state"] = state_of(measurements.get(m["measurement_id"]), run_at)
      seen[m["measurement_id"]] = m["state"]
  result["stale"] = {"marks": len(seen), **{k: sum(1 for v in seen.values() if v == k) for k in ("gone", "reopened", "changed")}}
  return result
