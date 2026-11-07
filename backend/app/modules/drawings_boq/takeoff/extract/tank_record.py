from __future__ import annotations
import math
import re
from app.engine.measure import rule_registry as RR
from app.engine.measure import rulebook as RB
from app.engine.measure import readings as QS
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.prep.texts import build_lines

MM_PER_IN = 25.4
KINDS = ("OHWT", "UGWT", "SEPTIC")
DECISION_PREFIX = "TANK_SIZE:"
DEPTH_RULE, WALL_RULE = "stage.tank_depth_mm", "stage.tank_wall_mm"
DEPTH_DEFAULT, WALL_DEFAULT = 1524.0, 152.4
PLAN_LONG_RULE, PLAN_SHORT_RULE = "stage.tank_plan_long_mm", "stage.tank_plan_short_mm"
PLAN_LONG_DEFAULT, PLAN_SHORT_DEFAULT = 2438.4, 1828.8
WATER = ("OHWT", "UGWT")
DEFAULTED = ("SIBLING", "SEED")
NO_SEED_RULE = "TANK_NO_SEED"
RANK = {"DECISION": 0, "DETAIL": 1, "LABEL": 2, "DETAIL_PICTURE": 3, "WALLS": 4, "SIBLING": 5, "SEED": 6, "CONVENTION": 7, "RULE": 8}
NEAR_LINES = 6.0
DEPTH_LINES = 3.5
MIN_SIDE_IN, MAX_SIDE_IN = 36.0, 360.0
MIN_DEPTH_IN, MAX_DEPTH_IN = 24.0, 144.0
SIDE_TOL = 0.05
MIN_WALLS = 4
PAIR = re.compile(r"^\s*(.+?)\s*[xX×]\s*(.+?)\s*$")
FEET = re.compile(r"^(\d{1,2})\s*'\s*-?\s*(\d{1,2})?\s*[\"”]?\s*$")
FEET_FRAC = re.compile(r"^(\d{1,2})\s*'\s*-?\s*(\d{1,2})\s*([½¼¾])\s*[\"”]?\s*$")
VULGAR = {"½": 0.5, "¼": 0.25, "¾": 0.75}

def _inches(text: str) -> float | None:
  t = (text or "").strip().replace("’", "'").replace("′", "'")
  m = FEET_FRAC.match(t)
  if m:
    return int(m.group(1)) * 12 + int(m.group(2)) + VULGAR[m.group(3)]
  m = FEET.match(t)
  if not m:
    return None
  return int(m.group(1)) * 12 + int(m.group(2) or 0)

def _stacked(text: str) -> float | None:
  t = (text or "").strip().replace("’", "'")
  m = re.match(r"^(\d{1,2})\s*'\s*-?\s*(\d{2})\s+(\d)\s*[\"”]?\s*$", t)
  if not m:
    return None
  digits, den = m.group(2), int(m.group(3))
  num = int(digits[1])
  if den not in (2, 4, 8) or not 0 < num < den:
    return None
  return int(m.group(1)) * 12 + int(digits[0]) + num / den

def length_in(text: str) -> float | None:
  got = _stacked(text)
  return got if got is not None else _inches(text)

def _ft(inches: float) -> str:
  return f"{int(inches // 12)}'-{inches - 12 * int(inches // 12):g}\""

def _lines_near(words: list, label, reach: float) -> list:
  h = max(label.height, 1.0)
  out = []
  for ln in build_lines(words):
    if not ln.spans:
      continue
    ws = [w for _, _, w in ln.spans]
    cx, cy = sum(w.cx for w in ws) / len(ws), sum(w.cy for w in ws) / len(ws)
    d = math.hypot(cx - label.cx, cy - label.cy) / h
    if 0 < d <= reach:
      out.append(((ln.text or "").strip(), d, cx, cy))
  return sorted(out, key=lambda r: r[1])

def label_fields(words: list, label, page_no: int | None = None) -> dict:
  near = _lines_near(words, label, NEAR_LINES)
  pair = None
  for text, d, _cx, _cy in near:
    m = PAIR.match(text)
    if not m:
      continue
    a, b = length_in(m.group(1)), length_in(m.group(2))
    if a is None or b is None or not (MIN_SIDE_IN <= min(a, b) and max(a, b) <= MAX_SIDE_IN):
      continue
    pair = (text, d, sorted((a, b), reverse=True))
    break
  if pair is None:
    from app.modules.drawings_boq.takeoff.extract import tank_capacity as TC
    return TC.fields(words, label, page_no) if TC.enabled() else {}
  out = {"plan": {"route": "LABEL", "page_no": page_no, "mm": [round(v * MM_PER_IN, 1) for v in pair[2]], "basis": "INSIDE", "text": pair[0]}}
  
  lone = []
  for text, d, _cx, _cy in near:
    if text == pair[0] or d > DEPTH_LINES or PAIR.match(text):
      continue
    v = length_in(text)
    if v is not None and MIN_DEPTH_IN <= v <= MAX_DEPTH_IN:
      lone.append((text, v))
  if len(lone) == 1:
    out["depth"] = {"route": "LABEL", "page_no": page_no, "mm": round(lone[0][1] * MM_PER_IN, 1), "basis": "INSIDE", "text": lone[0][0]}
  return out

def _axis(p, q) -> str:
  return "H" if abs(q[0] - p[0]) >= abs(q[1] - p[1]) else "V"

def wall_plan(walls: list, mm_per_pt: float) -> dict | None:
  segs = []
  for w in walls:
    pts = (w.geometry or {}).get("points") or []
    if len(pts) < 2:
      continue
    p, q = pts[0], pts[-1]
    segs.append({"axis": _axis(p, q), "len": math.hypot(q[0] - p[0], q[1] - p[1]) * mm_per_pt, "mid": ((p[0] + q[0]) / 2 * mm_per_pt, (p[1] + q[1]) / 2 * mm_per_pt)})
    
  hs, vs = [s for s in segs if s["axis"] == "H"], [s for s in segs if s["axis"] == "V"]
  best = None
  for i, a in enumerate(hs):
    for b in hs[i + 1:]:
      for j, c in enumerate(vs):
        for d in vs[j + 1:]:
          lh, lv = (a["len"] + b["len"]) / 2.0, (c["len"] + d["len"]) / 2.0
          if min(lh, lv) <= 0 or abs(a["len"] - b["len"]) > SIDE_TOL * lh or abs(c["len"] - d["len"]) > SIDE_TOL * lv:
            continue
          gap_v, gap_h = abs(a["mid"][1] - b["mid"][1]), abs(c["mid"][0] - d["mid"][0])
          if abs(gap_v - lv) > SIDE_TOL * lv or abs(gap_h - lh) > SIDE_TOL * lh:
            continue
          if best is None or lh * lv < best[0] * best[1]:
            best = (lh, lv)
            
  if best is None:
    return None
  return {"mm": [round(max(best), 1), round(min(best), 1)], "walls": len(segs)}

def detail_fields(facts: dict) -> dict:
  sizes, said, src = facts.get("sizes_mm") or {}, facts.get("sizes_assumed") or {}, facts.get("sizes_from") or {}
  pages = [d.get("page_no") for d in facts.get("tank_drawings") or [] if d.get("page_no") is not None]
  page = pages[0] if pages else None
  out: dict = {}
  read = any(x.get("source") == "PICTURE" for d in facts.get("tank_drawings") or [] for x in d.get("lengths") or [])
  def route(token: str) -> str:
    return "DETAIL_PICTURE" if read and src.get(token) == "PICTURE" else "DETAIL"
  
  if sizes.get("length_mm") and sizes.get("width_mm"):
    out["plan"] = {"route": route("length_mm"), "page_no": page, "mm": [sizes["length_mm"], sizes["width_mm"]], "basis": "OUTSIDE", "text": said.get("length_mm") or ""}
  if sizes.get("height_mm"):
    out["depth"] = {"route": route("height_mm"), "page_no": page, "mm": sizes["height_mm"], "basis": "OUTSIDE", "text": said.get("height_mm") or ""}
  if sizes.get("thickness_mm"):
    out["wall"] = {"route": route("thickness_mm"), "page_no": page, "mm": sizes["thickness_mm"], "text": said.get("thickness_mm") or "", "from": src.get("thickness_mm")}
  slabs = facts.get("tank_slabs_mm") or {}
  for key, name in (("top_mm", "top"), ("bottom_mm", "bottom")):
    if slabs.get(key):
      out[name] = {"route": route("thickness_mm"), "page_no": page, "mm": slabs[key], "text": "the slab the tank detail prints"}
  return out

def sheet_fields(sites: list, walls: list, words: list, mm_per_pt: float) -> int:
  n = 0
  for s in sites:
    f = s.facts or {}
    kind = f.get("tank_kind")
    if kind not in KINDS:
      continue
  
    fields = detail_fields(f)
    labels = [w for w in words if _is_label(kind, w)]
    if not labels:
      from app.modules.drawings_boq.takeoff.extract import tank_capacity as TC
      labels = TC.labels(words).get(kind, []) if TC.enabled() else []
    if labels and "plan" not in fields:
      for k, v in label_fields(words, labels[0]).items():
        fields.setdefault(k, v)
    if "plan" not in fields:
      mine = [w for w in walls if (w.facts or {}).get("enclosure") == "TANK" and (w.facts or {}).get("tank_kind") in (kind, "TANK")]
      got = wall_plan(mine, mm_per_pt) if len(mine) >= MIN_WALLS else None
      if got:
        fields["plan"] = {"route": "WALLS", "page_no": None, "mm": got["mm"], "basis": "CENTRE", "text": f"{got['walls']} walls drawn round the tank, centre lines {got['mm'][0] / 1000:.3f} x {got['mm'][1] / 1000:.3f} m"}
    if fields:
      f["tank_fields"] = {**fields, "mm_per_pt": mm_per_pt}
      s.facts = f
      n += 1
  return n

def _is_label(kind: str, w) -> bool:
  from app.modules.drawings_boq.takeoff.extract import site_items as SI
  t = (w.text or "").strip()
  if kind == "SEPTIC":
    return bool(SI.SEPTIC_WORD.match(t))
  return any(k == kind and pat.search(t) for k, pat in SI.TANK_WORDS)

def _best(entries: list) -> dict | None:
  return min(entries, key=lambda e: (RANK[e["route"]], e.get("mm_per_pt") or 0.0, e.get("page_no") or 0)) if entries else None

def _rule(key: str, default: float) -> float:
  return float(RB.pick(key, default))

def decided(raw) -> dict | None:
  if raw is None:
    return None
  parts = [p for p in re.split(r"\s*[xX,]\s*", str(raw).strip()) if p]
  if len(parts) not in (2, 4):
    return None
  try:
    return dict(zip(("length_mm", "width_mm", "height_mm", "thickness_mm"), (float(p) for p in parts)))
  except ValueError:
    return None

def fallback_plan(kind: str, printed: dict) -> dict:
  other = printed.get("UGWT" if kind == "OHWT" else "OHWT") if kind in WATER else None
  if other and other.get("plan_mm"):
    a, b = other["plan_mm"]
    return {"route": "SIBLING", "mm": [a, b], "text": f"no sheet prints the plan of this tank, so it is taken as the plan of the {other['kind']} of the same drawing, {a / 1000:.3f} x {b / 1000:.3f} m outside"}
  a, b = _rule(PLAN_LONG_RULE, PLAN_LONG_DEFAULT), _rule(PLAN_SHORT_RULE, PLAN_SHORT_DEFAULT)
  return {"route": "SEED", "mm": [a, b], "text": f"no sheet prints the plan of this tank and no other water tank of the drawing gives one, so the seed {a / 1000:.3f} x {b / 1000:.3f} m outside is used"}

def hold(kind: str, items: list, decision: str | None = None, answered: dict | None = None) -> dict:
  rec = make(kind, items, decision, answered, None)
  by_scale = sorted(items, key=lambda i: (i["sh"].get("mm_per_pt") or 0.0, i["page_no"]))
  for i in by_scale[1:]:
    i["c"].facts = {**(i["c"].facts or {}), FS.SET_ASIDE: {"by": FS.TANK_BY, "page_no": by_scale[0]["page_no"], "kind": kind}}
  rec["held"] = True
  return rec

def make(kind: str, items: list, decision: dict | None = None, answered: dict | None = None, fallback: dict | None = None) -> dict:
  per: dict = {}
  for it in items:
    tf = it["fields"]
    for name, e in tf.items():
      if name == "mm_per_pt" or not isinstance(e, dict):
        continue
      per.setdefault(name, []).append({**e, "mm_per_pt": tf.get("mm_per_pt"), "page_no": e.get("page_no") or it.get("page_no")})
      
  sources: dict = {}
  rec: dict = {"kind": kind, "pages": sorted({it["page_no"] for it in items if it.get("page_no") is not None})}
  typed = decided(decision)
  if typed:
    answer = answered or {}
    for name, key in (("plan", None), ("depth", "height_mm"), ("wall", "thickness_mm")):
      if name != "plan" and key not in typed:
        continue
      if name == "plan":
        per["plan"] = [{"route": "DECISION", "mm": [typed["length_mm"], typed["width_mm"]], "basis": "OUTSIDE", "text": answer.get("source") or f"decision {DECISION_PREFIX}{kind}", "page_no": None}]
      else:
        per[name] = [{"route": "DECISION", "mm": typed[key], "basis": "OUTSIDE" if name == "depth" else None, "text": answer.get("source") or f"decision {DECISION_PREFIX}{kind}", "page_no": None}]
        
  if fallback and not per.get("plan"):
    per["plan"] = [{"route": fallback["route"], "mm": fallback["mm"], "basis": "OUTSIDE", "text": fallback["text"], "page_no": None}]
  wall = _best(per.get("wall") or [])
  if wall:
    rec["wall_mm"], sources["wall"] = float(wall["mm"]), _cite(wall)
  else:
    rec["wall_mm"], sources["wall"] = _rule(WALL_RULE, WALL_DEFAULT), {"route": "RULE", "key": WALL_RULE, "text": "no wall thickness is printed for this tank"}
  for name, key, conv in (("top", "top_mm", "tank_top_slab_mm"), ("bottom", "base_mm", "tank_bottom_slab_mm")):
    e = _best(per.get(name) or [])
    if e:
      rec[key], sources[name] = float(e["mm"]), _cite(e)
    else:
      rec[key], sources[name] = float(QS.convention(conv)), {"route": "CONVENTION", "key": conv, "text": "the slab the QS gave (S11); the drawing prints none for this tank"}
  t = rec["wall_mm"]
  plan = _best(per.get("plan") or [])
  if plan:
    a, b = (float(v) for v in plan["mm"])
    add = {"INSIDE": 2 * t, "CENTRE": t}.get(plan.get("basis"), 0.0)
    rec["plan_mm"], sources["plan"] = [round(a + add, 1), round(b + add, 1)], {**_cite(plan), "basis": plan.get("basis")}
    
  depth = _best(per.get("depth") or [])
  if depth:
    h = float(depth["mm"]) + (rec["top_mm"] + rec["base_mm"] if depth.get("basis") == "INSIDE" else 0.0)
    rec["depth_mm"], sources["depth"] = round(h, 1), {**_cite(depth), "basis": depth.get("basis")}
  else:
    rec["depth_mm"], sources["depth"] = _rule(DEPTH_RULE, DEPTH_DEFAULT), {"route": "RULE", "key": DEPTH_RULE, "text": "no depth is printed for this tank"}
  rec["sources"], rec["complete"] = sources, "plan" in sources
  rec["defaulted"] = bool(plan and plan["route"] in DEFAULTED)
  rec["assumed"] = sorted(k for k, v in sources.items() if v["route"] in ("RULE", "CONVENTION", "WALLS") + DEFAULTED or v.get("basis") in ("INSIDE", "CENTRE"))
  return rec

def _cite(e: dict) -> dict:
  return {"route": e["route"], "page_no": e.get("page_no"), "text": e.get("text") or ""}

def _sources_text(kind: str, record: dict) -> str:
  return f"{kind}: " + "; ".join(f"{k} from {v['route'].lower().replace('_', ' ')}" + (f" p.{v['page_no']}" if v.get("page_no") else "") for k, v in record["sources"].items())

def pair(read: list, decisions: dict | None = None, answered: dict | None = None) -> list:
  by_kind: dict = {}
  for sh in read:
    for c in sh["candidates"]:
      f = c.facts or {}
      if (f.get(FS.SET_ASIDE) or {}).get("by") == FS.TANK_BY:
        c.facts = f = {k: v for k, v in f.items() if k != FS.SET_ASIDE}
      if c.category == "SITE" and f.get("tank_kind") in KINDS and not FS.is_set_aside(c):
        by_kind.setdefault(f["tank_kind"], []).append((sh, c))
        
  built = {}
  for kind in sorted(by_kind):
    items = [{"fields": (c.facts or {}).get("tank_fields") or {}, "page_no": sh["page_no"], "c": c, "sh": sh} for sh, c in by_kind[kind]]
    built[kind] = (items, make(kind, items, (decisions or {}).get(DECISION_PREFIX + kind), (answered or {}).get(DECISION_PREFIX + kind)))
  printed = {k: rec for k, (_items, rec) in built.items() if rec["complete"]}
  out = []
  for kind in sorted(built):
    items, rec = built[kind]
    if not rec["complete"]:
      fallback = fallback_plan(kind, printed)
      if fallback["route"] == "SEED" and RR.on(NO_SEED_RULE):
        out.append(hold(kind, items, (decisions or {}).get(DECISION_PREFIX + kind), (answered or {}).get(DECISION_PREFIX + kind)))
        continue
      rec = make(kind, items, (decisions or {}).get(DECISION_PREFIX + kind), (answered or {}).get(DECISION_PREFIX + kind), fallback)
  
    plan = rec["sources"]["plan"]
    by_scale = sorted(items, key=lambda i: (i["sh"].get("mm_per_pt") or 0.0, i["page_no"]))
    pick = next((i for i in by_scale if plan["route"] != "DECISION" and (i["fields"].get("plan") or {}).get("route") == plan["route"] and i["page_no"] == plan.get("page_no")), by_scale[0])
    _write(pick["c"], rec)
    rec["kept_page"] = pick["page_no"]
    for i in items:
      if i is pick:
        continue
    
      i["c"].facts = {**(i["c"].facts or {}), FS.SET_ASIDE: {"by": FS.TANK_BY, "page_no": pick["page_no"], "kind": kind}}
    for sh in read:
      for c in sh["candidates"]:
        f = c.facts or {}
        if c.category == "WALL" and f.get("enclosure") == "TANK" and f.get("tank_kind") in (kind, "TANK") and not FS.is_set_aside(c):
          c.facts = {**f, FS.SET_ASIDE: {"by": FS.TANK_BY, "page_no": pick["page_no"], "kind": kind}}
    out.append(rec)
  return out

def _write(c, rec: dict) -> None:
  f = dict(c.facts or {})
  t, (a, b) = rec["wall_mm"], rec["plan_mm"]
  sizes = {"length_mm": a, "width_mm": b, "height_mm": rec["depth_mm"], "thickness_mm": t}
  said = {}
  fields = {"length_mm": "plan", "width_mm": "plan", "height_mm": "depth", "thickness_mm": "wall"}
  for token, name in fields.items():
    s = rec["sources"][name]
    
    said[token] = f"{s['route'].lower().replace('_', ' ')}" + (f" p.{s['page_no']}"if s.get("page_no") else "") + (f", {s['text']}" if s.get("text") else "") + (f" ({s['key']})" if s.get("key") else "")
  f["sizes_mm"], f["sizes_assumed"] = sizes, said
  f["sizes_from"] = {token: rec["sources"][name]["route"] for token, name in fields.items()}
  f["sizes_source"] = "DRAWING_ASSUMED"
  f["tank_slabs_mm"] = {"top_mm": rec["top_mm"], "bottom_mm": rec["base_mm"]}
  f["tank_record"] = {k: v for k, v in rec.items() if k != "kept_page"}
  c.facts = f
  c.missing = []
  
  codes = {"TANK_SIZE_HELD", "SITE_TANK_SIZES_TYPED", "SITE_TANK_SIZES_LISTED"}
  c.notes = [n for n in c.notes if n.get("code") not in codes]
  c.notes.append(C.note("TANK_RECORD_BUILT", kind=rec["kind"], sources=_sources_text(rec["kind"], rec)))
  for name, code in (("depth", "TANK_DEPTH_BY_RULE"), ("wall", "TANK_WALL_BY_RULE")):
    if rec["sources"][name]["route"] == "RULE":
      c.notes.append(C.note(code, kind=rec["kind"], key=rec["sources"][name]["key"]))
  if rec["sources"]["plan"]["route"] == "WALLS":
    c.notes.append(C.note("TANK_PLAN_FROM_WALLS", kind=rec["kind"]))
  if rec["defaulted"]:
    c.notes.append(C.note("TANK_SIZE_DEFAULTED", kind=rec["kind"], route=rec["sources"]["plan"]["route"], plan=rec["sources"]["plan"]["text"]))
  from app.modules.drawings_boq.takeoff.extract import note_scope as NS
  c.status = NS.status_of(c.notes)
