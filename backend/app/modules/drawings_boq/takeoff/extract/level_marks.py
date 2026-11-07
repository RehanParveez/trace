from __future__ import annotations
import re
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.prep import storeys as SR

RULE = "LEVEL_MARK_ITEMS"
META_KEY = "level_mark_items"
SOURCE_KEY = "level_marks"
SAME_LINE = 0.5
GAP_SIZES = 1.5
MAX_INCH = 12 * 120
SIGNS = ("+", "-", "±", "+/-")
_FRAMES = {0: ((1.0, 0.0), (0.0, -1.0)), 90: ((0.0, 1.0), (1.0, 0.0)), 180: ((-1.0, 0.0), (0.0, 1.0)), 270: ((0.0, -1.0), (-1.0, 0.0))}
_Q = "[\"”″]"
_FOOT = r"(?P<ft>\d{1,3})\s*['’′]\s*(?:-?\s*(?P<in>\d{1,2}(?:\s+\d/\d)?)\s*" + _Q + r"?)?"
_INCH_ONLY = r"(?P<only>\d{1,3})\s*" + _Q
_VALUE = re.compile(r"^(?:" + _FOOT + "|" + _INCH_ONLY + r")$")
_GLUED = re.compile(r"(?<![\d'\"’′”″-])(?P<sign>\+/-|[+±])\s*(?P<v>" + _FOOT + "|" + _INCH_ONLY + r")$")
_NAME_WORD = re.compile(r"^[A-Za-z][A-Za-z.]*$")
_NAME_END = re.compile(r"^LEV(?:EL)?\.?$", re.I)

def enabled() -> bool:
  return RR.on(RULE)

def _inches(m) -> float | None:
  if m.group("only") is not None:
    return float(m.group("only"))
  inch = 0.0
  if m.group("in"):
    parts = m.group("in").split()
    inch = float(parts[0])
    if len(parts) > 1:
      a, b = parts[1].split("/")
      inch += float(a) / float(b)
  return int(m.group("ft")) * 12.0 + inch

class _W:
  __slots__ = ("w", "angle", "u", "v", "half", "size")
  def __init__(self, w, angle: int):
    (ax, ay), (dx, dy) = _FRAMES[angle]
    cx, cy = (w.x0 + w.x1) / 2, (w.y0 + w.y1) / 2
    self.w, self.angle, self.size = w, angle, max(float(w.size or 0.0), 1.0)
    self.u, self.v = cx * ax + cy * ay, cx * dx + cy * dy
    self.half = max(float(w.length or 0.0), 0.0) / 2.0

def _upright(words: list) -> list:
  out = []
  for w in words or []:
    if not (w.text or "").strip():
      continue
    a = SR._snap(w.angle)
    if a is not None:
      out.append(_W(w, a))
  return out

def _next_on_line(a: _W, ws: list) -> _W | None:
  best = None
  for x in ws:
    if x is a or x.angle != a.angle or abs(x.v - a.v) > SAME_LINE * a.size:
      continue
    gap = (x.u - x.half) - (a.u + a.half)
    if -0.3 * a.size <= gap <= GAP_SIZES * a.size and x.u > a.u and (best is None or x.u < best.u):
      best = x
  return best

def _name_after(last: _W, ws: list) -> tuple:
  words, cur = [], last
  while True:
    nxt = _next_on_line(cur, ws)
    if nxt is None or not _NAME_WORD.match((nxt.w.text or "").strip()):
      break
    words.append(nxt)
    cur = nxt
  while words and not _NAME_END.match(words[-1].w.text.strip()):
    words.pop()
  return words

def _box(parts: list) -> list:
  xs0, ys0 = min(p.w.x0 for p in parts), min(p.w.y0 for p in parts)
  xs1, ys1 = max(p.w.x1 for p in parts), max(p.w.y1 for p in parts)
  return [round((xs0 + xs1) / 2, 1), round((ys0 + ys1) / 2, 1)]

def _mark(sign: str, value: str, name: list) -> str:
  return f"{sign} {value}" + (" " + " ".join(n.w.text.strip() for n in name) if name else "")

def marks_of(words: list) -> list:
  ws = _upright(words)
  out, seen = [], set()
  
  for a in ws:
    text = (a.w.text or "").strip()
    parts, sign, value, rest = [a], None, None, None
    if text in SIGNS:
      nxt = _next_on_line(a, ws)
      if nxt is None:
        continue
      m = _VALUE.match((nxt.w.text or "").strip())
      if not m:
        continue
      sign, value, rest = text, m, nxt
      parts.append(nxt)
    else:
      g = _GLUED.search(text)
      if not g:
        continue
      sign, rest = g.group("sign"), a
      value = _VALUE.match(g.group("v"))
      if not value:
        continue
    inches = _inches(value)
    if inches is None or inches > MAX_INCH:
      continue
    
    name = _name_after(rest, ws)
    parts += name
    glued = rest is a and sign in SIGNS and text not in SIGNS
    signed = -inches if sign == "-" else inches
    shown = (rest.w.text.strip() if sign in SIGNS and rest is not a else _GLUED.search(text).group("v"))
    mark = _mark("±" if sign == "+/-" else sign, shown, name)
    at = _box(parts)
    
    if glued and not name and len(text) > 0:
      g = _GLUED.search(text)
      frac = (g.start() + (len(text) - g.start()) / 2.0) / len(text)
      (ax, ay), _d = _FRAMES[a.angle]
      shift = (frac - 0.5) * 2.0 * a.half
      at = [round(at[0] + ax * shift, 1), round(at[1] + ay * shift, 1)]
    key = (mark, at[0], at[1])
    if key in seen:
      continue
    seen.add(key)
    out.append({"mark": mark, "value_in": signed, "at": at})
  return sorted(out, key=lambda r: (r["at"][1], r["at"][0]))

def read(raw) -> dict | None:
  if not enabled() or not raw.words:
    return None
  got = marks_of(raw.words)
  return {"marks": got} if got else None

def apply(rows: list) -> int:
  made = 0
  for row in rows:
    meta = row.get("meta")
    if meta is None:
      continue
    meta.pop(META_KEY, None)
    if not enabled():
      continue
    if (meta.get("identity") or {}).get("role") in SKIPPED_ROLES:
      continue
    marks = ((meta.get("structure_tables") or {}).get(SOURCE_KEY) or {}).get("marks") or []
    if marks:
      meta[META_KEY] = {"marks": marks}
      made += len(marks)
  return made

SKIPPED_ROLES = ("DIVIDER", "LEGEND", "INDEX", "SCHEDULE")
