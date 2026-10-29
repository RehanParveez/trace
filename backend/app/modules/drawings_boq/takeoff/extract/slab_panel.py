from __future__ import annotations

def inch_text(mm: float) -> str:
  return f"{mm / 25.4:g}\""

def parts(head: str, sep: str, tail: str) -> dict:
  return {"head": head, "sep": sep, "tail": tail}

def compose(label_parts: dict, thickness_mm) -> str:
  return label_parts["head"] + (label_parts["sep"] + inch_text(float(thickness_mm)) if thickness_mm else "") + label_parts["tail"]

def current(cand) -> str:
  lp = (cand.facts or {}).get("label_parts")
  if not lp:
    return cand.label
  return compose(lp, (cand.params or {}).get("depth_mm"))