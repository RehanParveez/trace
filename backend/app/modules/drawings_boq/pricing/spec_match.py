from __future__ import annotations
import re
from app.modules.drawings_boq.pricing.mrs_spec import mix_of

ORDER = ("member", "part", "mix", "psi", "grade", "thick")
MM_PER_IN = 25.4
THICK_TOL_MM = 5.0                                        
MEMBER_OF_CODE = {"CON-PCC": "plain"}
_PSI = re.compile(r"\b(\d{4})\s*psi\b", re.I)
_STEEL = re.compile(r"\bG[-\s]?(\d{2})\b|\bgrade[\s-]*(\d{2})\b", re.I)
_THICK = re.compile(r"^(<=|>)(\d+(?:\.\d+)?)in$")

def parse_spec(text: str | None) -> dict | None:
  out: dict = {}
  for part in str(text or "").lower().split(";"):                
    key, _, value = part.partition("=")
    if key not in ORDER or not value:
      return None
    out[key] = value
  return out or None

def split_code(code: str) -> tuple:
  base, at, tail = str(code).partition("@")
  if not at or "~" in tail:
    return base, None
  return base, parse_spec(tail)

def stated_spec(item) -> dict:
  code = str(getattr(item, "work_item_code", None) or "").upper()
  grade = str(getattr(item, "material_grade", None) or "")
  raw = getattr(item, "spec", None)
  spec = raw if isinstance(raw, dict) else {}
  params = spec.get("params") if isinstance(spec.get("params"), dict) else {}
  
  out: dict = {}
  if code in MEMBER_OF_CODE:
    out["member"] = MEMBER_OF_CODE[code]
  for text in (spec.get("mortar"), spec.get("grade"), grade):
    mix = mix_of(str(text)) if text else None
    if mix:
      out["mix"] = mix
      break
  for text in (spec.get("grade"), grade):
    found = _PSI.search(str(text or ""))
    if found:
      out["psi"] = found.group(1)
      break
  if code.startswith("STL-"):
    found = _STEEL.search(grade)
    if found:
      out["grade"] = found.group(1) or found.group(2)
  thickness = spec.get("thickness_mm")
  if thickness is None:
    thickness = params.get("plaster_thickness_mm") if code.startswith("FIN-PLASTER") else params.get("pcc_thickness_mm") if code == "CON-PCC" else None
    
  try:
    if thickness is not None and float(thickness) > 0:
      out["thick_mm"] = float(thickness)
  except (TypeError, ValueError):
    pass
  return out

def matches(rate: dict, stated: dict) -> tuple:
  gap = None
  
  for key, value in rate.items():
    if key == "thick":
      shown, found = stated.get("thick_mm"), _THICK.match(value)
      if shown is None or found is None:
        return False, None
      limit = float(found.group(2)) * MM_PER_IN
      if found.group(1) == "<=":
        if shown > limit + THICK_TOL_MM:
          return False, None
        gap = limit - shown
      else:
        if shown <= limit + THICK_TOL_MM:
          return False, None
        gap = shown - limit
    elif stated.get(key) != value:
      return False, None
  return True, gap

def choose(published: list, stated: dict) -> dict:
  agreeing = []
  for spec, code in published:
    ok, gap = matches(spec, stated)
    if ok:
      agreeing.append((len(spec), -(gap if gap is not None else 0.0), code, spec))
  if not agreeing:
    return {}

  agreeing.sort(key=lambda r: (-r[0], -r[1], r[2]))
  best = agreeing[0]
  tied = [r for r in agreeing if (r[0], round(r[1], 3)) == (best[0], round(best[1], 3)) and r[3] != best[3]]
  if tied:
    return {"ambiguous": sorted({best[2], *(r[2] for r in tied)})}
  return {"code": best[2], "spec": best[3]}
