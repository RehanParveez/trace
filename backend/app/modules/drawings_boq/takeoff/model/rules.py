from __future__ import annotations
import re
from app.engine.measure import rule_formulas as RF

WEB_BELOW_SLAB, FULL_DEPTH = "WEB_BELOW_SLAB", "FULL_DEPTH"
FULL_DEPTH_ROLES = ("PLINTH", "BAND")
FULL_DEPTH_MARKS = ("GB", "PB", "TB")

def depth_basis(beam_role: str | None, mark: str | None, includes_slab: bool, upstand: bool = False) -> str | None:
  if upstand:
    return None
  letters = re.sub(r"[^A-Z]", "", str(mark or "").upper())
  if beam_role in FULL_DEPTH_ROLES or letters in FULL_DEPTH_MARKS:
    return FULL_DEPTH
  return WEB_BELOW_SLAB if includes_slab else FULL_DEPTH

def beam_web(depth_mm: float, slab_mm: float | None, basis: str | None) -> dict | None:
  if basis is None or not depth_mm:
    return None
  if basis == FULL_DEPTH or slab_mm is None:
    return {"web_mm": float(depth_mm), "basis": basis, "slab_mm": slab_mm}
  return {**RF.web_below_slab({}, {"beam_depth_mm": depth_mm, "slab_mm": slab_mm, "includes_slab": True}), "basis": basis, "slab_mm": slab_mm}
