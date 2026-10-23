from __future__ import annotations
import re
import math

INCH_MM = 25.4
LABEL_REACH_MM = 1800.0          
WIDTH_AGREE = 0.35              
NEIGHBOUR_SIZES = 3.5            
ANGLE_TOL = 6.0
SIZE_MIN_MM, SIZE_MAX_MM = 300.0, 6000.0
DOOR_NOTE_MM = (1800.0, 3500.0)
WINDOW_NOTE_MM = (300.0, 3500.0)

_ANCHOR = re.compile(r"^\s*([WD])\s*=\s*(.*)$", re.I)
_SILL = re.compile(r"^\s*SILL\s*=\s*(.*)$", re.I)
_PIECE = re.compile(r"^[0-9'\"\-\.xX\u00d7/\u00bd\s]+$")
_FTIN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*'\s*(?:-?\s*(\d+)(?:\s+(12|1\s+2|\u00bd|1/2))?\s*\"?)?\s*$")
_INCH = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*\"\s*$")
_METRIC = re.compile(r"^\s*(\d{3,4})\s*$")

def _clean(text: str) -> str:
  return text.replace("\u2019", "'").replace("\u2032", "'").replace("\u201d", '"').replace("\u2033", '"').replace("\u201c", '"')

def parse_length(text: str | None, imperial: bool = True) -> float | None:
  if not text:
    return None
  t = _clean(text).strip()
  m = _FTIN.match(t)
  
  if m:
    ft, inch, half = float(m.group(1)), float(m.group(2) or 0), m.group(3)
    if inch >= 12:
      return None
    return (ft * 12.0 + inch + (0.5 if half else 0.0)) * INCH_MM
  m = _INCH.match(t)
  
  if m:
    return float(m.group(1)) * INCH_MM
  m = _METRIC.match(t)
  if m and not imperial:
    return float(m.group(1))
  return None

def _angle_ok(a: float, b: float) -> bool:
  d = abs((a - b + 180.0) % 360.0 - 180.0)
  return d <= ANGLE_TOL

def _along_across(w) -> tuple:
  rad = math.radians(round(w.angle / 90.0) * 90.0)
  ux, uy = math.cos(rad), math.sin(rad)
  return w.cx * ux + w.cy * uy, -w.cx * uy + w.cy * ux

def _reach(a) -> float:
  return float(a.length) / 2.0 + NEIGHBOUR_SIZES * max(float(a.size), 1.0)

def read(words: list, imperial: bool = True) -> dict:
  anchors = [w for w in words if _ANCHOR.match(w.text or "")]
  sills = [w for w in words if _SILL.match(w.text or "")]
  
  if not anchors:
    return {"labels": [], "unread": 0}
  pieces = [w for w in words if w not in anchors and w not in sills and _PIECE.match(w.text or "") and (w.text or "").strip()]
  own: dict = {id(a): [] for a in anchors}
  for p in pieces:
    best, best_d = None, None
    for a in anchors:
      if not _angle_ok(a.angle, p.angle):
        continue
    
      d = math.hypot(a.cx - p.cx, a.cy - p.cy)
      if d <= _reach(a) and (best_d is None or d < best_d):
        best, best_d = a, d
    if best is not None:
      own[id(best)].append(p)
      
  own_sill: dict = {}
  for s in sills:
    best, best_d = None, None
    for a in anchors:
      if not _angle_ok(a.angle, s.angle):
        continue
    
      d = math.hypot(a.cx - s.cx, a.cy - s.cy)
      if d <= _reach(a) and (best_d is None or d < best_d):
        best, best_d = a, d
    if best is not None and id(best) not in own_sill:
      own_sill[id(best)] = s
      
  labels, unread = [], 0
  for a in anchors:
    m = _ANCHOR.match(a.text)
    kind = "DOOR" if m.group(1).upper() == "D" else "WINDOW"
    a_along, a_across = _along_across(a)
    tol = max(a.size, 1.0) * 0.5
    rows: dict = {}
    for p in own[id(a)]:
      along, across = _along_across(p)
      row = 0 if abs(across - a_across) <= tol else (1 if across < a_across else -1)
      if row == 0 and along < a_along:
        continue
    
      rows.setdefault(row, []).append(((round(along, 1), -across), p.text))
    ordered = [(key[1], key[0], t) for row in sorted(k for k in rows if k >= 0) for key, t in sorted(rows[row])]     
    row0 = [t for _, t in sorted(rows.get(0, []))]
    rest = _clean(m.group(2)).strip()
    parts = re.split(r"\s*[xX\u00d7]\s*", rest, maxsplit=1)
    width_text = parts[0]
    height_text = parts[1] if len(parts) == 2 and parts[1].strip() else None
    if len(parts) == 1:
      if re.search(r"\d$", width_text):                          
        for t in row0:
          t = _clean(t).strip()
          if not re.fullmatch(r"[0-9\"]{1,2}", t):
            break
          width_text += " " + t
          if '"' in t:
            break
        
      for neg_across, along, t in ordered:
        t = _clean(t).strip()
        if re.match(r"^\"?\s*[xX\u00d7]", t):
          after = t.lstrip('" ')[1:].strip()
          if after:
            height_text = after
          else:                                                   
            later = [(a2, t2) for n2, a2, t2 in ordered if abs(n2 - neg_across) <= tol and a2 > along]
            if later:
              height_text = _clean(min(later)[1]).strip()
          break
      
    text = re.sub(r"(?<=\d)\s+1\s+2(?=\s*\"?$)", " 1/2", width_text) + (f" X {height_text}" if height_text else "")
    width = parse_length(width_text.replace('" "', '"'), imperial)
    height = parse_length(height_text, imperial) if height_text else None
    if width is None or not (SIZE_MIN_MM <= width <= SIZE_MAX_MM):
      unread += 1
      continue
  
    if height is not None and not (SIZE_MIN_MM <= height <= SIZE_MAX_MM):
      height = None
    sill = None
    s = own_sill.get(id(a))
    if s is not None:
      sill = parse_length(_SILL.match(s.text).group(1), imperial)
      if sill is not None and not (0.0 <= sill <= 2500.0):
        sill = None
    labels.append({"kind": kind, "x": float(a.cx), "y": float(a.cy), "w_mm": round(width, 1), "h_mm": None if height is None else round(height, 1),
      "sill_mm": None if sill is None else round(sill, 1), "text": f"{m.group(1).upper()}={text}"})
  return {"labels": labels, "unread": unread}

def pair(symbols: list, labels: list, kind: str, mm_per_pt: float, scale_verified: bool) -> int:
  reach = LABEL_REACH_MM / mm_per_pt
  cand = []
  
  for si, s in enumerate(symbols):
    for li, lab in enumerate(labels):
      if lab["kind"] != kind:
        continue
      d = math.hypot(s["x"] - lab["x"], s["y"] - lab["y"])
      if d > reach:
        continue
      if scale_verified and abs(float(s["width_mm"]) - lab["w_mm"]) > WIDTH_AGREE * lab["w_mm"]:
        continue
      cand.append((d, si, li))
      
  cand.sort()
  used_s, used_l, n = set(), set(), 0
  for d, si, li in cand:
    if si in used_s or li in used_l:
      continue
    used_s.add(si)
    used_l.add(li)
    symbols[si]["label"] = labels[li]
    labels[li]["paired"] = True
    n += 1
  return n

_FT_TEXT = r"(\d+\s*'\s*(?:-?\s*\d+(?:\s*(?:\u00bd|1/2))?\s*\")?)"
_NOTE_DOOR = (re.compile(rf"\bDOORS?\s+(?:HEIGHT|HT\.?)\s*[:=\-]?\s*{_FT_TEXT}", re.I), re.compile(rf"\bALL\s+DOORS?\s*[:=\-]?\s*{_FT_TEXT}\s*(?:HIGH|HT|HEIGHT)", re.I))
_NOTE_WINDOW = (re.compile(rf"\bWINDOWS?\s+(?:HEIGHT|HT\.?)\s*[:=\-]?\s*{_FT_TEXT}", re.I), re.compile(rf"\bALL\s+WINDOWS?\s*[:=\-]?\s*{_FT_TEXT}\s*(?:HIGH|HT|HEIGHT)", re.I))

def height_notes(lines: list) -> dict:
  found: dict = {"DOOR": set(), "WINDOW": set()}
  for ln in lines:
    t = _clean(getattr(ln, "text", "") or "")
    for kind, pats, lo_hi in (("DOOR", _NOTE_DOOR, DOOR_NOTE_MM), ("WINDOW", _NOTE_WINDOW, WINDOW_NOTE_MM)):
      for rx in pats:
        for m in rx.finditer(t):
          v = parse_length(m.group(1).replace("\u00bd", " 1/2"), True)
          if v is not None and lo_hi[0] <= v <= lo_hi[1]:
            found[kind].add(round(v, 1))
  return {k: next(iter(v)) for k, v in found.items() if len(v) == 1}
