from __future__ import annotations
import re
from app.engine.measure import grades as GRD

FLOOR_LAYERS = ("pcc", "brick ballast", "sand filling")   
STRUCTURAL = ("COLUMN", "BEAM", "SLAB", "FOOTING", "LINTEL", "STAIR")
MEMBER_WORDS = {"COLUMN": ("column",), "BEAM": ("beam", "girder"), "SLAB": ("slab", "roof"), "FOOTING": ("footing", "foundation", "raft"), "LINTEL": ("lintel",),
  "STAIR": ("stair", "staircase")}
GENERIC_WORDS = ("all", "structural", "rcc", "r c c", "reinforced")
RING_MEMBERS = ("BEAM", "COLUMN", "LINTEL")
PLASTER_ITEMS = ("PLASTER_INSIDE", "PLASTER_OUTSIDE", "CEILING_PLASTER")
PCC_BED_ITEMS = ("PCC_STRIP", "PCC_PAD")
ROOF_HEADINGS = ("TERRACE", "ROOF", "PORCH_ROOF", "MUMTY")

def _pick(rows: list[dict], key) -> tuple:
  by: dict = {}
  
  for r in rows:
    k = key(r)
    row = by.setdefault(k, {**r, "count": 0, "pages": set()})
    row["count"] += int(r.get("count", 1))
    row["pages"].update(r.get("pages") or [])
  ranked = sorted(by.values(), key=lambda r: (-r["count"], str(key(r))))
  ranked = [{**r, "pages": sorted(r["pages"])} for r in ranked]
  if not ranked:
    return None, [], False
  if len(ranked) > 1 and ranked[0]["count"] == ranked[1]["count"]:
    return None, ranked, True
  return ranked[0], ranked[1:], False

def members_of(scope: str | None) -> tuple:
  words = re.sub(r"[^a-z ]+", " ", (scope or "").lower())
  words = re.sub(r"\b[a-z]+\s+(?:stirrups?|ties|links?)\b", " ", words)      
  named = tuple(cat for cat, keys in MEMBER_WORDS.items() if any(re.search(rf"\b{k}s?\b", words) for k in keys))
  generic = any(re.search(rf"\b{g}\b", words) for g in GENERIC_WORDS)
  return named, generic

def ring_members_of(scope: str | None) -> tuple:
  named: list = []
  generic = False
  for text in GRD.steel_clauses(scope)["RING"]:
    cats, gen = members_of(text)
    named.extend(c for c in cats if c not in named)
    generic = generic or gen or not text.strip()
  return tuple(named), generic

def _layer_table(items: list) -> tuple:
  layers, ambiguous = {}, []
  for name in sorted({i.get("layer") for i in items if i.get("kind") == "BUILD_UP_LAYER" and i.get("layer")}):
    rows = [i for i in items if i.get("kind") == "BUILD_UP_LAYER" and i.get("layer") == name]
    best, others, tie = _pick(rows, lambda r: (r.get("value_mm"), r.get("mix")))
    if tie:
      ambiguous.append({"layer": name, "values": [{"value_mm": o["value_mm"], "mix": o.get("mix"), "count": o["count"]} for o in others]})
    elif best:
      layers[name] = {"value_mm": best["value_mm"], "mix": best.get("mix"), "count": best["count"], "pages": best["pages"],
        "others": [{"value_mm": o["value_mm"], "mix": o.get("mix"), "count": o["count"]} for o in others], "text": best.get("text")}
  return layers, ambiguous

def _waterproof_rows(items: list) -> list:
  wp: dict = {}
  
  for i in items:
    if i.get("kind") == "WATERPROOF_LAYER":
      row = wp.setdefault(i.get("material"), {"material": i.get("material"), "layers": 0, "unit": i.get("unit"), "pages": set(), "options": set()})
      row["options"].add(int(i.get("value") or 0))
      row["pages"].update(i.get("pages") or [])
  out = []
  for row in wp.values():
    opts = sorted(row["options"])
    out.append({"material": row["material"], "unit": row["unit"], "layers": opts[0] if len(opts) == 1 else None, "options": opts, "pages": sorted(row["pages"])})
  return out

def _fall(items: list) -> dict | None:
  rows = [i for i in items if i.get("kind") == "ROOF_FALL"]
  best, others, tie = _pick(rows, lambda r: (r.get("min_mm"), r.get("max_mm")))
  if tie or not best:
    return None
  return {"min_mm": best["min_mm"], "max_mm": best["max_mm"], "avg_mm": best["value_mm"], "count": best["count"], "pages": best["pages"], "text": best.get("text")}

def _by_heading(items: list) -> dict:
  heads: dict = {}
  
  for i in items:
    if i.get("under"):
      heads.setdefault(i["under"], {"heading": i.get("heading") or i["under"], "items": []})["items"].append(i)
  out: dict = {}
  for key, h in heads.items():
    layers, ambiguous = _layer_table(h["items"])
    out[key] = {"key": key, "heading": h["heading"], "layers": layers, "layers_ambiguous": ambiguous, "waterproof": _waterproof_rows(h["items"]), "fall": _fall(h["items"]),
      "pages": sorted({p for i in h["items"] for p in i.get("pages") or []})}
  return out

def build(items: list) -> dict:
  items = items or []
  loose = [i for i in items if not i.get("under")]
  layers, ambiguous = _layer_table(loose)
  
  bed_rows = [i for i in items if i.get("kind") in ("PCC_THICKNESS", "PCC_PROJECTION") and i.get("scope") == "pcc bed" and i.get("mix")]
  bed, bed_others, bed_tie = _pick(bed_rows, lambda r: r["mix"])
  plaster_rows = [i for i in items if i.get("kind") == "PLASTER_THICKNESS" and i.get("scope") == "cement mortar plaster" and i.get("mix")]
  plaster, plaster_others, plaster_tie = _pick(plaster_rows, lambda r: r["mix"])
  concrete = [{"class": i.get("concrete_class"), "mix": i.get("mix"), "scope": i.get("scope"), "members": members_of(i.get("scope"))[0], "generic": members_of(i.get("scope"))[1],
    "pages": i.get("pages") or [], "text": i.get("text")} for i in items if i.get("kind") == "CONCRETE_CLASS"]
  steel = [{"grade": i.get("grade"), "scope": i.get("scope"), "members": members_of(i.get("scope"))[0], "generic": members_of(i.get("scope"))[1],
    "ring_members": ring_members_of(i.get("scope"))[0], "ring_generic": ring_members_of(i.get("scope"))[1],
    "pages": i.get("pages") or [], "text": i.get("text")} for i in items if i.get("kind") == "STEEL_GRADE"]
  
  waterproof = _waterproof_rows(loose)
  return {"layers": layers, "layers_ambiguous": ambiguous, "by_heading": _by_heading(items),
    "pcc_bed": ({"mix": bed["mix"], "count": bed["count"], "pages": bed["pages"]} if bed else None), "pcc_bed_ambiguous": bed_tie,
    "plaster": ({"mix": plaster["mix"], "thickness_mm": plaster.get("value_mm"), "count": plaster["count"], "pages": plaster["pages"]} if plaster else None), "plaster_ambiguous": plaster_tie,
    "concrete": concrete, "steel": steel, "waterproof": waterproof}

def floor_set(spec: dict | None, level_hint: str | None) -> dict | None:
  key = str(level_hint or "").upper()
  head = ((spec or {}).get("by_heading") or {}).get(key)
  return head if head and key not in ROOF_HEADINGS else None

def roof_sets(spec: dict | None) -> list:
  heads = (spec or {}).get("by_heading") or {}
  out: list = []
  for key in ROOF_HEADINGS:
    head = heads.get(key)
    if not head or not (head["layers"] or head["waterproof"] or head.get("fall")):
      continue
    layers = [{"layer": n, "value_mm": v["value_mm"], "mix": v.get("mix"), "count": v["count"], "pages": v["pages"]} for n, v in sorted(head["layers"].items())]
    out.append({"key": key, "heading": head["heading"], "layers": layers, "ambiguous": head["layers_ambiguous"], "waterproof": head["waterproof"], "fall": head.get("fall"), "pages": head["pages"]})
  return out

def waterproof_for(spec: dict | None, level_hint: str | None) -> list:
  head = floor_set(spec, level_hint)
  if head is not None:
    return [{**r, "heading": head["heading"]} for r in head["waterproof"]]
  return [dict(r) for r in (spec or {}).get("waterproof") or []]

def _rows_for(rows: list, category: str) -> list:
  named = [r for r in rows if category in r["members"]]
  return named if named else [r for r in rows if r["generic"] and not r["members"]]

def concrete_for(spec: dict, category: str) -> tuple:
  rows = _rows_for((spec or {}).get("concrete") or [], category)
  mixes = sorted({r["mix"] for r in rows if r.get("mix")})
  if len(mixes) == 1:
    return mixes[0], rows, False
  return None, rows, len(mixes) > 1

def steel_for(spec: dict, category: str, part: str | None = None) -> list:
  rows = (spec or {}).get("steel") or []
  if part == "RING":
    named = [r for r in rows if category in (r.get("ring_members") or ())]
    chosen = named if named else [r for r in rows if r.get("ring_generic") and not r.get("ring_members")]
    return sorted({int(r["grade"]) for r in chosen if r.get("grade")})
  return sorted({int(r["grade"]) for r in _rows_for(rows, category) if r.get("grade")})

def annotate(cands: list, spec: dict | None, note) -> dict:
  stats = {"graded": 0, "conflicts": 0, "steel_noted": 0, "ring_noted": 0}
  if not spec:
    return stats
  for c in cands:
      
    facts = c.facts if isinstance(getattr(c, "facts", None), dict) else None
    if facts is None or facts.get("spec_grade"):
      continue
  
    item = facts.get("foundation_item")
    grade = what = pages = None
    if item in PLASTER_ITEMS and spec.get("plaster"):
      grade, what, pages = spec["plaster"]["mix"], "plaster mortar", spec["plaster"]["pages"]
    elif item in PCC_BED_ITEMS and spec.get("pcc_bed"):
      grade, what, pages = spec["pcc_bed"]["mix"], "plain concrete bed", spec["pcc_bed"]["pages"]
    elif not item and c.category in STRUCTURAL:
      mix, rows, conflict = concrete_for(spec, c.category)
      if conflict:
        stats["conflicts"] += 1
        c.notes.append(note("SPEC_GRADE_CONFLICT", member=c.category.lower(), mixes=sorted({r["mix"] for r in rows if r.get("mix")})))
      elif mix:
        grade, what, pages = mix, "concrete", sorted({p for r in rows for p in r["pages"]})
      steel = steel_for(spec, c.category)
      if steel:
        facts["spec_steel_grade"] = steel
        stats["steel_noted"] += 1
      ring = steel_for(spec, c.category, "RING") if c.category in RING_MEMBERS else []
      if ring:
        facts["spec_steel_ring_grade"] = ring
        stats["ring_noted"] += 1
        
    if grade:
      facts["spec_grade"] = {"grade": grade, "what": what, "pages": pages}
      c.notes.append(note("SPEC_GRADE_PRINTED", grade=grade, what=what, pages=pages))
      stats["graded"] += 1
  return stats
