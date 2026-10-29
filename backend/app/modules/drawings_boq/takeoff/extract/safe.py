from __future__ import annotations
from app.modules.drawings_boq.takeoff.evidence import PRINTED, VERIFIED, evidence_for
from app.modules.drawings_boq.takeoff.model import members as MB

SAFE, REVIEW = "SAFE", "REVIEW"
PRINTED_SOURCE, TWO_SIGHTINGS, NOT_SAFE = "PRINTED_SOURCE", "TWO_SIGHTINGS", "NONE"
PRINTED_BASES = (PRINTED, VERIFIED)
KIND_TEXT = {MB.SCHEDULE: "schedule", MB.DETAIL: "detail", MB.PLAN: "plan", "IFC": "IFC model"}
TOLERANCE_MM = {"COLUMN": MB.SIZE_TOL_MM, "FOOTING": MB.SIZE_TOL_MM, "BEAM": MB.SIZE_TOL_MM}     

def printed_source(ev: dict) -> list | None:
  items = [i for i in ev.get("inputs") or [] if i.get("name") != "count"]
  if ev.get("grade") != PRINTED or not items or any(i.get("basis") not in PRINTED_BASES for i in items):
    return None
  return [str(i["name"]) for i in items]

def _same(a, b, tol: float) -> bool:
  return a is not None and b is not None and len(a) == len(b) and all(abs(x - y) <= tol for x, y in zip(a, b))

def sightings(read: list, ifc: tuple = ()) -> dict:
  sheets = [s for s in read if "title" in s and "stats" in s]
  by_key = {MB.key_of(c): c for s in sheets for c in s["candidates"] if c.category in MB.KINDS}
  
  try:
    ms = MB.merge(MB.build(read), tuple(ifc or ()))
  except Exception:
    return {}
  out: dict = {}
  
  for m in ms.members:
    for s in m.sightings:
      c = by_key.get(s.candidate_key)
      mine = MB.size_of(c) if c is not None else None
      tol = TOLERANCE_MM.get(c.category, MB.SIZE_TOL_MM) if c is not None else MB.SIZE_TOL_MM
      if mine is not None and any(_same(mine, theirs, tol) for theirs in ms.ifc_sizes.get(m.id, [])):
        out.setdefault(s.candidate_key, []).append(("IFC", 0, "IFC", s.basis))
        
  for m in ms.members:
    seen = []
    
    for s in m.sightings:
      c = by_key.get(s.candidate_key)
      if c is not None:
        seen.append((s, MB.size_of(c), c))
    for s, size, c in seen:
      tol = TOLERANCE_MM.get(c.category, MB.SIZE_TOL_MM)
      for o, osize, oc in seen:
        if (o.drawing_id, o.page_no) != (s.drawing_id, s.page_no) and o.basis != s.basis and _same(size, osize, tol):
          out.setdefault(s.candidate_key, []).append((o.drawing_id, o.page_no, o.basis, s.basis))
  return out

def classify(c, ev: dict, seen: list | None, page_no: int | None = None) -> dict:
  names = printed_source(ev)
  if names:
    return {"status": SAFE, "basis": PRINTED_SOURCE, "text": "one printed source gives " + ", ".join(names)}
  if seen:
    o = seen[0]

    here = KIND_TEXT.get(o[3], str(o[3]))
    there = KIND_TEXT.get(o[2], str(o[2]))
    return {"status": SAFE, "basis": TWO_SIGHTINGS, "text": f"the {here}{f' on sheet {page_no}' if page_no is not None else ''} and the {there} on sheet {o[1]} agree on the size within {TOLERANCE_MM.get(c.category, MB.SIZE_TOL_MM):g} mm"}
  grade = ev.get("grade")
  ask = (ev.get("ask") or [None])[0]
  why = f"a value is {str(grade).lower()}" + (f" ({ask})" if ask else "") if grade in ("ASSUMED", "MISSING") else "no printed source for its value and no second independent sighting"
  return {"status": REVIEW, "basis": NOT_SAFE, "text": why}

def assess(read: list, live) -> dict:
  seen = sightings(read)
  out: dict = {}
  for sh in read:
    for c in sh.get("candidates") or []:
      if not live(c):
        continue
      out[str(c.id)] = classify(c, evidence_for(c), seen.get(MB.key_of(c)), sh.get("page_no"))
  return out
