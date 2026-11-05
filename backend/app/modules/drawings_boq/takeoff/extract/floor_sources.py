from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import combine_plan as CP
from app.modules.drawings_boq.takeoff.extract import floor_overlap as FO
from app.modules.drawings_boq.takeoff.extract import floor_order as FOR
from app.modules.drawings_boq.takeoff.extract import base_plan as BP
from app.modules.drawings_boq.takeoff.extract import config as C

SET_ASIDE = "set_aside"         
SET_ASIDE_BY = "FLOOR_CHOICE"
ROLE_BY = "ROLE_UNEXPECTED"
STACK_BY = "COLUMN_STACK"
FAMILY_BY = "FOOTING_FAMILY"
LAYOUT_BY = "LAYOUT_CHOICE"
MARK_BY = "MARK_CHOICE"
OPTION_BY = "OPTION_CHOICE"
ASSUMED_BY = "ASSUMED_ALTERNATIVE"     
TANK_BY = "TANK_PAIR"
COPY_BY = "COPY_CHOICE"
OPENINGS = ("DOOR", "WINDOW")
PLAN, KEY_PLAN = "PLAN", "KEY_PLAN"
COPY_PREFIX = "FLOOR_COPY:"

ORDER = ["FOUNDATION", "BASEMENT", "GROUND", "MEZZANINE", "FIRST", "SECOND", "THIRD", "FOURTH", "TYPICAL", "ROOF"]

def in_floor(c, floor: str, sheet_floor: str | None) -> bool:
  """An item that belongs to this floor of its sheet (a slab is read from the framing sheets, not from the plans, and is left out)."""
  return c.category != "SLAB" and (FO.level_of(c) or sheet_floor) == floor

def lift_assumed(cands: list, work_item: str, note) -> int:
  items = [c for c in cands if (getattr(c, "suggested_work_item", None) or getattr(c, "work_item", None)) == work_item and getattr(c, "status", None) != "INVALID"]
  if any(not is_set_aside(c) for c in items):
    return 0
  lifted = [c for c in items if ((c.facts or {}).get(SET_ASIDE) or {}).get("by") == ASSUMED_BY]
  for c in lifted:
    c.facts = {k: v for k, v in (c.facts or {}).items() if k != SET_ASIDE}
    c.decision = "NEW"
    c.notes = [*(c.notes or []), note("ROOF_ASSUMED_COUNTED")]
  return len(lifted)

def is_set_aside(c) -> bool:
  """Rejected because the floor's other sheet was chosen, or because the other sheet holds the same item (a combine)."""
  return ((c.facts or {}).get(SET_ASIDE) or {}).get("by") in (SET_ASIDE_BY, CP.BY, LAYOUT_BY, MARK_BY, OPTION_BY, ASSUMED_BY, COPY_BY, TANK_BY, ROLE_BY, STACK_BY, FAMILY_BY)

def _source(sheet: dict, floor: str, from_plans: bool) -> dict:
  title = sheet["title"] or {}
  sheet_floor = None if title.get("composite") else title.get("level_hint")
  rows = [c for c in sheet["candidates"] if in_floor(c, floor, sheet_floor) and not BP.is_electrical(c)]
  walls = [c for c in rows if c.category == "WALL"]
  plan = next((p for p in ((sheet["stats"] or {}).get("plan_regions") or {}).get("plans") or [] if p.get("level_hint") == floor), None)
  own = [c for c in rows if "copy_used" not in (c.facts or {})]
  open_n = sum(1 for c in own if c.decision == "NEW")
  accepted = sum(1 for c in own if c.decision == "ACCEPTED")
  
  basis = "ORDER" if sheet.get("_order") else ((sheet.get("identity") or {}).get("floor_basis") if (sheet.get("identity") or {}).get("floor") == floor else None) or "TITLE"
  return {"sheet_id": sheet["sheet_id"], "page_no": sheet["page_no"], "from_plans": from_plans, "drawing_id": sheet.get("drawing_id"), "drawing_name": sheet.get("drawing_name"),
    "drawing_order": sheet.get("drawing_order") or 0, "plan_kind": (sheet.get("identity") or {}).get("plan_kind"), "dims": int((sheet.get("clues") or {}).get("dim_pairs") or 0),
    "read_as": (sheet["stats"] or {}).get("read_as"),"floor_basis": basis, "floor_guess": (sheet.get("_order") or {}).get("reason"), "advice": ((sheet["stats"] or {}).get("sheet_role") or {}).get("advice"), "purpose": ((sheet["stats"] or {}).get("sheet_role") or {}).get("purpose"),
    "caption": plan["caption"] if plan else title.get("title"),
    "wall_m": round(sum(float((c.facts or {}).get("length_cc_m") or 0.0) for c in walls), 1), "walls": len(walls), "items": len(rows),
    "open": open_n, "accepted": accepted, "rejected": sum(1 for c in rows if c.decision == "REJECTED"),
    "combined": sum(1 for c in rows if CP.combined_away(c)),
    "added": sum(1 for c in rows if c.decision != "REJECTED" and ((c.facts or {}).get(CP.STAMP) or {}).get("role") == CP.ADDED),
    "added_wall_m": round(sum(float((c.facts or {}).get("length_cc_m") or 0.0) for c in walls if c.decision != "REJECTED" and ((c.facts or {}).get(CP.STAMP) or {}).get("role") == CP.ADDED), 1),
    "set_aside": bool(rows) and open_n == 0 and accepted == 0}

def _suggest(sources: list) -> str | None:
  """The source to use unless the person says otherwise: the one that already has accepted items (it cannot be set aside), else the floor's own
  sheet over the sheet that holds every plan, else the lowest page. None when two sources both have accepted items: that is for the person to untangle."""
  held = [s for s in sources if s["accepted"] > 0]
  if len(held) > 1:
    return None
  if held:
    return held[0]["sheet_id"]
  base = BP.best(sources)
  if base is not None:
    return base["sheet_id"]
  own = [s for s in sources if not s["from_plans"]]
  return min(own or sources, key=lambda s: (s.get("purpose") == "FURNITURE", s.get("advice") not in (None, "READ"), s["page_no"]))["sheet_id"]

def build(sheets: list) -> dict:
  """sheets: [{"sheet_id", "page_no", "title", "stats", "candidates"}], only sheets that have been read. -> {"floors": [...], "to_decide": n}"""
  by_floor: dict = {}
  guesses = FOR.assign(sheets) if any(s.get("clues") for s in sheets) else {}
  placed: list = []
  for sheet in sheets:
    guess = guesses.get(sheet["sheet_id"])
    if guess:
      sheet = {**sheet, "title": {**(sheet["title"] or {}), "level_hint": guess["floor"]}, "_order": guess}
    placed.append(sheet)
    floors, from_plans = FO.floors_read(sheet["stats"], sheet["title"])
    for fl in floors:
      by_floor.setdefault(fl, []).append(_source(sheet, fl, from_plans))
  out = []
  
  for fl in sorted(by_floor, key=lambda k: (ORDER.index(k) if k in ORDER else len(ORDER), k)):
    sources = sorted(by_floor[fl], key=lambda s: (s["from_plans"], s["drawing_order"], s["page_no"]))
    taking = [s for s in sources if BP.eligible(s)]
    furniture = [s for s in taking if s.get("purpose") == "FURNITURE"]
    choosable = len(taking) >= 2 and (any(s["from_plans"] for s in taking) or 0 < len(furniture) < len(taking) or BP.across_drawings(taking))
    live = [s for s in taking if s["open"] + s["accepted"] > 0]
    base = BP.best(taking) if choosable else None
    for s in sources:
      s["base"] = base is not None and s["sheet_id"] == base["sheet_id"]
    if len(sources) == 1:
      state = "SINGLE"
    elif not choosable:
      state = "LISTED"
    elif len(live) > 1:
      state = "COMBINED" if any(s["combined"] for s in sources) else "DOUBLE"
    elif len(live) == 1:
      state = "CHOSEN"
    else:
      state = "NONE"
      
    out.append({"floor": fl, "state": state, "choosable": choosable,
      "chosen_sheet_id": live[0]["sheet_id"] if state == "CHOSEN" else None,
      "suggested_sheet_id": _suggest(taking) if choosable else None, "base_sheet_id": base["sheet_id"] if base else None,
      "base_reason": BP.reason(base, base) if base else None,
      "conflict": sum(1 for s in sources if s["accepted"] > 0) > 1, "sources": sources,
      "notes": [C.note("FLOOR_FROM_SHEET_ORDER", pages=[s["page_no"] for s in sources if s["floor_basis"] == "ORDER"])] if any(s["floor_basis"] == "ORDER" for s in sources) else []})
  pages = {s["sheet_id"]: s["page_no"] for s in sheets}
  ordered = [{"sheet_id": sid, "page_no": pages.get(sid), "floor": g["floor"], "reason": g["reason"], "floor_basis": "ORDER", "pages": g["pages"]} for sid, g in guesses.items()]
  copies = [{"floor": e["floor"], "kept_page": e["kept_page"], "aside_page": e["aside_page"], "default": PLAN, "marks": [{"mark": m, "plan": n[0], "key_plan": n[1]} for m, n in e["marks"].items()],
    "notes": [C.note("FLOOR_COPY_DEFAULT_USED", floor=e["floor"], pages=[e["kept_page"], e["aside_page"]])]} for e in floor_copies(placed).values()]
  return {"floors": out, "to_decide": sum(1 for f in out if f["state"] == "DOUBLE"), "ordered": sorted(ordered, key=lambda x: x["page_no"] or 0), "copies": copies}

def plan_choice(entry: dict, sheet_id) -> dict:
  """What choosing one source of a floor does: {"keep": the source, "set_aside": the others, "blocked": why not, if it cannot be done}."""
  keep = next((s for s in entry["sources"] if s["sheet_id"] == sheet_id), None)
  others = [s for s in entry["sources"] if s["sheet_id"] != sheet_id and BP.eligible(s)]
  if keep is None or not entry["choosable"] or not BP.eligible(keep):
    return {"keep": keep, "set_aside": [], "blocked": "FLOOR_CHOICE_NOT_OFFERED"}
  held = [s for s in others if s["accepted"] > 0]
  if held:
    return {"keep": keep, "set_aside": [], "blocked": "FLOOR_OTHER_SOURCE_ACCEPTED", "pages": [s["page_no"] for s in held]}
  return {"keep": keep, "set_aside": others, "blocked": None, "services_kept": [s["sheet_id"] for s in others if BP.keeps_services(s, keep, entry["sources"])]}

def set_aside_floors(rows: list, sheet_floor: str | None) -> dict:
  """The floors of a sheet that a choice set aside as a whole: every item of the floor is rejected with the mark. {floor: the mark}. A floor in which
  one item is open, accepted or rejected by hand is not set aside as a whole."""
  by: dict = {}
  for c in rows:
    fl = FO.level_of(c) or sheet_floor
    if c.category != "SLAB" and fl and not BP.is_electrical(c):
      by.setdefault(fl, []).append(c)
  return {fl: dict(cs[0].facts[SET_ASIDE]) for fl, cs in by.items() if all(c.decision == "REJECTED" and is_set_aside(c) and c.facts[SET_ASIDE].get("by") not in (ROLE_BY, STACK_BY) for c in cs)}

def opening_mark(c) -> str:
  f = c.facts or {}
  tag = c.tag if c.category in OPENINGS else (f.get("opening_tag") or f.get("door_tag") or f.get("mark")) if f.get("derived_from") in ("OPENINGS", "DOORS", "WINDOWS") else None
  return str(tag or "").strip().upper()

def copy_counts(kept: list, aside: list) -> dict:
  """Openings by mark on the copy of a floor that is kept and on the copy that was set aside: {mark: (kept_n, aside_n)}. An opening without a mark is not counted."""
  out: dict = {}
  for i, rows in enumerate((kept, aside)):
    for c in rows:
      mark = opening_mark(c) if c.category in OPENINGS else ""
      if mark:
        out.setdefault(mark, [0, 0])[i] += int(c.count or 1)
  return {m: (v[0], v[1]) for m, v in sorted(out.items())}

def floor_copies(sheets: list) -> dict:
  kept: dict = {}
  aside: dict = {}
  for sh in sheets:
    title = sh.get("title") or {}
    sheet_floor = None if title.get("composite") else title.get("level_hint")
    for c in sh["candidates"]:
      floor = FO.level_of(c) or sheet_floor
      if c.category not in OPENINGS or not floor:
        continue
      held = (c.facts or {}).get(SET_ASIDE) or {}
      if held.get("by") == SET_ASIDE_BY:
        aside.setdefault((floor, held.get("page_no"), sh["page_no"]), []).append(c)
      elif not is_set_aside(c) and c.decision != "REJECTED":
        kept.setdefault((floor, sh["page_no"]), []).append(c)
        
  out: dict = {}
  for (floor, kept_page, aside_page), rows in sorted(aside.items(), key=lambda kv: (str(kv[0][0]), kv[0][1] or 0, kv[0][2])):
    counts = copy_counts(kept.get((floor, kept_page), []), rows)
    differ = {m: n for m, n in counts.items() if n[0] != n[1]}
    if differ and floor not in out:
      out[floor] = {"floor": floor, "kept_page": kept_page, "aside_page": aside_page, "marks": differ, "counts": counts}
  return out

def _marked(sheets: list, entry: dict):
  marks = set(entry["marks"])
  for sh in sheets:
    title = sh.get("title") or {}
    sheet_floor = None if title.get("composite") else title.get("level_hint")
    for c in sh["candidates"]:
      if (FO.level_of(c) or sheet_floor) == entry["floor"] and opening_mark(c) in marks:
        yield c, sh["page_no"], ((c.facts or {}).get(SET_ASIDE) or {}).get("by") == SET_ASIDE_BY

def note_default(sheets: list, entry: dict) -> int:
  n = 0
  for c, page, aside in _marked(sheets, entry):
    if page == entry["kept_page"] and not aside and not is_set_aside(c):
      c.notes = [*(c.notes or []), C.note("FLOOR_COPY_DEFAULT_USED", floor=entry["floor"], pages=[entry["kept_page"], entry["aside_page"]])]
      n += 1
  return n

def swap_copy(sheets: list, entry: dict) -> int:
  moved = 0
  for c, page, aside in list(_marked(sheets, entry)):
    facts = dict(c.facts or {})
    if page == entry["aside_page"] and aside:
      facts.pop(SET_ASIDE)
      facts["copy_used"] = {"from_page": entry["aside_page"], "kept_page": entry["kept_page"]}
      c.facts, c.decision = facts, "NEW"
      moved += 1
      
    elif page == entry["kept_page"] and not is_set_aside(c) and c.decision != "REJECTED":
      facts[SET_ASIDE] = {"by": COPY_BY, "page_no": entry["aside_page"]}
      c.facts, c.decision = facts, "REJECTED"
      moved += 1
  return moved
