from __future__ import annotations
import re
from app.engine.measure import rule_registry as RR
from app.engine.measure import steel_grammar as SG
from app.modules.drawings_boq.takeoff.extract import structure_tables as ST

RULE = "BEAM_CALLOUTS"
CAPTION_MARK = re.compile(r"^[A-Z]{1,2}-?\d{1,2}$")
CAPTION_WORDS = ("BEAM",)
LINE_TOL = 3.0
LINE_GAP = 25.0
ABOVE_LINES = 20.0
PICTURE_LEFT = 60.0
PICTURE_RIGHT = 110.0
PICTURE_HEIGHT = 150.0
NOTE_REACH = 45.0

def enabled() -> bool:
  return RR.on(RULE)

def _line_of(words: list, mark) -> list:
  same = sorted([w for w in words if w.turn == 0 and abs(w.vc - mark.vc) <= LINE_TOL], key=lambda w: w.u0)
  at = same.index(mark)
  lo = at
  while lo > 0 and same[lo].u0 - same[lo - 1].u1 <= LINE_GAP:
    lo -= 1
  hi = at
  while hi < len(same) - 1 and same[hi + 1].u0 - same[hi].u1 <= LINE_GAP:
    hi += 1
  return same[lo:hi + 1]

def captions_of(words: list) -> list:
  out = []
  for w in words:
    if w.turn != 0 or not CAPTION_MARK.match(w.text.upper()):
      continue
    
    line = _line_of(words, w)
    at = line.index(w)
    if at == 0 or line[at - 1].text.upper().strip(".:") not in CAPTION_WORDS:
      continue
    
    top = max(x.vc for x in line)
    centre = sum(x.uc for x in line) / len(line)
    for x in words:
      if x.turn == 0 and 0 < x.vc - top <= ABOVE_LINES and min(l.u0 for l in line) - LINE_GAP <= x.uc <= max(l.u1 for l in line) + LINE_GAP:
        top = max(top, x.vc)
    out.append({"mark": w.text.upper().replace("-", ""), "u": centre, "top": top, "word": w})
  return out

def _is_note(words: list, w) -> bool:
  return any(o is not w and o.turn == 0 and abs(o.vc - w.vc) <= LINE_TOL and 0 <= o.u0 - w.u1 <= NOTE_REACH and re.match(r"^[A-Za-z]{2,}", o.text) for o in words)

def callouts_in(words: list) -> list:
  out = []
  for w in words:
    if w.turn != 0:
      continue
    
    got = SG.parse_callout(w.text)
    if got["bars"] and not got["unread"] and got["bars"][0].get("n") and got["bars"][0].get("bar") and not got["spaced"]:
      b = got["bars"][0]
      out.append({"kind": "BARS", "text": f"{b['n']}-#{b['bar']}", "n": b["n"], "bar": b["bar"], "u": w.uc, "v": w.vc, "note": _is_note(words, w)})
    elif got["spaced"] and not got["unread"] and not got["bars"]:
      out.append({"kind": "RING", "text": w.text, "bar": got["spaced"][0]["bar"], "spacing_mm": got["spaced"][0]["spacing_mm"], "u": w.uc, "v": w.vc, "note": False})
  return out

def read_words(words: list) -> dict | None:
  caps = captions_of(words)
  if not caps:
    return None
  taken: dict = {c["mark"]: [] for c in caps}
  for c in callouts_in(words):
    if c["note"]:
      continue
    near = [k for k in caps if k["u"] - PICTURE_LEFT <= c["u"] <= k["u"] + PICTURE_RIGHT and k["top"] + 3 <= c["v"] <= k["top"] + PICTURE_HEIGHT]
    if not near:
      continue
    
    best = min(near, key=lambda k: abs(c["u"] - (k["u"] + 30.0)))
    taken[best["mark"]].append(c)
  sections = []
  
  for cap in caps:
    mine = taken[cap["mark"]]
    bars = sorted([c for c in mine if c["kind"] == "BARS"], key=lambda c: -c["v"])
    rings = [c for c in mine if c["kind"] == "RING"]
    rec = {"mark": cap["mark"], "top": None, "bottom": None, "stirrup": None, "reasons": []}
    if len(bars) >= 2:
      rec["top"], rec["bottom"] = bars[0]["text"], bars[-1]["text"]
    elif len(bars) == 1:
      rec["reasons"].append("JOIN_MISSING")
    if rings and len(bars) >= 2:
      rec["stirrup"] = rings[0]["text"]
    if rec["top"]:
      sections.append(rec)
  return {"kind": "BEAM_CALLOUTS", "sections": sections} if sections else None

def read(raw) -> dict | None:
  if not enabled() or not raw.words:
    return None
  words, _ = ST.upright_words(raw)
  return read_words(words)
