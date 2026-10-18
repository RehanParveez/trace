from __future__ import annotations
from app.modules.drawings_boq import quantity_range as QR
from app.modules.drawings_boq import range_drivers as RD
from app.modules.drawings_boq.lab.compare import closeness_of
from statistics import mean

LEFT_OUT_CLASSES = ("QS_ERROR", "CONVENTION")
TOP = 5

def _r1(v):
  return None if v is None else round(v, 1)

def range_payload(rows: list) -> dict:
  groups: dict = {}
  
  for r in rows:
    key = (r.get("work_item_code") or "?", r.get("unit") or "")
    g = groups.setdefault(key, {"item_id": key[0], "name": key[0], "unit": key[1], "factor": 1, "rows": []})
    g["rows"].append((r.get("quantity") or 0, QR.row_range(r.get("trace"))))
  units = []
  
  for u in RD.build(list(groups.values()))["units"]:
    likely = u["likely"]
    spread = round((u["high"] - u["low"]) / abs(likely) * 100.0, 2) if likely else None
    units.append({"unit": u["unit"], "likely": likely, "low": u["low"], "high": u["high"], "spread_pct": spread, "rows": u["rows"],
      "bounded_rows": u["bounded_rows"], "unbounded_rows": u["unbounded_rows"], "no_range_rows": u["no_range_rows"], "leaves_out_rows": u["leaves_out_rows"],
      "top_drivers": [{"name": d["name"], "basis": d["basis"], "share_pct": d["share_pct"]} for d in u["drivers"][:TOP]],
      "open_inputs": [{"name": o["name"], "rows": o["rows"], "quantity": o["quantity"]} for o in u["open_inputs"][:TOP]]})
  return {"units": units}

def compare_payload(result: dict, scope: str) -> dict:
  lines = result.get("lines") or []
  scored = [(l, closeness_of(l.get("status"), l.get("error_pct"))) for l in lines]
  scored = [(l, c) for l, c in scored if c is not None]
  kept = [c for l, c in scored if l.get("class") not in LEFT_OUT_CLASSES]
  found = [c for l, c in scored if l.get("status") != "MISSING"]
  
  m = result.get("measures") or {}
  return {"scope": scope, "tolerance_pct": result.get("tolerance_pct"), "scored": len(scored),
    "closeness_pct": _r1(mean(c for _, c in scored)) if scored else None,
    "found_pct": _r1(mean(found)) if found else None,
    "adjusted_pct": _r1(mean(kept)) if kept else None,
    "compared": m.get("compared"), "within_tolerance": m.get("within_tolerance"), "coverage_pct": m.get("coverage_pct"),
    "open_differences": sum(1 for l in lines if l.get("status") in ("DIFF", "MISSING", "EXTRA") and not l.get("class"))}

def _delta(now, before):
  return None if now is None or before is None else round(now - before, 1)

def trend(points: list) -> dict:
  ordered = sorted(points, key=lambda p: (str(p.get("run_created_at") or ""), str(p.get("created_at") or "")))
  
  closeness: list = []
  last_by_label: dict = {}
  for p in ordered:
    if p["kind"] != "COMPARE":
      continue
  
    pl = p["payload"] or {}
    before = last_by_label.get(p["label"])
    closeness.append({"run_id": str(p["run_id"]), "at": p["run_created_at"], "label": p["label"], "scope": pl.get("scope"), "closeness_pct": pl.get("closeness_pct"),
      "found_pct": pl.get("found_pct"), "adjusted_pct": pl.get("adjusted_pct"), "within_tolerance": pl.get("within_tolerance"), "compared": pl.get("compared"),
      "open_differences": pl.get("open_differences"), "change": _delta(pl.get("closeness_pct"), before)})
    last_by_label[p["label"]] = pl.get("closeness_pct")
  ranges: list = []
  prev: dict = {}
  for p in ordered:
    if p["kind"] != "RANGE":
      continue
  
    units = []
    for u in (p["payload"] or {}).get("units") or []:
      before = prev.get(u["unit"])
      units.append({"unit": u["unit"], "likely": u["likely"], "spread_pct": u["spread_pct"], "change": _delta(u["spread_pct"], before and before["spread_pct"]),
        "open_rows": u["unbounded_rows"], "open_change": None if before is None else u["unbounded_rows"] - before["unbounded_rows"],
        "top_driver": (u["top_drivers"] or [None])[0], "open_inputs": u["open_inputs"]})
      prev[u["unit"]] = u
    ranges.append({"run_id": str(p["run_id"]), "at": p["run_created_at"], "units": units})
  return {"closeness": closeness, "ranges": ranges}
