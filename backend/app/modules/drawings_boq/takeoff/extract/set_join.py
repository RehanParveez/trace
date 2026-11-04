from __future__ import annotations
import math
import re
from collections import Counter
from difflib import SequenceMatcher
from app.engine.measure import readings as RD

ALIASES = {"BWP": "BAHAWALPUR", "BWN": "BAHAWALNAGAR", "LHR": "LAHORE", "ISB": "ISLAMABAD", "RWP": "RAWALPINDI"}
PLOT_AT = re.compile(r"PLOT\s*(?:NO\.?|NUMBER|#)?\s*[:.]?\s*(\d{1,4})\b")
PLOT_HOUSE = re.compile(r"\b(\d{1,4})\s*-\s*([A-Z])\s+HOUSE\b")
SECTOR = re.compile(r"\bSECTOR\s*-?\s*([A-Z])\b")
SCHEME = re.compile(r"\bD\.?\s?H\.?\s?A\.?(?:\s*[-,]?\s*(?:PHASE\s*)?([IVX]+|\d)\b)?[\s,.]*([A-Z]{3,}\.?)?")
def _spaced(word: str) -> str:
  """A pattern for a word that may be letter-spaced (S L A B), as some title lines are plotted."""
  return r"\s*".join(word)

SLAB_CAPTION = re.compile(_spaced("SLAB") + r"\s+" + _spaced("THICKNESS") + r"\s*=\s*(\d+(?:\.\d+)?)\s*(?:\"|”|IN)")
SLAB_NOTE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:INCH|IN\b|\"|”)\s*(?:THICK|THK)\.?\s*(?:R\.?C\.?C\.?\s*)?SLAB")
IN_MM = 25.4
FT_MM = 304.8

def _text(words: list) -> str:
  return re.sub(r"\s+", " ", " ".join(w.text for w in words)).upper()

def plot_text(words: list) -> dict | None:
  t = _text(words)
  plot = sector = scheme = city = None
  m = PLOT_AT.search(t)
  if m:
    plot = m.group(1)
  h = PLOT_HOUSE.search(t)
  if h:
    plot, sector = plot or h.group(1), h.group(2)
  s = SECTOR.search(t)
  if s:
    sector = sector or s.group(1)
  d = SCHEME.search(t)
  if d:
    scheme = "DHA"
    word = (d.group(2) or "").strip(". ")
    if word and word not in ("HOUSE", "THE", "AND", "FOR", "SECTOR", "PLOT", "BWP,") and len(word) >= 3:
      city = ALIASES.get(word, word)
  if not plot and not scheme:
    return None
  return {"plot": plot, "sector": sector, "scheme": scheme, "city": city}

def slab_statements(words: list, page_text: str = "") -> list:
  t = _text(words) + " | " + re.sub(r"\s+", " ", page_text or "").upper()
  out, seen = [], set()
  for m in SLAB_CAPTION.finditer(t):
    out.append({"inches": float(m.group(1)), "kind": "PLAN_CAPTION"})
  for m in SLAB_NOTE.finditer(t):
    if "DEPRESS" not in t[max(0, m.start() - 12):m.end() + 12]:
      out.append({"inches": float(m.group(1)), "kind": "NOTE"})
  return [o for o in out if not (o["inches"], o["kind"]) in seen and not seen.add((o["inches"], o["kind"]))]

def _vote(items: list) -> str | None:
  c = Counter(i for i in items if i)
  return c.most_common(1)[0][0] if c else None

def set_identity(rows: list) -> dict:
  texts = [((r.get("meta") or {}).get("plot_text") or {}) for r in rows]
  return {k: _vote([t.get(k) for t in texts]) for k in ("plot", "sector", "scheme", "city")}

def _same_city(x: str, y: str) -> bool:
  return x == y or SequenceMatcher(None, x, y).ratio() >= 0.85

def pair_sets(a: dict, b: dict) -> dict:
  same = lambda k: a.get(k) and b.get(k) and (_same_city(a[k], b[k]) if k == "city" else a[k] == b[k])
  shared = [k for k in ("plot", "scheme", "sector", "city") if same(k)]
  clash = [k for k in ("plot", "scheme", "city", "sector") if a.get(k) and b.get(k) and not same(k)]
  if clash:
    return {"paired": False, "shared": shared, "why": "the title blocks differ in " + ", ".join(clash)}
  if "plot" in shared and "scheme" in shared:
    return {"paired": True, "shared": shared, "why": "the title blocks print the same " + ", ".join(shared)}
  return {"paired": False, "shared": shared, "why": "the title blocks do not both print a plot and a scheme"}

def fit_similarity(pairs: list, rotations: tuple = (0, 90, 180, 270)) -> dict | None:
  if len(pairs) < 2:
    return None

  best = None
  for deg in rotations:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    a = [(c * p[0][0] - s * p[0][1], s * p[0][0] + c * p[0][1]) for p in pairs]
    b = [p[1] for p in pairs]
    n = len(pairs)
    ca, cb = (sum(p[0] for p in a) / n, sum(p[1] for p in a) / n), (sum(p[0] for p in b) / n, sum(p[1] for p in b) / n)
    num = sum((x[0] - ca[0]) * (y[0] - cb[0]) + (x[1] - ca[1]) * (y[1] - cb[1]) for x, y in zip(a, b))
    den = sum((x[0] - ca[0]) ** 2 + (x[1] - ca[1]) ** 2 for x in a)
    if den <= 0:
      continue
    k = num / den
    if k <= 0:
      continue
  
    dx, dy = cb[0] - k * ca[0], cb[1] - k * ca[1]
    res = math.sqrt(sum((k * x[0] + dx - y[0]) ** 2 + (k * x[1] + dy - y[1]) ** 2 for x, y in zip(a, b)) / n)
    if best is None or res < best["residual_mm"]:
      best = {"scale": round(k, 5), "rotation": deg, "dx": round(dx, 1), "dy": round(dy, 1), "residual_mm": round(res, 2), "n": n}
  return best

def footprint_mm(row: dict) -> tuple | None:
  k = row.get("mm_per_pt")
  samples = (((row.get("meta") or {}).get("outline") or {}).get("samples")) or []
  if not k or not samples:
    return None
  near = [s for s in samples if abs(s["f"] - k) <= RD.SET_FOOTPRINT_SCALE_TOL * k]
  
  if not near:
    return None
  s = min(near, key=lambda s: abs(s["f"] - k))
  return (round(s["short_pt"] * k, 1), round(s["long_pt"] * k, 1))

def _rect(a: float, b: float) -> list:
  return [(0.0, 0.0), (a, 0.0), (a, b), (0.0, b)]

def align_outline(a_rows: list, b_rows: list, floor: str = "GROUND") -> dict:
  def pick(rows: list) -> tuple:
    best = None
    for r in rows:
      ident = (r.get("meta") or {}).get("identity") or {}
      if ident.get("floor") == floor and ident.get("plan_kind") in ("WORKING", "FRAMING", "FOUNDATION", None):
        fp = footprint_mm(r)
        if fp and (best is None or fp[0] * fp[1] > best[0][0] * best[0][1]):
          best = (fp, r["page_no"])
    return best or (None, None)

  fa, pa = pick(a_rows)
  fb, pb = pick(b_rows)
  if fa is None or fb is None:
    return {"basis": "OUTLINE", "status": "UNSURE", "fit": None, "residual_in": None, "pages": {"a": pa, "b": pb}, "why": f"no building outline could be measured on the {floor.lower()} plan of {'either set' if fa is None and fb is None else 'one set'}"}
  fit = fit_similarity(list(zip(_rect(*fa), _rect(*fb))))
  res_in = round(fit["residual_mm"] / IN_MM, 2) if fit else None
  why = "the sets share no grid, so they are aligned on the building outline alone"
  if res_in is not None and res_in > RD.SET_JOIN_MAX_RESIDUAL_IN:
    why += f"; the residual {res_in:g} in is over {RD.SET_JOIN_MAX_RESIDUAL_IN:g} in"
  return {"basis": "OUTLINE", "status": "UNSURE", "fit": fit, "residual_in": res_in, "outline_a_mm": list(fa), "outline_b_mm": list(fb), "pages": {"a": pa, "b": pb}, "why": why}

def align_grid(pairs: list) -> dict:
  fit = fit_similarity(pairs)
  if fit is None:
    return {"basis": "GRID", "status": "UNSURE", "fit": None, "residual_in": None, "why": "fewer than two grid crossings are shared"}
  res_in = round(fit["residual_mm"] / IN_MM, 2)
  if fit["n"] < RD.SET_JOIN_MIN_CROSSINGS:
    return {"basis": "GRID", "status": "UNSURE", "fit": fit, "residual_in": res_in, "why": f"only {fit['n']} grid crossings are shared"}
  ok = res_in <= RD.SET_JOIN_MAX_RESIDUAL_IN
  return {"basis": "GRID", "status": "ALIGNED" if ok else "UNSURE", "fit": fit, "residual_in": res_in, "why": None if ok else f"the residual {res_in:g} in is over {RD.SET_JOIN_MAX_RESIDUAL_IN:g} in"}

def slab_join(a_rows: list, b_rows: list) -> dict:
  where: dict = {}
  for tag, rows in (("A", a_rows), ("B", b_rows)):
    for r in rows:
      for s in ((r.get("meta") or {}).get("slab_statements")) or []:
        where.setdefault(s["inches"], []).append({"set": tag, "page": r["page_no"], "kind": s["kind"]})
        
  captions = {v for v, ws in where.items() if any(w["kind"] == "PLAN_CAPTION" for w in ws)}
  notes = {v for v, ws in where.items() if any(w["kind"] == "NOTE" for w in ws)}
  conflict = bool(captions and notes and not (captions & notes))
  return {"values": [{"inches": v, "printed": ws} for v, ws in sorted(where.items())], "conflict": conflict, "captions_in": sorted(captions), "notes_in": sorted(notes),
    "cross_set": bool({w["set"] for ws in where.values() for w in ws} == {"A", "B"} and len(where) > 1)}

def levels_join(arch_rows: list, struct_floors: list) -> dict:
  from app.modules.drawings_boq.takeoff.prep import closure_facts as CF
  got = CF.level_names(arch_rows)
  floors = []
  last = None
  for name in struct_floors:
    mm = got.get(f"{name.lower()}_mm")
    rec = {"floor": name, "level_mm": mm, "level_ft": None if mm is None else round(mm / FT_MM, 3), "storey_height_mm": None if mm is None or last is None else round(mm - last, 1), "state": "DERIVED" if mm is not None else "MISSING"}
    floors.append(rec)
    last = mm if mm is not None else last
  return {"floors": floors, "plinth_mm": got.get("plinth_mm"), "named": {k: v for k, v in got.items() if k.endswith("_mm")}}

def columns_in_walls(col_pts: list, wall_boxes: list, fit: dict, status: str) -> dict:
  if status != "ALIGNED":
    return {"share": None, "columns": len(col_pts), "why": "the sets are not aligned by a grid, so positions cannot be trusted"}
  inside = 0
  for (x, y) in col_pts:
    X, Y = fit["scale"] * x + fit["dx"], fit["scale"] * y + fit["dy"]
    if any(b[0] <= X <= b[2] and b[1] <= Y <= b[3] for b in wall_boxes):
      inside += 1
  return {"share": round(inside / len(col_pts), 3) if col_pts else None, "columns": len(col_pts), "why": None}

def join_sets(a_name: str, a_rows: list, b_name: str, b_rows: list) -> dict:
  ia, ib = set_identity(a_rows), set_identity(b_rows)
  pair = pair_sets(ia, ib)
  out = {"a": a_name, "b": b_name, "identity": {"a": ia, "b": ib}, "pair": pair}
  if not pair["paired"]:
    return out

  out["alignment"] = align_outline(a_rows, b_rows)
  floors = [f for f in ("GROUND", "FIRST", "SECOND", "ROOF") if any(((r.get("meta") or {}).get("identity") or {}).get("floor") == f for r in a_rows)]
  out["levels"] = levels_join(b_rows, floors)
  out["slab"] = slab_join(a_rows, b_rows)
  cols = [c.geometry["points"][0] for r in a_rows for c in r.get("candidates") or [] if c.category == "COLUMN" and (c.geometry or {}).get("points")]
  out["columns_in_walls"] = columns_in_walls(cols, [], (out["alignment"].get("fit") or {}), out["alignment"]["status"])
  return out
