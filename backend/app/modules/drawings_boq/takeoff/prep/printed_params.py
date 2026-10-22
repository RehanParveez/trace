from __future__ import annotations
from app.engine.measure import grades as GR

COVER_PARAM_OF = {"slab": "steel_cover_slab_mm", "beam": "steel_cover_beam_mm", "column": "steel_cover_column_mm", "footing": "steel_cover_footing_mm", "wall": "steel_cover_wall_mm"}
PCC_PARAM = "pcc_thickness_mm"
FILL_PARAM = "fill_layer_mm"
PLASTER_PARAM = "plaster_thickness_mm"
SOIL_DEPTH_PARAM, SOIL_CEMENT_PARAM = "soil_stab_depth_mm", "soil_stab_cement_pct"
LAP_PARAM = "bar_lap_dia"
EIGHTH_MM = 3.175

def _bar_key(dia_mm: float) -> str | None:
  """A printed bar size as the bar number the steel reader uses (eighths of an inch): 9.53 mm is bar 3."""
  n = round(float(dia_mm) / EIGHTH_MM)
  return str(n) if 2 <= n <= 12 and abs(n * EIGHTH_MM - float(dia_mm)) < 0.6 else None

def _note(row: dict) -> dict:
  return {"text": row.get("text"), "pages": sorted(row.get("pages") or []), "count": int(row.get("count", 1))}

def _single(rows: list, name: str, conflicts: list) -> dict | None:
  """The one row of a note, or None when two rows print different values (the conflict is listed)."""
  by: dict = {}
  for r in rows:
    by.setdefault(round(float(r["value_mm"]), 2), r)
  if len(by) == 1:
    return next(iter(by.values()))
  if len(by) > 1:
    conflicts.append({"param": name, "values": [{"value_mm": v, **_note(r)} for v, r in sorted(by.items())]})
  return None

def from_items(items: list) -> dict:
  params: dict = {}
  notes: dict = {}
  conflicts: list = []
  covers: dict = {}
  for it in items or []:
    if it.get("kind") != "CLEAR_COVER" or it.get("value_mm") is None:
      continue
    scope = str(it.get("scope") or "")
    if scope not in COVER_PARAM_OF:
      continue
    where = str(it.get("where") or "")
    if scope == "slab" and "top" in where and "bottom" not in where:
      continue
  
    covers.setdefault(scope, []).append(it)
  for scope, rows in sorted(covers.items()):
    name = COVER_PARAM_OF[scope]
    row = _single(rows, name, conflicts)
    if row is not None:
      params[name] = round(float(row["value_mm"]), 2)
      notes[name] = _note(row)
  for kind, name in (("PCC_THICKNESS", PCC_PARAM), ("FILL_LAYER", FILL_PARAM), ("PLASTER_THICKNESS", PLASTER_PARAM)):
    rows = [r for r in items or [] if r.get("kind") == kind and r.get("value_mm") is not None]
    row = _single(rows, name, conflicts) if rows else None
    if row is not None:
      params[name] = round(float(row["value_mm"]), 2)
      notes[name] = _note(row)
      
  soil = _soil(items or [], params, notes, conflicts)
  table: dict = {}
  clash: set = set()
  for r in items or []:
    if r.get("kind") != "LAP_LENGTH" or r.get("value_mm") is None or r.get("bar_dia_mm") is None:
      continue
    key = _bar_key(r["bar_dia_mm"])
    if key is None:
      continue
  
    value = round(float(r["value_mm"]), 1)
    if key in table and table[key]["mm"] != value:
      clash.add(key)
    table.setdefault(key, {"mm": value, **_note(r)})
  for key in sorted(clash):
    conflicts.append({"param": "lap_table", "bar": key, "values": [{"value_mm": table[key]["mm"], **_note(table[key])}]})
    
    del table[key]
  lap_table = {k: v["mm"] for k, v in sorted(table.items(), key=lambda kv: int(kv[0]))}
  if lap_table:
    ratios = [mm / (int(k) * EIGHTH_MM) for k, mm in lap_table.items()]
    params[LAP_PARAM] = round(sum(ratios) / len(ratios), 1)
    notes[LAP_PARAM] = {"text": "; ".join(f"bar {k} = {mm:g} mm" for k, mm in lap_table.items()), "pages": sorted({p for v in table.values() for p in v["pages"]}),
      "count": sum(v["count"] for v in table.values())}
  return {"params": params, "lap_table_mm": lap_table, "notes": notes, "conflicts": conflicts, "grades": GR.rules_from_items(items or []), "soil": soil}

def _soil(items: list, params: dict, notes: dict, conflicts: list) -> dict | None:
  rows = [r for r in items if r.get("kind") == "SOIL_STABILISATION" and r.get("cement_pct") is not None]
  
  if not rows:
    return None
  out: dict = {"notes": [{**_note(r), "cement_pct": r["cement_pct"], "depth_mm": r.get("value_mm"), "loose_only": bool(r.get("loose"))} for r in rows], "cement_pct": None, "depth_mm": None}
  pcts = sorted({round(float(r["cement_pct"]), 2) for r in rows})
  if len(pcts) == 1:
    out["cement_pct"] = pcts[0]
    params[SOIL_CEMENT_PARAM] = pcts[0]
    notes[SOIL_CEMENT_PARAM] = _note(rows[0])
  else:
    conflicts.append({"param": SOIL_CEMENT_PARAM, "values": [{"value": v} for v in pcts]})
  depths = [r for r in rows if r.get("value_mm") is not None]
  row = _single(depths, SOIL_DEPTH_PARAM, conflicts) if depths else None
  if row is not None:
    out["depth_mm"] = round(float(row["value_mm"]), 2)
    params[SOIL_DEPTH_PARAM] = out["depth_mm"]
    notes[SOIL_DEPTH_PARAM] = _note(row)
  return out

def for_run(printed: dict) -> dict:
  return {"params": dict(printed.get("params") or {}), "lap_table_mm": dict(printed.get("lap_table_mm") or {}), "grades": dict(printed.get("grades") or {})}
