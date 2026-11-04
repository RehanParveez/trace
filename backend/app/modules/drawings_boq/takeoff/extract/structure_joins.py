from __future__ import annotations
from app.modules.drawings_boq.takeoff.prep.details import norm_mark
from collections import Counter
from app.modules.drawings_boq.takeoff.extract import config as C

FLOOR_RANK = ("BASEMENT", "GROUND", "FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH", "ROOF", "MUMTY")
JOINED, ASSUMED, MISSING, UNSURE = "JOINED", "ASSUMED", "JOIN_MISSING", "UNSURE"
SIZE_TOL_MM = 13.0
IN_MM = 25.4

def norm(mark) -> str:
  return norm_mark(str(mark or ""))

def _rank(floor: str) -> int:
  return FLOOR_RANK.index(floor) if floor in FLOOR_RANK else len(FLOOR_RANK)

def cell_key(rec: dict) -> str:
  return f"{rec['mark']}:{rec['floor']}"

def cell_size_mm(rec: dict) -> list | None:
  s = (rec.get("size") or {}).get("size_in")
  return [round(s[0] * IN_MM, 1), round(s[1] * IN_MM, 1)] if s else None

def cell_trusted(rec: dict) -> bool:
  size = rec.get("size") or {}
  if not size.get("size_in") or not size.get("confirmed"):
    return False
  return not ((rec.get("sketch") or {}).get("conflicts") or [])

def schedule_index(rows: list) -> dict:
  out: dict = {}
  for row in rows:
    cells = ((((row.get("meta") or {}).get("structure_tables") or {}).get("column_schedule")) or {}).get("cells") or []
    for rec in cells:
      if rec.get("state") != "READ":
        continue
      slot = out.setdefault(norm(rec["mark"]), {})
      held = slot.get(rec["floor"])
      if held is None:
        slot[rec["floor"]] = {"sheet": row["page_no"], "rec": rec}
      elif cell_size_mm(held["rec"]) != cell_size_mm(rec) or held["rec"].get("steel") != rec.get("steel"):
        held["duplicate"] = True
        
  return out

def _same_everywhere(cells: dict) -> bool:
  seen = {(tuple(cell_size_mm(c["rec"]) or ()), tuple(c["rec"].get("steel") or ())) for c in cells.values()}
  return len(seen) == 1

def join_column(mark: str, floor: str | None, index: dict) -> dict:
  cells = index.get(norm(mark))
  if not cells:
    return {"status": MISSING, "how": None, "to": None, "size_mm": None, "feed": False, "reason": f"no schedule cell for {mark}"}
  if floor:
    held = cells.get(floor)
    if held is None:
      return {"status": MISSING, "how": "FLOOR", "to": None, "size_mm": None, "feed": False, "reason": f"{mark} has no cell on the {floor.lower()} floor"}
    how = "FLOOR"
  elif len(cells) == 1:
    held, how = next(iter(cells.values())), "ONLY_FLOOR"
  elif _same_everywhere(cells):
    held, how = cells[min(cells, key=_rank)], "SAME_ON_EVERY_FLOOR"
  else:
    held, how = cells[min(cells, key=_rank)], "LOWEST_FLOOR"
  rec = held["rec"]
  to = {"sheet": held["sheet"], "class": "COLUMN_SCHEDULE_CELL", "key": cell_key(rec)}
  
  size = cell_size_mm(rec)
  if held.get("duplicate"):
    return {"status": UNSURE, "how": how, "to": to, "size_mm": None, "feed": False, "reason": f"{mark} is printed twice with different cells"}
  if how == "LOWEST_FLOOR":
    return {"status": ASSUMED, "how": how, "to": to, "size_mm": size, "feed": False, "reason": f"{mark} differs by floor and the plan names none; the lowest floor's cell is shown, not used"}
  feed = cell_trusted(rec)
  reason = None if feed else ("the size is not confirmed" if not (rec.get("size") or {}).get("confirmed") else "the sketch disagrees with the printed size")
  return {"status": JOINED, "how": how, "to": to, "size_mm": size, "feed": feed, "reason": reason}

def beam_section_index(rows: list) -> dict:
  out: dict = {}
  for row in rows:
    for rec in ((((row.get("meta") or {}).get("structure_tables") or {}).get("beam_sections")) or {}).get("sections") or []:
      k = norm(rec["mark"])
      held = out.get(k)
      if held is None:
        out[k] = {"sheet": row["page_no"], "rec": rec, "conflict": False}
      elif (held["rec"]["width_in"], held["rec"]["depth_in"]) != (rec["width_in"], rec["depth_in"]):
        held["conflict"] = True
        
  return out

def join_beam(mark: str, size_mm: tuple | None, index: dict) -> dict:
  held = index.get(norm(mark))
  
  if held is None:
    return {"status": MISSING, "to": None, "size_mm": None, "feed": False, "reason": f"no section for {mark}"}
  rec = held["rec"]
  to = {"sheet": held["sheet"], "class": "BEAM_SECTION", "key": f"{rec['mark']}-section"}
  sec = [round(rec["width_in"] * IN_MM, 1), round(rec["depth_in"] * IN_MM, 1)]
  if held["conflict"] or rec.get("conflicts"):
    return {"status": UNSURE, "to": to, "size_mm": sec, "feed": False, "reason": "the section is drawn with different sizes or disagrees with its own sketch"}
  if size_mm and (abs(size_mm[0] - sec[0]) > SIZE_TOL_MM or abs(size_mm[1] - sec[1]) > SIZE_TOL_MM):
    return {"status": UNSURE, "to": to, "size_mm": sec, "feed": False, "reason": f"the plan reads {size_mm[0] / IN_MM:g}x{size_mm[1] / IN_MM:g} in and the section prints {rec['width_in']:g}x{rec['depth_in']:g} in", "conflict": "SIZE_PLAN_VS_SECTION"}
  return {"status": JOINED, "to": to, "size_mm": sec, "feed": True, "reason": None}

def footing_section_index(rows: list) -> dict:
  out: dict = {}
  for row in rows:
    meta = row.get("meta") or {}
    for rec in list(meta.get("footing_sections") or []) + list(((meta.get("structure_tables") or {}).get("footing_sections") or {}).get("sections") or []):
      if rec.get("mark") and norm(rec["mark"]) not in out:
        out[norm(rec["mark"])] = {"sheet": row["page_no"], "rec": rec}
  return out

def join_footing(mark: str, index: dict) -> dict:
  held = index.get(norm(mark))
  if held is None:
    return {"status": MISSING, "to": None, "reason": f"no section was read for {mark}"}
  return {"status": JOINED, "to": {"sheet": held["sheet"], "class": "FOOTING_SECTION", "key": str(held["rec"]["mark"])}, "reason": None}

def _live(c) -> bool:
  aside = (c.facts or {}).get("set_aside")
  return c.decision != "REJECTED" and not aside

def _floor_of(row: dict) -> str | None:
  ident = (row.get("meta") or {}).get("identity") or {}
  title = row.get("title") or {}
  return ident.get("floor") or (None if title.get("composite") else title.get("level_hint"))

def _has_size(c) -> bool:
  p = c.params or {}
  return bool(p.get("length_mm") and p.get("width_mm"))

def _feed_column(c, join: dict) -> None:
  a, b = join["size_mm"]
  c.params["length_mm"], c.params["width_mm"] = a, b
  c.params["dims_basis"] = "SPECIFIED"
  c.facts["size_schedule_mm"] = [a, b]
  c.facts["size_used_mm"] = [a, b]
  c.notes = [n for n in c.notes if n.get("code") != "SIZE_NOT_FOUND"] + [C.note("SIZE_FROM_SCHEDULE")]

def _feed_beam(c, join: dict) -> None:
  w, d = join["size_mm"]
  c.params["width_mm"], c.params["depth_mm"] = w, d
  c.facts["size_section_mm"] = [w, d]
  c.notes = [n for n in c.notes if n.get("code") != "SIZE_NOT_FOUND"]

def join_rows(rows: list) -> dict:
  cells = schedule_index(rows)
  sections = beam_section_index(rows)
  footings = footing_section_index(rows)
  total = {"columns": Counter(), "planted": Counter(), "beams": Counter(), "footings": Counter()}
  fed: list = []
  
  for row in rows:
    page, floor = row["page_no"], _floor_of(row)
    meta = row.setdefault("meta", {})
    sj: dict = {"columns": [], "planted": [], "beams": [], "footings": []}
    
    if cells:
      for c in row.get("candidates") or []:
        if c.category != "COLUMN" or not c.tag or not _live(c):
          continue
        j = join_column(c.tag, floor, cells)
        c.facts = {**(c.facts or {}), "schedule_join": j}
        total["columns"][j["status"]] += int(c.count or 1)
        if j["feed"] and not _has_size(c) and j["size_mm"]:
          _feed_column(c, j)
          fed.append({"sheet": page, "class": "COLUMN", "mark": c.tag, "size_mm": j["size_mm"], "to": j["to"]["key"]})
        sj["columns"].append({"mark": c.tag, "count": int(c.count or 1), **j})
        
      labels = (((meta.get("structure_tables") or {}).get("planted_labels")) or {}).get("labels") or []
      for lab in labels:
        if norm(lab["mark"]) not in cells:
          continue
        j = join_column(lab["mark"], floor, cells)
        own = floor or (j["to"]["key"].split(":", 1)[1] if j["to"] and j["how"] in ("ONLY_FLOOR", "FLOOR") else None)
        sj["planted"].append({"mark": lab["mark"], "at": lab["at"], "floor": own, **j})
        total["planted"][j["status"]] += 1
        
    if sections:
      for c in row.get("candidates") or []:
        if c.category != "BEAM" or not c.tag or not _live(c):
          continue
        p = c.params or {}
        j = join_beam(c.tag, (p["width_mm"], p["depth_mm"]) if p.get("width_mm") and p.get("depth_mm") else None, sections)
        c.facts = {**(c.facts or {}), "section_join": j}
        total["beams"][j["status"]] += int(c.count or 1)
        if j["feed"] and not (p.get("width_mm") and p.get("depth_mm")):
          _feed_beam(c, j)
          fed.append({"sheet": page, "class": "BEAM", "mark": c.tag, "size_mm": j["size_mm"], "to": j["to"]["key"]})
        sj["beams"].append({"mark": c.tag, "count": int(c.count or 1), **j})
        
    for c in row.get("candidates") or []:
      if c.category != "FOOTING" or not c.tag or not _live(c):
        continue
      j = join_footing(c.tag, footings)
      c.facts = {**(c.facts or {}), "footing_section_join": j}
      total["footings"][j["status"]] += int(c.count or 1)
      sj["footings"].append({"mark": c.tag, "count": int(c.count or 1), **j})
    if any(sj.values()):
      meta["structure_joins"] = sj
  return {**total, "fed": fed}
