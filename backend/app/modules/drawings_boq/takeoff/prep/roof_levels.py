from __future__ import annotations
import math
import re
from app.modules.drawings_boq.takeoff.prep import schedules as S

KIND = "ROOF_LEVEL"
SHEETS = (("SECTION", re.compile(r"\bSECTIONS?\b")), ("ELEVATION", re.compile(r"\bELEVATIONS?\b")))
NAMES = (("PARAPET", re.compile(r"\bPARAPET\b")), ("FLOOR", re.compile(r"\b(?:FLOOR|ROOF)\b")))
SIGNS = ("+", "±", "-", "–")
LINE_MIN, LINE_MAX = 0.5, 2.6
WORD_GAP = 3.0
OVERLAP = 0.5

def sheet_kind(words: list) -> str | None:
  text = " ".join(w.text for w in sorted(words, key=lambda w: -w.size)[:12]).upper()
  return next((name for name, rx in SHEETS if rx.search(text)), None)

def _axes(angle: float) -> tuple | None:
  quarter = round(angle / 90.0)
  if abs(angle - 90.0 * quarter) > 2.0:
    return None
  ux, uy = math.cos(math.radians(90.0 * quarter)), math.sin(math.radians(90.0 * quarter))
  return ux, uy, -uy, ux

def _name_line(words: list, sign, mark, ux: float, uy: float, nx: float, ny: float) -> str:
  h = mark.height
  a0 = sign.cx * ux + sign.cy * uy - 0.5 * sign.length
  a1 = mark.cx * ux + mark.cy * uy + 0.5 * mark.length
  lines: dict = {}
  for w in words:
    if w is mark or w is sign or not w.text or not any(c.isalpha() for c in w.text):
      continue
    if abs(w.angle - mark.angle) > 2.0:
      continue
    d = (w.cx - mark.cx) * nx + (w.cy - mark.cy) * ny
    if not LINE_MIN * h <= abs(d) <= LINE_MAX * h:
      continue
    lines.setdefault((1 if d > 0 else -1, round(d / (0.35 * h))), []).append(w)
  best = None
  
  for _k, ws in lines.items():
    ws = sorted(ws, key=lambda w: w.cx * ux + w.cy * uy)
    chains: list = [[ws[0]]]
    for w in ws[1:]:
      prev = chains[-1][-1]
      gap = (w.cx * ux + w.cy * uy - 0.5 * w.length) - (prev.cx * ux + prev.cy * uy + 0.5 * prev.length)
      if gap <= WORD_GAP * h:
        chains[-1].append(w)
      else:
        chains.append([w])
        
    for chain in chains:
      b0 = chain[0].cx * ux + chain[0].cy * uy - 0.5 * chain[0].length
      b1 = chain[-1].cx * ux + chain[-1].cy * uy + 0.5 * chain[-1].length
      share = (min(a1, b1) - max(a0, b0)) / max(a1 - a0, 1e-6)
      if share < OVERLAP:
        continue
      text = " ".join(w.text for w in chain).upper()
      if any(rx.search(text) for _n, rx in NAMES) and (best is None or share > best[0]):
        best = (share, text)
  return best[1] if best else ""

def read(words: list) -> list:
  kind = sheet_kind(words)
  if kind is None:
    return []

  out: list = []
  for mark in words:
    if "'" not in mark.text:
      continue
    axes = _axes(mark.angle)
    mm = S.feet_inches_mm(mark.text)
    if axes is None or mm is None:
      continue
  
    ux, uy, nx, ny = axes
    sign = next((s for s in words if s.text in SIGNS and abs((mark.cx - s.cx) * nx + (mark.cy - s.cy) * ny) <= 0.8 * mark.height and 0 < (mark.cx - s.cx) * ux + (mark.cy - s.cy) * uy <= 6.0 * mark.height), None)
    if sign is None or sign.text != "+":
      continue
    label = _name_line(words, sign, mark, ux, uy, nx, ny)
    name = next((n for n, rx in NAMES if rx.search(label)), None)
    if name:
      out.append({"name": name, "mm": mm, "sheet": kind, "text": f"{label.title()} + {mark.text}"})
  return out
