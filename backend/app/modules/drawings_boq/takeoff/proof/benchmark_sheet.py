from __future__ import annotations
from app.modules.drawings_boq.takeoff.prep import facts as F
from app.modules.drawings_boq.takeoff.proof import known_facts as K

SHEET_KINDS = ("LEVEL", "STOREY", "AREA_TABLE", "STAIR", "SITE_ITEM")
NEEDS = {"LEVEL": ("name", "mm"), "STOREY": ("clear_mm", "count"), "AREA_TABLE": ("key", "value"), "STAIR": ("field", "value"), "SITE_ITEM": ("site_kind", "count")}
SFT_TO_M2 = 0.09290304
MM_TOL = 1.0                     
AREA_TOL_SFT = 0.5
SITE_SIZES = ("length_mm", "width_mm", "height_mm")

def _res(f: dict, text: str, status: str, expected, found, message: str) -> dict:
  return {"fact": {"kind": f["kind"], "category": f["kind"]}, "text": text, "status": status, "expected": expected, "found": found, "message": message, "note": str(f.get("note") or "")}

def _gathered(read: list) -> dict:
  return F.gather([{"page_no": sh["page_no"], "facts": sh.get("facts")} for sh in read if sh.get("facts")])

def _schedule(read: list) -> dict:
  for sh in read:
    if sh.get("schedule"):
      return sh["schedule"]
  return {}

def _level(f: dict, g: dict) -> dict:
  name, mm = str(f["name"]).upper(), float(f["mm"])
  text = f"level {name} at {mm:g} mm"
  found = [x for x in (g.get("named_levels") or []) if x["name"] == name]
  
  if not found:
    return _res(f, text, K.MISSING, mm, None, f"No level named {name} was read from the sections.")
  if any(abs(x["mm"] - mm) <= MM_TOL for x in found):
    return _res(f, text, K.PASS, mm, mm, f"{name} read at {mm:g} mm, {sum(x['count'] for x in found)} time(s).")
  return _res(f, text, K.FAIL, mm, found[0]["mm"], f"You say {mm:g} mm; {', '.join(format(x['mm'], 'g') for x in found)} mm was read for {name}.")

def _storey(f: dict, g: dict) -> dict:
  clear, n = float(f["clear_mm"]), int(f["count"])
  text = f"{n} storey(s) {clear:g} mm clear"
  
  st = g.get("storeys")
  if not st:
    return _res(f, text, K.MISSING, n, None, "No storey heights were read from the sections.")
  hit = [c for c in st["clusters"] if abs(c["clear_mm"] - clear) <= MM_TOL]
  if not hit:
    return _res(f, text, K.MISSING if not st["clusters"] else K.FAIL, n, 0, f"No storey of {clear:g} mm; read: {', '.join(format(c['clear_mm'], 'g') for c in st['clusters'])} mm.")
  if len(hit) != n:
    return _res(f, text, K.FAIL, n, len(hit), f"You say {n} storey(s) of {clear:g} mm; {len(hit)} were read.")
  if f.get("slab_mm") is not None:
    bad = [c["implied_slab_mm"] for c in hit if c.get("implied_slab_mm") is not None and abs(c["implied_slab_mm"] - float(f["slab_mm"])) > MM_TOL]
    if bad:
      return _res(f, text, K.FAIL, n, len(hit), f"The slab the levels imply is {bad[0]:g} mm, not {float(f['slab_mm']):g}.")
  return _res(f, text, K.PASS, n, len(hit), f"{len(hit)} storey(s) of {clear:g} mm clear.")

def _area(f: dict, sched: dict) -> dict:
  key, val = str(f["key"]).upper(), float(f["value"])
  unit = str(f.get("unit") or "SFT").upper()
  want_sft = val if unit == "SFT" else val / SFT_TO_M2
  text = f"area table {key} {val:g} {unit.lower()}"
  rows = [r for r in (sched.get("areas") or []) if r.get("key") == key]
  
  if not rows:
    return _res(f, text, K.MISSING, val, None, f"No line '{key}' was read from the area table.")
  got = rows[0]["m2"] / SFT_TO_M2
  if abs(got - want_sft) <= AREA_TOL_SFT:
    return _res(f, text, K.PASS, val, round(got, 1), f"{key} read as {rows[0]['value']:g} {rows[0]['unit'].lower()}.")
  return _res(f, text, K.FAIL, val, round(got, 1), f"You say {want_sft:g} sft; {got:.1f} sft was read.")

def _stair(f: dict, sched: dict) -> dict:
  field, val = str(f["field"]), float(f["value"])
  text = f"stair {field} {val:g}"
  st = sched.get("stair") or {}
  if st.get(field) is None:
    return _res(f, text, K.MISSING, val, None, f"The stair specification has no {field}.")
  if abs(float(st[field]) - val) <= (0.0 if field == "steps" else MM_TOL):
    return _res(f, text, K.PASS, val, st[field], f"{field} = {st[field]:g}.")
  return _res(f, text, K.FAIL, val, st[field], f"You say {val:g}; {st[field]:g} was read.")

def _site(f: dict, read: list) -> dict:
  kind, n = str(f["site_kind"]).upper(), int(f["count"])
  page = f.get("page")
  text = f"{n} x {kind}" + (f" on page {page}" if page else "")
  rows = [c for sh in read if not page or sh["page_no"] == int(page) for c in sh["candidates"] if c.category == "SITE" and (c.facts or {}).get("site_kind") == kind]
  
  if not rows:
    return _res(f, text, K.MISSING, n, 0, f"No {kind} was read.")
  if len(rows) != n:
    return _res(f, text, K.FAIL, n, len(rows), f"You say {n}; {len(rows)} read.")
  for size in SITE_SIZES:
    if f.get(size) is not None:
      got = (rows[0].facts or {}).get(size)
      if got is None:
        return _res(f, text, K.MISSING, n, len(rows), f"The {kind} was read without its {size}.")
      if abs(float(got) - float(f[size])) > 5.0:
        return _res(f, text, K.FAIL, n, len(rows), f"{size}: you say {float(f[size]):g}; {float(got):g} was read.")
  return _res(f, text, K.PASS, n, len(rows), f"{len(rows)} {kind} read.")

def check(f: dict, read: list) -> dict:
  k = f["kind"]
  if k == "LEVEL":
    return _level(f, _gathered(read))
  if k == "STOREY":
    return _storey(f, _gathered(read))
  if k == "AREA_TABLE":
    return _area(f, _schedule(read))
  if k == "STAIR":
    return _stair(f, _schedule(read))
  return _site(f, read)
