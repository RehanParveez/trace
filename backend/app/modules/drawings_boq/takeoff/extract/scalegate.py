from __future__ import annotations
AUTO_OK = ("VERIFIED", "VERIFIED_WEAK", "DIMENSIONS_ONLY")
MIN_DECLARED_TRUST = 0.6
STRONG_CONFLICT_SUPPORT = 8

_NEEDS_PERSON = {
  "DECLARED_ONLY": "The scale printed on this sheet could not be trusted (a scanned or resized sheet, or more than one scale). Confirm the scale on the Measure page.",
  "CONFLICT": "The printed scale and the printed dimensions of this sheet disagree. Confirm the scale on the Measure page.",
  "CONFLICT_UNRESOLVED": "The printed scale and the few readable dimensions of this sheet disagree. Confirm the scale on the Measure page.",
  "MULTI_SCALE": "More than one drawing scale is on this sheet. Calibrate each view on the Measure page.",
  "DIMENSIONS_WEAK": "Only two printed dimensions could be read on this sheet. Confirm the scale on the Measure page.",
}

def auto_scale_gate(analysis: dict | None) -> tuple:
  a = analysis or {}
  agreement, rec = a.get("agreement"), a.get("recommended")
  if rec is None or agreement in (None, "NONE"):
    return False, "SCALE_NOT_FOUND", "No scale or readable dimensions were found on this sheet. Set the scale on the Measure page."
  if agreement in AUTO_OK:
    return True, None, None
  if agreement == "DECLARED_ONLY" and float(rec.get("trust") or 0) >= MIN_DECLARED_TRUST:
    return True, None, None
  if agreement == "CONFLICT" and int(rec.get("support") or 0) >= STRONG_CONFLICT_SUPPORT:
    return True, None, None
  return False, "SCALE_NEEDS_CONFIRMATION", _NEEDS_PERSON.get(agreement, "The scale of this sheet is not confirmed. Confirm it on the Measure page.")

def composite_issue(title: dict | None, others_read: bool):
  t = title or {}
  if not t.get("composite") or not others_read:
    return None
  if int(t.get("structural_views") or 0) >= 2:
    return ("COMPOSITE_STRUCTURAL", "ACTION", "This sheet shows several structural drawings (foundation, framing, details) at different scales. "
      "It is not read automatically yet. Measure it by hand on the Measure page.")
  return ("SET_ASIDE_COMPOSITE", "INFO", "This sheet shows several drawings at different scales (plans, sections, elevations, schedules). "
    "Its floor plans are read from their own sheets, so it is not read again here.")