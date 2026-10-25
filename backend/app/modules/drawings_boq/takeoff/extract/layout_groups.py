from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS

BY = FS.LAYOUT_BY
MIN_ROOMS = 3
NEAR_TOTAL_PCT = 5.0
LAYOUT_KINDS = ("WALL", "ROOM", "DOOR", "WINDOW", "LINTEL", "STAIR")

def in_layout(c) -> bool:
  """An item that comes from the drawn plan of a floor: walls, rooms, openings, lintels, stairs and the beams worked out from the walls."""
  return c.category in LAYOUT_KINDS or (c.category == "BEAM" and (c.facts or {}).get("derived_from") == "WALLS")

def is_layout_set_aside(c) -> bool:
  return ((c.facts or {}).get(FS.SET_ASIDE) or {}).get("by") == BY

def _name(c) -> str:
  return re.sub(r"[^A-Z0-9]", "", str((c.facts or {}).get("name") or "").upper())

def _is_plan(sheet: dict) -> bool:
  stats = sheet.get("stats") or {}
  if "walls" not in stats or (stats.get("sheet_role") or {}).get("advice") == "SKIP":
    return False
  return not (sheet.get("title") or {}).get("composite")

def _rooms(sheet: dict) -> list:
  out = []
  for c in sheet["candidates"]:
    if c.category != "ROOM" or (c.decision == "REJECTED" and not FS.is_set_aside(c)):
      continue
    name, area = _name(c), (c.facts or {}).get("area_m2")
    if name and area:
      out.append((name, round(float(area), 1)))
  return sorted(out)

def _source(sheet: dict, rooms: list) -> dict:
  title = sheet.get("title") or {}

  rows = [c for c in sheet["candidates"] if in_layout(c)]
  walls = [c for c in rows if c.category == "WALL"]
  open_n = sum(1 for c in rows if c.decision == "NEW")
  accepted = sum(1 for c in rows if c.decision == "ACCEPTED")
  stats = sheet.get("stats") or {}
  role = stats.get("sheet_role") or {}
  return {"sheet_id": sheet["sheet_id"], "page_no": sheet["page_no"], "caption": title.get("title"), "floor": title.get("level_hint"), "advice": role.get("advice"), "role": role.get("role"),
    "rooms": len(rooms), "room_area_m2": round(sum(a for _n, a in rooms), 1), "wall_m": round(sum(float((c.facts or {}).get("length_cc_m") or 0.0) for c in walls), 1),
    "items": len(rows), "open": open_n, "accepted": accepted, "rejected": sum(1 for c in rows if c.decision == "REJECTED"),
    "set_aside": bool(rows) and open_n == 0 and accepted == 0 and any(is_layout_set_aside(c) for c in rows)}

def _suggest(sources: list) -> str | None:
  held = [s for s in sources if s["accepted"] > 0]
  if len(held) > 1:
    return None
  if held:
    return held[0]["sheet_id"]
  return min(sources, key=lambda s: (s["floor"] is None, s["advice"] not in (None, "READ"), -s["items"], s["page_no"]))["sheet_id"]

def _group(kind: str, sheets: list, rooms_of: dict) -> dict:
  sources = sorted((_source(s, rooms_of[s["sheet_id"]]) for s in sheets), key=lambda s: s["page_no"])
  live = [s for s in sources if s["open"] + s["accepted"] > 0]
  if kind == "NEAR":
    state = "NEAR"
  elif len(live) > 1:
    state = "DOUBLE"
  elif len(live) == 1:
    state = "CHOSEN"
  else:
    state = "NONE"
  floors = [s["floor"] for s in sources if s["floor"]]
  return {"key": f"L{sources[0]['page_no']}", "kind": kind, "state": state, "floor": floors[0] if floors else None, "rooms": sources[0]["rooms"], "room_area_m2": sources[0]["room_area_m2"],
    "chosen_sheet_id": live[0]["sheet_id"] if state == "CHOSEN" else None, "suggested_sheet_id": _suggest(sources) if kind == "SAME" else None,
    "conflict": kind == "SAME" and sum(1 for s in sources if s["accepted"] > 0) > 1, "choosable": kind == "SAME", "sources": sources,
    "counted_twice_m2": round(sum(s["room_area_m2"] for s in live[1:]), 1) if kind == "SAME" else 0.0}

def build(read: list) -> dict:
  plans = [s for s in read if "title" in s and "stats" in s and _is_plan(s)]
  rooms_of = {s["sheet_id"]: _rooms(s) for s in plans}
  by_sig: dict = {}

  for s in plans:
    r = rooms_of[s["sheet_id"]]
    if len(r) >= MIN_ROOMS:
      by_sig.setdefault(tuple(r), []).append(s)
  groups = [_group("SAME", g, rooms_of) for g in by_sig.values() if len(g) > 1]
  used = {s["sheet_id"] for g in by_sig.values() if len(g) > 1 for s in g}
  by_names: dict = {}
  for s in plans:
    r = rooms_of[s["sheet_id"]]
    if s["sheet_id"] not in used and len(r) >= MIN_ROOMS:
      by_names.setdefault(tuple(n for n, _a in r), []).append(s)

  for names, g in by_names.items():
    totals = [sum(a for _n, a in rooms_of[s["sheet_id"]]) for s in g]
    if len(g) > 1 and max(totals) > 0 and (max(totals) - min(totals)) / max(totals) * 100.0 <= NEAR_TOTAL_PCT:
      groups.append(_group("NEAR", g, rooms_of))
  groups.sort(key=lambda g: (g["kind"] != "SAME", g["sources"][0]["page_no"]))
  return {"groups": groups, "to_decide": sum(1 for g in groups if g["state"] == "DOUBLE"),
    "repeated_room_area_m2": round(sum(g["counted_twice_m2"] for g in groups if g["state"] == "DOUBLE"), 1)}

def undecided_sheets(read: list) -> set:
  out: set = set()
  for g in build(read)["groups"]:
    if g["state"] == "DOUBLE":
      out.update(s["sheet_id"] for s in g["sources"] if s["open"] + s["accepted"] > 0)
  return out
