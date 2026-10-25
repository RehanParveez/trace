from __future__ import annotations
import hashlib
from app.engine.measure import readings as QS

STRUCTURAL, ARCHITECTURAL, UNKNOWN = "STRUCTURAL", "ARCHITECTURAL", "UNKNOWN"
POLICIES = ("STRUCTURAL", "ARCHITECTURAL", "LARGER", "SMALLER", "AS_READ", "QS")
SLAB, BEAM, COUNT = "SLAB_THICKNESS", "BEAM_SECTION", "SOURCE_COUNT"
DEFAULT_POLICY = {SLAB: "QS", BEAM: "AS_READ", COUNT: "AS_READ"}
SUBSTANTIVE_MM = 1.0
CHOICE_KEY = "conflict"      
MM = 25.4

def sheet_discipline(title: dict | None) -> str:
  t = title or {}
  if t.get("structural_views"):
    return STRUCTURAL
  return ARCHITECTURAL

def _id(*parts) -> str:
  return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:16]

def _inch(mm) -> str:
  return f"{float(mm) / MM:g}\"" if mm is not None else "?"

def _slab_area_m2(f: dict, p: dict) -> float | None:
  if p.get("length_mm") and p.get("width_mm"):
    return float(p["length_mm"]) * float(p["width_mm"]) / 1e6
  if f.get("gross_area_m2") or f.get("area_m2"):
    return float(f.get("gross_area_m2") or f.get("area_m2"))
  return None

def _disciplines(option: dict, own_page: int | None, own_discipline: str, by_page: dict) -> list:
  out: list = []
  for src in option.get("sources") or []:
    if src == "PLAN_NOTE":
      out.append({"discipline": own_discipline, "page_no": own_page, "basis": src})
    elif src == "SECTIONS":
      out.append({"discipline": ARCHITECTURAL, "page_no": None, "basis": src})
  for pg in option.get("pages") or []:
    out.append({"discipline": by_page.get(pg, UNKNOWN), "page_no": pg, "basis": "OTHER_SHEET" if "SECTION_LABEL" not in (option.get("sources") or []) else "SECTION_LABEL"})
  seen: dict = {}
  
  for o in out:
    k = (o["discipline"], o["page_no"])
    if o["page_no"] is None:
      k = (o["discipline"], None, o["basis"])
    if k not in seen:
      seen[k] = o
    elif o["basis"] not in seen[k]["basis"].split("+"):
      seen[k] = {**seen[k], "basis": seen[k]["basis"] + "+" + o["basis"]}
  merged: list = []
  
  for o in seen.values():
    if o["page_no"] is None:
      twin = next((m for m in seen.values() if m["page_no"] is not None and m["discipline"] == o["discipline"]), None)
      if twin is not None:
        twin["basis"] = twin["basis"] + "+" + o["basis"]
        continue
    merged.append(o)
  return merged

def _pick(values: list, policy: str, used_mm=None) -> int | None:
  if policy == "QS":
    qs = float(QS.convention("slab_thickness_mm"))
    hit = [i for i, v in enumerate(values) if v.get("value_mm") is not None and abs(v["value_mm"] - qs) <= SUBSTANTIVE_MM]
    return hit[0] if len(hit) == 1 else _pick(values, "STRUCTURAL", used_mm)
  if policy == "AS_READ":
    return next((i for i, v in enumerate(values) if used_mm is not None and abs(v["value_mm"] - used_mm) <= SUBSTANTIVE_MM), None)
  if policy in ("STRUCTURAL", "ARCHITECTURAL"):
    hit = [i for i, v in enumerate(values) if any(s["discipline"] == policy for s in v["sources"])]
    other = [i for i, v in enumerate(values) if i not in hit and any(s["discipline"] != policy for s in v["sources"])]
    if len(hit) == 1:
      return hit[0]
    if len(hit) > 1 and not other:
      return None
    return None

  nums = [(i, v["value_mm"]) for i, v in enumerate(values) if v.get("value_mm") is not None]
  if not nums:
    return None
  return (max if policy == "LARGER" else min)(nums, key=lambda t: t[1])[0]

def _finish(c: dict, policy: str, used_mm=None, chosen_mm=None) -> dict:
  vals = c["values"]
  gi = None
  by = None
  
  if chosen_mm is not None:
    gi = next((i for i, v in enumerate(vals) if v.get("value_mm") is not None and abs(v["value_mm"] - chosen_mm) <= SUBSTANTIVE_MM), None)
    by = "CHOSEN" if gi is not None else None
  if gi is None:
    gi = _pick(vals, policy, used_mm)
    by = "POLICY" if gi is not None and policy != "AS_READ" else ("AS_READ" if gi is not None else None)
  base = vals[gi]["quantity"] if gi is not None else (vals[0]["quantity"] if False else None)
  for i, v in enumerate(vals):
    v["governing"] = i == gi
    v["delta"] = round(v["quantity"] - base, 4) if base is not None and v["quantity"] is not None else None
    v["delta_pct"] = round((v["quantity"] - base) / base * 100.0, 1) if base and v["quantity"] is not None else None
    
  qs = [v["quantity"] for v in vals if v["quantity"] is not None]
  c.update({"governing_index": gi, "governing_by": by, "policy": policy, "spread": round(max(qs) - min(qs), 4) if len(qs) > 1 else 0.0,
    "spread_pct": round((max(qs) - min(qs)) / max(qs) * 100.0, 1) if len(qs) > 1 and max(qs) else 0.0})
  return c

def slab_conflicts(rows: list, sheets: dict, policy: str) -> list:
  by_page = {s["page_no"]: s["discipline"] for s in sheets.values()}
  out = []
  
  for r in rows:
    f, p = r.facts or {}, r.params or {}
    opts = f.get("thickness_options") or []
    if r.category != "SLAB" or len({round(o["mm"] / SUBSTANTIVE_MM) for o in opts}) < 2:
      continue
    sh = sheets.get(r.sheet_id) or {}
    area = _slab_area_m2(f, p)
    used = p.get("depth_mm")
    values = []
    
    for o in sorted(opts, key=lambda o: o["mm"]):
      src = _disciplines(o, sh.get("page_no"), sh.get("discipline", STRUCTURAL), by_page)
      values.append({"value_mm": float(o["mm"]), "label": _inch(o["mm"]), "sources": src, "quantity": round(area * float(o["mm"]) / 1000.0, 4) if area else None})
    chosen = ((f.get(CHOICE_KEY) or {}).get("value") if (f.get(CHOICE_KEY) or {}).get("kind") == SLAB else None)
    c = {"id": _id(SLAB, r.id), "kind": SLAB, "subject": f"Slab · {f.get('floor') or ''}".strip(" ·"), "floor": f.get("floor"), "attribute": "thickness", "unit": "m³",
      "item_ids": [str(r.id)], "decision": r.decision, "used_mm": used, "page_no": sh.get("page_no"), "values": values}
    out.append(_finish(c, policy, used, chosen if chosen is not None else None))
  return out

def beam_conflicts(rows: list, sections: list, policy: str) -> list:
  out = []
  for r in rows:
    f, p = r.facts or {}, r.params or {}
    opts = [o for o in f.get("section_options") or [] if o.get("depth_mm")]
    assumed = bool(f.get("section_assumed")) and bool(p.get("depth_mm"))
    if r.category != "BEAM" or len(opts) < 2 or (p.get("depth_mm") and not assumed):
      continue
  
    L, W = p.get("length_mm"), p.get("width_mm")
    values = []
    
    for o in sorted(opts, key=lambda o: o["depth_mm"]):
      q = round(float(L) * float(W) * float(o["depth_mm"]) / 1e9, 4) if L and W else None
      values.append({"value_mm": float(o["depth_mm"]), "label": f"{o['mark']} · {_inch(o['depth_mm'])} deep", "mark": o["mark"], "sources": [{"discipline": STRUCTURAL, "page_no": None, "basis": "DETAIL"}],
        "steel_text": o.get("steel_text"), "quantity": q})
    chosen = ((f.get(CHOICE_KEY) or {}).get("value") if (f.get(CHOICE_KEY) or {}).get("kind") == BEAM else None)
    c = {"id": _id(BEAM, r.id), "kind": BEAM, "subject": f"{r.tag or 'Beam'}" + (f" · {f.get('level_hint')}" if f.get("level_hint") else ""), "floor": f.get("level_hint"), "attribute": "depth",
      "unit": "m³", "item_ids": [str(r.id)], "decision": r.decision, "used_mm": float(p["depth_mm"]) if assumed else None, "page_no": None, "values": values}
    out.append(_finish(c, policy if policy in ("LARGER", "SMALLER") else "AS_READ", float(p["depth_mm"]) if assumed else None, chosen))
  return out

def count_conflicts(rows: list, sheets: dict, policy: str = "AS_READ") -> list:
  out = []
  
  for r in rows:
    fu = (r.facts or {}).get("floor_union") or {}
    if fu.get("role") != "SAME" or fu.get("other_count") is None or r.category == "LINTEL":
      continue
    mine, other = int(r.count or 1), int(fu["other_count"])
    if mine == other:
      continue
    sh = sheets.get(r.sheet_id) or {}
    
    values = [
      {"value_mm": None, "label": f"page {sh.get('page_no')}: {mine}", "sources": [{"discipline": sh.get("discipline", ARCHITECTURAL), "page_no": sh.get("page_no"), "basis": "FLOOR_PLAN"}], "quantity": float(mine), "count": mine},
      {"value_mm": None, "label": f"page {fu.get('other_page')}: {other}", "sources": [{"discipline": ARCHITECTURAL, "page_no": fu.get("other_page"), "basis": "ALL_PLANS_SHEET"}], "quantity": float(other), "count": other}]
    chosen = (r.facts or {}).get(CHOICE_KEY) or {}
    c = {"id": _id(COUNT, r.id), "kind": COUNT, "subject": f"{r.tag or r.category} · {(r.facts or {}).get('floor') or fu.get('floor') or ''}".strip(" ·"), "floor": fu.get("floor"),
      "attribute": "count", "unit": "nos", "item_ids": [str(r.id)], "decision": r.decision, "used_mm": None, "page_no": sh.get("page_no"), "values": values}
    _finish(c, "AS_READ", None, None)
    gi = 0 if chosen.get("kind") != COUNT else next((i for i, v in enumerate(values) if v["count"] == chosen.get("value")), 0)
    by = "CHOSEN" if chosen.get("kind") == COUNT else "AS_READ"
    if by == "AS_READ" and policy in ("LARGER", "SMALLER"):
      gi, by = (max if policy == "LARGER" else min)(range(len(values)), key=lambda i: values[i]["count"]), "POLICY"
    c["governing_index"], c["governing_by"] = gi, by
    base = values[gi]["quantity"]
    
    for i, v in enumerate(values):
      v["governing"] = i == gi
      v["delta"] = v["quantity"] - base
      v["delta_pct"] = round((v["quantity"] - base) / base * 100.0, 1) if base else None
    out.append(c)
  return out

def build(rows: list, sheets: dict, sections: list | None = None, policy: dict | None = None) -> dict:
  """-> {"conflicts": [...], "policy": {kind: policy}, "undecided": n, "by_kind": {...}}. policy: {kind: STRUCTURAL | ARCHITECTURAL | LARGER | SMALLER | AS_READ}."""
  pol = {**DEFAULT_POLICY, **{k: v for k, v in (policy or {}).items() if v in POLICIES}}
  live = [r for r in rows if r.decision != "REJECTED"]
  found = [*slab_conflicts(live, sheets, pol[SLAB]), *beam_conflicts(live, sections or [], pol[BEAM]), *count_conflicts(live, sheets, pol[COUNT])]
  by_kind: dict = {}
  for c in found:
    by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + 1
  return {"conflicts": found, "policy": pol, "defaults": dict(DEFAULT_POLICY), "by_kind": by_kind, "undecided": sum(1 for c in found if c["governing_index"] is None)}

def resolutions(conflicts: list, choices: dict | None = None, use_policy: bool = True) -> list:
  out = []
  
  for c in conflicts:
    pick = (choices or {}).get(c["id"])
    vals = c["values"]
    
    if pick is not None:
      v = next((v for v in vals if (v.get("value_mm") is not None and abs(v["value_mm"] - float(pick)) <= SUBSTANTIVE_MM) or (v.get("count") is not None and v["count"] == pick)), None)
      by = "CHOSEN"
    elif use_policy and c["governing_by"] == "POLICY" and c["governing_index"] is not None:
      v, by = vals[c["governing_index"]], "POLICY"
    else:
      continue
    if v is None or c["decision"] == "ACCEPTED":
      continue
    rec = {"conflict_id": c["id"], "item_ids": c["item_ids"], "kind": c["kind"], "by": by, "policy": c.get("policy")}
    if c["kind"] == COUNT:
      rec["count"] = v["count"]
    else:
      rec["value_mm"] = v["value_mm"]
      if v.get("mark"):
        rec["mark"] = v["mark"]
    out.append(rec)
  return out

def apply_to_row(row, res: dict, section: dict | None = None) -> bool:
  if row.decision != "NEW":
    return False
  f, p = dict(row.facts or {}), dict(row.params or {})
  src = "CHOSEN" if res["by"] == "CHOSEN" else "POLICY"
  if res["kind"] == SLAB:
    mm = float(res["value_mm"])
    p["depth_mm"] = mm
    f["thickness_mm"], f["thickness_source"] = mm, src
    area = _slab_area_m2(f, p)
    if p.get("length_mm") and p.get("width_mm"):
      f["volume_m3"] = round(float(p["length_mm"]) * float(p["width_mm"]) * mm / 1e9, 4)
      
    elif area:
      f["volume_m3"] = round(area * mm / 1000.0, 4)
    row.missing = [m for m in (row.missing or []) if m not in ("thickness_mm", "depth_mm")]
  elif res["kind"] == BEAM:
    mm = float(res["value_mm"])
    p["depth_mm"] = mm
    f["section_mark"] = res.get("mark")
    f.pop("section_assumed", None)
    if section and section.get("steel"):
      p["steel"] = dict(section["steel"])
      f["steel_text"] = section.get("steel_text")
      f["steel_source"] = {"grade": "PRINTED" if res["by"] == "CHOSEN" else "ASSUMED", "text": f"beam section {res.get('mark')}"}
    row.missing = [m for m in (row.missing or []) if m != "depth_mm"]
    
  elif res["kind"] == COUNT:
    row.count = int(res["count"])
  else:
    return False
  rec = {"kind": res["kind"], "value": res.get("value_mm") if res.get("value_mm") is not None else res.get("count"), "by": res["by"], "policy": res.get("policy")}
  if res["kind"] == BEAM:
    rec["mark"] = res.get("mark")
    if section and section.get("steel"):
      rec["steel"], rec["steel_text"] = dict(section["steel"]), section.get("steel_text")
  f[CHOICE_KEY] = rec
  row.params, row.facts = p, f
  return True

def reapply(row, chosen: dict | None) -> bool:
  if not chosen or chosen.get("by") != "CHOSEN" or chosen.get("value") is None:
    return False
  f, kind, value = row.facts or {}, chosen.get("kind"), chosen["value"]
  res = {"kind": kind, "by": "CHOSEN", "policy": chosen.get("policy")}
  section = None
  
  if kind == SLAB:
    if not any(abs(float(o["mm"]) - float(value)) <= SUBSTANTIVE_MM for o in f.get("thickness_options") or []):
      return False
    res["value_mm"] = float(value)
  elif kind == BEAM:
    if not any(o.get("mark") == chosen.get("mark") and o.get("depth_mm") and abs(float(o["depth_mm"]) - float(value)) <= SUBSTANTIVE_MM for o in f.get("section_options") or []):
      return False
    res["value_mm"], res["mark"] = float(value), chosen.get("mark")
    if chosen.get("steel"):
      section = {"steel": chosen["steel"], "steel_text": chosen.get("steel_text")}
  elif kind == COUNT:
    res["count"] = int(value)
  else:
    return False
  return apply_to_row(row, res, section)
