from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.extract import structure_tables as ST

BAR_HEADER = re.compile(r"^#([3-9])$")
INCH = re.compile(r"^(\d+)\"")
CM = re.compile(r"(\d+)\s*cm")
ROW_TOL = 3.0
ELEMENTS = (("FOOTING", ("FOOTING",)), ("SLAB_WALL", ("SLABS,WALLS", "SLABS", "WALLS")), ("COLUMN_BEAM", ("COLUMNS",)), ("RAFT", ("RAFT",)))
FRACTION = re.compile(r"^(?:(\d+)\s+)?(\d+)/(\d+)\"?$")

def _row(words: list, ref, left: float = -5.0, right: float = 330.0) -> list:
  return sorted([w for w in words if abs(w.vc - ref.vc) <= ROW_TOL and ref.u0 + left <= w.u0 <= ref.u0 + right], key=lambda w: w.u0)

def _inches(tokens: list) -> float | None:
  for i, t in enumerate(tokens):
    m = re.match(r"^(\d+)\"$", t)
    if m:
      return float(m.group(1))
    m = re.match(r"^(\d+)/(\d+)\"$", t)
    if m:
      whole = float(tokens[i - 1]) if i and re.match(r"^\d+$", tokens[i - 1]) else 0.0
      return whole + int(m.group(1)) / int(m.group(2))
  return None

def _headings(words: list, pattern: str) -> list:
  return [w for w in words if re.search(pattern, w.text.upper())]

def _element_of(text: str) -> str | None:
  t = text.upper()
  for name, keys in ELEMENTS:
    if any(t.startswith(k) for k in keys):
      return name
  return None

def _heading_above(words: list, anchor, patterns: dict) -> str | None:
  best, name = None, None
  for label, pat in patterns.items():
    for w in _headings(words, pat):
      if w.vc > anchor.vc and w.vc - anchor.vc <= 90.0 and w.u0 - 5.0 <= anchor.u0 + 160.0 and w.u1 + 5.0 >= anchor.u0 - 10.0:
        if best is None or w.vc - anchor.vc < best:
          best, name = w.vc - anchor.vc, label
          
  return name

def element_lists(words: list) -> list:
  out, seen = [], set()
  for w in sorted(words, key=lambda w: (-w.vc, w.u0)):
    el = _element_of(w.text)
    if not el or w.turn != 0:
      continue
    row = _row(words, w, right=140.0)
    toks = [x.text for x in row[1:] if x.u0 < w.u0 + 140.0]
    
    if el == "COLUMN_BEAM":
      toks = [t for t in toks if t not in ("&", "BEAMS")]
    value = _inches(toks)
    if value is None:
      continue
    kind = _heading_above(words, w, {"COVER": r"^COVER$", "AGGREGATE": r"AGGREGATE"})
    if kind is None or (kind, el) in seen:
      continue
    seen.add((kind, el))
    if kind == "COVER" and el in ("RAFT",):
      continue
    out.append({"key": f"{kind}_{el}", "value": round(value, 3), "unit": "in", "uv": [round(w.uc, 1), round(w.vc, 1)]})
    
  return out

def bar_tables(words: list) -> list:
  out = []
  heads = sorted([w for w in words if w.turn == 0 and BAR_HEADER.match(w.text)], key=lambda w: (-w.vc, w.u0))
  rows: dict = {}
  
  for w in heads:
    rows.setdefault(round(w.vc / ROW_TOL), []).append(w)
  for hs in rows.values():
    hs.sort(key=lambda w: w.u0)
    if len(hs) < 5:
      continue
  
    v0, u0, u1 = max(h.vc for h in hs), min(h.u0 for h in hs), max(h.u1 for h in hs)
    title = None
    for label, pat in (("EMBEDMENT", r"EMBEDMENT"), ("LAP", r"^LAP$")):
      if any(v0 < t.vc <= v0 + 70.0 and u0 - 400.0 <= t.u0 <= u1 + 20.0 for t in _headings(words, pat)):
        title = label if title is None else title
    if title is None:
      continue
  
    band = [w for w in words if w.turn == 0 and v0 - 22.0 <= w.vc < v0 - 3.0 and u0 - 25.0 <= w.uc <= u1 + 45.0 and INCH.match(w.text)]
    for h in hs:
      cand = sorted([w for w in band if abs(w.uc - h.uc) <= 22.0], key=lambda w: abs(w.uc - h.uc))
      if not cand:
        continue
      out.append({"key": f"{title}_{h.text[1:]}", "value": float(INCH.match(cand[0].text).group(1)), "unit": "in", "uv": [round(h.uc, 1), round(h.vc, 1)]})
  return out

def curtailment(words: list) -> list:
  out = []
  
  for w in words:
    if w.turn == 0 and w.text.upper() == "CUT":
      row = _row(words, w, right=420.0)
      text = " ".join(x.text for x in row).upper()
      m = re.search(r"FOR (TOP|BOTTOM) REINFORCEMENT.*?\b(L/\d+)\b", text)
      if m:
        out.append({"key": f"CURTAILMENT_{m.group(1)}", "value": m.group(2), "uv": [round(w.uc, 1), round(w.vc, 1)]})
    if w.turn == 0 and w.text.upper() == "FOR":
      row = _row(words, w, left=-2.0, right=420.0)
      text = " ".join(x.text for x in row).upper()
      m = re.match(r"FOR (BOTTOM) REINFORCEMENT SHALL BE (L/\d+)\b", text)
      if m:
        out.append({"key": "CURTAILMENT_BOTTOM", "value": m.group(2), "uv": [round(w.uc, 1), round(w.vc, 1)]})
        
  seen, keep = set(), []
  for f in out:
    if f["key"] not in seen:
      seen.add(f["key"])
      keep.append(f)
  return keep

def spacing_rules(words: list) -> list:
  out = []
  
  text = " ".join(w.text for w in sorted(words, key=lambda w: (-round(w.vc / ROW_TOL), w.u0))).upper()
  if re.search(r"ONE HALF ADJACENT BAR SPACING", text) and re.search(r"FIRST AND LAST BARS", text):
    anchor = next((w for w in words if w.text.upper() == "HALF"), None)
    out.append({"key": "FIRST_LAST_BAR_START_AT_MAX_HALF_SPACING", "value": 0.5, "unit": "of adjacent spacing", "uv": [round(anchor.uc, 1), round(anchor.vc, 1)] if anchor else None})
  smaller = next((w for w in words if w.text.upper() == "SMALLER"), None)
  if smaller and any(w.text.upper() == "GOVERNED" and 0 < w.vc - smaller.vc <= 30.0 and abs(w.u0 - smaller.u0) <= 220.0 for w in words):
    out.append({"key": "LAP_DIFFERENT_SIZES_GOVERNED_BY", "value": "smaller bar", "uv": None})
  return out

def read(raw) -> dict | None:
  if not raw.words:
    return None
  words, _f = ST.upright_words(raw)
  facts = element_lists(words) + bar_tables(words) + curtailment(words) + spacing_rules(words)
  if len(facts) < 4:
    return None
  return {"kind": "REBAR_RULES", "facts": facts}
