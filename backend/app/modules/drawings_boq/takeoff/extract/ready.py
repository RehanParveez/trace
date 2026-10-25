from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import crosschecks as CK
from app.modules.drawings_boq.takeoff.extract import floor_overlap as FO
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.extract import accept_guard as AG
from app.modules.drawings_boq.takeoff.extract import layout_groups as LG
from app.modules.drawings_boq.takeoff.extract import mark_entities as ME
from app.modules.drawings_boq.takeoff.extract.crosschecks import _sheet_floor, _floor, _live
from app.modules.drawings_boq.takeoff.evidence import evidence_for

HELD_BY = {
  "COLUMNS_FOOTINGS_DIFFER": ("COLUMN", "FOOTING"), "COLUMNS_MORE_THAN_BELOW": ("COLUMN", "FOOTING"),
  "FLOOR_HAS_NO_SLAB": ("SLAB", "ROOM"), "SLAB_HAS_NO_ROOMS": ("SLAB", "ROOM"), "ROOMS_EXCEED_SLAB": ("SLAB", "ROOM"), "ROOMS_MISSING": ("SLAB", "ROOM"),
  "SCHEDULE_MARKS_NOT_FOUND": ("DOOR", "WINDOW"),
  "FLOOR_HAS_NO_WALLS": ("WALL",), "OPENINGS_IN_NO_WALL": ("DOOR", "WINDOW", "WALL"), "OPENINGS_WIDER_THAN_WALL": ("DOOR", "WINDOW", "WALL"),
  "PARAPET_DIFFERS_FROM_RING": ("SITE",), "BALCONY_OUTSIDE_SLAB": ("SITE", "sSLAB"),
  "WALLS_OPEN_ROUND_ROOMS": ("WALL", "ROOM"), "WALL_LONGER_THAN_ROOMS": ("WALL", "ROOM"), "WALL_SHORT_FOR_ROOMS": ("WALL", "ROOM"),
}

NOT_A_PLAN_KINDS = ("WALL", "ROOM", "DOOR", "WINDOW", "LINTEL", "STAIR")

def from_non_plan(sh: dict, c) -> bool:
  """True for a wall, room, opening, lintel, stair or wall-derived beam read from a sheet whose role says it is not a plan (section, elevation, detail, schedule, specification)."""
  if ((sh.get("stats") or {}).get("sheet_role") or {}).get("advice") != "SKIP":
    return False
  return c.category in NOT_A_PLAN_KINDS or (c.category == "BEAM" and (c.facts or {}).get("derived_from") == "WALLS")

REASON_TEXT = {
  "NOT_A_PLAN_SHEET": "This sheet is a section, elevation, detail, schedule or specification, not a floor plan; what was read from it is drawn detail or repeats the plans. Accept it by hand only if the sheet really holds a plan.",
  "ALREADY_DECIDED": "Already accepted or rejected.",
  "ERROR": "The reader found an error on it.",
  "WARNING": "The reader raised a warning on it.",
  "NOT_MEASURABLE": "A beam mark is only counted; its lengths are drawn by hand.",
  "VALUE_MISSING": "A value is missing; type it when accepting this item.",
  "ASSUMED": "A value was paired, defaulted or is disputed on the drawing.",
  "CHECK_WARNS": "A check between the readers is warning about this kind of item on this floor.",
  "ADDED_FROM_SECOND_SHEET": "Only the sheet that shows every plan has this item, not the floor's own sheet. That sheet is drawn small, so check it on the sheet before accepting.",
  "FLOOR_SOURCE_UNDECIDED": "This floor is open on two sheets. Choose the sheet to use for it before accepting, or the floor is counted twice.",
  "LAYOUT_SOURCE_UNDECIDED": "This plan is printed on several sheets (the same named rooms with the same areas) and was read from each. Choose the sheet that governs it before accepting, or the plan is counted once for every sheet it is printed on.",
  "MARK_ACCEPTED_ELSEWHERE": "The same mark of this floor is already accepted from another sheet, or the floor finish already accepted for this floor carries the baths and toilets. Accepting it here as well counts it twice.",
  "MARK_ON_SEVERAL_SHEETS": "The same mark of this floor is shown on another sheet with the same count and size, and that sheet is the one to use (a schedule before a detail before a plan label, then a sheet that names its floor). Choose the sheet in the list of marks, or accept this one by hand.",
  "MARK_SHEETS_DISAGREE": "The same mark of this floor is shown on more than one sheet with a different count or size. Choose the sheet that governs it in the list of marks before accepting, or the mark is counted from every sheet.",
}

def mark_skip(layout_open: set):
  """What the mark entities leave out because another rule already holds it: an item of a sheet that is not a plan, an item of a plan printed on several sheets."""
  def skip(sh: dict, c) -> bool:
    return from_non_plan(sh, c) or (sh["sheet_id"] in layout_open and LG.in_layout(c))
  return skip

def _warned(checks: list) -> list:
  return [(c["floor"], HELD_BY.get(c["code"]), c["code"]) for c in checks if c["status"] == CK.WARN]

def undecided_sources(read: list) -> set:
  """(sheet id, floor) of every source of a floor that is open on two sheets and not yet chosen. Accepting from both would count the floor twice."""
  out: set = set()
  for f in FS.build([s for s in read if "title" in s and "stats" in s])["floors"]:
    if f["state"] == "DOUBLE":
      out.update((s["sheet_id"], f["floor"]) for s in f["sources"] if s["open"] + s["accepted"] > 0)
  return out

def ready(read: list, checks: list | None = None) -> dict:
  checks = checks if checks is not None else CK.run(read)["checks"]
  warned = _warned(checks)
  undecided = undecided_sources(read)
  layout_open = LG.undecided_sheets(read)
  ok: list = []
  guard = AG.Guard(AG.held_marks(read, lambda c, sh: _floor(c, _sheet_floor(sh))))
  skip_mark = mark_skip(layout_open)
  marks = ME.lookup(ME.build([s for s in read if "title" in s and "stats" in s], skip_mark))
  held: list = []
  
  for sh in read:
    sf = _sheet_floor(sh)
    for c in sh["candidates"]:
      if not _live(c):
        continue
    
      fl = _floor(c, sf)
      item = {"id": str(c.id), "category": c.category, "tag": c.tag, "floor": fl, "page_no": sh["page_no"], "grade": None, "reasons": []}
      why = item["reasons"]
      if c.decision != "NEW":
         why.append("ALREADY_DECIDED")
      elif c.category != "SLAB" and (sh["sheet_id"], FO.level_of(c) or sf) in undecided:
        why.append("FLOOR_SOURCE_UNDECIDED")
      elif sh["sheet_id"] in layout_open and LG.in_layout(c):
        why.append("LAYOUT_SOURCE_UNDECIDED")
      if c.decision == "NEW" and from_non_plan(sh, c):
        why.append("NOT_A_PLAN_SHEET")
      if c.decision == "NEW" and guard.clash(c, fl) is not None:
        why.append("MARK_ACCEPTED_ELSEWHERE")
      elif c.decision == "NEW" and not skip_mark(sh, c) and (code := ME.held_code(marks, c, fl)):
        why.append(code)
      if c.decision == "NEW" and ((c.facts or {}).get("floor_union") or {}).get("role") == "ADDED":
        why.append("ADDED_FROM_SECOND_SHEET")
      if c.status == "INVALID":
        why.append("ERROR")
      elif c.status == "WARNING":
        why.append("WARNING")
      f = c.facts or {}
      
      if c.category == "BEAM" and f.get("derived_from") != "WALLS" and not f.get("from_strips"):
        why.append("NOT_MEASURABLE")
      if c.missing:
        why.append("VALUE_MISSING")
      ev = evidence_for(c)
      item["grade"] = ev["grade"]
      if ev["grade"] in ("ASSUMED", "MISSING") and "VALUE_MISSING" not in why:
        why.append("ASSUMED" if ev["grade"] == "ASSUMED" else "VALUE_MISSING")
      if any((wf is None or wf == fl) and (kinds is None or c.category in kinds) for wf, kinds, _ in warned):
        why.append("CHECK_WARNS")
      (held if why else ok).append(item)
      
  by: dict = {}
  for h in held:
    for r in h["reasons"]:
      by[r] = by.get(r, 0) + 1
  for h in held:
    h["reasons"] = [{"code": r, "message": REASON_TEXT[r]} for r in h["reasons"]]
  for o in ok:
    o.pop("reasons")
  return {"ready": ok, "held": held, "held_by_reason": by, "checks_warning": len(warned)}
