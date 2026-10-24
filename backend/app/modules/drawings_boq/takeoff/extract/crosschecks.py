from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.extract import floor_overlap as FO
from app.modules.drawings_boq.takeoff.extract import config as C

PASS, WARN, INFO = "PASS", "WARN", "INFO"
OUTDOOR = re.compile(r"PORCH|LAWN|GARDEN|PARKING|DRIVE|COURT|TERRACE|BALCON|SIT[\s-]?OUT|YARD|SETBACK", re.I)

def _live(c) -> bool:
  return c.decision != "REJECTED" and not FS.is_set_aside(c)

def _sheet_floor(sheet: dict) -> str | None:
  if ((sheet.get("stats") or {}).get("sheet_role") or {}).get("advice") == "SKIP":
    return None
  t = sheet.get("title") or {}
  return None if t.get("composite") else t.get("level_hint")

def _floor(c, sheet_floor: str | None) -> str | None:
  f = c.facts or {}
  return FO.level_of(c) or f.get("level_hint") or sheet_floor

def _rank(floor: str) -> int:
  return FS.ORDER.index(floor) if floor in FS.ORDER else len(FS.ORDER)

def _check(code: str, status: str, floor: str | None, message: str, pages: list | None = None, **numbers) -> dict:
  return {"code": code, "status": status, "floor": floor, "message": message, "pages": sorted(set(pages or [])), "numbers": numbers}

def _slabs(read: list) -> dict:
  out: dict = {}
  for sh in read:
    for c in sh["candidates"]:
      f = c.facts or {}
      if c.category == "SLAB" and _live(c) and f.get("floor") and f.get("area_m2"):
        if f["floor"] not in out or float(f["area_m2"]) > float(out[f["floor"]]["area_m2"]):
          out[f["floor"]] = {"area_m2": float(f["area_m2"]), "page_no": sh["page_no"]}
  return out

def rooms_and_slab(read: list) -> list:
  slabs = _slabs(read)
  out: list = []
  seen_floors: set = set()
  for sh in read:
    floors, _ = FO.floors_read(sh["stats"], sh["title"])
    sf = _sheet_floor(sh)
    for fl in sorted(floors, key=lambda k: (_rank(k), k)):
      rooms = [c for c in sh["candidates"] if c.category == "ROOM" and _live(c) and (FO.level_of(c) or sf) == fl]
      indoor = [c for c in rooms if not OUTDOOR.search(str((c.facts or {}).get("name") or ""))]
      if not indoor:
        continue
    
      seen_floors.add(fl)
      total = round(sum(float((c.facts or {}).get("area_m2") or 0.0) for c in indoor), 2)
      slab = slabs.get(fl)
      if slab is None:
        out.append(_check("FLOOR_HAS_NO_SLAB", INFO, fl, f"The {fl.title()} floor has {len(indoor)} rooms ({total:g} m²) but no slab was read for it. Read its framing plan.", [sh["page_no"]], rooms_m2=total))
        continue
    
      ratio = round(total / slab["area_m2"], 3)
      pages = [sh["page_no"], slab["page_no"]]
      head = f"The {len(indoor)} rooms of the {fl.title()} floor (page {sh['page_no']}) add up to {total:g} m², {ratio * 100:.0f}% of the {slab['area_m2']:g} m² the slab covers"
      if ratio > C.CHECK_ROOMS_MAX_RATIO:
        out.append(_check("ROOMS_EXCEED_SLAB", WARN, fl, head + ". Rooms cannot add up to more than the slab: a room is counted twice, an outline is wrong, or the scale is.", pages, rooms_m2=total, slab_m2=slab["area_m2"], ratio=ratio))
      elif ratio < C.CHECK_ROOMS_MIN_RATIO:
        out.append(_check("ROOMS_MISSING", WARN, fl, head + ". Rooms that are drawn were probably not read.", pages, rooms_m2=total, slab_m2=slab["area_m2"], ratio=ratio))
      else:
        out.append(_check("ROOMS_FIT_SLAB", PASS, fl, head + ", which is what walls and a stair leave.", pages, rooms_m2=total, slab_m2=slab["area_m2"], ratio=ratio))
  for fl in sorted(set(slabs) - seen_floors, key=lambda k: (_rank(k), k)):
    out.append(_check("SLAB_HAS_NO_ROOMS", INFO, fl, f"A slab was read for the {fl.title()} floor ({slabs[fl]['area_m2']:g} m²) but no room was read on its plan.", [slabs[fl]["page_no"]], slab_m2=slabs[fl]["area_m2"]))
  return out

def _counts(read: list, category: str) -> dict:
  """{tag: {floor: count}} of the live items of a category that have a mark. A floor read from two sheets takes the larger count, not the sum. Neck columns, which are
  worked out from the footings, are left out."""
  out: dict = {}
  
  for sh in read:
    sf = _sheet_floor(sh)
    for c in sh["candidates"]:
      f = c.facts or {}
      if c.category != category or not _live(c) or not c.tag or f.get("neck_of"):
        continue
      fl = _floor(c, sf)
      if not fl:
        continue
      slot = out.setdefault(c.tag, {})
      slot[fl] = max(slot.get(fl, 0), int(c.count or 1))
  return out

def columns_up(read: list) -> list:
  cols = _counts(read, "COLUMN")
  out: list = []
  
  bad = 0
  pairs = 0
  for tag in sorted(cols):
    floors = sorted(cols[tag], key=lambda k: (_rank(k), k))
    for lower, upper in zip(floors, floors[1:]):
      pairs += 1
      if cols[tag][upper] > cols[tag][lower]:
        bad += 1
        out.append(_check("COLUMNS_MORE_THAN_BELOW", WARN, upper, f"{cols[tag][upper]} columns {tag} on the {upper.title()} floor but {cols[tag][lower]} on the {lower.title()} floor under it. A column stands on a column: one count is wrong.", None, tag=tag, above=cols[tag][upper], below=cols[tag][lower]))
  if pairs and not bad:
    out.append(_check("COLUMNS_STACK", PASS, None, f"Every column mark has no more columns on a floor than on the floor under it ({pairs} floor pairs checked).", None, pairs=pairs))
  return out

def columns_and_footings(read: list) -> list:
  foot = _counts(read, "FOOTING")
  cols = _counts(read, "COLUMN")
  if not foot or not cols:
    return []

  lowest = min({fl for v in foot.values() for fl in v}, key=lambda k: (_rank(k), k))
  col_here = {t: v[lowest] for t, v in cols.items() if lowest in v}
  if not col_here:
    return []
  nf, nc = sum(v[lowest] for v in foot.values() if lowest in v), sum(col_here.values())
  detail = f"{nc} columns ({', '.join(f'{t} {n}' for t, n in sorted(col_here.items()))}) and {nf} footings ({', '.join(f'{t} {v[lowest]}' for t, v in sorted(foot.items()) if lowest in v)}) on the {lowest.title()} floor"
  if nc != nf:
    return [_check("COLUMNS_FOOTINGS_DIFFER", WARN, lowest, f"{detail}. Each column stands on a footing, so the counts should be equal: a column or a footing is missing or counted twice.", None, columns=nc, footings=nf)]
  return [_check("COLUMNS_ON_FOOTINGS", PASS, lowest, f"{detail}: as many footings as columns.", None, columns=nc, footings=nf)]

def schedule_marks(read: list) -> list:
  listed: dict = {}
  for sh in read:
    for o in (sh.get("schedule") or {}).get("openings") or []:
      listed.setdefault(o["mark"], []).append(sh["page_no"])
  if not listed:
    return []

  found = {c.tag for sh in read for c in sh["candidates"] if c.category in ("DOOR", "WINDOW") and _live(c) and c.tag}
  missing = sorted(m for m in listed if m not in found)
  if missing:
    return [_check("SCHEDULE_MARKS_NOT_FOUND", WARN, None, f"The schedule lists {', '.join(missing)} but no plan shows {'it' if len(missing) == 1 else 'them'}: not drawn, not read, or a different mark on the plan.", [p for m in missing for p in listed[m]], marks=missing, listed=len(listed))]
  return [_check("SCHEDULE_MARKS_FOUND", PASS, None, f"All {len(listed)} marks of the opening schedule are found on a plan.", [p for v in listed.values() for p in v], listed=len(listed))]

def run(read: list) -> dict:
  """read: [{"sheet_id", "page_no", "title", "stats", "candidates", "schedule"}] of the sheets that have been read. -> {"checks": [...], "warnings", "info", "passed"}"""
  from app.modules.drawings_boq.takeoff.extract import shape_checks as SC
  checks = [*rooms_and_slab(read), *columns_up(read), *columns_and_footings(read), *schedule_marks(read), *SC.run(read)]
  order = {WARN: 0, INFO: 1, PASS: 2}
  checks.sort(key=lambda c: (order[c["status"]], _rank(c["floor"]) if c["floor"] else 99, c["code"]))
  return {"checks": checks, "warnings": sum(1 for c in checks if c["status"] == WARN), "info": sum(1 for c in checks if c["status"] == INFO),
    "passed": sum(1 for c in checks if c["status"] == PASS)}
