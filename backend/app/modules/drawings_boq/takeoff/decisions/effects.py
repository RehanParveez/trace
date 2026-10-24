from __future__ import annotations
from app.modules.drawings_boq.takeoff.decisions import catalog
from app.modules.drawings_boq.takeoff.extract import wall_net

CFT = 35.3146667
HEIGHT_NOTES = ("HEIGHT_FROM_SECTION", "HEIGHT_FROM_QS")

def _fig(key: str, value: float, unit: str) -> dict:
  return {"key": key, "value": round(float(value), 2), "unit": unit}

def _cut(basis: str, lowest: bool, plinth: float, web: float) -> float:
  if basis not in catalog.BEAM_BASES:
    return 0.0
  return (plinth if lowest else 0.0) + (web if basis == "BETWEEN_BEAMS" else 0.0)

def wall_row(c, level: str | None) -> dict | None:
  codes = {n.get("code") for n in (c.notes or []) if isinstance(n, dict)}
  f, p = c.facts or {}, c.params or {}
  if c.category != "WALL" or not (codes & set(HEIGHT_NOTES)) or "HEIGHT_FROM_NOTE" in codes or f.get("enclosure") or f.get("foundation_item"):
    return None

  length, height = float(f.get("length_cc_m") or 0.0), float(p.get("height_mm") or 0.0)
  if length <= 0.0 or height <= 0.0:
    return None
  op = f.get("openings")
  return {"level": level, "length_m": length, "height_mm": height, "thickness_mm": float(f.get("thickness_used_mm") or p.get("thickness_mm") or 0.0),
    "open_m2": float((op or {}).get("area_m2") or 0.0) if isinstance(op, dict) else 0.0, "clear_mm": float(f.get("clear_height_mm") or 0.0), "rcc": f.get("construction") == "RCC"}

def height(rows: list, current: str, lowest: str | None, plinth_mm: float, web_mm: float) -> dict:
  if not rows:
    return {"applies": False, "options": {}}
  opts: dict = {}
  for o in catalog.by_key(catalog.HEIGHT)["options"]:
    area = brick = 0.0
    unknown = False
    for r in rows:
      is_low = bool(lowest) and r["level"] == lowest
      if current == "CLEAR":
        if o["value"] == "CLEAR":
          h = r["height_mm"]
        else:
          unknown = True
          break
      else:
        base = r["height_mm"] + _cut(current, is_low, plinth_mm, web_mm)
        if o["value"] == "CLEAR":
          h = r["clear_mm"] or base
        else:
          cut = _cut(o["value"], is_low, plinth_mm, web_mm)
          h = base - cut if 0.0 < cut < base else base
      m2 = max(r["length_m"] * h / 1000.0 - r["open_m2"], 0.0)
      area += m2
      if not r["rcc"]:
        brick += m2 * r["thickness_mm"] / 1000.0
    opts[o["value"]] = None if unknown else {"figures": [_fig("wall_area", area, "m2"), _fig("brick", brick, "m3")], "brick_m3": brick}
  return {"applies": True, "walls": len(rows), "options": _diff(opts, current)}

def _diff(opts: dict, current: str) -> dict:
  now = (opts.get(current) or {}).get("brick_m3")
  out = {}
  for k, v in opts.items():
    if v is None:
      out[k] = {"figures": [], "diff": None, "diff_unit": "m3"}
      continue
    out[k] = {"figures": v["figures"], "diff": None if now is None else round(v["brick_m3"] - now, 2), "diff_unit": "m3"}
  return out

def band(recs: list, current: str) -> dict:
  recs = [r for r in recs if isinstance(r, dict) and r.get("with_band_cft") is not None]
  if not recs:
    return {"applies": False, "options": {}}
  one = both = 0.0
  for r in recs:
    single = r["mode"] == "SINGLE"
    one += float(r["counted_cft"] if single else r["without_band_cft"])
    both += float(r["with_band_cft"] if single else r["counted_cft"])
  vals = {"ONE_BAND": one, "BAND_AND_BEAM": both}
  now = vals[current]
  return {"applies": True, "floors": sorted({str(r.get("floor")) for r in recs}), "options": {k: {"figures": [_fig("band_concrete", v, "cft")], "diff": round(v - now, 2), "diff_unit": "cft"} for k, v in vals.items()}}

def lintel_net(sheets: list, current: str) -> dict:
  total, n = 0.0, 0
  for walls, lintels in sheets:
    sizes = wall_net.lintel_sizes(lintels)

    if not sizes:
      continue
    for w in walls:
      if not wall_net._brick_wall(w):
        continue
      lines = wall_net.less_lines(w, sizes)
      total += sum(x["value"] for x in lines)
      n += len(lines)

  if n == 0:
    return {"applies": False, "options": {}}
  net = {"figures": [_fig("lintel_off", total, "m3"), _fig("lintels", n, "nos")], "diff": 0.0, "diff_unit": "m3"}
  gross = {"figures": [_fig("lintel_off", 0.0, "m3")], "diff": 0.0, "diff_unit": "m3"}
  if current == "NET":
    gross["diff"] = round(total, 2)
  else:
    net["diff"] = round(-total, 2)
  return {"applies": True, "options": {"NET": net, "GROSS": gross}}
