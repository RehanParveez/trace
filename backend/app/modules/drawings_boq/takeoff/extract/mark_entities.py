from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.extract.crosschecks import _floor, _sheet_floor
from app.modules.drawings_boq.takeoff.extract import accept_guard as AG

BY = FS.MARK_BY
DOUBLE, DIFFER, UNPLACED, CHOSEN, SINGLE = "DOUBLE", "DIFFER", "UNPLACED", "CHOSEN", "SINGLE"
INCH_MM = 25.4
SCHEDULE_CODES = ("SIZE_FROM_SCHEDULE",)
DETAIL_CODES = ("SIZE_FROM_DETAIL", "SIZE_FROM_COLUMN_DETAIL")
BASIS = ("SCHEDULE", "DETAIL", "PLAN")

def is_mine(c) -> bool:
  return c.decision == "REJECTED" and ((c.facts or {}).get(FS.SET_ASIDE) or {}).get("by") == BY

def floor_of_item(c, sheet_floor) -> str | None:
  return "SITE" if c.category == "SITE" else _floor(c, sheet_floor)

def _shape(c) -> tuple:
  p = c.params or {}
  return tuple(round(float(p[k]) / INCH_MM) for k in ("length_mm", "width_mm", "depth_mm") if p.get(k))

def _basis(rows: list) -> int:
  codes = {n.get("code") for c in rows for n in (c.notes or []) if isinstance(n, dict)}
  return 0 if codes & set(SCHEDULE_CODES) else 1 if codes & set(DETAIL_CODES) else 2

def _source(sh: dict, sf, live: list, aside: list) -> dict:
  stats = sh.get("stats") or {}
  title = sh.get("title") or {}
  shapes = sorted({s for s in (_shape(c) for c in live) if s})
  return {"sheet_id": sh["sheet_id"], "page_no": sh["page_no"], "caption": title.get("title"), "floor": sf, "advice": (stats.get("sheet_role") or {}).get("advice"),
    "count": sum(int(c.count or 1) for c in live), "shapes": [list(s) for s in shapes], "basis": BASIS[_basis(live)] if live else None,
    "open": sum(1 for c in live if c.decision == "NEW"), "accepted": sum(1 for c in live if c.decision == "ACCEPTED"), "set_aside": len(aside)}

def _agree(sources: list) -> bool:
  if len({s["count"] for s in sources}) > 1:
    return False
  sized = [tuple(map(tuple, s["shapes"])) for s in sources if s["shapes"]]
  return len(set(sized)) <= 1

def _rank(s: dict) -> tuple:
  return (s["accepted"] == 0, BASIS.index(s["basis"]) if s["basis"] in BASIS else 2, s["floor"] is None, s["advice"] not in (None, "READ"), s["page_no"])

def _entity(cat: str, norm: str, floor, tag, rows_by_sheet: dict) -> dict | None:
  sources = [_source(r["sh"], r["sf"], r["live"], r["aside"]) for r in rows_by_sheet.values()]
  sources.sort(key=lambda s: s["page_no"])
  live = [s for s in sources if s["open"] + s["accepted"] > 0]
  aside = [s for s in sources if s["set_aside"] > 0]
  if len(live) >= 2:
    agree = _agree(live)

    state = UNPLACED if floor is None else DOUBLE if agree else DIFFER
  elif len(live) == 1 and aside:
    agree, state = True, CHOSEN
  elif len(live) == 1:
    agree, state = True, SINGLE
  else:
    return None
  best = min(live, key=_rank)
  return {"key": f"{cat}:{norm}:{floor or '-'}", "category": cat, "mark": norm, "tag": tag, "floor": floor if floor != "SITE" else None, "state": state, "agree": agree,
    "live_sheets": len(live), "suggested_sheet_id": best["sheet_id"] if state in (DOUBLE, UNPLACED, DIFFER) else None,
    "chosen_sheet_id": live[0]["sheet_id"] if state == CHOSEN else None,
    "conflict": sum(1 for s in live if s["accepted"] > 0) > 1, "choosable": state != SINGLE, "sources": [s for s in sources if s["open"] + s["accepted"] + s["set_aside"] > 0]}

def build(read: list, skip=None) -> dict:
  groups: dict = {}
  tags: dict = {}

  for sh in read:
    if "title" not in sh or "stats" not in sh:
      continue
    sf = _sheet_floor(sh)
    for c in sh["candidates"]:
      mk = AG.mark_key(c.category, c.tag, c.facts)
      if mk is None or (skip is not None and skip(sh, c)):
        continue
      if c.decision == "REJECTED" and not is_mine(c):
        continue
      k = (mk[0], mk[1], floor_of_item(c, sf))
      tags.setdefault(k, c.tag)
      slot = groups.setdefault(k, {}).setdefault(sh["sheet_id"], {"sh": sh, "sf": sf, "live": [], "aside": []})
      slot["aside" if c.decision == "REJECTED" else "live"].append(c)

  found = [e for k, g in groups.items() for e in [_entity(k[0], k[1], k[2], tags[k], g)] if e is not None]
  listed = [e for e in found if e["state"] != SINGLE]
  order = {DIFFER: 0, DOUBLE: 1, UNPLACED: 2, CHOSEN: 3}
  listed.sort(key=lambda e: (order[e["state"]], e["category"], e["floor"] or "", e["mark"]))
  return {"entities": listed, "single": len(found) - len(listed), "to_decide": sum(1 for e in listed if e["state"] in (DOUBLE, DIFFER)),
    "unplaced": sum(1 for e in listed if e["state"] == UNPLACED), "differ": sum(1 for e in listed if e["state"] == DIFFER)}

def lookup(view: dict) -> dict:
  return {(e["category"], e["mark"], e["floor"] if e["category"] != "SITE" else "SITE"): e for e in view["entities"]}

def held_code(view_lookup: dict, c, floor) -> str | None:
  mk = AG.mark_key(c.category, c.tag, c.facts)
  if mk is None or c.decision != "NEW":
    return None

  e = view_lookup.get((mk[0], mk[1], "SITE" if c.category == "SITE" else floor))
  if e is None:
    return None
  if e["state"] == DIFFER:
    return "MARK_SHEETS_DISAGREE"
  if e["state"] == DOUBLE and e["suggested_sheet_id"] is not None:
    return "MARK_ON_SEVERAL_SHEETS" if getattr(c, "sheet_id", None) != e["suggested_sheet_id"] else None
  return None

def plan_choice(entity: dict, sheet_id) -> dict:
  keep = next((s for s in entity["sources"] if s["sheet_id"] == sheet_id), None)
  others = [s for s in entity["sources"] if s["sheet_id"] != sheet_id]
  if keep is None or not entity["choosable"]:
    return {"keep": keep, "set_aside": [], "blocked": "MARK_CHOICE_NOT_OFFERED"}
  held = [s for s in others if s["accepted"] > 0]

  if held:
    return {"keep": keep, "set_aside": [], "blocked": "MARK_OTHER_SHEET_ACCEPTED", "pages": [s["page_no"] for s in held]}
  return {"keep": keep, "set_aside": [s for s in others if s["open"] > 0], "blocked": None}
