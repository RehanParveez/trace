from __future__ import annotations

GAP_TOL = 0.015
MIN_PAIRS = 20
DOUBLE_SHARE = 0.4

def gap_of(unit: float, paper: str | None, notes_mm: list, peaks: list, scale: dict) -> dict:
  return {"notes_mm": list(notes_mm), "peaks": [[round(g, 3), int(n)] for g, n in peaks[:4]], "unit": unit, "paper": paper,
    "scale": {k: scale.get(k) for k in ("status", "mm_per_pt", "thickness_mm", "gap_pt", "pairs") if k in scale}}

def _found(g: dict | None) -> bool:
  return bool(g) and (g.get("scale") or {}).get("status") == "FOUND" and bool((g.get("scale") or {}).get("mm_per_pt"))

def _witness(own: dict, ref: dict) -> int | None:
  if not own.get("peaks") or float(own.get("unit") or 1.0) != float(ref.get("unit") or 1.0):
    return None
  gap, pairs = own["peaks"][0]
  ref_gap = float(ref["scale"]["gap_pt"])
  if pairs < MIN_PAIRS or abs(gap / ref_gap - 1.0) > GAP_TOL:
    return None
  double = max((n for g, n in own["peaks"] if abs(g / (2.0 * ref_gap) - 1.0) <= GAP_TOL), default=0)
  return int(pairs) if double >= DOUBLE_SHARE * pairs else None

def apply(sheets: list) -> list:
  refs = [(p, g) for p, g, _i in sheets if _found(g)]
  changed: list = []
  for page, gap, identity in sorted(sheets, key=lambda s: s[0]):
    if not identity or identity.get("basis") == "PERSON":
      continue
  
    own_found = _found(gap)
    best = None
    if gap and not own_found:
      for rp, rg in sorted(refs, key=lambda r: abs(r[0] - page)):
        if rp == page or rg.get("paper") != gap.get("paper"):
          continue
        pairs = _witness(gap, rg)
        if pairs is not None:
          best = {"mm_per_pt": float(rg["scale"]["mm_per_pt"]), "thickness_mm": rg["scale"].get("thickness_mm"), "gap_pt": float(rg["scale"]["gap_pt"]), "pairs": pairs, "from_page": rp}
          break
      
    if best is not None:
      if identity.get("scale_sibling") != best:
        identity["scale_sibling"] = best
        changed.append({"page": page, "from_page": best["from_page"], "mm_per_pt": best["mm_per_pt"]})
    elif identity.pop("scale_sibling", None) is not None:
      changed.append({"page": page, "from_page": None, "mm_per_pt": None})
  return changed
