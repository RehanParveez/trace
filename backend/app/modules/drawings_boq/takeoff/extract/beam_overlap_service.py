from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import config as C
from uuid import UUID
from app.modules.drawings_boq.takeoff.extract.pipeline import _status
import re
from app.modules.drawings_boq.takeoff.prep.details import norm_mark

CODES = ("BEAM_STRIPS_OVERLAP_WALL_BEAMS", "BEAM_STRIPS_DRAWN_ON_FLOOR", "BEAM_FROM_FRAMING_PLAN")

NOT_ROOF_MARKS = ("GB", "PB", "TB")

def roof_mark(tag) -> bool:
  return re.sub(r"[^A-Z]", "", norm_mark(str(tag or ""))) not in NOT_ROOF_MARKS

def strips_by_level(sheets: list, exts: dict) -> dict:
  out: dict = {}
  for s in sorted(sheets, key=lambda x: x.page_no):
    st = (exts[s.id].stats or {}) if s.id in exts else {}
    reads = [v.get("beam_strips") for v in st.get("views") or [] if v.get("beam_strips")]
    
    if st.get("beam_strips"):
      reads.append(st["beam_strips"])
    for r in reads:
      level = r.get("level_hint")
      if not level:
        continue
      marks = {str(t): float(m) for t, m in (r.get("by_tag") or {}).items() if roof_mark(t)}
      m = round(sum(marks.values()) + float(r.get("unmarked_m") or 0.0), 3)
      cur = out.get(level)
      if m > 0 and (cur is None or m > cur["m"]):
        out[level] = {"m": m, "pages": [s.page_no], "marks": marks}
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

def framing_floors(strips: dict, walls: dict) -> dict:
  return {lv: s for lv, s in strips.items() if lv in walls and walls[lv]["m"] > 0 and s["m"] >= C.BEAM_FRAMING_MIN_SHARE * walls[lv]["m"]}

def annotate(rows: list, strips: dict, walls: dict) -> set:
  owned = framing_floors(strips, walls)
  changed: set = set()
  for r in rows:
    f = r.facts or {}
    if r.category != "BEAM" or r.decision == "ACCEPTED":
      continue
    wall_beam = f.get("derived_from") == "WALLS" and f.get("beam_role") == "ROOF"
    strip_beam = bool(f.get("from_strips")) and roof_mark(r.tag)
    
    if not wall_beam and not f.get("from_strips"):
      continue
    level = f.get("level_hint") or (f.get("view") or {}).get("level_hint")
    notes = [n for n in (r.notes or []) if n.get("code") not in CODES]
    framing = None
    if wall_beam and level in owned:
      s = owned[level]
      framing = {"strips_m": s["m"], "wall_beams_m": walls[level]["m"], "pages": s["pages"], "marks": sorted(s["marks"])}
      notes.append(C.note("BEAM_FROM_FRAMING_PLAN", **framing))
    elif wall_beam and level in strips and level in walls:
      s = strips[level]
      
      notes.append(C.note("BEAM_STRIPS_DRAWN_ON_FLOOR", strips_m=s["m"], marks=sorted(s["marks"]), pages=s["pages"]))
    if strip_beam and level in walls and level in strips and level not in owned:
      w = walls[level]
      notes.append(C.note("BEAM_STRIPS_OVERLAP_WALL_BEAMS", wall_beams_m=w["m"], pages=w["pages"]))
    held_before = f.get("framing_plan")
    if notes != (r.notes or []) or framing != held_before:
      r.notes = notes
      r.facts = {**{k: v for k, v in f.items() if k != "framing_plan"}, **({"framing_plan": framing} if framing else {})}
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
