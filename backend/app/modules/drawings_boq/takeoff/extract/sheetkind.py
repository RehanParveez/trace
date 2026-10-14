from __future__ import annotations
import re

STRUCTURAL = re.compile(r"\b(?:FOUNDATIONS?|FOOTINGS?\s+(?:LAYOUT|PLAN)|COLUMN\s+(?:LAYOUT|PLAN|LOCATION)|COLUMNS?\s+AND\s+FOOTINGS?|"
  r"(?:ROOF|FLOOR|GROUND|FIRST|SECOND)\s+(?:BEAM|BEAMS|SLAB)\s*(?:LAYOUT|PLAN|AND|&|FRAMING)?|BEAMS?\s+(?:LAYOUT|PLAN)|SLAB\s+(?:LAYOUT|PLAN)|"
  r"FRAMING\s+PLAN|STRUCTURAL|REINFORCEMENT|TIE\s+BEAM|PLINTH\s+BEAM)\b", re.I)
PLAN = re.compile(r"\b(?:(?:GROUND|FIRST|SECOND|THIRD|TYPICAL|UPPER|LOWER|BASEMENT|MEZZANINE|MEZZ|TERRACE)\s+FLOOR\s+PLAN|FLOOR\s+PLAN|"
  r"ARCHITECTURAL\s+PLAN|LAYOUT\s+PLAN|BASEMENT\s+PLAN|ROOF\s+PLAN|MUMTY|(?:GROUND|FIRST|SECOND|THIRD)\s+FLOOR)\b", re.I)

def sheet_kind(words: list) -> dict:
  
  best = None  
  by_line: dict = {}
  for w in words:
    if abs(((w.angle + 45) % 90) - 45) > 6:
      continue
    by_line.setdefault((round(w.angle / 90.0) % 4, round(w.cy / max(w.size * 0.6, 1.0))), []).append(w)
    
  for ws in by_line.values():
    ws.sort(key=lambda o: o.x0)
    text = " ".join(o.text for o in ws)
    size = max(o.size for o in ws)
    struct = bool(STRUCTURAL.search(text))
    plan = bool(PLAN.search(text)) and not struct
    if not plan and not struct:
      continue
    cand = (size, plan, text[:80])
    
    if best is None or (cand[0], cand[1]) > (best[0], best[1]):
      best = cand
  if best is None:
    return {"kind": "UNKNOWN", "title": None}
  return {"kind": "PLAN" if best[1] else "STRUCTURAL", "title": best[2]}