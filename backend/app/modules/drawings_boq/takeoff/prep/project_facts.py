from __future__ import annotations
from types import SimpleNamespace
from app.modules.drawings_boq.takeoff.prep import opening_heights as OHT

STRIDE = 1000                      
HEIGHT_TOL_MM = 1.0                
FACT_NAMES = ("storey_heights", "slab_values", "spec_facts", "beam_sections", "tank_details", "footing_sections", "footing_views", "schedule", "units", "opening_labels", "column_details")

def stamp(pairs: list) -> tuple:
  order: dict = {}
  sheets, table = [], {}
  for drawing_id, s in pairs:
    n = order.setdefault(drawing_id, len(order))
    page = int(s.page_no)
    unique = n * STRIDE + page
    table[unique] = (drawing_id, page)
    sheets.append(SimpleNamespace(page_no=unique, label=getattr(s, "label", None), prep_meta=getattr(s, "prep_meta", None) or {}))
  return sheets, table

def _sources(unique_pages: list, table: dict) -> list:
  seen, out = set(), []
  for p in unique_pages:
    hit = table.get(p)
    if hit is not None and hit not in seen:
      seen.add(hit)
      out.append({"drawing_id": hit[0], "page_no": hit[1]})
  return out

def unstamp(value, table: dict):
  if isinstance(value, list):
    return [unstamp(v, table) for v in value]
  if not isinstance(value, dict):
    return value
  out = {k: unstamp(v, table) for k, v in value.items()}
  pages = value.get("pages")
  if isinstance(pages, list) and pages and all(isinstance(p, int) and not isinstance(p, bool) for p in pages):
    src = _sources(pages, table)
    out["pages"] = sorted({s["page_no"] for s in src}) if src else pages
    out["sources"] = src
  page = value.get("page_no")
  if isinstance(page, int) and not isinstance(page, bool) and page in table:
    out["page_no"] = table[page][1]
    out["sources"] = _sources([page], table)
  return out

def strip_sources(value):
  if isinstance(value, list):
    return [strip_sources(v) for v in value]
  if isinstance(value, dict):
    return {k: strip_sources(v) for k, v in value.items() if k != "sources"}
  return value

def column_details_of(metas: list) -> dict:
  from app.modules.drawings_boq.takeoff.extract.structure import column_details
  return column_details({"details": [d for m in metas for d in ((m or {}).get("details") or [])]})

def gather_all(sheets: list) -> dict:
  from app.modules.drawings_boq.takeoff import prep_service as PSV
  from app.modules.drawings_boq.takeoff.extract import spec_facts as SPF
  from app.modules.drawings_boq.takeoff.prep import beam_details as BD, facts as DF, schedules as DS, tank_details as TD, units as UR
  from app.modules.drawings_boq.takeoff.prep.storeys import storey_heights
  floor_keys = PSV.PrepService._floor_keys(sheets)
  gathered = DF.gather([{"page_no": s.page_no, "label": s.label, "facts": s.prep_meta.get("facts")} for s in sheets if s.prep_meta.get("facts") is not None])
  return {
    "floor_keys": floor_keys, "gathered": gathered,
    "storey_heights": storey_heights(floor_keys, gathered.get("storeys")),
    "slab_values": DF.slab_values(gathered["items"]),
    "spec_facts": SPF.build(gathered["items"]),
    "beam_sections": BD.gather([{"page_no": s.page_no, "details": s.prep_meta.get("beam_details")} for s in sheets if s.prep_meta.get("beam_details")]),
    "tank_details": TD.gather([{"page_no": s.page_no, "details": s.prep_meta.get("tank_details")} for s in sheets if s.prep_meta.get("tank_details")]),
    "footing_sections": [{**sec, "page_no": s.page_no} for s in sheets for sec in (s.prep_meta.get("footing_sections") or [])],
    "footing_views": [{**v, "page_no": s.page_no} for s in sheets for v in (s.prep_meta.get("footing_views") or [])],
    "column_details": column_details_of([s.prep_meta for s in sheets]),
    "units": UR.drawing_imperial([{"page_no": s.page_no, "units": s.prep_meta.get("units"), "hint": s.prep_meta.get("units_hint")} for s in sheets]),
    "schedule": DS.gather(PSV.PrepService._schedule_sheets(sheets)),
    "opening_labels": OHT.gather(sheets),
  }

def project_of(pairs: list) -> dict:
  sheets, table = stamp(pairs)
  out = gather_all(sheets)
  return {k: unstamp(v, table) for k, v in out.items()}

def _core(value):
  if isinstance(value, list):
    return [_core(v) for v in value]
  if isinstance(value, dict):
    return {k: _core(v) for k, v in value.items() if k not in ("sources", "pages", "page_no", "count", "text")}
  return value

def _unique(sources: list) -> list:
  seen, out = set(), []
  for s in sources:
    key = (str(s["drawing_id"]), s["page_no"])
    if key not in seen:
      seen.add(key)
      out.append(s)
  return out

def _src(item) -> list:
  return list((item or {}).get("sources") or []) if isinstance(item, dict) else []

def _conflict(fact: str, key, own, other) -> dict:
  return {"fact": fact, "key": key, "own": own, "other": other}

def _keyed(own: list, other: list, fact: str, key, differs=None) -> tuple:
  have = {key(x): x for x in own}
  merged, filled, conflicts = list(own), [], []
  for x in other:
    k = key(x)
    if k in have:
      if differs is not None and differs(have[k], x):
        conflicts.append(_conflict(fact, k, have[k], x))
      continue
    have[k] = x
    merged.append(x)
    filled += _src(x)
  return merged, filled, conflicts

def merge(own: dict, other: dict) -> dict:
  facts, filled, conflicts = {}, {}, []
  def put(name, value, src, found=()):
    facts[name] = value
    if src:
      filled[name] = _unique(src)
    conflicts.extend(found)

  own_h, oth_h = own["storey_heights"], other["storey_heights"]
  heights, src, found = dict(own_h), [], []
  for fl, v in oth_h.items():
    if fl not in heights:
      heights[fl] = v
      src += _src(v) or _src(other["gathered"].get("storeys"))
    elif v.get("clear_mm") and heights[fl].get("clear_mm") and abs(float(v["clear_mm"]) - float(heights[fl]["clear_mm"])) > HEIGHT_TOL_MM:
      found.append(_conflict("STOREY_HEIGHT", fl, heights[fl], v))
  put("storey_heights", heights, src, found)

  items, src, found = _keyed(own["slab_values"], other["slab_values"], "SLAB_THICKNESS", lambda x: round(float(x["mm"]), 1))
  if own["slab_values"] and other["slab_values"] and round(float(own["slab_values"][0]["mm"]), 1) != round(float(other["slab_values"][0]["mm"]), 1):
    found.append(_conflict("SLAB_THICKNESS", "most printed", own["slab_values"][0], other["slab_values"][0]))
  put("slab_values", items, src, found)

  spec, src, found = dict(own["spec_facts"]), [], []
  for k, v in other["spec_facts"].items():
    if not spec.get(k) and v:
      spec[k] = v
      src += _src(v) if isinstance(v, dict) else [s for x in v if isinstance(x, dict) for s in _src(x)] if isinstance(v, list) else []
    elif v and spec.get(k) and _core(v) != _core(spec[k]):
      found.append(_conflict("SPEC", k, spec[k], v))
  put("spec_facts", spec, src, found)

  items, src, found = _keyed(own["beam_sections"], other["beam_sections"], "BEAM_SECTION", lambda x: str(x.get("mark")),
    lambda a, b: a.get("depth_mm") and b.get("depth_mm") and abs(float(a["depth_mm"]) - float(b["depth_mm"])) > 1.0)
  put("beam_sections", items, src, found)

  items, src, _ = _keyed(own["tank_details"], other["tank_details"], "TANK", lambda x: (x.get("kind"), x.get("view")))
  put("tank_details", items, src)

  items, src, _ = _keyed(own["footing_sections"], other["footing_sections"], "FOOTING_SECTION", lambda x: (str(x.get("caption")), x.get("wall_in")))
  put("footing_sections", items, src)

  items, src, _ = _keyed(own.get("footing_views") or [], other.get("footing_views") or [], "FOOTING_VIEW", lambda x: str(x.get("mark")),
    lambda a, b: a.get("size_mm") and b.get("size_mm") and a["size_mm"] != b["size_mm"])
  put("footing_views", items, src)

  sched, src, found = dict(own["schedule"]), [], []
  for k, v in other["schedule"].items():
    mine = sched.get(k)
    if isinstance(v, list) and isinstance(mine, list) and v and all(isinstance(x, dict) for x in v + mine):
      if k == "openings":
        sched[k], more, c = _keyed(mine, v, "OPENING_SIZE", lambda x: x.get("mark"), lambda a, b: (a.get("width_mm"), a.get("height_mm")) != (b.get("width_mm"), b.get("height_mm")))
      elif k == "areas":
        sched[k], more, c = _keyed(mine, v, "FLOOR_AREA", lambda x: (x.get("key"), x.get("kind")))
      elif not mine:
        sched[k], more, c = v, [s for x in v for s in _src(x)], []
      else:
        continue
    
      src += more
      found += c
    elif not mine and v:
      sched[k] = v
      src += _src(v) if isinstance(v, dict) else [s for x in v if isinstance(x, dict) for s in _src(x)] if isinstance(v, list) else []
  put("schedule", sched, src, found)

  units, found = own["units"], []
  if units.get("imperial") is None and other["units"].get("imperial") is not None:
    units, src = other["units"], _src(other["units"])
  else:
    src = []
    if other["units"].get("imperial") is not None and units.get("imperial") != other["units"]["imperial"]:
      found.append(_conflict("UNITS", "imperial", units, other["units"]))
  put("units", units, src, found)
  put("opening_labels", OHT.merge(own["opening_labels"], other["opening_labels"]), [])
  cols, found = dict(own["column_details"]), []
  for mark, rec in other["column_details"].items():
    mine = cols.get(mark)
    if mine is None or not mine.get("sizes_in"):
      cols[mark] = rec
    elif rec.get("sizes_in") and rec["sizes_in"] != mine["sizes_in"]:
      found.append(_conflict("COLUMN_DETAIL", mark, mine["sizes_in"], rec["sizes_in"]))
  put("column_details", cols, [], found)
  return {"facts": facts, "filled": filled, "conflicts": conflicts}

def bundle(pairs: list, own_drawing) -> dict:
  drawings = {d for d, _ in pairs}
  own_pairs = [p for p in pairs if p[0] == own_drawing]
  others = [p for p in pairs if p[0] != own_drawing]
  own_sheets, own_table = stamp(own_pairs)
  own = gather_all(own_sheets)
  if not others:
    return {"facts": {k: own[k] for k in FACT_NAMES}, "filled": {}, "conflicts": [], "drawings": len(drawings) or 1, "gathered": own["gathered"]}
  other_sheets, other_table = stamp(others)
  
  merged = merge({k: unstamp(v, own_table) for k, v in own.items()}, {k: unstamp(v, other_table) for k, v in gather_all(other_sheets).items()})
  merged["facts"] = {k: strip_sources(v) for k, v in merged["facts"].items()}
  merged["drawings"] = len(drawings)
  merged["gathered"] = own["gathered"]
  return merged

def summary(bundle: dict) -> dict:
  import json
  def plain(v):
    return json.loads(json.dumps(v, default=str))
  return {"drawings": bundle.get("drawings", 1), "filled": plain(bundle.get("filled") or {}),
    "conflicts": [plain({"fact": c["fact"], "key": c["key"], "own": c["own"], "other": c["other"]}) for c in bundle.get("conflicts") or []]}
