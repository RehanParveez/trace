from __future__ import annotations
from app.modules.drawings_boq.takeoff.prep.facts import FLOOR_ORDER

PRINTED, ARCH_SET, DECISION, DEFAULT_RULE = "PRINTED", "ARCH_SET", "DECISION", "DEFAULT_RULE"
SOURCES = (PRINTED, ARCH_SET, DECISION, DEFAULT_RULE)
CONFLICT_MM = 25.4
FT_MM, IN_MM = 304.8, 25.4
UNIT_MM = {"mm": 1.0, "in": IN_MM, "ft": FT_MM}
LADDER_KIND = {PRINTED: "SECTION", ARCH_SET: "ARCH_SET", DECISION: "DECISION", DEFAULT_RULE: "RULE"}
HEIGHT_KEYS = {"ftf_mm": "mm", "ftf_in": "in", "ftf_ft": "ft"}
FFL_KEYS = {"ffl_mm": "mm", "ffl_in": "in", "ffl_ft": "ft"}
RULE_NAME = "PK_STOREY_DEFAULT"

def to_mm(value, unit: str) -> float | None:
  factor = UNIT_MM.get(str(unit or "").lower())
  try:
    v = float(value)
  except (TypeError, ValueError):
    return None
  return round(v * factor, 1) if factor and v == v and v > 0 else None

def _level_mm(value, unit: str) -> float | None:
  factor = UNIT_MM.get(str(unit or "").lower())
  try:
    v = float(value)
  except (TypeError, ValueError):
    return None
  return round(v * factor, 1) if factor and v == v else None

def record(floor: str, ftf_mm: float | None, ffl_mm: float | None, source: str, evidence: dict | None = None) -> dict:
  return {"floor": floor, "ffl_mm": ffl_mm, "ftf_mm": ftf_mm, "source": source, "evidence": dict(evidence or {})}

def printed_records(heights: dict | None) -> list:
  out = []
  for floor, e in (heights or {}).items():
    if not isinstance(e, dict):
      continue
    
    ftf = to_mm(e.get("floor_to_floor_mm"), "mm")
    if ftf is None:
      continue
    out.append(record(floor, ftf, _level_mm(e.get("level_mm"), "mm"), PRINTED, {"basis": e.get("basis"), "clear_mm": e.get("clear_mm"), "count": e.get("count")}))
  return out

def joined_records(join: dict | None) -> list:
  out = []
  for f in ((join or {}).get("floors") or []):
    ftf = to_mm(f.get("storey_height_mm"), "mm")
    if ftf is None:
      continue
    out.append(record(str(f["floor"]), ftf, _level_mm(f.get("level_mm"), "mm"), ARCH_SET, {"state": f.get("state")}))
  return out

def decision_records(rows: list | None) -> list:
  out = []
  for r in rows or []:
    ftf = next((to_mm(r[k], u) for k, u in HEIGHT_KEYS.items() if r.get(k) is not None), None)
    ffl = next((_level_mm(r[k], u) for k, u in FFL_KEYS.items() if r.get(k) is not None), None)
    if ftf is None:
      continue
    out.append(record(str(r["floor"]).upper(), ftf, ffl, DECISION, {k: r.get(k) for k in ("answered_by", "date", "source") if r.get(k) is not None}))
  return out

def default_records(floors: list, ftf_mm: float | None) -> list:
  value = to_mm(ftf_mm, "mm")
  return [record(f, value, None, DEFAULT_RULE, {"rule": RULE_NAME}) for f in floors] if value is not None else []

def resolve(floor_keys: list | None, printed: list | None = None, joined: list | None = None, decision: list | None = None, default: list | None = None) -> dict:
  by_source = {PRINTED: printed or [], ARCH_SET: joined or [], DECISION: decision or [], DEFAULT_RULE: default or []}
  floors = [f for f in FLOOR_ORDER if f in set(floor_keys or ()) | {r["floor"] for rows in by_source.values() for r in rows}]
  floors += sorted({r["floor"] for rows in by_source.values() for r in rows} - set(floors))
  
  storeys, conflicts = [], []
  for floor in floors:
    got = [(s, r) for s in SOURCES for r in by_source[s] if r["floor"] == floor]
    if not got:
      continue
    
    measured = [(s, r) for s, r in got if s != DEFAULT_RULE]
    heights = [r["ftf_mm"] for _, r in measured]
    if len(heights) > 1 and max(heights) - min(heights) > CONFLICT_MM:
      conflicts.append({"floor": floor, "values": [{"source": s, "ftf_mm": r["ftf_mm"]} for s, r in measured]})
      continue
    storeys.append(got[0][1])
  return {"storeys": storeys, "conflicts": conflicts}

def heights_of(storeys: list | None) -> dict:
  out = {}
  for r in storeys or []:
    if r["source"] == PRINTED:
      continue
    out[r["floor"]] = {"floor_to_floor_mm": r["ftf_mm"], "level_mm": r["ffl_mm"], "basis": r["source"]}
  return out

def ladder_of(rows: list) -> dict:
  return {"what": "FLOOR_TO_FLOOR", "floor": "+".join(r["floor"] for r in rows), "kind": LADDER_KIND[rows[0]["source"]] if len({r["source"] for r in rows}) == 1 else "MIXED",
    "basis": "STOREYS", "entry": {r["floor"]: r["ftf_mm"] for r in rows}, "sources": {r["floor"]: r["source"] for r in rows}}

def heights_ft(rows: list | None) -> dict:
  out = {}
  for r in decision_records(rows):
    out[r["floor"]] = round(r["ftf_mm"] / FT_MM, 4)
  return out
