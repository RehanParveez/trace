from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.proof import readsummary as RS

KINDS = ("TOTAL", "COUNT", "ROOM_AREA", "SLAB_AREA", "SCHEDULE")
PASS, FAIL, MISSING = "PASS", "FAIL", "MISSING"
FLOOR_WORDS = {"GF": "GROUND", "G": "GROUND", "FF": "FIRST", "SF": "SECOND", "TF": "THIRD", "BSMT": "BASEMENT", "B": "BASEMENT", "BASEMENT": "BASEMENT", "GROUND": "GROUND",
  "FIRST": "FIRST", "SECOND": "SECOND", "THIRD": "THIRD", "FOURTH": "FOURTH", "ROOF": "ROOF", "MEZZANINE": "MEZZANINE", "FOUNDATION": "FOUNDATION", "TYPICAL": "TYPICAL"}
AREA_TOL_PCT = 3.0

def floor_key(word: str | None) -> str | None:
  if word is None or not str(word).strip():
    return None
  w = str(word).strip().upper().replace(" FLOOR", "")
  if w not in FLOOR_WORDS:
    raise ValueError(f"'{word}' is not a floor I know (basement, ground, first, second, roof, or GF, FF, SF).")
  return FLOOR_WORDS[w]

def _num(raw, name: str, minimum: float = 0.0) -> float:
  try:
    v = float(raw)
  except (TypeError, ValueError):
    raise ValueError(f"{name} must be a number, not '{raw}'.")
  if v < minimum:
    raise ValueError(f"{name} cannot be below {minimum:g}.")
  return v

def normalise(raw: dict) -> dict:
  """A fact as given -> the fact as kept (upper-case words, floors as the reader names them). Raises ValueError with a plain sentence when it cannot be used."""
  kind = str(raw.get("kind") or "").strip().upper()
  if kind not in KINDS:
    raise ValueError(f"A fact is one of {', '.join(KINDS)}; '{raw.get('kind')}' is not.")
  out: dict = {"kind": kind}
  
  if kind in ("TOTAL", "COUNT"):
    cat = str(raw.get("category") or "").strip().upper()
    if cat not in C.CATEGORIES:
      raise ValueError(f"'{raw.get('category')}' is not a kind of item I read ({', '.join(C.CATEGORIES)}).")
    out["category"] = cat
    out["floor"] = floor_key(raw.get("floor"))
    out["count"] = int(_num(raw.get("count"), "The count"))
    if kind == "COUNT":
      tag = str(raw.get("tag") or "").strip().upper()
      if not tag:
        raise ValueError("A count of one mark needs the mark (C1, D2, F1).")
      out["tag"] = tag
      
  elif kind == "ROOM_AREA":
    name = str(raw.get("name") or "").strip().upper()
    if not name:
      raise ValueError("A room area needs the name of the room as the plan prints it.")
    out.update(name=name, floor=floor_key(raw.get("floor")), area_m2=_num(raw.get("area_m2"), "The area", 0.01))
  elif kind == "SLAB_AREA":
    fl = floor_key(raw.get("floor"))
    
    if not fl:
      raise ValueError("A slab area needs the floor.")
    out.update(floor=fl, area_m2=_num(raw.get("area_m2"), "The area", 0.01))
  else:
    mark = str(raw.get("mark") or "").strip().upper()
    if not mark:
      raise ValueError("A schedule row needs the mark (D1, W2).")
    out["mark"] = mark
    for k in ("width_mm", "height_mm"):
      if raw.get(k) not in (None, ""):
        out[k] = _num(raw.get(k), k, 1.0)
        
  if raw.get("tolerance_pct") not in (None, ""):
    out["tolerance_pct"] = _num(raw.get("tolerance_pct"), "The tolerance", 0.0)
  return out

def describe(f: dict) -> str:
  fl = f" on the {f['floor'].title()} floor" if f.get("floor") else ""
  if f["kind"] == "TOTAL":
    return f"{f['count']} {f['category'].lower()}{fl}"
  if f["kind"] == "COUNT":
    return f"{f['count']} of {f['tag']}{fl}"
  if f["kind"] == "ROOM_AREA":
    return f"{f['name'].title()}{fl} is {f['area_m2']:g} m²"
  if f["kind"] == "SLAB_AREA":
    return f"the slab over the {f['floor'].title()} floor covers {f['area_m2']:g} m²"
  extra = " ".join(f"{k[:-3]} {f[k]:g}" for k in ("width_mm", "height_mm") if k in f)
  return f"schedule row {f['mark']} {extra}".strip()

def _pages(read: list, pred) -> list:
  return sorted({sh["page_no"] for sh in read if pred(sh)})

def _result(f: dict, status: str, expected, found, message: str, pages: list) -> dict:
  return {"fact": f, "text": describe(f), "status": status, "expected": expected, "found": found, "message": message, "pages": pages}

def _count_fact(read: list, f: dict) -> dict:
  cat = f["category"]
  table = RS.counts(read, cat)
  pages = _pages(read, lambda sh: any(c.category == cat for c in sh["candidates"]))
  
  if f["kind"] == "TOTAL":
    floors = [f["floor"]] if f.get("floor") else list(table)
    found = sum(n for fl in floors for n in table.get(fl, {}).values())
    where = f" on the {f['floor'].title()} floor" if f.get("floor") else ""
    label = cat.lower() + ("s" if not cat.endswith("S") else "")
    
  else:
    floors = [f["floor"]] if f.get("floor") else list(table)
    found = sum(table.get(fl, {}).get(f["tag"], 0) for fl in floors)
    where = f" on the {f['floor'].title()} floor" if f.get("floor") else ""
    label = f"of {f['tag']}"
  if found == 0 and f["count"] != 0:
    return _result(f, MISSING, f["count"], 0, f"No {cat.lower()}{'' if f['kind'] == 'TOTAL' else ' ' + f['tag']} was read{where}. It is not on a sheet that has been read, or it was read as something else.", pages)
  if found == f["count"]:
    return _result(f, PASS, f["count"], found, f"{found} {label}{where}: as you say.", pages)
  d = found - f["count"]
  return _result(f, FAIL, f["count"], found, f"You say {f['count']} {label}{where}; {found} were read ({abs(d)} {'more' if d > 0 else 'fewer'}).", pages)

def _room_fact(read: list, f: dict) -> dict:
  tol = (f.get("tolerance_pct") if f.get("tolerance_pct") is not None else AREA_TOL_PCT) / 100.0
  table = RS.rooms(read)
  floors = [f["floor"]] if f.get("floor") else list(table)
  hits = [(fl, name, a) for fl in floors for name, a in table.get(fl, {}).items() if f["name"] in name]
  pages = _pages(read, lambda sh: any(c.category == "ROOM" for c in sh["candidates"]))
  
  if not hits:
    return _result(f, MISSING, f["area_m2"], None, f"No room called {f['name'].title()} was read{' on the ' + f['floor'].title() + ' floor' if f.get('floor') else ''}.", pages)
  best = min(hits, key=lambda h: abs(h[2] - f["area_m2"]))
  fl, name, a = best
  also = [h for h in hits if h is not best]
  
  more = f" Also read under this name: {', '.join(f'{n.title()} ({x.title()}) {v:.2f} m²' for x, n, v in also[:4])}." if also else ""
  off = (a - f["area_m2"]) / f["area_m2"]
  if abs(off) <= tol:
    return _result(f, PASS, f["area_m2"], round(a, 2), f"{name.title()} ({fl.title()}): {a:.2f} m², {off * 100:+.1f}% from {f['area_m2']:g}: within {tol * 100:g}%." + more, pages)
  return _result(f, FAIL, f["area_m2"], round(a, 2), f"{name.title()} ({fl.title()}): {a:.2f} m² was read, {off * 100:+.1f}% from your {f['area_m2']:g}: outside {tol * 100:g}%." + more, pages)

def _slab_fact(read: list, f: dict) -> dict:
  tol = (f.get("tolerance_pct") if f.get("tolerance_pct") is not None else AREA_TOL_PCT) / 100.0
  a = RS.slabs(read).get(f["floor"])
  pages = _pages(read, lambda sh: any(c.category == "SLAB" for c in sh["candidates"]))
  
  if a is None:
    return _result(f, MISSING, f["area_m2"], None, f"No slab was read for the {f['floor'].title()} floor.", pages)
  off = (a - f["area_m2"]) / f["area_m2"]
  ok = abs(off) <= tol
  return _result(f, PASS if ok else FAIL, f["area_m2"], round(a, 2), f"The slab over the {f['floor'].title()} floor covers {a:.2f} m², {off * 100:+.1f}% from your {f['area_m2']:g}: {'within' if ok else 'outside'} {tol * 100:g}%.", pages)

def _schedule_fact(read: list, f: dict) -> dict:
  rows = [(sh["page_no"], o) for sh in read for o in ((sh.get("schedule") or {}).get("openings") or []) if str(o.get("mark", "")).upper() == f["mark"]]
  if not rows:
    return _result(f, MISSING, f["mark"], None, f"No row {f['mark']} was read from an opening schedule.", [])
  page, o = rows[0]
  
  bad = []
  for k in ("width_mm", "height_mm"):
    if k in f and o.get(k) is not None and abs(float(o[k]) - f[k]) > max(1.0, 0.005 * f[k]):
      bad.append(f"{k[:-3]} {float(o[k]):g} read, {f[k]:g} yours")
  if bad:
    return _result(f, FAIL, {k: f[k] for k in ("width_mm", "height_mm") if k in f}, {k: o.get(k) for k in ("width_mm", "height_mm")}, f"Schedule row {f['mark']} (page {page}): {'; '.join(bad)}.", [page])
  return _result(f, PASS, f["mark"], f["mark"], f"Schedule row {f['mark']} (page {page}) is as you say.", [page])

def check(read: list, facts: list) -> list:
  out = []
  for f in facts:
    out.append(_count_fact(read, f) if f["kind"] in ("TOTAL", "COUNT") else _room_fact(read, f) if f["kind"] == "ROOM_AREA"
      else _slab_fact(read, f) if f["kind"] == "SLAB_AREA" else _schedule_fact(read, f))
  return out

def tally(results: list) -> dict:
  return {"pass": sum(1 for r in results if r["status"] == PASS), "fail": sum(1 for r in results if r["status"] == FAIL), "missing": sum(1 for r in results if r["status"] == MISSING)}
