from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import config as C
from uuid import UUID
from app.modules.drawings_boq.takeoff.extract.pipeline import _status

CODES = ("BEAM_STRIPS_OVERLAP_WALL_BEAMS", "BEAM_STRIPS_DRAWN_ON_FLOOR")

def strips_by_level(sheets: list, exts: dict) -> dict:
  out: dict = {}
  
  for s in sorted(sheets, key=lambda x: x.page_no):
    st = (exts[s.id].stats or {}) if s.id in exts else {}
    reads = [v.get("beam_strips") for v in st.get("views") or [] if v.get("beam_strips")]
    if st.get("beam_strips"):
      reads.append(st["beam_strips"])
    for r in reads:
      level = r.get("level_hint")
      if not level or not r.get("length_m"):
        continue
      cur = out.get(level)
      if cur is None or r["length_m"] > cur["m"]:
        out[level] = {"m": float(r["length_m"]), "pages": [s.page_no], "marks": dict(r.get("by_tag") or {})}
  return out

def walls_by_level(rows: list, page_of: dict) -> dict:
  """{level: {"m": length of the roof beams worked out from the walls of that floor, "pages": [page]}}, from the beam rows. A floor read from two sheets takes the longer."""
  per: dict = {}
  for r in rows:
    f = r.facts or {}
    if r.category != "BEAM" or f.get("derived_from") != "WALLS" or f.get("beam_role") != "ROOF" or not f.get("level_hint"):
      continue
  
    key = (f["level_hint"], r.sheet_id)
    per[key] = per.get(key, 0.0) + float(f.get("length_m") or 0.0)
  out: dict = {}
  for (level, sheet_id), m in per.items():
    cur = out.get(level)
    if m > 0 and (cur is None or m > cur["m"]):
      out[level] = {"m": round(m, 3), "pages": [page_of.get(sheet_id)]}
  return out

def annotate(rows: list, strips: dict, walls: dict) -> set:
  """Puts the overlap notes on the beam rows of every floor that has both readings, and takes them off where one reading has gone. Returns the ids of the sheets
  whose rows changed. An accepted row is left as it is."""
  changed: set = set()
  for r in rows:
    f = r.facts or {}
    
    if r.category != "BEAM" or r.decision == "ACCEPTED":
      continue
    wall_beam = f.get("derived_from") == "WALLS" and f.get("beam_role") == "ROOF"
    if not wall_beam and not f.get("from_strips"):
      continue
    level = f.get("level_hint") or (f.get("view") or {}).get("level_hint")
    notes = [n for n in (r.notes or []) if n.get("code") not in CODES]
    if wall_beam and level in strips and level in walls:
      s = strips[level]
      notes.append(C.note("BEAM_STRIPS_DRAWN_ON_FLOOR", strips_m=s["m"], marks=sorted(s["marks"]), pages=s["pages"]))
    if f.get("from_strips") and level in walls and level in strips:
      w = walls[level]
      notes.append(C.note("BEAM_STRIPS_OVERLAP_WALL_BEAMS", wall_beams_m=w["m"], pages=w["pages"]))
    if notes != (r.notes or []):
      r.notes = notes
      r.status = _status(notes)
      changed.add(r.sheet_id)
  return changed

async def reconcile_beams(svc, org: UUID, drawing_id: UUID) -> set:
  """Brings the overlap notes of the beams of the drawing up to date. Returns the ids of the sheets whose items changed."""
  sheets = await svc.core.repo.sheets(org, drawing_id)
  exts = {e.sheet_id: e for e in await svc.repo.extractions(org, [s.id for s in sheets])}
  rows = await svc.repo.candidates(org, [s.id for s in sheets if s.id in exts])
  changed = annotate(rows, strips_by_level(sheets, exts), walls_by_level(rows, {s.id: s.page_no for s in sheets}))
  if changed:
    await svc.session.flush()
  return changed
