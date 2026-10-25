from __future__ import annotations
import math
import re
import statistics
from app.modules.drawings_boq.takeoff.prep import facts as F

GUTTER_SHARE = 0.01
BULLETS = ("•", "●", "·", "*", "-")
MIN_WORDS = 80
MIN_HEADINGS = 3
UNIT_MM = 25.4
BAR_EIGHTH_MM = 3.175
_HEADING = re.compile(r"^[A-Z][A-Z &/,\-]{3,60}$")
_NUM = r"(?:\d{1,2}(?:\s*\d/\d)?|\d/\d|[½¼¾⅛⅜⅝⅞])"
_INCH_MARK = r"(?:''|’’|”|″|\")?"
_VALUE = re.compile(r"(?P<v>" + _NUM + r")\s*" + _INCH_MARK + r"\s*$")
_STRENGTH = re.compile(r"\bCONCRE\w*\s+FOR\s+(?P<scope>[A-Z&, ]+?)\s+TO\s+HAVE\b.*?\bMINIMUM\s+OF\s+(?P<psi>\d{3,5})\s*(?:P\.?\s?S\.?\s?I\.?)", re.I)
_GRADE = re.compile(r"\b(?:GRADE\s+(?P<g1>40|60|75)|(?P<g2>40|60|75)\s+GRADE)\b", re.I)
_BINDERS = re.compile(r"\b(?:BINDERS?|STIRRUPS?|TIES|LINKS?|HOOPS?)\b", re.I)
_BAR_TOKEN = re.compile(r"^#(?P<n>\d{1,2})$")
_INCH_TOKEN = re.compile(r"^(?P<v>\d{1,3})\s*(?:''|’’|”|″|\")$")
COVER_SCOPES = (("FOUNDATION", ("footing",)), ("SLAB", ("slab",)), ("COLUMN", ("column", "beam")), ("BEAM", ("beam",)), ("WALL", ("wall",)))

def _columns(words: list) -> list:
  spans = [(float(w.x0), float(w.x0) + float(w.length)) for w in words]
  lo, hi = min(s[0] for s in spans), max(s[1] for s in spans)
  width = int(math.ceil(hi - lo)) + 1
  cover = [0] * width
  for a, b in spans:
    for i in range(max(0, int(a - lo)), min(width, int(math.ceil(b - lo)) + 1)):
      cover[i] += 1

  limit = max(2, int(GUTTER_SHARE * len(words)))
  size = statistics.median(float(w.size) for w in words)
  gaps, start = [], None
  for i, c in enumerate(cover + [limit + 1]):
    if c <= limit and start is None:
      start = i
    elif c > limit and start is not None:
      if i - start >= 1.5 * size and start > 0 and i < width:
        gaps.append((lo + start, lo + i))
      start = None
  edges = [lo - 1.0] + [m for g in gaps for m in ((g[0] + g[1]) / 2.0,)] + [hi + 1.0]
  return list(zip(edges, edges[1:]))

def _rows(words: list) -> list:
  out: list = []
  for w in sorted(words, key=lambda w: (-w.cy, w.x0)):
    if out and abs(out[-1]["cy"] - w.cy) <= 0.5 * max(float(w.size), out[-1]["size"]):
      out[-1]["words"].append(w)
      out[-1]["size"] = max(out[-1]["size"], float(w.size))
    else:
      out.append({"cy": w.cy, "size": float(w.size), "words": [w]})
      
  for r in out:
    r["words"].sort(key=lambda w: w.x0)
    r["texts"] = [w.text for w in r["words"]]
    r["text"] = " ".join(r["texts"]).strip()
  return out

def _is_heading(r: dict) -> bool:
  t = r["text"].strip()
  return bool(_HEADING.match(t)) and not t.startswith(BULLETS) and len(r["words"]) <= 8

def read_columns(words: list | None) -> list:
  ws = [w for w in (words or []) if abs(((w.angle + 45) % 90) - 45) <= 6 and round(w.angle / 90.0) % 4 == 0 and w.text.strip()]
  if len(ws) < MIN_WORDS:
    return []
  out: list = []
  headings = 0

  for lo, hi in _columns(ws):
    rows = _rows([w for w in ws if lo <= w.cx < hi])
    heading = None
    for r in rows:
      if _is_heading(r):
        heading = r["text"].strip()
        headings += 1
        continue
      out.append({"heading": heading, "row": r})
  return out if headings >= MIN_HEADINGS else []

def entries(cols: list) -> list:
  out: list = []
  for item in cols:
    r, head = item["row"], item["heading"]
    texts = r["texts"]
    bullet = bool(texts) and texts[0] in BULLETS
    text = " ".join(t for t in texts if t not in BULLETS).strip()

    if not text:
      continue
    if bullet or not out or out[-1]["heading"] != head:
      out.append({"heading": head, "text": text, "rows": [r["texts"]]})
    else:
      out[-1]["text"] += " " + text
      out[-1]["rows"].append(r["texts"])
  return out

def _fraction_mm(raw: str) -> float | None:
  s = F._fix(raw).strip()
  return F.inches_mm(s)

def _scope_words(raw: str) -> str:
  return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z&, ]+", " ", raw or "")).strip().lower()

def items_of(entry: dict) -> list:
  head, text = (entry["heading"] or "").upper(), entry["text"]
  fixed = F._fix(text)

  out: list = []
  if "CONCRETE" in head and "PROTECTION" not in head:
    m = _STRENGTH.search(fixed)
    if m:
      out.append(F._item("CONCRETE_CLASS", fixed, concrete_class=None, mix=f"{int(m.group('psi'))} psi", scope=_scope_words(m.group("scope"))))
  if "STEEL" in head:
    m = _GRADE.search(fixed)
    if m:
      grade = int(m.group("g1") or m.group("g2"))
      out.append(F._item("STEEL_GRADE", fixed, grade=grade, scope="stirrups" if _BINDERS.search(fixed) else "all bars"))
  if "COVER" in head or "PROTECTION" in head:
    out.extend(_covers(entry))
  return out

def _covers(entry: dict) -> list:
  out: list = []
  label = None

  for texts in entry["rows"]:
    row = F._fix(" ".join(t for t in texts if t not in BULLETS).strip())
    m = _VALUE_ROW.match(row)
    name = (m.group("label") if m else row).strip(" .")
    up = name.upper()
    scopes = next((s for key, s in COVER_SCOPES if key in up), None)
    where = ""

    if scopes is None and label is not None and "FACE" in up:
      scopes, where = label, _scope_words(name)
    elif scopes is not None:
      label = scopes
    if not m or scopes is None:
      continue
    mm = _fraction_mm(m.group("v"))
    if mm is None:
      continue
    for scope in scopes:
      out.append(F._item("CLEAR_COVER", row, value_mm=mm, scope=scope, where=where))
  return out
_VALUE_ROW = re.compile(r"^(?P<label>.*?[A-Za-z\)])\s+(?P<v>" + _NUM + r")\s*" + _INCH_MARK + r"\s*$")

def lap_items(cols: list) -> list:
  rows = [c["row"] for c in cols]
  out: list = []

  for i, r in enumerate(rows):
    bars = [m for m in (_BAR_TOKEN.match(t) for t in r["texts"]) if m]
    if len(bars) < 3 or len(bars) != len(r["texts"]):
      continue

    for nxt in rows[i + 1:i + 3]:
      toks = nxt["texts"]
      if toks and toks[0].isdigit() and int(toks[0]) in (40, 60, 75) and len(toks) == len(bars) + 1:
        vals = [_INCH_TOKEN.match(t) for t in toks[1:]]
        if all(vals):
          for b, v in zip(bars, vals):
            dia = int(b.group("n")) * BAR_EIGHTH_MM
            out.append(F._item("LAP_LENGTH", " ".join(toks), value_mm=round(int(v.group("v")) * UNIT_MM, 2), bar_dia_mm=round(dia, 3), scope=f"lap bar {int(b.group('n'))}", grade=int(toks[0])))
        break
  return out

def read(words: list | None) -> list:
  cols = read_columns(words)
  if not cols:
    return []
  out: list = []
  for e in entries(cols):
    out.extend(items_of(e))
  out.extend(lap_items(cols))
  return out
