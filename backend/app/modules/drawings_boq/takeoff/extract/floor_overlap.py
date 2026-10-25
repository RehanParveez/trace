from __future__ import annotations
from collections import Counter
from app.modules.drawings_boq.takeoff.extract import config as C

MM_PER_IN = 25.4

def floors_read(stats: dict | None, title: dict | None) -> tuple:
  """(floors, from_plans): the floors a sheet's walls were read for, and whether they came from the plans of a sheet that holds several."""
  stats = stats or {}
  if "walls" not in stats:
    return set(), False
  if (stats.get("sheet_role") or {}).get("advice") == "SKIP":
    return set(), False
  regions = stats.get("plan_regions") or {}
  if regions.get("count"):
    return {p["level_hint"] for p in regions.get("plans") or [] if p.get("level_hint")}, True
  t = title or {}
  if t.get("level_hint") and not t.get("composite"):
    return {t["level_hint"]}, False
  return set(), False

def elsewhere(sheets: list) -> dict:
  """sheets: [(page_no, stats, title)] of the other sheets that have been read. -> {floor: [{"page_no": n, "plans": bool}]}"""
  out: dict = {}
  for page_no, stats, title in sheets:
    floors, plans = floors_read(stats, title)
    for fl in floors:
      out.setdefault(fl, []).append({"page_no": page_no, "plans": plans})
  return out

def level_of(c) -> str | None:
  return ((c.facts or {}).get("view") or {}).get("level_hint")

def apply(found: list, notes: list, stats: dict | None, title: dict | None, other: dict, status) -> list:
  """Adds the warning to the items of each floor of this sheet that is also read elsewhere; returns [{"floor", "pages"}]. Only a pair that has a
  sheet of several plans in it is flagged (two ordinary sheets of one floor are another matter), and only for a sheet whose walls were read (a
  framing plan shows the same floor but is not the same reading)."""
  floors, from_plans = floors_read(stats, title)
  if not floors:
    return []
  sheet_floor = None if (title or {}).get("composite") else (title or {}).get("level_hint")
  hit: dict = {}
  for fl, rows in other.items():
    if from_plans or any(r["plans"] for r in rows):
      hit[fl] = sorted({r["page_no"] for r in rows})
  out = []
  for fl in sorted(floors & set(hit)):
    out.append({"floor": fl, "pages": hit[fl]})
    note = C.note("FLOOR_READ_ON_OTHER_SHEET", floor=fl, pages=hit[fl])
    notes.append(note)
    for c in found:
      if (level_of(c) or sheet_floor) == fl and c.category != "SLAB":
        c.notes.append(note)
        c.status = status(c.notes)
  return out