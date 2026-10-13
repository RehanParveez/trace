from __future__ import annotations
from dataclasses import dataclass
import re
import math
from decimal import Decimal, InvalidOperation
from app.modules.drawings_boq.takeoff.scale import parse_scale_text

MM_PER_INCH = 25.4
MM_PER_FOOT = 304.8
MIN_DIM_MM = 50.0
MAX_DIM_MM = 120_000.0

@dataclass(frozen=True)
class Reading:
  value_mm: float
  unit: str      
  prior: float   

_FTIN = re.compile(r"""^\(?\s*(?:(?P<ft>\d+(?:\.\d+)?)\s*(?:'|ft\.?|feet|foot|′))?\s*[-–]?\s*
  (?:(?P<in>\d+(?:\.\d+)?)\s*(?:"|in\.?|inch(?:es)?|″|”|(?=\s*\d+\s*/\s*\d+)))?\s*
  (?:(?P<n>\d+)\s*/\s*(?P<d>\d+)\s*(?:"|″|”)?)?\s*\)?$""", re.X | re.I)
_METRIC = re.compile(r"^\(?\s*(?P<v>\d+(?:[.,]\d+)?)\s*(?P<u>mm|cm|m)\s*\)?$", re.I)
_PLAIN = re.compile(r"^\(?\s*(?P<v>\d{1,3}(?:,\d{3})+|\d+)(?:\.(?P<f>\d{1,3}))?\s*\)?$")

def _prior_table(hint: str | None) -> dict:
  base = {"mm_int": 0.9, "mm_dec": 0.35, "m_dec": 0.8, "m_int": 0.15, "cm_int": 0.12, "ft_dec": 0.12, "in_int": 0.06}
  if hint == "mm":
    base.update(mm_int=1.0, mm_dec=0.6, m_dec=0.1, m_int=0.02, cm_int=0.02, ft_dec=0.02, in_int=0.01)
  elif hint == "m":
    base.update(mm_int=0.25, m_dec=1.0, m_int=0.6, cm_int=0.05, ft_dec=0.03)
  elif hint == "cm":
    base.update(cm_int=1.0, mm_int=0.2, m_dec=0.2)
  elif hint in ("ft-in", "ft"):
    base.update(mm_int=0.35, ft_dec=0.7 if hint == "ft" else 0.25, in_int=0.4 if hint == "ft-in" else 0.1, m_dec=0.2)
  return base

def parse_dimension(text: str, hint: str | None = None) -> list[Reading]:
  s = (text or "").strip().replace("’", "'").replace("′", "'").replace("”", '"').replace("″", '"').replace("“", '"')
  if not s or len(s) > 24:
    return []
  out: list[Reading] = []
  m = _METRIC.match(s)
  
  if m:
    v = float(m.group("v").replace(",", "."))
    mm = v * {"mm": 1.0, "cm": 10.0, "m": 1000.0}[m.group("u").lower()]
    return [Reading(mm, m.group("u").lower(), 1.0)] if MIN_DIM_MM <= mm <= MAX_DIM_MM else []
  if ("'" in s or '"' in s or re.search(r"\b(ft|feet|foot|in|inch)", s, re.I)) and re.search(r"\d", s):
    m = _FTIN.match(s)
    if m and (m.group("ft") or m.group("in") or m.group("n")):
      ft = float(m.group("ft") or 0)
      inch = float(m.group("in") or 0)
      if m.group("n") and m.group("d") and int(m.group("d")) != 0:
        inch += int(m.group("n")) / int(m.group("d"))
      mm = ft * MM_PER_FOOT + inch * MM_PER_INCH
      if MIN_DIM_MM <= mm <= MAX_DIM_MM:
        return [Reading(mm, "ft-in" if m.group("ft") else "in", 1.0)]
    
    return []
  m = _PLAIN.match(s)
  if not m:
    return []
  whole = m.group("v").replace(",", "")
  frac = m.group("f")
  v = float(whole + ("." + frac if frac else ""))
  pri = _prior_table(hint)
  if frac is None:
    iv = int(whole)
    if 100 <= iv <= 100_000:
      out.append(Reading(float(iv), "mm", pri["mm_int"]))
    if 1 <= iv <= 120:
      out.append(Reading(iv * 1000.0, "m", pri["m_int"]))
    if 10 <= iv <= 12_000:
      out.append(Reading(iv * 10.0, "cm", pri["cm_int"]))
    if 12 <= iv <= 4_800:
      out.append(Reading(iv * MM_PER_INCH, "in", pri["in_int"]))
  else:
    if 0.1 <= v <= 120:
      out.append(Reading(v * 1000.0, "m", pri["m_dec"]))
    if 5 <= v <= 400:
      out.append(Reading(v * MM_PER_FOOT, "ft", pri["ft_dec"]))
    if 100 <= v <= 100_000 and float(frac) == 0:
      out.append(Reading(v, "mm", pri["mm_dec"]))
  return [r for r in out if MIN_DIM_MM <= r.value_mm <= MAX_DIM_MM and r.prior > 0.0]

def to_visual(x: float, y: float, crop: tuple, rotation: int) -> tuple:

  l, b, r, t = crop
  w, h = max(r - l, 1e-9), max(t - b, 1e-9)
  u, v = (x - l) / w, (y - b) / h  
  if rotation == 90:
    return (v, u)
  if rotation == 180:
    return (1 - u, v)
  if rotation == 270:
    return (1 - v, 1 - u)
  return (u, 1 - v)

@dataclass
class TextLine:
  text: str
  spans: list     
  angle: float

  def locate(self, start: int, end: int) -> tuple:
    ws = [w for a, b, w in self.spans if b > start and a < end]
    if not ws:
      return (0.0, 0.0)
    return (sum(w.cx for w in ws) / len(ws), sum(w.cy for w in ws) / len(ws))

def build_lines(words: list) -> list[TextLine]:

  buckets: dict = {}
  for w in words:
    a = round(w.angle / 90.0) % 4
    if abs(((w.angle + 45) % 90) - 45) > 6:  
      continue
    ang = a * 90
    rad = math.radians(ang)
    ux, uy = math.cos(rad), math.sin(rad)
    along = w.cx * ux + w.cy * uy
    across = -w.cx * uy + w.cy * ux
    tol = max(w.size, 1.0) * 0.7
    buckets.setdefault((ang, round(across / tol)), []).append((along, w, across))
  lines = []
  
  for (ang, _), items in buckets.items():
    items.sort(key=lambda t: t[0])
    text, spans, prev_end = "", [], None
    for along, w, across in items:
      half = w.length / 2
      start_s, end_s = along - half, along + half
      if prev_end is not None and start_s - prev_end > max(w.size, 1.0) * 2.5:
        lines.append(TextLine(text, spans, ang))
        text, spans, prev_end = "", [], None
      if text:
        text += " "
      spans.append((len(text), len(text) + len(w.text), w))
      text += w.text
      prev_end = end_s
    if text:
      lines.append(TextLine(text, spans, ang))
  return lines

_LABEL_SCALE = re.compile(r"\bSCALES?\b\s*[:=\-]?\s*(?P<v>.{0,40})", re.I)
_RATIO_RE = re.compile(r"(?<![\d.:/])(?P<a>\d+(?:\.\d+)?)\s*:\s*(?P<b>\d+(?:\.\d+)?)(?![\d:])")
_SLASH_RATIO_RE = re.compile(r"^\s*(?P<a>1)\s*/\s*(?P<b>\d{1,5})(?![\d/\"'])")
_IMPERIAL_RE = re.compile(r"\d+(?:\s*/\s*\d+)?(?:\.\d+)?\s*\"\s*=\s*\d+(?:\.\d+)?\s*'(?:\s*-?\s*\d+(?:\.\d+)?\s*\")?", re.I)
_NTS_RE = re.compile(r"\b(N\.?\s?T\.?\s?S\.?|NOT\s+TO\s+SCALE|AS\s+SHOWN|NO\s+SCALE)\b", re.I)

def find_scale_candidates(lines: list[TextLine]) -> list[dict]:
  out: list[dict] = []
  seen = set()
  for ln in lines:
    t = ln.text.replace("’", "'").replace("”", '"').replace("″", '"').replace("′", "'")
    labelled_at = None
    lm = _LABEL_SCALE.search(t)
    if lm:
      labelled_at = lm.start("v")
    for m in _RATIO_RE.finditer(t):
      try:
        a, b = Decimal(m.group("a")), Decimal(m.group("b"))
      except InvalidOperation:
        continue
      if not (a == 1 or (b == 1 and a in (2, 4, 5, 10, 20, 50))):
        continue
      txt = m.group(0)
      ratio = parse_scale_text(f"{a}:{b}")
      
      if ratio is None:
        continue
      lab = labelled_at is not None and 0 <= m.start() - labelled_at <= 3
      x, y = ln.locate(m.start(), m.end())
      key = (str(ratio), round(x, 0), round(y, 0))
      
      if key in seen:
        continue
      seen.add(key)
      out.append({"text": txt, "ratio": float(ratio), "labelled": bool(lab), "x": x, "y": y, "line": t[:80]})
    if labelled_at is not None:
      v = t[labelled_at:]
      sm = _SLASH_RATIO_RE.match(v)
      if sm:
        ratio = parse_scale_text(f"1:{sm.group('b')}")
        if ratio is not None:
          x, y = ln.locate(lm.start(), lm.end() + 8)
          key = (str(ratio), round(x, 0), round(y, 0))
          if key not in seen:
            seen.add(key)
            out.append({"text": "1/" + sm.group("b"), "ratio": float(ratio), "labelled": True, "x": x, "y": y, "line": t[:80]})
    for m in _IMPERIAL_RE.finditer(t):
      ratio = parse_scale_text(m.group(0))
      if ratio is None:
        continue
      x, y = ln.locate(m.start(), m.end())
      key = (str(ratio), round(x, 0), round(y, 0))
      if key in seen:
        continue
      seen.add(key)
      lab = labelled_at is not None and 0 <= m.start() - labelled_at <= 3
      out.append({"text": m.group(0), "ratio": float(ratio), "labelled": bool(lab), "x": x, "y": y, "line": t[:80]})
  return out

def has_not_to_scale(lines: list[TextLine]) -> bool:
  return any(_NTS_RE.search(ln.text) for ln in lines)


_UNIT_PATTERNS = (
  ("ft-in", re.compile(r"DIMENSIONS?\s+(?:ARE\s+)?IN\s+(?:FEET\s*(?:&|AND|/)\s*INCH|FT\.?\s*(?:&|AND|-|/)\s*IN)", re.I)),
  ("mm", re.compile(r"(?:ALL\s+)?DIMENSIONS?\s+(?:ARE\s+)?(?:GIVEN\s+)?IN\s+(?:MM|MILLI\s?METE?RS?)\b", re.I)),
  ("m", re.compile(r"(?:ALL\s+)?DIMENSIONS?\s+(?:ARE\s+)?(?:GIVEN\s+)?IN\s+(?:METE?RS?|M)\b", re.I)),
  ("cm", re.compile(r"(?:ALL\s+)?DIMENSIONS?\s+(?:ARE\s+)?(?:GIVEN\s+)?IN\s+(?:CM|CENTI\s?METE?RS?)\b", re.I)),
  ("ft", re.compile(r"(?:ALL\s+)?DIMENSIONS?\s+(?:ARE\s+)?(?:GIVEN\s+)?IN\s+(?:FEET|FT|FOOT)\b", re.I)),
  ("mm", re.compile(r"\bUNITS?\s*[:=]\s*(?:MM|MILLI\s?METE?RS?)\b", re.I)),
  ("m", re.compile(r"\bUNITS?\s*[:=]\s*(?:METE?RS?|M)\b", re.I)),
  ("ft-in", re.compile(r"\bUNITS?\s*[:=]\s*(?:FEET\s*(?:&|AND)\s*INCH\w*|FT[- ]?IN)\b", re.I)),
  ("mm", re.compile(r"\(\s*ALL\s+(?:DIMS?|DIMENSIONS?)\s+IN\s+MM\s*\)", re.I)),
)

def find_units_hint(lines: list[TextLine]) -> str | None:
  joined = [ln.text for ln in lines]
  for unit, pat in _UNIT_PATTERNS:
    for t in joined:
      if pat.search(t):
        return unit
  return None

PAPERS = (
  ("A0", 841.0, 1189.0), ("A1", 594.0, 841.0), ("A2", 420.0, 594.0), ("A3", 297.0, 420.0), ("A4", 210.0, 297.0),
  ("ARCH E", 914.4, 1219.2), ("ARCH D", 609.6, 914.4), ("ARCH C", 457.2, 609.6), ("ARCH B", 304.8, 457.2), ("ARCH A", 228.6, 304.8),
  ("ANSI B", 279.4, 431.8), ("LETTER", 215.9, 279.4), ("LEGAL", 215.9, 355.6),
)

def paper_size(width_pt: float, height_pt: float, user_unit: float = 1.0) -> dict:
  w = width_pt * user_unit * MM_PER_INCH / 72.0
  h = height_pt * user_unit * MM_PER_INCH / 72.0
  lo, hi = min(w, h), max(w, h)
  best = None
  
  for name, pw, ph in PAPERS:
    err = max(abs(lo - pw) / pw, abs(hi - ph) / ph)
    if best is None or err < best[0]:
      best = (err, name, pw, ph)
  match = best is not None and best[0] <= 0.02
  return {"name": best[1] if match else None, "width_mm": round(w, 1), "height_mm": round(h, 1),
          "orientation": "LANDSCAPE" if w >= h else "PORTRAIT", "standard": bool(match),
          "nearest": best[1], "error_pct": round(best[0] * 100, 2)}

_SHEET_NO = re.compile(r"\b(?:DWG|DRG|DRAWING|SHEET)\.?\s*(?:NO|NUMBER|#)\.?\s*[:\-]?\s*(?P<n>[A-Z]{1,3}\s?[-.]?\s?\d{1,4}[A-Z]?(?:\.\d+)?)\b", re.I)
_PLAN_PHRASE = re.compile(
  r"\b(?P<p>(?:(?:GROUND|FIRST|SECOND|THIRD|FOURTH|FIFTH|TOP|BASEMENT|LOWER|UPPER|MEZZANINE|TYPICAL|ROOF|TERRACE|FOUNDATION|FOOTING|"
  r"COLUMN|BEAM|SLAB|SITE|LAYOUT|ELEVATION|SECTION|SECTIONAL|DETAIL|DETAILS|FLOOR|PLAN|SCHEDULE|FRAMING|STAIRCASE|PLUMBING|"
  r"ELECTRICAL|DRAINAGE|LIFT|SEPTIC|PARKING|BOUNDARY|MAIN)\s+){0,5}(?:PLANS?|LAYOUTS?|ELEVATIONS?|SECTIONS?|DETAILS?|SCHEDULES?))\b", re.I)
_LEVEL_WORDS = (
  ("BASEMENT", re.compile(r"\bBASEMENT\b|\bB\d\b|\bLOWER\s+GROUND\b", re.I)),
  ("GROUND", re.compile(r"\bGROUND\b|\bG\.?F\.?\b", re.I)),
  ("FIRST", re.compile(r"\bFIRST\b|\b1ST\b", re.I)),
  ("SECOND", re.compile(r"\bSECOND\b|\b2ND\b", re.I)),
  ("THIRD", re.compile(r"\bTHIRD\b|\b3RD\b", re.I)),
  ("FOURTH", re.compile(r"\bFOURTH\b|\b4TH\b", re.I)),
  ("MEZZANINE", re.compile(r"\bMEZZANINE\b", re.I)),
  ("ROOF", re.compile(r"\bROOF\b|\bTERRACE\b", re.I)),
  ("FOUNDATION", re.compile(r"\bFOUNDATION\b|\bFOOTING\b", re.I)),
  ("TYPICAL", re.compile(r"\bTYPICAL\b", re.I)),
)

COMPOSITE_VIEWS = 4
_STRUCTURAL_VIEW = re.compile(r"FRAMING|FOUNDATION|FOOTING|COLUMN|BEAM|SLAB|REINFORC|STEEL", re.I)

def title_hints(lines: list[TextLine]) -> dict:
  sheet_no = None
  phrases = []
  views = 0
  structural_views = 0
  for ln in lines:
    t = ln.text
    if sheet_no is None:
      m = _SHEET_NO.search(t)
      if m:
        sheet_no = re.sub(r"\s+", "", m.group("n")).upper()
    for m in _PLAN_PHRASE.finditer(t):
      p = re.sub(r"\s+", " ", m.group("p")).strip().upper()
      views += 1
      
      if _STRUCTURAL_VIEW.search(p):
        structural_views += 1
      if len(p.split()) >= 2:
        size = max((w.size for a, b, w in ln.spans if a >= m.start() and b <= m.end() + 1), default=0.0)
        phrases.append((size, len(p), p))
  title = None
  if phrases:
    phrases.sort(reverse=True)
    title = phrases[0][2]
  level = None
  if title:
    for key, pat in _LEVEL_WORDS:
      if pat.search(title):
        level = key
        break
  return {"sheet_no": sheet_no, "title": title, "level_hint": level, "views": views, "structural_views": structural_views,
    "composite": views >= COMPOSITE_VIEWS}

TAG_RE = re.compile(r"^[A-Z]{1,3}[-.]?\d{1,3}[A-Z]?$")

def is_tag(text: str) -> bool:
  t = (text or "").strip().upper()
  return bool(TAG_RE.match(t)) and not re.match(r"^(?:A[0-4]|ANSI|ISO)\d?$", t)
