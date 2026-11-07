from __future__ import annotations
import math
import re
from app.engine.measure import rule_registry as RR

RULE = "SLAB_TOP_EXTENTS"
META_KEY = "slab_top_extents"
MIN_CALLOUTS = 6
REACH_HEIGHTS = 6.0
CALLOUT = re.compile(r"^#(\d+)@(\d+(?:\.\d+)?)\"?(?:/(\d+(?:\.\d+)?)\")?C/?C$", re.I)
LENGTH = re.compile(r"^(\d+)'(?:-(\d+)(?:(\d+)/(\d+))?\")?$")

def enabled() -> bool:
  return RR.on(RULE)

def parse_callout(text: str) -> dict | None:
  m = CALLOUT.match((text or "").replace(" ", ""))
  if not m:
    return None
  return {"bar": int(m.group(1)), "spacing_in": float(m.group(2)), "end_spacing_in": float(m.group(3)) if m.group(3) else None}

def parse_length_ft(text: str) -> float | None:
  m = LENGTH.match((text or "").replace(" ", ""))
  if not m:
    return None
  inch = float(m.group(2) or 0)
  if m.group(3):
    inch += int(m.group(3)) / int(m.group(4))
  return int(m.group(1)) + inch / 12.0

def runs_along(angle: float) -> str:
  return "H" if round(float(angle or 0) / 90.0) % 2 == 0 else "V"

def _norm(w) -> str:
  return (w.text or "").strip().upper().strip(".,:;()")

def title_line(words: list) -> bool:
  slabs = [w for w in words or [] if _norm(w) == "SLAB"]
  lays = [w for w in words or [] if _norm(w) == "LAYOUT"]
  for s in slabs:
    for l in lays:
      h = max(float(s.height or 0), float(l.height or 0))
      if h <= 0 or abs(float(s.height) - float(l.height)) > 0.15 * h:
        continue
      if abs(s.cx - l.cx) + abs(s.cy - l.cy) <= 30 * h and (abs(s.cy - l.cy) <= 0.6 * h or abs(s.cx - l.cx) <= 0.6 * h):
        return True
  return False

def is_slab_plan(words: list) -> bool:
  return title_line(words) and sum(1 for w in words if parse_callout(w.text)) >= MIN_CALLOUTS

def pair(words: list) -> tuple:
  calls = [(w, c) for w in words for c in [parse_callout(w.text)] if c and c["end_spacing_in"] is None]
  lens = [(w, v) for w in words for v in [parse_length_ft(w.text)] if v is not None]
  options = []
  
  for i, (cw, _c) in enumerate(calls):
    reach = REACH_HEIGHTS * float(cw.height or 0)
    for j, (lw, _v) in enumerate(lens):
      if runs_along(lw.angle) != runs_along(cw.angle):
        continue
      d = math.hypot(lw.cx - cw.cx, lw.cy - cw.cy)
      if d <= reach:
        options.append((d, i, j))
        
  taken_c, taken_l, out = set(), set(), []
  for d, i, j in sorted(options):
    if i in taken_c or j in taken_l:
      continue
    taken_c.add(i)
    taken_l.add(j)
    cw, c = calls[i]
    out.append({"bar": c["bar"], "spacing_in": c["spacing_in"], "extent_ft": round(lens[j][1], 4), "runs": runs_along(cw.angle), "at": [round(cw.cx, 1), round(cw.cy, 1)], "gap_pt": round(d, 1)})
  return out, [calls[i][1] for i in range(len(calls)) if i not in taken_c]

def read(words: list) -> dict | None:
  if not enabled() or not is_slab_plan(words):
    return None
  pairs, left = pair(words)
  kinds: dict = {}
  
  for p in pairs:
    k = f"#{p['bar']}@{int(p['spacing_in']) if p['spacing_in'] == int(p['spacing_in']) else p['spacing_in']}"
    kinds.setdefault(k, []).append(p["extent_ft"])
  return {"read": "OK", "pairs": sorted(pairs, key=lambda p: (p["at"][1], p["at"][0])), "paired_by_kind": {k: sorted(v) for k, v in sorted(kinds.items())},
    "unpaired": len(left), "callouts": len(pairs) + len(left)}
