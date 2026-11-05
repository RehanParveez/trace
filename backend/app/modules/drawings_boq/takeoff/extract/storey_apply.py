from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import read_status as RS
from app.modules.drawings_boq.takeoff.extract import structure_joins as SJ
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.model import storeys as ST

ALL = "ALL"
NEEDS, CONFLICT = "NEEDS_STOREY_HEIGHT", "STOREY_CONFLICT"

def _live(c) -> bool:
  return c.decision != "REJECTED" and not (c.facts or {}).get("set_aside")

def unfloored_column_layout(row: dict) -> bool:
  meta = row.get("meta") or {}
  ident = meta.get("identity") or {}
  title = row.get("title") or {}
  if RS.role_of(ident) != "PLAN" or RS.plan_kind_of(ident) != "COLUMN_LAYOUT":
    return False
  return not (ident.get("floor") or (None if title.get("composite") else title.get("level_hint")))

def stack_of(tag: str, cells: dict) -> list:
  floors = list((cells.get(SJ.norm(tag)) or {}))
  return sorted(floors, key=SJ._rank)

def _hold(c, code: str, **extra) -> None:
  RS.mark(c, RS.UNSURE, [code])
  c.notes = [n for n in c.notes if n.get("code") != code] + [C.note(code, **extra)]

def apply(rows: list, resolved: dict) -> dict:
  by_floor = {r["floor"]: r for r in resolved.get("storeys") or []}
  conflicts = {x["floor"]: x for x in resolved.get("conflicts") or []}
  cells = SJ.schedule_index(rows)
  seen = {"pages": [], "columns": 0, "with_height": 0, "held": 0}
  for row in rows:
    if not unfloored_column_layout(row):
      continue
  
    seen["pages"].append(row["page_no"])
    for c in row.get("candidates") or []:
      if c.category != "COLUMN" or not _live(c):
        continue
    
      seen["columns"] += int(c.count or 1)
      c.facts = {**(c.facts or {}), "floor_all": {"floor": ALL, "reason": "FLOOR_FROM_SCHEDULE"}}
      c.notes = [n for n in c.notes if n.get("code") != "FLOOR_FROM_SCHEDULE"] + [C.note("FLOOR_FROM_SCHEDULE")]
      join = (c.facts or {}).get("schedule_join") or {}
      floors = stack_of(c.tag, cells) if c.tag else []
      if not floors and join.get("to"):
        floors = [join["to"]["key"].split(":", 1)[1]]
      c.facts["storey_stack"] = floors
      bad = [f for f in floors if f in conflicts]
      lacking = [f for f in floors if f not in by_floor]
      
      if not floors or bad or lacking:
        seen["held"] += int(c.count or 1)
        if bad:
          _hold(c, CONFLICT, floors=bad, values=[conflicts[f]["values"] for f in bad])
        else:
          _hold(c, NEEDS, floors=lacking or ["?"])
        continue
    
      rows_used = [by_floor[f] for f in floors]
      total = round(sum(r["ftf_mm"] for r in rows_used), 1)
      c.params = {**(c.params or {}), "depth_mm": total}
      c.missing = [m for m in (c.missing or []) if m != "height_mm"]
      c.facts["storey_heights"] = [{"floor": r["floor"], "ftf_mm": r["ftf_mm"], "source": r["source"], "evidence": r["evidence"]} for r in rows_used]
      c.notes = [n for n in c.notes if n.get("code") != "HEIGHT_FROM_STOREYS"] + [C.note("HEIGHT_FROM_STOREYS", ladder=ST.ladder_of(rows_used), height_mm=total, floors=floors)]
      seen["with_height"] += int(c.count or 1)
      
  return seen
