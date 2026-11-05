from __future__ import annotations
import copy
import dataclasses
import hashlib
from app.modules.drawings_boq.takeoff.extract import structure_joins as SJ
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.model import storeys as ST
from app.modules.drawings_boq.takeoff.extract import read_status as RS
from app.modules.drawings_boq.takeoff.extract import note_scope as NS
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS

DECISION_PREFIX = "column_conflict."
CONVENTION = "X9"
CFT_MM3 = 304.8 ** 3
KEPT = ("FLOOR_FROM_SCHEDULE", "UNMARKED_COLUMNS", "PLANTED_COLUMN")
DROPPED = ("HEIGHT_FROM_STOREYS", "SIZE_FROM_SCHEDULE", "SIZE_NOT_FOUND")

def _key(*parts) -> str:
  return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:24]

def _fmt_mm(v: float) -> str:
  return str(int(round(v))) if abs(v - round(v)) < 0.05 else f"{v:.1f}"

def _live(c) -> bool:
  return c.decision != "REJECTED" and not (c.facts or {}).get("set_aside")

def _is_schedule(row: dict) -> bool:
  return bool(((((row.get("meta") or {}).get("structure_tables") or {}).get("column_schedule")) or {}).get("cells"))

def options_of(rec: dict) -> list:
  conflicts = (rec.get("sketch") or {}).get("conflicts") or []
  if not conflicts:
    return []
  out = []
  
  for label, key in (("PRINTED", "printed_in"), ("SKETCH", "sketch_in")):
    s = conflicts[0].get(key)
    if s and len(s) == 2:
      value = f"{s[0]:g}x{s[1]:g}"
      if value not in {o["value"] for o in out}:
        out.append({"value": value, "size_in": [float(s[0]), float(s[1])], "from": label})
        
  return out if len(out) > 1 else []

def parse_option(value: str) -> list | None:
  try:
    a, b = str(value).lower().replace("×", "x").split("x")
    return [round(float(a) * SJ.IN_MM, 1), round(float(b) * SJ.IN_MM, 1)]
  except ValueError:
    return None

def _member(c, floor: str, rec: dict | None, cell: dict | None, storey: dict | None, floors: list, *, planted_at: list | None = None, count: int | None = None) -> object:
  params = {k: v for k, v in (c.params or {}).items() if k not in ("length_mm", "width_mm", "depth_mm", "height_mm", "dims_basis")}
  missing = [m for m in (c.missing or []) if m not in ("size", "height_mm")]
  facts = {k: v for k, v in (c.facts or {}).items() if k not in ("set_aside", "size_used_mm", "size_schedule_mm", "storey_heights", "storey_stack", "floor_all", "schedule_join")}
  facts["view"] = {**(facts.get("view") or {}), "level_hint": floor}
  notes = [n for n in (c.notes or []) if n.get("code") in KEPT]
  n = int(count if count is not None else c.count or 1)
  size = SJ.cell_size_mm(rec) if rec else None
  trusted = bool(rec) and SJ.cell_trusted(rec)
  options = options_of(rec) if rec else []
  
  stack = {"mark": c.tag, "floor": floor, "floors": list(floors), "of": len(floors), "convention": CONVENTION, "cell": cell["key"] if cell else None, "sheet": cell["sheet"] if cell else None}
  if trusted and size:
    params.update({"length_mm": size[0], "width_mm": size[1], "dims_basis": "SPECIFIED"})
    facts["size_schedule_mm"], facts["size_used_mm"] = size, size
    notes.append(C.note("SIZE_FROM_SCHEDULE"))
  else:
    missing.insert(0, "size")
    why = "the sketch disagrees with the printed size" if options else "the size is not confirmed" if rec else "no schedule cell for this mark on this floor"
    stack["size_held"] = why
    notes.append(C.note("COLUMN_SIZE_HELD", reason=why))
    if options:
      height = storey["ftf_mm"] if storey else None
      areas = [o["size_in"][0] * o["size_in"][1] * SJ.IN_MM ** 2 for o in options]
      facts["column_conflict"] = {"id": DECISION_PREFIX + str(c.tag), "mark": c.tag, "floor": floor, "options": options, "chosen": None,
        "cft_range": [round(n * min(areas) * height / CFT_MM3, 3), round(n * max(areas) * height / CFT_MM3, 3)] if height else None}
      
  if storey:
    params["depth_mm"] = storey["ftf_mm"]
    facts["storey_heights"] = [{"floor": floor, "ftf_mm": storey["ftf_mm"], "source": storey["source"], "evidence": storey["evidence"]}]
    notes.append(C.note("HEIGHT_FROM_STOREYS", ladder={**ST.ladder_of([storey]), "convention": CONVENTION}, height_mm=storey["ftf_mm"], floors=[floor]))
  else:
    missing.append("height_mm")
  facts["stack"] = stack
  geometry = {"points": [list(p) for p in planted_at]} if planted_at is not None else copy.deepcopy(c.geometry)
  label = f"{c.tag} ×{n}" + (f" · {_fmt_mm(params['length_mm'])}×{_fmt_mm(params['width_mm'])} mm" if "length_mm" in params else "") + f" · {floor.title()}"
  m = dataclasses.replace(c, key=_key("COLUMN", "STACK", c.key, c.tag, floor), label=label, params=params, missing=missing, facts=facts, notes=notes, count=n, geometry=geometry)
  m.decision = "PENDING"
  if not storey:
    RS.mark(m, RS.UNSURE, ["NEEDS_STOREY_HEIGHT"])
    m.notes = m.notes + [C.note("NEEDS_STOREY_HEIGHT", floors=[floor])]
  m.status = NS.status_of(m.notes)
  return m

def apply(rows: list, resolved: dict) -> dict:
  by_floor = {r["floor"]: r for r in resolved.get("storeys") or []}
  cells = SJ.schedule_index(rows)
  seen = {"marks": 0, "members": 0, "planted": 0, "floors": {}}
  for row in rows:
    made: list = []
    
    for c in list(row.get("candidates") or []):
      if c.category != "COLUMN" or not _live(c) or not (c.facts or {}).get("floor_all") or not c.tag:
        continue
      floors = list((c.facts or {}).get("storey_stack") or [])
      if not floors:
        continue
      held = (cells.get(SJ.norm(c.tag)) or {})
      for f in floors:
        cell = held.get(f)
        
        made.append(_member(c, f, cell["rec"] if cell else None, {"key": SJ.cell_key(cell["rec"]), "sheet": cell["sheet"]} if cell else None, by_floor.get(f), floors))
      c.facts = {**(c.facts or {}), "set_aside": {"by": FS.STACK_BY, "mark": c.tag, "floors": floors}}
      seen["marks"] += 1
      
    sj = ((row.get("meta") or {}).get("structure_joins") or {})
    if not _is_schedule(row) and sj.get("planted"):
      groups: dict = {}
      for p in sj["planted"]:
        floor = p.get("floor") or (p["to"]["key"].split(":", 1)[1] if p.get("to") and p.get("how") in ("ONLY_FLOOR", "FLOOR") else None)
        if floor and p.get("status") == SJ.JOINED:
          groups.setdefault((p["mark"], floor), []).append(p["at"])
      work_item, mode, kind = C.SUGGESTIONS["COLUMN"]
      for (mark, floor), pts in sorted(groups.items()):
        held = (cells.get(SJ.norm(mark)) or {})
        cell = held.get(floor)
        base = _planted_base(row, mark, floor, pts, work_item, mode, kind)
        made.append(_member(base, floor, cell["rec"] if cell else None, {"key": SJ.cell_key(cell["rec"]), "sheet": cell["sheet"]} if cell else None, by_floor.get(floor), [floor], planted_at=pts, count=len(pts)))
        seen["planted"] += len(pts)
    if made:
      row["candidates"] = list(row["candidates"]) + made
      for m in made:
        seen["members"] += 1
        f = (m.facts.get("stack") or {}).get("floor")
        seen["floors"][f] = seen["floors"].get(f, 0) + int(m.count or 1)
  return seen

def _planted_base(row: dict, mark: str, floor: str, pts: list, work_item, mode, kind):
  from app.modules.drawings_boq.takeoff.extract.pipeline import Candidate
  return Candidate(key=_key("COLUMN", "PLANTED", row["page_no"], mark, floor), category="COLUMN", kind=kind, quantity_mode=mode, label=mark, tag=mark, geometry={"points": []}, params={}, missing=["size", "height_mm"],
    work_item=work_item, status="VALID", confidence=0.6, facts={"tag": mark, "planted": True, "count": len(pts), "view": {"key": "PLANTED:" + mark, "caption": "PLANTED COLUMNS", "kind": "STRUCT_PLAN", "level_hint": floor}},
    notes=[C.note("PLANTED_COLUMN")], source="TAG_SCAN", count=len(pts))
