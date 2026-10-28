from __future__ import annotations
AUTO_OK = ("VERIFIED", "VERIFIED_WEAK", "DIMENSIONS_ONLY", "ROOMS_ONLY", "OUTLINE_ONLY")
MIN_DECLARED_TRUST = 0.6
STRONG_CONFLICT_SUPPORT = 8

_NEEDS_PERSON = {
  "DECLARED_ONLY": "The scale printed on this sheet could not be trusted (a scanned or resized sheet, or more than one scale). Confirm the scale on the Measure page.",
  "CONFLICT": "The printed scale and the printed dimensions of this sheet disagree. Confirm the scale on the Measure page.",
  "CONFLICT_UNRESOLVED": "The printed scale and the few readable dimensions of this sheet disagree. Confirm the scale on the Measure page.",
  "MULTI_SCALE": "More than one drawing scale is on this sheet. Calibrate each view on the Measure page.",
  "DIMENSIONS_WEAK": "Only two printed dimensions could be read on this sheet. Confirm the scale on the Measure page.",
  "WITNESS_CONFLICT": "The scale found on this sheet and the room sizes written on its plan give different scales. Confirm the scale on the Measure page."
}

STANDARD = (1, 2, 5, 10, 20, 25, 30, 40, 48, 50, 75, 96, 100, 120, 150, 200, 250, 300, 400, 500)

def _hint(a: dict) -> str:
  """The scales the printed dimensions of the sheet suggest, as a short sentence; empty when none were read."""
  try:
    clusters = sorted(((a.get("measured") or {}).get("clusters") or []), key=lambda c: -float(c.get("weight") or 0))[:3]
    out = []
    for c in clusters:
      r = float(c["ratio"])
      near = min(STANDARD, key=lambda s: abs(r / s - 1.0))
      txt = f"1:{near}" if abs(r / near - 1.0) <= 0.05 else f"1:{r:.0f}"
      if txt not in out:
        out.append(txt)
    if out:
      return f" The printed dimensions suggest about {', '.join(out)}."
    for w in a.get("witnesses") or []:
      if w.get("source") == "ROOM_LABELS" and w.get("ratio") and not w.get("strong") and int(w.get("support") or 0) >= 2:
        return f" The {int(w['support'])} {'slab panel' if w.get('panels') else 'room'} sizes written on the plan that agree suggest about 1:{float(w['ratio']):.0f}, too few to rely on."
    return ""
  except Exception:
    return ""

def auto_scale_gate(analysis: dict | None) -> tuple:
  a = analysis or {}
  agreement, rec = a.get("agreement"), a.get("recommended")
  if rec is None or agreement in (None, "NONE"):
    hint = _hint(a)
    if hint:
      return False, "SCALE_NOT_FOUND", "The printed dimensions of this sheet do not agree on one scale and none is printed (it may show several views at different scales). Calibrate each view on the Measure page." + hint
    if (a.get("declared") or {}).get("not_to_scale"):
      return False, "SCALE_NOT_FOUND", "This sheet says it is not to be scaled and prints no scale or readable dimension. Set the scale on the Measure page from a length you know, or measure it by hand."
    return False, "SCALE_NOT_FOUND", "No scale or readable dimensions were found on this sheet. Set the scale on the Measure page."
  if agreement in AUTO_OK:
    return True, None, None
  if agreement == "DECLARED_ONLY" and (a.get("declared") or {}).get("not_to_scale"):
    return False, "SCALE_NEEDS_CONFIRMATION", "This sheet prints a scale and also says it is not to be scaled, and no printed dimension confirms the scale. Confirm the scale on the Measure page."
  if agreement == "DECLARED_ONLY" and float(rec.get("trust") or 0) >= MIN_DECLARED_TRUST:
    return True, None, None
  if agreement == "CONFLICT" and int(rec.get("support") or 0) >= STRONG_CONFLICT_SUPPORT:
    return True, None, None
  return False, "SCALE_NEEDS_CONFIRMATION", _NEEDS_PERSON.get(agreement, "The scale of this sheet is not confirmed. Confirm it on the Measure page.") + _hint(a)

def composite_issue(title: dict | None, others_read: bool):
  t = title or {}
  if not t.get("composite") or not others_read:
    return None
  if int(t.get("structural_views") or 0) >= 2:
    return None     
  return ("SET_ASIDE_COMPOSITE", "INFO", "This sheet shows several drawings at different scales (plans, sections, elevations, schedules). "
    "Its floor plans are read from their own sheets, so it is not read again here.")