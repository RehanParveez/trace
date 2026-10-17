from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract.crosschecks import _live, _floor, _sheet_floor
from app.modules.drawings_boq.takeoff.extract import config as C

SUMMED = ("WALL", "ROOM", "LINTEL", "STAIR", "SITE", "SLAB")     

def counts(read: list, category: str) -> dict:
  per_sheet: list = []
  for sh in read:
    sf = _sheet_floor(sh)
    slot: dict = {}
    
    for c in sh["candidates"]:
      f = c.facts or {}
      if c.category != category or not _live(c) or f.get("neck_of"):
        continue
    
      fl = _floor(c, sf) or "UNKNOWN"
      tag = c.tag or "(no mark)"
      n = int(c.count or 1)
      by = slot.setdefault(fl, {})
      by[tag] = by.get(tag, 0) + n if (category in SUMMED or not c.tag) else max(by.get(tag, 0), n)
    per_sheet.append(slot)
  out: dict = {}
  
  for slot in per_sheet:
    for fl, by in slot.items():
      dst = out.setdefault(fl, {})
      for tag, n in by.items():
        dst[tag] = max(dst.get(tag, 0), n)
  return out

def rooms(read: list) -> dict:
  """{floor: {name: area_m2}}; two rooms of one name on a floor are told apart by a number."""
  out: dict = {}
  
  for sh in read:
    sf = _sheet_floor(sh)
    for c in sh["candidates"]:
      f = c.facts or {}
      if c.category != "ROOM" or not _live(c) or not f.get("area_m2"):
        continue
    
      fl = _floor(c, sf) or "UNKNOWN"
      name = str(f.get("name") or "(no name)").strip().upper()
      by = out.setdefault(fl, {})
      key, n = name, 1
      while key in by and by[key] != float(f["area_m2"]):
        n += 1
        key = f"{name} #{n}"
      by[key] = float(f["area_m2"])
  return out

def slabs(read: list) -> dict:
  out: dict = {}
  for sh in read:
    for c in sh["candidates"]:
      f = c.facts or {}
      if c.category == "SLAB" and _live(c) and f.get("floor") and f.get("area_m2"):
        out[f["floor"]] = max(out.get(f["floor"], 0.0), float(f["area_m2"]))
  return out

def wall_metres(read: list) -> dict:
  """{floor: centre-line length of the walls, in metres}"""
  out: dict = {}
  
  for sh in read:
    sf = _sheet_floor(sh)
    per: dict = {}
    for c in sh["candidates"]:
      f = c.facts or {}
      
      if c.category == "WALL" and _live(c) and f.get("length_cc_m"):
        fl = _floor(c, sf) or "UNKNOWN"
        per[fl] = per.get(fl, 0.0) + float(f["length_cc_m"]) * int(c.count or 1)
    for fl, v in per.items():
      out[fl] = max(out.get(fl, 0.0), v)
  return {k: round(v, 2) for k, v in out.items()}

def summary(read: list) -> dict:
  cats = {cat: counts(read, cat) for cat in C.CATEGORIES}
  return {"counts": {k: v for k, v in cats.items() if v}, "totals": {k: sum(n for by in v.values() for n in by.values()) for k, v in cats.items() if v},
    "rooms": rooms(read), "slab_m2": slabs(read), "wall_m": wall_metres(read)}

def _close(a: float, b: float, tol: float) -> bool:
  return abs(a - b) <= tol * max(abs(a), abs(b), 1e-9)

def compare(a: dict, b: dict, area_tol: float = 0.03, length_tol: float = 0.02) -> list:
  out: list = []
  
  for cat in sorted(set(a["counts"]) | set(b["counts"])):
    fa, fb = a["counts"].get(cat, {}), b["counts"].get(cat, {})
    for fl in sorted(set(fa) | set(fb)):
      for tag in sorted(set(fa.get(fl, {})) | set(fb.get(fl, {}))):
        x, y = fa.get(fl, {}).get(tag, 0), fb.get(fl, {}).get(tag, 0)
        
        if x != y:
          out.append({"kind": "COUNT", "key": f"{cat} {tag} {fl}", "a": x, "b": y})
  for fl in sorted(set(a["rooms"]) | set(b["rooms"])):
    ra, rb = a["rooms"].get(fl, {}), b["rooms"].get(fl, {})
    for name in sorted(set(ra) | set(rb)):
      if name not in ra or name not in rb or not _close(ra[name], rb[name], area_tol):
        out.append({"kind": "ROOM", "key": f"{name} {fl}", "a": ra.get(name), "b": rb.get(name)})
        
  for fl in sorted(set(a["slab_m2"]) | set(b["slab_m2"])):
    x, y = a["slab_m2"].get(fl), b["slab_m2"].get(fl)
    if x is None or y is None or not _close(x, y, area_tol):
      out.append({"kind": "SLAB", "key": fl, "a": x, "b": y})
  for fl in sorted(set(a["wall_m"]) | set(b["wall_m"])):
    x, y = a["wall_m"].get(fl), b["wall_m"].get(fl)
    if x is None or y is None or not _close(x, y, length_tol):
      out.append({"kind": "WALL_M", "key": fl, "a": x, "b": y})
  return out

def pages(read: list) -> dict:
  return {sh["page_no"]: summary([sh]) for sh in read}

SAME, NAMED, DIFFERENT = "SAME", "NAMED", "DIFFERENT"

def verdict(base, new, skipped: list) -> dict:
  b, n, why = (base if isinstance(base, dict) else pages(base)), (new if isinstance(new, dict) else pages(new)), dict(skipped)
  out = []
  
  for page in sorted(set(b) | set(n)):
    if page not in n:
      out.append({"page_no": page, "status": NAMED if page in why else DIFFERENT, "code": why.get(page), "diffs": [{"kind": "SHEET", "key": f"page {page}", "a": "read", "b": "not read"}]})
    elif page not in b:
      out.append({"page_no": page, "status": DIFFERENT, "code": None, "diffs": [{"kind": "SHEET", "key": f"page {page}", "a": "not read", "b": "read"}]})
    else:
      d = compare(b[page], n[page])
      other = sorted(p for p in why if p != page)
      if d and other and all(x["kind"] == "COUNT" and str(x["key"]).startswith("COLUMN ") for x in d):
        out.append({"page_no": page, "status": NAMED, "code": f"DEPENDS_ON_PAGE_{other[0]}", "diffs": d})
        continue
    
      out.append({"page_no": page, "status": SAME if not d else DIFFERENT, "code": None, "diffs": d})
  worst = DIFFERENT if any(p["status"] == DIFFERENT for p in out) else NAMED if any(p["status"] == NAMED for p in out) else SAME
  return {"verdict": worst, "pages": out}
