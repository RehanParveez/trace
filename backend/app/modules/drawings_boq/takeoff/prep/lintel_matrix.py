from __future__ import annotations
import math
import re
from app.modules.drawings_boq.takeoff.prep.lintels import _fix

MM_INCH = 25.4
MM_FOOT = 304.8
MIN_ROWS = 3
SPAN_FT = (1.0, 40.0)
WALL_IN = (3.0, 24.0)
DEPTH_IN = (3.0, 36.0)
LABEL_SIZE_SHARE = 0.85

_LENGTH = re.compile(r"(?P<ft>\d{1,2})\s*'?\s*-\s*(?P<in>\d{1,2})\s*\"?")
_UP_TO = re.compile(r"\bUP\s*TO\b", re.I)
_DEPTH = re.compile(r"^(?P<n>\d{1,2}(?:\.\d)?)\s*\"$")
_WALL = re.compile(r"^(?P<n>\d{1,2})(?:\s+(?P<a>\d)/(?P<b>\d))?\s*\"$")

def _xy(w, quarter: int) -> tuple:
  rad = math.radians(quarter * 90)
  ux, uy = math.cos(rad), math.sin(rad)
  return w.cx * ux + w.cy * uy, -w.cx * uy + w.cy * ux

def _feet(m) -> float:
  return int(m.group("ft")) + int(m.group("in")) / 12.0

def _inches(text: str) -> float | None:
  m = _WALL.match(_fix(text).strip())
  if not m:
    return None
  v = int(m.group("n")) + (int(m.group("a")) / int(m.group("b")) if m.group("a") else 0.0)
  return v if WALL_IN[0] <= v <= WALL_IN[1] else None

def _labels(words: list) -> tuple:
  best = None
  for q in range(4):
    items = [w for w in words if round(w.angle / 90) % 4 == q and abs(((w.angle + 45) % 90) - 45) <= 6]
    quant = []
    for w in items:
      m = _LENGTH.fullmatch(_fix(w.text).strip())
      if m and SPAN_FT[0] <= _feet(m) <= SPAN_FT[1]:
        quant.append(w)
    if len(quant) >= 2 * MIN_ROWS - 1 and (best is None or len(quant) > len(best[1])):
      best = (q, quant, items)
  if best is None:
    return None, []

  q, quant, items = best
  size = max(w.size for w in quant)
  quant = [w for w in quant if w.size >= LABEL_SIZE_SHARE * size]
  rows: list = []
  for w in sorted(quant, key=lambda t: _xy(t, q)[1]):
    a = _xy(w, q)[1]
    if rows and abs(a - rows[-1]["across"]) <= 0.6 * size:
      rows[-1]["words"].append(w)
    else:
      rows.append({"across": a, "words": [w]})

  out = []
  for r in rows:
    ws = sorted(r["words"], key=lambda t: _xy(t, q)[0])
    vals = [_feet(_LENGTH.fullmatch(_fix(w.text).strip())) for w in ws]
    centre = sum(_xy(w, q)[1] for w in ws) / len(ws)
    around = [w for w in items if w.size >= LABEL_SIZE_SHARE * size and abs(_xy(w, q)[1] - centre) <= 0.6 * size]
    up_to = bool(_UP_TO.search(" ".join(w.text for w in sorted(around, key=lambda t: _xy(t, q)[0]))))

    if len(vals) == 1 and up_to:
      lo, hi = None, vals[0]
    elif len(vals) == 2 and vals[0] < vals[1]:
      lo, hi = vals[0], vals[1]
    else:
      continue
    alongs = [_xy(w, q)[0] for w in around]
    out.append({"across": centre, "lo": lo, "hi": hi, "size": size, "along": (min(alongs), max(alongs))})
  return q, out

def read(words: list | None) -> list:
  words = [w for w in (words or []) if (w.text or "").strip()]
  if not any(re.fullmatch(r"LINTELS?", w.text.strip(), re.I) for w in words) or not any(w.text.strip().upper() == "THICKNESS" for w in words):
    return []
  q, rows = _labels(words)
  if q is None or len(rows) < MIN_ROWS:
    return []

  size = rows[0]["size"]
  thick = next(w for w in words if w.text.strip().upper() == "THICKNESS")
  mean = sum(r["across"] for r in rows) / len(rows)
  sgn = 1.0 if _xy(thick, q)[1] > mean else -1.0
  rows.sort(key=lambda r: -sgn * r["across"])
  steps = sorted(abs(rows[i + 1]["across"] - rows[i]["across"]) for i in range(len(rows) - 1))
  pitch = steps[len(steps) // 2]
  top = rows[0]["across"]

  heads = []
  for w in words:
    n = _inches(w.text)
    a = sgn * (_xy(w, q)[1] - top)
    if n is not None and 0.25 * pitch <= a <= 1.2 * pitch and w.size < LABEL_SIZE_SHARE * size:
      heads.append((_xy(w, q)[0], n, w))
  heads.sort(key=lambda t: t[0])
  if not heads:
    return []
  gap = (heads[-1][0] - heads[0][0]) / (len(heads) - 1) if len(heads) > 1 else 6 * size
  lo_edge, hi_edge = heads[0][0] - 0.6 * gap, heads[-1][0] + 0.6 * gap
  bottom = rows[-1]["across"]

  cells: dict = {}
  for w in words:
    m = _DEPTH.match(_fix(w.text).strip())
    if not m or w.size >= LABEL_SIZE_SHARE * size:
      continue
    d = float(m.group("n"))
    along, across = _xy(w, q)
    if not (DEPTH_IN[0] <= d <= DEPTH_IN[1] and lo_edge <= along <= hi_edge):
      continue
    ri = min(range(len(rows)), key=lambda i: abs(rows[i]["across"] - across))
    if abs(rows[ri]["across"] - across) > 0.5 * pitch:
      continue
    ci = min(range(len(heads)), key=lambda i: abs(heads[i][0] - along))
    if w is heads[ci][2]:
      continue
    cells.setdefault((ri, ci), []).append((w.size, d))

  out: list = []
  seen: set = set()
  for ri, r in enumerate(rows):
    if r["hi"] in seen:
      continue
    cols = []
    for ci, (_, wall_in, _) in enumerate(heads):
      got = cells.get((ri, ci))
      if got and len({d for _, d in got}) == 1:
        cols.append((wall_in, got[0][1]))
    if not cols:
      continue
    
    seen.add(r["hi"])
    cols.sort()
    wall_in, d_in = cols[-1]
    entry = {"span_max_ft": round(r["hi"], 3), "span_max_mm": round(r["hi"] * MM_FOOT, 1), "width_mm": round(wall_in * MM_INCH, 1), "depth_mm": round(d_in * MM_INCH, 1),
      "text": "up to " + f"{r['hi']:.2f}".rstrip("0").rstrip(".") + " ft: " + ", ".join(f"{w:g} in wall {d:g} in deep" for w, d in reversed(cols)), "basis": "MATRIX"}
    if r["lo"] is not None:
      entry["span_min_ft"] = round(r["lo"], 3)
    if len(cols) > 1:
      tw, td = cols[0]
      entry["thin"] = {"wall_mm": round(tw * MM_INCH, 1), "width_mm": round(tw * MM_INCH, 1), "depth_mm": round(td * MM_INCH, 1)}
    out.append(entry)
  out.sort(key=lambda e: e["span_max_ft"])
  return out if len(out) >= MIN_ROWS else []
