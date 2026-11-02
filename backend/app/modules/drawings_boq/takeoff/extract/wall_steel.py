from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.extract import note_scope as NS
from app.modules.drawings_boq.takeoff.extract.slab_panels import BAR, BAR_NUMBERS, SPACING_IN, MM_INCH

TITLE = re.compile(r"R\.?\s*C\.?\s*C\.?\s*WALL\s*SECTION\s*[-–:]?\s*(\d+)", re.I)
REACH_X_SIZES = 9.0
REACH_Y_SIZES = 30.0
FACES = 2
AMBIGUOUS_BARS = "ROLE_UNKNOWN"
SECTIONS_DISAGREE = "SECTIONS_DISAGREE"

def _string(text: str) -> dict | None:
  m = BAR.search(text or "")
  if m is None:
    return None
  bar, spacing = int(m.group("bar")), float(m.group("s"))
  if not (BAR_NUMBERS[0] <= bar <= BAR_NUMBERS[1] and SPACING_IN[0] <= spacing <= SPACING_IN[1]):
    return None
  return {"bar": bar, "spacing_in": spacing}

def titles(lines: list) -> list:
  out = []
  for ln in lines:
    m = TITLE.search(ln.text or "")
    if m is not None and abs(ln.angle) < 1.0:
      x, y = ln.locate(0, len(ln.text))
      out.append({"mark": m.group(1), "x": x, "y": y, "size": max(float(ln.spans[0][2].size), 1.0)})
  return out

def read(lines: list) -> dict:
  tl = titles(lines)
  sections = {t["mark"]: {"mark": t["mark"], "strings": []} for t in tl}
  if not tl:
    return {"sections": [], "loose": 0}
  loose = 0
  for ln in lines:
    s = _string(ln.text)
    if s is None or abs(ln.angle) >= 1.0 or TITLE.search(ln.text or ""):
      continue
    x, y = ln.locate(0, len(ln.text))
    near = sorted(((abs(x - t["x"]), t) for t in tl if 0.0 < y - t["y"] <= REACH_Y_SIZES * t["size"] and abs(x - t["x"]) <= REACH_X_SIZES * t["size"]), key=lambda p: p[0])
    if not near:
      continue
    if len(near) > 1 and near[0][0] == near[1][0]:
      loose += 1
      continue
    sections[near[0][1]["mark"]]["strings"].append({**s, "text": ln.text.strip(), "x": round(x, 1), "y": round(y, 1)})
    
  out = []
  for mark in sorted(sections):
    sec = sections[mark]
    if sec["strings"]:
      out.append(_roles(sec))
  return {"sections": out, "loose": loose}

def _roles(sec: dict) -> dict:
  bars = sorted({s["bar"] for s in sec["strings"]})
  sec = {**sec, "bars": bars, "problem": None}
  if len(bars) != 2:
    sec["problem"] = AMBIGUOUS_BARS
    return sec
  small, large = bars
  sec["horizontal"] = [s for s in sec["strings"] if s["bar"] == small]
  sec["vertical"] = [s for s in sec["strings"] if s["bar"] == large]
  return sec

def mean_spacing_in(strings: list) -> float:
  return len(strings) / sum(1.0 / s["spacing_in"] for s in strings)

def combine(found: dict) -> dict | None:
  secs = [s for s in found["sections"] if not s["problem"]]
  if not secs:
    return None
  hbars = {s["bar"] for sec in secs for s in sec["horizontal"]}
  vbars = {s["bar"] for sec in secs for s in sec["vertical"]}
  if len(hbars) != 1 or len(vbars) != 1:
    return {"problem": SECTIONS_DISAGREE, "sections": [s["mark"] for s in secs]}
  hor = [s for sec in secs for s in sec["horizontal"]]
  ver = [s for sec in secs for s in sec["vertical"]]
  hs, vs = mean_spacing_in(hor), mean_spacing_in(ver)
  return {"problem": None, "sections": [s["mark"] for s in secs], "h_bar": hbars.pop(), "v_bar": vbars.pop(), "h_mean_in": round(hs, 3), "v_mean_in": round(vs, 3),
    "h_spacings_in": sorted({s["spacing_in"] for s in hor}), "v_spacings_in": sorted({s["spacing_in"] for s in ver}), "h_strings": len(hor), "v_strings": len(ver),
    "texts": [s["text"] for sec in secs for s in sec["strings"]]}

def steel_of(got: dict) -> dict:
  return {"mesh": {"bar": got["h_bar"], "spacing_mm": round(got["h_mean_in"] * MM_INCH, 1), "ways": 2, "layers": FACES, "across": {"bar": got["v_bar"], "spacing_mm": round(got["v_mean_in"] * MM_INCH, 1)}}}

def _is_rcc_wall(c) -> bool:
  return c.category == "WALL" and (c.facts or {}).get("construction") == "RCC"

def _spacing_text(vals: list) -> str:
  return ", ".join(f"{v:g}" for v in vals) + " in"

def sections_of(rows: list) -> dict:
  secs: dict = {}
  loose = 0
  for r in rows:
    got = (r.get("stats") or {}).get("wall_sections") or {}
    loose += int(got.get("loose") or 0)
    for sec in got.get("sections") or []:
      secs[(r["page_no"], sec["mark"])] = {**sec, "page_no": r["page_no"]}
  return {"sections": [secs[k] for k in sorted(secs)], "loose": loose}

def apply(rows: list, note) -> dict:
  found = sections_of(rows)
  walls = [c for r in rows for c in r["candidates"] if _is_rcc_wall(c)]
  stats = {"walls": len(walls), "attached": 0, "sections": len(found["sections"]), "problem": None}
  
  if not walls or not found["sections"]:
    return stats
  got = combine(found)
  if got is None or got["problem"]:
    stats["problem"] = (got or {}).get("problem") or AMBIGUOUS_BARS
    why = {SECTIONS_DISAGREE: "the sections print different bar sizes for the same role", AMBIGUOUS_BARS: "a section does not print exactly two bar sizes, so which is vertical and which horizontal is not settled"}[stats["problem"]]
    for c in walls:
      n = note("WALL_STEEL_NOT_READ", reason=stats["problem"])
      n["message"] = f"The drawing has {len(found['sections'])} RCC wall section(s) with bar strings but the bars of this wall were not taken from them: {why}. The wall steel stays on the usual band."
      c.notes.append(n)
      c.status = NS.status_of(c.notes)
    return stats
  steel = steel_of(got)
  
  mixed = len(got["h_spacings_in"]) > 1 or len(got["v_spacings_in"]) > 1
  text = (f"mesh #{got['h_bar']} at {got['h_mean_in']:g} in horizontal and #{got['v_bar']} at {got['v_mean_in']:g} in vertical, both faces, from RCC wall section"
    f"{'s' if len(got['sections']) > 1 else ''} {', '.join(got['sections'])}")
  for c in walls:
    if c.params.get("steel"):
      continue
    c.params["steel"] = steel
    c.facts["steel_text"] = text
    c.facts["steel_source"] = {"grade": "PRINTED", "text": "bar strings of the RCC wall sections: " + ", ".join(got["texts"])}
    c.facts["wall_steel"] = {k: got[k] for k in ("sections", "h_bar", "v_bar", "h_mean_in", "v_mean_in", "h_spacings_in", "v_spacings_in", "h_strings", "v_strings")}
    n = note("WALL_STEEL_FROM_SECTIONS", text=text)
    n["message"] = (f"The bars of the RCC wall are read from the strings written on the wall section{'s' if len(got['sections']) > 1 else ''} {', '.join(got['sections'])} of the drawing: {', '.join(got['texts'])}. "
      f"The smaller bar (#{got['h_bar']}) is taken as the horizontal bars and the larger (#{got['v_bar']}) as the vertical bars, one set on each face. "
      + (f"The sections print different spacings (horizontal {_spacing_text(got['h_spacings_in'])}, vertical {_spacing_text(got['v_spacings_in'])}) and the wall is not tied to one section or zone, "
        f"so each set is weighed at the spacing that gives the average number of bars of the strings read ({got['h_mean_in']:g} in horizontal, {got['v_mean_in']:g} in vertical). " if mixed else "")
      + "The bars are cut to the wall run and height less cover; the laps, the starter bars into the footing and the corner bars are not in these figures.")
    c.notes.append(n)
    
    if mixed:
      m = note("WALL_STEEL_ZONES_AVERAGED", horizontal=got["h_spacings_in"], vertical=got["v_spacings_in"])
      c.notes.append(m)
    c.status = NS.status_of(c.notes)
    stats["attached"] += 1
  return stats
