from __future__ import annotations
from app.engine.measure.steel_grammar import parse_callout

def options(drawings: list) -> list:
  out: list = []
  seen: set = set()
  for d in drawings or []:
    for text in d.get("bar_notes") or []:
      for s in parse_callout(text).get("spaced") or []:
        key = (s.get("bar"), s.get("dia_mm"), s["spacing_mm"])
        if key in seen:
          continue
        seen.add(key)
        out.append({"text": text, "bar": s.get("bar"), "dia_mm": s.get("dia_mm"), "spacing_mm": s["spacing_mm"], "view": d.get("view"), "page_no": d.get("page_no")})
  return out
