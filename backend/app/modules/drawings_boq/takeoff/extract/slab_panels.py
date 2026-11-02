from __future__ import annotations
import re
import math
from decimal import Decimal
from app.engine.measure.member_steel import member_lines, kg_per_m
from app.engine.measure import readings as QS
from app.modules.drawings_boq.takeoff.prep.views import _SLAB_PANEL

BAR = re.compile(r"#\s*(?P<bar>\d{1,2})\s*[\"”″]?\s*@\s*(?P<s>\d{1,2}(?:\.\d)?)")
MM_INCH = 25.4
MIN_LINE_PT = 12.0
ARROW_RADIUS_PT = 2.6
ARROW_STROKES = 3
WORD_REACH_PT = 5.0
OVERLAP_SHARE = 0.5
MARK_MARGIN_PT = 2.0
BAR_NUMBERS = (2, 12)
SPACING_IN = (2.0, 24.0)
MAX_BARS = 400
TAG = re.compile(r"\(\s*(?P<t>TOP|B\.?\s*W\.?)\s*\)", re.I)
TAG_REACH_SIZES = 2.5
BOTH_WAYS = 2

def _arrow_end(index, px: float, py: float) -> bool:
  segs, _, _ = index.window(px - ARROW_RADIUS_PT, py - ARROW_RADIUS_PT, px + ARROW_RADIUS_PT, py + ARROW_RADIUS_PT)
  n = sum(1 for (x0, y0, x1, y1, k) in segs if k == 2 and min(math.hypot(x0 - px, y0 - py), math.hypot(x1 - px, y1 - py)) <= ARROW_RADIUS_PT)
  return n == ARROW_STROKES

def bar_lines(index, bbox) -> list:
  x0, y0, x1, y1 = bbox
  segs, _, _ = index.window(x0, y0, x1, y1)
  out, seen = [], set()
  for (ax, ay, bx, by, k) in segs:
    if k != 0:
      continue
  
    horizontal, vertical = abs(ay - by) < 0.01, abs(ax - bx) < 0.01
    length = math.hypot(bx - ax, by - ay)
    if not (horizontal or vertical) or length < MIN_LINE_PT:
      continue
    if not (_arrow_end(index, ax, ay) and _arrow_end(index, bx, by)):
      continue
    rec = ({"axis": "X", "a": min(ax, bx), "b": max(ax, bx), "p": ay} if horizontal else {"axis": "Y", "a": min(ay, by), "b": max(ay, by), "p": ax})
    key = (rec["axis"], round(rec["a"], 1), round(rec["b"], 1), round(rec["p"], 1))
    if key not in seen:
      seen.add(key)
      out.append({**rec, "len_pt": length})
  return out

def _string_of(w) -> dict | None:
  m = BAR.search(w.text or "")
  if m is None:
    return None
  bar, spacing = int(m.group("bar")), float(m.group("s"))
  if not (BAR_NUMBERS[0] <= bar <= BAR_NUMBERS[1] and SPACING_IN[0] <= spacing <= SPACING_IN[1]):
    return None
  text_axis = "X" if abs(round(w.angle / 90.0)) % 2 == 0 else "Y"
  return {"bar": bar, "spacing_in": spacing, "spacing_mm": round(spacing * MM_INCH, 1), "axis": text_axis, "x": w.cx, "y": w.cy, "text": w.text.strip()}

def _bind(strings: list, lines: list) -> tuple:
  pairs, unbound = [], []
  
  for s in strings:
    best = None
    for ln in lines:
      if ln["axis"] != s["axis"]:
        continue
      along, across = (s["x"], s["y"]) if ln["axis"] == "X" else (s["y"], s["x"])
      if not (ln["a"] - 1.0 <= along <= ln["b"] + 1.0):
        continue
      d = abs(across - ln["p"])
      if d <= WORD_REACH_PT and (best is None or d < best[0]):
        best = (d, ln)
    if best is None:
      unbound.append(s)
    else:
      pairs.append((s, best[1]))
  return pairs, unbound

def _linked(a: dict, b: dict) -> bool:
  if a["axis"] == b["axis"]:
    return False
  x, y = (a, b) if a["axis"] == "X" else (b, a)       
  return x["a"] - 1.0 <= y["p"] <= x["b"] + 1.0 and y["a"] - 1.0 <= x["p"] <= y["b"] + 1.0

def _groups(pairs: list) -> list:
  parent = list(range(len(pairs)))
  def find(i):
    while parent[i] != i:
      parent[i] = parent[parent[i]]
      i = parent[i]
    return i

  for i in range(len(pairs)):
    for j in range(i + 1, len(pairs)):
      if _linked(pairs[i][1], pairs[j][1]):
        parent[find(i)] = find(j)
  out: dict = {}
  for i, p in enumerate(pairs):
    out.setdefault(find(i), []).append(p)
  return list(out.values())

def read(index, bbox, mm_per_pt: float) -> dict:
  words = [w for w in index.words if bbox[0] <= w.cx <= bbox[2] and bbox[1] <= w.cy <= bbox[3]]
  strings = [s for s in (_string_of(w) for w in words) if s]
  lines = bar_lines(index, bbox)
  pairs, unbound = _bind(strings, lines)
  marks = [{"mark": w.text.strip().upper(), "x": w.cx, "y": w.cy} for w in words if _SLAB_PANEL.match(w.text.strip().upper())]
  panels = []
  
  for grp in _groups(pairs):
    xs = [ln for _, ln in grp if ln["axis"] == "X"]
    ys = [ln for _, ln in grp if ln["axis"] == "Y"]
    lo_x = min([ln["a"] for ln in xs] + [ln["p"] for ln in ys]) if (xs or ys) else 0.0
    hi_x = max([ln["b"] for ln in xs] + [ln["p"] for ln in ys]) if (xs or ys) else 0.0
    lo_y = min([ln["a"] for ln in ys] + [ln["p"] for ln in xs]) if (xs or ys) else 0.0
    hi_y = max([ln["b"] for ln in ys] + [ln["p"] for ln in xs]) if (xs or ys) else 0.0
    inside = [m for m in marks if lo_x - MARK_MARGIN_PT <= m["x"] <= hi_x + MARK_MARGIN_PT and lo_y - MARK_MARGIN_PT <= m["y"] <= hi_y + MARK_MARGIN_PT]
    span_x = max((ln["b"] - ln["a"] for ln in xs), default=0.0) * mm_per_pt        
    span_y = max((ln["b"] - ln["a"] for ln in ys), default=0.0) * mm_per_pt
    sets, by_string, lines_n = [], {}, 0
    
    for s, ln in grp:
      lines_n += 1
      cut = (ln["b"] - ln["a"]) * mm_per_pt
      across = span_y if ln["axis"] == "X" else span_x
      key = (ln["axis"], s["bar"], s["spacing_in"])
      rec = by_string.get(key)
      if rec is None:
        rec = {"axis": ln["axis"], "bar": s["bar"], "spacing_mm": s["spacing_mm"], "text": s["text"], "cut_mm": round(cut, 1), "across_mm": round(across, 1), "lines": 0, "lines_cut_mm": []}
        by_string[key] = rec
        sets.append(rec)
      rec["lines"] += 1
      
      rec["lines_cut_mm"].append(round(cut, 1))
      rec["cut_mm"] = max(rec["cut_mm"], round(cut, 1))
    ok = span_x > 0 and span_y > 0 and all(x["across_mm"] > 0 for x in sets)
    panels.append({"mark": inside[0]["mark"] if len(inside) == 1 else None, "marks_inside": sorted({m["mark"] for m in inside}), "length_mm": round(max(span_x, span_y), 1) if ok else None,
      "width_mm": round(min(span_x, span_y), 1) if ok else None, "x_mm": round(span_x, 1), "y_mm": round(span_y, 1),
      "area_m2": round(span_x * span_y / 1e6, 3) if ok else None, "sets": sets, "lines": lines_n, "steel_ok": ok, "centre": [round((lo_x + hi_x) / 2.0, 2), round((lo_y + hi_y) / 2.0, 2)]})
  panels.sort(key=lambda p: (p["mark"] or "~", p["centre"]))
  return {"panels": panels, "strings": len(strings), "lines": len(lines), "unbound": [s["text"] for s in unbound], "marks": sorted({m["mark"] for m in marks})}


SET_KEYS = ("axis", "bar", "spacing_mm", "text", "cut_mm", "across_mm")

def _record(p: dict) -> dict:
  return {"mark": p["mark"], "length_mm": p["length_mm"], "width_mm": p["width_mm"], "area_m2": p["area_m2"], "sets": [{k: s[k] for k in SET_KEYS} for s in p["sets"]]}

def _kg(records: list) -> float:
  _, kg = member_lines("SLAB", Decimal("1"), Decimal("1"), Decimal("0"), {"panels": records}, Decimal("0"), Decimal("0"))
  return float(kg)

def _all_lines(p: dict) -> dict:
  sets = []
  for s in p["sets"]:
    for cut in s["lines_cut_mm"]:
      sets.append({**{k: s[k] for k in SET_KEYS}, "cut_mm": cut})
  return {**_record(p), "sets": sets}

def why_left(p: dict, dup: set) -> str | None:
  if p["mark"] is None:
    return "SEVERAL_MARKS" if len(p["marks_inside"]) > 1 else "NO_MARK"
  if p["mark"] in dup:
    return "MARK_TWICE"
  if not p["steel_ok"]:
    return "ONE_SPAN"
  return None

def steel_of(found: dict) -> tuple:
  marks = [p["mark"] for p in found["panels"] if p["mark"]]
  dup = {m for m in marks if marks.count(m) > 1}
  used, left = [], []
  for p in found["panels"]:
    why = why_left(p, dup)
    if why is None:
      used.append(p)
    else:
      left.append({"mark": p["mark"], "marks_inside": p["marks_inside"], "why": why, "strings": sorted({s["text"] for s in p["sets"]}), "lines": p.get("lines", 0)})
      
  records = [_record(p) for p in used]
  area = round(sum(p["area_m2"] for p in used), 3)
  kg = _kg(records) if records else 0.0
  facts = {"panels_used": [p["mark"] for p in used], "panels_left": left, "marks_on_plan": found["marks"], "unbound_strings": found["unbound"], "panel_area_m2": area,
    "bar_kg": round(kg, 1), "kg_per_m2": round(kg / area, 2) if area else None, "alt_all_lines_kg": round(_kg([_all_lines(p) for p in used]), 1) if used else 0.0,
    "strings": found["strings"], "lines": found["lines"]}
  return ({"panels": records} if records else None), facts

def steel_text(steel: dict) -> str:
  strings = sorted({s["text"] for p in steel["panels"] for s in p["sets"]})
  return f"{len(steel['panels'])} panels, bars from the drawn lines ({', '.join(strings)})"


def tagged_strings(index, bbox) -> list:
  words = [w for w in index.words if bbox[0] <= w.cx <= bbox[2] and bbox[1] <= w.cy <= bbox[3]]
  tags = [(w, "TOP" if m.group("t").upper() == "TOP" else "BW") for w in words for m in [TAG.search(w.text or "")] if m]
  out = []
  for w in words:
    s = _string_of(w)
    if s is None:
      continue
    near = sorted(((math.hypot(t.cx - w.cx, t.cy - w.cy), name) for t, name in tags if round(t.angle) == round(w.angle)), key=lambda p: p[0])
    s["tag"] = near[0][1] if near and near[0][0] <= TAG_REACH_SIZES * max(float(w.size), 1.0) else None
    out.append(s)
  return out

def bottom_rate(s: dict) -> float:
  return round(float(BOTH_WAYS * kg_per_m({"bar": s["bar"]})) / (s["spacing_mm"] / 1000.0), 2)

def strings_fact(strings: list) -> dict:
  sets: dict = {}
  for s in strings:
    key = (s["tag"] or "UNTAGGED", s["bar"], s["spacing_in"])
    sets[key] = sets.get(key, 0) + 1
  by_tag: dict = {}
  for (tag, _bar, _sp), n in sets.items():
    by_tag[tag] = by_tag.get(tag, 0) + n
  listed = [{"tag": t, "text": f"#{b}@{sp:g}", "times": n} for (t, b, sp), n in sorted(sets.items())]
  bottom = [{"text": f"#{b}@{sp:g}", "kg_per_m2": bottom_rate({"bar": b, "spacing_mm": sp * MM_INCH})} for (t, b, sp) in sorted(sets) if t == "BW"]
  return {"strings": len(strings), "by_tag": dict(sorted(by_tag.items())), "sets": listed, "bottom_both_ways": bottom}

def attach_strings(cand, plan: dict, index, note) -> None:
  bbox = plan.get("bbox")
  if not bbox:
    return
  strings = tagged_strings(index, bbox)
  if not strings:
    return
  fact = strings_fact(strings)
  cand.facts["slab_bar_strings"] = fact
  rule = float(QS.param("slab_steel_kg_per_m2") or 0.0)
  
  tags = ", ".join(f"{v} {k.lower()}" for k, v in fact["by_tag"].items())
  rates = ", ".join(f"{b['text']} = {b['kg_per_m2']} kg/m\u00b2 of panel" for b in fact["bottom_both_ways"])
  vs_rule = f", against the QS rule of thumb of {rule:g} kg/m\u00b2 for the whole slab (bottom, top and bearing)" if rule else ""
  n = note("SLAB_BARS_NOT_MEASURED", strings=fact["strings"], by_tag=fact["by_tag"])
  n["message"] = (f"The framing plan prints {fact['strings']} bar strings for this slab ({tags}), but the sheet is not to scale and its scale is not verified, "
    "so no length is read from the drawn lines and the slab steel stays on the usual band. "
    + (f"Bottom sets printed as both ways (B.W.): {rates}{vs_rule}. " if rates else "")
    + "These weights per m\u00b2 do not need a scale, but the top bars over the supports and the panel each set belongs to do, so they are not billed.")
  cand.notes.append(n)

def attach(cand, plan: dict, index, note, scale_unverified: bool = False) -> None:
  if scale_unverified:
    attach_strings(cand, plan, index, note)
    return
  bbox = plan.get("bbox")
  mm = plan.get("mm_per_pt")
  if not bbox or not mm:
    return
  found = read(index, bbox, float(mm))
  if not found["panels"] and not found["strings"]:
    return

  steel, facts = steel_of(found)
  cand.facts["panel_steel"] = facts
  area, rule = facts["panel_area_m2"], float(QS.param("slab_steel_kg_per_m2") or 0.0)
  slab_m2 = float(cand.facts.get("gross_area_m2") or cand.facts.get("area_m2") or 0.0)
  
  if steel:
    cand.params["steel"] = steel
    cand.facts["steel_text"] = steel_text(steel)
    cand.facts["steel_source"] = {"grade": "PRINTED", "text": "bar strings beside the arrowed bar lines of the panels of the framing plan"}
    n = note("SLAB_STEEL_FROM_PANELS", panels=facts["panels_used"], bar_kg=facts["bar_kg"], panel_area_m2=area)
    n["message"] = (f"The bars of {len(facts['panels_used'])} slab panels ({', '.join(facts['panels_used'])}) are read from the arrowed bar lines of the framing plan and the bar string beside each (one set per distinct string): "
      f"{facts['bar_kg']:,.0f} kg over {area:,.1f} m\u00b2 of panel ({facts['kg_per_m2']} kg/m\u00b2)" + (f", against {rule * slab_m2:,.0f} kg ({rule:g} kg/m\u00b2 x {slab_m2:,.1f} m\u00b2 of slab) by the QS rule of thumb" if rule and slab_m2 else "")
      + f". If every drawn line counted as its own set the bars would weigh {facts['alt_all_lines_kg']:,.0f} kg. Not in these figures: the top steel over the supports, the bearing and anchorage of each bar and laps; "
      f"the panels cover {area:,.1f} m\u00b2 of the {slab_m2:,.1f} m\u00b2 slab (the rest has no panel drawn). Bar counts are the panel span over the spacing, plus one.")
    cand.notes.append(n)
    
  if facts["panels_left"] or facts["unbound_strings"] or not steel:
    left = facts["panels_left"]
    n = note("SLAB_PANEL_STEEL_PARTIAL", panels=[l["mark"] for l in left], unbound=facts["unbound_strings"])
    why = {"NO_MARK": "no panel mark stands inside", "SEVERAL_MARKS": "more than one panel mark stands inside", "MARK_TWICE": "the mark is used by another panel on the plan", "ONE_SPAN": "only one span is drawn"}
    groups: dict = {}
    for l in left:
      groups.setdefault(l["why"], []).append(l)
      
    parts = []
    for k, ls in groups.items():
      lines_n = sum(l["lines"] for l in ls)
      parts.append(f"{len(ls)} group{'s' if len(ls) != 1 else ''} of bar lines ({lines_n} line{'s' if lines_n != 1 else ''}; {', '.join(sorted({t for l in ls for t in l['strings']}))}) not used because {why[k]}")
    k_un = len(facts["unbound_strings"])
    n["message"] = ((f"{len(facts['panels_used'])} panels carry steel. " if steel else "No panel of this plan could carry steel. ")
      + ("; ".join(parts) + ". " if parts else "")
      + (f"{k_un} bar string{'s' if k_un != 1 else ''} ({', '.join(facts['unbound_strings'])}) stand{'s' if k_un == 1 else ''} beside no drawn bar line and {'was' if k_un == 1 else 'were'} not used. " if k_un else "")
      + "Whatever is not in a panel has no steel in the slab here: it is not estimated.")
    cand.notes.append(n)
