from __future__ import annotations
import re
from app.engine.measure import readings as RD
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.extract import slab_panels as SP
from app.modules.drawings_boq.takeoff.extract import structure_tables as ST
from app.modules.drawings_boq.takeoff.page import access as AC
from app.modules.drawings_boq.takeoff.page import model as PM

RULE = "SLAB_CALLOUT_ITEMS"

RULE = "SLAB_CALLOUT_ITEMS"
META_KEY = "slab_callout_items"
SOURCE_KEY = "slab_callouts"
INCH_MARK = r"(?:[\"”″]|'')?"
CALLOUT = re.compile(rf"^#\s*(?P<bar>\d{{1,2}})\s*{INCH_MARK}\s*@\s*(?P<s>\d{{1,2}}(?:\.\d)?)\s*{INCH_MARK}\s*(?P<alt>/\s*\d{{1,2}}(?:\.\d)?\s*{INCH_MARK})?\s*(?:C\s*/\s*C)?\s*$", re.I)
PLAN_KINDS = ("STRUCT_PLAN", "PLAN")
PLAN_WORDS = ("REINFORCEMENT", "SLAB")
NOT_SLAB = ("FOUNDATION", "FOOTING", "COLUMN", "STAIR", "TANK", "SEPTIC")
NOT_SLAB_UNLESS_SLAB = ("BEAM", "LINTEL")

def enabled() -> bool:
  return RR.on(RULE)

def strings_of(words: list) -> dict:
  one, alt = [], []
  
  for w in words:
    m = CALLOUT.match((w.text or "").strip())
    if m is None:
      continue
    
    bar, spacing = int(m.group("bar")), float(m.group("s"))
    if not (SP.BAR_NUMBERS[0] <= bar <= SP.BAR_NUMBERS[1] and SP.SPACING_IN[0] <= spacing <= SP.SPACING_IN[1]):
      continue
    rec = {"text": w.text.strip(), "bar": bar, "spacing_in": spacing, "at": [round((w.x0 + w.x1) / 2, 2), round((w.y0 + w.y1) / 2, 2)], "axis": "X" if round(float(w.angle) / 90.0) % 2 == 0 else "Y"}
    (alt if m.group("alt") else one).append(rec)
  return {"callouts": one, "alternate": alt}

def read(raw, model: dict | None = None) -> dict | None:
  if not enabled() or not raw.words:
    return None
  words, _ = ST.upright_words(raw)
  model = model or AC.model_of(raw)
  mine = [words[i].raw for r in AC.regions_of(model, PM.CALLOUT) for i in r.words if 0 <= i < len(words)]
  got = strings_of(mine)
  return got if got["callouts"] or got["alternate"] else None

def plan_view(meta: dict) -> str | None:
  for view in meta.get("views") or []:
    key = (view.get("key") if isinstance(view, dict) else None) or ""
    kind, _, rest = key.partition(":")
    title = rest.partition(":")[2].upper()
    if kind in PLAN_KINDS and any(w in title for w in PLAN_WORDS) and not any(n in title for n in NOT_SLAB):
      if "REINFORCEMENT" in title or "SLAB" in title or not any(n in title for n in NOT_SLAB_UNLESS_SLAB):
        return key
  return None

def captionless_plan(meta: dict, got: dict) -> bool:
  if len(got.get("callouts") or []) < RD.SLAB_PLAN_MIN_CALLOUTS:
    return False
  for view in meta.get("views") or []:
    key = (view.get("key") if isinstance(view, dict) else None) or ""
    if any(n in key.upper() for n in NOT_SLAB):
      return False
  return True

def panels_of(row: dict) -> list:
  from shapely.geometry import Polygon
  graph = (row.get("stats") or {}).get("slab_panel_graph") or {}
  out = []
  for view in graph.get("views") or []:
    for i, p in enumerate(view.get("panels") or []):
      ring = p.get("polygon") or []
      if len(ring) >= 3:
        out.append({"view": view.get("key"), "n": i + 1, "mark": p.get("mark"), "void": bool(p.get("void")), "face": Polygon(ring)})
  return out

def table_of(row: dict) -> list:
  graph = (row.get("stats") or {}).get("slab_panel_graph") or {}
  out = []
  for view in graph.get("views") or []:
    for i, p in enumerate(view.get("panels") or []):
      calls = [{"bar": c["bar"], "spacing_in": c["spacing_in"], "axis": c["axis"], "role": c.get("role")} for c in p.get("callouts") or []]
      if calls and not p.get("void"):
        out.append({"view": view.get("key"), "n": i + 1, "spans": p.get("spans"), "x_ft": p.get("clear_span_x_ft"), "y_ft": p.get("clear_span_y_ft"), "flags": list(p.get("flags") or []), "callouts": calls})
  return out

def bind(callouts: list, panels: list) -> dict:
  from shapely.geometry import Point
  bound, loose = 0, 0
  for c in callouts:
    c.pop("panel", None)
    where = Point(c["at"][0], c["at"][1])
    hits = sorted((p for p in panels if p["face"].contains(where)), key=lambda p: p["face"].area)
    if hits and not hits[0]["void"]:
      c["panel"] = {"view": hits[0]["view"], "n": hits[0]["n"], "mark": hits[0]["mark"]}
      bound += 1
    else:
      loose += 1
  return {"bound": bound, "unbound": loose, "panels": len(panels)}

def apply(rows: list) -> int:
  made = 0
  for row in rows:
    meta = row.get("meta")
    if meta is None:
      continue
    
    meta.pop(META_KEY, None)
    if not enabled():
      continue
    
    got = (meta.get("structure_tables") or {}).get(SOURCE_KEY)
    if not got or not got.get("callouts"):
      continue
    key = plan_view(meta)
    if key is None and not captionless_plan(meta, got):
      continue
    callouts = [dict(c) for c in got["callouts"]]
    meta[META_KEY] = {"view": key, "callouts": callouts, "alternate": len(got.get("alternate") or []), "binding": bind(callouts, panels_of(row)), "panels": table_of(row)}
    made += len(got["callouts"])
  return made
