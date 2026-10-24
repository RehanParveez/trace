from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import combine_plan as CP
from app.modules.drawings_boq.takeoff.extract import floor_overlap as FO

SET_ASIDE = "set_aside"         
SET_ASIDE_BY = "FLOOR_CHOICE"

ORDER = ["FOUNDATION", "BASEMENT", "GROUND", "MEZZANINE", "FIRST", "SECOND", "THIRD", "FOURTH", "TYPICAL", "ROOF"]

def in_floor(c, floor: str, sheet_floor: str | None) -> bool:
  """An item that belongs to this floor of its sheet (a slab is read from the framing sheets, not from the plans, and is left out)."""
  return c.category != "SLAB" and (FO.level_of(c) or sheet_floor) == floor

def is_set_aside(c) -> bool:
  """Rejected because the floor's other sheet was chosen, or because the other sheet holds the same item (a combine)."""
  return ((c.facts or {}).get(SET_ASIDE) or {}).get("by") in (SET_ASIDE_BY, CP.BY)

def _source(sheet: dict, floor: str, from_plans: bool) -> dict:
  title = sheet["title"] or {}
  sheet_floor = None if title.get("composite") else title.get("level_hint")
  rows = [c for c in sheet["candidates"] if in_floor(c, floor, sheet_floor)]
  walls = [c for c in rows if c.category == "WALL"]
  plan = next((p for p in ((sheet["stats"] or {}).get("plan_regions") or {}).get("plans") or [] if p.get("level_hint") == floor), None)
  open_n = sum(1 for c in rows if c.decision == "NEW")
  accepted = sum(1 for c in rows if c.decision == "ACCEPTED")
  
  return {"sheet_id": sheet["sheet_id"], "page_no": sheet["page_no"], "from_plans": from_plans, "advice": ((sheet["stats"] or {}).get("sheet_role") or {}).get("advice"), "purpose": ((sheet["stats"] or {}).get("sheet_role") or {}).get("purpose"),
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
  own = [s for s in sources if not s["from_plans"]]
  return min(own or sources, key=lambda s: (s.get("purpose") == "FURNITURE", s.get("advice") not in (None, "READ"), s["page_no"]))["sheet_id"]

def build(sheets: list) -> dict:
  """sheets: [{"sheet_id", "page_no", "title", "stats", "candidates"}], only sheets that have been read. -> {"floors": [...], "to_decide": n}"""
  by_floor: dict = {}
  for sheet in sheets:
    floors, from_plans = FO.floors_read(sheet["stats"], sheet["title"])
    for fl in floors:
      by_floor.setdefault(fl, []).append(_source(sheet, fl, from_plans))
  out = []
  
  for fl in sorted(by_floor, key=lambda k: (ORDER.index(k) if k in ORDER else len(ORDER), k)):
    sources = sorted(by_floor[fl], key=lambda s: (s["from_plans"], s["page_no"]))
    furniture = [s for s in sources if s.get("purpose") == "FURNITURE"]
    choosable = len(sources) >= 2 and (any(s["from_plans"] for s in sources) or 0 < len(furniture) < len(sources))
    live = [s for s in sources if s["open"] + s["accepted"] > 0]
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
      "suggested_sheet_id": _suggest(sources) if choosable else None,
      "conflict": sum(1 for s in sources if s["accepted"] > 0) > 1, "sources": sources})
  return {"floors": out, "to_decide": sum(1 for f in out if f["state"] == "DOUBLE")}

def plan_choice(entry: dict, sheet_id) -> dict:
  """What choosing one source of a floor does: {"keep": the source, "set_aside": the others, "blocked": why not, if it cannot be done}."""
  keep = next((s for s in entry["sources"] if s["sheet_id"] == sheet_id), None)
  others = [s for s in entry["sources"] if s["sheet_id"] != sheet_id]
  if keep is None or not entry["choosable"]:
    return {"keep": keep, "set_aside": [], "blocked": "FLOOR_CHOICE_NOT_OFFERED"}
  held = [s for s in others if s["accepted"] > 0]
  if held:
    return {"keep": keep, "set_aside": [], "blocked": "FLOOR_OTHER_SOURCE_ACCEPTED", "pages": [s["page_no"] for s in held]}
  return {"keep": keep, "set_aside": others, "blocked": None}

def set_aside_floors(rows: list, sheet_floor: str | None) -> dict:
  """The floors of a sheet that a choice set aside as a whole: every item of the floor is rejected with the mark. {floor: the mark}. A floor in which
  one item is open, accepted or rejected by hand is not set aside as a whole."""
  by: dict = {}
  for c in rows:
    fl = FO.level_of(c) or sheet_floor
    if c.category != "SLAB" and fl:
      by.setdefault(fl, []).append(c)
  return {fl: dict(cs[0].facts[SET_ASIDE]) for fl, cs in by.items() if all(c.decision == "REJECTED" and is_set_aside(c) for c in cs)}
