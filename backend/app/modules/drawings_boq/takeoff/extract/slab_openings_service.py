from __future__ import annotations
from uuid import UUID
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import slab_openings as SO
from app.modules.drawings_boq.takeoff.extract.pipeline import _status

"""The holes in the slabs of a drawing are read from the floor plans, and the slabs from the framing plans: different sheets, read one at a time. After a
sheet is read this sets each slab against the stair wells, shafts and ducts of its floor, so the slab measures what is there. An accepted slab is left as it is."""

CODES = ("SLAB_OPENINGS_DEDUCTED", "SLAB_OPENINGS_SMALL")
KEYS = ("openings", "openings_area_m2", "openings_twin_area_m2")

def annotate(rows: list, placed: dict) -> set:
  """Sets the openings (and their notes) on every open slab of the drawing, and takes them off a slab that has none now. Returns the ids of the sheets whose rows changed."""
  changed: set = set()
  for r in rows:
    if r.category != "SLAB" or r.decision == "ACCEPTED":
      continue
    f = dict(r.facts or {})
    info = placed.get(f.get("floor"))
    items = SO.entries_for_facts(info["items"]) if info else []
    for k in KEYS:
      f.pop(k, None)
    notes = [n for n in (r.notes or []) if n.get("code") not in CODES]
    if items:
      f["openings"] = items
      f["openings_area_m2"] = SO.deducted_area(items)
      if info.get("twin_area_m2"):
        f["openings_twin_area_m2"] = round(float(info["twin_area_m2"]), 3)
      big = [i for i in items if i["deduct"]]
      
      if big:
        n = C.note("SLAB_OPENINGS_DEDUCTED", count=len(big), area_m2=f["openings_area_m2"], names=[i["name"] for i in big])
        n["message"] = ("Taken off this slab: " + "; ".join(f"{i['name']} {i['area_m2']:.2f} m² ({i['text']}; plan of sheet {i['page_no']})" for i in big)
          + f"; {f['openings_area_m2']:.2f} m² in all. A stair well is the area of the flight as drawn on the plan of the floor above or below; a shaft or duct is taken off only where the plan prints a size.")
        notes.append(n)
      if len(big) < len(items):
        small = [i for i in items if not i["deduct"]]
        n = C.note("SLAB_OPENINGS_SMALL", count=len(small))
        n["message"] = ("Not deducted, 0.1 m² or smaller (IS 1200 Part 2 cl. 4.1.6): " + "; ".join(f"{i['name']} {i['area_m2']:.2f} m² ({i['text']})" for i in small) + ".")
        
        notes.append(n)
    if f != (r.facts or {}) or notes != (r.notes or []):
      r.facts, r.notes = f, notes
      r.status = _status(notes)
      changed.add(r.sheet_id)
  return changed

async def reconcile_slab_openings(svc, org: UUID, drawing_id: UUID) -> set:
  """Brings the openings of the slabs of the drawing up to date. Returns the ids of the sheets whose items changed."""
  sheets = await svc.core.repo.sheets(org, drawing_id)
  exts = {e.sheet_id: e for e in await svc.repo.extractions(org, [s.id for s in sheets])}
  rows = await svc.repo.candidates(org, [s.id for s in sheets if s.id in exts])
  levels = SO.by_level(sheets, exts)
  known = {(r.facts or {}).get("floor") for r in rows if r.category == "SLAB"} | set(levels)
  changed = annotate(rows, SO.place(levels, {k for k in known if k}))
  if changed:
    await svc.session.flush()
  return changed
