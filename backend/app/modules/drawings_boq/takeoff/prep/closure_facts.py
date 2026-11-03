from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.prep import facts as F
from app.modules.drawings_boq.takeoff.prep import general_notes as GN
from app.modules.drawings_boq.takeoff.prep import spec_blocks as SB

MM_INCH = 25.4
MM_FOOT = 304.8
ANGLES = (0, 90, 180, 270)
SPEC_KEYS = ("GROUND", "FIRST", "TERRACE", "ROOF", "PORCH_ROOF")
ROOF_KEYS = ("TERRACE", "ROOF", "PORCH_ROOF")
ROW_TOL = 0.5

_MIX = r"(?P<{n}>\d(?:\.\d)?\s*:\s*\d(?:\.\d)?(?:\s*:\s*\d(?:\.\d)?)?)"
_SCALE = re.compile(r"DO\s+NOT\s+SCALE", re.I)
_TERMITE = re.compile(r"TERMITE", re.I)
_BEDS = re.compile(r"\bBEDS?\b", re.I)
_SIDES = re.compile(r"SIDE\s+SLOPES?", re.I)
_PLASTER_MIX = re.compile(r"PLASTERED\s+WITH\s+" + _MIX.format(n="a") + r"\s+(?:CEMENT\s+SAND|C\s*/\s*S)\s+MORTAR\s+FOR\s+(?P<fa>INTERNAL|EXTERNAL)\s+FACE\s+AND\s+" + _MIX.format(n="b") + r"\s+FOR\s+(?P<fb>INTERNAL|EXTERNAL)", re.I)
_MORTAR_MIX = re.compile(r"LAID\s+IN\s+" + _MIX.format(n="a") + r"\s+(?:CEMENT\s+SAND|C\s*/\s*S)\s+MORTAR\s+FOR\s+(?P<ta>\d(?:\s*1/2)?)\s+INCH\s+THICK\s+WALL\s+AND\s+" + _MIX.format(n="b")
  + r"\s+(?:CEMENT\s+SAND|C\s*/\s*S)\s+MORTAR\s+FOR\s+(?P<tb>\d(?:\s*1/2)?)\s+INCH", re.I)
_SLAB_NOTE = re.compile(r"SLAB\s+THICKNESS\s*=\s*(?P<in>\d{1,2}(?:\s+\d/\d)?)\s*(?:\"|″|”|'')", re.I)
_DPC_SPEC = re.compile(r"(?P<in>\d{1,2})\s*(?:\"|″|”|'')\s*THICK\s*\(\s*(?P<mix>\d\s*:\s*\d(?:\s+1/2)?\s*(?:\"|″|”|'')?\s*:\s*\d)\s*\)", re.I)
_PUDLO = re.compile(r"(?P<pct>\d{1,2})\s*%\s*PU[D]{1,2}LO", re.I)
_VERTICAL_DPC = re.compile(r"VERTICAL\s+D\.?\s?P\.?\s?C", re.I)
_BITUMEN = re.compile(r"\b(?P<n>ONE|TWO|THREE|[1-3])\s+COATS?\s+OF\s+HOT\s+BITUMEN", re.I)
_V_MIX = re.compile(r"PLASTER\s+WITH\s+" + _MIX.format(n="mix") + r"\s+C\s*/\s*S", re.I)
_OUTSIDE = re.compile(r"OUT\s*SIDE\s+LEVEL", re.I)
_INSIDE = re.compile(r"F\.?\s?F\.?\s?L\.?\s*INSIDE\s+LEVEL", re.I)
_SILL = re.compile(r"WINDOW\s+SILL\s+DETAIL\s*-?\s*(?P<mark>[A-Z])\b", re.I)
_SILL_MATERIAL = re.compile(r"MARBLE|GRANITE", re.I)
_LINTEL_ROW = re.compile(r"(?P<mark>L\d)\s*\(\s*UP\s*TO\s*(?P<ft>\d{1,2})\s*(?:'|’|′)?\s*SPAN\s*\)", re.I)
_COUNT = {"ONE": 1, "TWO": 2, "THREE": 3, "1": 1, "2": 2, "3": 3}
_AREA = re.compile(r"^\s*AREA\s*=\s*(?P<v>\d{3,5}(?:\.\d+)?)\s*(?:SFT|SQ\.?\s*FT)\b", re.I)
_PLAN_TITLE = re.compile(r"\b(?P<f>BASEMENT|GROUND|FIRST|SECOND|THIRD|MEZZANINE|ROOF|TERRACE)\s+FLOOR\s+PLAN\b", re.I)

def _mix_text(raw: str) -> str:
  s = F._fix(raw)
  s = re.sub(r"(?<=\d)\s+1/2", ".5", s)
  return re.sub(r"[\s\"″”']+", "", s)

def _item(kind: str, text: str, **extra) -> dict:
  return {"kind": kind, "text": re.sub(r"\s+", " ", text).strip()[:200], **extra}

def _note_entries(words: list) -> list:
  out: list = []
  for angle in ANGLES:
    ws = words if angle == 0 else GN._upright(words or [], angle)
    cols = GN.read_columns(ws)
    if cols:
      out.extend(GN.entries(cols))
  return out

def _rows_text(words: list) -> list:
  out: list = []
  for angle in ANGLES:
    ws = [w for w in (words if angle == 0 else GN._upright(words or [], angle)) if w.text.strip()]
    if not ws:
      continue
    ordered = sorted(ws, key=lambda w: (-w.cy, w.x0))
    rows: list = []
    for w in ordered:
      if rows and abs(rows[-1]["cy"] - w.cy) <= ROW_TOL * max(float(w.size), rows[-1]["size"]):
        rows[-1]["words"].append(w)
        rows[-1]["size"] = max(rows[-1]["size"], float(w.size))
      else:
        rows.append({"cy": w.cy, "size": float(w.size), "words": [w]})
    for r in rows:
      r["words"].sort(key=lambda w: w.x0)
      out.append(" ".join(w.text for w in r["words"]))
  return out

def _note_items(entries: list) -> list:
  out: list = []
  for e in entries:
    text = F._fix(e["text"])
    if _SCALE.search(text):
      out.append(_item("DO_NOT_SCALE", text))
    if _TERMITE.search(text):
      tail = text[_TERMITE.search(text).start():]
      if _BEDS.search(tail) or _SIDES.search(tail):
        out.append(_item("TERMITE_NOTE", tail, beds=bool(_BEDS.search(tail)), side_slopes=bool(_SIDES.search(tail))))
    m = _PLASTER_MIX.search(text)
    if m:
      mixes = {m.group("fa").upper(): _mix_text(m.group("a")), m.group("fb").upper(): _mix_text(m.group("b"))}
      if len(mixes) == 2:
        out.append(_item("PLASTER_MIX", m.group(0), internal=mixes["INTERNAL"], external=mixes["EXTERNAL"]))
    m = _MORTAR_MIX.search(text)
    if m:
      thick = {re.sub(r"\s+", "", F._fix(m.group("ta"))).replace("1/2", ".5"): _mix_text(m.group("a")), re.sub(r"\s+", "", F._fix(m.group("tb"))).replace("1/2", ".5"): _mix_text(m.group("b"))}
      out.append(_item("MORTAR_MIX", m.group(0), by_wall_in={k: v for k, v in thick.items()}))
    m = _SLAB_NOTE.search(text)
    if m and F.inches_mm(m.group("in")):
      out.append(_item("SLAB_NOTE", m.group(0), value_mm=F.inches_mm(m.group("in"))))
      
  return out

def _line_items(rows: list) -> list:
  out: list = []
  joined = " ".join(F._fix(r) for r in rows)
  for i, r in enumerate(rows):
    t = F._fix(r)
    m = _AREA.match(t)
    if m:
      title = next((_PLAN_TITLE.search(F._fix(p)) for p in rows[max(0, i - 2):i][::-1] if _PLAN_TITLE.search(F._fix(p))), None)
      if title:
        out.append(_item("COVERED_AREA", f"{title.group(0)} {t}", floor=title.group("f").upper(), value_sft=float(m.group("v"))))
    m = _SLAB_NOTE.search(t)
    if m and F.inches_mm(m.group("in")):
      out.append(_item("SLAB_NOTE", m.group(0), value_mm=F.inches_mm(m.group("in"))))
    m = _DPC_SPEC.search(t)
    if m and F.inches_mm(m.group("in")):
      out.append(_item("DPC_SPEC", t, thickness_mm=F.inches_mm(m.group("in")), mix=_mix_text(m.group("mix"))))
    m = _PUDLO.search(t)
    if m:
      out.append(_item("DPC_ADMIXTURE", t, pudlo_pct=float(m.group("pct"))))
    m = _SILL.search(t)
    if m:
      out.append(_item("SILL_DETAIL", t, mark=m.group("mark").upper()))
  if _VERTICAL_DPC.search(joined):
    v = _V_MIX.search(joined)
    b = _BITUMEN.search(joined)
    out.append(_item("VERTICAL_DPC", joined[_VERTICAL_DPC.search(joined).start():][:160], plaster_mix=_mix_text(v.group("mix")) if v else None, bitumen_coats=_COUNT[b.group("n").upper()] if b else None,
      from_outside_level=bool(_OUTSIDE.search(joined)), to_inside_ffl=bool(_INSIDE.search(joined))))
  if any(_SILL_MATERIAL.search(F._fix(r)) for r in rows) and any(_SILL.search(F._fix(r)) for r in rows):
    out.append(_item("SILL_MATERIAL", "marble or granite sill", material="marble/granite"))
  return out

def _lintel_marks(rows: list) -> list:
  seen: dict = {}
  for r in rows:
    for m in _LINTEL_ROW.finditer(F._fix(r)):
      seen.setdefault(m.group("mark").upper(), float(m.group("ft")))
  return [_item("LINTEL_SPAN", f"{k} up to {v:g} ft", mark=k, max_span_ft=v) for k, v in sorted(seen.items())]

def read(lines: list, words: list | None) -> dict:
  if not words:
    return {"items": [], "blocks": []}
  rows = _rows_text(words)
  items = _note_items(_note_entries(words)) + _line_items(rows) + _lintel_marks(rows)
  found = SB.read(words)
  blocks = [{"key": b["key"], "heading": b["heading"], "entries": [e if isinstance(e, str) else e.get("text", "") for e in b["entries"]]} for b in found["blocks"]]
  seen: set = set()
  out: list = []
  
  for it in items:
    key = tuple(sorted((k, str(v)) for k, v in it.items() if k != "text"))
    if key not in seen:
      seen.add(key)
      out.append(it)
  return {"items": out, "blocks": blocks}

def of_sheet(sh: dict) -> dict:
  return (sh.get("meta") or {}).get("closure") or {"items": [], "blocks": []}

def items(read_: list, kind: str) -> list:
  return [(sh["page_no"], it) for sh in read_ for it in of_sheet(sh).get("items") or [] if it.get("kind") == kind]

def fact_items(read_: list, kind: str) -> list:
  return [(sh["page_no"], it) for sh in read_ for it in ((sh.get("meta") or {}).get("facts") or {}).get("items") or [] if it.get("kind") == kind]

def blocks(read_: list) -> dict:
  out: dict = {}
  for sh in read_:
    for b in of_sheet(sh).get("blocks") or []:
      out.setdefault(b["key"], {"page_no": sh["page_no"], "heading": b["heading"], "entries": b["entries"]})
  return out

def sections(read_: list) -> list:
  return [(sh["page_no"], rec) for sh in read_ for rec in ((sh.get("meta") or {}).get("footing_sections") or []) if rec.get("read") == "OK"]

def wall_footing(read_: list, mark: str) -> dict | None:
  mark = str(mark).upper()
  hits = [(p, r) for p, r in sections(read_) if str(r.get("mark") or "").upper() == mark and r.get("steps")]
  if not hits:
    return None
  page, rec = hits[0]
  
  dpc = [it for p, it in items(read_, "DPC_SPEC") if p == page]
  admix = [it for p, it in items(read_, "DPC_ADMIXTURE") if p == page]
  pcc = [it for p, it in fact_items(read_, "PCC_THICKNESS") if p == page and it.get("mix")]
  out = {"mark": mark, "page": page, "wall_in": rec.get("wall_in"), "exterior": bool(rec.get("exterior")),
    "trench_width_in": round(float(rec["base_width_mm"]) / MM_INCH, 2) if rec.get("base_width_mm") else None,
    "depth_below_ngl_in": round(float(rec["depth_mm"]) / MM_INCH, 2) if rec.get("depth_mm") else None,
    "pcc_in": round(float(rec["pcc_mm"]) / MM_INCH, 2) if rec.get("pcc_mm") else None, "sand_in": round(float(rec["sand_mm"]) / MM_INCH, 2) if rec.get("sand_mm") else None,
    "pcc_mix": pcc[0]["mix"] if pcc else None, "steps": [{"width_in": s["width_in"], "height_in": s["height_in"]} for s in rec["steps"]],
    "dpc_in": round(float(dpc[0]["thickness_mm"]) / MM_INCH, 2) if dpc else None, "dpc_mix": dpc[0]["mix"] if dpc else None, "dpc_pudlo_pct": admix[0]["pudlo_pct"] if admix else None}
  return out

def section_marks(read_: list) -> list:
  every = fact_items(read_, "ROOF_LEVEL")
  sect = [(p, it) for p, it in every if it.get("where") == "SECTION"]
  return sect or every

def level_conflicts(read_: list) -> list:
  sect = {(it["scope"], round(it["value_mm"], 1)) for _p, it in section_marks(read_)}
  top = {sc: max(v for s, v in sect if s == sc) for sc in {s for s, _v in sect}}
  out: list = []
  
  for p, it in fact_items(read_, "ROOF_LEVEL"):
    if it.get("where") == "SECTION":
      continue
    v, sc = round(it["value_mm"], 1), it["scope"]
    if sc in top and v > top[sc] and (sc, v) not in sect:
      out.append({"name": f"{sc.lower()} top", "section_mm": top[sc], "other_mm": v, "page": p, "text": it["text"]})
  return out

def level_names(read_: list) -> dict:
  out: dict = {"road_mm": 0.0}
  plan = sorted(((sh["page_no"], ((sh.get("meta") or {}).get("facts") or {}).get("plan_levels") or {}) for sh in read_), key=lambda x: x[0])
  floors = [(p, pl["floor"]) for p, pl in plan if pl.get("floor")]
  floors.sort(key=lambda x: x[1]["level_mm"])
  for (p, fl), name in zip(floors, ("ground_mm", "first_mm")):
    out[name] = fl["level_mm"]
    out[name.replace("_mm", "_page")] = p
  for p, pl in plan:
    if pl.get("floor") and pl.get("other_levels_mm") and pl["floor"]["level_mm"] == out.get("ground_mm"):
      lower = [v for v in pl["other_levels_mm"] if v < pl["floor"]["level_mm"]]
      if lower:
        out["porch_mm"] = min(lower)
        
  marks = section_marks(read_)
  floor_marks = sorted({round(it["value_mm"], 1) for _p, it in marks if it.get("scope") == "FLOOR" and it["value_mm"] > 0})
  parapets = sorted({round(it["value_mm"], 1) for _p, it in marks if it.get("scope") == "PARAPET"})
  rest = [v for v in floor_marks if v not in (out.get("ground_mm"), out.get("first_mm"), out.get("porch_mm"))]
  
  if rest:
    out["roof_mm"] = max(rest)
    mid = [v for v in rest if v != out["roof_mm"]]
    if mid:
      out["terrace_mm"] = mid[0]
  if len(parapets) >= 2:
    out["parapet_level_mm"], out["parapet_top_mm"] = parapets[0], parapets[-1]
  elif parapets:
    out["parapet_top_mm"] = parapets[0]
  if out.get("ground_mm") is not None:
    out["plinth_mm"] = out["ground_mm"]
  return out

LAYER_NAMES = {"cement sand bed": "cement sand bed", "pcc": "pcc", "brick ballast": "brick ballast", "sand filling": "sand filling", "brick tiles": "brick tiles", "mud plaster": "mud plaster"}

def floor_buildup(read_: list, floor: str) -> dict | None:
  floor = str(floor).upper()
  layers = [{"material": it["layer"], "thickness_mm": it["value_mm"], "mix": it.get("mix")} for _p, it in fact_items(read_, "BUILD_UP_LAYER") if it.get("under") == floor]
  block = blocks(read_).get(floor)
  if not layers and not block:
    return None
  text = " ".join(block["entries"]).upper() if block else ""
  waterproof = [it for _p, it in fact_items(read_, "WATERPROOF_LAYER") if it.get("under") == floor]
  return {"floor": floor, "layers": layers, "termite_proofed": "TERMITE" in text, "compacted_earth": "COMPACTED EARTH" in text, "waterproofed": bool(waterproof),
    "waterproof_layers": [{"material": it["material"], "count": it["value"]} for it in waterproof]}

def covered_area(read_: list, floor: str) -> dict | None:
  floor = str(floor).upper()
  seen: dict = {}
  for p, it in items(read_, "COVERED_AREA"):
    if it.get("floor") == floor:
      seen.setdefault(it["value_sft"], []).append(p)
  if not seen:
    return None
  value, pages = max(seen.items(), key=lambda kv: (len(kv[1]), kv[0]))
  return {"floor": floor, "value_sft": value, "pages": sorted(set(pages)), "other_values": sorted(v for v in seen if v != value)}

def slab_values(read_: list) -> list:
  by: dict = {}
  for p, it in items(read_, "SLAB_NOTE"):
    by.setdefault(round(it["value_mm"], 1), set()).add(("layout note", p))
  for p, it in fact_items(read_, "SLAB_THICKNESS"):
    by.setdefault(round(it["value_mm"], 1), set()).add(("slab note", p))
  for p, it in fact_items(read_, "DEPRESSED_SLAB"):
    by.setdefault(round(it["value_mm"], 1), set()).add(("depressed slab", p))
  return [{"mm": mm, "where": sorted(w)} for mm, w in sorted(by.items())]

_BAR_SPACING = re.compile(r"C\s*/\s*C|@", re.I)

def _discipline(sh: dict) -> str:
  return str((((sh.get("meta") or {}).get("identity")) or {}).get("discipline") or "").upper()

def slab_prints(read_: list) -> list:
  out: list = []
  
  for sh in read_:
    page, disc = sh["page_no"], _discipline(sh)
    for it in of_sheet(sh).get("items") or []:
      if it.get("kind") == "SLAB_NOTE":
        out.append({"mm": round(it["value_mm"], 1), "page": page, "discipline": disc})
    for it in ((sh.get("meta") or {}).get("facts") or {}).get("items") or []:
      if it.get("kind") == "SLAB_THICKNESS" and it.get("value_mm") and (it.get("scope") or "slab") in F.GENERIC_SLAB_SCOPES and not _BAR_SPACING.search(it.get("text") or ""):
        out.append({"mm": round(it["value_mm"], 1), "page": page, "discipline": disc})
  return out

def slab_conflict(read_: list, governs: bool = True) -> dict | None:
  prints = slab_prints(read_)
  values = sorted({p["mm"] for p in prints})
  if len(values) < 2:
    return None
  structural = sorted({p["mm"] for p in prints if p["discipline"].startswith("STRUCT")})
  pick = structural[0] if governs and len(structural) == 1 else None
  return {"about": "SLAB_THICKNESS", "governs_mm": pick, "values_mm": values, "basis": "STRUCTURE_SET" if pick is not None else "UNDECIDED",
    "prints": sorted(({"mm": p["mm"], "page": p["page"], "discipline": p["discipline"]} for p in prints), key=lambda x: (x["mm"], x["page"]))}
